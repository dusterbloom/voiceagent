# Voice Agent Web Interface

A simple web frontend for your voice agent system that works in any modern browser.

## 🚀 Quick Start

1. **Start required services:**
   ```bash
   # WhisperLive STT server
   python -m whisper_live.server --port 9091
   
   # Ollama LLM server (in Docker)
   docker run -d -p 11434:11434 ollama/ollama
   ```

2. **Start the web server:**
   ```bash
   python start_web.py
   ```

3. **Open the frontend:**
   - Open `frontend/index.html` in your browser
   - Or visit: `file:///path/to/voiceagent/frontend/index.html`

## 🎯 How It Works

### Frontend (`frontend/`)
- **index.html** - Clean, responsive web interface
- **script.js** - Handles microphone access, audio recording, WebSocket communication

### Backend (`web_server.py`)
- WebSocket server on `ws://localhost:8765`
- Bridges web frontend with your existing voice agent components
- Processes audio through WhisperLive → Ollama → Piper pipeline

## 🔧 Features

- ✅ **Browser microphone access** - Works on Windows, Mac, Linux
- ✅ **Real-time audio recording** - High-quality 16kHz mono audio
- ✅ **Live conversation display** - See transcriptions and responses
- ✅ **Audio playback** - Hear TTS responses directly in browser
- ✅ **WebSocket communication** - Fast, real-time data exchange
- ✅ **Responsive design** - Works on desktop and mobile

## 🎤 Usage

1. Click "Start Recording" to begin speaking
2. Click "Stop Recording" when finished
3. Watch as your speech is:
   - Transcribed by WhisperLive
   - Processed by Ollama LLM
   - Converted to speech by Piper TTS
   - Played back in the browser

## 🔍 Troubleshooting

### Microphone Issues
- Browser will ask for microphone permission
- Make sure microphone is not muted
- Check browser console for errors

### Connection Issues
- Ensure web server is running on port 8765
- Check that WhisperLive (9091) and Ollama (11434) are running
- Look for WebSocket connection status in browser

### Audio Issues
- Browser must support WebRTC audio recording
- FFmpeg required for audio format conversion
- Check browser console for audio playback errors

## 🌐 Browser Compatibility

- ✅ Chrome/Chromium (recommended)
- ✅ Firefox
- ✅ Safari (macOS)
- ✅ Edge

## 🔒 Security Notes

- Microphone access requires HTTPS in production
- For local development, `file://` protocol works fine
- WebSocket server runs on localhost only by default

## 📁 File Structure

```
voiceagent/
├── frontend/
│   ├── index.html          # Web interface
│   └── script.js           # Frontend logic
├── web_server.py           # WebSocket backend
├── start_web.py            # Easy startup script
└── README_WEB.md           # This file
```

This web interface solves the WSL audio issues by using the browser's native microphone access!