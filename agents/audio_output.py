import asyncio
import pygame
import io
import wave
import logging
from typing import Optional
import threading
import queue
from config import SAMPLE_RATE

logger = logging.getLogger(__name__)


class AudioOutputAgent:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.is_initialized = False
        self.is_playing = False
        self.audio_queue = queue.Queue()
        self.playback_thread: Optional[threading.Thread] = None
        self.stop_playback = threading.Event()

    def initialize(self):
        """Initialize pygame mixer for audio playback"""
        try:
            pygame.mixer.pre_init(
                frequency=self.sample_rate,
                size=-16,  # 16-bit signed
                channels=1,  # Mono
                buffer=1024,
            )
            pygame.mixer.init()
            self.is_initialized = True
            logger.info(f"Audio output initialized: {self.sample_rate}Hz")

            # Start playback thread
            self.playback_thread = threading.Thread(
                target=self._playback_worker, daemon=True
            )
            self.playback_thread.start()

        except Exception as e:
            logger.error(f"Failed to initialize audio output: {e}")
            raise

    def _playback_worker(self):
        """Worker thread for audio playback"""
        while not self.stop_playback.is_set():
            try:
                # Get audio data from queue (with timeout)
                audio_data = self.audio_queue.get(timeout=0.1)

                if audio_data is None:  # Shutdown signal
                    break

                self._play_audio_data(audio_data)
                self.audio_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Playback worker error: {e}")

    def _play_audio_data(self, audio_data: bytes):
        """Play audio data using pygame"""
        try:
            # Create a BytesIO object from audio data
            audio_io = io.BytesIO(audio_data)

            # Load and play the audio
            sound = pygame.mixer.Sound(audio_io)
            channel = sound.play()

            # Wait for playback to complete
            while channel.get_busy():
                pygame.time.wait(10)

        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    async def play_audio(self, audio_data: bytes):
        """Queue audio data for playback"""
        if not self.is_initialized:
            self.initialize()

        if not audio_data:
            logger.warning("Empty audio data received")
            return

        try:
            # Add audio to playback queue
            self.audio_queue.put(audio_data)
            logger.debug(f"Queued audio: {len(audio_data)} bytes")

        except Exception as e:
            logger.error(f"Failed to queue audio: {e}")

    def stop_all_audio(self):
        """Stop all audio playback"""
        try:
            pygame.mixer.stop()
            # Clear the queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except queue.Empty:
                    break
            logger.info("Stopped all audio playback")
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")

    def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)"""
        try:
            volume = max(0.0, min(1.0, volume))  # Clamp to valid range
            pygame.mixer.music.set_volume(volume)
            logger.info(f"Volume set to {volume}")
        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    def is_busy(self) -> bool:
        """Check if audio is currently playing"""
        try:
            return pygame.mixer.get_busy() or not self.audio_queue.empty()
        except:
            return False

    def wait_for_completion(self, timeout: float = 10.0):
        """Wait for all queued audio to finish playing"""
        import time

        start_time = time.time()

        while self.is_busy() and (time.time() - start_time) < timeout:
            time.sleep(0.1)

    def cleanup(self):
        """Cleanup resources"""
        try:
            self.stop_playback.set()

            if self.playback_thread and self.playback_thread.is_alive():
                # Signal shutdown
                self.audio_queue.put(None)
                self.playback_thread.join(timeout=2.0)

            if self.is_initialized:
                pygame.mixer.quit()
                self.is_initialized = False

            logger.info("Audio output cleanup completed")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def __del__(self):
        """Destructor"""
        self.cleanup()


# Alternative simpler audio output using sounddevice
try:
    import sounddevice as sd
    import numpy as np

    class SoundDeviceOutputAgent:
        """Alternative audio output using sounddevice"""

        def __init__(self, sample_rate: int = SAMPLE_RATE):
            self.sample_rate = sample_rate

        async def play_audio(self, audio_data: bytes):
            """Play audio using sounddevice"""
            try:
                # Convert bytes to numpy array
                # Assuming 16-bit PCM audio
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

                # Normalize to float32 range [-1, 1]
                audio_float = audio_array.astype(np.float32) / 32768.0

                # Play audio (blocking)
                sd.play(audio_float, samplerate=self.sample_rate)
                sd.wait()  # Wait for playback to complete

            except Exception as e:
                logger.error(f"SoundDevice playback error: {e}")

        def stop_all_audio(self):
            """Stop all audio playback"""
            sd.stop()

        def set_volume(self, volume: float):
            """Set volume (not directly supported by sounddevice)"""
            logger.warning("Volume control not supported with sounddevice")

        def is_busy(self) -> bool:
            """Check if audio is playing"""
            return sd.get_stream().active if sd.get_stream() else False

        def cleanup(self):
            """Cleanup"""
            sd.stop()

except ImportError:
    logger.warning("sounddevice not available, using pygame only")
    SoundDeviceOutputAgent = None


# Example usage
async def main():
    logging.basicConfig(level=logging.INFO)

    agent = AudioOutputAgent()

    try:
        # Test with a simple beep (generate test audio)
        import numpy as np
        import wave
        import tempfile

        # Generate a test tone
        duration = 1.0  # seconds
        frequency = 440  # Hz (A4 note)
        sample_rate = 16000

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t)

        # Convert to 16-bit PCM
        audio_data = (tone * 32767).astype(np.int16)

        # Create WAV file in memory
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            with wave.open(temp_file.name, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())

            # Read the WAV file as bytes
            with open(temp_file.name, "rb") as f:
                wav_bytes = f.read()

        # Play the test audio
        print("Playing test tone...")
        await agent.play_audio(wav_bytes)

        # Wait for completion
        agent.wait_for_completion()
        print("Test completed")

    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
