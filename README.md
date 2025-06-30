# Local Voice Agent System

A fully local voice assistant that runs entirely on your machine without cloud dependencies.

## Features

- **Real-time Speech Recognition**: WhisperLive for streaming STT
- **Local LLM**: Ollama with OpenAI-compatible API
- **Text-to-Speech**: Piper TTS or espeak fallback
- **Audio I/O**: PyAudio for microphone and speaker handling
- **Async Pipeline**: Real-time audio processing

## Architecture

```
Microphone → Audio Input → WhisperLive → LLM (Ollama) → TTS → Audio Output → Speakers
```

## Quick Start

### 1. Setup
```bash
python3 setup.py
```

### 2. Install Ollama
```bash
# Install Ollama from https://ollama.ai
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2:3b

# Start Ollama server
ollama serve
```

### 3. Start WhisperLive Server
```bash
./start_whisperlive.sh
```

### 4. Start Voice Agent
```bash
./start_voice_agent.sh
```

## Manual Setup

### Dependencies
```bash
pip install -r requirements.txt
```

### WhisperLive Setup
```bash
git clone https://github.com/collabora/WhisperLive.git
cd WhisperLive
pip install -r requirements/server.txt
python run_server.py --host 0.0.0.0 --port 9090
```

### TTS Setup (Optional)
```bash
# Option 1: Piper TTS (recommended)
# Follow installation instructions at: https://github.com/rhasspy/piper

# Option 2: espeak (fallback)
sudo apt install espeak  # Linux
brew install espeak      # macOS
```

## Configuration

Edit `config.py` to customize:

- **WhisperLive**: Host, port, model settings
- **Ollama**: Model selection, API endpoint
- **Audio**: Sample rate, chunk size, VAD threshold
- **TTS**: Voice selection, engine preference

## Usage

1. Start all services (Ollama, WhisperLive)
2. Run `python3 main.py`
3. Speak into your microphone
4. The assistant will respond with voice

### Voice Commands
- "exit", "quit", "goodbye", "stop" - Shutdown the system

## Troubleshooting

### WhisperLive Connection Issues
```bash
# Check if server is running
curl http://localhost:9090/health

# Check logs
tail -f WhisperLive/logs/server.log
```

### Ollama Issues
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check available models
ollama list
```

### Audio Issues
```bash
# Test audio devices
python3 -c "from agents.audio_input import AudioInputAgent; agent = AudioInputAgent(); print(agent.get_audio_devices())"

# Test audio output
python3 agents/audio_output.py
```

### TTS Issues
```bash
# Check available TTS engines
python3 agents/tts_agent.py
```

## File Structure

```
voiceagent/
├── agents/
│   ├── audio_input.py          # Microphone capture
│   ├── whisper_live_client.py  # STT client
│   ├── llm_agent.py           # LLM processing
│   ├── tts_agent.py           # Text-to-speech
│   └── audio_output.py        # Speaker output
├── main.py                    # Main coordinator
├── config.py                  # Configuration
├── setup.py                   # Setup script
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # WhisperLive container
└── README.md                  # This file
```

## Performance

- **Latency**: < 2s end-to-end (local processing)
- **CPU Usage**: < 50% on modern CPU
- **Memory**: < 4GB RAM (including models)
- **Real-time**: Streaming audio processing

## Models

### Recommended Models

**LLM (Ollama)**:
- `llama3.2:3b` - Fast, good quality
- `llama3.2:1b` - Fastest, basic quality
- `qwen2.5:3b` - Alternative option

**STT (WhisperLive)**:
- `base` - Good balance of speed/accuracy
- `small` - Faster, less accurate
- `medium` - Better accuracy, slower

**TTS**:
- Piper: `en_US-lessac-medium` - Natural voice
- espeak: Built-in voices

## Development

### Adding New Agents
1. Create agent class in `agents/`
2. Implement required methods
3. Add to main pipeline in `main.py`
4. Update configuration in `config.py`

### Testing Individual Agents
Each agent can be tested independently:
```bash
python3 agents/audio_input.py
python3 agents/whisper_live_client.py
python3 agents/llm_agent.py
python3 agents/tts_agent.py
python3 agents/audio_output.py
```

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request