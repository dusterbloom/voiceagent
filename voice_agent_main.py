"""
Main Voice Agent - Integrates STT + LLM + TTS
Clean, unified voice conversation system
"""

import logging
import time
from components import STTComponent, LLMComponent, TTSComponent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceAgent:
    """Main voice agent that coordinates STT, LLM, and TTS"""

    def __init__(self):
        # Initialize components
        self.stt = STTComponent()
        self.llm = LLMComponent()
        self.tts = TTSComponent()

        # State
        self.is_active = False
        self.conversation_active = False
        self.last_user_input = ""
        self.last_ai_response = ""

        # Settings
        self.vad_sensitivity = "medium"
        self.system_prompt = (
            "You are a helpful AI assistant. Keep responses concise and conversational."
        )

        # Set up STT callback
        self.stt.set_transcription_callback(self._on_speech_detected)

    def check_all_services(self):
        """Check if all required services are running"""
        status = {}
        status["stt"] = self.stt.check_server()
        status["llm"] = self.llm.check_server()
        status["tts"] = self.tts.check_piper() and self.tts.check_model()

        all_ready = all(status.values())
        return all_ready, status

    def start_conversation(self, vad_sensitivity="medium", system_prompt=None):
        """Start voice conversation"""
        if self.conversation_active:
            return False, "Conversation already active"

        # Check services
        all_ready, status = self.check_all_services()
        if not all_ready:
            missing = [service for service, ready in status.items() if not ready]
            return False, f"Services not ready: {', '.join(missing)}"

        # Set parameters
        self.vad_sensitivity = vad_sensitivity
        if system_prompt:
            self.system_prompt = system_prompt

        # Start STT
        success, message = self.stt.start_streaming(vad_sensitivity)
        if not success:
            return False, f"STT failed: {message}"

        self.conversation_active = True
        logger.info("Voice conversation started")
        return True, "Voice conversation active"

    def stop_conversation(self):
        """Stop voice conversation"""
        if not self.conversation_active:
            return False, "No active conversation"

        # Stop components
        self.stt.stop_streaming()
        self.tts.stop_speaking()

        self.conversation_active = False
        logger.info("Voice conversation stopped")
        return True, "Conversation stopped"

    def _on_speech_detected(self, text, segments):
        """Callback when speech is detected and transcribed"""
        if not self.conversation_active:
            return

        # Filter out very short or repetitive text
        if len(text.strip()) < 3 or text == self.last_user_input:
            return

        self.last_user_input = text
        logger.info(f"User said: {text}")

        # Generate AI response
        self._generate_and_speak_response(text)

    def _generate_and_speak_response(self, user_input):
        """Generate LLM response and speak it"""
        try:
            # Generate response
            logger.info("Generating AI response...")
            ai_response = self.llm.generate_response(
                user_input, system_prompt=self.system_prompt
            )

            if ai_response and not ai_response.startswith("Error:"):
                self.last_ai_response = ai_response
                logger.info(f"AI response: {ai_response}")

                # Speak response
                success, message = self.tts.speak_text(ai_response, blocking=False)
                if not success:
                    logger.error(f"TTS failed: {message}")
            else:
                logger.error(f"LLM failed: {ai_response}")

        except Exception as e:
            logger.error(f"Response generation error: {e}")

    def send_text_message(self, text):
        """Send text message (for testing without STT)"""
        if not self.conversation_active:
            return False, "Conversation not active"

        self._generate_and_speak_response(text)
        return True, "Message sent"

    def get_conversation_status(self):
        """Get current conversation status"""
        return {
            "active": self.conversation_active,
            "stt_streaming": self.stt.is_streaming,
            "tts_speaking": self.tts.is_currently_speaking(),
            "last_user_input": self.last_user_input,
            "last_ai_response": self.last_ai_response,
            "conversation_length": self.llm.get_conversation_length(),
        }

    def clear_conversation(self):
        """Clear conversation history"""
        self.llm.clear_conversation()
        self.last_user_input = ""
        self.last_ai_response = ""
        return True, "Conversation cleared"

    def set_system_prompt(self, prompt):
        """Set system prompt for AI"""
        self.system_prompt = prompt
        return True, "System prompt updated"

    def set_vad_sensitivity(self, sensitivity):
        """Set VAD sensitivity (requires restart)"""
        self.vad_sensitivity = sensitivity
        return (
            True,
            f"VAD sensitivity set to {sensitivity} (restart conversation to apply)",
        )


if __name__ == "__main__":
    # Simple test
    agent = VoiceAgent()

    print("🤖 Voice Agent Test")
    print("Checking services...")

    all_ready, status = agent.check_all_services()
    for service, ready in status.items():
        print(f"  {service.upper()}: {'✅' if ready else '❌'}")

    if all_ready:
        print("\n✅ All services ready!")
        print("Starting conversation...")
        success, message = agent.start_conversation()
        print(f"Status: {message}")

        if success:
            print("\n🎤 Speak into your microphone...")
            print("Press Ctrl+C to stop")

            try:
                while True:
                    time.sleep(1)
                    status = agent.get_conversation_status()
                    if status["last_user_input"]:
                        print(f"Last heard: {status['last_user_input']}")
                    if status["last_ai_response"]:
                        print(f"Last response: {status['last_ai_response']}")
            except KeyboardInterrupt:
                print("\nStopping conversation...")
                agent.stop_conversation()
    else:
        print("\n❌ Some services not ready. Please check:")
        if not status["stt"]:
            print(
                "  - Start WhisperLive: python WhisperLive/run_server.py --port 9091 --backend faster_whisper"
            )
        if not status["llm"]:
            print("  - Start Ollama: ollama serve")
        if not status["tts"]:
            print("  - Install Piper and check model path")
