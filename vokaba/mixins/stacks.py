import os
import sys
import shutil
import subprocess
from datetime import datetime

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard

try:
    from plyer import filechooser as plyer_filechooser
except Exception:
    plyer_filechooser = None


class StacksMixin:
    """Stack selection screen + import/export/delete helpers."""

    def select_stack(self, stack: str):
        log(f"opened stack: {stack}")
        self.reload_config()
        self.window.clear_widgets()

        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        vocab_file = os.path.join(self.vocab_root(), stack)
        data = save.load_vocab(vocab_file)
        vocab_current = data[0] if isinstance(data, tuple) else data

        # Top-center: stack title
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=15 * pad_mul)
        top_center.add_widget(self.make_title_label(stack[:-4], size_hint=(None, None), size=(dp(300), dp(40))))
        self.window.add_widget(top_center)

        # Top-right: back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        back_button = self.make_icon_button("assets/back_button.png", on_press=self.main_menu, size=dp(56))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=[30, 60, 100, 30])
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.7), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        add_btn = self.make_primary_button(getattr(labels, "add_vocab_button_text", "Vokabeln hinzufügen"), size_hint_y=None, height=dp(64))
        add_btn.bind(on_press=lambda _i: self.add_vocab(stack, vocab_current))
        grid.add_widget(add_btn)

        self.recompute_available_modes()
        learn_btn = self.make_primary_button(getattr(labels, "learn_stack_vocab_button_text", "Stapel lernen"), size_hint_y=None, height=dp(64))
        learn_btn.bind(on_press=lambda _i: self.learn(stack))
        grid.add_widget(learn_btn)

        edit_btn = self.make_secondary_button(getattr(labels, "edit_vocab_button_text", "Vokabeln bearbeiten"), size_hint_y=None, height=dp(60))
        edit_btn.bind(on_press=lambda _i, v=vocab_current: self.edit_vocab(stack, v))
        grid.add_widget(edit_btn)

        import_export = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(60), spacing=dp(8))
        import_btn = self.make_secondary_button(getattr(labels, "stack_import_button_text", "Importieren …"), size_hint=(0.5, 1))
        export_btn = self.make_secondary_button(getattr(labels, "stack_export_button_text", "Exportieren …"), size_hint=(0.5, 1))
        import_btn.bind(on_press=lambda _i: self.import_stack_dialog(stack))
        export_btn.bind(on_press=lambda _i: self.export_stack_dialog(stack))
        import_export.add_widget(import_btn)
        import_export.add_widget(export_btn)
        grid.add_widget(import_export)

        meta_btn = self.make_secondary_button(getattr(labels, "edit_metadata_button_text", "Metadaten Bearbeiten"), size_hint_y=None, height=dp(60))
        meta_btn.bind(on_press=lambda _i: self.edit_metadata(stack))
        grid.add_widget(meta_btn)

        del_btn = self.make_danger_button(getattr(labels, "delete_stack_button", "Stapel löschen"), size_hint_y=None, height=dp(60))
        del_btn.bind(on_press=lambda _i: self.delete_stack_confirmation(stack))
        grid.add_widget(del_btn)

        scroll.add_widget(grid)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    def delete_stack_confirmation(self, stack: str):
        log("Entered delete stack confirmation")
        self.window.clear_widgets()
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        back_button = self.make_icon_button("assets/back_button.png", on_press=lambda _i: self.select_stack(stack), size=dp(56))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.8, 0.6), padding=dp(16), spacing=dp(12), bg_color=(0.25, 0.10, 0.10, 1))

        caution = self.make_title_label(getattr(labels, "caution", "[color=ff0000]ACHTUNG[/color]"), size_hint_y=None, height=dp(40))
        caution.markup = True
        card.add_widget(caution)

        text = self.make_text_label(getattr(labels, "delete_stack_confirmation_text", "Sicher?"), size_hint_y=None, height=dp(60))
        text.markup = True
        card.add_widget(text)

        not_undone = self.make_text_label(getattr(labels, "cant_be_undone", "[color=ff0000]Nicht rückgängig![/color]"), size_hint_y=None, height=dp(40))
        not_undone.markup = True
        card.add_widget(not_undone)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(60), spacing=dp(12))
        cancel_btn = self.make_secondary_button(getattr(labels, "cancel", "Abbrechen"))
        cancel_btn.bind(on_press=lambda _i: self.select_stack(stack))
        delete_btn = self.make_danger_button(getattr(labels, "delete", "löschen"))
        delete_btn.bind(on_press=lambda _i: self.delete_stack(stack))

        row.add_widget(cancel_btn)
        row.add_widget(delete_btn)
        card.add_widget(row)

        center.add_widget(card)
        self.window.add_widget(center)

    def delete_stack(self, stack: str, _instance=None):
        try:
            os.remove(os.path.join(self.vocab_root(), stack))
        except Exception as e:
            log(f"delete_stack failed: {e}")
        self.main_menu()

    # --------------------
    # Import / export
    # --------------------

    def export_stack_dialog(self, stack: str, _instance=None):
        vocab_root = self.vocab_root()
        src = os.path.join(vocab_root, stack)

        chooser = FileChooserIconView(path=os.path.expanduser("~"), dirselect=True)
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(chooser)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        cancel_btn = self.make_secondary_button(getattr(labels, "import_export_cancel", "Abbrechen"), size_hint=(0.5, 1))
        ok_btn = self.make_primary_button(getattr(labels, "stack_export_button_text", "Exportieren …"), size_hint=(0.5, 1))
        row.add_widget(cancel_btn)
        row.add_widget(ok_btn)
        content.add_widget(row)

        popup = Popup(title=getattr(labels, "stack_export_popup_title", "Stapel exportieren"), content=content, size_hint=(0.9, 0.9))

        def do_export(*_a):
            target_dir = chooser.path
            if chooser.selection:
                sel = chooser.selection[0]
                target_dir = sel if os.path.isdir(sel) else os.path.dirname(sel)
            try:
                os.makedirs(target_dir, exist_ok=True)
                dest = os.path.join(target_dir, os.path.basename(stack))
                shutil.copy2(src, dest)
            except Exception as e:
                log(f"export failed: {e}")
            popup.dismiss()

        ok_btn.bind(on_press=do_export)
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        popup.open()

    def import_stack_dialog(self, stack: str, _instance=None):
        vocab_root = self.vocab_root()
        target = os.path.join(vocab_root, stack)

        # 1) System dialog (plyer) if available
        if plyer_filechooser is not None:
            def on_sel(selection):
                if not selection:
                    return
                src = selection[0]
                try:
                    if os.path.exists(target):
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        shutil.copy2(target, target + f".backup_{ts}")
                    shutil.copy2(src, target)
                    self.select_stack(stack)
                except Exception as e:
                    log(f"import (plyer) failed: {e}")

            try:
                plyer_filechooser.open_file(on_selection=on_sel, filters=["*.csv"])
                return
            except Exception as e:
                log(f"plyer dialog failed, fallback to kivy chooser: {e}")

        # 2) Fallback: Kivy chooser
        chooser = FileChooserIconView(path=os.path.expanduser("~"), dirselect=False, filters=["*.csv"])
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(chooser)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        cancel_btn = self.make_secondary_button(getattr(labels, "import_export_cancel", "Abbrechen"), size_hint=(0.5, 1))
        ok_btn = self.make_primary_button(getattr(labels, "stack_import_button_text", "Importieren …"), size_hint=(0.5, 1))
        row.add_widget(cancel_btn)
        row.add_widget(ok_btn)
        content.add_widget(row)

        popup = Popup(title=getattr(labels, "stack_import_popup_title", "CSV importieren"), content=content, size_hint=(0.9, 0.9))

        def do_import(*_a):
            if not chooser.selection:
                return
            src = chooser.selection[0]
            try:
                if os.path.exists(target):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    shutil.copy2(target, target + f".backup_{ts}")
                shutil.copy2(src, target)
                popup.dismiss()
                self.select_stack(stack)
            except Exception as e:
                log(f"import (kivy) failed: {e}")
                popup.dismiss()

        ok_btn.bind(on_press=do_import)
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        popup.open()

    # --------------------
    # Open folder helper
    # --------------------

    def open_stack_folder(self, stack: str, _instance=None):
        vocab_root = self.vocab_root()
        base_name = os.path.splitext(stack)[0]
        candidate = os.path.join(vocab_root, base_name)
        target = os.path.abspath(candidate if os.path.isdir(candidate) else vocab_root)

        try:
            if os.name == "nt":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as e:
            log(f"Could not open folder: {e}")
