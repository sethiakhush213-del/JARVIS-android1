"""
android_voice.py
-----------------
Speech-to-text and text-to-speech for the Android app, built on
Android's own native voice APIs via pyjnius (lets Python call Java/
Android APIs directly). This ONLY works when actually running on
Android through python-for-android - you can't test this file on a
regular PC.

THIS IS THE MOST LIKELY FILE TO NEED ADJUSTING. Android API behavior
can vary a bit across versions/manufacturers (Samsung's own voice
stack, for instance, can behave slightly differently than stock
Android). If listen()/speak() error out on your phone, send me the
error from the Buildozer log (or logcat) and we'll adjust this file -
the rest of the app doesn't need to change.
"""

import os
import time
import tempfile
import threading
import traceback
import requests
import config

try:
    from jnius import autoclass
    from android import activity, mActivity
    ANDROID_AVAILABLE = True
except Exception:
    ANDROID_AVAILABLE = False

_pending_callback = None

if ANDROID_AVAILABLE:
    Intent = autoclass("android.content.Intent")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    Activity = autoclass("android.app.Activity")

    REQUEST_CODE_SPEECH = 4321

    def _on_activity_result(request_code, result_code, intent):
        """Called by Android once the built-in voice input dialog closes
        (RESULT_OK if it heard something, cancelled otherwise)."""
        global _pending_callback
        if request_code != REQUEST_CODE_SPEECH:
            return
        heard = None
        try:
            if result_code == Activity.RESULT_OK and intent is not None:
                results = intent.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                if results and results.size() > 0:
                    heard = results.get(0)
        except Exception:
            traceback.print_exc()
        if _pending_callback:
            cb, _pending_callback = _pending_callback, None
            cb(heard)

    activity.bind(on_activity_result=_on_activity_result)


def listen(on_result):
    """Pops up Android's own built-in voice input dialog (the same one
    Google apps use) and calls on_result(text) with what was heard, or
    on_result(None) if nothing was understood/it was cancelled. Must be
    called from the main UI thread (a button's on_release handler is
    fine - Kivy runs those on the main thread already)."""
    global _pending_callback
    if not ANDROID_AVAILABLE:
        on_result(None)
        return

    _pending_callback = on_result
    intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
    intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
    intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to Jarvis...")
    try:
        mActivity.startActivityForResult(intent, REQUEST_CODE_SPEECH)
    except Exception:
        traceback.print_exc()
        _pending_callback = None
        on_result(None)


# ==================== TEXT TO SPEECH ====================

_tts_engine = None


def _get_android_tts():
    """Lazily creates Android's native TextToSpeech engine - used as a
    fallback if ElevenLabs isn't configured or a request to it fails."""
    global _tts_engine
    if _tts_engine is not None or not ANDROID_AVAILABLE:
        return _tts_engine
    try:
        TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
        _tts_engine = TextToSpeech(mActivity, None)
    except Exception:
        traceback.print_exc()
    return _tts_engine


def _speak_android_native(text: str):
    engine = _get_android_tts()
    if engine is None:
        return
    try:
        Locale = autoclass("java.util.Locale")
        engine.setLanguage(Locale.US)
        QUEUE_FLUSH = 0
        engine.speak(text, QUEUE_FLUSH, None, None)
        # Android's TTS speaks asynchronously with no easy "wait until
        # done" hook here, so we just estimate based on text length.
        time.sleep(min(8, 0.06 * len(text)))
    except Exception:
        traceback.print_exc()


def _speak_elevenlabs(text: str) -> bool:
    """Tries ElevenLabs. Returns True on success. Loading/playing the
    sound has to happen on Kivy's main thread (Kivy's audio system
    isn't safe to touch from a background thread), so this schedules
    that work via Clock and waits for it to finish."""
    key = getattr(config, "ELEVENLABS_API_KEY", "").strip()
    if not key:
        return False

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": getattr(config, "ELEVENLABS_MODEL", "eleven_flash_v2_5"),
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    tmp_path = os.path.join(tempfile.gettempdir(), "jarvis_speech.mp3")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return False

        with open(tmp_path, "wb") as f:
            f.write(response.content)

        from kivy.core.audio import SoundLoader
        from kivy.clock import Clock

        done = threading.Event()
        holder = {}

        def _load_and_play(dt):
            sound = SoundLoader.load(tmp_path)
            if not sound:
                done.set()
                return
            holder["sound"] = sound

            def _on_stop(instance):
                done.set()

            sound.bind(on_stop=_on_stop)
            sound.play()

        Clock.schedule_once(_load_and_play, 0)
        done.wait(timeout=30)
        return "sound" in holder
    except Exception:
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def speak(text: str):
    if not text:
        return
    if _speak_elevenlabs(text):
        return
    _speak_android_native(text)
