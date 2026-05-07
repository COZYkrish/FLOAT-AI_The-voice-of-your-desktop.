# # config.py — FLOAT AI Desktop Assistant
# # Loads environment variables, sets up logging, and defines global constants.

# import os
# import sys
# import logging
# from logging.handlers import RotatingFileHandler
# from pathlib import Path
# from dotenv import load_dotenv

# # ─── Paths ────────────────────────────────────────────────────────────────────
# BASE_DIR   = Path(__file__).parent.resolve()
# LOG_DIR    = BASE_DIR / "logs"
# ASSETS_DIR = BASE_DIR / "assets"
# LOG_FILE   = LOG_DIR / "float.log"

# # Make sure directories exist
# LOG_DIR.mkdir(exist_ok=True)
# ASSETS_DIR.mkdir(exist_ok=True)

# # ─── Load .env ────────────────────────────────────────────────────────────────
# load_dotenv(BASE_DIR / ".env")

# GROQ_API_KEY          = os.getenv("GROQ_API_KEY", "")
# GMAIL_ADDRESS         = os.getenv("GMAIL_ADDRESS", "")
# GMAIL_APP_PASSWORD    = os.getenv("GMAIL_APP_PASSWORD", "")
# WEATHER_API_KEY       = os.getenv("WEATHER_API_KEY", "")
# NEWS_API_KEY          = os.getenv("NEWS_API_KEY", "")
# SPOTIPY_CLIENT_ID     = os.getenv("SPOTIPY_CLIENT_ID", "")
# SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "")
# SPOTIPY_REDIRECT_URI  = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
# DEFAULT_CITY          = os.getenv("DEFAULT_CITY", "Bhubaneswar")

# # ─── FLOAT Constants ──────────────────────────────────────────────────────────
# FLOAT_VERSION       = "1.0.0"
# GROQ_MODEL          = "llama-3.3-70b-versatile"
# MAX_TOKENS          = 1024
# TEMPERATURE         = 0.7
# WAKE_WORD           = "float"
# LISTEN_TIMEOUT      = 10       # seconds to wait for a command after wake
# PHRASE_TIMEOUT      = 3        # seconds of silence to end phrase
# AMBIENT_DURATION    = 0.5      # seconds to calibrate ambient noise
# CHIME_PATH          = ASSETS_DIR / "chime.wav"

# TTS_LANG            = "en"     # 'en' for English, 'hi' for Hindi
# STT_LANG            = "en-US"  # 'en-US' or 'hi-IN'

# # WhatsApp Web (Selenium)
# WHATSAPP_SESSION_DIR = str(BASE_DIR / "whatsapp_session")
# WHATSAPP_HEADLESS    = os.getenv("WHATSAPP_HEADLESS", "false").lower() == "true"

# SYSTEM_PROMPT = (
#     "You are FLOAT, a smart AI desktop assistant. Be concise, "
#     "friendly, and helpful. Always address the user as 'sir' (use 'सर' if speaking in Hindi, never use 'सिर'). "
#     "Answer questions, perform tasks, and respond naturally as if "
#     "you are a voice assistant. Keep responses brief — under 3 sentences."
# )

# # ─── Logging ──────────────────────────────────────────────────────────────────
# def setup_logger() -> logging.Logger:
#     """Configure and return the root FLOAT logger."""
#     logger = logging.getLogger("FLOAT")
#     logger.setLevel(logging.DEBUG)

#     # Rotating file handler — 10 MB max, 3 backups
#     fh = RotatingFileHandler(
#         LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
#     )
#     fh.setLevel(logging.DEBUG)
#     fh.setFormatter(
#         logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
#     )

#     # Console handler (errors only, to keep terminal clean)
#     ch = logging.StreamHandler(sys.stdout)
#     ch.setLevel(logging.WARNING)
#     ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

#     logger.addHandler(fh)
#     logger.addHandler(ch)
#     return logger


# log = setup_logger()
