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


class GentleVADStreamer:
    def __init__(self):
        self.client = None
        self.is_streaming = False
        self.transcription_text = "Ready to start streaming..."
        self.streaming_thread = None
        self.vad_sensitivity = "medium"  # gentle, medium, aggressive

    def transcription_callback(self, text, segments):
        """Callback function to handle transcription results"""
        if text.strip():
            self.transcription_text = text
            logger.info(f"Transcription: {text}")

    def get_vad_settings(self, sensitivity):
        """Get VAD settings based on sensitivity level"""
        if sensitivity == "gentle":
            return {
                "send_last_n_segments": 8,
                "no_speech_thresh": 0.2,  # Very sensitive
                "clip_audio": False,
                "same_output_threshold": 3,
            }
        elif sensitivity == "medium":
            return {
                "send_last_n_segments": 5,
                "no_speech_thresh": 0.3,  # Moderately sensitive
                "clip_audio": False,
                "same_output_threshold": 5,
            }
        else:  # aggressive
            return {
                "send_last_n_segments": 3,
                "no_speech_thresh": 0.5,  # Less sensitive
                "clip_audio": True,
                "same_output_threshold": 8,
            }

    def start_streaming(self, sensitivity="medium"):
        """Start real-time microphone transcription with VAD sensitivity"""
        if self.is_streaming:
            return "Already streaming", self.transcription_text

        try:
            self.vad_sensitivity = sensitivity
            self.transcription_text = (
                f"Initializing WhisperLive client with {sensitivity} VAD..."
            )

            # Get VAD settings
            vad_settings = self.get_vad_settings(sensitivity)

            # Initialize WhisperLive client with chosen VAD settings
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
                **vad_settings,  # Apply VAD settings
            )

            self.is_streaming = True
            self.transcription_text = (
                f"🎤 Listening with {sensitivity} VAD... Speak into your microphone!"
            )

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

            return (
                f"🎤 Started microphone streaming with {sensitivity} VAD",
                self.transcription_text,
            )

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
streamer = GentleVADStreamer()


def start_transcription(sensitivity):
    """Start button handler with VAD sensitivity"""
    status, transcription = streamer.start_streaming(sensitivity)
    return status, transcription


def stop_transcription():
    """Stop button handler"""
    status, transcription = streamer.stop_streaming()
    return status, transcription


def refresh_transcription():
    """Refresh transcription display"""
    return streamer.get_transcription()


# Create Gradio interface
with gr.Blocks(title="WhisperLive Gentle VAD", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🎤 WhisperLive with Gentle VAD")
    gr.Markdown(
        "**Adjustable Voice Activity Detection** for optimal speech sensitivity!"
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

            # VAD Sensitivity selector
            vad_sensitivity = gr.Radio(
                choices=["gentle", "medium", "aggressive"],
                value="medium",
                label="🎚️ VAD Sensitivity",
                info="Gentle = picks up quiet speech, Aggressive = only clear speech",
            )

            # Control buttons
            with gr.Row():
                start_btn = gr.Button("🎤 Start with Selected VAD", variant="primary")
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
                value="Select VAD sensitivity and click 'Start with Selected VAD'...",
                lines=10,
                max_lines=20,
            )

            # Manual refresh button
            refresh_btn = gr.Button("🔄 Refresh Transcription")

    # VAD Settings explanation
    gr.Markdown("### 🎚️ VAD Sensitivity Levels:")

    with gr.Row():
        with gr.Column():
            gr.Markdown("**🟢 Gentle VAD:**")
            gr.Markdown("- Speech threshold: 0.2 (very sensitive)")
            gr.Markdown("- Segments: 8 (smooth flow)")
            gr.Markdown("- No audio clipping")
            gr.Markdown("- Best for: Quiet speakers, whispers")

        with gr.Column():
            gr.Markdown("**🟡 Medium VAD:**")
            gr.Markdown("- Speech threshold: 0.3 (balanced)")
            gr.Markdown("- Segments: 5 (good flow)")
            gr.Markdown("- No audio clipping")
            gr.Markdown("- Best for: Normal conversation")

        with gr.Column():
            gr.Markdown("**🔴 Aggressive VAD:**")
            gr.Markdown("- Speech threshold: 0.5 (less sensitive)")
            gr.Markdown("- Segments: 3 (focused)")
            gr.Markdown("- Audio clipping enabled")
            gr.Markdown("- Best for: Noisy environments")

    # Usage instructions
    gr.Markdown("### 🎯 Usage:")
    gr.Markdown(
        "1. Make sure WhisperLive server is running: `python WhisperLive/run_server.py --port 9091 --backend faster_whisper`"
    )
    gr.Markdown("2. Choose your VAD sensitivity level")
    gr.Markdown("3. Click 'Start with Selected VAD'")
    gr.Markdown("4. Speak into your microphone")
    gr.Markdown("5. Click 'Refresh Transcription' to see latest results")
    gr.Markdown("6. Click 'Stop Streaming' when done")

    # Connect button handlers
    start_btn.click(
        fn=start_transcription,
        inputs=[vad_sensitivity],
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
    print("🎤 Starting WhisperLive Gentle VAD Interface...")
    print("📋 Service Status:")
    print(check_services())
    print("\n🌐 Interface: http://localhost:7873")
    print("🎯 Adjustable VAD sensitivity for optimal speech detection!")
    print("⚡ Choose gentle for quiet speech, aggressive for noisy environments!")

    app.launch(server_name="0.0.0.0", server_port=7873, share=False)
