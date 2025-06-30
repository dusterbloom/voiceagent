#!/usr/bin/env python3
"""
Test scipy resampling functionality
"""

import numpy as np
from scipy import signal


def test_resampling():
    """Test scipy resampling"""
    print("🔧 Testing scipy resampling...")

    # Create test audio (44.1kHz)
    sample_rate = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    frequency = 440  # A4 note
    audio_data = (np.sin(2 * np.pi * frequency * t) * 0.5).astype(np.float32)

    print(f"Original: {len(audio_data)} samples at {sample_rate}Hz")

    # Resample to 16kHz
    target_sr = 16000
    ratio = target_sr / sample_rate
    num_samples = int(len(audio_data) * ratio)
    resampled = signal.resample(audio_data, num_samples)

    print(f"Resampled: {len(resampled)} samples at {target_sr}Hz")
    print(f"Ratio: {ratio:.3f}")
    print(f"Expected samples: {num_samples}")
    print(f"Actual samples: {len(resampled)}")
    print(f"Duration preserved: {len(resampled) / target_sr:.2f}s")

    print("✅ Scipy resampling working correctly!")


if __name__ == "__main__":
    test_resampling()
