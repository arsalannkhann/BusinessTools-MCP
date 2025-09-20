#!/usr/bin/env python3
"""
Local testing script for Gemini TTS Interface
Run this to test the interface before AWS deployment
"""

import asyncio
import os
import sys
import wave
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

async def test_gemini_tts_interface():
    """Test the TTS interface locally"""
    print("🧪 Testing Gemini TTS Interface Locally")
    print("=" * 50)

    # Check environment variables
    required_env_vars = [
        "GEMINI_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS"  # For Google Cloud Speech/TTS
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Set these variables before testing:")
        print("   export GEMINI_API_KEY='your-api-key'")
        print("   export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'")
        return False

    try:
        # Import and initialize the interface
        from gemini_tts_interface import GeminiTTSInterface

        print("✅ Imports successful")

        # Create interface instance
        interface = GeminiTTSInterface()
        print("✅ Interface initialized")

        # Test text-to-speech
        print("\n🔊 Testing Text-to-Speech...")
        test_text = "Hello! I'm your AI assistant. How can I help you today?"
        audio_url = await interface.text_to_speech(test_text)

        if audio_url:
            print(f"✅ TTS successful: {audio_url}")
        else:
            print("❌ TTS failed")
            return False

        # Test Gemini processing
        print("\n🤖 Testing Gemini AI processing...")
        test_input = "What can you help me with?"
        response = await interface.process_text_with_mcp(test_input)

        if response:
            print(f"✅ Gemini response: {response[:100]}...")
        else:
            print("❌ Gemini processing failed")
            return False

        print("\n🎉 All tests passed! Ready for AWS deployment.")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Install missing dependencies:")
        print("   pip install -r requirements.tts.txt")
        return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def create_test_audio():
    """Create a simple test audio file"""
    print("\n🎵 Creating test audio file...")

    try:
        import numpy as np

        # Generate a simple sine wave
        duration = 2  # seconds
        sample_rate = 44100
        frequency = 440  # A4 note

        t = np.linspace(0, duration, sample_rate * duration, False)
        audio_data = np.sin(frequency * 2 * np.pi * t)

        # Convert to 16-bit integers
        audio_data = (audio_data * 32767).astype(np.int16)

        # Save as WAV file
        with wave.open("test_audio.wav", "w") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        print("✅ Test audio file created: test_audio.wav")
        return True

    except ImportError:
        print("⚠️  NumPy not available, skipping audio generation")
        return False
    except Exception as e:
        print(f"❌ Audio creation failed: {e}")
        return False

async def test_server_startup():
    """Test if the server can start locally"""
    print("\n🚀 Testing server startup...")

    try:
        from gemini_tts_interface import GeminiTTSInterface

        interface = GeminiTTSInterface()
        print("✅ Server can be initialized")

        # Test health check endpoint
        health_status = {
            "status": "healthy",
            "services": {
                "gemini": interface.gemini_model is not None,
                "tts": interface.tts_client is not None,
                "stt": interface.stt_client is not None,
                "mcp_server": interface.mcp_server is not None
            }
        }

        print(f"✅ Health status: {health_status}")
        return True

    except Exception as e:
        print(f"❌ Server startup test failed: {e}")
        return False

def check_aws_prerequisites():
    """Check AWS deployment prerequisites"""
    print("\n☁️  Checking AWS prerequisites...")

    try:
        import subprocess

        # Check AWS CLI
        result = subprocess.run(["aws", "--version"], check=False, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ AWS CLI installed")
        else:
            print("❌ AWS CLI not found")
            return False

        # Check Docker
        result = subprocess.run(["docker", "--version"], check=False, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker installed")
        else:
            print("❌ Docker not found")
            return False

        # Check AWS credentials
        result = subprocess.run(["aws", "sts", "get-caller-identity"], check=False, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ AWS credentials configured")
        else:
            print("❌ AWS credentials not configured")
            return False

        return True

    except Exception as e:
        print(f"❌ AWS prerequisites check failed: {e}")
        return False

def main():
    """Main testing function"""
    print("🧪 MCP Server + TTS Interface - Local Testing")
    print("=" * 60)

    # Run all tests
    tests = [
        ("Environment Check", lambda: asyncio.run(test_gemini_tts_interface())),
        ("Audio Generation", create_test_audio),
        ("Server Startup", lambda: asyncio.run(test_server_startup())),
        ("AWS Prerequisites", check_aws_prerequisites)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Ready for AWS deployment.")
        print("\n📋 Next steps:")
        print("1. Update aws/deploy.sh with your AWS configuration")
        print("2. Run: ./aws/deploy.sh")
        print("3. Configure AWS Secrets Manager")
        print("4. Test the deployed interface")
    else:
        print("⚠️  Some tests failed. Please fix issues before deployment.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
