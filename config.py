import os

# WhisperLive Configuration
WHISPER_LIVE_HOST = "localhost"
WHISPER_LIVE_PORT = 9091
WHISPER_LIVE_URL = f"ws://{WHISPER_LIVE_HOST}:{WHISPER_LIVE_PORT}"

# Ollama Configuration (Docker)
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434  # Default Ollama Docker port
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/v1"
OLLAMA_MODEL = "llama3.2:3b"  # Change to your preferred model

# Audio Configuration
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
CHANNELS = 1
FORMAT = "int16"

# Piper TTS Configuration
TTS_MODEL = "piper"
PIPER_MODEL_PATH = "./models/piper"
PIPER_VOICE = "en_US-lessac-medium.onnx"
PIPER_CONFIG = "en_US-lessac-medium.onnx.json"
TTS_VOICE = "en_US-lessac-medium"

# System Configuration
DEBUG = True
LOG_LEVEL = "INFO"
