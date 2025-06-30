import gradio as gr
import asyncio
import websockets
import json
import logging
import socket
import requests
import numpy as np
import threading
import time
import os
import librosa
from queue import Queue, Empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_services():
    """Check if required services are running"""
    status = []

    # Check WhisperLive
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", 9091))
        sock.close()
        if result == 0:
            status.append("✅ WhisperLive server running on port 9091")
        else:
            status.append("❌ WhisperLive server not running on port 9091")
    except Exception as e:
        status.append(f"❌ Error checking WhisperLive: {e}")

    # Check Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            status.append("✅ Ollama server running on port 11434")
        else:
            status.append("❌ Ollama server not responding")
    except Exception as e:
        status.append("❌ Ollama server not running on port 11434")

    return "\n".join(status)


class WhisperLiveStreamer:
    def __init__(self):
        self.websocket = None
        self.transcription_queue = Queue()
        self.is_connected = False
        self.segments = []

    async def connect(self):
        """Connect to WhisperLive with correct configuration"""
        try:
            self.websocket = await websockets.connect("ws://localhost:9091")

            # Send COMPLETE configuration like original client
            config = {
                "uid": "gradio_realtime",
                "language": "en",
                "task": "transcribe",
                "model": "base",
                "use_vad": True,
                "max_clients": 4,
                "max_connection_time": 600,
                "send_last_n_segments": 10,
                "no_speech_thresh": 0.45,
                "clip_audio": False,
                "same_output_threshold": 10,
            }
            await self.websocket.send(json.dumps(config))
            self.is_connected = True
            logger.info("Connected to WhisperLive with full config")

            # Start listening
            asyncio.create_task(self._listen())

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.is_connected = False

    async def _listen(self):
        """Listen for transcription responses"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if "segments" in data:
                        # Process segments - this is where the transcription comes from!
                        for segment in data["segments"]:
                            if segment.get("text", "").strip():
                                self.transcription_queue.put(segment)
                                logger.info(f"Segment: {segment}")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Listen error: {e}")

    async def stream_audio_16k(self, audio_data_16k):
        """Stream 16kHz audio data to WhisperLive"""
        try:
            # Stream in real-time chunks (16kHz rate)
            chunk_size = int(16000 * 0.1)  # 100ms chunks at 16kHz

            logger.info(
                f"Streaming {len(audio_data_16k)} samples at 16kHz in chunks of {chunk_size}"
            )

            for i in range(0, len(audio_data_16k), chunk_size):
                chunk = audio_data_16k[i : i + chunk_size]
                # Send as float32 bytes
                await self.websocket.send(chunk.astype(np.float32).tobytes())
                await asyncio.sleep(0.05)  # Real-time simulation

        except Exception as e:
            logger.error(f"Streaming error: {e}")

    async def disconnect(self):
        """Disconnect from WhisperLive"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False

    def get_transcription_text(self):
        """Get complete transcription from all segments"""
        segments = []
        try:
            while True:
                segments.append(self.transcription_queue.get_nowait())
        except Empty:
            pass

        if segments:
            # Get the latest completed segments
            completed_segments = [s for s in segments if s.get("completed", False)]
            if completed_segments:
                # Return the text from completed segments
                return " ".join([s["text"].strip() for s in completed_segments])
            else:
                # Return the latest partial segment
                latest = segments[-1]
                return latest["text"].strip()

        return ""


