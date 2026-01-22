# vokaba/mixins/ocr_import.py
from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import subprocess


from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.utils import platform as kivy_platform
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

import save
from vokaba.core.logging_utils import log
from vokaba.core.paths import data_dir
from vokaba.ui.widgets.rounded import RoundedCard


class OcrImportMixin:
    """
    OCR import wizard:
      1) Pick image (jpg/png)
      2) Choose column count + mapping (own/foreign/third)
      3) Run OCR (background thread) + loading animation
      4) Review extracted vocab top-to-bottom; accept / back / skip
      5) Import accepted entries into the current stack
    """

    def ocr_wizard(self, stack: str, vocab_list: list, _instance=None):
        self.reload_config()
        # wenn wir aus add_vocab kommen: dessen Key-Handler abklemmen (sonst Tab/Enter in OCR-Screens)
        try:
            if hasattr(self, "_unbind_add_vocab_keys"):
                self._unbind_add_vocab_keys()
        except Exception:
            pass

        self._ocr_stack = stack
        self._ocr_vocab_list_ref = vocab_list
        self._ocr_image_path = None  # local real path (not content://)
        self._ocr_cancel_token = object()
        self._ocr_setup_screen()

    # -------------------------
    # Screen 1: setup
    # -------------------------

    def _ocr_setup_screen(self):
        stack = getattr(self, "_ocr_stack", None)
        if not stack:
            return

        self.window.clear_widgets()
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        input_h = self.get_textinput_height()

        latin_active = bool(save.read_languages(self.vocab_root() + stack)[3])

        # Back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(
            self.make_icon_button("assets/back_button.png", on_press=self._ocr_back_to_add_vocab, size=dp(56))
        )
        self.window.add_widget(top_right)

        # Title
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=30 * pad_mul)
        top_center.add_widget(self.make_title_label("OCR-Import", size_hint=(None, None), size=(dp(360), dp(40))))
        self.window.add_widget(top_center)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.95, 0.92),
            padding=dp(16),
            spacing=dp(12),
            bg_color=self.colors["card"],
        )

        scroll = ScrollView(size_hint=(1, 1))
        form = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(8), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        hint = (
            "1) Bild auswählen (JPG/PNG)\n"
            "2) Spalten zuordnen\n"
            "3) OCR starten\n\n"
            "Tipp: Beim ersten Mal lädt PaddleOCR Modelle (kann dauern)."
        )
        form.add_widget(self.make_text_label(hint, size_hint_y=None, height=dp(140)))

        # Pick image
        pick_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=input_h, spacing=dp(10))
        pick_btn = self.make_primary_button("Bild auswählen …", size_hint=(0.55, 1))
        self._ocr_selected_label = self.make_text_label("Kein Bild gewählt", size_hint=(0.45, 1), halign="left")
        pick_btn.bind(on_press=self._ocr_pick_image)
        pick_row.add_widget(pick_btn)
        pick_row.add_widget(self._ocr_selected_label)
        form.add_widget(pick_row)

        # OCR lang
        form.add_widget(self.make_title_label("OCR-Sprache (PaddleOCR 'lang')", size_hint_y=None, height=dp(32)))
        self._ocr_lang_input = self.style_textinput(
            TextInput(text="en", multiline=False, size_hint=(1, None), height=input_h)
        )
        form.add_widget(self._ocr_lang_input)

        # Orientation
        ori_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(42), spacing=dp(10))
        self._ocr_textline_ori = CheckBox(active=True)
        ori_row.add_widget(self._ocr_textline_ori)
        ori_row.add_widget(self.make_text_label("Textline-Orientation (gegen gedrehte Fotos)", halign="left"))
        form.add_widget(ori_row)

        # Column count
        form.add_widget(self.make_title_label("Wie viele Spalten hat die Seite?", size_hint_y=None, height=dp(32)))
        values = ["2", "3"]
        self._ocr_colcount_spinner = Spinner(
            text="2" if not latin_active else "3",
            values=values,
            size_hint=(1, None),
            height=input_h,
        )
        self.style_spinner(self._ocr_colcount_spinner)
        form.add_widget(self._ocr_colcount_spinner)

        # Column mapping (spinners)
        form.add_widget(self.make_title_label("Spalten-Zuordnung", size_hint_y=None, height=dp(32)))

        role_values = ["Fremdsprache", "Eigene Sprache", "Dritte Spalte", "Ignorieren"]
        self._ocr_map_spinners: List[Spinner] = []

        def add_map_row(idx: int):
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=input_h, spacing=dp(10))
            row.add_widget(self.make_text_label(f"Spalte {idx}:", size_hint=(0.35, 1), halign="left"))
            spn = Spinner(text=role_values[min(idx - 1, 2)], values=role_values, size_hint=(0.65, 1))
            self.style_spinner(spn)
            row.add_widget(spn)
            form.add_widget(row)
            self._ocr_map_spinners.append(spn)

        add_map_row(1)
        add_map_row(2)
        add_map_row(3)

        if not latin_active:
            form.add_widget(
                self.make_text_label(
                    "Hinweis: Dein Stapel ist 2-spaltig. Wenn du trotzdem 3 Spalten OCRst, "
                    "landet Spalte 'Dritte Spalte' im Info-Feld.",
                    size_hint_y=None,
                    height=dp(70),
                    halign="left",
                )
            )

        self._ocr_setup_error = Label(
            text="",
            color=self.colors["danger"],
            font_size=sp(int(self.config_data["settings"]["gui"]["text_font_size"])),
            size_hint_y=None,
            height=dp(26),
        )
        self._ocr_setup_error.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        form.add_widget(self._ocr_setup_error)

        start_btn = self.make_success_button("OCR starten", size_hint=(1, None), height=dp(64))
        start_btn.bind(on_press=self._ocr_start)
        form.add_widget(start_btn)

        scroll.add_widget(form)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

        def _on_cols(_inst, value):
            try:
                n = int(value)
            except Exception:
                n = 2
            for i, spn in enumerate(self._ocr_map_spinners, start=1):
                spn.disabled = (i > n)
                spn.opacity = 0.35 if i > n else 1.0

        self._ocr_colcount_spinner.bind(text=_on_cols)
        _on_cols(self._ocr_colcount_spinner, self._ocr_colcount_spinner.text)

    def _ocr_back_to_add_vocab(self, _instance=None):
        stack = getattr(self, "_ocr_stack", None)
        vocab_list = getattr(self, "_ocr_vocab_list_ref", None)
        if stack and vocab_list is not None:
            self.add_vocab(stack, vocab_list)
        else:
            self.main_menu()

    # -------------------------
    # Image picker
    # -------------------------

    def _ocr_pick_image(self, _instance=None):
        def on_sel(selection):
            if not selection:
                return
            src = selection[0]
            local = self._ocr_copy_to_local_file(src)
            if not local:
                self._ocr_setup_error.text = "Konnte Bild nicht öffnen."
                return
            self._ocr_image_path = local
            self._ocr_selected_label.text = os.path.basename(local) if local else "Bild gewählt"
            self._ocr_setup_error.text = ""

        try:
            if hasattr(self, "run_open_file_dialog") and self.run_open_file_dialog(
                on_sel,
                filters=["*.png", "*.jpg", "*.jpeg"],
                title="Bild auswählen",
            ):
                return
        except Exception as e:
            log(f"ocr pick image: system dialog failed: {e}")

        if kivy_platform == "android":
            Popup(
                title="Bild auswählen nicht möglich",
                content=self.make_text_label(
                    "Auf Android muss der System-Dateiauswahldialog aufgehen.\n"
                    "Wenn der nicht aufgeht, fehlt meist 'plyer' im Build (requirements).",
                    halign="center",
                ),
                size_hint=(0.85, None),
                height=dp(220),
            ).open()
            return

        from kivy.uix.filechooser import FileChooserIconView

        chooser = FileChooserIconView(path=os.path.expanduser("~"), dirselect=False, filters=["*.png", "*.jpg", "*.jpeg"])
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(chooser)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        cancel_btn = self.make_secondary_button("Abbrechen", size_hint=(0.5, 1))
        ok_btn = self.make_primary_button("Auswählen", size_hint=(0.5, 1))
        row.add_widget(cancel_btn)
        row.add_widget(ok_btn)
        content.add_widget(row)

        popup = Popup(title="Bild auswählen", content=content, size_hint=(0.9, 0.9))

        def _ok(*_a):
            if chooser.selection:
                on_sel([chooser.selection[0]])
            popup.dismiss()

        ok_btn.bind(on_press=_ok)
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        popup.open()

    def _ocr_copy_to_local_file(self, src_raw: str) -> str:
        try:
            src = self._normalize_picker_path(src_raw) if hasattr(self, "_normalize_picker_path") else str(src_raw)
        except Exception:
            src = str(src_raw)

        ext = ".png"
        low = (src or "").lower()
        if low.endswith(".jpg") or low.endswith(".jpeg"):
            ext = ".jpg"
        elif low.endswith(".png"):
            ext = ".png"

        base = Path(data_dir()) / "ocr_cache"
        try:
            base.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        dest = base / f"ocr_input_{int(time.time())}{ext}"

        try:
            if hasattr(self, "copy_any_to_file"):
                ok = bool(self.copy_any_to_file(src, str(dest)))
            else:
                import shutil
                shutil.copy2(src, str(dest))
                ok = True
        except Exception:
            ok = False

        return str(dest) if ok and dest.exists() else ""

    # -------------------------
    # Run OCR (threaded)
    # -------------------------

    def _ocr_start(self, _instance=None):
        if not getattr(self, "_ocr_image_path", None):
            self._ocr_setup_error.text = "Bitte zuerst ein Bild auswählen."
            return

        try:
            n_cols = int(getattr(self, "_ocr_colcount_spinner", None).text)
        except Exception:
            n_cols = 2
        n_cols = 3 if n_cols >= 3 else 2

        mapping = []
        for spn in (getattr(self, "_ocr_map_spinners", [])[:n_cols]):
            mapping.append((spn.text or "Ignorieren").strip())

        lang = (getattr(self, "_ocr_lang_input", None).text or "en").strip() or "en"
        use_ori = bool(getattr(self, "_ocr_textline_ori", None).active)

        token = object()
        self._ocr_cancel_token = token

        self._ocr_loading_screen()

        th = threading.Thread(
            target=self._ocr_worker,
            kwargs={
                "token": token,
                "image_path": str(self._ocr_image_path),
                "lang": lang,
                "use_textline_orientation": use_ori,
                "n_cols": n_cols,
                "mapping": mapping,
            },
            daemon=True,
        )
        th.start()

    def _ocr_loading_screen(self):
        self.window.clear_widgets()
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.5), padding=dp(16), spacing=dp(14), bg_color=self.colors["card"])

        card.add_widget(self.make_title_label("OCR läuft …", size_hint_y=None, height=dp(40)))
        card.add_widget(self.make_text_label("Bitte warten. Das kann beim ersten Mal länger dauern.", size_hint_y=None, height=dp(60), halign="center"))

        pb = ProgressBar(max=100, value=0)
        pb.size_hint_y = None
        pb.height = dp(18)
        card.add_widget(pb)

        state = {"v": 0, "dir": 1}

        def tick(_dt):
            if getattr(self, "_ocr_cancel_token", None) is None:
                return False
            v = state["v"] + state["dir"] * 6
            if v >= 100:
                v = 100
                state["dir"] = -1
            elif v <= 0:
                v = 0
                state["dir"] = 1
            state["v"] = v
            pb.value = v
            return True

        self._ocr_loading_clock = Clock.schedule_interval(tick, 0.05)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(12))
        cancel_btn = self.make_secondary_button("Abbrechen", size_hint=(1, 1))
        cancel_btn.bind(on_press=self._ocr_cancel_loading)
        row.add_widget(cancel_btn)
        card.add_widget(row)

        center.add_widget(card)
        self.window.add_widget(center)

    def _ocr_cancel_loading(self, _instance=None):
        self._ocr_cancel_token = None
        try:
            if hasattr(self, "_ocr_loading_clock") and self._ocr_loading_clock is not None:
                self._ocr_loading_clock.cancel()
        except Exception:
            pass
        self._ocr_setup_screen()

    def _ocr_worker(
        self,
        *,
        token: object,
        image_path: str,
        lang: str,
        use_textline_orientation: bool,
        n_cols: int,
        mapping: List[str],
    ):
        try:
            cache = Path(data_dir()) / "paddleocr_models"
            cache.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("DISABLE_AUTO_LOGGING_CONFIG", "1")
            os.environ.setdefault("PADDLEX_HOME", str(cache))
            os.environ.setdefault("PADDLEX_CACHE_DIR", str(cache))

            import sys

            # Model cache dir (du hast cache schon)
            cache = Path(data_dir()) / "paddleocr_models"
            cache.mkdir(parents=True, exist_ok=True)

            out_json = Path(data_dir()) / "ocr_cache" / f"ocr_out_{int(time.time())}.json"
            try:
                out_json.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            cmd = [
                sys.executable, "-m", "vokaba.ocr_runner",
                "--image", str(image_path),
                "--lang", str(lang),
                "--cache-dir", str(cache),
                "--out", str(out_json),
                "--no-source-check",
            ]
            if use_textline_orientation:
                cmd.append("--textline-ori")

            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                raise RuntimeError(err or f"OCR subprocess failed (code {proc.returncode})")

            if not out_json.exists():
                raise RuntimeError("OCR subprocess returned ok, but output JSON is missing.")

            json_pages = json.loads(out_json.read_text(encoding="utf-8"))
            try:
                out_json.unlink(missing_ok=True)  # py3.12 ok
            except Exception:
                pass


            import paddleocr as paddleocr_pkg  # noqa: F401
            from paddleocr import PaddleOCR

            if not hasattr(self, "_paddleocr_engine") or self._paddleocr_engine is None:
                self._paddleocr_engine = PaddleOCR(lang=lang, use_textline_orientation=use_textline_orientation)
                self._paddleocr_engine_lang = lang
                self._paddleocr_engine_ori = use_textline_orientation
            else:
                if getattr(self, "_paddleocr_engine_lang", None) != lang or getattr(self, "_paddleocr_engine_ori", None) != use_textline_orientation:
                    self._paddleocr_engine = PaddleOCR(lang=lang, use_textline_orientation=use_textline_orientation)
                    self._paddleocr_engine_lang = lang
                    self._paddleocr_engine_ori = use_textline_orientation

            ocr = self._paddleocr_engine
            results = ocr.predict(str(image_path), use_textline_orientation=use_textline_orientation)

            json_pages = []
            for res in results or []:
                j = getattr(res, "json", None)
                if isinstance(j, dict):
                    json_pages.append(j)

            rows = self._ocr_rows_from_paddle_json(json_pages, n_cols=n_cols)
            entries = self._ocr_rows_to_vocab_entries(rows, mapping=mapping)

        except Exception as e:
            msg = f"OCR Fehler: {e}"
            log(msg)

            def _show(_dt):
                if getattr(self, "_ocr_cancel_token", None) is token:
                    self._ocr_show_error(msg)

            Clock.schedule_once(_show, 0)
            return

        def _done(_dt):
            if getattr(self, "_ocr_cancel_token", None) is not token:
                return
            self._ocr_review_screen(entries)

        Clock.schedule_once(_done, 0)

    def _ocr_show_error(self, msg: str):
        try:
            if hasattr(self, "_ocr_loading_clock") and self._ocr_loading_clock is not None:
                self._ocr_loading_clock.cancel()
        except Exception:
            pass

        Popup(
            title="OCR fehlgeschlagen",
            content=self.make_text_label(
                msg + "\n\n"
                "Wenn das auf Android passiert: PaddleOCR ist sehr groß und braucht spezielle Buildozer/NDK-Konfiguration.\n"
                "Auf Desktop sollte es (mit installierter paddleocr/paddle) laufen.",
                halign="center",
            ),
            size_hint=(0.9, None),
            height=dp(320),
        ).open()

        self._ocr_setup_screen()

    # -------------------------
    # Parsing OCR output -> rows -> entries
    # -------------------------

    def _ocr_rows_from_paddle_json(self, pages: List[Dict[str, Any]], *, n_cols: int) -> List[List[str]]:
        items = []

        def bbox_from_poly(poly):
            try:
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                return min(xs), min(ys), max(xs), max(ys)
            except Exception:
                return None

        for page in pages or []:
            payload = page.get("res", page) if isinstance(page, dict) else {}
            texts = payload.get("rec_texts") or []
            scores = payload.get("rec_scores") or []
            boxes = (
                payload.get("dt_polys")
                or payload.get("dt_boxes")
                or payload.get("rec_boxes")
                or payload.get("boxes")
                or []
            )

            if not boxes or not isinstance(boxes, list):
                for i, t in enumerate(texts):
                    t = (t or "").strip()
                    if not t:
                        continue
                    sc = float(scores[i]) if i < len(scores) else 1.0
                    if sc < 0.45:
                        continue
                    items.append({"text": t, "x": 0.0, "y": float(i) * 10.0, "h": 10.0})
                continue

            for i, t in enumerate(texts):
                t = (t or "").strip()
                if not t:
                    continue
                sc = float(scores[i]) if i < len(scores) else 1.0
                if sc < 0.45:
                    continue

                b = boxes[i] if i < len(boxes) else None
                bb = None
                if isinstance(b, (list, tuple)) and b and isinstance(b[0], (list, tuple)):
                    bb = bbox_from_poly(b)
                if bb is None and isinstance(b, (list, tuple)) and len(b) == 4 and all(isinstance(x, (int, float)) for x in b):
                    bb = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))

                if bb is None:
                    items.append({"text": t, "x": 0.0, "y": float(i) * 10.0, "h": 10.0})
                    continue

                x1, y1, x2, y2 = bb
                items.append(
                    {
                        "text": t,
                        "x": float((x1 + x2) / 2.0),
                        "y": float((y1 + y2) / 2.0),
                        "h": float(max(1.0, y2 - y1)),
                    }
                )

        if not items:
            return []

        items.sort(key=lambda it: (it["y"], it["x"]))

        hs = sorted([float(it.get("h", 10.0) or 10.0) for it in items])
        med_h = hs[len(hs) // 2] if hs else 10.0
        line_tol = max(8.0, med_h * 0.65)

        lines: List[Dict[str, Any]] = []
        for it in items:
            y = float(it["y"])
            if not lines:
                lines.append({"y": y, "items": [it]})
                continue
            if abs(y - float(lines[-1]["y"])) <= line_tol:
                lines[-1]["items"].append(it)
                ys = [x["y"] for x in lines[-1]["items"]]
                lines[-1]["y"] = sum(ys) / max(1, len(ys))
            else:
                lines.append({"y": y, "items": [it]})

        xs = [float(it["x"]) for it in items]
        _, bounds = self._kmeans_1d(xs, k=n_cols)

        def col_idx(x: float) -> int:
            for i, b in enumerate(bounds):
                if x <= b:
                    return i
            return n_cols - 1

        rows: List[List[str]] = []
        for ln in lines:
            its = sorted(ln["items"], key=lambda it: it["x"])
            cols = [[] for _ in range(n_cols)]
            for it in its:
                c = col_idx(float(it["x"]))
                cols[c].append(it["text"])

            row = []
            for c in cols:
                txt = " ".join([self._clean_cell_text(x) for x in c if self._clean_cell_text(x)])
                row.append(txt.strip())
            if self._row_is_noise(row):
                continue
            rows.append(row)

        fixed = []
        for row in rows:
            if sum(1 for x in row if x) <= 1:
                merged = " ".join([x for x in row if x]).strip()
                parts = self._split_by_separators(merged, n_cols=n_cols)
                fixed.append(parts if parts else row)
            else:
                fixed.append(row)

        return fixed

    def _ocr_rows_to_vocab_entries(self, rows: List[List[str]], *, mapping: List[str]) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        n_cols = len(mapping)

        for r in rows:
            cols = list(r[:n_cols]) + [""] * max(0, n_cols - len(r))
            own = foreign = third = ""
            for i, role in enumerate(mapping):
                txt = (cols[i] or "").strip()
                if not txt or role == "Ignorieren":
                    continue
                if role == "Eigene Sprache":
                    own = txt
                elif role == "Fremdsprache":
                    foreign = txt
                elif role == "Dritte Spalte":
                    third = txt

            own = self._clean_cell_text(own)
            foreign = self._clean_cell_text(foreign)
            third = self._clean_cell_text(third)

            if not own or not foreign:
                continue

            entries.append(
                {
                    "own_language": own,
                    "foreign_language": foreign,
                    "latin_language": third,
                    "info": "",
                    "_keep": "1",
                }
            )
        return entries

    # -------------------------
    # Review screen
    # -------------------------

    def _ocr_review_screen(self, entries: List[Dict[str, str]]):
        try:
            if hasattr(self, "_ocr_loading_clock") and self._ocr_loading_clock is not None:
                self._ocr_loading_clock.cancel()
        except Exception:
            pass

        self._ocr_entries = entries or []
        self._ocr_index = 0

        if not self._ocr_entries:
            Popup(
                title="Keine Vokabeln gefunden",
                content=self.make_text_label(
                    "Ich konnte keine passenden Vokabel-Paare extrahieren.\n\n"
                    "Tipp: Foto näher ran, gute Beleuchtung, nicht schräg.",
                    halign="center",
                ),
                size_hint=(0.85, None),
                height=dp(240),
            ).open()
            self._ocr_setup_screen()
            return

        self._ocr_render_review()

    def _ocr_render_review(self):
        stack = getattr(self, "_ocr_stack", None)
        vocab_list = getattr(self, "_ocr_vocab_list_ref", None)
        if not stack or vocab_list is None:
            self.main_menu()
            return

        self.window.clear_widgets()
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        input_h = self.get_textinput_height()
        latin_active = bool(save.read_languages(self.vocab_root() + stack)[3])

        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(self.make_icon_button("assets/back_button.png", on_press=lambda _i: self._ocr_setup_screen(), size=dp(56)))
        self.window.add_widget(top_right)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.92, 0.85), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        total = len(self._ocr_entries)
        idx = int(getattr(self, "_ocr_index", 0) or 0)
        idx = max(0, min(total - 1, idx))

        card.add_widget(self.make_title_label(f"Review {idx+1}/{total}", size_hint_y=None, height=dp(40)))

        entry = self._ocr_entries[idx]

        card.add_widget(self.make_title_label("Fremdsprache", size_hint_y=None, height=dp(30)))
        self._ocr_in_foreign = self.style_textinput(TextInput(text=entry.get("foreign_language", ""), multiline=False, size_hint=(1, None), height=input_h))
        card.add_widget(self._ocr_in_foreign)

        card.add_widget(self.make_title_label("Eigene Sprache", size_hint_y=None, height=dp(30)))
        self._ocr_in_own = self.style_textinput(TextInput(text=entry.get("own_language", ""), multiline=False, size_hint=(1, None), height=input_h))
        card.add_widget(self._ocr_in_own)

        if latin_active:
            card.add_widget(self.make_title_label("Dritte Spalte", size_hint_y=None, height=dp(30)))
            self._ocr_in_third = self.style_textinput(TextInput(text=entry.get("latin_language", ""), multiline=False, size_hint=(1, None), height=input_h))
            card.add_widget(self._ocr_in_third)
        else:
            self._ocr_in_third = None

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(10))
        back_btn = self.make_secondary_button("Zurück", size_hint=(0.33, 1))
        skip_btn = self.make_secondary_button("Überspringen", size_hint=(0.33, 1))
        ok_btn = self.make_success_button("Passt", size_hint=(0.34, 1))

        back_btn.bind(on_press=self._ocr_prev)
        skip_btn.bind(on_press=self._ocr_skip)
        ok_btn.bind(on_press=self._ocr_accept)

        row.add_widget(back_btn)
        row.add_widget(skip_btn)
        row.add_widget(ok_btn)
        card.add_widget(row)

        done_btn = self.make_primary_button("Import jetzt abschließen", size_hint=(1, None), height=dp(54))
        done_btn.bind(on_press=self._ocr_finish)
        card.add_widget(done_btn)

        center.add_widget(card)
        self.window.add_widget(center)

        Clock.schedule_once(lambda _dt: setattr(self._ocr_in_foreign, "focus", True), 0.05)

    def _ocr_store_current_edits(self):
        idx = int(getattr(self, "_ocr_index", 0) or 0)
        if not (0 <= idx < len(self._ocr_entries)):
            return
        e = self._ocr_entries[idx]
        e["foreign_language"] = (getattr(self, "_ocr_in_foreign", None).text or "").strip()
        e["own_language"] = (getattr(self, "_ocr_in_own", None).text or "").strip()
        if getattr(self, "_ocr_in_third", None) is not None:
            e["latin_language"] = (self._ocr_in_third.text or "").strip()

    def _ocr_prev(self, _instance=None):
        self._ocr_store_current_edits()
        idx = int(getattr(self, "_ocr_index", 0) or 0)
        if idx <= 0:
            self._ocr_setup_screen()
            return
        self._ocr_index = idx - 1
        self._ocr_render_review()

    def _ocr_skip(self, _instance=None):
        self._ocr_store_current_edits()
        idx = int(getattr(self, "_ocr_index", 0) or 0)
        if 0 <= idx < len(self._ocr_entries):
            self._ocr_entries[idx]["_keep"] = ""
        self._ocr_index = idx + 1
        if self._ocr_index >= len(self._ocr_entries):
            self._ocr_finish()
            return
        self._ocr_render_review()

    def _ocr_accept(self, _instance=None):
        self._ocr_store_current_edits()
        idx = int(getattr(self, "_ocr_index", 0) or 0)
        if 0 <= idx < len(self._ocr_entries):
            self._ocr_entries[idx]["_keep"] = "1"
        self._ocr_index = idx + 1
        if self._ocr_index >= len(self._ocr_entries):
            self._ocr_finish()
            return
        self._ocr_render_review()

    def _ocr_finish(self, _instance=None):
        stack = getattr(self, "_ocr_stack", None)
        vocab_list = getattr(self, "_ocr_vocab_list_ref", None)
        if not stack or vocab_list is None:
            self.main_menu()
            return

        self._ocr_store_current_edits()
        latin_active = bool(save.read_languages(self.vocab_root() + stack)[3])

        added = 0
        for e in getattr(self, "_ocr_entries", []) or []:
            keep = bool((e.get("_keep") or "").strip())
            if not keep:
                continue

            own = (e.get("own_language") or "").strip()
            foreign = (e.get("foreign_language") or "").strip()
            third = (e.get("latin_language") or "").strip()
            if not own or not foreign:
                continue

            info = ""
            if not latin_active and third:
                info = (e.get("info") or "").strip()
                info = (info + " | " if info else "") + third
                third = ""

            vocab_list.append(
                {
                    "own_language": own,
                    "foreign_language": foreign,
                    "latin_language": third,
                    "info": info,
                    "knowledge_level": 0.0,
                }
            )
            added += 1

        save.save_to_vocab(vocab_list, self.vocab_root() + stack)

        Popup(
            title="OCR Import",
            content=self.make_text_label(f"✅ Importiert: {added} Einträge", halign="center"),
            size_hint=(0.7, None),
            height=dp(180),
        ).open()

        self.add_vocab(stack, vocab_list)

    # -------------------------
    # Heuristics helpers
    # -------------------------

    def _clean_cell_text(self, s: str) -> str:
        s = "" if s is None else str(s)
        s = s.replace("\u00ad", "")
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r"^(?:\(?\d{1,3}\)?[.)]\s*|[A-Za-z][.)]\s*|[-•·]\s*)", "", s).strip()
        if re.fullmatch(r"\d{1,4}", s or ""):
            return ""
        return s

    def _row_is_noise(self, row: List[str]) -> bool:
        cols = [(c or "").strip() for c in row]
        if not any(cols):
            return True
        nonempty = [c for c in cols if c]
        if len(nonempty) == 1:
            c = nonempty[0]
            if re.fullmatch(r"\d{1,4}", c):
                return True
            if len(c) == 1 and not c.isdigit():
                return True
            if c.lower() in ("unit", "lektion", "kapitel"):
                return True
        joined = " ".join(nonempty).lower()
        if "©" in joined or "copyright" in joined or "www." in joined:
            return True
        return False

    def _split_by_separators(self, s: str, *, n_cols: int) -> Optional[List[str]]:
        s = (s or "").strip()
        if not s:
            return None
        seps = [" | ", " - ", " – ", " — ", "\t"]
        for sep in seps:
            if sep.strip() and sep in s:
                parts = [p.strip() for p in s.split(sep) if p.strip()]
                if len(parts) >= n_cols:
                    out = parts[:n_cols]
                    out += [""] * (n_cols - len(out))
                    return out
        if re.search(r"\s{3,}", s):
            parts = [p.strip() for p in re.split(r"\s{3,}", s) if p.strip()]
            if len(parts) >= n_cols:
                out = parts[:n_cols]
                out += [""] * (n_cols - len(out))
                return out
        return None

    def _kmeans_1d(self, values: List[float], *, k: int, iters: int = 18) -> Tuple[List[float], List[float]]:
        vals = [float(v) for v in values if v is not None]
        if not vals:
            centers = [0.0] * k
            bounds = [0.0] * max(0, k - 1)
            return centers, bounds

        vals.sort()
        if len(vals) < k:
            centers = (vals + [vals[-1]] * (k - len(vals)))[:k]
            centers.sort()
            bounds = [(centers[i] + centers[i + 1]) / 2.0 for i in range(k - 1)]
            return centers, bounds

        centers = []
        for i in range(k):
            pos = int(((i + 0.5) / k) * (len(vals) - 1))
            centers.append(vals[pos])
        centers.sort()

        for _ in range(iters):
            groups = [[] for _ in range(k)]
            for v in vals:
                best_i = 0
                best_d = abs(v - centers[0])
                for i in range(1, k):
                    d = abs(v - centers[i])
                    if d < best_d:
                        best_d = d
                        best_i = i
                groups[best_i].append(v)

            new_centers = []
            for i in range(k):
                g = groups[i]
                new_centers.append(sum(g) / len(g) if g else centers[i])

            if max(abs(new_centers[i] - centers[i]) for i in range(k)) < 1e-3:
                centers = new_centers
                break
            centers = new_centers

        centers.sort()
        bounds = [(centers[i] + centers[i + 1]) / 2.0 for i in range(k - 1)]
        return centers, bounds
