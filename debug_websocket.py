#!/usr/bin/env python3
"""
Debug WebSocket communication with WhisperLive
"""

import asyncio
import websockets
import json
import logging
import numpy as np

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def debug_whisperlive_connection():
    """Debug the WebSocket connection to WhisperLive"""
    try:
        print("🔍 Connecting to WhisperLive...")
        websocket = await websockets.connect("ws://localhost:9091")
        print("✅ Connected!")

        # Send configuration
        config = {
            "uid": "debug_client",
            "language": "en",
            "task": "transcribe",
            "model": "base",
            "use_vad": True,
            "save_output_recording": False,
            "log_transcription": True,
        }

        print(f"📤 Sending config: {config}")
        await websocket.send(json.dumps(config))

        # Listen for initial response
        print("👂 Listening for server response...")
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"📥 Server response: {response}")

            # Try to parse as JSON
            try:
                data = json.loads(response)
                print(f"📋 Parsed response: {data}")
            except json.JSONDecodeError:
                print(f"⚠️ Non-JSON response: {response}")

        except asyncio.TimeoutError:
            print("⏰ No response from server within 5 seconds")

        # Generate test audio (sine wave)
        print("🎵 Generating test audio...")
        sample_rate = 44100
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        frequency = 440  # A4 note
        audio_data = (np.sin(2 * np.pi * frequency * t) * 16384).astype(np.int16)

        # Convert to float32 like WhisperLive expects
        audio_float = audio_data.astype(np.float32) / 32768.0

        print(
            f"🎵 Audio: {len(audio_float)} samples, range {np.min(audio_float):.3f} to {np.max(audio_float):.3f}"
        )

        # Send audio in chunks
        chunk_size = int(sample_rate * 0.1)  # 100ms chunks
        print(
            f"📦 Sending {len(audio_float) // chunk_size} chunks of {chunk_size} samples each"
        )

        # Start listening for responses
        async def listen_for_responses():
            try:
                async for message in websocket:
                    print(f"📥 Received: {message}")
                    try:
                        data = json.loads(message)
                        print(f"📋 Parsed: {data}")
                        if "text" in data:
                            print(f"🎯 TRANSCRIPTION: '{data['text']}'")
                    except json.JSONDecodeError:
                        print(f"⚠️ Non-JSON: {message}")
            except Exception as e:
                print(f"❌ Listen error: {e}")

        # Start listener
        listen_task = asyncio.create_task(listen_for_responses())

        # Send audio chunks
        for i in range(0, len(audio_float), chunk_size):
            chunk = audio_float[i : i + chunk_size]
            print(f"📤 Sending chunk {i // chunk_size + 1}: {len(chunk)} samples")
            await websocket.send(chunk.tobytes())
            await asyncio.sleep(0.1)  # 100ms delay

        print("⏳ Waiting for transcription results...")
        await asyncio.sleep(3)

        # Cancel listener and close
        listen_task.cancel()
        await websocket.close()
        print("🔚 Connection closed")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    print("🔍 WhisperLive WebSocket Debug")
    print("=" * 40)
    await debug_whisperlive_connection()


if __name__ == "__main__":
    asyncio.run(main())
