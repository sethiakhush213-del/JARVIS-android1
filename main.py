"""
main.py
-------
The Jarvis app itself. Run this file (through buildozer, on Android)
to launch it. See BUILD_INSTRUCTIONS.txt for how to actually turn this
into an installable .apk.
"""

import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

import config
import memory
import notes
import reminders
import android_voice
from brain import Jarvis

STATE_COLORS = {
    "idle": "#00d4ff",
    "listening": "#ff5c33",
    "thinking": "#ffd23f",
    "speaking": "#3dffb0",
}


class JarvisApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex("#03080f")

        # Android apps can only write to their own private storage
        # folder - point our storage modules at it before anything
        # else touches memory/notes/reminders.
        memory.set_data_dir(self.user_data_dir)
        notes.set_data_dir(self.user_data_dir)
        reminders.set_data_dir(self.user_data_dir)

        self.state = "idle"
        try:
            self.jarvis = Jarvis()
            self.jarvis_error = None
        except ValueError as e:
            self.jarvis = None
            self.jarvis_error = str(e)

        root = BoxLayout(orientation="vertical", padding=14, spacing=10)

        self.status_label = Label(
            text="IDLE", size_hint=(1, 0.07),
            color=get_color_from_hex(STATE_COLORS["idle"]),
            font_size="16sp", bold=True,
        )
        root.add_widget(self.status_label)

        self.log_layout = GridLayout(cols=1, size_hint_y=None, spacing=10, padding=6)
        self.log_layout.bind(minimum_height=self.log_layout.setter("height"))
        self.scroll = ScrollView(size_hint=(1, 0.75))
        self.scroll.add_widget(self.log_layout)
        root.add_widget(self.scroll)

        input_row = BoxLayout(size_hint=(1, 0.1), spacing=8)
        self.text_input = TextInput(multiline=False, hint_text="Message Jarvis...")
        self.text_input.bind(on_text_validate=self._on_send)
        send_btn = Button(
            text="Send", size_hint=(0.28, 1),
            background_color=get_color_from_hex(STATE_COLORS["idle"]),
        )
        send_btn.bind(on_release=self._on_send)
        mic_btn = Button(
            text="Talk", size_hint=(0.28, 1),
            background_color=get_color_from_hex(STATE_COLORS["listening"]),
        )
        mic_btn.bind(on_release=self._on_mic)
        input_row.add_widget(self.text_input)
        input_row.add_widget(send_btn)
        input_row.add_widget(mic_btn)
        root.add_widget(input_row)

        Clock.schedule_interval(self._check_reminders, 15)
        Clock.schedule_once(lambda dt: self._say_and_display("Jarvis", config.GREETING), 1)

        return root

    # ---------------- LOG ----------------
    def _add_entry(self, speaker, text):
        color = "#ffffff" if speaker == "You" else STATE_COLORS["idle"]
        lbl = Label(
            text=f"[b][color={color}]{speaker}:[/color][/b] {text}",
            markup=True, size_hint_y=None, halign="left", valign="top",
            text_size=(Window.width - 40, None),
        )
        lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        self.log_layout.add_widget(lbl)
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.1)

    def _set_state(self, state):
        self.state = state
        self.status_label.text = state.upper()
        self.status_label.color = get_color_from_hex(STATE_COLORS[state])

    # ---------------- SEND / CHAT ----------------
    def _on_send(self, *args):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""
        self._handle_user_message(text)

    def _handle_user_message(self, text):
        self._add_entry("You", text)

        note_result = notes.try_handle(text)
        if note_result:
            self._say_and_display("Jarvis", note_result)
            return

        reminder_result = reminders.try_handle(text)
        if reminder_result:
            self._say_and_display("Jarvis", reminder_result)
            return

        if text.lower() in ("forget everything", "forget everything you know", "clear your memory", "clear memory"):
            if self.jarvis:
                self.jarvis.forget_everything()
            self._say_and_display("Jarvis", "Done, memory's wiped. Clean slate.")
            return

        if not self.jarvis:
            self._add_entry("Jarvis", f"I'm not connected - {self.jarvis_error}")
            return

        threading.Thread(target=self._think_thread, args=(text,), daemon=True).start()

    def _think_thread(self, text):
        Clock.schedule_once(lambda dt: self._set_state("thinking"), 0)
        try:
            reply = self.jarvis.ask(text)
        except Exception as e:
            reply = f"I ran into an error: {e}"
        Clock.schedule_once(lambda dt: self._say_and_display("Jarvis", reply), 0)

    def _say_and_display(self, speaker, text):
        self._add_entry(speaker, text)
        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()

    def _speak_thread(self, text):
        Clock.schedule_once(lambda dt: self._set_state("speaking"), 0)
        android_voice.speak(text)
        Clock.schedule_once(lambda dt: self._set_state("idle"), 0)

    # ---------------- MIC ----------------
    def _on_mic(self, *args):
        self._set_state("listening")
        android_voice.listen(on_result=self._on_heard)

    def _on_heard(self, heard_text):
        Clock.schedule_once(lambda dt: self._after_heard(heard_text), 0)

    def _after_heard(self, heard_text):
        self._set_state("idle")
        if heard_text:
            self._handle_user_message(heard_text)
        else:
            self._add_entry("Jarvis", "Didn't catch that - try again?")

    # ---------------- REMINDERS ----------------
    def _check_reminders(self, dt):
        for msg in reminders.get_due():
            self._say_and_display("Jarvis", f"Reminder: {msg}.")


if __name__ == "__main__":
    JarvisApp().run()
