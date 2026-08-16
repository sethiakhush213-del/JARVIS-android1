"""
reminders.py
------------
Reminders and timers. Say things like:
  "remind me to call mom in 20 minutes"
  "set a timer for 5 minutes"
  "remind me to leave at 6pm"
"""

import json
import os
import re
from datetime import datetime, timedelta

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
REMINDERS_PATH = os.path.join(_DATA_DIR, "reminders.json")


def set_data_dir(path):
    global _DATA_DIR, REMINDERS_PATH
    _DATA_DIR = path
    REMINDERS_PATH = os.path.join(_DATA_DIR, "reminders.json")


def _load():
    if not os.path.exists(REMINDERS_PATH):
        return []
    try:
        with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(reminders_list):
    try:
        with open(REMINDERS_PATH, "w", encoding="utf-8") as f:
            json.dump(reminders_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _add(message: str, when: datetime) -> str:
    reminders_list = _load()
    reminders_list.append({
        "message": message.strip(),
        "trigger_time": when.isoformat(),
        "fired": False,
    })
    _save(reminders_list)
    return f"Got it - I'll remind you to {message.strip()} at {when.strftime('%I:%M %p').lstrip('0')}."


def get_due() -> list:
    reminders_list = _load()
    now = datetime.now()
    due = []
    changed = False
    for r in reminders_list:
        if not r.get("fired") and datetime.fromisoformat(r["trigger_time"]) <= now:
            due.append(r["message"])
            r["fired"] = True
            changed = True
    if changed:
        _save(reminders_list)
    return due


def list_upcoming() -> str:
    reminders_list = [r for r in _load() if not r.get("fired")]
    if not reminders_list:
        return "You don't have any reminders set."
    reminders_list.sort(key=lambda r: r["trigger_time"])
    lines = []
    for r in reminders_list:
        when = datetime.fromisoformat(r["trigger_time"])
        lines.append(f"- {r['message']} at {when.strftime('%I:%M %p').lstrip('0')}")
    return "Here's what's coming up:\n" + "\n".join(lines)


_UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600}


def try_handle(user_text: str):
    text = user_text.strip()
    lowered = text.lower()

    if lowered in ("what are my reminders", "what reminders do i have", "list my reminders", "my reminders", "my timers"):
        return list_upcoming()

    match = re.search(r"remind me to (.+?) in (\d+)\s*(second|minute|hour)s?\b", lowered)
    if match:
        message, amount, unit = match.group(1), int(match.group(2)), match.group(3)
        when = datetime.now() + timedelta(seconds=amount * _UNIT_SECONDS[unit])
        return _add(message, when)

    match = re.search(r"(?:set (?:a )?timer for|timer for)\s*(\d+)\s*(second|minute|hour)s?\b", lowered)
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        when = datetime.now() + timedelta(seconds=amount * _UNIT_SECONDS[unit])
        return _add("your timer's up", when)

    match = re.search(r"remind me to (.+?) at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lowered)
    if match:
        message = match.group(1)
        hour = int(match.group(2))
        minute = int(match.group(3)) if match.group(3) else 0
        meridiem = match.group(4)

        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0

        now = datetime.now()
        when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)
        return _add(message, when)

    return None
