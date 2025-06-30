#!/usr/bin/env python3
"""
Test TTS functionality
"""

import asyncio
import logging
from agents.tts_agent import TTSAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_tts():
    """Test TTS functionality"""
    print("Testing TTS Agent...")

    agent = TTSAgent()

    # Check available engines
    available = await agent.check_tts_availability()
    print(f"Available TTS engines: {available}")

    # Test audio generation
    test_text = "Hello! This is a test of the text to speech system. Can you hear me?"
    print(f"Generating speech for: '{test_text}'")

    audio_data = await agent.text_to_speech(test_text)

    if audio_data:
        print(f"✓ Generated {len(audio_data)} bytes of audio")

        # Try to play it
        from agents.audio_output import AudioOutputAgent

        output_agent = AudioOutputAgent()
        output_agent.initialize()

        print("Playing audio...")
        await output_agent.play_audio(audio_data)
        output_agent.wait_for_completion()

        print("✓ Audio playback completed")
        output_agent.cleanup()

        return True
    else:
        print("❌ No audio generated")
        return False


async def main():
    """Main test function"""
    print("TTS Test")
    print("=" * 20)

    success = await test_tts()

    if success:
        print("\n✓ TTS is working correctly!")
    else:
        print("\n❌ TTS test failed")

    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        exit(1)
