# voice.py — FLOAT AI Desktop Assistant
Wake word detection, Speech-to-Text (Google), Text-to-Speech (pyttsx3/gTTS)

import io
import os
import time
import wave
import struct
import math
import threading
import queue
import logging

import speech_recognition as sr

from config import (
    WAKE_WORD, LISTEN_TIMEOUT, PHRASE_TIMEOUT, AMBIENT_DURATION,
    CHIME_PATH, TTS_LANG, STT_LANG, log
)

logger = logging.getLogger("FLOAT.voice")

CURRENT_LANG = TTS_LANG

def set_language(lang: str) -> None:
    global CURRENT_LANG
    CURRENT_LANG = lang
    logger.info(f"Language switched to {lang}")

# ─── Generate chime if missing ────────────────────────────────────────────────
def _generate_chime(path) -> None:
    """Create a simple sine-wave chime WAV file programmatically."""
    try:
        sample_rate = 44100
        duration    = 0.4          # seconds
        frequency   = 880.0        # Hz — A5
        amplitude   = 0.4

        n_samples = int(sample_rate * duration)
        samples = []
        for i in range(n_samples):
            t = i / sample_rate
            # Fade out envelope
            env = 1.0 - (i / n_samples)
            val = amplitude * env * math.sin(2 * math.pi * frequency * t)
            # 16-bit PCM
            samples.append(int(val * 32767))

        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        logger.info(f"Generated chime at {path}")
    except Exception as e:
        logger.error(f"Could not generate chime: {e}")


if not CHIME_PATH.exists():
    _generate_chime(CHIME_PATH)

# ─── pygame mixer ─────────────────────────────────────────────────────────────
_pygame_ok = False
try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    _pygame_ok = True
except Exception as e:
    logger.warning(f"pygame not available: {e}")


def play_chime() -> None:
    """Play the wake-word activation chime (non-blocking)."""
    if not _pygame_ok:
        return
    try:
        sound = pygame.mixer.Sound(str(CHIME_PATH))
        sound.play()
    except Exception as e:
        logger.error(f"Chime play error: {e}")


# ─── TTS engine ───────────────────────────────────────────────────────────────
_tts_queue = queue.Queue()

def _tts_worker():
    try:
        import pyttsx3
        import pythoncom
        pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.setProperty("volume", 1.0)
        voices = engine.getProperty("voices")
        
        target_voice = None
        for v in voices:
            if CURRENT_LANG == "hi" and ("Hindi" in v.name or "hi-IN" in getattr(v, "languages", []) or "hi" in getattr(v, "id", "").lower()):
                target_voice = v
                break
            elif CURRENT_LANG == "en" and "English" in v.name:
                target_voice = v
                break

        if CURRENT_LANG == "hi":
            # Force edge-tts for Hindi as Windows SAPI5 voices often fail silently on Devanagari
            engine = None
        elif target_voice:
            engine.setProperty("voice", target_voice.id)
        elif len(voices) > 0:
            engine.setProperty("voice", voices[0].id)
    except Exception as e:
        logger.warning(f"pyttsx3 init failed in worker: {e}")
        engine = None

    while True:
        text = _tts_queue.get()
        if text is None:
            break
            
        if CURRENT_LANG == "hi":
            # Bypass pyttsx3 to use edge-tts male Hindi voice
            _edge_speak(text)
        elif engine:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.error(f"pyttsx3 say error: {e}")
                _edge_speak(text)
        else:
            _edge_speak(text)
        _tts_queue.task_done()

# Start the dedicated TTS worker thread
threading.Thread(target=_tts_worker, daemon=True, name="TTSThread").start()

def speak(text: str, blocking: bool = True) -> None:
    """Speak text aloud using the dedicated TTS worker thread."""
    logger.debug(f"TTS queued: {text}")
    _tts_queue.put(text)
    if blocking:
        _tts_queue.join()


def _edge_speak(text: str) -> None:
    """TTS using edge-tts (deep male voices) + pygame."""
    if not _pygame_ok:
        logger.warning("No TTS available.")
        return
    try:
        import edge_tts
        import asyncio
        import tempfile

        if CURRENT_LANG == "hi":
            # Prevent mispronunciation of "sir" in Hindi voice
            text = text.replace("सिर", "सर").replace("sir", "सर").replace("Sir", "सर")

        voice = "hi-IN-MadhurNeural" if CURRENT_LANG == "hi" else "en-US-ChristopherNeural"

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            tmp_path = fp.name

        async def _save():
            comm = edge_tts.Communicate(text, voice, rate="+35%")
            await comm.save(tmp_path)

        # Run async function in a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_save())
        loop.close()

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()  # Fix WinError 32 file lock
        try:
            os.unlink(tmp_path)
        except OSError as e:
            logger.warning(f"Could not delete temp edge-tts file {tmp_path}: {e}")
    except Exception as e:
        logger.error(f"edge-tts speak error: {e}")
        _gtts_speak(text)


