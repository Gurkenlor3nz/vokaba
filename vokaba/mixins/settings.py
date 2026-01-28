from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.colorpicker import ColorPicker

import labels
import save

from vokaba.core.dict_path import get_in, set_in, bool_cast
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard
from vokaba.ui.widgets.slider import NoScrollSlider
from vokaba.theme.theme_manager import apply_theme_from_config


class SettingsMixin:
    """Settings screen (GUI sliders, theme, learning mode toggles)."""

    def settings(self, _instance=None):
        log("opened settings")
        self.reload_config()

        self.window.clear_widgets()
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        # Top-right: back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        back_button = self.make_icon_button("assets/back_button.png", on_press=self.main_menu, size=dp(56))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.85), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(16), padding=dp(4))
        content.bind(minimum_height=content.setter("height"))

        # Sliders
        settings_definitions = [
            {
                "label": getattr(labels, "settings_title_font_size_slider_test_label", "Titelgröße"),
                "min": 10,
                "max": 100,
                "value": float(self.config_data["settings"]["gui"]["title_font_size"]),
                "path": ["settings", "gui", "title_font_size"],
                "cast": int,
            },
            {
                "label": getattr(labels, "settings_font_size_slider", "Textgröße"),
                "min": 10,
                "max": 45,
                "value": float(self.config_data["settings"]["gui"]["text_font_size"]),
                "path": ["settings", "gui", "text_font_size"],
                "cast": int,
            },
            {
                "label": getattr(labels, "settings_padding_multiplikator_slider", "Padding"),
                "min": 0.1,
                "max": 3.0,
                "value": float(self.config_data["settings"]["gui"]["padding_multiplicator"]),
                "path": ["settings", "gui", "padding_multiplicator"],
                "cast": float,
            },
        ]

        for s in settings_definitions:
            row = RoundedCard(orientation="vertical", size_hint_y=None, height=dp(110), padding=dp(8), spacing=dp(4), bg_color=self.colors["card"])
            lbl = self.make_text_label(s["label"], size_hint_y=None, height=self.get_textinput_height())
            slider = NoScrollSlider(min=s["min"], max=s["max"], value=s["value"], size_hint_y=None, height=self.get_textinput_height())
            slider.bind(value=self._on_setting_changed(s["path"], s["cast"]))
            row.add_widget(lbl)
            row.add_widget(slider)
            content.add_widget(row)

        content.add_widget(Label(size_hint_y=None, height=dp(12)))

        # Session size (number input)
        session_card = RoundedCard(orientation="vertical", size_hint_y=None, height=dp(90), padding=dp(8), spacing=dp(4), bg_color=self.colors["card"])
        session_label = self.make_text_label(getattr(labels, "settings_session_size_label", "Karten pro Lernsitzung"), size_hint_y=None, height=dp(40))

        session_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        current_session = str(int(get_in(self.config_data, ["settings", "session_size"], 20) or 20))
        session_input = self.style_textinput(TextInput(text=current_session, multiline=False, size_hint=(0.3, 1), halign="center"))
        session_input.input_filter = "int"

        def on_focus(inst, focused):
            if focused:
                return
            txt = (inst.text or "").strip()
            try:
                num = int(txt)
            except Exception:
                num = int(get_in(self.config_data, ["settings", "session_size"], 20) or 20)
            num = max(1, min(500, num))
            set_in(self.config_data, ["settings", "session_size"], num)
            save.save_settings(self.config_data)
            inst.text = str(num)

        session_input.bind(focus=on_focus)
        unit_label = self.make_text_label(getattr(labels, "settings_session_size_unit", "Karten"), size_hint_y=None, height=dp(40))
        session_row.add_widget(session_input)
        session_row.add_widget(unit_label)

        session_card.add_widget(session_label)
        session_card.add_widget(session_row)
        content.add_widget(session_card)

        # Daily goal input
        goal_card = RoundedCard(orientation="vertical", size_hint_y=None, height=dp(90), padding=dp(8), spacing=dp(4), bg_color=self.colors["card"])
        goal_label = self.make_text_label(getattr(labels, "settings_daily_goal_label", "Heutiges Ziel (Karten)"), size_hint_y=None, height=dp(40))

        goal_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        cur_goal = str(int(get_in(self.config_data, ["settings", "daily_target_cards"], 300) or 300))
        goal_input = self.style_textinput(TextInput(text=cur_goal, multiline=False, size_hint=(0.3, 1), halign="center"))
        goal_input.input_filter = "int"

        def on_goal_focus(inst, focused):
            if focused:
                return
            txt = (inst.text or "").strip()
            try:
                num = int(txt)
            except Exception:
                num = int(get_in(self.config_data, ["settings", "daily_target_cards"], 300) or 300)
            num = max(1, min(5000, num))
            set_in(self.config_data, ["settings", "daily_target_cards"], num)
            save.save_settings(self.config_data)
            inst.text = str(num)
            self._refresh_daily_progress_ui()

        goal_input.bind(focus=on_goal_focus)
        goal_row.add_widget(goal_input)
        goal_row.add_widget(self.make_text_label("Karten", size_hint_y=None, height=dp(40)))
        goal_card.add_widget(goal_label)
        goal_card.add_widget(goal_row)
        content.add_widget(goal_card)

        # Theme
        content.add_widget(Label(size_hint_y=None, height=dp(12)))
        content.add_widget(self.make_title_label(getattr(labels, "settings_theme_header", "Farbschema (Theme)"), size_hint_y=None, height=dp(40)))

        theme_card = RoundedCard(orientation="vertical", size_hint_y=None, padding=dp(10), spacing=dp(10), bg_color=self.colors["card"])
        theme_card.bind(minimum_height=theme_card.setter("height"))

        current_preset = self.config_data.get("settings", {}).get("theme", {}).get("preset", "dark")

        preset_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
        dark_btn = self.make_secondary_button(getattr(labels, "settings_theme_dark", "Dark"), size_hint=(0.5, 1))
        light_btn = self.make_secondary_button(getattr(labels, "settings_theme_light", "Light"), size_hint=(0.5, 1))

        if current_preset == "dark":
            dark_btn.set_bg_color(self.colors["primary"])
        elif current_preset == "light":
            light_btn.set_bg_color(self.colors["primary"])

        dark_btn.bind(on_press=lambda _i: self.set_theme_preset("dark"))
        light_btn.bind(on_press=lambda _i: self.set_theme_preset("light"))

        preset_row.add_widget(dark_btn)
        preset_row.add_widget(light_btn)
        theme_card.add_widget(preset_row)

        # Color pickers
        custom_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
        primary_btn = self.make_secondary_button(getattr(labels, "settings_theme_primary", "Primärfarbe"), size_hint=(0.5, 1))
        primary_btn.set_bg_color(self.colors["primary"])
        primary_btn.bind(on_press=lambda _i: self.open_color_picker("primary"))

        accent_btn = self.make_secondary_button(getattr(labels, "settings_theme_accent", "Akzentfarbe"), size_hint=(0.5, 1))
        accent_btn.set_bg_color(self.colors["accent"])
        accent_btn.bind(on_press=lambda _i: self.open_color_picker("accent"))

        custom_row.add_widget(primary_btn)
        custom_row.add_widget(accent_btn)
        theme_card.add_widget(custom_row)

        bg_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
        bg1_btn = self.make_secondary_button(getattr(labels, "settings_theme_bg_primary", "Hintergrund 1"), size_hint=(0.25, 1))
        bg1_btn.set_bg_color(self.colors["bg"])
        bg1_btn.bind(on_press=lambda _i: self.open_color_picker("bg"))

        bg2_btn = self.make_secondary_button(getattr(labels, "settings_theme_bg_secondary", "Hintergrund 2"), size_hint=(0.25, 1))
        bg2_btn.set_bg_color(self.colors["card"])
        bg2_btn.bind(on_press=lambda _i: self.open_color_picker("card"))

        reset_btn = self.make_secondary_button(getattr(labels, "settings_theme_reset", "Zurücksetzen"), size_hint=(0.5, 1))
        reset_btn.bind(on_press=self.reset_custom_colors)

        bg_row.add_widget(bg1_btn)
        bg_row.add_widget(bg2_btn)
        bg_row.add_widget(reset_btn)

        theme_card.add_widget(bg_row)
        content.add_widget(theme_card)

        content.add_widget(Label(size_hint_y=None, height=dp(24)))

        # Learning mode toggles
        content.add_widget(self.make_title_label(getattr(labels, "settings_modes_header", "Lernmodi"), size_hint_y=None, height=dp(40)))

        modes_card = RoundedCard(orientation="vertical", size_hint_y=None, padding=dp(8), spacing=dp(8), bg_color=self.colors["card"])
        modes_card.bind(minimum_height=modes_card.setter("height"))

        grid = GridLayout(cols=2, size_hint_y=None, row_default_height=dp(50), row_force_default=True, spacing=dp(8), padding=(0, dp(4), 0, dp(4)))
        grid.bind(minimum_height=grid.setter("height"))

        total_vocab, unique_vocab = self._get_vocab_counts_for_modes()

        def add_mode(mode_key, mode_label, needs=None):
            current = bool_cast(get_in(self.config_data, ["settings", "modes", mode_key], True))
            lbl = self.make_text_label(mode_label, size_hint_y=None, height=dp(50))
            cb = CheckBox(active=current, size_hint=(None, None), size=(dp(36), dp(36)))

            disabled = False
            if needs == "vocab>=5" and total_vocab < 5:
                disabled = True
            if needs == "unique>=5" and unique_vocab < 5:
                disabled = True
            if needs == "vocab>=3" and total_vocab < 3:
                disabled = True

            if disabled:
                cb.disabled = True
                lbl.text += getattr(labels, "not_enougn_vocab_warning", " (mind. nötig)")
                lbl.markup = True

            cb.bind(active=self.on_mode_checkbox_changed(["settings", "modes", mode_key]))
            grid.add_widget(lbl)
            grid.add_widget(cb)

        add_mode("front_back", getattr(labels, "learn_flashcards_front_to_back", "Front->Back"))
        add_mode("back_front", getattr(labels, "learn_flashcards_back_to_front", "Back->Front"))
        add_mode("multiple_choice", getattr(labels, "learn_flashcards_multiple_choice", "Multiple Choice"), needs="vocab>=5")
        add_mode("letter_salad", getattr(labels, "learn_flashcards_letter_salad", "Letter Salad"))
        add_mode("connect_pairs", getattr(labels, "learn_flashcards_connect_pairs", "Connect Pairs"), needs="unique>=5")
        add_mode("typing", getattr(labels, "learn_flashcards_typing_mode", "Typing"))
        add_mode("syllable_salad", getattr(labels, "learn_flashcards_syllable_salad", "Silben-Modus"), needs="vocab>=3")

        modes_card.add_widget(grid)
        content.add_widget(modes_card)

        content.add_widget(Label(size_hint_y=None, height=dp(18)))
        content.add_widget(self.make_title_label(getattr(labels, "settings_stacks_header", "Stapel & Filter"),
                                                 size_hint_y=None, height=dp(40)))

        extra_card = RoundedCard(orientation="vertical", size_hint_y=None, padding=dp(10), spacing=dp(10),
                                 bg_color=self.colors["card"])
        extra_card.bind(minimum_height=extra_card.setter("height"))

        grid2 = GridLayout(cols=2, size_hint_y=None, row_default_height=dp(50), row_force_default=True,
                           spacing=dp(8), padding=(0, dp(4), 0, dp(4)))
        grid2.bind(minimum_height=grid2.setter("height"))

        # 1) Sort by language
        sort_mode = str(get_in(self.config_data, ["settings", "stack_sort_mode"], "name") or "name").lower()
        lbl = self.make_text_label(getattr(labels, "settings_sort_stacks_by_language", "Stapel nach Sprache sortieren"),
                                   size_hint_y=None, height=dp(50))
        cb = CheckBox(active=(sort_mode == "language"), size_hint=(None, None), size=(dp(36), dp(36)))

        def _set_sort(_inst, value):
            set_in(self.config_data, ["settings", "stack_sort_mode"], "language" if value else "name")
            save.save_settings(self.config_data)

        cb.bind(active=_set_sort)
        grid2.add_widget(lbl)
        grid2.add_widget(cb)

        # 2) Typing self-rating toggle
        typing_need = bool_cast(get_in(self.config_data, ["settings", "typing", "require_self_rating"], True))
        lbl2 = self.make_text_label(
            getattr(labels, "settings_typing_require_self_rating", "Tippen: Selbstbewertung nach richtig"),
            size_hint_y=None, height=dp(50))
        cb2 = CheckBox(active=typing_need, size_hint=(None, None), size=(dp(36), dp(36)))

        def _set_typing(_inst, value):
            set_in(self.config_data, ["settings", "typing", "require_self_rating"], bool(value))
            save.save_settings(self.config_data)

        cb2.bind(active=_set_typing)
        grid2.add_widget(lbl2)
        grid2.add_widget(cb2)

        extra_card.add_widget(grid2)

        # 3) Global learn language filter button
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
        row.add_widget(
            self.make_text_label(getattr(labels, "settings_global_learn_languages", "Allgemeines Lernen: Sprachen"),
                                 size_hint=(0.55, 1), halign="left"))
        btn = self.make_secondary_button(
            getattr(labels, "settings_global_learn_languages_button", "Sprachen auswählen…"),
            size_hint=(0.45, 1))
        btn.bind(on_press=lambda _i: self._open_global_learn_language_popup())
        row.add_widget(btn)
        extra_card.add_widget(row)

        content.add_widget(extra_card)

        scroll.add_widget(content)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    # -----------------------
    # Settings callbacks
    # -----------------------

    def _on_setting_changed(self, path, cast_type):
        def cb(_instance, value):
            if cast_type is int:
                value = int(value)
            elif cast_type is float:
                value = float(value)
            set_in(self.config_data, path, value)
            save.save_settings(self.config_data)
            self.colors = apply_theme_from_config(self.config_data)
        return cb

    def on_mode_checkbox_changed(self, path):
        def handler(_instance, value):
            set_in(self.config_data, path, bool(value))
            save.save_settings(self.config_data)
            self.recompute_available_modes()
        return handler

    def recompute_available_modes(self):
        """
        Build available modes based on config and REAL vocab counts (global).
        """
        modes_cfg = get_in(self.config_data, ["settings", "modes"], {}) or {}
        total_vocab, unique_vocab = self._get_vocab_counts_for_modes()

        available = []
        if bool_cast(modes_cfg.get("front_back", True)):
            available.append("front_back")
        if bool_cast(modes_cfg.get("back_front", True)):
            available.append("back_front")
        if bool_cast(modes_cfg.get("letter_salad", True)):
            available.append("letter_salad")
        if bool_cast(modes_cfg.get("typing", True)):
            available.append("typing")

        if bool_cast(modes_cfg.get("multiple_choice", True)) and total_vocab >= 5:
            available.append("multiple_choice")
        if bool_cast(modes_cfg.get("connect_pairs", True)) and unique_vocab >= 5:
            available.append("connect_pairs")
        if bool_cast(modes_cfg.get("syllable_salad", True)) and total_vocab >= 3:
            available.append("syllable_salad")

        if not available:
            available = ["front_back"]

        self.available_modes = available

    def _open_global_learn_language_popup(self):
        # verfügbare Sprachen aus Stack-Meta sammeln
        langs = set()
        for f in self._list_stack_files():
            try:
                own, foreign, _latin, _latin_active = save.read_languages(f)
                if own: langs.add(str(own).strip())
                if foreign: langs.add(str(foreign).strip())
            except Exception:
                pass
        langs = sorted([l for l in langs if l])

        selected = set(get_in(self.config_data, ["settings", "global_learn_languages"], []) or [])

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        scroll = ScrollView(size_hint=(1, 1))
        inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        inner.bind(minimum_height=inner.setter("height"))

        for lang in langs:
            r = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
            r.add_widget(self.make_text_label(lang, size_hint=(0.75, 1), halign="left"))
            cb = CheckBox(active=(lang in selected), size_hint=(None, None), size=(dp(36), dp(36)))

            def _toggle(_cb, val, l=lang):
                if val:
                    selected.add(l)
                else:
                    selected.discard(l)

            cb.bind(active=_toggle)
            r.add_widget(cb)
            inner.add_widget(r)

        scroll.add_widget(inner)
        box.add_widget(scroll)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
        all_btn = self.make_secondary_button("Alle", size_hint=(0.33, 1))
        cancel_btn = self.make_secondary_button("Abbrechen", size_hint=(0.33, 1))
        ok_btn = self.make_primary_button("OK", size_hint=(0.34, 1))
        row.add_widget(all_btn)
        row.add_widget(cancel_btn)
        row.add_widget(ok_btn)
        box.add_widget(row)

        popup = Popup(title="Sprachen fürs allgemeine Lernen", content=box, size_hint=(0.9, 0.9))

        def _all(*_a):
            selected.clear()

        def _ok(*_a):
            set_in(self.config_data, ["settings", "global_learn_languages"], sorted(selected))
            save.save_settings(self.config_data)
            popup.dismiss()

        all_btn.bind(on_press=_all)
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        ok_btn.bind(on_press=_ok)

        popup.open()

    # -----------------------
    # Theme functions
    # -----------------------

    def set_theme_preset(self, preset_name: str):
        theme = self.config_data.setdefault("settings", {}).setdefault("theme", {})
        theme["preset"] = preset_name
        theme["base_preset"] = preset_name
        theme["custom_colors"] = {}
        save.save_settings(self.config_data)
        self.colors = apply_theme_from_config(self.config_data)
        self.settings()

    def set_custom_color(self, color_key: str, rgba):
        theme = self.config_data.setdefault("settings", {}).setdefault("theme", {})
        if "base_preset" not in theme:
            theme["base_preset"] = theme.get("preset", "dark")
        theme["preset"] = "custom"
        custom = theme.setdefault("custom_colors", {})
        custom[color_key] = [float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])]
        save.save_settings(self.config_data)
        self.colors = apply_theme_from_config(self.config_data)
        self.settings()

    def reset_custom_colors(self, _instance=None):
        theme = self.config_data.setdefault("settings", {}).setdefault("theme", {})
        base = theme.get("base_preset", "dark")
        theme["preset"] = base
        theme["custom_colors"] = {}
        save.save_settings(self.config_data)
        self.colors = apply_theme_from_config(self.config_data)
        self.settings()

    def open_color_picker(self, color_key: str):
        current = self.colors.get(color_key, (1, 1, 1, 1))
        picker = ColorPicker()
        picker.color = current

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(picker)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        ok_btn = self.make_primary_button(getattr(labels, "colorpicker_ok", "Übernehmen"), size_hint=(0.5, 1))
        cancel_btn = self.make_secondary_button(getattr(labels, "colorpicker_cancel", "Abbrechen"), size_hint=(0.5, 1))
        row.add_widget(cancel_btn)
        row.add_widget(ok_btn)
        content.add_widget(row)

        popup = Popup(title=f"Farbe wählen: {color_key}", content=content, size_hint=(0.9, 0.9))

        ok_btn.bind(on_press=lambda *_a: (self.set_custom_color(color_key, picker.color), popup.dismiss()))
        cancel_btn.bind(on_press=lambda *_a: popup.dismiss())
        popup.open()
