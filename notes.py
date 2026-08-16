"""
notes.py
--------
Simple notes / to-do list storage. Say things like:
  "note buy milk"
  "add pay rent to my list"
  "what's on my list"
  "clear my notes"
  "remove note 2"
"""

import json
import os
import re

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_PATH = os.path.join(_DATA_DIR, "notes.json")


def set_data_dir(path):
    global _DATA_DIR, NOTES_PATH
    _DATA_DIR = path
    NOTES_PATH = os.path.join(_DATA_DIR, "notes.json")


def _load():
    if not os.path.exists(NOTES_PATH):
        return []
    try:
        with open(NOTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(notes_list):
    try:
        with open(NOTES_PATH, "w", encoding="utf-8") as f:
            json.dump(notes_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_note(text: str) -> str:
    notes_list = _load()
    notes_list.append(text.strip())
    _save(notes_list)
    return f'Added to your list: "{text.strip()}".'


def list_notes() -> str:
    notes_list = _load()
    if not notes_list:
        return "Your list's empty."
    lines = [f"{i + 1}. {n}" for i, n in enumerate(notes_list)]
    return "Here's what's on your list:\n" + "\n".join(lines)


def clear_notes() -> str:
    _save([])
    return "Cleared your whole list."


def remove_note(index: int) -> str:
    notes_list = _load()
    if index < 1 or index > len(notes_list):
        return f"I don't see a note numbered {index}."
    removed = notes_list.pop(index - 1)
    _save(notes_list)
    return f'Removed: "{removed}".'


def try_handle(user_text: str):
    text = user_text.strip()
    lowered = text.lower()

    if lowered in (
        "what's on my list", "whats on my list", "read my notes", "read my list",
        "show my notes", "show my list", "my notes", "my to-do list", "my todo list",
    ):
        return list_notes()

    if lowered in ("clear my notes", "clear my list", "clear my to-do list", "clear my todo list"):
        return clear_notes()

    match = re.match(r"(?:remove|delete) note (\d+)", lowered)
    if match:
        return remove_note(int(match.group(1)))

    match = re.match(r"(?:note down|note|add note)\s+(.+)", text, re.IGNORECASE)
    if match:
        return add_note(match.group(1))

    match = re.match(r"add (.+?) to my (?:list|notes|to-do list|todo list)", text, re.IGNORECASE)
    if match:
        return add_note(match.group(1))

    return None
