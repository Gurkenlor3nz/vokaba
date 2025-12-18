import os

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label

import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard


class AddStackMixin:
    """Create stack screen + validation + file creation."""

    def add_stack(self, _instance=None):
        self.reload_config()
        self.window.clear_widgets()
        log("opened add stack menu")

        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        input_h = self.get_textinput_height()

        # Top-right: back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(self.make_icon_button("assets/back_button.png", on_press=self.main_menu, size=dp(56)))
        self.window.add_widget(top_right)

        # Top-center: title
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=30 * pad_mul)
        top_center.add_widget(self.make_title_label(getattr(labels, "add_stack_title_text", "Stapel Hinzufügen"), size_hint=(None, None), size=(dp(300), dp(40))))
        self.window.add_widget(top_center)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.7), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        scroll = ScrollView(size_hint=(1, 1))
        form = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(8), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Stack filename
        form.add_widget(self.make_text_label(getattr(labels, "add_stack_filename", "Stapelname:"), size_hint_y=None, height=dp(24)))
        self.stack_input = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
        form.add_widget(self.stack_input)

        # Foreign language first
        form.add_widget(self.make_text_label(getattr(labels, "add_foreign_language", "Fremdsprache:"), size_hint_y=None, height=dp(24)))
        self.foreign_language_input = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
        form.add_widget(self.foreign_language_input)

        # Own language
        form.add_widget(self.make_text_label(getattr(labels, "add_own_language", "Eigene Sprache:"), size_hint_y=None, height=dp(24)))
        self.own_language_input = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
        form.add_widget(self.own_language_input)

        # Optional third column
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(10))
        row.add_widget(self.make_text_label(getattr(labels, "three_digit_toggle", "3-Spaltig:"), size_hint_y=None, height=dp(30)))
        self.three_columns = CheckBox(active=False, size_hint=(None, None), size=(dp(36), dp(36)))
        row.add_widget(self.three_columns)
        form.add_widget(row)

        # Create button
        btn = self.make_primary_button(getattr(labels, "add_stack_button_text", "Stapel Hinzufügen"), size_hint=(1, None), height=input_h)
        btn.bind(on_press=self.add_stack_button_func)
        form.add_widget(btn)

        # Inline error
        self.add_stack_error_label = self.make_title_label("", size_hint=(None, None), size=(dp(600), dp(40)))
        form.add_widget(self.add_stack_error_label)

        scroll.add_widget(form)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    def add_stack_button_func(self, _instance=None):
        stackname = (self.stack_input.text or "").strip()
        own_lang = (self.own_language_input.text or "").strip()
        foreign_lang = (self.foreign_language_input.text or "").strip()
        latin_active = bool(self.three_columns.active)

        if not (stackname and own_lang and foreign_lang):
            self.add_stack_error_label.text = getattr(labels, "add_stack_title_text_empty", "Fehler: Eine Box ist nicht ausgefüllt")
            return

        if not stackname.lower().endswith(".csv"):
            stackname += ".csv"

        filename = os.path.join(self.vocab_root(), stackname)

        if os.path.exists(filename):
            self.add_stack_error_label.text = getattr(labels, "add_stack_title_text_exists", "Fehler: Dieser Stapelnahme ist schon vergeben")
            return

        # Create empty stack + meta
        open(filename, "a", encoding="utf-8").close()
        save.save_to_vocab(
            vocab=[],
            filename=filename,
            own_lang=own_lang,
            foreign_lang=foreign_lang,
            latin_lang="Latein",
            latin_active=latin_active,
        )
        self.main_menu()
