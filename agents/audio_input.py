import asyncio
import pyaudio
import numpy as np
from typing import Callable, Optional
import logging
from config import SAMPLE_RATE, CHUNK_SIZE, CHANNELS, FORMAT

logger = logging.getLogger(__name__)


class AudioInputAgent:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        chunk_size: int = CHUNK_SIZE,
        channels: int = CHANNELS,
        vad_threshold: float = 0.01,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.vad_threshold = vad_threshold
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_recording = False
        self.audio_callback: Optional[Callable] = None

    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """Set callback function to handle audio chunks"""
        self.audio_callback = callback

    def start_recording(self):
        """Start audio recording"""
        if self.is_recording:
            logger.warning("Already recording")
            return

        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
            )
            self.stream.start_stream()
            self.is_recording = True
            logger.info(
                f"Started recording: {self.sample_rate}Hz, {self.channels} channel(s)"
            )

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise

    def stop_recording(self):
        """Stop audio recording"""
        if not self.is_recording:
            return

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            self.is_recording = False
            logger.info("Stopped recording")

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for processing audio chunks"""
        if status:
            logger.warning(f"Audio callback status: {status}")

        # Voice Activity Detection (simple energy-based)
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        energy = np.sqrt(np.mean(audio_data**2))

        # Normalize energy to 0-1 range
        normalized_energy = energy / 32768.0

        if normalized_energy > self.vad_threshold:
            if self.audio_callback:
                self.audio_callback(in_data)

        return (None, pyaudio.paContinue)

    async def record_async(self, duration: Optional[float] = None):
        """Async recording method"""
        self.start_recording()

        try:
            if duration:
                await asyncio.sleep(duration)
            else:
                # Record indefinitely until stopped
                while self.is_recording:
                    await asyncio.sleep(0.1)
        finally:
            self.stop_recording()

    def get_audio_devices(self):
        """Get list of available audio input devices"""
        devices = []
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:
                devices.append(
                    {
                        "index": i,
                        "name": device_info["name"],
                        "channels": device_info["maxInputChannels"],
                        "sample_rate": device_info["defaultSampleRate"],
                    }
                )
        return devices

    def __del__(self):
        """Cleanup on destruction"""
        self.stop_recording()
        if hasattr(self, "audio"):
            self.audio.terminate()


# Example usage
async def main():
    logging.basicConfig(level=logging.INFO)

    def audio_handler(audio_data):
        print(f"Received audio chunk: {len(audio_data)} bytes")

    agent = AudioInputAgent()
    agent.set_audio_callback(audio_handler)

    # List available devices
    devices = agent.get_audio_devices()
    print("Available audio devices:")
    for device in devices:
        print(f"  {device['index']}: {device['name']}")

    # Record for 5 seconds
    await agent.record_async(duration=5.0)


if __name__ == "__main__":
    asyncio.run(main())
