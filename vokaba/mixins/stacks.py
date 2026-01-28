import os
import sys
import shutil
import subprocess
from datetime import datetime

from kivy.metrics import dp
from kivy.utils import platform as kivy_platform
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.uix.checkbox import CheckBox


import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard

try:
    from plyer import filechooser as plyer_filechooser
except Exception:
    plyer_filechooser = None

try:
    from plyer import share as plyer_share
except Exception:
    plyer_share = None



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

        self.recompute_available_modes()
        learn_btn = self.make_success_button(
            getattr(labels, "learn_stack_vocab_button_text", "Stapel lernen"),
            size_hint_y=None,
            height=dp(64),
        )
        learn_btn.bind(on_press=lambda _i: self.learn(stack=stack))
        grid.add_widget(learn_btn)

        add_btn = self.make_primary_button(
            getattr(labels, "add_vocab_button_text", "Vokabeln hinzufügen"),
            size_hint_y=None,
            height=dp(64),
        )
        add_btn.bind(on_press=lambda _i: self.add_vocab(stack, vocab_current))
        grid.add_widget(add_btn)

        edit_btn = self.make_secondary_button(
            getattr(labels, "edit_vocab_button_text", "Vokabeln bearbeiten"),
            size_hint_y=None,
            height=dp(64),
        )
        edit_btn.bind(on_press=lambda _i: self.edit_vocab(stack, vocab_current))
        grid.add_widget(edit_btn)

        export_btn = self.make_secondary_button(
            getattr(labels, "stack_export_button_text", "Exportieren …"),
            size_hint_y=None,
            height=dp(60),
        )
        export_btn.bind(on_press=lambda _i: self.export_stack_dialog(stack))
        grid.add_widget(export_btn)


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
        filename = os.path.abspath(os.path.join(self.vocab_root(), stack))

        try:
            os.remove(filename)
        except Exception as e:
            log(f"delete_stack failed: {e}")

        # purge in-memory autosave caches so it can't be re-created on exit
        try:
            if isinstance(getattr(self, "all_vocab_list", None), list) and isinstance(
                    getattr(self, "entry_to_stack_file", None), dict):
                ids_in_stack = {id(e) for e in self.all_vocab_list if self.entry_to_stack_file.get(id(e)) == filename}
                self.all_vocab_list = [e for e in self.all_vocab_list if id(e) not in ids_in_stack]
                for _id in ids_in_stack:
                    self.entry_to_stack_file.pop(_id, None)

            if isinstance(getattr(self, "stack_vocab_lists", None), dict):
                self.stack_vocab_lists.pop(filename, None)
            if isinstance(getattr(self, "stack_meta_map", None), dict):
                self.stack_meta_map.pop(filename, None)

            # also invalidate daily pool cache if it referenced this stack
            if getattr(self, "_daily_pool_stack_key", None) == filename:
                self._daily_pool_date = None
                self._daily_pool_stack_key = None
                self._daily_pool_total_vocab_count = None
        except Exception:
            pass

        self.main_menu()

    # --------------------
    # Import / export
    # --------------------

    def import_stack_dialog(self, stack: str, _instance=None):
        vocab_root = self.vocab_root()
        target = os.path.join(vocab_root, stack)

        def do_import(src_raw: str):
            if not src_raw:
                return
            src = src_raw

            # Backup
            try:
                if os.path.exists(target):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    shutil.copy2(target, target + f".backup_{ts}")
            except Exception:
                pass

            ok = False
            err = ""
            try:
                if hasattr(self, "copy_any_to_file"):
                    ok = bool(self.copy_any_to_file(src, target))
                else:
                    shutil.copy2(src, target)
                    ok = True
            except Exception as e:
                ok = False
                err = str(e)

            if ok:
                self.select_stack(stack)
            else:
                Popup(
                    title="Import fehlgeschlagen",
                    content=self.make_text_label(
                        "Die Datei konnte nicht importiert werden.\n\n"
                        f"Quelle: {src}\nZiel: {target}\n\n"
                        f"Fehler: {err or 'unbekannt'}",
                        halign="center",
                    ),
                    size_hint=(0.9, None),
                    height=dp(320),
                ).open()

        # 1) System-Dialog (Android Picker / Desktop Öffnen)
        def on_sel(selection):
            if selection:
                # sicher im Kivy-Thread ausführen
                Clock.schedule_once(lambda _dt: do_import(selection[0]), 0)

        try:
            if hasattr(self, "run_open_file_dialog") and self.run_open_file_dialog(
                    on_sel, filters=["*.csv"], title="CSV importieren"
            ):
                return
        except Exception as e:
            log(f"System open dialog failed: {e}")

        # Android: kein Kivy-Fallback
        if kivy_platform == "android":
            err = getattr(self, "_last_share_error", "") or ""
            Popup(
                title="Export fehlgeschlagen",
                content=self.make_text_label(
                    "Der Share-Dialog konnte nicht geöffnet werden.\n\n"
                    f"Details: {err or 'keine Details verfügbar'}\n\n"
                    "Check: Buildozer requirements: python3,kivy,pyjnius,plyer\n"
                    "Und ggf. FileProvider im Manifest.",
                    halign="center",
                ),
                size_hint=(0.85, None),
                height=dp(340),
            ).open()
            return

        # Desktop-Fallback: Kivy chooser
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

        popup = Popup(title=getattr(labels, "stack_import_popup_title", "CSV importieren"), content=content,
                      size_hint=(0.9, 0.9))

        def _ok(*_a):
            if chooser.selection:
                do_import(chooser.selection[0])
            popup.dismiss()

        ok_btn.bind(on_press=_ok)
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        popup.open()

        def _ok(*_a):
            if chooser.selection:
                do_import(chooser.selection[0])
            popup.dismiss()

        ok_btn.bind(on_press=_ok)
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        popup.open()


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

    def _write_export_csv(self, src: str, dest: str, *, include_progress: bool) -> bool:
        """
        Writes the export file.
        - include_progress=True  -> exact copy (current behavior)
        - include_progress=False -> reset learning fields in the EXPORT only:
                                   dates -> today, knowledge_level -> 0, streak -> 0
        """
        if not src or not dest:
            return False

        # Default / current behavior
        if include_progress:
            try:
                shutil.copy2(src, dest)
                return True
            except Exception as e:
                log(f"export copy failed: {e}")
                return False

        # "No progress" export: sanitize only the exported file
        try:
            vocab_list, own, foreign, latin, latin_active = save.load_vocab(src)
        except Exception as e:
            log(f"export load_vocab failed (fallback to copy): {e}")
            try:
                shutil.copy2(src, dest)
                return True
            except Exception:
                return False

        today = datetime.now().date().isoformat()

        cleaned = []
        for entry in (vocab_list or []):
            if not isinstance(entry, dict):
                continue

            row = dict(entry)  # do NOT mutate app data

            # Lernlevel / Fortschritt resetten (nur im Export)
            row["knowledge_level"] = 0.0
            row["srs_streak"] = 0

            # Alle Datumswerte auf "heute"
            row["srs_last_seen"] = today
            row["srs_due"] = today
            row["daily_goal_anchor_date"] = today

            # Optional: Anker resetten (steht im CSV-Schema)
            row["daily_goal_anchor"] = 0

            cleaned.append(row)

        try:
            save.save_to_vocab(
                cleaned,
                dest,
                own_lang=own or "Deutsch",
                foreign_lang=foreign or "Englisch",
                latin_lang=latin or "Latein",
                latin_active=bool(latin_active),
            )
            return True
        except Exception as e:
            log(f"export save_to_vocab failed (fallback to copy): {e}")
            try:
                shutil.copy2(src, dest)
                return True
            except Exception:
                return False

    def _write_sanitized_export_csv(self, src_path: str, dst_path: str) -> None:
        """
        Export ohne Lernstand:
          - knowledge_level = 0
          - SRS Felder/Anker auf "heute"
        """
        data = save.load_vocab(src_path)

        vocab_list = []
        own = "Deutsch"
        foreign = "Englisch"
        latin = "Latein"
        latin_active = False

        if isinstance(data, tuple):
            if len(data) == 5:
                vocab_list, own, foreign, latin, latin_active = data
            elif len(data) == 4:
                vocab_list, own, foreign, latin = data
            elif len(data) == 3:
                vocab_list, own, foreign = data
            elif len(data) >= 1:
                vocab_list = data[0]
        elif isinstance(data, dict):
            vocab_list = data.get("vocab_list", data.get("vocab", [])) or []
            own = data.get("own_language", own) or own
            foreign = data.get("foreign_language", foreign) or foreign
            latin = data.get("latin_language", latin) or latin
            latin_active = bool(data.get("latin_active", latin_active))
        else:
            vocab_list = data or []

        now = datetime.now()
        today_iso = now.date().isoformat()
        now_iso = now.isoformat()
        due_iso = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        for e in vocab_list:
            if not isinstance(e, dict):
                continue
            e["knowledge_level"] = 0.0
            e["srs_streak"] = 0
            e["srs_last_seen"] = now_iso
            e["srs_due"] = due_iso
            e["daily_goal_anchor"] = 0
            e["daily_goal_anchor_date"] = today_iso

        save.save_to_vocab(
            vocab=vocab_list,
            filename=dst_path,
            own_lang=own or "Deutsch",
            foreign_lang=foreign or "Englisch",
            latin_lang=latin or "Latein",
            latin_active=bool(latin_active),
        )

    def export_stack_dialog(self, stack: str, _instance=None):
        """
        Export / Share a stack CSV.

        - Erst Dialog: "Lernfortschritt mitexportieren?"
        - Wenn NEIN: knowledge_level -> 0 und Datumsfelder -> heute
        - Danach wie gehabt:
          - Android: share sheet
          - Desktop: save-as
        """
        # Resolve source file
        try:
            src = os.path.join(self.vocab_root(), stack)
            if hasattr(self, "_resolve_stack_file"):
                resolved = self._resolve_stack_file(stack)
                if resolved:
                    src = resolved
            src = os.path.abspath(src)
        except Exception:
            src = ""

        if not src or not os.path.isfile(src):
            Popup(
                title="Export fehlgeschlagen",
                content=self.make_text_label(
                    f"Datei nicht gefunden:\n{src or '(leer)'}",
                    halign="center",
                ),
                size_hint=(0.9, None),
                height=dp(240),
            ).open()
            return

        # ------------------------------------------------------------
        # 1) Optionen-Dialog (muss VOR dem Export kommen)
        # ------------------------------------------------------------
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))

        title_lbl = self.make_text_label(
            "Export-Optionen",
            halign="center",
            size_hint_y=None,
            height=dp(28),
        )
        title_lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        content.add_widget(title_lbl)

        hint_lbl = self.make_text_label(
            "Wenn du den Lernfortschritt nicht mitexportierst, wird die Datei so vorbereitet,\n"
            "dass sie wie „neu“ ist: alle Lernlevel = 0 und alle Datumsfelder = heute.",
            halign="center",
            size_hint_y=None,
            height=dp(90),
        )
        hint_lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        content.add_widget(hint_lbl)

        row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(44))
        cb = CheckBox(active=True, size_hint=(None, None), size=(dp(36), dp(36)))
        row.add_widget(cb)

        cb_lbl = self.make_text_label(
            "Lernfortschritt mitexportieren (Lernlevel & Wiederholungs-Status)",
            halign="left",
        )
        cb_lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        row.add_widget(cb_lbl)
        content.add_widget(row)

        btn_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(44))
        cancel_btn = self.make_secondary_button(getattr(labels, "cancel", "Abbrechen"), size_hint=(0.5, 1))
        ok_btn = self.make_primary_button("Export starten", size_hint=(0.5, 1))
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(ok_btn)
        content.add_widget(btn_row)

        popup = Popup(
            title="",
            content=content,
            size_hint=(0.92, None),
            height=dp(300),
        )

        def start_export(include_stats: bool):
            # --------------------------
            # ANDROID: share sheet
            # --------------------------
            if kivy_platform == "android":
                share_path = src

                # copy to a dedicated export dir (more predictable filename)
                try:
                    from pathlib import Path
                    from vokaba.core.paths import data_dir

                    export_dir = Path(data_dir()) / "exports"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    dst = export_dir / os.path.basename(src)

                    if include_stats:
                        shutil.copy2(src, str(dst))
                    else:
                        self._write_sanitized_export_csv(src, str(dst))

                    share_path = str(dst)
                except Exception as e:
                    log(f"export temp copy failed: {e}")
                    share_path = src  # fallback

                ok = False

                # 1) Prefer your Android Intent helper (FileProvider/text fallback)
                try:
                    if hasattr(self, "run_share_file_dialog"):
                        ok = bool(self.run_share_file_dialog(share_path, mime_type="text/csv", title="CSV teilen"))
                except Exception as e:
                    log(f"run_share_file_dialog failed: {e}")
                    ok = False

                # 2) plyer.share fallback
                if not ok and plyer_share is not None:
                    try:
                        try:
                            plyer_share.share(filepath=share_path, mime_type="text/csv", title="CSV teilen")
                        except TypeError:
                            plyer_share.share(filepath=share_path, title="CSV teilen")
                        ok = True
                    except Exception as e:
                        log(f"plyer_share failed: {e}")
                        ok = False

                if not ok:
                    err = getattr(self, "_last_share_error", "") or ""
                    Popup(
                        title="Export fehlgeschlagen",
                        content=self.make_text_label(
                            "Der Share-Dialog konnte nicht geöffnet werden.\n\n"
                            f"Datei: {share_path}\n\n"
                            f"Details: {err or 'keine Details verfügbar'}",
                            halign="center",
                        ),
                        size_hint=(0.9, None),
                        height=dp(340),
                    ).open()

                return

            # --------------------------
            # DESKTOP: save-as dialog
            # --------------------------
            def do_export(dest_path: str):
                if not dest_path:
                    return
                dest = str(dest_path)
                if not dest.lower().endswith(".csv"):
                    dest += ".csv"

                try:
                    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
                    if include_stats:
                        shutil.copy2(src, dest)
                    else:
                        self._write_sanitized_export_csv(src, dest)

                    Popup(
                        title="Export erfolgreich",
                        content=self.make_text_label(f"Exportiert nach:\n{dest}", halign="center"),
                        size_hint=(0.9, None),
                        height=dp(240),
                    ).open()
                except Exception as e:
                    Popup(
                        title="Export fehlgeschlagen",
                        content=self.make_text_label(
                            f"Konnte nicht exportieren.\n\nQuelle: {src}\nZiel: {dest}\n\nFehler: {e}",
                            halign="center",
                        ),
                        size_hint=(0.9, None),
                        height=dp(340),
                    ).open()

            def on_sel(selection):
                if selection:
                    Clock.schedule_once(lambda _dt: do_export(selection[0]), 0)

            # try system save dialog
            try:
                if hasattr(self, "run_save_file_dialog") and self.run_save_file_dialog(
                        on_sel, default_filename=os.path.basename(src), title="CSV exportieren"
                ):
                    return
            except Exception as e:
                log(f"System save dialog failed: {e}")

            # fallback: choose a folder and copy into it
            chooser = FileChooserIconView(path=os.path.expanduser("~"), dirselect=True)
            content2 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
            content2.add_widget(chooser)

            row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
            cancel_btn2 = self.make_secondary_button(getattr(labels, "cancel", "Abbrechen"), size_hint=(0.5, 1))
            ok_btn2 = self.make_primary_button("In Ordner exportieren", size_hint=(0.5, 1))
            row2.add_widget(cancel_btn2)
            row2.add_widget(ok_btn2)
            content2.add_widget(row2)

            popup2 = Popup(title="CSV exportieren", content=content2, size_hint=(0.9, 0.9))

            def _ok2(*_a):
                if chooser.selection:
                    folder = chooser.selection[0]
                    dest = os.path.join(folder, os.path.basename(src))
                    do_export(dest)
                popup2.dismiss()

            ok_btn2.bind(on_press=_ok2)
            cancel_btn2.bind(on_press=lambda *_a: popup2.dismiss())
            popup2.open()

        def _on_ok(*_a):
            include_stats = bool(cb.active)
            popup.dismiss()
            # wichtig: Export erst im nächsten Frame starten, damit der Dialog garantiert “vorher” sichtbar war
            Clock.schedule_once(lambda _dt: start_export(include_stats), 0)

        ok_btn.bind(on_press=_on_ok)
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
