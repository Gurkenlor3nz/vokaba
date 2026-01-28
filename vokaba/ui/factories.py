import os
import shutil
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform as kivy_platform
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner

from vokaba.ui.widgets.rounded import RoundedButton
from vokaba.theme.theme_manager import get_icon_path

try:
    from plyer import filechooser as plyer_filechooser
except Exception:
    plyer_filechooser = None

try:
    from plyer import share as plyer_share
except Exception:
    plyer_share = None


class UIFactoryMixin:
    """
    Shared UI factories. Uses:
      self.config_data (dict)
      self.colors (dict)
      self.current_focus_input (TextInput|None)
    """

    def cfg_int(self, path, default=0) -> int:
        ref = self.config_data
        for k in path:
            if not isinstance(ref, dict) or k not in ref:
                return int(default)
            ref = ref[k]
        try:
            return int(ref)
        except Exception:
            return int(default)

    def cfg_float(self, path, default=0.0) -> float:
        ref = self.config_data
        for k in path:
            if not isinstance(ref, dict) or k not in ref:
                return float(default)
            ref = ref[k]
        try:
            return float(ref)
        except Exception:
            return float(default)

    def make_title_label(self, text, **kwargs):
        # Kivy expects px internally; use sp() so text scales correctly on high/low DPI devices.
        font_size = kwargs.pop("font_size", sp(self.cfg_int(["settings", "gui", "title_font_size"], 32)))
        lbl = Label(
            text=text,
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )
        lbl.halign = kwargs.get("halign", "center")
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_text_label(self, text, **kwargs):
        font_size = kwargs.pop("font_size", sp(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        lbl = Label(
            text=text,
            color=self.colors["muted"],
            font_size=font_size,
            **kwargs,
        )
        lbl.halign = kwargs.get("halign", "left")
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_primary_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", sp(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return RoundedButton(
            text=text,
            bg_color=self.colors["primary"],
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_success_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", sp(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return RoundedButton(
            text=text,
            bg_color=self.colors["success"],
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_secondary_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", sp(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return RoundedButton(
            text=text,
            # statt "card" -> "card_selected" (wie in der CSV-Liste)
            bg_color=self.colors.get("card_selected", self.colors["card"]),
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_danger_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", sp(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return RoundedButton(
            text=text,
            bg_color=self.colors["danger"],
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_list_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", sp(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        btn = RoundedButton(
            text=text,
            bg_color=self.colors["card_selected"],
            color=self.colors["text"],
            font_size=font_size,
            size_hint_y=None,
            height=dp(50),
            radius=dp(25),
            **kwargs,
        )
        btn.halign = "left"
        btn.valign = "middle"
        btn.padding = (dp(16), 0)

        def _update_text_size(inst, size):
            inst.text_size = (size[0] - dp(32), None)

        btn.bind(size=_update_text_size)
        return btn

    def make_icon_button(self, icon_path, on_press, size=dp(56), **kwargs):
        icon_path = get_icon_path(self.config_data, icon_path)
        btn = Button(
            size_hint=(None, None),
            size=(size, size),
            background_normal=icon_path,
            background_down=icon_path,
            border=(0, 0, 0, 0),
            **kwargs,
        )
        btn.bind(on_press=on_press)
        return btn

    def style_textinput(self, ti: TextInput) -> TextInput:
        ti.background_normal = ""
        ti.background_active = ""
        ti.background_color = self.colors.get("card_selected", self.colors["card"])
        ti.foreground_color = self.colors["text"]
        ti.cursor_color = self.colors["accent"]
        ti.padding = [dp(12), dp(10), dp(12), dp(10)]
        ti.font_size = sp(self.cfg_int(["settings", "gui", "text_font_size"], 18))

        # Single-line: NICHT mehr automatisch zentrieren.
        # Wenn der Caller explizit halign="center" setzt (z.B. Zahlenfelder), bleibt es center.
        if not getattr(ti, "multiline", False):
            try:
                desired = str(getattr(ti, "halign", "auto")).lower()
                if desired not in ("center", "right"):
                    ti.halign = "left"
                ti.valign = "middle"

                def _update_text_size(_inst, size):
                    ti.text_size = (max(0, size[0] - dp(24)), None)

                ti.bind(size=_update_text_size)
                _update_text_size(ti, ti.size)
            except Exception:
                pass

        def _on_focus(instance, value):
            if value:
                self.current_focus_input = instance
            else:
                if getattr(self, "current_focus_input", None) is instance:
                    self.current_focus_input = None

        ti.bind(focus=_on_focus)
        return ti

    def force_focus(self, ti: TextInput, delays=(0, 0.15, 0.35)):
        # Android/Tablets: manchmal braucht es mehrere Fokus-“Ticks”
        if ti is None:
            return

        def _set(_dt):
            try:
                ti.focus = True
                self.current_focus_input = ti
            except Exception:
                pass

        for d in delays:
            Clock.schedule_once(_set, d)

    def get_textinput_height(self) -> float:
        # ~1 line + padding. Uses sp() so the height stays usable across DPI classes.
        fs = float(sp(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return max(dp(48), fs * 1.55 + dp(22))

    def is_portrait(self) -> bool:
        try:
            w, h = Window.size
        except Exception:
            return False
        return h > w

    # ----------------------------
    # Language helpers (dropdown)
    # ----------------------------

    def get_common_learning_languages(self):
        """
        Übliche Lernsprachen in Deutschland + relativ TTS-freundlich (offline eher verfügbar).
        Nicht zu viele, bewusst kompakt.
        """
        return [
            "Deutsch",
            "Englisch",
            "Französisch",
            "Spanisch",
            "Italienisch",
            "Türkisch",
            "Arabisch",
            "Russisch",
            "Polnisch",
            "Niederländisch",
        ]

    def style_spinner(self, spn: Spinner) -> Spinner:
        # Spinner ist intern ein Button
        spn.background_normal = ""
        spn.background_down = ""
        spn.background_color = self.colors.get("card_selected", self.colors.get("card", (0, 0, 0, 1)))
        spn.color = self.colors.get("text", (1, 1, 1, 1))
        spn.font_size = sp(self.cfg_int(["settings", "gui", "text_font_size"], 18))
        spn.halign = "center"
        spn.valign = "middle"
        spn.padding = [dp(10), dp(10)]

        # WICHTIG: text_size dynamisch an echte Widget-Breite binden (sonst Wrap bei Resize)
        def _update_text_size(_inst, size):
            spn.text_size = (max(0, size[0] - dp(20)), None)

        spn.bind(size=_update_text_size)
        _update_text_size(spn, spn.size)

        return spn

    def make_language_spinner(self, default: str = "Deutsch", *, allow_custom: bool = True, **kwargs) -> Spinner:
        values = list(self.get_common_learning_languages())
        other_label = "Andere…"
        if allow_custom and other_label not in values:
            values.append(other_label)

        spn = Spinner(text=default or "Deutsch", values=values, **kwargs)
        self.style_spinner(spn)

        if allow_custom:
            state = {"prev": spn.text}

            def _open_custom_popup():
                content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
                ti = self.style_textinput(
                    TextInput(text="", multiline=False, size_hint_y=None, height=self.get_textinput_height())
                )
                content.add_widget(ti)

                row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(44))
                cancel_btn = self.make_secondary_button("Abbrechen", size_hint=(0.5, 1))
                ok_btn = self.make_primary_button("OK", size_hint=(0.5, 1))
                row.add_widget(cancel_btn)
                row.add_widget(ok_btn)
                content.add_widget(row)

                popup = Popup(title="Sprache eingeben", content=content, size_hint=(0.85, None), height=dp(220))

                def _cancel(*_a):
                    spn.text = state["prev"]
                    popup.dismiss()

                def _ok(*_a):
                    val = (ti.text or "").strip()
                    if val:
                        spn.text = val
                        state["prev"] = val
                    else:
                        spn.text = state["prev"]
                    popup.dismiss()

                cancel_btn.bind(on_press=_cancel)
                ok_btn.bind(on_press=_ok)

                popup.open()
                Clock.schedule_once(lambda _dt: setattr(ti, "focus", True), 0.05)

            def _on_text(_inst, value):
                if value == other_label:
                    # Spinner nicht auf "Andere…" stehen lassen
                    spn.text = state["prev"]
                    _open_custom_popup()
                else:
                    state["prev"] = value

            spn.bind(text=_on_text)

        return spn

    # ----------------------------
    # System file dialogs (Import/Export)
    # ----------------------------

    def _tk_dialogs(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception:
            return None, None

        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
        except Exception:
            return None, None

        return root, filedialog

    def desktop_open_file_dialog(self, *, title="Datei öffnen", filetypes=None, initialdir=None):
        root, filedialog = self._tk_dialogs()
        if root is None:
            return None
        try:
            path = filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=initialdir)
            return path or None
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    def desktop_save_file_dialog(self, *, title="Speichern unter", filetypes=None, initialdir=None, initialfile=None):
        root, filedialog = self._tk_dialogs()
        if root is None:
            return None
        try:
            path = filedialog.asksaveasfilename(
                title=title,
                filetypes=filetypes,
                initialdir=initialdir,
                initialfile=initialfile,
                defaultextension=".csv",
            )
            return path or None
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    def run_open_file_dialog(self, on_selection, *, filters=None, title="Datei öffnen") -> bool:
        """
        System-Öffnen-Dialog:
        - Android: plyer.filechooser.open_file (system picker)
        - Desktop: Tk open dialog
        Ruft on_selection(list_of_paths) auf.
        Gibt True zurück, wenn ein Dialog versucht wurde.
        """
        # Android system picker via plyer
        if kivy_platform == "android" and plyer_filechooser is not None:
            try:
                plyer_filechooser.open_file(on_selection=on_selection, filters=filters or ["*.csv"])
                return True
            except Exception:
                pass

        # Desktop: Tk dialog
        if kivy_platform in ("win", "linux", "macosx"):
            ft = [("CSV", "*.csv"), ("Alle Dateien", "*.*")]
            try:
                path = self.desktop_open_file_dialog(title=title, filetypes=ft)
                on_selection([path] if path else [])
                return True
            except Exception:
                pass

        return False

    def run_save_file_dialog(self, on_selection, *, default_filename="export.csv", title="Speichern unter") -> bool:
        """
        System-Speichern-Dialog (Desktop).
        Ruft on_selection(list_of_paths) auf.
        """
        if kivy_platform in ("win", "linux", "macosx"):
            ft = [("CSV", "*.csv"), ("Alle Dateien", "*.*")]
            try:
                path = self.desktop_save_file_dialog(title=title, filetypes=ft, initialfile=default_filename)
                on_selection([path] if path else [])
                return True
            except Exception:
                pass

        return False


    def _normalize_picker_path(self, s: str) -> str:
        """
        plyer/filechooser kann je nach Android-Version zurückgeben:
          - /storage/... (normal)
          - file:///storage/...
          - content://...
        """
        if not s:
            return ""
        s = str(s).strip()
        if s.startswith("file://"):
            s = s[7:]
        return s

    def _android_copy_content_uri_to_file(self, uri_str: str, dest_path: str) -> bool:
        """
        Kopiert content://... via ContentResolver in eine echte Datei (dest_path).
        Funktioniert ohne dass die App Ordner browsen können muss.
        """
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            Uri = autoclass("android.net.Uri")
            BufferedInputStream = autoclass("java.io.BufferedInputStream")
            BufferedOutputStream = autoclass("java.io.BufferedOutputStream")
            FileOutputStream = autoclass("java.io.FileOutputStream")
            ByteArray = autoclass("[B")
        except Exception:
            return False

        try:
            os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
            uri = Uri.parse(uri_str)
            cr = activity.getContentResolver()
            ins = cr.openInputStream(uri)
            if ins is None:
                return False

            bis = BufferedInputStream(ins)
            fos = FileOutputStream(dest_path)
            bos = BufferedOutputStream(fos)

            buf = ByteArray(16 * 1024)
            while True:
                n = bis.read(buf)
                if n <= 0:
                    break
                bos.write(buf, 0, n)

            bos.flush()
            try:
                bos.close()
            except Exception:
                pass
            try:
                bis.close()
            except Exception:
                pass
            return True
        except Exception:
            try:
                bos.close()
            except Exception:
                pass
            try:
                bis.close()
            except Exception:
                pass
            return False

    def copy_any_to_file(self, src: str, dest: str) -> bool:
        """
        Cross-platform copy:
          - normal path: shutil.copy2
          - android content:// : ContentResolver copy
        """
        src = self._normalize_picker_path(src)
        if not src or not dest:
            return False

        if kivy_platform == "android" and src.startswith("content://"):
            return self._android_copy_content_uri_to_file(src, dest)

        try:
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            shutil.copy2(src, dest)
            return True
        except Exception:
            return False

    def _android_share_file_intent(self, filepath: str, mime_type: str = "text/csv", title: str = "Teilen") -> bool:
        """
        Share-Sheet via Android Intent.
        """
        # fürs Debug/Popup
        try:
            self._last_share_error = ""
        except Exception:
            pass

        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity

            Intent = autoclass("android.content.Intent")
            File = autoclass("java.io.File")
            Uri = autoclass("android.net.Uri")
            VERSION = autoclass("android.os.Build$VERSION")
            sdk = int(VERSION.SDK_INT)

            try:
                from android.runnable import run_on_ui_thread
            except Exception:
                run_on_ui_thread = None
        except Exception as e:
            self._last_share_error = str(e)
            return False

        file_obj = File(filepath)
        uri = None

        FileProvider = None
        try:
            FileProvider = autoclass("androidx.core.content.FileProvider")
        except Exception:
            try:
                FileProvider = autoclass("android.support.v4.content.FileProvider")
            except Exception:
                FileProvider = None

        if FileProvider is not None:
            pkg = activity.getApplicationContext().getPackageName()
            for suffix in (".fileprovider", ".provider"):
                try:
                    uri = FileProvider.getUriForFile(activity, pkg + suffix, file_obj)
                    break
                except Exception as e:
                    uri = None
                    self._last_share_error = str(e)

        # WICHTIG: Auf Android >= 24 KEIN Uri.fromFile fallback mehr (häufig kaputt)
        if uri is None and sdk < 24:
            try:
                uri = Uri.fromFile(file_obj)
            except Exception as e:
                uri = None
                self._last_share_error = str(e)

        def _start(intent_obj):
            try:
                chooser = Intent.createChooser(intent_obj, title)
                if run_on_ui_thread is not None:
                    @run_on_ui_thread
                    def _go():
                        activity.startActivity(chooser)

                    _go()
                else:
                    activity.startActivity(chooser)
                return True
            except Exception as e:
                self._last_share_error = str(e)
                return False

        # try file share
        if uri is not None:
            try:
                intent = Intent(Intent.ACTION_SEND)
                intent.setType(mime_type or "*/*")
                intent.putExtra(Intent.EXTRA_STREAM, uri)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                if _start(intent):
                    return True
            except Exception as e:
                self._last_share_error = str(e)

        # fallback: share as text (damit wenigstens Share-Sheet aufgeht)
        try:
            try:
                txt = open(filepath, "r", encoding="utf-8").read()
            except Exception:
                txt = filepath
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_TEXT, txt)
            return _start(intent)
        except Exception as e:
            self._last_share_error = str(e)
            return False


    def run_share_file_dialog(self, filepath: str, *, mime_type: str = "text/csv", title: str = "Teilen") -> bool:
        if not filepath:
            return False
        if kivy_platform != "android":
            return False

        # 1) Intent first (reliable)
        try:
            if self._android_share_file_intent(filepath, mime_type=mime_type, title=title):
                return True
        except Exception:
            pass

        # 2) plyer.share fallback
        if plyer_share is not None:
            try:
                try:
                    plyer_share.share(filepath=filepath, mime_type=mime_type, title=title)
                except TypeError:
                    plyer_share.share(filepath=filepath, title=title)
                return True
            except Exception:
                pass

        return False


    def create_accent_bar(self):
        accents = ["é", "è", "ê", "ë", "à", "â", "î", "ï", "ô", "ù", "û", "ç", "œ", "æ"]
        bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(4))

        for ch in accents:
            btn = self.make_secondary_button(ch, size_hint=(None, 1), width=dp(40))

            def make_handler(char):
                def _insert(_inst):
                    ti = getattr(self, "current_focus_input", None)
                    if isinstance(ti, TextInput):
                        ti.insert_text(char)

                        def _refocus(_dt):
                            ti.focus = True
                            self.current_focus_input = ti

                        Clock.schedule_once(_refocus, 0)

                return _insert

            btn.bind(on_press=make_handler(ch))
            bar.add_widget(btn)

        return bar

    def run_open_file_dialog(self, on_selection, *, filters=None, title="Datei öffnen") -> bool:
        """
        System-Öffnen-Dialog:
        - Android: plyer.filechooser.open_file (system picker)
        - Desktop: Tk open dialog
        Ruft on_selection(list_of_paths) auf.
        Gibt True zurück, wenn ein Dialog versucht wurde.
        """
        filters = filters or ["*.*"]

        def _safe_call(selection):
            # plyer callback kann nicht im Kivy-Thread sein -> immer schedulen
            try:
                sel = list(selection) if selection else []
            except Exception:
                sel = []
            Clock.schedule_once(lambda _dt: on_selection(sel), 0)

        # Android system picker via plyer
        if kivy_platform == "android" and plyer_filechooser is not None:
            try:
                plyer_filechooser.open_file(on_selection=_safe_call, filters=filters)
                return True
            except Exception:
                pass

        # Desktop: Tk dialog
        if kivy_platform in ("win", "linux", "macosx"):
            patterns = " ".join(filters) if isinstance(filters, (list, tuple)) else str(filters)
            low = patterns.lower()
            if "csv" in low:
                label = "CSV"
            elif any(x in low for x in ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff", "*.webp")):
                label = "Bilder"
            else:
                label = "Dateien"

            ft = [(label, patterns), ("Alle Dateien", "*.*")]
            try:
                path = self.desktop_open_file_dialog(title=title, filetypes=ft)
                _safe_call([path] if path else [])
                return True
            except Exception:
                pass

        return False
