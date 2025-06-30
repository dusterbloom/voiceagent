import gradio as gr
import threading
import logging
import socket
import sys
import time

# Add WhisperLive to path
sys.path.append("./WhisperLive")

from whisper_live.client import TranscriptionClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_services():
    """Check if required services are running"""
    status = []
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
    return "\n".join(status)


class SimpleWhisperStreamer:
    def __init__(self):
        self.client = None
        self.is_streaming = False
        self.transcription_text = "Ready to start streaming..."
        self.streaming_thread = None

    def transcription_callback(self, text, segments):
        """Callback function to handle transcription results"""
        if text.strip():
            self.transcription_text = text
            logger.info(f"Transcription: {text}")

    def start_streaming(self):
        """Start real-time microphone transcription"""
        if self.is_streaming:
            return "Already streaming", self.transcription_text

        try:
            self.transcription_text = "Initializing WhisperLive client..."

            # Initialize WhisperLive client with gentle VAD settings
            self.client = TranscriptionClient(
                host="localhost",
                port=9091,
                lang="en",
                translate=False,
                model="base",
                use_vad=True,
                save_output_recording=False,
                log_transcription=False,
                transcription_callback=self.transcription_callback,
                # Gentle VAD settings for better sensitivity
                send_last_n_segments=5,  # Send more segments for smoother experience
                no_speech_thresh=0.3,  # Lower threshold = more sensitive (default 0.45)
                clip_audio=False,  # Don't clip audio aggressively
                same_output_threshold=5,  # Reduce repetition threshold
            )

            self.is_streaming = True
            self.transcription_text = "🎤 Listening... Speak into your microphone!"

            # Start streaming in a separate thread
            def stream():
                try:
                    # Call client() with no parameters for microphone input
                    self.client()
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    self.transcription_text = f"Streaming error: {e}"
                    self.is_streaming = False

            self.streaming_thread = threading.Thread(target=stream, daemon=True)
            self.streaming_thread.start()

            return "🎤 Started microphone streaming", self.transcription_text

        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            self.is_streaming = False
            self.transcription_text = f"Error: {str(e)}"
            return f"❌ Error: {str(e)}", self.transcription_text

    def stop_streaming(self):
        """Stop real-time transcription"""
        if not self.is_streaming:
            return "Not streaming", self.transcription_text

        try:
            self.is_streaming = False
            if self.client:
                self.client.close_all_clients()

            self.transcription_text = "⏹️ Streaming stopped"
            return "⏹️ Stopped transcription", self.transcription_text

        except Exception as e:
            logger.error(f"Failed to stop streaming: {e}")
            return f"❌ Error: {str(e)}", self.transcription_text

    def get_transcription(self):
        """Get current transcription text"""
        return self.transcription_text


# Global streamer instance
streamer = SimpleWhisperStreamer()


def start_transcription():
    """Start button handler"""
    status, transcription = streamer.start_streaming()
    return status, transcription


def stop_transcription():
    """Stop button handler"""
    status, transcription = streamer.stop_streaming()
    return status, transcription


def refresh_transcription():
    """Refresh transcription display"""
    return streamer.get_transcription()


# Create Gradio interface
with gr.Blocks(title="WhisperLive Microphone Streaming", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🎤 WhisperLive Real-Time Microphone Transcription")
    gr.Markdown(
        "**Live microphone streaming** using WhisperLive's built-in microphone support!"
    )

    with gr.Row():
        with gr.Column():
            # Service status
            status_display = gr.Textbox(
                label="Service Status",
                value=check_services(),
                interactive=False,
                lines=2,
            )

            # Control buttons
            with gr.Row():
                start_btn = gr.Button(
                    "🎤 Start Microphone Streaming", variant="primary"
                )
                stop_btn = gr.Button("⏹️ Stop Streaming", variant="secondary")

            # Status messages
            status_output = gr.Textbox(
                label="Status",
                value="Ready to start...",
                lines=2,
            )

        with gr.Column():
            # Live transcription display
            transcription_output = gr.Textbox(
                label="🎯 Live Transcription",
                value="Click 'Start Microphone Streaming' to begin...",
                lines=10,
                max_lines=20,
            )

            # Manual refresh button
            refresh_btn = gr.Button("🔄 Refresh Transcription")

    # Usage instructions
    # VAD Settings info
    gr.Markdown("### ⚡ Gentle VAD Features:")
    gr.Markdown(
        "- **Sensitive Detection**: Lower speech threshold (0.3) for better pickup"
    )
    gr.Markdown("- **Smooth Streaming**: More segments (5) for continuous flow")
    gr.Markdown("- **Less Clipping**: Preserves quiet speech")
    gr.Markdown("- **Reduced Repetition**: Smart filtering of duplicate outputs")

    gr.Markdown("### 🎯 Usage:")
    gr.Markdown(
        "1. Make sure WhisperLive server is running: `python WhisperLive/run_server.py --port 9091 --backend faster_whisper`"
    )
    gr.Markdown("2. Click 'Start Microphone Streaming'")
    gr.Markdown("3. Speak into your microphone (even quietly!)")
    gr.Markdown("4. Click 'Refresh Transcription' to see latest results")
    gr.Markdown("5. Click 'Stop Streaming' when done")

    # Connect button handlers
    start_btn.click(
        fn=start_transcription,
        outputs=[status_output, transcription_output],
    )

    stop_btn.click(
        fn=stop_transcription,
        outputs=[status_output, transcription_output],
    )

    refresh_btn.click(
        fn=refresh_transcription,
        outputs=[transcription_output],
    )

    # Add refresh button for status
    refresh_status_btn = gr.Button("🔄 Refresh Service Status")
    refresh_status_btn.click(fn=check_services, outputs=[status_display])


if __name__ == "__main__":
    print("🎤 Starting WhisperLive Microphone Streaming Interface...")
    print("📋 Service Status:")
    print(check_services())
    print("\n🌐 Interface: http://localhost:7872")
    print("🎯 Real-time microphone transcription using WhisperLive!")
    print("⚡ Just click Start and speak into your microphone!")

    app.launch(server_name="0.0.0.0", server_port=7872, share=False)
