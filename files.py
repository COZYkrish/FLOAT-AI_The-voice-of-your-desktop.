# files.py — FLOAT AI Desktop Assistant
# File ops, Reminders, To-do list, Calculator, Timer/Stopwatch

import json
import time
import math
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

import schedule

from config import BASE_DIR, log
from brain import ask_groq

logger = logging.getLogger("FLOAT.files")

REMINDERS_FILE = BASE_DIR / "reminders.json"
TODOS_FILE     = Path.home() / "float_todos.json"

# Callback set by float.py so this module can speak without circular import
_speak_callback = None

def set_speak_callback(fn) -> None:
    global _speak_callback
    _speak_callback = fn

def _speak(text: str) -> None:
    if _speak_callback:
        _speak_callback(text)
    else:
        print(f"[FLOAT] {text}")


# ─── File Operations ──────────────────────────────────────────────────────────
def create_file(filename: str, content: str = "") -> str:
    try:
        path = Path(filename).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Created file: {path}."
    except Exception as e:
        logger.error(f"Create file error: {e}")
        return "I couldn't create the file."


def create_folder(folder_name: str) -> str:
    try:
        path = Path(folder_name).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return f"Created folder: {path}."
    except Exception as e:
        logger.error(f"Create folder error: {e}")
        return "I couldn't create the folder."


def delete_file(filename: str) -> str:
    try:
        path = Path(filename).expanduser()
        if not path.exists():
            return f"File not found: {filename}."
        path.unlink()
        return f"Deleted: {path}."
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return "I couldn't delete the file."


def open_file(filename: str) -> str:
    try:
        path = Path(filename).expanduser()
        if not path.exists():
            # Search for it
            found = search_file(filename)
            if not found:
                return f"File not found: {filename}."
            path = Path(found[0])
        import os, platform
        if platform.system() == "Windows":
            os.startfile(str(path))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return f"Opening {path.name}."
    except Exception as e:
        logger.error(f"Open file error: {e}")
        return "I couldn't open the file."


def search_file(query: str, search_root: str = "~") -> list[str]:
    """Walk the filesystem and find files with names matching query."""
    results = []
    root = Path(search_root).expanduser()
    q = query.lower()
    try:
        for p in root.rglob("*"):
            if q in p.name.lower():
                results.append(str(p))
                if len(results) >= 10:
                    break
    except PermissionError:
        pass
    return results


def read_file(filename: str) -> str:
    """Read a text file and summarise it with Groq."""
    try:
        # Try exact path first
        path = Path(filename).expanduser()
        if not path.exists():
            # Search for it
            hits = search_file(filename)
            if not hits:
                return f"I couldn't find a file called '{filename}'."
            path = Path(hits[0])

        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > 3000:
            text = text[:3000] + "\n[... truncated ...]"

        if not text.strip():
            return f"{path.name} appears to be empty."

        summary = ask_groq(f"Summarise this file content briefly:\n\n{text}")
        return f"Here's a summary of {path.name}: {summary}"
    except Exception as e:
        logger.error(f"Read file error: {e}")
        return "I couldn't read that file."


