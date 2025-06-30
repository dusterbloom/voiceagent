#!/usr/bin/env python3
"""
Real-time STT test with actual microphone input
"""

import asyncio
import logging
import sys
import numpy as np
from agents.whisper_live_client import WhisperLiveClient
from agents.audio_input import AudioInputAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class STTTester:
    def __init__(self):
        self.whisper_client = WhisperLiveClient()
        self.audio_input = AudioInputAgent()
        self.transcriptions = []

    def transcription_handler(self, text: str, is_final: bool):
        status = "FINAL" if is_final else "PARTIAL"
        print(f"[{status}] {text}")
        if is_final:
            self.transcriptions.append(text)

    async def audio_handler(self, audio_data: bytes):
        """Handle audio from microphone"""
        await self.whisper_client.send_audio(audio_data)

    async def test_realtime_stt(self, duration: int = 10):
        """Test real-time STT with microphone"""
        print(f"Testing real-time STT for {duration} seconds...")
        print("Speak into your microphone!")

        # Setup callbacks
        self.whisper_client.set_transcription_callback(self.transcription_handler)

        def audio_wrapper(audio_data):
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.audio_handler(audio_data))
                )
            except RuntimeError:
                pass

        self.audio_input.set_audio_callback(audio_wrapper)

        try:
            # Connect to WhisperLive
            await self.whisper_client.connect()
            await self.whisper_client.start_streaming()

            # Start recording
            self.audio_input.start_recording()

            print("Recording started! Speak now...")

            # Record for specified duration
            await asyncio.sleep(duration)

            print("Recording finished.")

            # Stop everything
            self.audio_input.stop_recording()
            await self.whisper_client.stop_streaming()

            return len(self.transcriptions) > 0

        except Exception as e:
            logger.error(f"Test failed: {e}")
            return False
        finally:
            await self.whisper_client.disconnect()


async def main():
    """Main test function"""
    print("Real-time STT Test")
    print("=" * 30)

    tester = STTTester()

    try:
        success = await tester.test_realtime_stt(duration=10)

        if success:
            print(
                f"\n✓ STT is working! Captured {len(tester.transcriptions)} transcriptions:"
            )
            for i, text in enumerate(tester.transcriptions, 1):
                print(f"  {i}. {text}")
        else:
            print("\n❌ STT test failed - no transcriptions captured")
            print("Check that:")
            print("1. WhisperLive server is running")
            print("2. Microphone is working")
            print("3. You spoke during the test")

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
