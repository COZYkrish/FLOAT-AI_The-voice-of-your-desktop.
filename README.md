# FLOAT — AI Desktop Assistant

> A fully-featured, voice-activated AI desktop assistant powered by Groq (LLaMA 3 70B).

---

## Features

| Category | Capabilities |
|---|---|
| **AI Brain** | LLaMA 3 70B via Groq API, full conversation history |
| **Wake Word** | Continuous "Float" detection — hands-free |
| **Voice I/O** | Google STT + pyttsx3 TTS (offline), gTTS fallback |
| **System Control** | WiFi, Bluetooth, Volume, Brightness, App Launcher, Screenshot, Lock, Shutdown |
| **Messaging** | WhatsApp (pywhatkit), Gmail send & read (summarised by AI) |
| **Web** | Google Search, Wikipedia, OpenWeatherMap, NewsAPI |
| **Music** | Spotify (spotipy), YouTube audio (yt-dlp), Local music |
| **Productivity** | Reminders, To-do list, Calculator, Timer, File read/create |
| **GUI** | Animated tkinter dashboard + system tray |

---

## Requirements

- Python 3.11+
- Windows 10/11 (primary), Linux, macOS
- Microphone
- FFmpeg (for YouTube audio)
- Internet connection

---

## Quick Start (Windows)

```bash
# 1. Clone / download the project
cd "FLOAT AI"

# 2. Run the one-command installer
setup.bat

# 3. Edit your API keys
notepad .env

# 4. Launch FLOAT
python float.py
```

---

## Quick Start (Linux / macOS)

```bash
cd "FLOAT AI"

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows alternative

# Install dependencies
pip install -r requirements.txt

# Copy and fill in your .env
cp .env.template .env
nano .env

# Run
python float.py
```

---

## API Keys Setup

### 1. Groq API Key (Required)
1. Sign up at [console.groq.com](https://console.groq.com)
2. Create an API key
3. Add to `.env`: `GROQ_API_KEY=your_key`

### 2. Gmail App Password (for email)
1. Go to your Google Account → Security
2. Enable 2-Step Verification
3. Go to **App Passwords**, generate one for "Mail"
4. Add to `.env`: `GMAIL_APP_PASSWORD=your_16_char_password`

### 3. OpenWeatherMap (weather)
1. Register at [openweathermap.org](https://openweathermap.org/api)
2. Get free API key
3. Add to `.env`: `WEATHER_API_KEY=your_key`

### 4. NewsAPI (news headlines)
1. Register at [newsapi.org](https://newsapi.org)
2. Get free API key
3. Add to `.env`: `NEWS_API_KEY=your_key`

### 5. Spotify (optional)
1. Go to [developer.spotify.com](https://developer.spotify.com/dashboard)
2. Create an app, set redirect URI to `http://localhost:8888/callback`
3. Add client ID and secret to `.env`

---

## FFmpeg Installation (Windows)

Required for YouTube audio playback:

1. Download from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/)
2. Extract and add the `bin` folder to your `PATH`
3. Verify: `ffmpeg -version`

---

## Voice Commands Reference

```
"Float, turn on WiFi"
"Float, turn off Bluetooth"
"Float, set volume to 60"
"Float, volume up"
"Float, open Chrome"
"Float, take a screenshot"
"Float, lock my screen"
"Float, text Mom I'll be home late"
"Float, read my latest emails"
"Float, play Blinding Lights on Spotify"
"Float, pause music"
"Float, next song"
"Float, what's the weather in Bhubaneswar?"
"Float, search Python tutorials"
"Float, open YouTube"
"Float, who is Elon Musk?"
"Float, remind me to take medicine in 1 hour"
"Float, add buy groceries to my to-do list"
"Float, show my to-do list"
"Float, what is 458 divided by 13?"
"Float, set a 20 minute timer"
"Float, read my notes.txt file"
"Float, shutdown the computer"
```

---

## Project Structure

```
FLOAT AI/
├── float.py            # Main entry point
├── config.py           # .env loader, constants, logger
├── voice.py            # Wake word, STT, TTS
├── brain.py            # Groq API, intent router, entity extractor
├── system_control.py   # System operations
├── messaging.py        # WhatsApp + Gmail
├── web.py              # Search, weather, news, Wikipedia
├── media.py            # Spotify, YouTube, local music
├── files.py            # Files, reminders, todos, calculator, timer
├── gui.py              # tkinter dashboard + system tray
├── contacts.json       # WhatsApp contacts
├── reminders.json      # Stored reminders
├── .env                # Your API keys (never share!)
├── requirements.txt
├── setup.bat
└── logs/float.log      # Rotating log
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `PyAudio install fails` | Install via `pipwin install pyaudio` or use the wheel from [unofficial binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/) |
| `No voice detected` | Check microphone permissions in Windows Settings → Privacy |
| `Groq API error` | Verify your `GROQ_API_KEY` in `.env` |
| `YouTube won't play` | Install FFmpeg and ensure it's in your PATH |
| `pycaw not found` | Run `pip install pycaw comtypes` |
| `FLOAT crashes at startup` | Check `logs/float.log` for the full error trace |

---

## License
MIT — Free to use, modify, and distribute.
