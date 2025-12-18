from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard


class AddVocabMixin:
    """Add single vocab entry screen + keyboard navigation."""

    def _unbind_add_vocab_keys(self):
        try:
            Window.unbind(on_key_down=self.on_key_down)
        except Exception:
            pass

    def _on_add_vocab_back(self, _instance=None):
        self._unbind_add_vocab_keys()
        stack = getattr(self, "_add_vocab_stack", None)
        if stack:
            self.select_stack(stack)
        else:
            self.main_menu()

    def add_vocab(self, stack: str, vocab_list: list, _instance=None):
        log("entered add vocab")
        self.reload_config()
        self.window.clear_widgets()

        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        input_h = self.get_textinput_height()
        self._add_vocab_stack = stack

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=[40 * pad_mul, 120 * pad_mul, 40 * pad_mul, 40 * pad_mul])
        scroll = ScrollView(size_hint=(1, 1))

        card = RoundedCard(orientation="vertical", size_hint=(0.9, 0.85), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])
        form = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(8), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Foreign first
        form.add_widget(self.make_title_label(getattr(labels, "add_foreign_language", "Fremdsprache:"), size_hint_y=None, height=dp(32)))
        self.add_foreign_language = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
        form.add_widget(self.add_foreign_language)

        # Own
        form.add_widget(self.make_title_label(getattr(labels, "add_own_language", "Eigene Sprache:"), size_hint_y=None, height=dp(32)))
        self.add_own_language = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
        form.add_widget(self.add_own_language)

        # Optional third
        self.third_column_input = None
        latin_active = save.read_languages(self.vocab_root() + stack)[3]
        if latin_active:
            form.add_widget(self.make_title_label(getattr(labels, "add_third_column", "Dritte Spalte:"), size_hint_y=None, height=dp(32)))
            self.third_column_input = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
            form.add_widget(self.third_column_input)

        # Info
        form.add_widget(self.make_title_label(getattr(labels, "add_additional_info", "Mehr Infos:"), size_hint_y=None, height=dp(32)))
        self.add_additional_info = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
        form.add_widget(self.add_additional_info)

        # Accent bar
        form.add_widget(self.make_text_label("Akzent-Hilfe (Tippen zum Einfügen):", size_hint_y=None, height=dp(24)))
        form.add_widget(self.create_accent_bar())

        # Inline error
        self.add_vocab_error_label = Label(text="", color=self.colors["danger"], font_size=int(self.config_data["settings"]["gui"]["text_font_size"]), size_hint_y=None, height=dp(26))
        self.add_vocab_error_label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        form.add_widget(self.add_vocab_error_label)

        # Add button
        self.add_vocab_button = self.make_primary_button(getattr(labels, "add_vocabulary_button_text", "Vokabel Hinzufügen"), size_hint=(1, None), height=input_h)
        self.add_vocab_button.bind(on_press=lambda _i: self.add_vocab_button_func(vocab_list, stack))
        form.add_widget(self.add_vocab_button)

        # Keyboard navigation list
        if self.third_column_input:
            self.widgets_add_vocab = [self.add_foreign_language, self.add_own_language, self.third_column_input, self.add_additional_info, self.add_vocab_button]
        else:
            self.widgets_add_vocab = [self.add_foreign_language, self.add_own_language, self.add_additional_info, self.add_vocab_button]
        self.add_vocab_button_widget = self.add_vocab_button

        Window.bind(on_key_down=self.on_key_down)

        scroll.add_widget(form)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

        # Back button (top-right)
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(self.make_icon_button("assets/back_button.png", on_press=self._on_add_vocab_back, size=dp(56)))
        self.window.add_widget(top_right)

        Clock.schedule_once(lambda _dt: setattr(self.add_foreign_language, "focus", True), 0.05)

    def clear_inputs(self):
        self.add_foreign_language.text = ""
        self.add_own_language.text = ""
        if self.third_column_input is not None:
            self.third_column_input.text = ""
        self.add_additional_info.text = ""

        def _refocus(_dt):
            self.add_foreign_language.focus = True
            self.current_focus_input = self.add_foreign_language

        Clock.schedule_once(_refocus, 0)

    def add_vocab_button_func(self, vocab_list: list, stack: str, _instance=None):
        own = (self.add_own_language.text or "").strip()
        foreign = (self.add_foreign_language.text or "").strip()
        third = (self.third_column_input.text or "").strip() if self.third_column_input else ""
        info = (self.add_additional_info.text or "").strip()

        if not own or not foreign:
            msg = getattr(labels, "add_vocab_both_languages_required", "Bitte fülle beide Sprachfelder aus.")
            self.add_vocab_error_label.text = msg
            return

        vocab_list.append({
            "own_language": own,
            "foreign_language": foreign,
            "latin_language": third,
            "info": info,
            "knowledge_level": 0.0,
        })

        save.save_to_vocab(vocab_list, self.vocab_root() + stack)
        self.add_vocab_error_label.text = ""
        self.clear_inputs()

    # ------------------------
    # Keyboard navigation
    # ------------------------

    def on_key_down(self, _window, key, _scancode, _codepoint, modifiers):
        """
        Add-vocab keyboard navigation:
          - Tab / Shift+Tab: move focus
          - Enter: trigger add button (from a TextInput)
          - ESC / Android back: return to stack
        """
        if not hasattr(self, "widgets_add_vocab") or not self.widgets_add_vocab:
            return False

        # ESC/back
        if key == 27:
            stack = getattr(self, "_add_vocab_stack", None)
            if stack:
                self._unbind_add_vocab_keys()
                self.select_stack(stack)
                return True
            return False

        if key not in (9, 13):
            return False

        focused = None
        for i, w in enumerate(self.widgets_add_vocab):
            if getattr(w, "focus", False):
                focused = i
                break

        if focused is None:
            for w in self.widgets_add_vocab:
                if hasattr(w, "focus"):
                    w.focus = True
                    break
            return True

        if key == 9:
            if "shift" in modifiers:
                nxt = (focused - 1) % len(self.widgets_add_vocab)
            else:
                nxt = (focused + 1) % len(self.widgets_add_vocab)
            self.widgets_add_vocab[nxt].focus = True
            return True

        if key == 13:
            cur = self.widgets_add_vocab[focused]
            if isinstance(cur, TextInput):
                btn = getattr(self, "add_vocab_button_widget", None)
                if btn is not None:
                    btn.trigger_action(duration=0.1)
            return True

        return False
