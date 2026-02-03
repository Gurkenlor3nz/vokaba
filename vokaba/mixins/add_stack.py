import os
import shutil

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from vokaba.ui.widgets.vokaba_textinput import VokabaTextInput as TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
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
        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=[40 * pad_mul, 120 * pad_mul, 40 * pad_mul, 40 * pad_mul],
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.92, 0.82),
            padding=dp(16),
            spacing=dp(12),
            bg_color=self.colors["card"],
        )

        scroll = ScrollView(size_hint=(1, 1))
        form = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(8), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Stack filename
        form.add_widget(self.make_text_label(getattr(labels, "add_stack_filename", "Stapelname:"), size_hint_y=None, height=dp(24)))
        self.stack_input = self.style_textinput(TextInput(size_hint=(1, None), height=input_h, multiline=False))
        form.add_widget(self.stack_input)

        # Foreign language first (dropdown)
        form.add_widget(self.make_text_label(getattr(labels, "add_foreign_language", "Fremdsprache:"), size_hint_y=None, height=dp(24)))
        self.foreign_language_input = self.make_language_spinner(default="Englisch", size_hint=(1, None), height=input_h)
        form.add_widget(self.foreign_language_input)

        # Own language (dropdown)
        form.add_widget(self.make_text_label(getattr(labels, "add_own_language", "Eigene Sprache:"), size_hint_y=None, height=dp(24)))
        self.own_language_input = self.make_language_spinner(default="Deutsch", size_hint=(1, None), height=input_h)
        form.add_widget(self.own_language_input)

        # Optional third column
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(10))
        row.add_widget(self.make_text_label(getattr(labels, "third_column_digit_toggle", "3-Spaltig:"), size_hint_y=None, height=dp(30)))
        self.three_columns = CheckBox(active=False, size_hint=(None, None), size=(dp(36), dp(36)))
        row.add_widget(self.three_columns)
        form.add_widget(row)

        # Actions row (Import / Create) – hübsch, nicht nervig
        actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=input_h, spacing=dp(8))
        import_btn = self.make_secondary_button(getattr(labels, "stack_import_button_text", "Importieren …"), size_hint=(0.5, 1))
        create_btn = self.make_primary_button(getattr(labels, "add_stack_button_text", "Stapel Hinzufügen"), size_hint=(0.5, 1))
        import_btn.bind(on_press=self.import_stack_button_func)
        create_btn.bind(on_press=self.add_stack_button_func)
        actions.add_widget(import_btn)
        actions.add_widget(create_btn)
        form.add_widget(actions)

        # Inline error
        self.add_stack_error_label = self.make_title_label("", size_hint=(None, None), size=(dp(600), dp(40)))
        form.add_widget(self.add_stack_error_label)

        scroll.add_widget(form)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    def import_stack_button_func(self, _instance=None):
        """Importiert eine CSV als NEUEN Stapel in den lokalen vocab-Ordner."""
        from kivy.utils import platform as kivy_platform  # <-- wichtig (verhindert Android-crash)

        vocab_root = self.vocab_root()
        os.makedirs(vocab_root, exist_ok=True)

        def unique_dest(dest_path: str) -> str:
            base, ext = os.path.splitext(dest_path)
            i = 1
            candidate = dest_path
            while os.path.exists(candidate):
                candidate = f"{base}_import{i}{ext}"
                i += 1
            return candidate

        def do_import(src_raw: str):
            if not src_raw:
                return
            try:
                name = os.path.basename(str(src_raw))
                if not name.lower().endswith(".csv"):
                    name += ".csv"
                dest = unique_dest(os.path.join(vocab_root, name))

                ok = False
                if hasattr(self, "copy_any_to_file"):
                    ok = self.copy_any_to_file(src_raw, dest)
                else:
                    shutil.copy2(src_raw, dest)
                    ok = True

                if ok:
                    log(f"Imported stack: {src_raw} -> {dest}")
                    self.main_menu()
                else:
                    raise RuntimeError("copy failed")
            except Exception as e:
                log(f"Import failed: {e}")
                self.add_stack_error_label.text = getattr(labels, "import_failed", "Fehler beim Import")

        def on_sel(selection):
            if selection:
                do_import(selection[0])

        try:
            if hasattr(self, "run_open_file_dialog") and self.run_open_file_dialog(
                    on_sel, filters=["*.csv"], title="CSV importieren"
            ):
                return
        except Exception as e:
            log(f"System open dialog failed: {e}")

        if kivy_platform == "android":
            self.add_stack_error_label.text = (
                "Auf Android muss der System-Dateiauswahldialog aufgehen.\n"
                "Wenn nicht: 'plyer' fehlt im Build (requirements)."
            )
            return

        chooser = FileChooserIconView(path=os.path.expanduser("~"), dirselect=False, filters=["*.csv"])
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(chooser)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        cancel_btn = self.make_secondary_button(getattr(labels, "import_export_cancel", "Abbrechen"),
                                                size_hint=(0.5, 1))
        ok_btn = self.make_primary_button(getattr(labels, "stack_import_button_text", "Importieren …"),
                                          size_hint=(0.5, 1))
        row.add_widget(cancel_btn)
        row.add_widget(ok_btn)
        content.add_widget(row)

        popup = Popup(title="CSV importieren", content=content, size_hint=(0.9, 0.9))

        def _ok(*_a):
            if chooser.selection:
                do_import(chooser.selection[0])
            popup.dismiss()

        ok_btn.bind(on_press=_ok)
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        popup.open()


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