# ─── Reminders ────────────────────────────────────────────────────────────────
def _load_reminders() -> list:
    try:
        if REMINDERS_FILE.exists():
            with open(REMINDERS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Load reminders error: {e}")
    return []


def _save_reminders(reminders: list) -> None:
    try:
        with open(REMINDERS_FILE, "w") as f:
            json.dump(reminders, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Save reminders error: {e}")


def set_reminder(task: str, amount: int, unit: str) -> str:
    """Schedule a reminder. unit: 'second', 'minute', 'hour'."""
    try:
        multiplier = {"second": 1, "minute": 60, "hour": 3600}.get(unit, 60)
        seconds    = amount * multiplier
        fire_time  = datetime.now() + timedelta(seconds=seconds)

        reminder = {
            "task":      task,
            "fire_time": fire_time.isoformat(),
            "done":      False,
        }
        reminders = _load_reminders()
        reminders.append(reminder)
        _save_reminders(reminders)

        # Schedule in background
        def _fire():
            _speak(f"Reminder: {task}")
            logger.info(f"Reminder fired: {task}")

        t = threading.Timer(seconds, _fire)
        t.daemon = True
        t.start()

        unit_label = unit + ("s" if amount != 1 else "")
        return f"Reminder set: '{task}' in {amount} {unit_label}."
    except Exception as e:
        logger.error(f"Set reminder error: {e}")
        return "I couldn't set the reminder."


# ─── To-Do List ───────────────────────────────────────────────────────────────
def _load_todos() -> list:
    try:
        if TODOS_FILE.exists():
            with open(TODOS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_todos(todos: list) -> None:
    try:
        with open(TODOS_FILE, "w") as f:
            json.dump(todos, f, indent=2)
    except Exception as e:
        logger.error(f"Save todos error: {e}")


def add_todo(item: str) -> str:
    todos = _load_todos()
    todos.append({"task": item, "done": False})
    _save_todos(todos)
    return f"Added '{item}' to your to-do list."


def list_todos() -> str:
    todos = _load_todos()
    if not todos:
        return "Your to-do list is empty."
    pending = [t["task"] for t in todos if not t["done"]]
    if not pending:
        return "All tasks are completed!"
    return "Your pending tasks: " + ", ".join(f"{i+1}. {t}" for i, t in enumerate(pending))


def complete_todo(item_number: int) -> str:
    todos = _load_todos()
    pending = [t for t in todos if not t["done"]]
    if item_number < 1 or item_number > len(pending):
        return f"No task number {item_number}."
    pending[item_number - 1]["done"] = True
    _save_todos(todos)
    return f"Marked task {item_number} as done."


def delete_todo(item_number: int) -> str:
    todos = _load_todos()
    pending = [t for t in todos if not t["done"]]
    if item_number < 1 or item_number > len(pending):
        return f"No task number {item_number}."
    task = pending[item_number - 1]["task"]
    todos.remove(pending[item_number - 1])
    _save_todos(todos)
    return f"Removed '{task}' from your to-do list."


# ─── Calculator ───────────────────────────────────────────────────────────────
def calculate(expression: str) -> str:
    """Safely evaluate a math expression using simpleeval."""
    try:
        from simpleeval import simple_eval, EvalWithCompoundTypes
        # Clean up voice-friendly words
        expr = (expression
                .replace("times",   "*")
                .replace("plus",    "+")
                .replace("minus",   "-")
                .replace("divided by", "/")
                .replace("x",       "*")
                .replace("^",       "**")
                .replace("percent", "/100")
                .strip())
        result = simple_eval(expr)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"The answer is {result}."
    except Exception as e:
        logger.error(f"Calculator error for '{expression}': {e}")
        return "I couldn't calculate that. Please try a simpler expression."


# ─── Timer / Stopwatch ────────────────────────────────────────────────────────
_stopwatch_start: float | None = None


def set_timer(amount: int, unit: str) -> str:
    """Set a countdown timer."""
    try:
        multiplier = {"second": 1, "minute": 60, "hour": 3600}.get(unit, 60)
        seconds    = amount * multiplier

        def _fire():
            _speak(f"Your {amount} {unit} timer is done!")

        t = threading.Timer(seconds, _fire)
        t.daemon = True
        t.start()

        unit_label = unit + ("s" if amount != 1 else "")
        return f"Timer set for {amount} {unit_label}."
    except Exception as e:
        logger.error(f"Timer error: {e}")
        return "I couldn't set the timer."


def start_stopwatch() -> str:
    global _stopwatch_start
    _stopwatch_start = time.time()
    return "Stopwatch started."


def stop_stopwatch() -> str:
    global _stopwatch_start
    if _stopwatch_start is None:
        return "Stopwatch is not running."
    elapsed = time.time() - _stopwatch_start
    _stopwatch_start = None
    mins  = int(elapsed // 60)
    secs  = elapsed % 60
    return f"Stopwatch stopped at {mins} minutes and {secs:.1f} seconds."


# ─── Reminder Scheduler (schedule loop) ──────────────────────────────────────
def run_scheduler() -> None:
    """Run the schedule event loop in a daemon thread."""
    while True:
        schedule.run_pending()
        time.sleep(1)


def start_scheduler() -> None:
    t = threading.Thread(target=run_scheduler, name="SchedulerThread", daemon=True)
    t.start()
    logger.info("Reminder scheduler started")
