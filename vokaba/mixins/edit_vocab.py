import os

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard


class EditVocabMixin:
    """Bulk edit vocab grid + metadata editor."""

    def edit_vocab(self, stack: str, vocab: list, _instance=None):
        log("entered edit vocab")
        self.reload_config()
        self.window.clear_widgets()

        self.edit_vocab_original_list = vocab
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        # Top-right: back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(self.make_icon_button("assets/back_button.png", on_press=lambda _i: self.select_stack(stack), size=dp(56)))
        self.window.add_widget(top_right)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=80 * pad_mul)
        scroll = ScrollView(size_hint=(1, 1))
        card = RoundedCard(orientation="vertical", size_hint=(0.9, 0.85), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        layout = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(8), size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        latin_active = save.read_languages(self.vocab_root() + stack)[3]
        matrix = self.build_vocab_grid(layout, vocab, latin_active)

        input_h = self.get_textinput_height()
        save_btn = self.make_primary_button(getattr(labels, "save", "Speichern"), size_hint=(1, None), height=input_h)
        save_btn.bind(on_press=lambda _i, m=matrix: self.edit_vocab_func(m, stack))
        layout.add_widget(save_btn)

        scroll.add_widget(layout)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    def edit_vocab_func(self, matrix, stack: str, _instance=None):
        latin_active = save.read_languages(self.vocab_root() + stack)[3]
        vocab = self.read_vocab_from_grid(matrix, latin_active, getattr(self, "edit_vocab_original_list", None))
        save.save_to_vocab(vocab, self.vocab_root() + stack)
        self.select_stack(stack)

    def build_vocab_grid(self, parent_layout, vocab_list, latin_active: bool):
        cols = 4 if latin_active else 3
        grid = GridLayout(cols=cols, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter("height"))

        matrix = []
        input_h = self.get_textinput_height()

        for vocab in vocab_list:
            row = []

            for key in ["foreign_language", "own_language"]:
                ti = self.style_textinput(TextInput(text=vocab.get(key, ""), multiline=False, size_hint_y=None, height=input_h))
                grid.add_widget(ti)
                row.append(ti)

            if latin_active:
                ti = self.style_textinput(TextInput(text=vocab.get("latin_language", ""), multiline=False, size_hint_y=None, height=input_h))
                grid.add_widget(ti)
                row.append(ti)

            ti = self.style_textinput(TextInput(text=vocab.get("info", ""), multiline=False, size_hint_y=None, height=input_h))
            grid.add_widget(ti)
            row.append(ti)

            matrix.append(row)

        parent_layout.add_widget(grid)
        return matrix

    def read_vocab_from_grid(self, matrix, latin_active: bool, original_vocab_list=None):
        vocab_list = []
        for idx, row in enumerate(matrix):
            if latin_active:
                foreign, own, latin, info = [ti.text.strip() for ti in row]
            else:
                foreign, own, info = [ti.text.strip() for ti in row]
                latin = ""

            if not own and not foreign:
                continue
            if not own or not foreign:
                continue

            entry = {
                "own_language": own,
                "foreign_language": foreign,
                "latin_language": latin,
                "info": info,
            }

            if original_vocab_list is not None and idx < len(original_vocab_list):
                entry["knowledge_level"] = float(original_vocab_list[idx].get("knowledge_level", 0.0) or 0.0)
                entry["srs_streak"] = int(original_vocab_list[idx].get("srs_streak", 0) or 0)
                entry["srs_last_seen"] = (original_vocab_list[idx].get("srs_last_seen") or "")
                entry["srs_due"] = (original_vocab_list[idx].get("srs_due") or "")
            else:
                entry["knowledge_level"] = 0.0
                entry["srs_streak"] = 0
                entry["srs_last_seen"] = ""
                entry["srs_due"] = ""

            vocab_list.append(entry)

        return vocab_list

    # -------------------------
    # Metadata editing
    # -------------------------

    def edit_metadata(self, stack: str, _instance=None):
        log("entered edit metadata")
        self.reload_config()
        self.window.clear_widgets()

        meta = save.read_languages(self.vocab_root() + stack)
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        input_h = self.get_textinput_height()

        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(self.make_icon_button("assets/back_button.png", on_press=lambda _i: self.select_stack(stack), size=dp(56)))
        self.window.add_widget(top_right)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=80 * pad_mul)
        scroll = ScrollView(size_hint=(1, 1))
        card = RoundedCard(orientation="vertical", size_hint=(0.9, 0.85), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        layout = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(8), size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        layout.add_widget(self.make_title_label(getattr(labels, "add_foreign_language", "Fremdsprache:"), size_hint_y=None, height=dp(32)))
        self.edit_foreign_language_textbox = self.style_textinput(TextInput(text=meta[1] or "", multiline=False, size_hint=(1, None), height=input_h))
        layout.add_widget(self.edit_foreign_language_textbox)

        layout.add_widget(self.make_title_label(getattr(labels, "add_own_language", "Eigene Sprache:"), size_hint_y=None, height=dp(32)))
        self.edit_own_language_textbox = self.style_textinput(TextInput(text=meta[0] or "", multiline=False, size_hint=(1, None), height=input_h))
        layout.add_widget(self.edit_own_language_textbox)

        layout.add_widget(self.make_title_label(getattr(labels, "add_stack_filename", "Stapelname:"), size_hint_y=None, height=dp(32)))
        self.edit_name_textbox = self.style_textinput(TextInput(text=stack[:-4], multiline=False, size_hint=(1, None), height=input_h))
        layout.add_widget(self.edit_name_textbox)

        save_btn = self.make_primary_button(getattr(labels, "save", "Speichern"), size_hint=(1, None), height=input_h)
        save_btn.bind(on_press=lambda _i: self.edit_metadata_func(stack))
        layout.add_widget(save_btn)

        scroll.add_widget(layout)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    def edit_metadata_func(self, stack: str, _instance=None):
        filename = self.vocab_root() + stack
        latin_active = save.read_languages(filename)[3]

        save.change_languages(
            filename,
            self.edit_own_language_textbox.text,
            self.edit_foreign_language_textbox.text,
            "Latein",
            latin_active=latin_active,
        )

        new_name = (self.edit_name_textbox.text or "").strip()
        if not new_name.lower().endswith(".csv"):
            new_name += ".csv"

        new_path = self.vocab_root() + new_name
        if new_path != filename:
            os.rename(filename, new_path)

        self.select_stack(new_name)
