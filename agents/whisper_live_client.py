import asyncio
import websockets
import json
import base64
import logging
import uuid
import numpy as np
from typing import Callable, Optional
from config import WHISPER_LIVE_HOST, WHISPER_LIVE_PORT, SAMPLE_RATE

logger = logging.getLogger(__name__)


class WhisperLiveClient:
    def __init__(
        self,
        host: str = WHISPER_LIVE_HOST,
        port: int = WHISPER_LIVE_PORT,
        sample_rate: int = SAMPLE_RATE,
        language: str = "en",
        model: str = "base",
    ):
        self.host = host
        self.port = port
        self.server_url = f"ws://{host}:{port}"
        self.sample_rate = sample_rate
        self.language = language
        self.model = model
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.transcription_callback: Optional[Callable] = None
        self.uid = str(uuid.uuid4())
        self.waiting = False

    def set_transcription_callback(self, callback: Callable[[str, bool], None]):
        """Set callback for transcription results
        Args:
            callback: Function that takes (text, is_final) parameters
        """
        self.transcription_callback = callback

    async def connect(self):
        """Connect to WhisperLive server"""
        try:
            # Connect to WhisperLive server
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            logger.info(f"Connected to WhisperLive server at {self.server_url}")

            # Send initial configuration message matching WhisperLive protocol
            config_message = {
                "uid": self.uid,
                "language": self.language,
                "task": "transcribe",
                "model": self.model,
                "use_vad": True,
                "save_output_recording": False,
                "log_transcription": True,
            }
            await self.websocket.send(json.dumps(config_message))

            # Start listening for responses
            asyncio.create_task(self._listen_for_responses())

        except Exception as e:
            logger.error(f"Failed to connect to WhisperLive server: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """Disconnect from WhisperLive server"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.close()
                self.is_connected = False
                logger.info("Disconnected from WhisperLive server")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

    async def send_audio(self, audio_data: bytes):
        """Send audio data to WhisperLive server"""
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to server")
            return

        if self.waiting:
            logger.debug("Server is busy, skipping audio chunk")
            return

        try:
            # WhisperLive expects binary WebSocket frames
            # Convert to numpy array and ensure correct format
            audio_np = np.frombuffer(audio_data, dtype=np.int16)

            # Convert to float32 and normalize to [-1, 1] range
            audio_float = audio_np.astype(np.float32) / 32768.0

            # Send as binary data (not text)
            await self.websocket.send(audio_float.tobytes())

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed during audio send")
            self.is_connected = False
        except Exception as e:
            if "received 1000" in str(e):
                logger.debug("WebSocket closed normally")
                self.is_connected = False
            else:
                logger.error(f"Error sending audio: {e}")

    async def _listen_for_responses(self):
        """Listen for transcription responses from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_response(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse server response: {e}")
                    logger.debug(f"Raw message: {message}")
                except Exception as e:
                    logger.error(f"Error handling response: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in response listener: {e}")
            self.is_connected = False

    async def _handle_response(self, data: dict):
        """Handle different types of responses from server"""
        # Handle WhisperLive response format
        if "status" in data:
            status = data.get("status")

            if status == "WAIT":
                self.waiting = True
                wait_time = data.get("message", 0)
                logger.info(f"Server busy, waiting {wait_time:.1f} minutes")

            elif status == "CONNECTED":
                self.waiting = False
                logger.info("Connected to WhisperLive server")

        # Handle transcription results
        if "message" in data and isinstance(data["message"], str):
            text = data["message"].strip()
            if text and self.transcription_callback:
                # Assume final transcription for now
                self.transcription_callback(text, True)

        # Handle segments (more detailed transcription)
        if "segments" in data:
            segments = data["segments"]
            for segment in segments:
                if "text" in segment:
                    text = segment["text"].strip()
                    if text and self.transcription_callback:
                        # Check if this is a final segment
                        is_final = segment.get("end", 0) > 0
                        self.transcription_callback(text, is_final)

        # Handle uid confirmation
        if "uid" in data and data["uid"] == self.uid:
            logger.debug(f"Received confirmation for UID: {self.uid}")

    async def start_streaming(self):
        """Start streaming session"""
        if not self.is_connected:
            await self.connect()
        logger.info("Streaming started")

    async def stop_streaming(self):
        """Stop streaming session"""
        if self.is_connected and self.websocket:
            # Send end of audio signal
            await self.websocket.send("END_OF_AUDIO")
            logger.info("Streaming stopped")


# Alternative HTTP client for non-streaming use
import aiohttp


class WhisperLiveHTTPClient:
    def __init__(
        self,
        server_host: str = "localhost",
        server_port: int = 9090,
        language: str = "en",
    ):
        self.base_url = f"http://{server_host}:{server_port}"
        self.language = language

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using HTTP endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare form data
                data = aiohttp.FormData()
                data.add_field("audio", audio_data, content_type="audio/wav")
                data.add_field("language", self.language)

                async with session.post(
                    f"{self.base_url}/transcribe", data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("text", "")
                    else:
                        logger.error(f"HTTP transcription failed: {response.status}")
                        return ""

        except Exception as e:
            logger.error(f"HTTP transcription error: {e}")
            return ""


# Example usage
async def main():
    logging.basicConfig(level=logging.INFO)

    def transcription_handler(text: str, is_final: bool):
        status = "FINAL" if is_final else "PARTIAL"
        print(f"[{status}] {text}")

    client = WhisperLiveClient()
    client.set_transcription_callback(transcription_handler)

    try:
        await client.connect()
        await client.start_streaming()

        # Simulate sending audio for 10 seconds
        await asyncio.sleep(10)

        await client.stop_streaming()

    except Exception as e:
        logger.error(f"Client error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
