"""
Text-to-Speech Component using Piper
Clean, reusable TTS functionality
"""

import subprocess
import logging
import os
import tempfile
import pygame
import threading
import time

logger = logging.getLogger(__name__)


class TTSComponent:
    """Clean TTS component using Piper"""

    def __init__(self, model_path="models/piper/en_US-lessac-medium.onnx"):
        self.model_path = model_path
        self.is_speaking = False
        self.audio_queue = []
        self.speaking_thread = None

        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            logger.info("Pygame mixer initialized for TTS")
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")

    def check_piper(self):
        """Check if Piper is available"""
        try:
            result = subprocess.run(
                ["piper", "--help"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def check_model(self):
        """Check if TTS model exists"""
        return os.path.exists(self.model_path)

    def synthesize_to_file(self, text, output_file):
        """Synthesize text to audio file using Piper"""
        try:
            if not self.check_model():
                return False, f"Model not found: {self.model_path}"

            # Run Piper command
            cmd = ["piper", "--model", self.model_path, "--output_file", output_file]

            result = subprocess.run(
                cmd, input=text, text=True, capture_output=True, timeout=30
            )

            if result.returncode == 0 and os.path.exists(output_file):
                return True, "TTS synthesis successful"
            else:
                error_msg = result.stderr or "TTS synthesis failed"
                logger.error(f"Piper error: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "TTS synthesis timeout"
        except Exception as e:
            error_msg = f"TTS error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def speak_text(self, text, blocking=False):
        """Convert text to speech and play it"""
        if not text.strip():
            return False, "Empty text"

        try:
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Synthesize speech
            success, message = self.synthesize_to_file(text, temp_path)
            if not success:
                return False, message

            # Play audio
            if blocking:
                return self._play_audio_blocking(temp_path)
            else:
                return self._play_audio_async(temp_path)

        except Exception as e:
            error_msg = f"Speak error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _play_audio_blocking(self, audio_file):
        """Play audio file synchronously"""
        try:
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            # Clean up
            os.unlink(audio_file)
            return True, "Audio played successfully"

        except Exception as e:
            error_msg = f"Audio playback error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _play_audio_async(self, audio_file):
        """Play audio file asynchronously"""
        try:
            self.audio_queue.append(audio_file)

            # Start playback thread if not running
            if not self.is_speaking:
                self.speaking_thread = threading.Thread(
                    target=self._audio_playback_worker, daemon=True
                )
                self.speaking_thread.start()

            return True, "Audio queued for playback"

        except Exception as e:
            error_msg = f"Audio queue error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _audio_playback_worker(self):
        """Worker thread for audio playback queue"""
        self.is_speaking = True

        try:
            while self.audio_queue:
                audio_file = self.audio_queue.pop(0)

                try:
                    pygame.mixer.music.load(audio_file)
                    pygame.mixer.music.play()

                    # Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                    # Clean up
                    os.unlink(audio_file)

                except Exception as e:
                    logger.error(f"Playback error: {e}")

        finally:
            self.is_speaking = False

    def stop_speaking(self):
        """Stop current speech and clear queue"""
        try:
            pygame.mixer.music.stop()
            self.audio_queue.clear()
            self.is_speaking = False
            return True, "Speech stopped"
        except Exception as e:
            error_msg = f"Stop error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def is_currently_speaking(self):
        """Check if TTS is currently speaking"""
        return self.is_speaking or pygame.mixer.music.get_busy()

    def get_queue_length(self):
        """Get number of items in audio queue"""
        return len(self.audio_queue)
