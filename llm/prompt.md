Create a local AI voice assistant with ultra-low latency using Python. 

Architecture requirements:
- Event-driven with thread safety using asyncio
- Single configuration file (config.yaml)
- Single start script (start.py)
- Maximum 20 files total
- One comprehensive end-to-end test

Components to integrate:
1. Faster Whisper (base model) for STT
2. Whisper-live server/client for streaming
3. Ollama (Docker) for LLM processing
4. ChromaDB (Docker) for memory
5. Kokoro for TTS
6. Optional: Redis (Docker) for caching if truly needed

Core structure:
/voice_assistant/
  ├── config.yaml          # All configuration
  ├── start.py            # Single entry point
  ├── core/
  │   ├── __init__.py
  │   ├── audio_pipeline.py    # Audio I/O handling
  │   ├── stt_engine.py       # Whisper integration
  │   ├── llm_engine.py       # Ollama integration
  │   ├── tts_engine.py       # Kokoro integration
  │   ├── memory_store.py     # ChromaDB integration
  │   └── event_bus.py        # Central event system
  ├── utils/
  │   ├── __init__.py
  │   └── audio_utils.py
  ├── docker-compose.yml   # For Ollama, ChromaDB, Redis
  ├── requirements.txt
  └── tests/
      └── test_e2e.py    # Single end-to-end test

Key design principles:
1. Use asyncio throughout with proper event loops
2. Central event bus pattern for all component communication
3. Clean interfaces between components (abstract base classes)
4. Graceful shutdown handling
5. Comprehensive logging with clear component prefixes
6. Audio stays in numpy arrays throughout the pipeline
7. Use PyAudio for mic input and speaker output

The event flow should be:
Mic → Audio Pipeline → STT → Event Bus → LLM → Event Bus → TTS → Audio Pipeline → Speaker

Each component should:
- Subscribe to relevant events
- Process asynchronously
- Emit completion events
- Handle errors gracefully

The end-to-end test should:
- Start all services
- Simulate audio input
- Verify transcription
- Verify LLM response
- Verify TTS output
- Measure total latency

Focus on minimal latency by:
- Streaming audio in small chunks
- Processing in parallel where possible
- Pre-loading models
- Using connection pooling