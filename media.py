# media.py — FLOAT AI Desktop Assistant
# Spotify control (spotipy), YouTube audio (yt-dlp + pygame), Local music

import os
import re
import glob
import time
import logging
import tempfile
import threading
from pathlib import Path

from config import (
    SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, log
)

logger = logging.getLogger("FLOAT.media")

# ─── pygame mixer ─────────────────────────────────────────────────────────────
_pygame_ok = False
try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    _pygame_ok = True
except Exception as e:
    logger.warning(f"pygame not available for media: {e}")

# ─── Spotify ──────────────────────────────────────────────────────────────────
_sp = None

def _get_spotify():
    global _sp
    if _sp:
        return _sp
    if not (SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET):
        return None
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        scope = "user-modify-playback-state user-read-playback-state user-read-currently-playing"
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=scope,
            open_browser=True,
        ))
        logger.info("Spotify client initialized")
        return _sp
    except Exception as e:
        logger.warning(f"Spotify init failed: {e}")
        return None


def spotify_play(query: str) -> str:
    """Search Spotify for a track and play it on the active device."""
    sp = _get_spotify()
    if not sp:
        return None  # Caller will fall back to YouTube

    try:
        results = sp.search(q=query, type="track", limit=1)
        tracks = results["tracks"]["items"]
        if not tracks:
            return f"Couldn't find '{query}' on Spotify."
        track = tracks[0]
        uri   = track["uri"]
        name  = track["name"]
        artist = track["artists"][0]["name"]

        # Try to play on an active device
        try:
            sp.start_playback(uris=[uri])
        except Exception as e:
            # If no active device is found (HTTP 404), fallback to opening the URL
            if "404" in str(e) or "NO_ACTIVE_DEVICE" in str(e):
                logger.warning("No active Spotify device. Opening via web/app URL.")
                import webbrowser
                # "external_urls.spotify" handles both desktop app deep-linking and web player
                webbrowser.open(track["external_urls"]["spotify"])
            else:
                raise e
                
        return f"Playing {name} by {artist} on Spotify."
    except Exception as e:
        logger.error(f"Spotify play error: {e}")
        return None  # Fall back to YouTube


def spotify_pause() -> str:
    sp = _get_spotify()
    if not sp:
        return "Spotify is not connected."
    try:
        sp.pause_playback()
        return "Music paused."
    except Exception as e:
        logger.error(f"Spotify pause: {e}")
        return "Couldn't pause Spotify."


def spotify_resume() -> str:
    sp = _get_spotify()
    if not sp:
        return "Spotify is not connected."
    try:
        sp.start_playback()
        return "Music resumed."
    except Exception as e:
        logger.error(f"Spotify resume: {e}")
        return "Couldn't resume Spotify."


def spotify_next() -> str:
    sp = _get_spotify()
    if not sp:
        return "Spotify is not connected."
    try:
        sp.next_track()
        return "Skipped to next track."
    except Exception as e:
        logger.error(f"Spotify next: {e}")
        return "Couldn't skip to next track."


def spotify_prev() -> str:
    sp = _get_spotify()
    if not sp:
        return "Spotify is not connected."
    try:
        sp.previous_track()
        return "Going to previous track."
    except Exception as e:
        logger.error(f"Spotify prev: {e}")
        return "Couldn't go to previous track."


# ─── YouTube Audio (yt-dlp + pygame) ─────────────────────────────────────────
_yt_thread: threading.Thread | None = None
_yt_temp_file: str | None = None


def youtube_play(query: str) -> str:
    """Open YouTube search results for the requested video."""
    try:
        import webbrowser
        from urllib.parse import quote_plus
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        webbrowser.open(url)
        logger.info(f"Opening YouTube for: {query}")
        return f"Opening YouTube for: {query}."
    except Exception as e:
        logger.error(f"YouTube play error: {e}")
        return "I couldn't open YouTube."


def stop_youtube() -> str:
    if _pygame_ok and pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
        return "Music stopped."
    return "Nothing is playing."


# ─── Local Music ─────────────────────────────────────────────────────────────
def _scan_local_music() -> list[Path]:
    """Scan ~/Music for mp3/wav files."""
    music_dir = Path.home() / "Music"
    files = []
    if music_dir.exists():
        files += list(music_dir.rglob("*.mp3"))
        files += list(music_dir.rglob("*.wav"))
    return files


def play_local(song_name: str) -> str:
    """Play a local music file by fuzzy name match."""
    if not _pygame_ok:
        return "Audio playback is not available."

    files = _scan_local_music()
    if not files:
        return "No local music files found in ~/Music."

    try:
        from difflib import get_close_matches
        names = [f.stem.lower() for f in files]
        matches = get_close_matches(song_name.lower(), names, n=1, cutoff=0.4)

        if not matches:
            return f"I couldn't find '{song_name}' in your local music library."

        idx  = names.index(matches[0])
        path = files[idx]
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()
        return f"Playing local track: {path.stem}."
    except Exception as e:
        logger.error(f"Local music error: {e}")
        return "I couldn't play the local track."


# ─── Unified Play Entry ───────────────────────────────────────────────────────
def play_music(song: str, source: str = "auto") -> str:
    """
    Unified music play function.
    source: 'spotify', 'youtube', 'local', or 'auto' (tries Spotify → YouTube)
    """
    if source == "local":
        return play_local(song)

    if source in ("spotify", "auto"):
        result = spotify_play(song)
        if result:
            return result
        # Fall through to YouTube

    return youtube_play(song)


def pause_music() -> str:
    # Try Spotify first
    sp = _get_spotify()
    if sp:
        try:
            sp.pause_playback()
            return "Music paused."
        except Exception:
            pass
    # Try pygame
    if _pygame_ok and pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
        return "Music paused."
    return "Nothing is currently playing."


def next_track() -> str:
    sp = _get_spotify()
    if sp:
        return spotify_next()
    return "No music player is connected."


def prev_track() -> str:
    sp = _get_spotify()
    if sp:
        return spotify_prev()
    return "No music player is connected."