def _gtts_speak(text: str) -> None:
    """Fallback TTS using gTTS + pygame."""
    if not _pygame_ok:
        logger.warning("No TTS available.")
        return
    try:
        from gtts import gTTS
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            tmp_path = fp.name

        tts = gTTS(text=text, lang=CURRENT_LANG)
        tts.save(tmp_path)
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()  # Fix WinError 32 file lock
        try:
            os.unlink(tmp_path)
        except OSError as e:
            logger.warning(f"Could not delete temp gTTS file {tmp_path}: {e}")
    except Exception as e:
        logger.error(f"gTTS speak error: {e}")


# ─── Speech Recognition ───────────────────────────────────────────────────────
_recognizer = sr.Recognizer()
_mic         = None

def _get_mic():
    global _mic
    if _mic is None:
        try:
            _mic = sr.Microphone()
        except Exception as e:
            logger.error(f"Microphone init failed: {e}")
    return _mic


def listen_once(timeout: int = LISTEN_TIMEOUT, phrase_limit: int = PHRASE_TIMEOUT) -> str:
    """
    Listen for one phrase and return transcribed text.
    Returns empty string on failure.
    """
    mic = _get_mic()
    if mic is None:
        return ""
    try:
        with mic as source:
            _recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_DURATION)
            logger.debug("Listening for command...")
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        stt_lang = "hi-IN" if CURRENT_LANG == "hi" else "en-US"
        text = _recognizer.recognize_google(audio, language=stt_lang)
        logger.info(f"Heard: {text}")
        return text
    except sr.WaitTimeoutError:
        logger.debug("Listen timeout — no speech detected")
        return ""
    except sr.UnknownValueError:
        logger.debug("Speech unintelligible")
        return ""
    except Exception as e:
        logger.error(f"STT error: {e}")
        return ""


# ─── Wake Word Loop ───────────────────────────────────────────────────────────
class WakeWordListener:
    """
    Daemon thread that continuously listens for the wake word "float".
    On detection: plays chime, signals the GUI, then listens for a command.
    """
    def __init__(self, on_wake_callback, on_command_callback, status_queue: queue.Queue):
        self._on_wake    = on_wake_callback       # called when wake word heard
        self._on_command = on_command_callback    # called with command text
        self._status_q   = status_queue
        self._stop_event = threading.Event()
        self._manual_wake_event = threading.Event()
        self._thread     = threading.Thread(
            target=self._loop, name="WakeWordThread", daemon=True
        )

    def start(self) -> None:
        self._thread.start()
        logger.info("Wake word listener started")

    def stop(self) -> None:
        self._stop_event.set()

    def trigger_wake(self) -> None:
        self._manual_wake_event.set()

    def _set_status(self, status: str) -> None:
        try:
            self._status_q.put_nowait(("status", status))
        except queue.Full:
            pass

    def _loop(self) -> None:
        mic = _get_mic()
        if mic is None:
            logger.error("No microphone — wake word loop cannot start")
            return

        with mic as source:
            logger.info("Calibrating microphone for ambient noise...")
            _recognizer.adjust_for_ambient_noise(source, duration=2.0)
            logger.info("Microphone calibrated. Ready.")

            while not self._stop_event.is_set():
                try:
                    # ── Ambient listen for wake word ─────────────────────────
                    self._set_status("Sleeping...")
                    
                    wake_detected = False
                    if self._manual_wake_event.is_set():
                        self._manual_wake_event.clear()
                        wake_detected = True
                        logger.info("Wake triggered manually")
                    else:
                        try:
                            # short phrase limit for wake word
                            audio = _recognizer.listen(source, timeout=1, phrase_time_limit=3)
                            text = _recognizer.recognize_google(audio).lower()
                            wake_aliases = [WAKE_WORD, "flot", "flow", "slot", "flute", "load", "slow", "close"]
                            if any(w in text for w in wake_aliases):
                                wake_detected = True
                                logger.info(f"Wake word detected in: '{text}'")
                        except sr.WaitTimeoutError:
                            pass
                        except sr.UnknownValueError:
                            pass
                        except Exception as e:
                            logger.debug(f"Wake STT error: {e}")
                            pass

                    if not wake_detected:
                        if self._manual_wake_event.is_set():
                            self._manual_wake_event.clear()
                            wake_detected = True
                            logger.info("Wake triggered manually")
                        else:
                            continue

                    # ── Wake word detected ───────────────────────────────────
                    play_chime()
                    self._on_wake()
                    self._set_status("Listening...")

                    # Listen for the actual command using the SAME open microphone
                    command_text = ""
                    try:
                        cmd_audio = _recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_TIMEOUT)
                        stt_lang = "hi-IN" if CURRENT_LANG == "hi" else "en-US"
                        command_text = _recognizer.recognize_google(cmd_audio, language=stt_lang)
                        logger.info(f"Heard: {command_text}")
                    except sr.WaitTimeoutError:
                        logger.debug("Listen timeout — no speech detected")
                    except sr.UnknownValueError:
                        logger.debug("Speech unintelligible")
                    except Exception as e:
                        logger.error(f"STT command error: {e}")

                    if command_text:
                        self._set_status("Thinking...")
                        self._on_command(command_text)
                    else:
                        speak("I didn't catch that. Say Float again when you're ready.", blocking=False)
                        self._set_status("Sleeping...")

                except Exception as e:
                    logger.error(f"Wake word loop error: {e}", exc_info=True)
                    time.sleep(1)   # brief pause before retrying
