import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Optional, AsyncGenerator
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


class LLMAgent:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        system_prompt: str = None,
    ):
        self.base_url = base_url
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return """You are a helpful voice assistant. Respond naturally and conversationally. 
Keep your responses concise but informative. You are designed to have spoken conversations, 
so avoid using formatting like bullet points or numbered lists unless specifically requested."""

    async def _make_request(
        self, messages: List[Dict[str, str]], stream: bool = False
    ) -> Dict:
        """Make request to Ollama OpenAI-compatible API"""
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": 150,  # Keep responses concise for voice
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                ) as response:
                    if response.status == 200:
                        if stream:
                            return response
                        else:
                            return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"LLM API error {response.status}: {error_text}")
                        return {"error": f"API error: {response.status}"}

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return {"error": str(e)}

    async def generate_response(self, user_input: str) -> str:
        """Generate response to user input"""
        # Add user message to conversation
        self.conversation_history.append({"role": "user", "content": user_input})

        # Prepare messages with system prompt
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history (keep last 10 exchanges to manage context)
        recent_history = self.conversation_history[-20:]  # Last 10 exchanges
        messages.extend(recent_history)

        # Make request
        response = await self._make_request(messages)

        if "error" in response:
            error_msg = (
                f"Sorry, I'm having trouble processing that. {response['error']}"
            )
            logger.error(f"LLM error: {response['error']}")
            return error_msg

        try:
            assistant_response = response["choices"][0]["message"]["content"]

            # Add assistant response to conversation history
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_response}
            )

            return assistant_response.strip()

        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response format: {e}")
            return "Sorry, I didn't understand that. Could you try again?"

    async def generate_response_stream(
        self, user_input: str
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response to user input"""
        # Add user message to conversation
        self.conversation_history.append({"role": "user", "content": user_input})

        # Prepare messages
        messages = [{"role": "system", "content": self.system_prompt}]
        recent_history = self.conversation_history[-20:]
        messages.extend(recent_history)

        # Make streaming request
        response = await self._make_request(messages, stream=True)

        if isinstance(response, dict) and "error" in response:
            yield f"Sorry, I'm having trouble processing that. {response['error']}"
            return

        full_response = ""
        try:
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            full_response += content
                            yield content

                    except json.JSONDecodeError:
                        continue

            # Add complete response to history
            if full_response:
                self.conversation_history.append(
                    {"role": "assistant", "content": full_response}
                )

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield "Sorry, there was an error processing your request."

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def set_system_prompt(self, prompt: str):
        """Update system prompt"""
        self.system_prompt = prompt
        logger.info("System prompt updated")

    async def health_check(self) -> bool:
        """Check if LLM service is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/models") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Example usage
async def main():
    logging.basicConfig(level=logging.INFO)

    agent = LLMAgent()

    # Check if service is available
    if not await agent.health_check():
        print("LLM service not available. Make sure Ollama is running.")
        return

    print("Voice Assistant Ready! (type 'quit' to exit)")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        # Non-streaming response
        response = await agent.generate_response(user_input)
        print(f"Assistant: {response}")

        # Uncomment for streaming response
        # print("Assistant: ", end="", flush=True)
        # async for chunk in agent.generate_response_stream(user_input):
        #     print(chunk, end="", flush=True)
        # print()


if __name__ == "__main__":
    asyncio.run(main())
