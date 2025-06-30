#!/bin/bash
echo "Starting Voice Agent System..."
echo "Checking services..."

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama not accessible. Make sure your Ollama Docker container is running:"
    echo "   docker run -d -p 11434:11434 --name ollama ollama/ollama"
    exit 1
fi
echo "✓ Ollama is running"

# Check WhisperLive
if ! curl -s http://localhost:9091/health > /dev/null; then
    echo "❌ WhisperLive not accessible. Start it with:"
    echo "   ./start_whisperlive.sh"
    exit 1
fi
echo "✓ WhisperLive is running"

echo "Starting Voice Agent..."
python3 main.py
