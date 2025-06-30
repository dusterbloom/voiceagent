#!/usr/bin/env python3
"""
Test script for WhisperLive connection
"""

import asyncio
import logging
import sys
import numpy as np
from agents.whisper_live_client import WhisperLiveClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_whisperlive_connection():
    """Test basic WhisperLive connection"""
    print("Testing WhisperLive connection...")

    def transcription_handler(text: str, is_final: bool):
        status = "FINAL" if is_final else "PARTIAL"
        print(f"[{status}] {text}")

    client = WhisperLiveClient()
    client.set_transcription_callback(transcription_handler)

    try:
        # Test connection
        await client.connect()
        await client.start_streaming()

        print("✓ Connected successfully!")
        print("Sending test audio data...")

        # Generate some test audio (silence)
        sample_rate = 16000
        duration = 2.0  # 2 seconds
        samples = int(sample_rate * duration)

        # Generate silence (zeros)
        audio_data = np.zeros(samples, dtype=np.int16)

        # Send in chunks
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i : i + chunk_size]
            await client.send_audio(chunk.tobytes())
            await asyncio.sleep(0.1)  # Small delay between chunks

        print("Test audio sent. Waiting for response...")
        await asyncio.sleep(3)  # Wait for any responses

        await client.stop_streaming()
        print("✓ Test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await client.disconnect()


async def main():
    """Main test function"""
    print("WhisperLive Connection Test")
    print("=" * 30)

    success = await test_whisperlive_connection()

    if success:
        print("\n✓ WhisperLive is working correctly!")
        print("You can now start the voice agent with: python3 main.py")
    else:
        print("\n❌ WhisperLive test failed")
        print("Make sure WhisperLive server is running:")
        print("  ./start_whisperlive.sh")

    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
