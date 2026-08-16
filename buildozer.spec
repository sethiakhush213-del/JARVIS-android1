[app]
title = Jarvis
package.name = jarvis
package.domain = org.khush.jarvis

source.dir = .
source.include_exts = py,json

version = 1.0
requirements = python3,kivy==2.3.0,requests,pyjnius,certifi

orientation = portrait
fullscreen = 0

# RECORD_AUDIO is needed for the voice input dialog; INTERNET for
# talking to OpenRouter/ElevenLabs/web search.
android.permissions = INTERNET,RECORD_AUDIO

android.api = 33
android.minapi = 21
android.archs = arm64-v8a

# Buildozer will download the Android SDK/NDK itself on first run -
# this just says "yes" to the license prompts automatically.
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