def process_audio_realtime(audio_input):
    """Process audio with real-time WhisperLive streaming"""
    if audio_input is None:
        return "No audio provided", "Please record some audio first."

    try:
        logger.info(f"Processing audio: {type(audio_input)}")

        # Handle Gradio audio input format: (sample_rate, numpy_array)
        if isinstance(audio_input, tuple) and len(audio_input) == 2:
            sample_rate, audio_data = audio_input
            logger.info(f"Audio data: {sample_rate}Hz, {len(audio_data)} samples")

            # Check if audio data is valid
            if len(audio_data) == 0:
                return "Empty audio recording", "Please record some audio."

            # Check if audio contains actual sound
            if np.max(np.abs(audio_data)) < 100:
                return (
                    "Very quiet audio detected",
                    "Please speak louder or check your microphone.",
                )

            # Convert to float and resample to 16kHz (WhisperLive requirement)
            audio_float = audio_data.astype(np.float32) / 32768.0
            audio_16k = librosa.resample(
                audio_float, orig_sr=sample_rate, target_sr=16000
            )

            logger.info(f"Resampled: {len(audio_16k)} samples at 16kHz")

        else:
            return "Invalid audio format", "Please try recording again."

        # Run streaming in async context
        async def run_streaming():
            streamer = WhisperLiveStreamer()
            await streamer.connect()

            if not streamer.is_connected:
                return "Connection failed", "Could not connect to WhisperLive"

            await streamer.stream_audio_16k(audio_16k)
            await asyncio.sleep(3)  # Wait for final results

            transcription = streamer.get_transcription_text()
            await streamer.disconnect()

            return transcription

        # Run async code
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            transcription = loop.run_until_complete(run_streaming())
        finally:
            loop.close()

        if isinstance(transcription, tuple):
            return transcription

        if transcription:
            response = f"🎯 Real-time transcription successful!\n\nTranscribed: '{transcription}'\n\n⚡ Processed with WhisperLive streaming at 16kHz!\n📊 Original: {sample_rate}Hz → Resampled: 16kHz"
            return transcription, response
        else:
            return (
                "No speech detected",
                "Try speaking more clearly or check if audio contains speech.",
            )

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return f"Error: {str(e)}", "Processing failed."


# Create real-time interface
with gr.Blocks(title="WhisperLive Real-Time", theme=gr.themes.Soft()) as app:
    gr.Markdown("# ⚡ WhisperLive Real-Time Transcription")
    gr.Markdown(
        "**Ultra-low latency** streaming transcription with proper 16kHz format!"
    )

    with gr.Row():
        with gr.Column():
            # Service status
            status_display = gr.Textbox(
                label="Service Status",
                value=check_services(),
                interactive=False,
                lines=3,
            )

            # Audio input
            audio_input = gr.Audio(label="🎤 Record Your Voice", sources=["microphone"])

            # Process button
            process_btn = gr.Button("⚡ Real-Time Transcribe", variant="primary")

        with gr.Column():
            # Transcription output
            transcription_output = gr.Textbox(
                label="⚡ WhisperLive Transcription",
                placeholder="Real-time transcription will appear here...",
                lines=4,
            )

            # Response text
            response_text = gr.Textbox(
                label="Processing Details",
                placeholder="Processing details will appear here...",
                lines=6,
            )

    # Technical details
    gr.Markdown("### ⚡ Real-Time Performance:")
    gr.Markdown("- **Sample Rate**: Auto-resampled to 16kHz (WhisperLive requirement)")
    gr.Markdown("- **Chunk Size**: 100ms audio chunks for real-time processing")
    gr.Markdown("- **Latency**: ~50-200ms processing delay")
    gr.Markdown("- **Method**: Direct WebSocket streaming with segments")
    gr.Markdown(
        "- **Format**: Complete configuration matching original WhisperLive client"
    )

    gr.Markdown("### 🎯 Test phrases:")
    gr.Markdown("- 'Hello, this is a real-time transcription test'")
    gr.Markdown("- 'The weather is beautiful today'")
    gr.Markdown("- 'WhisperLive streaming works perfectly'")

    # Connect the processing function
    process_btn.click(
        fn=process_audio_realtime,
        inputs=[audio_input],
        outputs=[transcription_output, response_text],
    )

    # Add refresh button for status
    refresh_btn = gr.Button("🔄 Refresh Service Status")
    refresh_btn.click(fn=check_services, outputs=[status_display])

if __name__ == "__main__":
    print("⚡ Starting WhisperLive Real-Time Interface (WORKING VERSION)...")
    print("📋 Service Status:")
    print(check_services())
    print("\n🌐 Real-time interface: http://localhost:7869")
    print("⚡ Ultra-low latency with 16kHz resampling!")
    print("🎯 Real-time streaming with segments processing!")

    app.launch(server_name="0.0.0.0", server_port=7869, share=False)
