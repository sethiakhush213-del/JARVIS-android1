"""
brain.py
--------
Jarvis's "mind" - same logic as the desktop/mobile-web versions.
"""

import time
import requests
import config
import memory
from websearch import search_web

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class Jarvis:
    def __init__(self):
        if not config.OPENROUTER_API_KEY or "PASTE_YOUR" in config.OPENROUTER_API_KEY:
            raise ValueError(
                "No API key found. Open config.py and paste your OpenRouter "
                "API key into OPENROUTER_API_KEY."
            )
        self.system_message = {"role": "system", "content": config.SYSTEM_PROMPT}
        saved = memory.load_history() or []
        self.history = [self.system_message] + saved[-config.MAX_HISTORY_MESSAGES:]

    def forget_everything(self):
        self.history = [self.system_message]
        memory.clear_history()

    def _call_model(self):
        last_error = None
        for attempt in range(2):
            try:
                return self._call_model_once()
            except RuntimeError as e:
                last_error = e
                if attempt == 0:
                    time.sleep(0.5)
        raise last_error

    def _call_model_once(self):
        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.MODEL_NAME,
            "messages": self.history,
            "max_tokens": 300,
        }
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text[:300]}")

        data = response.json()
        if "error" in data:
            raise RuntimeError(f"Model error: {data['error']}")

        choices = data.get("choices")
        if not choices:
            raise RuntimeError(
                "The model didn't return an answer (it may be overloaded or "
                "rate-limited right now). Try again in a moment."
            )

        return choices[0]["message"]["content"].strip()

    def ask(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        self._trim_history()

        reply = self._call_model()

        if reply.upper().startswith("SEARCH:"):
            query = reply.split(":", 1)[1].strip()
            self.history.append({"role": "assistant", "content": reply})

            results = search_web(query)
            self.history.append({
                "role": "user",
                "content": (
                    f"Here are web search results for '{query}':\n\n{results}\n\n"
                    "Now answer my original question using this information, "
                    "in your own words, staying in character as Jarvis."
                )
            })
            reply = self._call_model()

        self.history.append({"role": "assistant", "content": reply})
        self._trim_history()
        memory.save_history(self.history[1:])
        return reply

    def _trim_history(self):
        if len(self.history) > config.MAX_HISTORY_MESSAGES + 1:
            self.history = [self.system_message] + self.history[-config.MAX_HISTORY_MESSAGES:]
