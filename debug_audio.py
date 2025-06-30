#!/usr/bin/env python3
"""
Debug audio input and VAD
"""

import asyncio
import logging
import sys
import numpy as np
from agents.audio_input import AudioInputAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioDebugger:
    def __init__(self):
        self.audio_input = AudioInputAgent(vad_threshold=0.001)  # Lower threshold
        self.audio_chunks_received = 0
        self.total_audio_bytes = 0

    def audio_handler(self, audio_data: bytes):
        """Debug audio handler"""
        self.audio_chunks_received += 1
        self.total_audio_bytes += len(audio_data)

        # Analyze audio data
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        if len(audio_np) > 0:
            energy = np.sqrt(np.mean(audio_np.astype(np.float64) ** 2))
            normalized_energy = energy / 32768.0

            print(
                f"Chunk {self.audio_chunks_received}: {len(audio_data)} bytes, energy: {normalized_energy:.4f}"
            )

            # Show if this would trigger VAD
            if normalized_energy > self.audio_input.vad_threshold:
                print(
                    f"  ✓ VAD TRIGGERED (energy {normalized_energy:.4f} > threshold {self.audio_input.vad_threshold})"
                )
            else:
                print(
                    f"  - Below VAD threshold ({normalized_energy:.4f} <= {self.audio_input.vad_threshold})"
                )

    async def test_audio_input(self, duration: int = 10):
        """Test audio input with debug info"""
        print(f"Testing audio input for {duration} seconds...")
        print("Speak into your microphone!")
        print(f"VAD threshold: {self.audio_input.vad_threshold}")

        # Setup callback
        self.audio_input.set_audio_callback(self.audio_handler)

        try:
            # Start recording
            self.audio_input.start_recording()
            print("Recording started! Speak now...")

            # Record for specified duration
            await asyncio.sleep(duration)

            print("Recording finished.")

            # Stop recording
            self.audio_input.stop_recording()

            print(f"\nSummary:")
            print(f"  Total chunks received: {self.audio_chunks_received}")
            print(f"  Total audio bytes: {self.total_audio_bytes}")
            print(
                f"  Average chunk size: {self.total_audio_bytes / max(1, self.audio_chunks_received):.1f} bytes"
            )

            return self.audio_chunks_received > 0

        except Exception as e:
            logger.error(f"Test failed: {e}")
            return False


async def main():
    """Main test function"""
    print("Audio Input Debug Test")
    print("=" * 30)

    debugger = AudioDebugger()

    try:
        success = await debugger.test_audio_input(duration=10)

        if success:
            print(f"\n✓ Audio input is working!")
        else:
            print(f"\n❌ No audio input detected")

        return success

    except KeyboardInterrupt:
        print("\nTest interrupted")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
