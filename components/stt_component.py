"""
Speech-to-Text Component using WhisperLive
Clean, reusable STT functionality
"""

import sys
import logging
import threading
import socket

# Add WhisperLive to path
sys.path.append("./WhisperLive")

from whisper_live.client import TranscriptionClient

logger = logging.getLogger(__name__)


class STTComponent:
    """Clean STT component using WhisperLive"""

    def __init__(self, host="localhost", port=9091):
        self.host = host
        self.port = port
        self.client = None
        self.is_streaming = False
        self.transcription_text = ""
        self.streaming_thread = None
        self.transcription_callback = None

    def set_transcription_callback(self, callback):
        """Set callback function for transcription results"""
        self.transcription_callback = callback

    def _internal_callback(self, text, segments):
        """Internal callback that handles transcription"""
        if text.strip():
            self.transcription_text = text
            logger.info(f"STT: {text}")

            # Call external callback if set
            if self.transcription_callback:
                self.transcription_callback(text, segments)

    def check_server(self):
        """Check if WhisperLive server is running"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def start_streaming(self, vad_sensitivity="medium"):
        """Start microphone streaming with VAD settings"""
        if self.is_streaming:
            return False, "Already streaming"

        if not self.check_server():
            return False, f"WhisperLive server not running on {self.host}:{self.port}"

        try:
            # VAD settings based on sensitivity
            vad_settings = self._get_vad_settings(vad_sensitivity)

            # Initialize WhisperLive client
            self.client = TranscriptionClient(
                host=self.host,
                port=self.port,
                lang="en",
                translate=False,
                model="base",
                use_vad=True,
                save_output_recording=False,
                log_transcription=False,
                transcription_callback=self._internal_callback,
                **vad_settings,
            )

            self.is_streaming = True

            # Start streaming in background thread
            def stream():
                try:
                    self.client()  # Start microphone streaming
                except Exception as e:
                    logger.error(f"STT streaming error: {e}")
                    self.is_streaming = False

            self.streaming_thread = threading.Thread(target=stream, daemon=True)
            self.streaming_thread.start()

            return True, f"Started STT with {vad_sensitivity} VAD"

        except Exception as e:
            logger.error(f"Failed to start STT: {e}")
            self.is_streaming = False
            return False, f"STT error: {str(e)}"

    def stop_streaming(self):
        """Stop microphone streaming"""
        if not self.is_streaming:
            return False, "Not streaming"

        try:
            self.is_streaming = False
            if self.client:
                self.client.close_all_clients()
            return True, "STT stopped"
        except Exception as e:
            logger.error(f"Failed to stop STT: {e}")
            return False, f"Stop error: {str(e)}"

    def get_latest_transcription(self):
        """Get the latest transcription text"""
        return self.transcription_text

    def clear_transcription(self):
        """Clear transcription text"""
        self.transcription_text = ""

    def _get_vad_settings(self, sensitivity):
        """Get VAD settings based on sensitivity level"""
        if sensitivity == "gentle":
            return {
                "send_last_n_segments": 8,
                "no_speech_thresh": 0.2,
                "clip_audio": False,
                "same_output_threshold": 3,
            }
        elif sensitivity == "medium":
            return {
                "send_last_n_segments": 5,
                "no_speech_thresh": 0.3,
                "clip_audio": False,
                "same_output_threshold": 5,
            }
        else:  # aggressive
            return {
                "send_last_n_segments": 3,
                "no_speech_thresh": 0.5,
                "clip_audio": True,
                "same_output_threshold": 8,
            }
