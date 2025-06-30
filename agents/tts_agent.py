import asyncio
import subprocess
import tempfile
import os
import logging
import json
import wave
import numpy as np
from typing import Optional, Callable
import io
from config import (
    TTS_MODEL,
    TTS_VOICE,
    SAMPLE_RATE,
    PIPER_MODEL_PATH,
    PIPER_VOICE,
    PIPER_CONFIG,
)

try:
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

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
            # Skip ONNX for now due to model complexity, use CLI directly
            return await self._piper_cli_tts(text)

        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            return await self._espeak_tts(text)  # Fallback to espeak

    async def _piper_onnx_tts(self, text: str) -> bytes:
        """Generate speech using Piper ONNX model directly"""
        try:
            model_path = os.path.join(PIPER_MODEL_PATH, PIPER_VOICE)
            config_path = os.path.join(PIPER_MODEL_PATH, PIPER_CONFIG)

            if not os.path.exists(model_path) or not os.path.exists(config_path):
                logger.warning(f"Piper model files not found at {PIPER_MODEL_PATH}")
                return await self._piper_cli_tts(text)

            # Load model configuration
            with open(config_path, "r") as f:
                config = json.load(f)

            # Create ONNX session
            session = ort.InferenceSession(model_path)

            # Text preprocessing (simplified)
            # In a full implementation, you'd need proper phonemization
            text_ids = self._text_to_ids(text, config)

            # Run inference
            audio = session.run(None, {"input": text_ids})[0]

            # Convert to WAV format
            return self._audio_to_wav(
                audio, config.get("audio", {}).get("sample_rate", 22050)
            )

        except Exception as e:
            logger.error(f"Piper ONNX TTS error: {e}")
            return await self._piper_cli_tts(text)

    async def _piper_cli_tts(self, text: str) -> bytes:
        """Generate speech using Piper CLI"""
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Try different piper command variations
            piper_commands = [
                [
                    "piper",
                    "--model",
                    os.path.join(PIPER_MODEL_PATH, PIPER_VOICE),
                    "--output_file",
                    temp_path,
                ],
                [
                    "python",
                    "-m",
                    "piper",
                    "--model",
                    os.path.join(PIPER_MODEL_PATH, PIPER_VOICE),
                    "--output_file",
                    temp_path,
                ],
                ["piper", "--model", self.voice, "--output_file", temp_path],
            ]

            for cmd in piper_commands:
                try:
                    # Run piper with text input
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await process.communicate(input=text.encode())

                    if process.returncode == 0:
                        # Read generated audio file
                        if os.path.exists(temp_path):
                            with open(temp_path, "rb") as f:
                                audio_data = f.read()
                            os.unlink(temp_path)  # Clean up temp file
                            return audio_data
                    else:
                        logger.debug(
                            f"Piper command failed: {' '.join(cmd)}, error: {stderr.decode()}"
                        )

                except FileNotFoundError:
                    continue

            logger.error("All Piper TTS commands failed")
            return b""

        except Exception as e:
            logger.error(f"Piper CLI TTS error: {e}")
            return b""

    def _text_to_ids(self, text: str, config: dict) -> np.ndarray:
        """Convert text to phoneme IDs (simplified)"""
        # This is a very basic implementation
        # A full implementation would use proper phonemization
        char_to_id = config.get("phoneme_id_map", {})
        ids = []
        for char in text.lower():
            if char in char_to_id:
                ids.append(char_to_id[char])
            elif char == " ":
                ids.append(0)  # Space token
        return np.array([ids], dtype=np.int64)

    def _audio_to_wav(self, audio: np.ndarray, sample_rate: int) -> bytes:
        """Convert audio array to WAV bytes"""
        # Normalize audio
        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)

        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        return wav_buffer.getvalue()
        # except FileNotFoundError:
        #     logger.error("Piper TTS not found. Please install piper-tts")
        #     return await self._espeak_tts(text)  # Fallback to espeak
        # except Exception as e:
        #     logger.error(f"Piper TTS error: {e}")
        #     return b""

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

        # Check Piper ONNX models
        piper_onnx_available = (
            ONNX_AVAILABLE
            and os.path.exists(os.path.join(PIPER_MODEL_PATH, PIPER_VOICE))
            and os.path.exists(os.path.join(PIPER_MODEL_PATH, PIPER_CONFIG))
        )
        available["piper_onnx"] = piper_onnx_available

        # Check Piper CLI
        piper_cli_commands = ["piper", "python -m piper"]
        piper_cli_available = False

        for cmd in piper_cli_commands:
            try:
                process = await asyncio.create_subprocess_shell(
                    f"{cmd} --help",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()
                if process.returncode == 0:
                    piper_cli_available = True
                    break
            except:
                continue

        available["piper_cli"] = piper_cli_available
        available["piper"] = piper_onnx_available or piper_cli_available

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
