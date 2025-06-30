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


def create_start_scripts():
    """Create convenience start scripts"""
    print("\nCreating start scripts...")

    # WhisperLive start script
    whisperlive_script = """#!/bin/bash
echo "Starting WhisperLive server..."
cd WhisperLive
python run_server.py --host 0.0.0.0 --port 9090
"""

    with open("start_whisperlive.sh", "w") as f:
        f.write(whisperlive_script)

    os.chmod("start_whisperlive.sh", 0o755)

    # Main voice agent script
    main_script = """#!/bin/bash
echo "Starting Voice Agent System..."
echo "Make sure WhisperLive and Ollama are running!"
python3 main.py
"""

    with open("start_voice_agent.sh", "w") as f:
        f.write(main_script)

    os.chmod("start_voice_agent.sh", 0o755)

    print("✓ Created start_whisperlive.sh and start_voice_agent.sh")
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

    # Setup WhisperLive
    setup_whisperlive()

    # Check audio devices
    check_audio_devices()

    # Create start scripts
    create_start_scripts()

    print("\n" + "=" * 40)
    print("Setup completed!")
    print("\nNext steps:")
    print("1. Install Ollama: https://ollama.ai")
    print("2. Run: ollama pull llama3.2:3b")
    print("3. Start Ollama: ollama serve")
    print("4. Start WhisperLive: ./start_whisperlive.sh")
    print("5. Start Voice Agent: ./start_voice_agent.sh")
    print("\nOptional TTS setup:")
    print("- Install piper-tts for better voice quality")
    print("- Or use espeak: sudo apt install espeak")

    return True


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
