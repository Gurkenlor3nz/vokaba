import os

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from vokaba.ui.widgets.vokaba_textinput import VokabaTextInput as TextInput
import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard


class EditVocabMixin:
    """Bulk edit vocab grid + metadata editor."""

    # -------------------------
    # Vocab grid editing
    # -------------------------

    def edit_vocab(self, stack: str, vocab: list, _instance=None):
        log("entered edit vocab")
        self.reload_config()
        self.window.clear_widgets()

        self._edit_vocab_stack = stack
        self.edit_vocab_original_list = vocab
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        # Top-center: stack title (außerhalb der Card)
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=15 * pad_mul)
        top_center.add_widget(self.make_title_label(stack[:-4], size_hint=(None, None), size=(dp(300), dp(40))))
        self.window.add_widget(top_center)

        # Top-right: back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(
            self.make_icon_button("assets/back_button.png", on_press=lambda _i: self.select_stack(stack), size=dp(56))
        )
        self.window.add_widget(top_right)

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=[40 * pad_mul, 120 * pad_mul, 40 * pad_mul, 40 * pad_mul],
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.95, 0.82),
            padding=dp(16),
            spacing=dp(12),
            bg_color=self.colors["card"],
        )

        latin_active = bool(save.read_languages(self.vocab_root() + stack)[3])
        self._edit_vocab_latin_active = latin_active

        # Scroll: nur die Tabelle
        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(8), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        matrix = self.build_vocab_grid(content, vocab, latin_active)
        self._edit_vocab_matrix = matrix

        scroll.add_widget(content)
        card.add_widget(scroll)

        # Save Button: FIX unten (außerhalb vom Scroll)
        input_h = self.get_textinput_height()
        save_btn = self.make_primary_button(getattr(labels, "save", "Speichern"), size_hint=(1, None), height=input_h)
        save_btn.bind(on_press=lambda _i, m=matrix: self.edit_vocab_func(m, stack))
        card.add_widget(save_btn)

        center.add_widget(card)
        self.window.add_widget(center)

    def _read_vocab_from_grid_unfiltered(self, matrix, latin_active: bool, original_vocab_list=None):
        """
        Wie read_vocab_from_grid, aber:
          - KEIN Filtern (auch leere/unvollständige Reihen bleiben)
          - damit Delete/Rebuild keine halben Edits wegwirft.
        """
        original_vocab_list = original_vocab_list or []
        vocab_list = []

        for idx, row in enumerate(matrix):
            if latin_active:
                foreign, own, latin, info = [ti.text for ti in row]
            else:
                foreign, own, info = [ti.text for ti in row]
                latin = ""

            entry = {
                "own_language": own,
                "foreign_language": foreign,
                "latin_language": latin,
                "info": info,
            }

            if idx < len(original_vocab_list):
                src = original_vocab_list[idx] or {}
                entry["knowledge_level"] = float(src.get("knowledge_level", 0.0) or 0.0)
                entry["srs_streak"] = int(src.get("srs_streak", 0) or 0)
                entry["srs_last_seen"] = (src.get("srs_last_seen") or "")
                entry["srs_due"] = (src.get("srs_due") or "")
            else:
                entry["knowledge_level"] = 0.0
                entry["srs_streak"] = 0
                entry["srs_last_seen"] = ""
                entry["srs_due"] = ""

            vocab_list.append(entry)

        return vocab_list

    def _edit_vocab_delete_row(self, row_index: int, _instance=None):
        """
        Löscht eine Zeile sofort aus der UI (rebuild), ohne die restlichen Edits zu verlieren.
        """
        stack = getattr(self, "_edit_vocab_stack", None)
        matrix = getattr(self, "_edit_vocab_matrix", None)
        latin_active = bool(getattr(self, "_edit_vocab_latin_active", False))
        original = getattr(self, "edit_vocab_original_list", None)

        if not stack or matrix is None:
            return

        current = self._read_vocab_from_grid_unfiltered(matrix, latin_active, original_vocab_list=original)
        if 0 <= row_index < len(current):
            current.pop(row_index)

        # rebuild screen with updated list
        self.edit_vocab(stack, current)

    def edit_vocab_func(self, matrix, stack: str, _instance=None):
        latin_active = save.read_languages(self.vocab_root() + stack)[3]
        vocab = self.read_vocab_from_grid(matrix, latin_active, getattr(self, "edit_vocab_original_list", None))
        save.save_to_vocab(vocab, self.vocab_root() + stack)
        self.select_stack(stack)

    def build_vocab_grid(self, parent_layout, vocab_list, latin_active: bool):
        """
        Grid + extra delete column (assets/delete.png).
        """
        base_cols = 4 if latin_active else 3
        cols = base_cols + 1  # + delete icon column

        grid = GridLayout(cols=cols, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter("height"))

        matrix = []
        input_h = self.get_textinput_height()

        for row_index, vocab in enumerate(vocab_list):
            row = []

            for key in ["foreign_language", "own_language"]:
                ti = self.style_textinput(
                    TextInput(text=vocab.get(key, ""), multiline=False, size_hint_y=None, height=input_h)
                )
                grid.add_widget(ti)
                row.append(ti)

            if latin_active:
                ti = self.style_textinput(
                    TextInput(text=vocab.get("latin_language", ""), multiline=False, size_hint_y=None, height=input_h)
                )
                grid.add_widget(ti)
                row.append(ti)

            ti = self.style_textinput(
                TextInput(text=vocab.get("info", ""), multiline=False, size_hint_y=None, height=input_h)
            )
            grid.add_widget(ti)
            row.append(ti)

            # Delete icon button
            del_btn = self.make_icon_button(
                "assets/delete.png",
                on_press=lambda _i, idx=row_index: self._edit_vocab_delete_row(idx),
                size=dp(44),
            )
            grid.add_widget(del_btn)

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

        # Top-center: stack title (außerhalb der Card)
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=15 * pad_mul)
        top_center.add_widget(self.make_title_label(stack[:-4], size_hint=(None, None), size=(dp(300), dp(40))))
        self.window.add_widget(top_center)

        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(
            self.make_icon_button("assets/back_button.png", on_press=lambda _i: self.select_stack(stack), size=dp(56))
        )
        self.window.add_widget(top_right)

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=[40 * pad_mul, 120 * pad_mul, 40 * pad_mul, 40 * pad_mul],
        )

        card = RoundedCard(orientation="vertical", size_hint=(0.95, 0.75), padding=dp(16), spacing=dp(12),
                           bg_color=self.colors["card"])

        scroll = ScrollView(size_hint=(1, 1))
        layout = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(8), size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        self.edit_foreign_language_textbox = self.make_language_spinner(
            default=(meta[1] or "Englisch"),
            size_hint=(1, None),
            height=input_h,
        )
        layout.add_widget(self.edit_foreign_language_textbox)

        self.edit_own_language_textbox = self.make_language_spinner(
            default=(meta[0] or "Deutsch"),
            size_hint=(1, None),
            height=input_h,
        )
        layout.add_widget(self.edit_own_language_textbox)

        layout.add_widget(self.make_title_label(getattr(labels, "add_stack_filename", "Stapelname:"), size_hint_y=None,
                                                height=dp(32)))
        self.edit_name_textbox = self.style_textinput(
            TextInput(text=stack[:-4], multiline=False, size_hint=(1, None), height=input_h)
        )
        layout.add_widget(self.edit_name_textbox)

        save_btn = self.make_primary_button(getattr(labels, "save", "Speichern"), size_hint=(1, None), height=input_h)
        save_btn.bind(on_press=lambda _i: self.edit_metadata_func(stack))
        layout.add_widget(save_btn)

        scroll.add_widget(layout)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)


    def edit_metadata_func(self, stack: str, _instance=None):
        old_path = self.vocab_root() + stack

        # aktuelle Meta lesen (damit latin_* gleich bleibt)
        own_old, foreign_old, latin_lang, latin_active = save.read_languages(old_path)

        # neue Werte aus UI
        own = (getattr(self.edit_own_language_textbox, "text", None) or own_old or "Deutsch").strip()
        foreign = (getattr(self.edit_foreign_language_textbox, "text", None) or foreign_old or "Englisch").strip()

        new_name = (self.edit_name_textbox.text or "").strip()
        if not new_name:
            new_name = stack[:-4]

        new_stack = new_name if new_name.endswith(".csv") else (new_name + ".csv")
        new_path = self.vocab_root() + new_stack

        # ggf. Datei umbenennen
        if new_stack != stack:
            if os.path.exists(new_path):
                log(f"Cannot rename: target exists: {new_stack}")
                return
            os.rename(old_path, new_path)
            stack = new_stack
            old_path = new_path

        # Meta speichern (ohne Vokabeln anzufassen)
        save.change_languages(
            old_path,
            new_own=own,
            new_foreign=foreign,
            new_latin=latin_lang or "",
            latin_active=bool(latin_active),
        )

        self.select_stack(stack)