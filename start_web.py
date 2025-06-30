#!/usr/bin/env python3
"""
Simple startup script for the web-based voice agent
"""

import subprocess
import sys
import time
import os
from pathlib import Path


def check_requirements():
    """Check if required packages are installed"""
    try:
        import asyncio
        from web_server import main

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Voice Agent Web Server stopped")
    except Exception as e:
        print(f"❌ Error starting web server: {e}")


if __name__ == "__main__":
    print("🎤 Voice Agent Web Interface")
    print("=" * 40)

    check_requirements()
    check_services()
    start_web_server()
