#!/usr/bin/env python3
"""
Local Voice Agent System
Coordinates all agents for real-time voice conversation
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

# Import all agents
from agents.audio_input import AudioInputAgent
from agents.whisper_live_client import WhisperLiveClient
from agents.llm_agent import LLMAgent
from agents.tts_agent import TTSAgent, SimpleTTSAgent
from agents.audio_output import AudioOutputAgent

# Import configuration
from config import DEBUG, LOG_LEVEL


class VoiceAgent:
    def __init__(self):
        # Initialize all agents
        self.audio_input = AudioInputAgent()
        self.whisper_client = WhisperLiveClient()
        self.llm_agent = LLMAgent()
        self.tts_agent = TTSAgent()
        self.audio_output = AudioOutputAgent()

        # State management
        self.is_running = False
        self.is_listening = True
        self.current_transcription = ""
        self.conversation_active = False

        # Setup callbacks
        self._setup_callbacks()

    def _setup_callbacks(self):
        """Setup callbacks between agents"""
        # Audio input -> WhisperLive
        self.audio_input.set_audio_callback(self._handle_audio_input)

        # WhisperLive -> LLM
        self.whisper_client.set_transcription_callback(self._handle_transcription)

        # TTS -> Audio output
        self.tts_agent.set_audio_callback(self._handle_tts_audio)

    async def _handle_audio_input(self, audio_data: bytes):
        """Handle audio input from microphone"""
        if self.is_listening and self.whisper_client.is_connected:
            await self.whisper_client.send_audio(audio_data)

    async def _handle_transcription(self, text: str, is_final: bool):
        """Handle transcription from WhisperLive"""
        if is_final and text.strip():
            logger.info(f"User said: {text}")
            self.current_transcription = text

            # Stop listening while processing response
            self.is_listening = False

            # Generate and speak response
            await self._process_user_input(text)

            # Resume listening
            self.is_listening = True
        else:
            # Show partial transcription
            if DEBUG and text.strip():
                print(f"[Partial] {text}", end="\r")

    async def _process_user_input(self, text: str):
        """Process user input and generate response"""
        try:
            # Check for exit commands
            if text.lower().strip() in ["exit", "quit", "goodbye", "stop"]:
                await self.tts_agent.speak_text("Goodbye!")
                await asyncio.sleep(2)  # Wait for TTS to complete
                await self.shutdown()
                return

            # Generate LLM response
            logger.info("Generating response...")
            response = await self.llm_agent.generate_response(text)

            if response:
                logger.info(f"Assistant: {response}")
                # Convert to speech
                await self.tts_agent.speak_text(response)
            else:
                logger.warning("No response generated")

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            await self.tts_agent.speak_text("Sorry, I had trouble processing that.")

    async def _handle_tts_audio(self, audio_data: bytes):
        """Handle audio from TTS agent"""
        await self.audio_output.play_audio(audio_data)

    async def start(self):
        """Start the voice agent system"""
        logger.info("Starting Voice Agent System...")

        try:
            # Check system requirements
            await self._check_requirements()

            # Initialize audio output
            self.audio_output.initialize()

            # Connect to WhisperLive
            logger.info("Connecting to WhisperLive server...")
            await self.whisper_client.connect()
            await self.whisper_client.start_streaming()

            # Start audio input
            logger.info("Starting audio input...")
            self.audio_input.start_recording()

            self.is_running = True
            logger.info("Voice Agent System is ready!")

            # Welcome message
            await self.tts_agent.speak_text(
                "Hello! I'm your voice assistant. How can I help you today?"
            )

            # Keep running until shutdown
            while self.is_running:
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Failed to start voice agent: {e}")
            await self.shutdown()
            raise

    async def _check_requirements(self):
        """Check if all required services are available"""
        # Check LLM service
        if not await self.llm_agent.health_check():
            logger.error("LLM service not available. Please start Ollama server.")
            raise RuntimeError("LLM service not available")

        # Check TTS availability
        tts_available = await self.tts_agent.check_tts_availability()
        if not any(tts_available.values()):
            logger.warning("No TTS engines available, falling back to simple TTS")
            self.tts_agent = SimpleTTSAgent()
            self.tts_agent.set_audio_callback(self._handle_tts_audio)

        logger.info(f"TTS engines available: {tts_available}")

    async def shutdown(self):
        """Shutdown the voice agent system"""
        logger.info("Shutting down Voice Agent System...")

        self.is_running = False
        self.is_listening = False

        try:
            # Stop audio input
            self.audio_input.stop_recording()

            # Stop WhisperLive
            await self.whisper_client.stop_streaming()
            await self.whisper_client.disconnect()

            # Stop audio output
            self.audio_output.stop_all_audio()
            self.audio_output.cleanup()

            logger.info("Voice Agent System shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Setup logging
def setup_logging():
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("voice_agent.log"),
        ],
    )


# Global logger
logger = logging.getLogger(__name__)

# Signal handlers for graceful shutdown
voice_agent_instance: Optional[VoiceAgent] = None


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if voice_agent_instance:
        asyncio.create_task(voice_agent_instance.shutdown())


async def main():
    """Main entry point"""
    global voice_agent_instance

    setup_logging()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        voice_agent_instance = VoiceAgent()
        await voice_agent_instance.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Voice agent error: {e}")
    finally:
        if voice_agent_instance:
            await voice_agent_instance.shutdown()


if __name__ == "__main__":
    print("Local Voice Agent System")
    print("=" * 40)
    print("Make sure you have:")
    print("1. WhisperLive server running (port 9090)")
    print("2. Ollama server running (port 11434)")
    print("3. TTS engine installed (piper-tts or espeak)")
    print("4. Microphone and speakers connected")
    print("=" * 40)
    print("Starting system...")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
