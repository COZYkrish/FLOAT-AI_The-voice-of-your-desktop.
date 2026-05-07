# system_control.py — FLOAT AI Desktop Assistant
# WiFi, Bluetooth, Volume, Brightness, App launcher, Screenshot, Lock, Power

import os
import sys
import time
import logging
import platform
import subprocess
import threading
from pathlib import Path

import pyautogui

from config import log
from voice import speak

logger = logging.getLogger("FLOAT.system")
OS = platform.system()   # "Windows", "Linux", "Darwin"


# ─── Helper ───────────────────────────────────────────────────────────────────
def _run(cmd: list, capture: bool = False) -> str:
    """Run a subprocess command and optionally return its output."""
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, timeout=10
        )
        return result.stdout.strip() if capture else ""
    except Exception as e:
        logger.error(f"subprocess error {cmd}: {e}")
        return ""


# ─── WiFi ─────────────────────────────────────────────────────────────────────
def toggle_wifi(state: str) -> str:
    """Turn WiFi on or off. state = 'on' or 'off'."""
    try:
        if OS == "Windows":
            if state == "on":
                _run(["netsh", "interface", "set", "interface", "Wi-Fi", "enable"])
            else:
                _run(["netsh", "interface", "set", "interface", "Wi-Fi", "disable"])
        elif OS == "Linux":
            _run(["nmcli", "radio", "wifi", state])
        elif OS == "Darwin":
            _run(["networksetup", "-setairportpower", "en0", state])
        msg = f"WiFi turned {state}."
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"WiFi toggle error: {e}")
        return "I couldn't change the WiFi state."


# ─── Bluetooth ────────────────────────────────────────────────────────────────
def toggle_bluetooth(state: str) -> str:
    """Turn Bluetooth on or off."""
    try:
        if OS == "Windows":
            # Use PowerShell to toggle Bluetooth radio
            ps_on  = ('$bt = Get-PnpDevice -Class Bluetooth; '
                      'Enable-PnpDevice -InstanceId $bt.InstanceId -Confirm:$false')
            ps_off = ('$bt = Get-PnpDevice -Class Bluetooth; '
                      'Disable-PnpDevice -InstanceId $bt.InstanceId -Confirm:$false')
            script = ps_on if state == "on" else ps_off
            subprocess.run(["powershell", "-Command", script], timeout=10)
        elif OS == "Linux":
            _run(["bluetoothctl", "power", state])
        elif OS == "Darwin":
            val = "1" if state == "on" else "0"
            _run(["blueutil", "--power", val])
        msg = f"Bluetooth turned {state}."
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"Bluetooth toggle error: {e}")
        return "I couldn't change the Bluetooth state."


# ─── Volume ───────────────────────────────────────────────────────────────────
def set_volume(level: int | None = None, direction: str | None = None) -> str:
    """
    Set volume to a percentage, or adjust up/down by 10%.
    level: 0-100, direction: 'up' or 'down'
    """
    try:
        if OS == "Windows":
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))

            if direction == "up":
                cur = int(volume.GetMasterVolumeLevelScalar() * 100)
                level = min(cur + 10, 100)
            elif direction == "down":
                cur = int(volume.GetMasterVolumeLevelScalar() * 100)
                level = max(cur - 10, 0)

            if level is not None:
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                msg = f"Volume set to {level}%."
                logger.info(msg)
                return msg
            return "I didn't understand the volume level."

        elif OS == "Linux":
            import pulsectl
            pulse = pulsectl.Pulse("float")
            sinks = pulse.sink_list()
            if not sinks:
                return "No audio sinks found."
            sink = sinks[0]
            if direction == "up":
                level = min(int(sink.volume.value_flat * 100) + 10, 100)
            elif direction == "down":
                level = max(int(sink.volume.value_flat * 100) - 10, 0)
            pulse.volume_set_all_chans(sink, level / 100.0)
            return f"Volume set to {level}%."

        elif OS == "Darwin":
            if direction == "up":
                _run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])
            elif direction == "down":
                _run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])
            elif level is not None:
                _run(["osascript", "-e", f"set volume output volume {level}"])
            return f"Volume adjusted."

    except Exception as e:
        logger.error(f"Volume error: {e}")
        return "I couldn't change the volume."


# ─── Brightness ───────────────────────────────────────────────────────────────
def set_brightness(level: int) -> str:
    """Set screen brightness (0-100)."""
    try:
        level = max(0, min(100, level))
        if OS == "Windows":
            import wmi
            c = wmi.WMI(namespace="wmi")
            methods = c.WmiMonitorBrightnessMethods()[0]
            methods.WmiSetBrightness(level, 0)
        elif OS == "Linux":
            _run(["brightnessctl", "set", f"{level}%"])
        elif OS == "Darwin":
            _run(["brightness", f"{level/100:.2f}"])
        msg = f"Brightness set to {level}%."
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"Brightness error: {e}")
        return "I couldn't change the brightness."


