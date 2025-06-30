"""
LLM Component using Ollama
Clean, reusable LLM functionality
"""

import requests
import logging
import json

logger = logging.getLogger(__name__)


class LLMComponent:
    """Clean LLM component using Ollama"""

    def __init__(self, host="localhost", port=11434, model="llama3.2"):
        self.host = host
        self.port = port
        self.model = model
        self.base_url = f"http://{host}:{port}"
        self.conversation_history = []

    def check_server(self):
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self):
        """List available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def set_model(self, model_name):
        """Set the model to use"""
        self.model = model_name
        logger.info(f"LLM model set to: {model_name}")

    def generate_response(self, user_input, system_prompt=None, stream=False):
        """Generate response from LLM"""
        try:
            # Build messages
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add conversation history
            messages.extend(self.conversation_history)

            # Add current user input
            messages.append({"role": "user", "content": user_input})

            # Prepare request
            payload = {"model": self.model, "messages": messages, "stream": stream}

            response = requests.post(
                f"{self.base_url}/api/chat", json=payload, timeout=30
            )

            if response.status_code == 200:
                if stream:
                    # Handle streaming response
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    content = data["message"]["content"]
                                    full_response += content
                                    yield content
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue

                    # Add to conversation history
                    self.conversation_history.append(
                        {"role": "user", "content": user_input}
                    )
                    self.conversation_history.append(
                        {"role": "assistant", "content": full_response}
                    )

                else:
                    # Handle non-streaming response
                    data = response.json()
                    assistant_response = data["message"]["content"]

                    # Add to conversation history
                    self.conversation_history.append(
                        {"role": "user", "content": user_input}
                    )
                    self.conversation_history.append(
                        {"role": "assistant", "content": assistant_response}
                    )

                    return assistant_response
            else:
                error_msg = f"LLM request failed: {response.status_code}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"LLM error: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_conversation_length(self):
        """Get number of messages in conversation"""
        return len(self.conversation_history)

    def set_conversation_limit(self, max_messages=20):
        """Limit conversation history to prevent context overflow"""
        if len(self.conversation_history) > max_messages:
            # Keep system message if present, then recent messages
            self.conversation_history = self.conversation_history[-max_messages:]
            logger.info(f"Conversation history trimmed to {max_messages} messages")
