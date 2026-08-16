"""
memory.py
---------
Saves/loads conversation history. On Android, files can only be
written to the app's own private storage folder (not just "next to
this script" like on desktop) - main.py calls set_data_dir() with
that folder right when the app starts, before anything else touches
storage.
"""

import json
import os
import config

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(_DATA_DIR, "jarvis_memory.json")


def set_data_dir(path):
    global _DATA_DIR, MEMORY_PATH
    _DATA_DIR = path
    MEMORY_PATH = os.path.join(_DATA_DIR, "jarvis_memory.json")


def load_history():
    if not config.MEMORY_ENABLED:
        return None
    if not os.path.exists(MEMORY_PATH):
        return None
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_history(history):
    if not config.MEMORY_ENABLED:
        return
    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clear_history():
    try:
        if os.path.exists(MEMORY_PATH):
            os.remove(MEMORY_PATH)
    except Exception:
        pass
