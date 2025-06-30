#!/usr/bin/env python3
"""
Test the fixed WhisperLive integration
"""

import asyncio
import websockets
import json
import logging
import numpy as np
from scipy import signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resample_audio(audio_data, orig_sr, target_sr):
    """Resample audio using scipy"""
    if orig_sr == target_sr:
        return audio_data

    ratio = target_sr / orig_sr
    num_samples = int(len(audio_data) * ratio)
    resampled = signal.resample(audio_data, num_samples)

    return resampled.astype(np.float32)


async def test_fixed_whisperlive():
    """Test WhisperLive with fixed dependencies"""
    try:
        print("🔧 Testing fixed WhisperLive integration...")

        # Connect to WhisperLive
        websocket = await websockets.connect("ws://localhost:9091")
        print("✅ Connected!")

        # Send complete configuration
        config = {
            "uid": "fixed_test",
            "language": "en",
            "task": "transcribe",
            "model": "base",
            "use_vad": True,
            "max_clients": 4,
            "max_connection_time": 600,
            "send_last_n_segments": 10,
            "no_speech_thresh": 0.45,
            "clip_audio": False,
            "same_output_threshold": 10,
        }

        await websocket.send(json.dumps(config))

        # Wait for SERVER_READY
        response = await websocket.recv()
        print(f"📥 Server response: {response}")

        # Generate test audio at 44.1kHz and resample to 16kHz
        print("🎵 Generating and resampling test audio...")
        sample_rate = 44100
        duration = 3.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        frequency = 440  # A4 note
        audio_44k = (np.sin(2 * np.pi * frequency * t) * 0.5).astype(np.float32)

        # Resample to 16kHz using scipy
        audio_16k = resample_audio(audio_44k, sample_rate, 16000)

        print(f"🎵 Original: {len(audio_44k)} samples at {sample_rate}Hz")
        print(f"🎵 Resampled: {len(audio_16k)} samples at 16000Hz")

        # Start listening for responses
        responses = []

        async def listen_for_responses():
            try:
                async for message in websocket:
                    print(f"📥 Received: {message}")
                    responses.append(message)
                    try:
                        data = json.loads(message)
                        if "segments" in data:
                            print(f"🎯 SEGMENTS: {data['segments']}")
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                print(f"❌ Listen error: {e}")

        # Start listener
        listen_task = asyncio.create_task(listen_for_responses())

        # Send audio in chunks (16kHz rate)
        chunk_size = int(16000 * 0.1)  # 100ms chunks at 16kHz
        print(f"📦 Sending audio in chunks of {chunk_size} samples (16kHz)")

        for i in range(0, len(audio_16k), chunk_size):
            chunk = audio_16k[i : i + chunk_size]
            await websocket.send(chunk.astype(np.float32).tobytes())
            await asyncio.sleep(0.05)

        print("📤 All audio sent, waiting for transcription...")
        await asyncio.sleep(3)

        print(f"📋 Total responses received: {len(responses)}")

        # Clean up
        listen_task.cancel()
        await websocket.close()
        print("🔚 Test completed")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    print("🔧 Testing Fixed WhisperLive Integration")
    print("=" * 40)
    await test_fixed_whisperlive()


if __name__ == "__main__":
    asyncio.run(main())
