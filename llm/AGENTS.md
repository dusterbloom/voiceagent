# Local Voice Agent System

## Core Agents (Local Only)

### 1. Audio Input Agent
**Purpose**: Capture and process microphone input
**Responsibilities**:
- Real-time audio capture
- Audio preprocessing and filtering
- Voice activity detection
- Audio chunking for processing

**Implementation**: Python with `pyaudio` or `sounddevice`
**Priority**: HIGH

### 2. Speech-to-Text Agent
**Purpose**: Convert speech to text locally with streaming
**Responsibilities**:
- Real-time streaming speech recognition
- Continuous transcription
- Audio format handling
- WebSocket/HTTP API interface

**Implementation**: WhisperLive (FastAPI endpoint, Docker, or Python server)
**Priority**: HIGH

### 3. LLM Agent
**Purpose**: Process text and generate responses
**Responsibilities**:
- Text understanding and processing
- Response generation
- Context management
- OpenAI API compatible interface

**Implementation**: Local LLM via Ollama with OpenAI-compatible API
**Priority**: HIGH

### 4. Text-to-Speech Agent
**Purpose**: Convert responses to speech locally
**Responsibilities**:
- Local voice synthesis
- Audio output streaming
- Voice quality control

**Implementation**: Local TTS via `piper-tts` or `coqui-tts`
**Priority**: HIGH

### 5. Audio Output Agent
**Purpose**: Play generated speech
**Responsibilities**:
- Audio playback
- Volume control
- Real-time streaming

**Implementation**: Python with `pygame` or `sounddevice`
**Priority**: HIGH

## Quick Local Setup (Same Day)

### Minimal Stack
1. **WhisperLive**: Real-time streaming STT server (FastAPI/Docker)
2. **Ollama**: Local LLM server with OpenAI-compatible API
3. **Piper TTS**: Fast local text-to-speech
4. **PyAudio**: Audio I/O handling

### Implementation Order
1. Setup WhisperLive server (Docker or Python)
2. Audio capture → WhisperLive streaming API
3. Text → Ollama (OpenAI API format)
4. Response → Piper TTS → Audio output
5. Connect pipeline with WebSocket/HTTP clients

## Local Technology Stack

### Speech Recognition
- **WhisperLive** (streaming Whisper server)
  - FastAPI endpoint option
  - Docker container option
  - Python server option

### LLM Processing
- **Ollama** (OpenAI API compatible)
- **llama.cpp** with OpenAI wrapper
- **vLLM** (if GPU available)

### Text-to-Speech
- **Piper TTS** (fast, lightweight)
- **Coqui TTS** (more voices)
- **espeak-ng** (basic fallback)

### Audio I/O
- **PyAudio** or **sounddevice**
- **pygame** for playback

## Local Pipeline Flow

```
Microphone → Audio Input → WhisperLive Server → LLM (Ollama) → Piper TTS → Audio Output → Speakers
                              ↑ (WebSocket/HTTP)
```

## Quick Start Setup

### 1. Setup WhisperLive Server
```bash
# Option A: Docker
docker run -p 9091:9091 whisper-live

# Option B: Python installation
git clone https://github.com/collabora/WhisperLive
cd WhisperLive
pip install -r requirements.txt
python run_server.py
```

### 2. Install Dependencies
```bash
pip install pyaudio sounddevice asyncio websockets aiohttp
# Install Ollama from https://ollama.ai
# Install Piper TTS
```

### 3. Setup Ollama
```bash
ollama pull llama3.2:3b  # or preferred model
ollama serve  # starts OpenAI-compatible API on localhost:11434
```

### 4. Implementation Checklist
- [ ] Setup WhisperLive server (port 9091)
- [ ] Audio capture with streaming to WhisperLive
- [ ] WebSocket/HTTP client for STT
- [ ] Ollama client with OpenAI format
- [ ] Piper TTS integration
- [ ] Audio playback system
- [ ] Async pipeline coordination
- [ ] Error handling and recovery

## Performance Targets (Local)

- **Latency**: < 2s end-to-end (local processing)
- **CPU Usage**: < 50% on modern CPU
- **Memory**: < 4GB RAM (including models)
- **Real-time**: Streaming audio processing

## File Structure
```
voiceagent/
├── agents/
│   ├── audio_input.py
│   ├── whisper_live_client.py
│   ├── llm_agent.py
│   ├── tts_agent.py
│   └── audio_output.py
├── main.py
├── config.py
├── requirements.txt
└── docker-compose.yml  # for WhisperLive server
```

## WhisperLive Integration Options

### Option 1: Docker Compose
```yaml
# docker-compose.yml
services:
  whisper-live:
    image: whisper-live
    ports:
      - "9091:9091"
```

### Option 2: FastAPI Endpoint
- WhisperLive provides REST API endpoints
- HTTP POST for audio chunks
- WebSocket for streaming

### Option 3: Python Server
- Direct integration with WhisperLive Python server
- Custom configuration options
- Better control over model parameters