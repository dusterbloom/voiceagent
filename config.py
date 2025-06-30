import os

# WhisperLive Configuration
WHISPER_LIVE_HOST = "localhost"
WHISPER_LIVE_PORT = 9090
WHISPER_LIVE_URL = f"ws://{WHISPER_LIVE_HOST}:{WHISPER_LIVE_PORT}"

# Ollama Configuration
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/v1"
OLLAMA_MODEL = "llama3.2:3b"

# Audio Configuration
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
CHANNELS = 1
FORMAT = "int16"

# TTS Configuration
TTS_MODEL = "piper"
TTS_VOICE = "en_US-lessac-medium"

# System Configuration
DEBUG = True
LOG_LEVEL = "INFO"
