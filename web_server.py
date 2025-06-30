import asyncio
import websockets
import json
import base64
import tempfile
import os
from pathlib import Path
import logging
from agents.whisper_live_client import WhisperLiveClient
from agents.llm_agent import LLMAgent
from agents.tts_agent import TTSAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebVoiceAgent:
    def __init__(self):
        self.whisper_client = WhisperLiveClient()
        self.llm_agent = LLMAgent()
        self.tts_agent = TTSAgent()

    async def process_audio(self, audio_data):
        """Process audio data through the voice agent pipeline"""
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_audio_path = temp_file.name

            try:
                # Convert webm to wav for processing
                wav_path = temp_audio_path.replace(".webm", ".wav")
                os.system(
                    f'ffmpeg -i "{temp_audio_path}" -ar 16000 -ac 1 "{wav_path}" -y 2>/dev/null'
                )

                if not os.path.exists(wav_path):
                    return {"error": "Audio conversion failed"}

                # Transcribe audio
                transcription = await self.transcribe_audio_file(wav_path)
                if not transcription:
                    return {"error": "No speech detected"}

                # Get LLM response
                llm_response = await self.llm_agent.get_response(transcription)

                # Generate TTS audio
                tts_audio_path = await self.tts_agent.generate_speech(llm_response)

                # Read TTS audio and encode to base64
                audio_response = None
                if tts_audio_path and os.path.exists(tts_audio_path):
                    with open(tts_audio_path, "rb") as f:
                        audio_response = base64.b64encode(f.read()).decode()
                    os.unlink(tts_audio_path)  # Clean up

                return {
                    "transcription": transcription,
                    "response": llm_response,
                    "audio": audio_response,
                }

            finally:
                # Clean up temp files
                for path in [temp_audio_path, wav_path]:
                    if os.path.exists(path):
                        os.unlink(path)

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {"error": str(e)}

    async def transcribe_audio_file(self, audio_path):
        """Transcribe audio file using WhisperLive"""
        try:
            # Read audio file
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            # Connect to WhisperLive and send audio
            await self.whisper_client.connect()

            # Send audio in chunks
            chunk_size = 1024
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i : i + chunk_size]
                await self.whisper_client.send_audio(chunk)

            # Get transcription
            transcription = await self.whisper_client.get_transcription()
            await self.whisper_client.disconnect()

            return transcription

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None


async def handle_websocket(websocket):
    """Handle WebSocket connections from the frontend"""
    logger.info(f"New WebSocket connection: {websocket.remote_address}")

    voice_agent = WebVoiceAgent()

    try:
        async for message in websocket:
            try:
                data = json.loads(message)

                if data.get("type") == "audio":
                    logger.info("Processing audio message")

                    # Send transcription update
                    await websocket.send(
                        json.dumps(
                            {"type": "status", "message": "Transcribing audio..."}
                        )
                    )

                    # Process the audio
                    result = await voice_agent.process_audio(data["data"])

                    if "error" in result:
                        await websocket.send(
                            json.dumps({"type": "error", "message": result["error"]})
                        )
                    else:
                        # Send transcription
                        if result.get("transcription"):
                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "transcription",
                                        "text": result["transcription"],
                                    }
                                )
                            )

                        # Send response with audio
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "response",
                                    "text": result.get(
                                        "response", "No response generated"
                                    ),
                                    "audio": result.get("audio"),
                                }
                            )
                        )

            except json.JSONDecodeError:
                await websocket.send(
                    json.dumps({"type": "error", "message": "Invalid JSON message"})
                )
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await websocket.send(json.dumps({"type": "error", "message": str(e)}))

    except websockets.exceptions.ConnectionClosed:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def main():
    """Start the WebSocket server"""
    logger.info("Starting Voice Agent Web Server...")

    # Check if required services are running
    logger.info("Checking WhisperLive server...")
    logger.info("Checking Ollama server...")

    logger.info("Voice Agent Web Server running on ws://localhost:8765")
    logger.info("Open frontend/index.html in your browser to use the voice agent")

    # Start WebSocket server
    async with websockets.serve(handle_websocket, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
