import asyncio
import websockets
import json
import base64
import logging
from typing import Callable, Optional
from config import WHISPER_LIVE_URL, SAMPLE_RATE

logger = logging.getLogger(__name__)


class WhisperLiveClient:
    def __init__(
        self,
        server_url: str = WHISPER_LIVE_URL,
        sample_rate: int = SAMPLE_RATE,
        language: str = "en",
    ):
        self.server_url = server_url
        self.sample_rate = sample_rate
        self.language = language
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.transcription_callback: Optional[Callable] = None
        self.session_id = None

    def set_transcription_callback(self, callback: Callable[[str, bool], None]):
        """Set callback for transcription results
        Args:
            callback: Function that takes (text, is_final) parameters
        """
        self.transcription_callback = callback

    async def connect(self):
        """Connect to WhisperLive server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            logger.info(f"Connected to WhisperLive server at {self.server_url}")

            # Send initial configuration
            config_message = {
                "type": "config",
                "data": {
                    "sample_rate": self.sample_rate,
                    "language": self.language,
                    "task": "transcribe",
                },
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

        try:
            # Encode audio data as base64
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")

            message = {
                "type": "audio",
                "data": {"audio": audio_b64, "sample_rate": self.sample_rate},
            }

            await self.websocket.send(json.dumps(message))

        except Exception as e:
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
        response_type = data.get("type")

        if response_type == "transcription":
            text = data.get("data", {}).get("text", "")
            is_final = data.get("data", {}).get("is_final", False)

            if text and self.transcription_callback:
                self.transcription_callback(text, is_final)

        elif response_type == "error":
            error_msg = data.get("data", {}).get("message", "Unknown error")
            logger.error(f"Server error: {error_msg}")

        elif response_type == "session":
            self.session_id = data.get("data", {}).get("session_id")
            logger.info(f"Session started: {self.session_id}")

        else:
            logger.debug(f"Unknown response type: {response_type}")

    async def start_streaming(self):
        """Start streaming session"""
        if not self.is_connected:
            await self.connect()

        start_message = {"type": "start", "data": {}}
        await self.websocket.send(json.dumps(start_message))

    async def stop_streaming(self):
        """Stop streaming session"""
        if self.is_connected and self.websocket:
            stop_message = {"type": "stop", "data": {}}
            await self.websocket.send(json.dumps(stop_message))


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