# ─── App Launcher ─────────────────────────────────────────────────────────────
_APP_ALIASES_WINDOWS = {
    "chrome":    "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox":   "firefox.exe",
    "edge":      "msedge.exe",
    "notepad":   "notepad.exe",
    "calculator": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer":  "explorer.exe",
    "vscode":    "code",
    "vs code":   "code",
    "spotify":   "spotify.exe",
    "discord":   "discord.exe",
    "telegram":  "telegram.exe",
    "word":      "winword.exe",
    "excel":     "excel.exe",
    "powerpoint":"powerpnt.exe",
    "cmd":       "cmd.exe",
    "terminal":  "wt.exe",
    "task manager": "taskmgr.exe",
    "paint":     "mspaint.exe",
    "vlc":       "vlc.exe",
}

_APP_ALIASES_LINUX = {
    "chrome": "google-chrome",
    "firefox": "firefox",
    "files": "nautilus",
    "vscode": "code",
    "terminal": "gnome-terminal",
    "calculator": "gnome-calculator",
    "text editor": "gedit",
}

_APP_ALIASES_MAC = {
    "chrome": "Google Chrome",
    "safari": "Safari",
    "finder": "Finder",
    "terminal": "Terminal",
    "vscode": "Visual Studio Code",
}


def open_app(app_name: str) -> str:
    """Launch an application by name or alias."""
    name = app_name.lower().strip()
    try:
        if OS == "Windows":
            exe = _APP_ALIASES_WINDOWS.get(name, name)
            subprocess.Popen([exe], shell=True)
        elif OS == "Linux":
            exe = _APP_ALIASES_LINUX.get(name, name)
            subprocess.Popen([exe])
        elif OS == "Darwin":
            app = _APP_ALIASES_MAC.get(name, app_name)
            subprocess.Popen(["open", "-a", app])
        msg = f"Opening {app_name}."
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"Open app error: {e}")
        return f"I couldn't open {app_name}."


# ─── Screenshot ───────────────────────────────────────────────────────────────
def take_screenshot() -> str:
    """Capture a screenshot and save to ~/Pictures/Float/."""
    try:
        save_dir = Path.home() / "Pictures" / "Float"
        save_dir.mkdir(parents=True, exist_ok=True)
        ts   = time.strftime("%Y%m%d_%H%M%S")
        path = save_dir / f"float_screenshot_{ts}.png"
        img  = pyautogui.screenshot()
        img.save(str(path))
        msg = f"Screenshot saved to {path}."
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return "I couldn't take a screenshot."


# ─── Lock Screen ──────────────────────────────────────────────────────────────
def lock_screen() -> str:
    try:
        if OS == "Windows":
            _run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif OS == "Linux":
            _run(["gnome-screensaver-command", "-l"])
        elif OS == "Darwin":
            _run(["pmset", "displaysleepnow"])
        return "Locking your screen."
    except Exception as e:
        logger.error(f"Lock screen error: {e}")
        return "I couldn't lock the screen."


# ─── Power Actions ────────────────────────────────────────────────────────────
def power_action(action: str) -> str:
    """
    Perform shutdown / restart / sleep after 5-second voice confirmation.
    action: 'shutdown', 'restart', 'sleep'
    """
    speak(f"Are you sure you want to {action}? Say yes to confirm.")

    # Import here to avoid circular at module level
    from voice import listen_once
    confirmation = listen_once(timeout=6, phrase_limit=3).lower()
    if "yes" not in confirmation:
        return f"{action.capitalize()} cancelled."

    try:
        if OS == "Windows":
            if action == "shutdown":
                _run(["shutdown", "/s", "/t", "5"])
            elif action == "restart":
                _run(["shutdown", "/r", "/t", "5"])
            elif action == "sleep":
                _run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        elif OS == "Linux":
            if action == "shutdown":
                _run(["systemctl", "poweroff"])
            elif action == "restart":
                _run(["systemctl", "reboot"])
            elif action == "sleep":
                _run(["systemctl", "suspend"])
        elif OS == "Darwin":
            if action == "shutdown":
                _run(["osascript", "-e", 'tell app "System Events" to shut down'])
            elif action == "restart":
                _run(["osascript", "-e", 'tell app "System Events" to restart'])
            elif action == "sleep":
                _run(["pmset", "sleepnow"])
        return f"Initiating {action}..."
    except Exception as e:
        logger.error(f"Power action error: {e}")
        return f"I couldn't {action} the computer."


# ─── Clipboard ────────────────────────────────────────────────────────────────
def get_clipboard() -> str:
    try:
        import pyperclip
        text = pyperclip.paste()
        return text if text else "Clipboard is empty."
    except Exception as e:
        logger.error(f"Clipboard read error: {e}")
        return "I couldn't read the clipboard."


def set_clipboard(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Copied to clipboard."
    except Exception as e:
        logger.error(f"Clipboard write error: {e}")
        return "I couldn't copy to the clipboard."
