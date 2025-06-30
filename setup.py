#!/usr/bin/env python3
"""
Setup script for Local Voice Agent System
"""

import subprocess
import sys
import os
import asyncio


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✓ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")

    dependencies = {
        "python3": "python3 --version",
        "pip": "pip --version",
        "docker": "docker --version",
        "git": "git --version",
    }

    missing = []
    for name, cmd in dependencies.items():
        if not run_command(cmd, f"Checking {name}"):
            missing.append(name)

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        return False

    return True


def install_python_packages():
    """Install required Python packages"""
    print("\nInstalling Python packages...")

    packages = [
        "pyaudio",
        "sounddevice",
        "websockets",
        "aiohttp",
        "requests",
        "numpy",
        "scipy",
        "pygame",
        "openai",
        "onnxruntime",
        "wave",
    ]

    for package in packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            print(f"Warning: Failed to install {package}")

    return True


def setup_whisperlive():
    """Setup WhisperLive server"""
    print("\nSetting up WhisperLive...")

    # Clone WhisperLive if not exists
    if not os.path.exists("WhisperLive"):
        if not run_command(
            "git clone https://github.com/collabora/WhisperLive.git",
            "Cloning WhisperLive repository",
        ):
            return False

    # Install WhisperLive requirements
    if os.path.exists("WhisperLive/requirements/server.txt"):
        if not run_command(
            "pip install -r WhisperLive/requirements/server.txt",
            "Installing WhisperLive requirements",
        ):
            print("Warning: Failed to install WhisperLive requirements")

    return True


def check_audio_devices():
    """Check available audio devices"""
    print("\nChecking audio devices...")

    try:
        import pyaudio

        audio = pyaudio.PyAudio()

        print("Available input devices:")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:
                print(f"  {i}: {device_info['name']}")

        print("Available output devices:")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxOutputChannels"] > 0:
                print(f"  {i}: {device_info['name']}")

        audio.terminate()
        return True

    except Exception as e:
        print(f"Error checking audio devices: {e}")
        return False


def setup_piper_tts():
    """Setup Piper TTS models"""
    print("\nSetting up Piper TTS...")

    # Create models directory
    models_dir = "models/piper"
    os.makedirs(models_dir, exist_ok=True)

    # Download Piper TTS models
    piper_models = {
        "en_US-lessac-medium.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "en_US-lessac-medium.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    }

    for filename, url in piper_models.items():
        filepath = os.path.join(models_dir, filename)
        if not os.path.exists(filepath):
            print(f"Downloading {filename}...")
            if not run_command(f"wget -O {filepath} {url}", f"Downloading {filename}"):
                print(f"Warning: Failed to download {filename}")
                print(f"You can manually download from: {url}")
        else:
            print(f"✓ {filename} already exists")

    # Try to install piper-tts package
    run_command("pip install piper-tts", "Installing piper-tts package")

    return True


def check_ollama_docker():
    """Check if Ollama is running in Docker"""
    print("\nChecking Ollama Docker container...")

    # Check if Ollama container is running
    if run_command("docker ps | grep ollama", "Checking for running Ollama container"):
        print("✓ Found running Ollama container")

        # Test API endpoint
        if run_command("curl -s http://localhost:11434/api/tags", "Testing Ollama API"):
            print("✓ Ollama API is accessible")
            return True
        else:
            print("⚠ Ollama container found but API not accessible on port 11434")
            print("Make sure Ollama container exposes port 11434")
            return False
    else:
        print("⚠ No running Ollama container found")
        print("Please start your Ollama Docker container with:")
        print("docker run -d -p 11434:11434 --name ollama ollama/ollama")
        return False


def create_start_scripts():
    """Create convenience start scripts"""
    print("\nCreating start scripts...")

    # WhisperLive start script
    whisperlive_script = """#!/bin/bash
echo "Starting WhisperLive server..."
cd WhisperLive
python run_server.py --port 9091 --backend faster_whisper
"""

    with open("start_whisperlive.sh", "w") as f:
        f.write(whisperlive_script)

    os.chmod("start_whisperlive.sh", 0o755)

    # Docker WhisperLive script
    docker_whisperlive_script = """#!/bin/bash
echo "Starting WhisperLive server with Docker..."
docker-compose up whisper-live
"""

    with open("start_whisperlive_docker.sh", "w") as f:
        f.write(docker_whisperlive_script)

    os.chmod("start_whisperlive_docker.sh", 0o755)

    # Main voice agent script
    main_script = """#!/bin/bash
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
"""

    with open("start_voice_agent.sh", "w") as f:
        f.write(main_script)

    os.chmod("start_voice_agent.sh", 0o755)

    print("✓ Created start scripts:")
    print("  - start_whisperlive.sh")
    print("  - start_whisperlive_docker.sh")
    print("  - start_voice_agent.sh")
    return True


def main():
    """Main setup function"""
    print("Local Voice Agent System Setup")
    print("=" * 40)

    # Check dependencies
    if not check_dependencies():
        print("Please install missing dependencies and run setup again.")
        return False

    # Install Python packages
    install_python_packages()

    # Check Ollama Docker
    check_ollama_docker()

    # Setup WhisperLive
    setup_whisperlive()

    # Setup Piper TTS
    setup_piper_tts()

    # Check audio devices
    check_audio_devices()

    # Create start scripts
    create_start_scripts()
    print("\n" + "=" * 40)
    print("Setup completed!")
    print("\nNext steps:")
    print("1. Make sure your Ollama Docker container is running:")
    print("   docker run -d -p 11434:11434 --name ollama ollama/ollama")
    print("   docker exec -it ollama ollama pull llama3.2:3b")
    print("2. Start WhisperLive: ./start_whisperlive.sh")
    print("3. Start Voice Agent: ./start_voice_agent.sh")
    print("\nPiper TTS models downloaded to: ./models/piper/")
    print(
        "Fallback TTS: sudo apt install espeak (Linux) or brew install espeak (macOS)"
    )

    return True


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
