import sys
import os

# Append the current directory so we can import config and voice
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from config import TTS_LANG
from voice import _gtts_speak

print(f"Current TTS_LANG is: {TTS_LANG}")
print("Testing gTTS...")
try:
    _gtts_speak("नमस्ते सर, मैं आपकी सहायता के लिए तैयार हूँ।")
    print("gTTS finished successfully.")
except Exception as e:
    print(f"Error: {e}")
