#!/usr/bin/env python3
"""
Docker service checker for Voice Agent System
"""

import subprocess
import requests
import json
import sys


def check_docker():
    """Check if Docker is running"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Docker is available")
            return True
        else:
            print("❌ Docker not found")
            return False
    except FileNotFoundError:
        print("❌ Docker not installed")
        return False


def check_ollama_container():
    """Check Ollama Docker container"""
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=ollama", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )

        if "ollama" in result.stdout:
            print("✓ Ollama container is running")

            # Test API
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    print(f"✓ Ollama API accessible with {len(models)} models")
                    for model in models:
                        print(f"  - {model['name']}")
                    return True
                else:
                    print("❌ Ollama API not responding correctly")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"❌ Cannot connect to Ollama API: {e}")
                return False
        else:
            print("❌ Ollama container not running")
            print(
                "Start with: docker run -d -p 11434:11434 --name ollama ollama/ollama"
            )
            return False

    except Exception as e:
        print(f"❌ Error checking Ollama container: {e}")
        return False


def check_whisperlive():
    """Check WhisperLive service"""
    try:
        response = requests.get("http://localhost:9091/health", timeout=5)
        if response.status_code == 200:
            print("✓ WhisperLive is running")
            return True
        else:
            print("❌ WhisperLive not responding")
            return False
    except requests.exceptions.RequestException:
        print("❌ WhisperLive not accessible on port 9091")
        print("Start with: ./start_whisperlive.sh")
        return False


def main():
    """Main check function"""
    print("Voice Agent System - Service Check")
    print("=" * 40)

    all_good = True

    # Check Docker
    if not check_docker():
        all_good = False

    # Check Ollama
    if not check_ollama_container():
        all_good = False

    # Check WhisperLive
    if not check_whisperlive():
        all_good = False

    print("=" * 40)
    if all_good:
        print("✓ All services are ready!")
        print("You can start the voice agent with: python3 main.py")
    else:
        print("❌ Some services need attention")
        print("Fix the issues above before starting the voice agent")

    return all_good


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
