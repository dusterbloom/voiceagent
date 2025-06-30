import asyncio
import subprocess
import tempfile
import os
import logging
from typing import Optional, Callable
import io
from config import TTS_MODEL, TTS_VOICE, SAMPLE_RATE

logger = logging.getLogger(__name__)


class TTSAgent:
    def __init__(
        self,
        model: str = TTS_MODEL,
        voice: str = TTS_VOICE,
        sample_rate: int = SAMPLE_RATE,
    ):
        self.model = model
        self.voice = voice
        self.sample_rate = sample_rate
        self.audio_callback: Optional[Callable] = None

    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """Set callback for generated audio"""
        self.audio_callback = callback

    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech and return audio bytes"""
        if not text.strip():
            return b""

        try:
            if self.model == "piper":
                return await self._piper_tts(text)
            elif self.model == "espeak":
                return await self._espeak_tts(text)
            else:
                logger.error(f"Unsupported TTS model: {self.model}")
                return b""

        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return b""

    async def _piper_tts(self, text: str) -> bytes:
        """Generate speech using Piper TTS"""
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Run Piper TTS command
            cmd = ["piper", "--model", self.voice, "--output_file", temp_path]

            # Run piper with text input
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(input=text.encode())

            if process.returncode != 0:
                logger.error(f"Piper TTS failed: {stderr.decode()}")
                return b""

            # Read generated audio file
            if os.path.exists(temp_path):
                with open(temp_path, "rb") as f:
                    audio_data = f.read()
                os.unlink(temp_path)  # Clean up temp file
                return audio_data
            else:
                logger.error("Piper TTS output file not found")
                return b""

        except FileNotFoundError:
            logger.error("Piper TTS not found. Please install piper-tts")
            return await self._espeak_tts(text)  # Fallback to espeak
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            return b""

    async def _espeak_tts(self, text: str) -> bytes:
        """Generate speech using espeak (fallback)"""
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Run espeak command
            cmd = [
                "espeak",
                "-w",
                temp_path,
                "-s",
                "150",  # Speed
                "-p",
                "50",  # Pitch
                "-a",
                "100",  # Amplitude
                text,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"espeak failed: {stderr.decode()}")
                return b""

            # Read generated audio file
            if os.path.exists(temp_path):
                with open(temp_path, "rb") as f:
                    audio_data = f.read()
                os.unlink(temp_path)  # Clean up temp file
                return audio_data
            else:
                logger.error("espeak output file not found")
                return b""

        except FileNotFoundError:
            logger.error("espeak not found. Please install espeak")
            return b""
        except Exception as e:
            logger.error(f"espeak error: {e}")
            return b""

    async def speak_text(self, text: str):
        """Generate speech and call audio callback"""
        audio_data = await self.text_to_speech(text)

        if audio_data and self.audio_callback:
            self.audio_callback(audio_data)
        elif not audio_data:
            logger.warning(f"No audio generated for text: {text[:50]}...")

    async def speak_text_stream(self, text_stream):
        """Handle streaming text input for TTS"""
        buffer = ""

        async for text_chunk in text_stream:
            buffer += text_chunk

            # Look for sentence endings to generate speech
            sentences = self._split_sentences(buffer)

            if len(sentences) > 1:
                # Process complete sentences
                for sentence in sentences[:-1]:
                    if sentence.strip():
                        await self.speak_text(sentence.strip())

                # Keep the last incomplete sentence in buffer
                buffer = sentences[-1]

        # Process any remaining text
        if buffer.strip():
            await self.speak_text(buffer.strip())

    def _split_sentences(self, text: str) -> list:
        """Split text into sentences for streaming TTS"""
        import re

        # Simple sentence splitting on common punctuation
        sentences = re.split(r"[.!?]+", text)
        return sentences

    async def check_tts_availability(self) -> dict:
        """Check which TTS engines are available"""
        available = {}

        # Check Piper
        try:
            process = await asyncio.create_subprocess_exec(
                "piper",
                "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            available["piper"] = process.returncode == 0
        except FileNotFoundError:
            available["piper"] = False

        # Check espeak
        try:
            process = await asyncio.create_subprocess_exec(
                "espeak",
                "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            available["espeak"] = process.returncode == 0
        except FileNotFoundError:
            available["espeak"] = False

        return available


# Alternative: Simple TTS using system commands
class SimpleTTSAgent:
    """Simplified TTS agent using system say command (macOS) or espeak (Linux)"""

    def __init__(self):
        self.audio_callback: Optional[Callable] = None

    def set_audio_callback(self, callback: Callable[[bytes], None]):
        self.audio_callback = callback

    async def speak_text(self, text: str):
        """Speak text using system TTS"""
        try:
            # Try macOS say command first
            try:
                process = await asyncio.create_subprocess_exec(
                    "say",
                    text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()
                return
            except FileNotFoundError:
                pass

            # Try espeak on Linux
            try:
                process = await asyncio.create_subprocess_exec(
                    "espeak",
                    text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()
                return
            except FileNotFoundError:
                pass

            logger.error("No TTS system found (tried 'say' and 'espeak')")

        except Exception as e:
            logger.error(f"TTS error: {e}")


# Example usage
async def main():
    logging.basicConfig(level=logging.INFO)

    agent = TTSAgent()

    # Check available TTS engines
    available = await agent.check_tts_availability()
    print(f"Available TTS engines: {available}")

    def audio_handler(audio_data: bytes):
        print(f"Generated audio: {len(audio_data)} bytes")
        # Here you would typically send to audio output agent

    agent.set_audio_callback(audio_handler)

    # Test TTS
    test_text = "Hello! This is a test of the text to speech system."
    await agent.speak_text(test_text)


if __name__ == "__main__":
    asyncio.run(main())
