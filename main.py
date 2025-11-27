"""Main UI module for the Vokaba vocabulary trainer (Kivy app)."""

# Standard library imports
from datetime import datetime, timedelta
import os
import os.path
import random
import re
import unicodedata
import webbrowser
import sys
import subprocess

# Third-party imports
import yaml

# Kivy core / config
from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.animation import Animation

# Kivy layouts & widgets
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.popup import Popup


# Local modules
import labels
import save

# ---------------------------------------------------------------------------
# Global configuration and simple shared state
# ---------------------------------------------------------------------------

selected_stack = ""
global vocab_current
global title_size_slider
global three_columns_check
config = save.load_settings()


# ---------------------------------------------------------------------------
# Theme configuration (colors, basic layout constants)
# ---------------------------------------------------------------------------

THEME_PRESETS = {
    "dark": {
        "bg":            (18 / 255, 18 / 255, 26 / 255, 1),
        "primary":       (0.26, 0.60, 0.96, 1),
        "primary_dark":  (0.18, 0.45, 0.80, 1),
        "accent":        (1.00, 0.76, 0.03, 1),
        "text":          (1, 1, 1, 1),
        "muted":         (0.75, 0.75, 0.80, 1),
        "card":          (0.16, 0.17, 0.23, 1),
        "card_selected": (0.24, 0.25, 0.32, 1),
        "danger":        (0.90, 0.22, 0.21, 1),
        "success":       (0.20, 0.70, 0.30, 1),
    },
    "light": {
        "bg":            (0.96, 0.97, 1.0, 1),
        "primary":       (0.18, 0.45, 0.80, 1),
        "primary_dark":  (0.12, 0.32, 0.60, 1),
        "accent":        (1.00, 0.76, 0.03, 1),
        "text":          (0.10, 0.10, 0.14, 1),
        "muted":         (0.35, 0.38, 0.45, 1),
        "card":          (1, 1, 1, 1),
        "card_selected": (0.90, 0.93, 1.0, 1),
        "danger":        (0.80, 0.16, 0.18, 1),
        "success":       (0.18, 0.60, 0.28, 1),
    },
}

# Aktuelle Farbpalette – wird beim Start aus config gesetzt
APP_COLORS = THEME_PRESETS["dark"].copy()


def apply_theme_from_config():
    """
    Liest das Theme aus config und baut APP_COLORS:
      - preset: 'dark' / 'light' / 'custom'
      - base_preset: Basis für 'custom'
      - custom_colors: einzelne Farboverrides
    """
    global APP_COLORS, config

    settings = config.setdefault("settings", {})
    theme_cfg = settings.setdefault("theme", {})

    preset_name = theme_cfg.get("preset", "dark")

    if preset_name == "custom":
        base_name = theme_cfg.get("base_preset", "dark")
        base_palette = THEME_PRESETS.get(base_name, THEME_PRESETS["dark"]).copy()
        custom_colors = theme_cfg.get("custom_colors", {})
        for key, rgba in custom_colors.items():
            try:
                base_palette[key] = tuple(rgba)
            except Exception:
                pass
        palette = base_palette
    else:
        palette = THEME_PRESETS.get(preset_name, THEME_PRESETS["dark"]).copy()
        theme_cfg.setdefault("base_preset", preset_name)
        theme_cfg.setdefault("custom_colors", {})

    APP_COLORS.update(palette)

    try:
        Window.clearcolor = APP_COLORS["bg"]
    except Exception:
        pass

    # Default-Werte zurück in die config schreiben
    save.save_settings(config)


class RoundedCard(BoxLayout):
    """Card-like container with rounded corners and a solid background."""

    def __init__(self, bg_color=None, radius=None, **kwargs):
        self._bg_color_value = bg_color or APP_COLORS["card"]
        self._radius = radius or dp(18)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color = Color(*self._bg_color_value)
            self._bg_rect = RoundedRectangle(radius=[self._radius] * 4)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class RoundedButton(Button):
    """Button with rounded corners and a custom background color."""

    def __init__(self, bg_color=None, radius=None, **kwargs):
        # Store our own values before Kivy initializes the widget
        self._bg_color_value = bg_color or APP_COLORS["primary"]
        self._radius = radius or dp(18)

        super().__init__(**kwargs)

        # Disable the default Kivy button background
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        # Remove any existing canvas instructions and draw our own
        self.canvas.before.clear()

        with self.canvas.before:
            self._bg_color_instr = Color(*self._bg_color_value)
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self._radius] * 4,
            )

        # Keep the rounded background in sync with widget size/position
        self.bind(pos=self._update_bg, size=self._update_bg)

    def set_bg_color(self, rgba):
        """Allow the button background color to be changed dynamically."""
        self._bg_color_value = rgba
        if hasattr(self, "_bg_color_instr"):
            self._bg_color_instr.rgba = rgba

    def _update_bg(self, *args):
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size


def log(text):
    """Simple console logger with timestamp."""
    print("LOG  time: " + str(datetime.now())[11:] + '; content: "' + text + '"')


class NoScrollSlider(Slider):
    """
    Slider that only reacts to direct touches and does not scroll the parent
    ScrollView when dragged.
    """

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Grab the touch so further movement is routed to this slider
            touch.grab(self)
            return super().on_touch_down(touch)
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            return super().on_touch_move(touch)
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return super().on_touch_up(touch)
        return False


class VokabaApp(App):
    """Main Kivy application class for the Vokaba vocabulary trainer."""

    def build(self):
        # Theme aus config übernehmen (dark/light/custom)
        apply_theme_from_config()

        try:
            Window.size = (1280, 800)
        except Exception as e:
            log(f"Could not set window size: {e}")

        self.window = FloatLayout()
        self.scroll = ScrollView(size_hint=(1, 1))
        self.main_menu()
        return self.window


    # ------------------------------------------------------------------
    # Shared styling helpers
    # ------------------------------------------------------------------

    def make_title_label(self, text, **kwargs):
        """Create a centered title label using the configured title font size."""
        lbl = Label(
            text=text,
            color=APP_COLORS["text"],
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            **kwargs,
        )
        lbl.halign = "center"
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_text_label(self, text, **kwargs):
        """Create a body-text label using the configured text font size."""
        lbl = Label(
            text=text,
            color=APP_COLORS["muted"],
            font_size=int(config["settings"]["gui"]["text_font_size"]),
            **kwargs,
        )
        lbl.halign = kwargs.get("halign", "left")
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_primary_button(self, text, **kwargs):
        """Create a primary (accent-colored) rounded button."""
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"]),
        )
        return RoundedButton(
            text=text,
            bg_color=APP_COLORS["primary"],
            color=APP_COLORS["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_secondary_button(self, text, **kwargs):
        """Create a neutral, card-colored rounded button."""
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"]),
        )
        return RoundedButton(
            text=text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_danger_button(self, text, **kwargs):
        """Create a red rounded button for destructive actions."""
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"]),
        )
        return RoundedButton(
            text=text,
            bg_color=APP_COLORS["danger"],
            color=APP_COLORS["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_list_button(self, text, **kwargs):
        """Create a list-style button used for stack entries."""
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"]),
        )
        btn = RoundedButton(
            text=text,
            bg_color=APP_COLORS["card_selected"],   # graue Fläche
            color=APP_COLORS["text"],
            font_size=font_size,
            size_hint_y=None,
            height=dp(50),
            radius=dp(25),                 # macht das Ding „rund“ (Pill)
            **kwargs,
        )

        # Text linksbündig mit etwas Innenabstand
        btn.halign = "left"
        btn.valign = "middle"
        btn.padding = (dp(16), 0)

        # Text über die Breite umbrechen, damit halign greift
        def _update_text_size(inst, size):
            inst.text_size = (size[0] - dp(32), None)

        btn.bind(size=_update_text_size)

        return btn


    def get_icon_path(self, icon_path: str) -> str:
        """
        Wählt automatisch die *_black.png-Variante, wenn ein helles Theme aktiv ist.

        Beispiel:
            'assets/settings_icon.png' -> 'assets/settings_icon_black.png'
            (falls vorhanden und Theme ist 'light')
        """
        try:
            theme_cfg = config.get("settings", {}).get("theme", {})
            preset = theme_cfg.get("preset", "dark")
            base = theme_cfg.get("base_preset", preset)
            effective = base if preset == "custom" else preset
        except Exception:
            effective = "dark"

        if effective == "light":
            root, ext = os.path.splitext(icon_path)
            alt = f"{root}_black{ext}"
            if os.path.exists(alt):
                return alt

        return icon_path



    def make_icon_button(self, icon_path, on_press, size=dp(56), **kwargs):
        """Create an icon-only button from an image asset (theme-aware)."""
        icon_path = self.get_icon_path(icon_path)

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
        """Apply a theme-aware style to a TextInput (dark/light/custom)."""
        ti.background_normal = ""
        ti.background_active = ""
        # etwas Kontrast zum Kartenhintergrund, damit die Felder sichtbar sind
        ti.background_color = APP_COLORS.get("card_selected", APP_COLORS["card"])
        ti.foreground_color = APP_COLORS["text"]
        ti.cursor_color = APP_COLORS["accent"]
        ti.padding = [dp(8), dp(8), dp(8), dp(8)]
        return ti


    def _count_unique_vocab_pairs(self):
        """Return the number of unique (own_language, foreign_language) pairs."""
        seen = set()
        for e in getattr(self, "all_vocab_list", []):
            key = (e.get("own_language", ""), e.get("foreign_language", ""))
            seen.add(key)
        return len(seen)

    def _compute_overall_stats(self):
        """Sammelt globale Stats über alle Stacks."""
        stats = {
            "stacks": 0,
            "total_vocab": 0,
            "unique_pairs": 0,
            "learned_vocab": 0,
            "avg_knowledge": 0.0,
        }

        unique_pairs = set()
        total_knowledge = 0.0
        total_entries = 0

        vocab_path = getattr(labels, "vocab_path", "vocab")
        if not os.path.exists(vocab_path):
            os.makedirs(vocab_path)

        for name in os.listdir(vocab_path):
            full = os.path.join(vocab_path, name)
            if not os.path.isfile(full):
                continue

            stats["stacks"] += 1

            data = save.load_vocab(full)
            if isinstance(data, tuple):
                vocab_list = data[0]
            else:
                vocab_list = data

            stats["total_vocab"] += len(vocab_list)

            for e in vocab_list:
                own = e.get("own_language", "") or ""
                foreign = e.get("foreign_language", "") or ""
                if own or foreign:
                    unique_pairs.add((own, foreign))

                level_raw = e.get("knowledge_level", 0.0)
                try:
                    level = float(level_raw)
                except (TypeError, ValueError):
                    level = 0.0
                level = max(0.0, min(1.0, level))

                total_knowledge += level
                total_entries += 1

                # ab ~70 % Wissen als "gelernt" zählen
                if level >= 0.7:
                    stats["learned_vocab"] += 1

        stats["unique_pairs"] = len(unique_pairs)
        stats["avg_knowledge"] = (total_knowledge / total_entries) if total_entries else 0.0
        return stats


    # ------------------------------------------------------------------
    # Main menu
    # ------------------------------------------------------------------

    def main_menu(self, instance=None):
        """Build and display the main menu with the stack list and learn button."""
        log("opened main menu")
        self.window.clear_widgets()
        global config
        config = save.load_settings()
        Config.window_icon = "assets/vokaba_icon.png"

        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-left: logo button (opens about screen)
        top_left = AnchorLayout(
            anchor_x="left",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        vokaba_logo = self.make_icon_button(
            "assets/vokaba_logo.png",
            on_press=self.about,
            size=dp(104),
        )
        top_left.add_widget(vokaba_logo)
        self.window.add_widget(top_left)

        # Top-right: settings icon
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        settings_button = self.make_icon_button(
            "assets/settings_icon.png",
            on_press=self.settings,
            size=dp(56),
        )
        top_right.add_widget(settings_button)
        self.window.add_widget(top_right)

        # Top-center: Welcome + Stats gemeinsam, damit nichts abgeschnitten wird
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=[0, 30 * padding_mul, 0, 0],
        )

        # Vertikal-Box für Überschrift + Stats-Karte
        top_box = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(dp(700), dp(170)),  # etwas breiter und höher, damit alles Platz hat
            spacing=dp(12),
        )

        # Welcome-Text
        welcome_label = self.make_title_label(
            labels.welcome_text,
            size_hint=(1, None),
            height=dp(60),
        )
        # Text soll die ganze Breite nutzen
        welcome_label.bind(
            size=lambda inst, val: setattr(inst, "text_size", (val[0], None))
        )

        # Stats berechnen
        overall_stats = self._compute_overall_stats()
        stats_template = getattr(
            labels,
            "main_stats_label_template",
            "Stacks: {stacks}   Vokabeln: {total}   Einzigartige Paare: {unique}",
        )
        stats_text = stats_template.format(
            stacks=overall_stats["stacks"],
            total=overall_stats["total_vocab"],
            unique=overall_stats["unique_pairs"],
        )

        # Stats-Karte direkt unter dem Welcome-Label
        stats_card = RoundedCard(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(100),
            padding=dp(10),
            spacing=dp(6),
        )

        stats_label = self.make_text_label(
            stats_text,
            size_hint_y=None,
            height=dp(30),
        )

        hint_text = getattr(
            labels,
            "main_stats_hint",
            "Tipp: Klick auf „Lernen“ – Vokaba wählt automatisch passende Modi und Vokabeln.",
        )
        hint_label = self.make_text_label(
            hint_text,
            size_hint_y=None,
            height=dp(45),
        )

        stats_card.add_widget(stats_label)
        stats_card.add_widget(hint_label)

        # beides in die Box, Box in den Anchor, Anchor ins Fenster
        top_box.add_widget(welcome_label)
        top_box.add_widget(stats_card)
        top_center.add_widget(top_box)
        self.window.add_widget(top_center)


        overall_stats = self._compute_overall_stats()
        stats_template = getattr(
            labels,
            "main_stats_label_template",
            "Stacks: {stacks}   Vokabeln: {total}   Einzigartige Paare: {unique}",
        )
        stats_text = stats_template.format(
            stacks=overall_stats["stacks"],
            total=overall_stats["total_vocab"],
            unique=overall_stats["unique_pairs"],
        )

        stats_card = RoundedCard(
            orientation="vertical",
            size_hint=(0.7, None),
            height=dp(90),
            padding=dp(10),
            spacing=dp(6),
        )

        stats_label = self.make_text_label(
            stats_text,
            size_hint_y=None,
            height=dp(30),
        )

        hint_text = getattr(
            labels,
            "main_stats_hint",
            "Tipp: Klick auf „Lernen“ – Vokaba wählt automatisch passende Modi und Vokabeln.",
        )
        hint_label = self.make_text_label(
            hint_text,
            size_hint_y=None,
            height=dp(30),
        )

        stats_card.add_widget(stats_label)
        stats_card.add_widget(hint_label)


        # Center: card with scrollable list of vocab stacks (weiter unten)
        center_anchor = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=[60 * padding_mul, 180 * padding_mul, 60 * padding_mul, 60 * padding_mul],
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.8, 0.8),
            padding=dp(12),
            spacing=dp(8),
        )

        # Scrollable list of files in vocab_path
        vocab_path = getattr(labels, "vocab_path", "vocab")
        if not os.path.exists(vocab_path):
            os.makedirs(vocab_path)

        self.file_list = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.file_list.bind(minimum_height=self.file_list.setter("height"))

        for name in os.listdir(vocab_path):
            full = os.path.join(vocab_path, name)
            if os.path.isfile(full):
                btn = self.make_list_button(name[:-4])
                btn.bind(on_release=lambda btn, fname=name: self.select_stack(fname))
                self.file_list.add_widget(btn)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_y=True)
        self.file_list.bind(minimum_width=self.file_list.setter("width"))
        self.scroll.add_widget(self.file_list)
        card.add_widget(self.scroll)

        center_anchor.add_widget(card)
        self.window.add_widget(center_anchor)

        # Bottom-left: Dashboard-Button
        bottom_left = AnchorLayout(
            anchor_x="left",
            anchor_y="bottom",
            padding=30 * padding_mul,
        )
        dashboard_button = self.make_icon_button(
            "assets/dashboard_icon.png",
            on_press=self.open_dashboard,
            size=dp(56),
        )
        bottom_left.add_widget(dashboard_button)
        self.window.add_widget(bottom_left)

        # Bottom-right: add-stack FAB
        bottom_right = AnchorLayout(
            anchor_x="right",
            anchor_y="bottom",
            padding=30 * padding_mul,
        )
        add_stack_button = self.make_icon_button(
            "assets/add_stack.png",
            on_press=self.add_stack,
            size=dp(64),
        )
        bottom_right.add_widget(add_stack_button)
        self.window.add_widget(bottom_right)

        # Bottom-center: "learn random stacks" button
        self.recompute_available_modes()
        bottom_center = AnchorLayout(
            anchor_x="center",
            anchor_y="bottom",
            padding=12 * padding_mul,
        )

        learn_text = getattr(labels, "learn_stack_vocab_button_text")
        learn_button = self.make_primary_button(
            learn_text,
            size_hint=(None, None),
            size=(dp(220), dp(80)),
            font_size=dp(26),
        )
        learn_button.bind(
            on_press=lambda instance: self.learn(
                stack=None,
                mode=random.choice(self.available_modes),
            )
        )
        bottom_center.add_widget(learn_button)
        self.window.add_widget(bottom_center)


    # ------------------------------------------------------------------
    # Settings screen
    # ------------------------------------------------------------------

    def settings(self, instance):
        """Build and display the settings screen."""
        log("opened settings")
        self.window.clear_widgets()
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-right: back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Center: card with all settings
        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=40 * padding_mul,
        )
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.85),
            padding=dp(16),
            spacing=dp(12),
        )

        scroll = ScrollView(size_hint=(1, 1))
        settings_content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(16),
            padding=dp(4),
        )
        settings_content.bind(minimum_height=settings_content.setter("height"))

        # Sliders: title font size, body font size, padding multiplier
        settings_definitions = [
            {
                "label": labels.settings_title_font_size_slider_test_label,
                "min": 10,
                "max": 100,
                "value": float(config["settings"]["gui"]["title_font_size"]),
                "callback": self.on_setting_changed(
                    ["settings", "gui", "title_font_size"], int
                ),
            },
            {
                "label": labels.settings_font_size_slider,
                "min": 10,
                "max": 45,
                "value": float(config["settings"]["gui"]["text_font_size"]),
                "callback": self.on_setting_changed(
                    ["settings", "gui", "text_font_size"], int
                ),
            },
            {
                "label": labels.settings_padding_multiplikator_slider,
                "min": 0.1,
                "max": 3,
                "value": float(config["settings"]["gui"]["padding_multiplicator"]),
                "callback": self.on_setting_changed(
                    ["settings", "gui", "padding_multiplicator"], float
                ),
            },
        ]

        for setting in settings_definitions:
            row_card = RoundedCard(
                orientation="vertical",
                size_hint_y=None,
                height=dp(110),
                padding=dp(8),
                spacing=dp(4),
            )

            lbl = self.make_text_label(
                setting["label"],
                size_hint_y=None,
                height=dp(40),
            )

            slider = NoScrollSlider(
                min=setting["min"],
                max=setting["max"],
                value=setting["value"],
                size_hint_y=None,
                height=dp(40),
            )
            slider.bind(value=setting["callback"])

            row_card.add_widget(lbl)
            row_card.add_widget(slider)
            settings_content.add_widget(row_card)


        # kleiner Abstand nach den Slidern
        settings_content.add_widget(
            Label(size_hint_y=None, height=dp(12))
        )

        # Sessiongröße als Zahl-Eingabe
        def on_session_size_focus(instance, focused):
            # Nur reagieren, wenn der Fokus VERLOREN wird
            if focused:
                return
            txt = (instance.text or "").strip()
            try:
                num = int(txt)
            except (TypeError, ValueError):
                num = int(get_in(config, ["settings", "session_size"], 20) or 20)
            if num < 1:
                num = 1
            if num > 500:
                num = 500
            set_in(config, ["settings", "session_size"], num)
            save.save_settings(config)
            instance.text = str(num)

        session_card = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(90),
            padding=dp(8),
            spacing=dp(4),
        )

        session_label = self.make_text_label(
            getattr(
                labels,
                "settings_session_size_label",
                "Karten pro Lernsitzung",
            ),
            size_hint_y=None,
            height=dp(40),
        )

        session_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8),
        )

        current_session_size = str(
            int(get_in(config, ["settings", "session_size"], 20) or 20)
        )
        session_input = self.style_textinput(
            TextInput(
                text=current_session_size,
                multiline=False,
                size_hint=(0.3, 1),
                halign="center",
            )
        )
        session_input.input_filter = "int"
        session_input.bind(focus=on_session_size_focus)

        unit_label = self.make_text_label(
            getattr(labels, "settings_session_size_unit", "Karten"),
            size_hint_y=None,
            height=dp(40),
        )

        session_row.add_widget(session_input)
        session_row.add_widget(unit_label)

        session_card.add_widget(session_label)
        session_card.add_widget(session_row)
        settings_content.add_widget(session_card)


        # ------------------------------------------------------------------
        # Theme-Auswahl (Preset + individuelle Farben)
        # ------------------------------------------------------------------

        theme_header_text = getattr(
            labels,
            "settings_theme_header",
        )

        settings_content.add_widget(
            self.make_title_label(
                theme_header_text,
                size_hint_y=None,
                height=dp(40),
            )
        )

        theme_card = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(10),
        )
        # Höhe automatisch an Kinder anpassen
        theme_card.bind(minimum_height=theme_card.setter("height"))

        current_preset = config.get("settings", {}).get("theme", {}).get("preset", "dark")

        # Preset-Buttons (Dark / Light)
        preset_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(10),
        )

        dark_text = getattr(labels, "settings_theme_dark")
        light_text = getattr(labels, "settings_theme_light")

        dark_btn = self.make_secondary_button(
            dark_text,
            size_hint=(0.5, 1),
        )
        light_btn = self.make_secondary_button(
            light_text,
            size_hint=(0.5, 1),
        )

        # Aktives Theme optisch hervorheben
        if current_preset == "dark":
            dark_btn.set_bg_color(APP_COLORS["primary"])
        elif current_preset == "light":
            light_btn.set_bg_color(APP_COLORS["primary"])

        dark_btn.bind(on_press=lambda inst: self.set_theme_preset("dark"))
        light_btn.bind(on_press=lambda inst: self.set_theme_preset("light"))

        preset_row.add_widget(dark_btn)
        preset_row.add_widget(light_btn)
        theme_card.add_widget(preset_row)

        # Zeile 1: Primärfarbe + Akzentfarbe
        custom_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(10),
        )

        primary_text = getattr(labels, "settings_theme_primary")
        accent_text = getattr(labels, "settings_theme_accent")
        reset_text = getattr(labels, "settings_theme_reset")

        primary_btn = self.make_secondary_button(
            primary_text,
            size_hint=(0.5, 1),
        )
        primary_btn.set_bg_color(APP_COLORS["primary"])
        primary_btn.bind(on_press=lambda inst: self.open_color_picker("primary"))

        accent_btn = self.make_secondary_button(
            accent_text,
            size_hint=(0.5, 1),
        )
        accent_btn.set_bg_color(APP_COLORS["accent"])
        accent_btn.bind(on_press=lambda inst: self.open_color_picker("accent"))

        custom_row.add_widget(primary_btn)
        custom_row.add_widget(accent_btn)
        theme_card.add_widget(custom_row)

        # Zeile 2: Primärer + sekundärer Hintergrund + Reset
        bg_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(10),
        )

        bg_primary_text = getattr(labels, "settings_theme_bg_primary", "Hintergrund 1")
        bg_secondary_text = getattr(labels, "settings_theme_bg_secondary", "Hintergrund 2")

        bg_primary_btn = self.make_secondary_button(
            bg_primary_text,
            size_hint=(0.25, 1),
        )
        bg_primary_btn.set_bg_color(APP_COLORS["bg"])
        bg_primary_btn.bind(on_press=lambda inst: self.open_color_picker("bg"))

        bg_secondary_btn = self.make_secondary_button(
            bg_secondary_text,
            size_hint=(0.25, 1),
        )
        bg_secondary_btn.set_bg_color(APP_COLORS["card"])
        bg_secondary_btn.bind(on_press=lambda inst: self.open_color_picker("card"))

        reset_btn = self.make_secondary_button(
            reset_text,
            size_hint=(0.5, 1),
        )
        reset_btn.bind(on_press=self.reset_custom_colors)

        bg_row.add_widget(bg_primary_btn)
        bg_row.add_widget(bg_secondary_btn)
        bg_row.add_widget(reset_btn)

        theme_card.add_widget(bg_row)
        settings_content.add_widget(theme_card)

        # kleiner Abstand zwischen Theme und Lernmodi
        settings_content.add_widget(
            Label(size_hint_y=None, height=dp(24))
        )

        # ------------------------------------------------------------------
        # Learning mode toggles
        # ------------------------------------------------------------------
        modes_header_text = getattr(labels, "settings_modes_header")

        settings_content.add_widget(
            self.make_title_label(
                modes_header_text,
                size_hint_y=None,
                height=dp(40),
            )
        )

        modes_card = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(8),
            spacing=dp(8),
        )
        modes_card.bind(minimum_height=modes_card.setter("height"))

        grid = GridLayout(
            cols=2,
            size_hint_y=None,
            row_default_height=dp(50),
            row_force_default=True,
            spacing=dp(8),
            padding=(0, dp(4), 0, dp(4)),
        )
        grid.bind(minimum_height=grid.setter("height"))

        def add_mode_row(mode_key, mode_label):
            current = bool_cast(get_in(config, ["settings", "modes", mode_key], True))
            lbl = self.make_text_label(
                mode_label,
                size_hint_y=None,
                height=dp(50),
            )
            cb = CheckBox(
                active=current,
                size_hint=(None, None),
                size=(dp(36), dp(36)),  # etwas größer
            )
            cb.bind(
                active=self.on_mode_checkbox_changed(
                    ["settings", "modes", mode_key]
                )
            )
            return lbl, cb

        vocab_len_in_settings = len(getattr(self, "all_vocab_list", []))
        unique_vocab_len_in_settings = len(
            {
                (e.get("own_language", ""), e.get("foreign_language", ""))
                for e in getattr(self, "all_vocab_list", [])
            }
        )

        # front_back
        l1, c1 = add_mode_row(
            "front_back", labels.learn_flashcards_front_to_back
        )
        grid.add_widget(l1)
        grid.add_widget(c1)

        # back_front
        l2, c2 = add_mode_row(
            "back_front", labels.learn_flashcards_back_to_front
        )
        grid.add_widget(l2)
        grid.add_widget(c2)

        # multiple_choice
        l3, c3 = add_mode_row(
            "multiple_choice", labels.learn_flashcards_multiple_choice
        )
        if vocab_len_in_settings < 5:
            c3.disabled = True
            l3.text += labels.not_enougn_vocab_warning
            l3.markup = True
        grid.add_widget(l3)
        grid.add_widget(c3)

        # letter salad
        l4, c4 = add_mode_row(
            "letter_salad", labels.learn_flashcards_letter_salad
        )
        grid.add_widget(l4)
        grid.add_widget(c4)

        # connect 5 pairs
        l5, c5 = add_mode_row(
            "connect_pairs",
            getattr(
                labels,
                "learn_flashcards_connect_pairs",
            ),
        )
        if unique_vocab_len_in_settings < 5:
            c5.disabled = True
            l5.text += (
                labels.not_enougn_vocab_warning
            )
            l5.markup = True
        grid.add_widget(l5)
        grid.add_widget(c5)

        # typing input mode
        typing_label_text = getattr(
            labels, "learn_flashcards_typing_mode",
        )
        l6, c6 = add_mode_row("typing", typing_label_text)
        grid.add_widget(l6)
        grid.add_widget(c6)

        # syllable salad
        l_syl, c_syl = add_mode_row(
            "syllable_salad",
            getattr(
                labels,
                "learn_flashcards_syllable_salad",
                "Silben-Modus (Wörter aus Silben)",
            ),
        )
        if vocab_len_in_settings < 3:
            c_syl.disabled = True
            l_syl.text += labels.not_enougn_vocab_warning
            l_syl.markup = True
        grid.add_widget(l_syl)
        grid.add_widget(c_syl)

        modes_card.add_widget(grid)
        settings_content.add_widget(modes_card)


        scroll.add_widget(settings_content)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    # ------------------------------------------------------------------
    # About screen for Vokaba logo
    # ------------------------------------------------------------------


    def about(self, instance=None):
        """'Über Vokaba'-Screen mit Texten aus labels.py und Discord-Link."""
        log("opened about screen")
        self.window.clear_widgets()

        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-right: zurück zum Hauptmenü
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Top-center: Titel
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=[0, 30 * padding_mul, 0, 0],
        )
        title_label = self.make_title_label(
            getattr(labels, "about_title", "Über Vokaba"),
            size_hint=(None, None),
            size=(dp(400), dp(60)),
        )
        top_center.add_widget(title_label)
        self.window.add_widget(top_center)

        # Center: Card mit ScrollView für den Text
        center_anchor = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=40 * padding_mul,
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.8),
            padding=dp(16),
            spacing=dp(12),
        )

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(12),
            padding=dp(4),
        )
        content.bind(minimum_height=content.setter("height"))

        # Intro-Text
        intro = self.make_text_label(
            getattr(
                labels,
                "about_intro",
                "Vokaba ist ein super-minimalistischer Vokabeltrainer.",
            ),
            size_hint_y=None,
            height=dp(120),
        )
        content.add_widget(intro)

        # Abschnitt: smartes Lernsystem
        heading_learning = self.make_title_label(
            getattr(labels, "about_heading_learning", "Smartes Lernsystem"),
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(heading_learning)

        bullet_1 = self.make_text_label(
            getattr(
                labels,
                "about_bullet_adaptive",
                "• Adaptive Wiederholung …",
            ),
            size_hint_y=None,
            height=dp(80),
        )
        content.add_widget(bullet_1)

        bullet_2 = self.make_text_label(
            getattr(
                labels,
                "about_bullet_modes",
                "• Wechselnde Modi …",
            ),
            size_hint_y=None,
            height=dp(80),
        )
        content.add_widget(bullet_2)

        bullet_3 = self.make_text_label(
            getattr(
                labels,
                "about_bullet_csv",
                "• CSV-Stacks …",
            ),
            size_hint_y=None,
            height=dp(80),
        )
        content.add_widget(bullet_3)

        bullet_4 = self.make_text_label(
            getattr(
                labels,
                "about_bullet_design",
                "• Super-minimalistisches Design …",
            ),
            size_hint_y=None,
            height=dp(80),
        )
        content.add_widget(bullet_4)

        # Alpha-Hinweis
        alpha_label = self.make_text_label(
            getattr(
                labels,
                "about_alpha_label",
                "Diese Version ist ein früher Alpha-Release.",
            ),
            size_hint_y=None,
            height=dp(80),
        )
        content.add_widget(alpha_label)

        # Abschnitt: Discord / Support
        heading_discord = self.make_title_label(
            getattr(labels, "about_heading_discord", "Support & Discord"),
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(heading_discord)

        discord_text = self.make_text_label(
            getattr(
                labels,
                "about_discord_text",
                "Feedback und Bugreports sind sehr willkommen.",
            ),
            size_hint_y=None,
            height=dp(80),
        )
        content.add_widget(discord_text)

        # Discord-Link (hier deinen echten Invite eintragen)
        DISCORD_URL = "https://discord.gg/zRRmfgt8Cn"

        discord_button = self.make_primary_button(
            getattr(labels, "about_discord_button", "Discord öffnen"),
            size_hint=(1, None),
            height=dp(50),
        )
        discord_button.bind(
            on_press=lambda inst: webbrowser.open(DISCORD_URL)
        )
        content.add_widget(discord_button)

        # Klarer Text-Link zum Kopieren
        link_prefix = getattr(labels, "about_discord_link_prefix", "Link:")
        discord_link_label = self.make_text_label(
            f"{link_prefix} {DISCORD_URL}",
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(discord_link_label)

        scroll.add_widget(content)
        card.add_widget(scroll)
        center_anchor.add_widget(card)
        self.window.add_widget(center_anchor)

    # ------------------------------------------------------------------
    # Dashboard for showing statistics
    # ------------------------------------------------------------------

    def open_dashboard(self, instance=None):
        """Dashboard-Screen mit globalen Lern-Stats."""
        log("opened dashboard")
        self.window.clear_widgets()
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-right: zurück zum Hauptmenü
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Top-center: Titel
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=[0, 30 * padding_mul, 0, 0],
        )
        title_label = self.make_title_label(
            getattr(labels, "dashboard_title", "Dashboard"),
            size_hint=(None, None),
            size=(dp(400), dp(60)),
        )
        top_center.add_widget(title_label)
        self.window.add_widget(top_center)

        # Center: Card mit Inhalt
        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=40 * padding_mul,
        )
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.8),
            padding=dp(16),
            spacing=dp(12),
        )

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(12),
            padding=dp(4),
        )
        content.bind(minimum_height=content.setter("height"))

        overall = self._compute_overall_stats()
        stats_cfg = config.get("stats", {}) or {}

        # Lernzeit formatieren
        total_seconds = int(stats_cfg.get("total_learn_time_seconds", 0) or 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 0:
            time_str = f"{hours}h {minutes}min"
        else:
            time_str = f"{minutes}min"

        total_vocab = overall["total_vocab"] or 1
        learned = overall["learned_vocab"]
        progress_percent = (learned / total_vocab) * 100.0
        avg_knowledge_percent = overall["avg_knowledge"] * 100.0

        # Abschnitt: Überblick
        overview_header = self.make_title_label(
            getattr(labels, "dashboard_overview_header", "Überblick"),
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(overview_header)

        overview_card = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(4),
        )
        overview_card.bind(minimum_height=overview_card.setter("height"))

        overview_template = getattr(
            labels,
            "dashboard_overview_stats",
            "Stacks: {stacks}   Vokabeln: {total}   Einzigartige Paare: {unique}",
        )
        overview_label = self.make_text_label(
            overview_template.format(
                stacks=overall["stacks"],
                total=overall["total_vocab"],
                unique=overall["unique_pairs"],
            ),
            size_hint_y=None,
            height=dp(30),
        )
        overview_card.add_widget(overview_label)
        content.add_widget(overview_card)

        # Abschnitt: Lernfortschritt
        learning_header = self.make_title_label(
            getattr(labels, "dashboard_learning_header", "Lernfortschritt"),
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(learning_header)

        learning_card = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(4),
        )
        learning_card.bind(minimum_height=learning_card.setter("height"))

        progress_template = getattr(
            labels,
            "dashboard_learned_progress",
            "Gelernte Vokabeln: {learned}/{total} ({percent:.0f} %)",
        )
        progress_label = self.make_text_label(
            progress_template.format(
                learned=learned,
                total=overall["total_vocab"],
                percent=progress_percent,
            ),
            size_hint_y=None,
            height=dp(30),
        )
        learning_card.add_widget(progress_label)

        avg_template = getattr(
            labels,
            "dashboard_average_knowledge",
            "Durchschnittlicher Wissensstand: {avg:.0f} %",
        )
        avg_label = self.make_text_label(
            avg_template.format(avg=avg_knowledge_percent),
            size_hint_y=None,
            height=dp(30),
        )
        learning_card.add_widget(avg_label)

        time_template = getattr(
            labels,
            "dashboard_time_spent",
            "Gesamtlernzeit: {time}",
        )
        time_label = self.make_text_label(
            time_template.format(time=time_str),
            size_hint_y=None,
            height=dp(30),
        )
        learning_card.add_widget(time_label)

        content.add_widget(learning_card)

        # Optionaler Tipp
        hint_text = getattr(
            labels,
            "dashboard_hint",
            "Tipp: Lieber regelmäßig kurze Sessions als seltene Marathons.",
        )
        hint_label = self.make_text_label(
            hint_text,
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(hint_label)

        scroll.add_widget(content)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)


    # ------------------------------------------------------------------
    # Stack selection and detail screens
    # ------------------------------------------------------------------

    def select_stack(self, stack):
        """Show actions for a single stack (add/edit vocab, learn, delete)."""
        vocab_file = str("vocab/" + stack)
        vocab_current = save.load_vocab(vocab_file)
        if "tuple" in str(type(vocab_current)):
            vocab_current = vocab_current[0]
        log("opened stack: " + stack)
        self.window.clear_widgets()
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-center: stack title
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=15 * padding_mul,
        )
        stack_title_label = self.make_title_label(
            stack[:-4],
            size_hint=(None, None),
            size=(dp(300), dp(40)),
        )
        top_center.add_widget(stack_title_label)
        self.window.add_widget(top_center)

        # Top-right: back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Center: card with actions for this stack
        center_anchor = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=[30, 60, 100, 30],
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.7),
            padding=dp(16),
            spacing=dp(12),
        )

        scroll = ScrollView(size_hint=(1, 1), do_scroll_y=True)
        grid = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        # Ordner mit Vokabel-SVGs öffnen
        open_folder_text = getattr(
            labels,
            "open_stack_folder_button_text",
            "Ordner mit Vokabel-SVGs öffnen",
        )
        open_folder_button = self.make_secondary_button(
            open_folder_text,
            size_hint_y=None,
            height=dp(60),
        )
        open_folder_button.bind(
            on_press=lambda instance: self.open_stack_folder(stack)
        )
        grid.add_widget(open_folder_button)

        # Edit vocab
        edit_vocab_button = self.make_secondary_button(
            labels.edit_vocab_button_text,
            size_hint_y=None,
            height=dp(60),
        )
        edit_vocab_button.bind(
            on_press=lambda instance: self.edit_vocab(stack, vocab_current)
        )
        grid.add_widget(edit_vocab_button)

        # Edit metadata
        edit_metadata_button = self.make_secondary_button(
            labels.edit_metadata_button_text,
            size_hint_y=None,
            height=dp(60),
        )
        edit_metadata_button.bind(
            on_press=lambda instance: self.edit_metadata(stack)
        )
        grid.add_widget(edit_metadata_button)

        # Delete stack
        delete_stack_button = self.make_danger_button(
            labels.delete_stack_button,
            size_hint_y=None,
            height=dp(60),
        )
        delete_stack_button.bind(
            on_press=lambda instance: self.delete_stack_confirmation(stack)
        )
        grid.add_widget(delete_stack_button)


        # Add vocab
        add_vocab_button = self.make_primary_button(
            labels.add_vocab_button_text,
            size_hint_y=None,
            height=dp(60),
        )
        add_vocab_button.bind(
            on_press=lambda instance: self.add_vocab(stack, vocab_current)
        )
        grid.add_widget(add_vocab_button)

        # Learn this stack
        self.recompute_available_modes()
        learn_vocab_button = self.make_primary_button(
            labels.learn_stack_vocab_button_text,
            size_hint_y=None,
            height=dp(60),
        )
        learn_vocab_button.bind(
            on_press=lambda instance: self.learn(
                stack, mode=random.choice(self.available_modes)
            )
        )
        grid.add_widget(learn_vocab_button)

        scroll.add_widget(grid)
        card.add_widget(scroll)
        center_anchor.add_widget(card)
        self.window.add_widget(center_anchor)


    def open_stack_folder(self, stack, instance=None):
        """
        Öffnet den Ordner für diesen Stack im Dateimanager.
        Wenn es einen Unterordner mit dem Stacknamen gibt (z.B. vocab/<stackname>/),
        wird dieser geöffnet, sonst der allgemeine vocab-Ordner.
        """
        # Basis-Vokabelordner (falls in labels.vocab_path konfiguriert)
        vocab_root = getattr(labels, "vocab_path", "vocab")

        # Kandidat: Unterordner mit gleichem Namen wie die CSV (ohne .csv)
        base_name = os.path.splitext(stack)[0]
        candidate = os.path.join(vocab_root, base_name)

        if os.path.isdir(candidate):
            target = os.path.abspath(candidate)
        else:
            target = os.path.abspath(vocab_root)

        log(f"Opening folder: {target}")

        try:
            if os.name == "nt":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as e:
            log(f"Could not open folder '{target}': {e}")


    def delete_stack_confirmation(self, stack, instance=None):
        """Confirmation dialog before deleting an entire stack."""
        log("Entered delete stack Confirmation")
        self.window.clear_widgets()
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-right: back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Center: warning card
        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=40 * padding_mul,
        )
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.8, 0.6),
            padding=dp(16),
            spacing=dp(12),
            bg_color=(0.25, 0.10, 0.10, 1),
        )

        caution_text = self.make_title_label(
            labels.caution,
            size_hint_y=None,
            height=dp(40),
        )
        caution_text.markup = True

        deleting_text = self.make_text_label(
            labels.delete_stack_confirmation_text,
            size_hint_y=None,
            height=dp(60),
        )
        deleting_text.markup = True

        not_undone_text = self.make_text_label(
            labels.cant_be_undone,
            size_hint_y=None,
            height=dp(40),
        )
        not_undone_text.markup = True

        card.add_widget(caution_text)
        card.add_widget(deleting_text)
        card.add_widget(not_undone_text)

        # Bottom row: cancel / delete
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            spacing=dp(12),
        )

        cancel_btn = self.make_secondary_button(labels.cancel)
        cancel_btn.bind(on_press=lambda instance: self.select_stack(stack))

        delete_btn = self.make_danger_button(labels.delete)
        delete_btn.markup = True
        delete_btn.bind(on_press=lambda instance: self.delete_stack(stack))

        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(delete_btn)

        card.add_widget(btn_row)
        center.add_widget(card)
        self.window.add_widget(center)

    # ------------------------------------------------------------------
    # Stack creation
    # ------------------------------------------------------------------

    def add_stack(self, instance):
        """Screen for creating a new stack and its basic metadata."""
        self.window.clear_widgets()
        log("opened add stack menu")
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-right: back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Top-center: title
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        add_stack_label = self.make_title_label(
            labels.add_stack_title_text,
            size_hint=(None, None),
            size=(dp(300), dp(40)),
        )
        top_center.add_widget(add_stack_label)
        self.window.add_widget(top_center)

        # Center: card with text fields
        center_center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=40 * padding_mul,
        )
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.7),
            padding=dp(16),
            spacing=dp(12),
        )

        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(
            cols=1,
            spacing=dp(10),
            padding=dp(8),
            size_hint_y=None,
        )
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Stack filename
        form_layout.add_widget(
            self.make_text_label(
                labels.add_stack_filename,
                size_hint_y=None,
                height=dp(40),
            )
        )
        self.stack_input = self.style_textinput(
            TextInput(
            size_hint_y=None,
            height=dp(60),
            multiline=False,
            )
        )
        form_layout.add_widget(self.stack_input)

        # Own language
        form_layout.add_widget(
            self.make_text_label(
                labels.add_own_language,
                size_hint_y=None,
                height=dp(24),
            )
        )
        self.own_language_input = self.style_textinput(
            TextInput(
            size_hint_y=None,
            height=dp(60),
            multiline=False,
            )
        )

        form_layout.add_widget(self.own_language_input)

        # Foreign language
        form_layout.add_widget(
            self.make_text_label(
                labels.add_foreign_language,
                size_hint_y=None,
                height=dp(24),
            )
        )
        self.foreign_language_input = self.style_textinput(
            TextInput(
            size_hint_y=None,
            height=dp(60),
            multiline=False,
        ))
        form_layout.add_widget(self.foreign_language_input)

        # Optional third column (Latin)
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(10),
        )
        row.add_widget(
            self.make_text_label(
                labels.three_digit_toggle,
                size_hint_y=None,
                height=dp(30),
            )
        )
        self.three_columns = CheckBox(
            active=False,
            size_hint=(None, None),
            size=(dp(36), dp(36)),
        )
        self.three_columns.bind(active=self.three_column_checkbox)
        row.add_widget(self.three_columns)
        form_layout.add_widget(row)

        # Submit button
        add_stack_button = self.make_primary_button(
            labels.add_stack_button_text,
            size_hint=(1, None),
            height=dp(60),
        )
        add_stack_button.bind(on_press=self.add_stack_button_func)
        form_layout.add_widget(add_stack_button)

        scroll.add_widget(form_layout)
        card.add_widget(scroll)
        center_center.add_widget(card)
        self.window.add_widget(center_center)

        # Bottom-center: error label for validation messages
        self.bottom_center = AnchorLayout(
            anchor_x="center",
            anchor_y="bottom",
            padding=30 * padding_mul,
        )
        self.add_stack_error_label = self.make_title_label(
            "",
            size_hint=(None, None),
            size=(dp(400), dp(40)),
        )
        self.bottom_center.add_widget(self.add_stack_error_label)
        self.window.add_widget(self.bottom_center)

    def on_setting_changed(self, key_path, cast_type):
        """
        Return a slider callback that updates a value inside the nested
        settings dict and persists it to disk.
        """

        def callback(instance, value):
            if cast_type == int:
                value = int(value)
            elif cast_type == float:
                value = float(value)

            ref = config
            for key in key_path[:-1]:
                ref = ref[key]
            ref[key_path[-1]] = value

            log(f"{key_path[-1]} updated to {value}")
            save.save_settings(config)
            log("config saved")

        return callback


    def set_theme_preset(self, preset_name, instance=None):
        """
        Theme-Preset wechseln ('dark' / 'light'), config aktualisieren,
        Custom-Farben zurücksetzen und Settings neu aufbauen.
        """
        global config

        settings_dict = config.setdefault("settings", {})
        theme_dict = settings_dict.setdefault("theme", {})
        theme_dict["preset"] = preset_name
        theme_dict["base_preset"] = preset_name
        theme_dict["custom_colors"] = {}

        save.save_settings(config)
        apply_theme_from_config()

        # Settings-Screen neu aufbauen, damit alles direkt aktualisiert ist
        self.settings(None)


    def set_custom_color(self, color_key: str, rgba, instance=None):
        """
        Einzelne Farbe (z.B. 'primary', 'accent') überschreiben und als 'custom'-Theme speichern.
        """
        global config

        settings_dict = config.setdefault("settings", {})
        theme_dict = settings_dict.setdefault("theme", {})

        if "base_preset" not in theme_dict:
            theme_dict["base_preset"] = theme_dict.get("preset", "dark")

        theme_dict["preset"] = "custom"
        custom = theme_dict.setdefault("custom_colors", {})
        custom[color_key] = [float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])]

        save.save_settings(config)
        apply_theme_from_config()
        self.settings(None)

    def reset_custom_colors(self, instance=None):
        """
        Custom-Farben löschen und zurück zum Basis-Preset wechseln.
        """
        global config

        settings_dict = config.setdefault("settings", {})
        theme_dict = settings_dict.setdefault("theme", {})
        base = theme_dict.get("base_preset", "dark")

        theme_dict["preset"] = base
        theme_dict["custom_colors"] = {}

        save.save_settings(config)
        apply_theme_from_config()
        self.settings(None)

    def open_color_picker(self, color_key: str, instance=None):
        """
        Öffnet einen ColorPicker in einem Popup, um eine Theme-Farbe zu wählen.
        """
        current_color = APP_COLORS.get(color_key, (1, 1, 1, 1))

        picker = ColorPicker()
        picker.color = current_color

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        content.add_widget(picker)

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8),
        )

        ok_text = getattr(labels, "colorpicker_ok", "Übernehmen")
        cancel_text = getattr(labels, "colorpicker_cancel", "Abbrechen")

        ok_btn = self.make_primary_button(ok_text, size_hint=(0.5, 1))
        cancel_btn = self.make_secondary_button(cancel_text, size_hint=(0.5, 1))

        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(ok_btn)
        content.add_widget(btn_row)

        popup = Popup(
            title=f"Farbe wählen: {color_key}",
            content=content,
            size_hint=(0.9, 0.9),
        )

        def apply_and_close(*args):
            self.set_custom_color(color_key, picker.color)
            popup.dismiss()

        def close_only(*args):
            popup.dismiss()

        ok_btn.bind(on_press=apply_and_close)
        cancel_btn.bind(on_press=close_only)

        popup.open()


    def add_stack_button_func(self, instance=None):
        """Validate the new stack form and create the stack on disk."""
        log("starting save")
        stackname = self.stack_input.text.strip()
        own_language = self.own_language_input.text.strip()
        foreign_language = self.foreign_language_input.text.strip()
        latin_active = self.three_columns.active
        log("reading textbox finished")

        if stackname and own_language and foreign_language:
            if stackname[-4:] == ".csv":
                actual_stackname = stackname
            else:
                actual_stackname = str(stackname + ".csv")

            if not os.path.isfile("vocab/" + actual_stackname):
                open("vocab/" + actual_stackname, "a").close()
                log(f"Created file: {actual_stackname}")

                save.save_to_vocab(
                    vocab=[],
                    filename="vocab/" + actual_stackname,
                    own_lang=own_language,
                    foreign_lang=foreign_language,
                    latin_lang="Latein",
                    latin_active=latin_active,
                )
                log("Added language info and Latin column state")
                self.main_menu()
            else:
                log("Saving failed, file already exists.")
                self.add_stack_error_label.text = (
                    labels.add_stack_title_text_exists
                )
        else:
            log("Saving failed, one or more input boxes empty.")
            self.add_stack_error_label.text = labels.add_stack_title_text_empty

    # ------------------------------------------------------------------
    # Unified learning entry point
    # ------------------------------------------------------------------

    def learn(self, stack=None, mode="front_back", instance=None):
        """
        Build the shared learning layout and prepare the list of vocab entries.

        Der übergebene mode wird nur noch geloggt; die eigentliche
        Moduswahl passiert pro Vokabel abhängig von knowledge_level.
        """
        log(f"entered learn menu with requested mode={mode}")
        # Modus wird jetzt dynamisch gewählt
        self.learn_mode = None
        self.self_rating_enabled = True  # Anki-style Selbstkontrolle

        self.window.clear_widgets()

        # Startzeit der Session (für Dashboard-Lernzeit)
        self.session_start_time = datetime.now()

        # Static container for all learning screens
        self.learn_area = FloatLayout()

        # Static container for all learning screens
        self.learn_area = FloatLayout()
        self.window.add_widget(self.learn_area)

        # Content area that is replaced per card/mode
        self.learn_content = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        self.learn_area.add_widget(self.learn_content)

        # Header label (optional title above learning content)
        self.header_anchor = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        self.header_label = Label(
            text="",
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(None, None),
            size=(80, 40),
        )
        self.header_anchor.add_widget(self.header_label)
        self.learn_area.add_widget(self.header_anchor)

        # Top-right back button (saves knowledge levels before leaving)
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.exit_learning,
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.learn_area.add_widget(top_right)

        # Build the vocab list for this session (single stack or all stacks)
        self.all_vocab_list = []
        self.stack_vocab_lists = {}
        self.stack_meta_map = {}
        self.entry_to_stack_file = {}

        self.is_back = False
        self.current_vocab_index = 0

        filenames = []
        if stack:
            filenames.append("vocab/" + stack)
        else:
            if not os.path.exists("vocab"):
                os.makedirs("vocab")
            for name in os.listdir("vocab/"):
                full = os.path.join("vocab", name)
                if os.path.isfile(full):
                    filenames.append(full)

        for filename in filenames:
            data = save.load_vocab(filename)
            # wie im restlichen Code: load_vocab kann Liste oder Tuple liefern
            if isinstance(data, tuple):
                vocab_list = data[0]
            else:
                vocab_list = data

            own_lang, foreign_lang, latin_lang, latin_active = save.read_languages(
                filename
            )

            self.stack_vocab_lists[filename] = vocab_list
            self.stack_meta_map[filename] = (
                own_lang,
                foreign_lang,
                latin_lang,
                latin_active,
            )

            for entry in vocab_list:
                # Zuordnung: welches Entry gehört zu welcher Datei?
                self.entry_to_stack_file[id(entry)] = filename
                # Safety: knowledge_level immer vorhanden
                if "knowledge_level" not in entry:
                    entry["knowledge_level"] = 0.0
                # evtl. alte Helper-Felder loswerden
                entry.pop("_stack_file", None)

                self.all_vocab_list.append(entry)

        random.shuffle(self.all_vocab_list)
        self.max_current_vocab_index = len(self.all_vocab_list)

        if self.max_current_vocab_index == 0:
            log("no vocab to learn")
            self.window.clear_widgets()
            msg_anchor = AnchorLayout(
                anchor_x="center",
                anchor_y="center",
            )
            msg_anchor.add_widget(
                Label(
                    text=labels.no_vocab_warning,
                    font_size=int(
                        config["settings"]["gui"]["title_font_size"]
                    ),
                )
            )
            self.window.add_widget(msg_anchor)
            return

        # Session-Zähler initialisieren (Tagesziel/Sessiongroße)
        self.session_cards_total = int(
            get_in(config, ["settings", "session_size"], 20) or 20
        )
        if self.session_cards_total < 1:
            self.session_cards_total = 1
        self.session_cards_done = 0
        self.session_correct = 0
        self.session_wrong = 0

        # Nur Modi erlauben, die aktiviert sind und für die genug Vokabeln da sind
        self.recompute_available_modes()

        # Startvokabel & Startmodus nach knowledge_level wählen
        self.current_vocab_index = self._pick_next_vocab_index(avoid_current=False)
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())

        self.show_current_card()



    # ------------------------------------------------------------------
    # Card routing depending on mode
    # ------------------------------------------------------------------

    def show_current_card(self):
        """Route to the correct UI for the current vocab entry and mode."""
        self.learn_content.clear_widgets()
        current_vocab = self.all_vocab_list[self.current_vocab_index]

        if self.learn_mode == "front_back":
            text = (
                current_vocab["own_language"]
                if not self.is_back
                else self._format_backside(current_vocab)
            )
            self.show_button_card(text, self.flip_card_learn_func)

        elif self.learn_mode == "back_front":
            text = (
                current_vocab["foreign_language"]
                if not self.is_back
                else current_vocab["own_language"]
            )
            self.show_button_card(text, self.flip_card_learn_func)

        elif self.learn_mode == "multiple_choice":
            self.multiple_choice()

        elif self.learn_mode == "letter_salad":
            self.letter_salad()

        elif self.learn_mode == "connect_pairs":
            self.connect_pairs_mode()

        elif self.learn_mode == "typing":
            self.typing_mode()

        elif self.learn_mode == "syllable_salad":
            self.syllable_salad()

        else:
            log(f"Unknown learn mode {self.learn_mode}, fallback to front_back")
            self.learn(None, "front_back")


    def show_button_card(self, text, callback):
        """Simple flashcard screen: one big button + optional self-rating row."""
        if hasattr(self, "header_label"):
            self.header_label.text = ""

        center_center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.7, 0.6),
            padding=dp(12),
            spacing=dp(8),
        )

        self.front_side_label = RoundedButton(
            text=text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(1, 0.8),
        )
        self.front_side_label.bind(on_press=callback)
        card.add_widget(self.front_side_label)

        # Self-rating buttons (Anki-like) only for front/back modes
        self.selfrating_box = None
        if getattr(self, "self_rating_enabled", False) and self.learn_mode in (
            "front_back",
            "back_front",
        ):
            self.selfrating_box = BoxLayout(
                orientation="horizontal",
                size_hint=(1, 0.2),
                spacing=dp(8),
            )

            buttons = [
                ("self_rating_very_easy", "very_easy"),
                ("self_rating_easy", "easy"),
                ("self_rating_hard", "hard"),
                ("self_rating_very_hard", "very_hard"),
            ]
            for label_name, quality in buttons:
                text_label = getattr(labels, label_name, quality)
                btn = self.make_secondary_button(
                    text_label,
                    size_hint=(0.25, 1),
                )
                btn.bind(
                    on_press=lambda inst, q=quality: self.self_rate_card(q)
                )
                self.selfrating_box.add_widget(btn)

            # initially hidden; becomes visible when back side is shown
            self.selfrating_box.opacity = 0
            self.selfrating_box.disabled = True

            card.add_widget(self.selfrating_box)

        center_center.add_widget(card)
        self.learn_content.add_widget(center_center)


    def self_rate_card(self, quality):
        """
        Self-assessment for flashcards (front/back, back/front), Anki style.

        quality: 'very_easy', 'easy', 'hard', 'very_hard'
        """
        if not getattr(self, "all_vocab_list", None):
            return

        current_vocab = self.all_vocab_list[self.current_vocab_index]

        if quality == "very_easy":
            delta = getattr(labels, "knowledge_delta_self_very_easy", 0.09)
        elif quality == "easy":
            delta = getattr(labels, "knowledge_delta_self_easy", 0.05)
        elif quality == "hard":
            delta = getattr(labels, "knowledge_delta_self_hard", -0.01)
        elif quality == "very_hard":
            delta = getattr(labels, "knowledge_delta_self_very_hard", -0.08)
        else:
            delta = 0.0

        self._adjust_knowledge_level(current_vocab, delta)

        # SRS-Update auf Basis des Self-Ratings
        if quality == "very_easy":
            q_val = 1.0
            was_correct = True
        elif quality == "easy":
            q_val = 0.75
            was_correct = True
        elif quality == "hard":
            q_val = 0.4
            was_correct = False
        elif quality == "very_hard":
            q_val = 0.1
            was_correct = False
        else:
            q_val = 0.5
            was_correct = False

        self.update_srs(current_vocab, was_correct=was_correct, quality=q_val)

        # Session-Schritt verbuchen
        was_correct_session = quality in ("very_easy", "easy")
        if self._register_session_step(was_correct_session):
            return

        # Nächste Vokabel (low score = höhere Wahrscheinlichkeit) + passenden Modus wählen
        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()


    # ------------------------------------------------------------------
    # Session-Tracking (Tagesziel / Lernsitzungen)
    # ------------------------------------------------------------------

    def _register_session_step(self, was_correct=None, steps=1):
        """
        Aktualisiert die Session-Zähler.

        Gibt True zurück, wenn die Session damit abgeschlossen ist und
        ein Summary-Screen angezeigt werden soll.

        steps = wie viele „Karten“ gezählt werden (z.B. 5 bei Connect-Pairs).
        """
        if not hasattr(self, "session_cards_total"):
            return False

        try:
            steps = int(steps)
        except (TypeError, ValueError):
            steps = 1
        if steps < 1:
            steps = 1

        self.session_cards_done = getattr(self, "session_cards_done", 0) + steps

        if was_correct is True:
            self.session_correct = getattr(self, "session_correct", 0) + steps
        elif was_correct is False:
            self.session_wrong = getattr(self, "session_wrong", 0) + steps

        if self.session_cards_done >= self.session_cards_total:
            self.show_session_summary()
            return True
        return False

    def show_session_summary(self):
        """Kleiner Abschluss-Screen für eine Lernsitzung."""
        self.learn_content.clear_widgets()

        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=40 * padding_mul,
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.8, 0.6),
            padding=dp(16),
            spacing=dp(12),
        )

        title_text = getattr(
            labels,
            "session_summary_title",
            "Session abgeschlossen",
        )
        title_lbl = self.make_title_label(
            title_text,
            size_hint_y=None,
            height=dp(40),
        )
        card.add_widget(title_lbl)

        total = getattr(self, "session_cards_done", 0)
        correct = getattr(self, "session_correct", 0)
        wrong = getattr(self, "session_wrong", 0)
        goal = getattr(self, "session_cards_total", total)

        text_template = getattr(
            labels,
            "session_summary_text",
            "Du hast {done} Karten in dieser Session abgeschlossen.\n"
            "Richtig: {correct}   Schwer / falsch: {wrong}\n"
            "Session-Ziel: {goal} Karten.",
        )

        body_lbl = self.make_text_label(
            text_template.format(
                done=total,
                correct=correct,
                wrong=wrong,
                goal=goal,
            ),
            size_hint_y=None,
            height=dp(120),
        )
        card.add_widget(body_lbl)

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(12),
        )

        cont_text = getattr(
            labels,
            "session_summary_continue_button",
            "Weiterlernen",
        )
        back_text = getattr(
            labels,
            "session_summary_back_button",
            "Zurück zum Hauptmenü",
        )

        cont_btn = self.make_primary_button(
            cont_text,
            size_hint=(0.5, 1),
        )
        back_btn = self.make_secondary_button(
            back_text,
            size_hint=(0.5, 1),
        )

        def _continue(*args):
            # Neue Session mit den gleichen Einstellungen starten
            self.session_cards_done = 0
            self.session_correct = 0
            self.session_wrong = 0
            self.show_current_card()

        def _back(*args):
            self.exit_learning()

        cont_btn.bind(on_press=_continue)
        back_btn.bind(on_press=_back)

        btn_row.add_widget(back_btn)
        btn_row.add_widget(cont_btn)

        card.add_widget(btn_row)
        center.add_widget(card)
        self.learn_content.add_widget(center)


    def _format_backside(self, vocab):
        """Combine back-side text (foreign, info, optional Latin) into one string."""
        back = vocab.get("foreign_language", "")
        additional = vocab.get("info", "")
        latin = vocab.get("latin_language")
        return (
            f"{back}\n\n{additional}\n\n{latin}"
            if latin
            else f"{back}\n\n{additional}"
        )

    def _format_answer_lines(self, vocab):
        """
        Helper für Nicht-Flashcard-Modi: kombiniert Fremdsprache,
        dritte Spalte und Info auf mehreren Zeilen.
        """
        foreign = (vocab.get("foreign_language") or "").strip()
        latin = (vocab.get("latin_language") or "").strip()
        info = (vocab.get("info") or "").strip()

        lines = []
        if foreign:
            lines.append(foreign)
        if latin:
            lines.append(latin)
        if info:
            lines.append(info)

        return "\n".join(lines) if lines else ""


    def _scramble_word(self, word: str) -> str:
        """Return a shuffled version of `word` that is usually different."""
        letters = list(word)
        if len(letters) <= 1:
            return word

        for _ in range(20):
            random.shuffle(letters)
            scrambled = "".join(letters)
            if scrambled != word:
                return scrambled
        return "".join(letters)

    def _strip_accents(self, ch: str) -> str:
        """Gibt den Buchstaben ohne Akzente zurück (é -> e)."""
        decomposed = unicodedata.normalize("NFD", ch)
        return "".join(c for c in decomposed if not unicodedata.combining(c))

    def _remove_parenthetical(self, text: str) -> str:
        """Entfernt alles in Klammern inkl. der Klammern."""
        if not text:
            return ""
        result = []
        in_parens = False
        for ch in text:
            if ch == "(":
                in_parens = True
                continue
            if ch == ")":
                in_parens = False
                continue
            if in_parens:
                continue
            result.append(ch)
        return "".join(result)

    def _normalize_for_compare(self, text: str) -> str:
        """
        Normalisiert Text für den inhaltlichen Vergleich:
        - entfernt Klammern + Inhalt
        - ignoriert alles außer Buchstaben
        - entfernt Akzente, vergleicht in lowercase
        """
        if not text:
            return ""
        no_par = self._remove_parenthetical(text)
        letters = []
        for ch in no_par:
            if ch.isalpha():
                base = self._strip_accents(ch).lower()
                letters.append(base)
        return "".join(letters)

    def _extract_main_lexeme(self, text: str) -> str:
        """
        Extrahiert das 'Hauptwort' aus einem Wörterbucheintrag.
        Beispiele:
            '(to) walk' -> 'walk'
            'to walk'   -> 'walk'
        """
        if not text:
            return ""
        no_par = self._remove_parenthetical(text)
        parts = no_par.strip().split()
        if not parts:
            return no_par.strip()
        # einfache Heuristik: letztes Wort
        return parts[-1]

    def _letters_outside_parentheses(self, text: str):
        """
        Liefert eine Liste (index, char) für Buchstaben, die NICHT in Klammern stehen.
        """
        letters = []
        in_parens = False
        for idx, ch in enumerate(text):
            if ch == "(":
                in_parens = True
                continue
            if ch == ")":
                in_parens = False
                continue
            if in_parens:
                continue
            if ch.isalpha():
                letters.append((idx, ch))
        return letters

    def _is_correct_typed_answer(self, typed: str, vocab: dict) -> bool:
        """
        Prüft, ob die getippte Antwort inhaltlich richtig ist:
        - ignoriert Akzente, Leerzeichen, Satzzeichen, Klammern
        - mehrere Lösungen getrennt durch ; , / sind erlaubt
        - akzeptiert sowohl den kompletten Eintrag als auch das Hauptwort
          (z.B. 'walk' ist korrekt für '(to) walk' oder 'to walk')
        """
        foreign = vocab.get("foreign_language", "") or ""
        parts = re.split(r"[;,/]", foreign)
        candidates = [p for p in parts if p.strip()] or [foreign]

        typed_norm = self._normalize_for_compare(typed)
        if not typed_norm:
            return False

        for cand in candidates:
            cand_norm_full = self._normalize_for_compare(cand)
            cand_main = self._extract_main_lexeme(cand)
            cand_norm_main = self._normalize_for_compare(cand_main)

            if typed_norm == cand_norm_full or typed_norm == cand_norm_main:
                return True

        return False

    def _classify_typed_vs_solution(self, solution_text: str, user_text: str):
        """
        Vergleicht nur Buchstaben außerhalb von Klammern.

        Rückgabe:
            user_classes: dict index -> "ok" | "accent" | "wrong"
            sol_classes:  dict index -> "ok" | "accent" | "wrong"
        """
        sol_letters = self._letters_outside_parentheses(solution_text)
        usr_letters = self._letters_outside_parentheses(user_text)

        user_classes = {}
        sol_classes = {}

        min_len = min(len(sol_letters), len(usr_letters))

        for i in range(min_len):
            s_idx, s_char = sol_letters[i]
            u_idx, u_char = usr_letters[i]

            base_s = self._strip_accents(s_char).lower()
            base_u = self._strip_accents(u_char).lower()

            if base_s == base_u:
                if s_char.lower() == u_char.lower():
                    kind = "ok"
                else:
                    # gleicher Buchstabe, aber Akzent/Kleinschreibung anders
                    kind = "accent"
            else:
                kind = "wrong"

            user_classes[u_idx] = kind
            sol_classes[s_idx] = kind

        # zusätzliche Buchstaben in der Eingabe -> falsch
        for j in range(min_len, len(usr_letters)):
            u_idx, _ = usr_letters[j]
            user_classes[u_idx] = "wrong"

        # fehlende Buchstaben in der Eingabe -> im Lösungstext markieren
        for j in range(min_len, len(sol_letters)):
            s_idx, _ = sol_letters[j]
            sol_classes[s_idx] = "wrong"

        return user_classes, sol_classes

    def _colorize_with_classes(self, text: str, classes_by_index):
        """
        Färbt nur Buchstaben entsprechend der Klassen ein.
        Nicht-Buchstaben bleiben unverändert.
        """
        result_parts = []
        for idx, ch in enumerate(text):
            kind = classes_by_index.get(idx)
            if kind is None or not ch.isalpha():
                result_parts.append(ch)
            else:
                if kind == "ok":
                    color = "FFFFFF"   # weiß
                elif kind == "accent":
                    color = "FFD700"   # gold/gelb
                else:
                    color = "FF5555"   # rot
                result_parts.append(f"[color=#{color}]{ch}[/color]")
        return "".join(result_parts)


    def _clean_target_for_salad(self, raw_target: str) -> str:
        """
        Entfernt Klammern und Leerzeichen für Buchstaben-/Silben-Salat.
        Z.B. '(to) walk' -> 'towalk' (ohne Leerzeichen, ohne Klammerinhalt)
        """
        if not raw_target:
            return ""
        cleaned_chars = []
        in_parens = False
        for ch in raw_target:
            if ch == "(":
                in_parens = True
                continue
            if ch == ")":
                in_parens = False
                continue
            if in_parens:
                continue
            if ch.isspace():
                continue
            cleaned_chars.append(ch)
        return "".join(cleaned_chars)

    def _clean_target_for_syllables(self, raw_target: str) -> str:
        """
        Entfernt nur Klammern für den Silbenmodus – Leerzeichen bleiben drin,
        damit Wortgrenzen sichtbar bleiben.
        Z.B. '(to) walk away' -> 'to walk away'
        """
        if not raw_target:
            return ""
        cleaned_chars = []
        in_parens = False
        for ch in raw_target:
            if ch == "(":
                in_parens = True
                continue
            if ch == ")":
                in_parens = False
                continue
            if in_parens:
                continue
            cleaned_chars.append(ch)
        return "".join(cleaned_chars)


    def _split_into_syllable_chunks(self, cleaned: str):
        """
        Teilt ein Wort in 'Silben-Karten':
        - Länge 1: eine Karte
        - Länge 2–5: zwei Teile
        - >5: hauptsächlich 3–4 Zeichen lange Karten
        """
        cleaned = cleaned or ""
        n = len(cleaned)
        if n == 0:
            return []
        if n == 1:
            return [cleaned]
        if 2 <= n <= 5:
            first_len = n // 2
            return [cleaned[:first_len], cleaned[first_len:]]
        # n > 5 -> hauptsächlich 3–4 Zeichen lange Karten
        chunks = []
        i = 0
        while n - i > 4:
            remain = n - i
            # vermeiden, dass am Ende nur 1 Zeichen übrig bleibt
            if remain - 3 == 1:
                size = 4
            else:
                size = 3
            chunks.append(cleaned[i: i + size])
            i += size
        if i < n:
            chunks.append(cleaned[i:])
        return chunks


    # ------------------------------------------------------------------
    # Knowledge / difficulty helpers
    # ------------------------------------------------------------------


    def update_srs(self, vocab, was_correct: bool, quality: float = 0.5):
        """
        Einfaches Spaced-Repetition-Update für einen Vokabeleintrag.

        - was_correct: True, wenn die Karte in diesem Durchgang gewusst /
          als „leicht/okay“ bewertet wurde.
        - quality: grobe Qualität 0.0–1.0 (z.B. aus Self-Ratings).
        """
        if not vocab:
            return

        now = datetime.now()

        try:
            streak = int(vocab.get("srs_streak", 0) or 0)
        except (TypeError, ValueError):
            streak = 0

        if was_correct:
            streak += 1
        else:
            streak = 0

        vocab["srs_streak"] = streak
        vocab["srs_last_seen"] = now.isoformat()

        # sehr simple Intervalle (Tage)
        base_intervals = [1, 2, 4, 7, 14, 30]
        idx = min(streak, len(base_intervals) - 1)
        days = base_intervals[idx]

        # quality (0.0–1.0) skaliert das Intervall leicht
        try:
            q = float(quality)
        except (TypeError, ValueError):
            q = 0.5
        q = max(0.0, min(1.0, q))

        factor = 0.75 + 0.5 * q  # 0.75–1.25
        days = max(1, int(days * factor))

        due = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days)
        vocab["srs_due"] = due.isoformat()

        # SRS-Daten direkt mitspeichern
        try:
            self._persist_single_entry(vocab)
        except Exception as e:
            log(f"error while auto-saving SRS data: {e}")


    def _adjust_knowledge_level(self, vocab, delta, persist_immediately=True):
        """
        Increase/decrease vocab['knowledge_level'] by `delta` and clamp to [0, 1].
        Wenn persist_immediately=True, wird der entsprechende Stack sofort gespeichert.
        """
        if not vocab:
            return
        try:
            current = float(vocab.get("knowledge_level", 0.0))
        except (TypeError, ValueError):
            current = 0.0
        try:
            delta_val = float(delta)
        except (TypeError, ValueError):
            delta_val = 0.0

        new_level = current + delta_val
        if new_level < 0.0:
            new_level = 0.0
        elif new_level > 1.0:
            new_level = 1.0

        vocab["knowledge_level"] = new_level

        if persist_immediately:
            try:
                self._persist_single_entry(vocab)
            except Exception as e:
                log(f"error while auto-saving knowledge_level: {e}")


    def _persist_single_entry(self, vocab):
        """
        Delegiert das Speichern eines einzelnen Eintrags an save.persist_single_entry.
        """
        if not hasattr(self, "stack_vocab_lists"):
            return

        try:
            save.persist_single_entry(
                vocab,
                getattr(self, "stack_vocab_lists", {}),
                getattr(self, "stack_meta_map", {}),
                getattr(self, "entry_to_stack_file", {}),
            )
        except Exception as e:
            log(f"error while auto-saving vocab '{vocab}': {e}")


    def persist_knowledge_levels(self):
        """
        Speichert alle Vokabel-Stapel aus der aktuellen Lernsession über save.persist_all_stacks().
        Wird beim Verlassen des Lernmodus (exit_learning) verwendet.
        """
        if not hasattr(self, "stack_vocab_lists"):
            return

        try:
            save.persist_all_stacks(
                getattr(self, "stack_vocab_lists", {}),
                getattr(self, "stack_meta_map", {}),
            )
        except Exception as e:
            log(f"error while saving vocab stacks: {e}")


    def exit_learning(self, instance=None):
        """Persist knowledge levels, Lernzeit updaten und zurück ins Hauptmenü."""
        try:
            self.persist_knowledge_levels()
        except Exception as e:
            log(f"persist_knowledge_levels failed: {e}")

        # Lernzeit im config.stats speichern
        try:
            start = getattr(self, "session_start_time", None)
            if start is not None:
                delta = datetime.now() - start
                seconds = max(0, int(delta.total_seconds()))
                stats_cfg = config.setdefault("stats", {})
                stats_cfg["total_learn_time_seconds"] = int(
                    stats_cfg.get("total_learn_time_seconds", 0) or 0
                ) + seconds
                save.save_settings(config)
        except Exception as e:
            log(f"error while updating learning time: {e}")

        self.main_menu()


    # ------------------------------------------------------------------
    # Vokabelauswahl & Moduswahl nach knowledge_level
    # ------------------------------------------------------------------

    def _compute_vocab_weight(self, entry):
        """
        Gewicht für die Zufallsauswahl:
        - niedriger knowledge_level  -> höheres Gewicht
        - höherer knowledge_level    -> niedrigeres Gewicht
        """
        try:
            level = float(entry.get("knowledge_level", 0.0))
        except (TypeError, ValueError):
            level = 0.0
        if level < 0.0:
            level = 0.0
        elif level > 1.0:
            level = 1.0

        weight = 1.0 - level  # 0 -> 1.0, 1 -> 0
        # kleines Minimum, damit „gute“ Vokabeln nicht komplett verschwinden
        if weight < 0.05:
            weight = 0.05
        return weight

    def _pick_next_vocab_index(self, avoid_current=True):
        """
        Wählt den Index der nächsten Vokabel:

        - zuerst werden fällige Karten (srs_due <= jetzt) bevorzugt
        - innerhalb der Kandidaten sind Vokabeln mit niedrigem
          knowledge_level wahrscheinlicher
        - optional wird die aktuelle Vokabel ausgeschlossen
        """
        if not getattr(self, "all_vocab_list", None):
            return 0

        n = len(self.all_vocab_list)
        if n <= 1:
            return 0

        now = datetime.now()
        due_indices = []

        # Kandidaten mit fälliger SRS-Datum sammeln
        for idx, entry in enumerate(self.all_vocab_list):
            due_raw = entry.get("srs_due")
            if not due_raw:
                continue
            try:
                due = datetime.fromisoformat(str(due_raw))
            except Exception:
                continue
            if due <= now:
                due_indices.append(idx)

        if due_indices:
            candidate_indices = due_indices
        else:
            candidate_indices = list(range(n))

        current_idx = getattr(self, "current_vocab_index", 0)

        if avoid_current and len(candidate_indices) > 1 and current_idx in candidate_indices:
            candidate_indices = [i for i in candidate_indices if i != current_idx]

        if not candidate_indices:
            candidate_indices = [i for i in range(n) if not (avoid_current and i == current_idx)]
            if not candidate_indices:
                return 0

        weights = []
        total = 0.0
        for idx in candidate_indices:
            entry = self.all_vocab_list[idx]
            w = self._compute_vocab_weight(entry)
            weights.append(w)
            total += w

        if total <= 0.0:
            return random.choice(candidate_indices)

        r = random.random() * total
        acc = 0.0
        for idx, w in zip(candidate_indices, weights):
            acc += w
            if r <= acc:
                return idx

        # Numerischer Fallback
        return candidate_indices[-1]


    def _get_current_vocab(self):
        if not getattr(self, "all_vocab_list", None):
            return None
        if not (0 <= getattr(self, "current_vocab_index", 0) < len(self.all_vocab_list)):
            self.current_vocab_index = 0
        return self.all_vocab_list[self.current_vocab_index]

    def _get_mode_pool_for_level(self, level):
        """
        Gibt die Liste der Modi für einen gegebenen knowledge_level zurück,
        geschnitten mit self.available_modes (Einstellungen bleiben gültig).

        Levelbänder:
          0.00 – 0.35 : front/back, back/front, multiple_choice, connect_pairs
          0.35 – 0.60 : multiple_choice, connect_pairs, letter_salad, syllable_salad
          > 0.60      : alles außer Flashcards (kein front_back/back_front)
        """
        try:
            lvl = float(level)
        except (TypeError, ValueError):
            lvl = 0.0
        if lvl < 0.0:
            lvl = 0.0
        elif lvl > 1.0:
            lvl = 1.0

        if lvl <= 0.35:
            base = {"front_back", "back_front", "multiple_choice", "connect_pairs"}
        elif lvl <= 0.60:
            base = {"multiple_choice", "connect_pairs", "letter_salad", "syllable_salad"}
        else:
            base = {"multiple_choice", "connect_pairs", "letter_salad", "syllable_salad", "typing"}

        candidates = [m for m in getattr(self, "available_modes", []) if m in base]
        if not candidates:
            # Falls der Nutzer alles in diesem Band deaktiviert hat,
            # nimm irgendeinen aktiven Modus.
            candidates = list(getattr(self, "available_modes", []))
        return candidates

    def _choose_mode_for_vocab(self, vocab):
        """Wählt einen Modus passend zum knowledge_level dieser Vokabel."""
        if vocab is None:
            return random.choice(self.available_modes) if self.available_modes else "front_back"
        level = vocab.get("knowledge_level", 0.0)
        pool = self._get_mode_pool_for_level(level)
        if not pool:
            return "front_back"
        return random.choice(pool)


    def flip_card_learn_func(self, instance=None):
        """
        Flip behavior for front_back / back_front.

        With self-rating enabled:
            - first tap shows the back side
            - rating buttons decide how to continue
        Without self-rating (legacy): second tap advances to the next card.
        """
        # New behavior with self-rating (Anki-style)
        if (
            getattr(self, "self_rating_enabled", False)
            and self.learn_mode in ("front_back", "back_front")
        ):
            # First tap: show back
            if not self.is_back:
                self.is_back = True
                self.animate_flip_current_card()
            # Second tap on the card does nothing; user must choose a rating
            return

        # Legacy behavior for other modes / when self-rating is disabled
        if not self.is_back and self.learn_mode in ("front_back", "back_front"):
            self.is_back = True
            self.animate_flip_current_card()
            return

        # Back side: advance to next card and randomize mode (legacy path)
        if self.is_back:
            if self.max_current_vocab_index > 1:
                self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
            else:
                self.current_vocab_index = 0

            self.is_back = False
            self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        else:
            self.is_back = True

        self.show_current_card()



    def animate_flip_current_card(self):
        """Small fade animation used when a card is flipped."""
        if not hasattr(self, "front_side_label"):
            self.show_current_card()
            return

        lbl = self.front_side_label
        current_vocab = self.all_vocab_list[self.current_vocab_index]

        if self.learn_mode == "front_back":
            new_text = self._format_backside(current_vocab)
        elif self.learn_mode == "back_front":
            new_text = current_vocab.get("own_language", "")
        else:
            new_text = lbl.text

        def set_back_text(*args):
            lbl.text = new_text

            # Self-rating row becomes visible once the back side is shown
            if (
                getattr(self, "self_rating_enabled", False)
                and self.learn_mode in ("front_back", "back_front")
                and hasattr(self, "selfrating_box")
                and self.selfrating_box is not None
            ):
                self.selfrating_box.disabled = False
                self.selfrating_box.opacity = 1

            anim_in = Animation(opacity=1, duration=0.15)
            anim_in.start(lbl)

        anim_out = Animation(opacity=0, duration=0.15)
        anim_out.bind(on_complete=set_back_text)
        anim_out.start(lbl)


    # ------------------------------------------------------------------
    # Multiple choice mode
    # ------------------------------------------------------------------

    def multiple_choice(self):
        """Show a multiple choice question for the current vocab entry."""
        self.learn_content.clear_widgets()

        if not self.all_vocab_list:
            log("no vocab -> multiple choice aborted")
            self.main_menu()
            return

        correct_vocab = self.all_vocab_list[self.current_vocab_index]
        pool = [w for w in self.all_vocab_list if w is not correct_vocab]

        wrong = []
        if len(pool) >= 4:
            wrong = random.sample(pool, 4)
        else:
            picked = set()
            while len(wrong) < min(4, len(pool)):
                c = random.choice(pool)
                key = (c.get("own_language", ""), c.get("foreign_language", ""))
                if key not in picked:
                    wrong.append(c)
                    picked.add(key)
            while len(wrong) < 4:
                wrong.append(correct_vocab)

        answers = []
        seen = set()
        for cand in wrong + [correct_vocab]:
            key = (cand.get("own_language", ""), cand.get("foreign_language", ""))
            if key not in seen:
                answers.append(cand)
                seen.add(key)

        if len(answers) < 2 and pool:
            answers.extend(random.sample(pool, min(3, len(pool))))
            tmp, seen2 = [], set()
            for a in answers:
                k = (a.get("own_language", ""), a.get("foreign_language", ""))
                if k not in seen2:
                    tmp.append(a)
                    seen2.add(k)
            answers = tmp

        if not any(
            a.get("own_language", "") == correct_vocab.get("own_language", "")
            and a.get("foreign_language", "")
            == correct_vocab.get("foreign_language", "")
            for a in answers
        ):
            answers.append(correct_vocab)

        random.shuffle(answers)

        # State for animated multiple choice
        self.multiple_choice_locked = False
        self.mc_buttons = []

        scroll = ScrollView(size_hint=(1, 1))
        form_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[
                50
                * float(config["settings"]["gui"]["padding_multiplicator"]),
                80
                * float(config["settings"]["gui"]["padding_multiplicator"]),
                120
                * float(config["settings"]["gui"]["padding_multiplicator"]),
                50
                * float(config["settings"]["gui"]["padding_multiplicator"]),
            ],
            size_hint_y=None,
        )
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Header: questioned word (own_language)
        if hasattr(self, "header_label"):
            self.header_label.color = APP_COLORS["text"]
            self.header_label.text = correct_vocab.get("own_language", "")

        for opt in answers:
            btn = RoundedButton(
                text=self._format_answer_lines(opt),
                bg_color=APP_COLORS["card"],
                color=APP_COLORS["text"],
                font_size=config["settings"]["gui"]["title_font_size"],
                size_hint=(1, None),
                height=dp(70),
            )

            btn.bind(
                on_press=lambda instance, choice=opt: self.multiple_choice_func(
                    correct_vocab, choice, instance
                )
            )
            self.mc_buttons.append(btn)
            form_layout.add_widget(btn)

        scroll.add_widget(form_layout)
        self.learn_content.add_widget(scroll)

    def multiple_choice_func(self, correct_vocab, chosen_vocab, button):
        """Handle a single button press in multiple choice mode."""
        if getattr(self, "multiple_choice_locked", False):
            return

        self.multiple_choice_locked = True

        if isinstance(button, RoundedButton):
            button.set_bg_color(APP_COLORS["accent"])
            button.color = APP_COLORS["text"]

        is_correct = chosen_vocab is correct_vocab or (
            chosen_vocab.get("own_language", "")
            == correct_vocab.get("own_language", "")
            and chosen_vocab.get("foreign_language", "")
            == correct_vocab.get("foreign_language", "")
        )

        # Update knowledge level for the target vocab
        if is_correct:
            delta = getattr(
                labels,
                "knowledge_delta_multiple_choice_correct",
                0.07,
            )
        else:
            delta = getattr(
                labels,
                "knowledge_delta_multiple_choice_wrong",
                -0.06,
            )
        self._adjust_knowledge_level(correct_vocab, delta)

        # SRS-Infos aktualisieren
        self.update_srs(
            correct_vocab,
            was_correct=is_correct,
            quality=1.0 if is_correct else 0.0,
        )

        if is_correct:
            if isinstance(button, RoundedButton):
                button.set_bg_color(APP_COLORS["success"])
                button.color = APP_COLORS["text"]
            anim = Animation(opacity=0.9, duration=0.1) + Animation(
                opacity=1, duration=0.1
            )
            anim.start(button)

            Clock.schedule_once(
                lambda dt: self._advance_after_correct(), 0.25
            )
        else:
            if isinstance(button, RoundedButton):
                button.set_bg_color(APP_COLORS["danger"])
                button.color = APP_COLORS["text"]

            anim = Animation(opacity=0.6, duration=0.1) + Animation(
                opacity=1, duration=0.1
            )
            anim.start(button)

            def reset_btn(dt, btn=button):
                if isinstance(btn, RoundedButton):
                    btn.set_bg_color(APP_COLORS["card"])
                    btn.color = APP_COLORS["text"]
                self.multiple_choice_locked = False

            Clock.schedule_once(reset_btn, 0.35)


    def _advance_after_correct(self):
        """After a correct multiple choice answer, go to the next card/mode."""
        # Session-Schritt: Multiple-Choice-Karte abgeschlossen
        if self._register_session_step(was_correct=True):
            self.multiple_choice_locked = False
            return

        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.multiple_choice_locked = False
        self.show_current_card()


    # ------------------------------------------------------------------
    # Connect pairs mode (match 5 pairs)
    # ------------------------------------------------------------------

    def connect_pairs_mode(self):
        """Mode where the user must connect 5 word pairs (own/foreign)."""
        self.learn_content.clear_widgets()

        unique_map = {}
        for e in self.all_vocab_list:
            key = (e.get("own_language", ""), e.get("foreign_language", ""))
            if key not in unique_map:
                unique_map[key] = e
        unique_items = list(unique_map.values())

        if len(unique_items) < 5:
            log("not enough unique vocab for connect_pairs, falling back")
            fallback_modes = [
                m for m in self.available_modes if m != "connect_pairs"
            ]
            self.learn_mode = random.choice(
                fallback_modes or self.available_modes
            )
            self.show_current_card()
            return

        if hasattr(self, "header_label"):
            self.header_label.text = ""

        # Pick 5 unique entries
        self.connect_pairs_items = random.sample(unique_items, 5)

        # State
        self.connect_pairs_left_buttons = {}
        self.connect_pairs_right_buttons = {}
        self.connect_pairs_selected_left = None
        self.connect_pairs_selected_right = None
        self.connect_pairs_matched_count = 0
        self.connect_pairs_locked = False

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=20 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.9, 0.7),
            padding=dp(16),
            spacing=dp(16),
        )

        header_text = getattr(
            labels,
            "connect_pairs_header",
        )
        header_lbl = self.make_text_label(
            header_text,
            size_hint_y=None,
            height=dp(30),
        )
        card.add_widget(header_lbl)

        content_row = BoxLayout(orientation="horizontal", spacing=dp(24))

        left_col = BoxLayout(orientation="vertical", spacing=dp(8))
        right_col = BoxLayout(orientation="vertical", spacing=dp(8))

        # Left column: own_language
        for entry in self.connect_pairs_items:
            text = entry.get("own_language", "")
            btn = RoundedButton(
                text=text,
                bg_color=APP_COLORS["card"],
                color=APP_COLORS["text"],
                size_hint=(1, None),
                height=dp(48),
                font_size=int(config["settings"]["gui"]["text_font_size"]),
            )
            btn._matched = False
            btn.bind(
                on_press=lambda instance, e=entry: self.on_connect_left_pressed(
                    instance, e
                )
            )
            self.connect_pairs_left_buttons[btn] = entry
            left_col.add_widget(btn)

        # Right column: foreign_language (shuffled)
        shuffled_items = self.connect_pairs_items[:]
        random.shuffle(shuffled_items)
        for entry in shuffled_items:
            text = self._format_answer_lines(entry)
            btn = RoundedButton(
                text=text,
                bg_color=APP_COLORS["card"],
                color=APP_COLORS["text"],
                size_hint=(1, None),
                height=dp(48),
                font_size=int(config["settings"]["gui"]["text_font_size"]),
            )
            btn._matched = False
            btn.bind(
                on_press=lambda instance, e=entry: self.on_connect_right_pressed(
                    instance, e
                )
            )
            self.connect_pairs_right_buttons[btn] = entry
            right_col.add_widget(btn)


        content_row.add_widget(left_col)
        content_row.add_widget(right_col)
        card.add_widget(content_row)

        center.add_widget(card)
        self.learn_content.add_widget(center)

    def _clear_connect_selection(self, side="both"):
        """Reset the selected buttons (left/right) if they are not matched."""
        if (
            side in ("left", "both")
            and self.connect_pairs_selected_left
            and not getattr(self.connect_pairs_selected_left, "_matched", False)
        ):
            self.connect_pairs_selected_left.set_bg_color(APP_COLORS["card"])
            self.connect_pairs_selected_left = None
        if (
            side in ("right", "both")
            and self.connect_pairs_selected_right
            and not getattr(self.connect_pairs_selected_right, "_matched", False)
        ):
            self.connect_pairs_selected_right.set_bg_color(APP_COLORS["card"])
            self.connect_pairs_selected_right = None

    def on_connect_left_pressed(self, button, entry):
        """Handle a click on a left-side (own_language) button."""
        if getattr(self, "connect_pairs_locked", False):
            return
        if getattr(button, "_matched", False):
            return

        if self.connect_pairs_selected_left is not button:
            self._clear_connect_selection("left")
            self.connect_pairs_selected_left = button
            button.set_bg_color(APP_COLORS["card_selected"])

        if self.connect_pairs_selected_right:
            self._check_connect_pair()

    def on_connect_right_pressed(self, button, entry):
        """Handle a click on a right-side (foreign_language) button."""
        if getattr(self, "connect_pairs_locked", False):
            return
        if getattr(button, "_matched", False):
            return

        if self.connect_pairs_selected_right is not button:
            self._clear_connect_selection("right")
            self.connect_pairs_selected_right = button
            button.set_bg_color(APP_COLORS["card_selected"])

        if self.connect_pairs_selected_left:
            self._check_connect_pair()

    def _check_connect_pair(self):
        """Check if the currently selected left/right buttons form a pair."""
        left_btn = self.connect_pairs_selected_left
        right_btn = self.connect_pairs_selected_right
        if not left_btn or not right_btn:
            return

        left_entry = self.connect_pairs_left_buttons.get(left_btn)
        right_entry = self.connect_pairs_right_buttons.get(right_btn)

        if left_entry is None or right_entry is None:
            return

        left_key = (
            left_entry.get("own_language", ""),
            left_entry.get("foreign_language", ""),
        )
        right_key = (
            right_entry.get("own_language", ""),
            right_entry.get("foreign_language", ""),
        )

        if left_key == right_key:
            # Correct pair: reward both vocab entries
            delta = getattr(
                labels,
                "knowledge_delta_connect_pairs_correct_word",
                0.06,
            )
            self._adjust_knowledge_level(left_entry, delta)
            self._adjust_knowledge_level(right_entry, delta)

            self.connect_pairs_locked = True
            for btn in (left_btn, right_btn):
                btn._matched = True
                btn.set_bg_color(APP_COLORS["success"])
                btn.color = APP_COLORS["text"]
                anim = Animation(opacity=0.95, duration=0.1) + Animation(
                    opacity=1, duration=0.1
                )
                anim.start(btn)

            self.connect_pairs_selected_left = None
            self.connect_pairs_selected_right = None
            self.connect_pairs_matched_count += 1
            self.connect_pairs_locked = False

            if self.connect_pairs_matched_count >= len(
                self.connect_pairs_items
            ):
                Clock.schedule_once(
                    lambda dt: self._connect_pairs_finish(), 0.3
                )
        else:
            # Wrong pair: penalty for both involved vocab entries
            delta_wrong = getattr(
                labels,
                "knowledge_delta_connect_pairs_wrong_word",
                -0.074,
            )
            self._adjust_knowledge_level(left_entry, delta_wrong)
            self._adjust_knowledge_level(right_entry, delta_wrong)

            self.connect_pairs_locked = True
            for btn in (left_btn, right_btn):
                btn.set_bg_color(APP_COLORS["danger"])
                btn.color = APP_COLORS["text"]
                anim = Animation(opacity=0.6, duration=0.1) + Animation(
                    opacity=1, duration=0.1
                )
                anim.start(btn)

            def reset(dt):
                if not getattr(left_btn, "_matched", False):
                    left_btn.set_bg_color(APP_COLORS["card"])
                if not getattr(right_btn, "_matched", False):
                    right_btn.set_bg_color(APP_COLORS["card"])
                self.connect_pairs_selected_left = None
                self.connect_pairs_selected_right = None
                self.connect_pairs_locked = False

            Clock.schedule_once(reset, 0.3)


    def _connect_pairs_finish(self):
        """After all 5 pairs are matched, go to the next card/mode."""
        # SRS für alle beteiligten Wörter
        items = getattr(self, "connect_pairs_items", []) or []
        for entry in items:
            self.update_srs(entry, was_correct=True, quality=1.0)

        # Session-Schritt (5 Paare = 5 „Exposures“)
        steps = len(items) if items else 1
        if self._register_session_step(was_correct=True, steps=steps):
            return

        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()


    # ------------------------------------------------------------------
    # Letter salad mode (click letters in the correct order)
    # ------------------------------------------------------------------

    def letter_salad(self):
        """Mode where the user clicks letters to assemble the target word."""
        self.learn_content.clear_widgets()

        if not self.all_vocab_list:
            log("no vocab -> letter_salad aborted")
            self.main_menu()
            return

        correct_vocab = self.all_vocab_list[self.current_vocab_index]

        if hasattr(self, "header_label"):
            self.header_label.text = ""

        raw_target = (correct_vocab.get("foreign_language", "") or "").strip()
        target_clean = self._clean_target_for_salad(raw_target)

        if not target_clean:
            log(
                f"letter_salad: cleaned target empty for '{raw_target}', skipping to next mode"
            )
            self.learn_mode = random.choice(
                [
                    m
                    for m in self.available_modes
                    if m != "letter_salad"
                ]
                or self.available_modes
            )
            self.show_current_card()
            return

        letters = list(target_clean)
        scrambled_letters = letters[:]
        random.shuffle(scrambled_letters)

        # State for this round
        self.letter_salad_vocab = correct_vocab
        self.letter_salad_target_raw = raw_target
        self.letter_salad_target_clean = target_clean
        self.letter_salad_is_short = len(target_clean) <= 4
        self.letter_salad_progress = 0
        self.letter_salad_typed = ""
        self.letter_salad_buttons = []

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.55),
            padding=dp(16),
            spacing=dp(12),
        )

        # Prompt: own_language at the top of the card
        prompt_lbl = self.make_title_label(
            correct_vocab.get("own_language", ""),
            size_hint_y=None,
            height=dp(40),
        )
        card.add_widget(prompt_lbl)

        # optionale dritte Spalte direkt darunter anzeigen
        latin_extra = (correct_vocab.get("latin_language") or "").strip()
        if latin_extra:
            latin_lbl = self.make_text_label(
                latin_extra,
                size_hint_y=None,
                height=dp(30),
            )
            card.add_widget(latin_lbl)

        # Instruction text
        instruction = self.make_text_label(
            getattr(
                labels,
                "letter_salad_instruction",
                labels.letter_salad_instruction,
            ),
            size_hint_y=None,
            height=dp(30),
        )
        card.add_widget(instruction)

        # Progress label showing what the user has built so far
        self.letter_salad_progress_label = self.make_title_label(
            "",
            size_hint_y=None,
            height=dp(40),
        )
        card.add_widget(self.letter_salad_progress_label)

        # Grid of letter tiles (mit ScrollView und hellgrauem Rahmen)
        cols = max(1, min(len(scrambled_letters), 10))
        letters_layout = GridLayout(
            cols=cols,
            spacing=dp(8),
            size_hint_y=None,
            padding=(0, dp(4)),
        )
        letters_layout.bind(minimum_height=letters_layout.setter("height"))

        for ch in scrambled_letters:
            btn = RoundedButton(
                text=ch,
                bg_color=APP_COLORS["card"],
                color=APP_COLORS["text"],
                font_size=int(config["settings"]["gui"]["title_font_size"]),
                size_hint=(None, None),
                size=(dp(56), dp(56)),
            )
            btn.bind(on_press=self.letter_salad_letter_pressed)
            self.letter_salad_buttons.append(btn)

            # kleine hellgraue Box drumherum
            wrapper = RoundedCard(
                orientation="vertical",
                size_hint=(None, None),
                padding=dp(3),
                spacing=0,
                bg_color=APP_COLORS["card_selected"],
            )
            wrapper.add_widget(btn)
            letters_layout.add_widget(wrapper)

        letters_scroll = ScrollView(
            size_hint=(1, None),
            height=dp(210),      # genug Platz für mehrere Reihen
            do_scroll_y=True,
            do_scroll_x=True,
        )
        letters_scroll.add_widget(letters_layout)
        card.add_widget(letters_scroll)

        # Bottom row: skip / reshuffle
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(12),
        )

        skip_text = getattr(labels, "letter_salad_skip")
        reshuffle_text = getattr(labels, "letter_salad_reshuffle")

        skip_btn = self.make_secondary_button(
            skip_text,
            size_hint=(0.5, 1),
        )
        skip_btn.bind(on_press=self.letter_salad_skip)

        reshuffle_btn = self.make_secondary_button(
            reshuffle_text,
            size_hint=(0.5, 1),
        )
        reshuffle_btn.bind(on_press=lambda inst: self.letter_salad())

        btn_row.add_widget(skip_btn)
        btn_row.add_widget(reshuffle_btn)

        card.add_widget(btn_row)

        center.add_widget(card)
        self.learn_content.add_widget(center)


    def letter_salad_letter_pressed(self, button, instance=None):
        """Handle a single letter tile click in letter salad mode."""
        target = getattr(self, "letter_salad_target_clean", "")
        progress = getattr(self, "letter_salad_progress", 0)
        vocab = getattr(self, "letter_salad_vocab", None)

        if not target:
            return

        if progress >= len(target):
            return

        expected_char = target[progress]
        clicked_char = (button.text or "").strip()

        if button.disabled:
            return

        if clicked_char == expected_char:
            button.set_bg_color(APP_COLORS["success"])
            button.color = APP_COLORS["text"]
            button.disabled = True

            # Knowledge: per correct letter
            delta = getattr(
                labels,
                "knowledge_delta_letter_salad_per_correct_letter",
                0.01,
            )
            self._adjust_knowledge_level(vocab, delta)

            self.letter_salad_progress = progress + 1

            typed = getattr(self, "letter_salad_typed", "")
            typed += clicked_char
            self.letter_salad_typed = typed
            if hasattr(self, "letter_salad_progress_label"):
                self.letter_salad_progress_label.text = typed

            if self.letter_salad_progress >= len(target):
                Clock.schedule_once(
                    lambda dt: self._letter_salad_finish(), 0.3
                )
        else:
            # Wrong letter -> penalty
            delta_wrong = getattr(
                labels,
                "knowledge_delta_letter_salad_wrong_letter",
                -0.025,
            )
            self._adjust_knowledge_level(vocab, delta_wrong)

            button.set_bg_color(APP_COLORS["danger"])
            button.color = APP_COLORS["text"]
            Clock.schedule_once(
                lambda dt, b=button: (
                    b.set_bg_color(APP_COLORS["card"]),
                    setattr(b, "color", APP_COLORS["text"]),
                ),
                0.25,
            )


    def _letter_salad_finish(self):
        """After a correct word, update knowledge and go to the next vocab entry/mode."""
        vocab = getattr(self, "letter_salad_vocab", None)
        if getattr(self, "letter_salad_is_short", False):
            bonus = getattr(
                labels,
                "knowledge_delta_letter_salad_short_word_bonus",
                0.02,
            )
            self._adjust_knowledge_level(vocab, bonus)

        # SRS-Update (Wort erfolgreich zusammengesetzt)
        if vocab is not None:
            self.update_srs(vocab, was_correct=True, quality=1.0)

        # Session-Schritt
        if self._register_session_step(was_correct=True):
            return

        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()


    def letter_salad_skip(self, instance=None):
        """Skip the current vocab entry in letter salad mode."""
        vocab = getattr(self, "letter_salad_vocab", None)
        if vocab is not None:
            # SRS – Karte als „falsch/übersprungen“ markieren
            self.update_srs(vocab, was_correct=False, quality=0.0)

        # Session-Schritt (übersprungen zählt als falsch)
        if self._register_session_step(was_correct=False):
            return

        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()


    # ------------------------------------------------------------------
    # Syllable salad mode (Silben-Karten anklicken)
    # ------------------------------------------------------------------

    def syllable_salad(self):
        """Wie Buchstabensalat, aber mit Silben und mehreren Wörtern."""
        self.learn_content.clear_widgets()

        if not self.all_vocab_list:
            log("no vocab -> syllable_salad aborted")
            self.main_menu()
            return

        # Hauptwort = aktuelles Vokabel, plus bis zu 2 weitere
        main_vocab = self.all_vocab_list[self.current_vocab_index]
        pool = [e for e in self.all_vocab_list if e is not main_vocab]

        max_words = 3
        num_extra = max(0, min(max_words - 1, len(pool)))
        extra = random.sample(pool, num_extra) if num_extra > 0 else []

        selected = [main_vocab] + extra

        # Duplikate entfernen
        unique = {}
        for e in selected:
            key = (e.get("own_language", ""), e.get("foreign_language", ""))
            if key not in unique:
                unique[key] = e
        selected = list(unique.values())

        # Zustand für diesen Durchgang
        self.syllable_salad_items = []
        self.syllable_salad_buttons = []
        self.syllable_salad_finished_count = 0

        # aktuell gewähltes (noch nicht fertiges) Wort
        self.syllable_salad_active_word_index = None


        if hasattr(self, "header_label"):
            self.header_label.text = ""

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.9, 0.6),
            padding=dp(16),
            spacing=dp(12),
        )

        instruction_text = getattr(
            labels,
            "syllable_salad_instruction",
            "Setze die Wörter aus Silben zusammen:",
        )
        instr_lbl = self.make_text_label(
            instruction_text,
            size_hint_y=None,
            height=dp(30),
        )
        card.add_widget(instr_lbl)

        # Oben: fertige Wörter / Fortschritt
        self.syllable_salad_progress_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(80),
            spacing=dp(4),
        )

        for vocab in selected:
            raw_target = (vocab.get("foreign_language", "") or "").strip()
            target_clean = self._clean_target_for_syllables(raw_target)
            if not target_clean:
                continue

            chunks = self._split_into_syllable_chunks(target_clean)
            if not chunks:
                continue

            own = vocab.get("own_language", "") or ""
            third = (vocab.get("latin_language") or "").strip()
            if third:
                base_text = f"[b]{own}[/b] ({third}): "
            else:
                base_text = f"[b]{own}[/b]: "

            lbl = self.make_text_label(
                base_text,
                size_hint_y=None,
                height=dp(24),
            )
            lbl.markup = True


            item = {
                "vocab": vocab,
                "target_clean": target_clean,
                "chunks": chunks,
                "next_index": 0,
                "built": "",
                "base_text": base_text,
                "label": lbl,
                "finished": False,
            }
            self.syllable_salad_items.append(item)
            self.syllable_salad_progress_box.add_widget(lbl)

        if not self.syllable_salad_items:
            log("syllable_salad: no suitable words, falling back")
            self.learn_mode = random.choice(
                [m for m in self.available_modes if m != "syllable_salad"]
                or self.available_modes
            )
            self.show_current_card()
            return

        card.add_widget(self.syllable_salad_progress_box)

        # Buttons für alle Silben erzeugen
        all_buttons = []
        for word_index, item in enumerate(self.syllable_salad_items):
            for chunk_index, chunk in enumerate(item["chunks"]):
                btn = RoundedButton(
                    text=chunk,
                    bg_color=APP_COLORS["card"],
                    color=APP_COLORS["text"],
                    font_size=int(
                        config["settings"]["gui"]["title_font_size"]
                    ),
                    size_hint=(None, None),
                    size=(dp(80), dp(56)),
                )
                btn._word_index = word_index
                btn._chunk_index = chunk_index
                btn.bind(on_press=self.syllable_salad_segment_pressed)
                all_buttons.append(btn)

        random.shuffle(all_buttons)

        total_segments = len(all_buttons)
        cols = max(1, min(total_segments, 6))
        segments_layout = GridLayout(
            cols=cols,
            spacing=dp(8),
            size_hint_y=None,
            padding=(0, dp(4)),
        )
        segments_layout.bind(minimum_height=segments_layout.setter("height"))

        for btn in all_buttons:
            # kleine hellgraue Box um jede Silben-Karte
            wrapper = RoundedCard(
                orientation="vertical",
                size_hint=(None, None),
                padding=dp(3),
                spacing=0,
                bg_color=APP_COLORS["card_selected"],  # hellgrauer Rahmen
            )
            wrapper.add_widget(btn)
            segments_layout.add_widget(wrapper)
            self.syllable_salad_buttons.append(btn)


        # ScrollView für viele Silben – etwas höher, damit mehrere Reihen sichtbar sind
        scroll = ScrollView(
            size_hint=(1, None),
            height=dp(210),   # vorher 150
            do_scroll_y=True,
            do_scroll_x=True,
        )
        scroll.add_widget(segments_layout)
        card.add_widget(scroll)


        # Skip / neu mischen
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(12),
        )

        skip_text = getattr(labels, "letter_salad_skip", "Überspringen")
        reshuffle_text = getattr(
            labels,
            "syllable_salad_reshuffle",
            getattr(labels, "letter_salad_reshuffle", "Neu mischen"),
        )

        skip_btn = self.make_secondary_button(
            skip_text,
            size_hint=(0.5, 1),
        )
        skip_btn.bind(on_press=self.syllable_salad_skip)

        reshuffle_btn = self.make_secondary_button(
            reshuffle_text,
            size_hint=(0.5, 1),
        )
        # einfach neu aufbauen (wie bei Buchstabensalat)
        reshuffle_btn.bind(on_press=lambda inst: self.syllable_salad())

        btn_row.add_widget(skip_btn)
        btn_row.add_widget(reshuffle_btn)
        card.add_widget(btn_row)

        center.add_widget(card)
        self.learn_content.add_widget(center)

    def _reset_syllable_word(self, word_index):
        """Setzt den Fortschritt eines Wortes im Silbenmodus vollständig zurück."""
        if not (0 <= word_index < len(self.syllable_salad_items)):
            return

        item = self.syllable_salad_items[word_index]
        item["next_index"] = 0
        item["built"] = ""
        item["finished"] = False

        lbl = item["label"]
        lbl.text = item["base_text"]
        lbl.color = APP_COLORS["muted"]
        lbl.markup = True

        # Alle Buttons dieses Wortes zurück auf grau + aktiv
        for btn in self.syllable_salad_buttons:
            if getattr(btn, "_word_index", None) == word_index:
                btn.disabled = False
                btn.set_bg_color(APP_COLORS["card"])
                btn.color = APP_COLORS["text"]


    def syllable_salad_segment_pressed(self, button, instance=None):
        """Verarbeitet einen Klick auf eine Silben-Karte."""
        if getattr(button, "disabled", False):
            return

        word_index = getattr(button, "_word_index", None)
        chunk_index = getattr(button, "_chunk_index", None)
        if word_index is None or chunk_index is None:
            return

        if not (0 <= word_index < len(self.syllable_salad_items)):
            return

        item = self.syllable_salad_items[word_index]
        if item["finished"]:
            return

        wrong_delta = getattr(
            labels,
            "knowledge_delta_syllable_wrong_word",
            -0.5,
        )
        correct_delta = getattr(
            labels,
            "knowledge_delta_syllable_correct_word",
            0.80,
        )

        # Aktives Wort bestimmen / wechseln
        active = getattr(self, "syllable_salad_active_word_index", None)

        if active is None:
            # noch kein Wort gewählt -> dieses wird aktiv
            self.syllable_salad_active_word_index = word_index
            active = word_index
        else:
            if active != word_index:
                # Wenn man den Wortanfang eines anderen Wortes klickt:
                # altes Wort zurücksetzen, neues wird aktiv
                if chunk_index == 0 and item["next_index"] == 0:
                    self._reset_syllable_word(active)
                    self.syllable_salad_active_word_index = word_index
                    active = word_index
                else:
                    # anderes Wort mitten drin angeklickt -> als Fehler werten
                    button.set_bg_color(APP_COLORS["danger"])
                    button.color = APP_COLORS["text"]

                    # Penalty für das Wort, dessen Silbe fälschlich gewählt wurde
                    wrong_item = self.syllable_salad_items[word_index]
                    self._adjust_knowledge_level(wrong_item.get("vocab"), wrong_delta)

                    def reset_btn(dt, b=button):
                        b.set_bg_color(APP_COLORS["card"])
                        b.color = APP_COLORS["text"]

                    Clock.schedule_once(reset_btn, 0.25)
                    return

        # Ab hier ist word_index das aktive Wort
        item = self.syllable_salad_items[word_index]
        expected_index = item["next_index"]

        # Richtige nächste Silbe?
        if chunk_index == expected_index:
            button.set_bg_color(APP_COLORS["success"])
            button.color = APP_COLORS["text"]
            button.disabled = True

            item["next_index"] += 1
            item["built"] += button.text

            lbl = item["label"]
            lbl.text = item["base_text"] + item["built"]
            lbl.markup = True

            if item["next_index"] >= len(item["chunks"]):
                # Wort fertig -> Belohnung
                item["finished"] = True
                self.syllable_salad_finished_count += 1
                lbl.color = APP_COLORS["success"]

                self._adjust_knowledge_level(item.get("vocab"), correct_delta)

                # aktives Wort freigeben, damit man ein neues starten kann
                self.syllable_salad_active_word_index = None

                if self.syllable_salad_finished_count >= len(
                    self.syllable_salad_items
                ):
                    Clock.schedule_once(
                        lambda dt: self._syllable_salad_finish(), 0.3
                    )
        else:
            # falsche Silbe -> Strafe für dieses Wort
            button.set_bg_color(APP_COLORS["danger"])
            button.color = APP_COLORS["text"]

            self._adjust_knowledge_level(item.get("vocab"), wrong_delta)

            def reset_btn(dt, b=button):
                b.set_bg_color(APP_COLORS["card"])
                b.color = APP_COLORS["text"]

            Clock.schedule_once(reset_btn, 0.25)


    def _syllable_salad_finish(self):
        """Wenn alle Wörter korrekt gebaut wurden, gehe weiter."""
        # NEU: SRS für alle Wörter dieser Runde
        items = getattr(self, "syllable_salad_items", []) or []
        for item in items:
            vocab = item.get("vocab")
            if vocab is not None:
                self.update_srs(vocab, was_correct=True, quality=1.0)

        steps = len(items) if items else 1
        if self._register_session_step(was_correct=True, steps=steps):
            return

        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()


    def syllable_salad_skip(self, instance=None):
        """Überspringt den aktuellen Silben-Durchgang."""
        items = getattr(self, "syllable_salad_items", []) or []
        for item in items:
            vocab = item.get("vocab")
            if vocab is not None:
                self.update_srs(vocab, was_correct=False, quality=0.0)

        steps = len(items) if items else 1
        if self._register_session_step(was_correct=False, steps=steps):
            return

        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()


    # ------------------------------------------------------------------
    # Typing mode (Übersetzung eintippen)
    # ------------------------------------------------------------------

    def typing_mode(self):
        """Mode where the user types the translation manually."""
        self.learn_content.clear_widgets()

        if not self.all_vocab_list:
            log("no vocab -> typing_mode aborted")
            self.main_menu()
            return

        current_vocab = self.all_vocab_list[self.current_vocab_index]

        if hasattr(self, "header_label"):
            self.header_label.text = ""

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.55),
            padding=dp(16),
            spacing=dp(12),
        )

        # Prompt: own_language oben
        prompt_lbl = self.make_title_label(
            current_vocab.get("own_language", ""),
            size_hint_y=None,
            height=dp(40),
        )
        card.add_widget(prompt_lbl)

        # Anweisung
        instruction_text = getattr(
            labels,
            "typing_mode_instruction",
            "Gib die passende Übersetzung ein:",
        )
        instruction_lbl = self.make_text_label(
            instruction_text,
            size_hint_y=None,
            height=dp(30),
        )
        card.add_widget(instruction_lbl)

        # Eingabefeld
        self.typing_input = self.style_textinput(
            TextInput(
                multiline=False,
                size_hint=(1, None),
                height=dp(48),
            )
        )
        self.typing_input.bind(on_text_validate=self.typing_check_answer)
        card.add_widget(self.typing_input)

        # Feedback-Label
        self.typing_feedback_label = self.make_text_label(
            "",
            size_hint_y=None,
            height=dp(80),
        )
        self.typing_feedback_label.markup = True  # wichtig für [color]-Tags
        card.add_widget(self.typing_feedback_label)


        # Self-rating row (Anki-style) – zunächst versteckt
        self.typing_selfrating_box = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8),
        )

        if getattr(self, "self_rating_enabled", False):
            buttons = [
                ("self_rating_very_easy", "very_easy"),
                ("self_rating_easy", "easy"),
                ("self_rating_hard", "hard"),
                ("self_rating_very_hard", "very_hard"),
            ]
            for label_name, quality in buttons:
                text_label = getattr(labels, label_name, quality)
                btn = self.make_secondary_button(
                    text_label,
                    size_hint=(0.25, 1),
                    font_size=int(config["settings"]["gui"]["text_font_size"]),
                )
                # gleiche Logik wie bei Flashcards: passt knowledge_level an
                btn.bind(on_press=lambda inst, q=quality: self.self_rate_card(q))
                self.typing_selfrating_box.add_widget(btn)

        # erst nach einer Antwort aktiv
        self.typing_selfrating_box.opacity = 0
        self.typing_selfrating_box.disabled = True

        card.add_widget(self.typing_selfrating_box)


        # Buttons: Überprüfen / Überspringen
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(12),
        )

        check_text = getattr(
            labels,
            "typing_mode_check",
            "Überprüfen",
        )
        skip_text = getattr(
            labels,
            "typing_mode_skip",
            getattr(labels, "letter_salad_skip", "Überspringen"),
        )

        check_btn = self.make_primary_button(
            check_text,
            size_hint=(0.5, 1),
        )
        check_btn.bind(on_press=self.typing_check_answer)

        skip_btn = self.make_secondary_button(
            skip_text,
            size_hint=(0.5, 1),
        )
        skip_btn.bind(on_press=self.typing_skip)

        btn_row.add_widget(check_btn)
        btn_row.add_widget(skip_btn)

        card.add_widget(btn_row)

        center.add_widget(card)
        self.learn_content.add_widget(center)

        # Fokus gleich ins Eingabefeld
        Clock.schedule_once(lambda dt: setattr(self.typing_input, "focus", True), 0.05)

    def typing_check_answer(self, instance=None):
        """Check die Eingabe, färbt Buchstaben ein und geht ggf. weiter."""
        if not hasattr(self, "typing_input"):
            return

        if not self.all_vocab_list:
            return

        current_vocab = self.all_vocab_list[self.current_vocab_index]
        user_input = self.typing_input.text or ""

        if not user_input.strip():
            self.typing_feedback_label.color = APP_COLORS["muted"]
            empty_text = getattr(
                labels,
                "typing_mode_empty",
                "Bitte gib eine Antwort ein.",
            )
            self.typing_feedback_label.text = empty_text
            return

        # Original-Lösung: Hauptwort extrahieren (z.B. '(to) walk' -> 'walk')
        foreign_full = current_vocab.get("foreign_language", "") or ""
        latin_full = current_vocab.get("latin_language", "") or ""
        solution_main = self._extract_main_lexeme(foreign_full)

        # Klassifikation + farbiges Rendering (gegen die Fremdsprache)
        user_classes, sol_classes = self._classify_typed_vs_solution(
            solution_main, user_input
        )
        colored_user = self._colorize_with_classes(user_input, user_classes)
        colored_solution = self._colorize_with_classes(
            solution_main, sol_classes
        )

        # evtl. dritte Spalte im Feedback anhängen
        latin_suffix = ""
        if latin_full.strip():
            latin_suffix = f"\n[b]3. Spalte:[/b] {latin_full}"

        # Korrektheit (ohne Akzente, ohne Formatierungszeichen, Klammern optional)
        is_correct = self._is_correct_typed_answer(user_input, current_vocab)
        has_accent_issue = any(v == "accent" for v in user_classes.values())

        self.typing_feedback_label.markup = True

        if is_correct:
            # Knowledge update: big reward for correct typed answer
            delta = getattr(
                labels,
                "knowledge_delta_typing_correct",
                0.93,
            )
            self._adjust_knowledge_level(current_vocab, delta)

            # Antwort inhaltlich korrekt; Akzentfehler werden nur gelb markiert
            self.typing_feedback_label.color = APP_COLORS["success"]

            if has_accent_issue:
                success_text = getattr(
                    labels,
                    "typing_mode_correct_with_accents",
                    "Richtig (Akzente beachten):",
                )
                self.typing_feedback_label.text = (
                    f"{success_text}\n"
                    f"[b]Deine Eingabe:[/b] {colored_user}\n"
                    f"[b]Lösung:[/b] {colored_solution}"
                    f"{latin_suffix}"
                )
                anim = Animation(opacity=0.9, duration=0.1) + Animation(
                    opacity=1, duration=0.1
                )
                anim.start(self.typing_feedback_label)

                # Selbstbewertungs-Buttons freischalten
                if hasattr(self, "typing_selfrating_box"):
                    self.typing_selfrating_box.disabled = False
                    self.typing_selfrating_box.opacity = 1

            else:
                success_text = getattr(
                    labels,
                    "typing_mode_correct",
                    "Richtig!",
                )
                # ggf. dritte Spalte trotzdem anzeigen
                self.typing_feedback_label.text = success_text + latin_suffix

            anim = Animation(opacity=0.9, duration=0.1) + Animation(
                opacity=1, duration=0.1
            )
            anim.start(self.typing_feedback_label)
            # auch bei richtiger Antwort: Selbstbewertung erlauben
            if hasattr(self, "typing_selfrating_box"):
                self.typing_selfrating_box.disabled = False
                self.typing_selfrating_box.opacity = 1

        else:
            # Knowledge update: penalty per typed character
            per_char = getattr(
                labels,
                "knowledge_delta_typing_wrong_per_char",
                -0.01,
            )
            num_chars = len(user_input.strip())
            if num_chars > 0:
                self._adjust_knowledge_level(current_vocab, per_char * num_chars)

            # Inhaltlich falsch -> falsche Buchstaben rot, Akzentfehler gelb
            self.typing_feedback_label.color = APP_COLORS["text"]
            wrong_text = getattr(
                labels,
                "typing_mode_wrong",
                "Nicht ganz. Richtige Lösung:",
            )

            self.typing_feedback_label.text = (
                f"{wrong_text}\n"
                f"[b]Deine Eingabe:[/b] {colored_user}\n"
                f"[b]Lösung:[/b] {colored_solution}"
                f"{latin_suffix}"
            )

            anim = Animation(opacity=0.6, duration=0.1) + Animation(
                opacity=1, duration=0.1
            )
            anim.start(self.typing_feedback_label)


    def _typing_advance(self):
        """After a correct typed answer, go to the next vocab entry/mode."""
        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()

    def typing_skip(self, instance=None):
        """Skip the current vocab entry in typing mode."""
        current_vocab = self._get_current_vocab()
        if current_vocab is not None:
            # SRS – Karte als „falsch/übersprungen“
            self.update_srs(current_vocab, was_correct=False, quality=0.0)

        # Session-Schritt
        if self._register_session_step(was_correct=False):
            return

        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0

        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()


    # ------------------------------------------------------------------
    # Add / edit vocabulary entries
    # ------------------------------------------------------------------

    def add_vocab(self, stack, vocab, instance=None):
        """Screen for adding a single vocab entry to a stack."""
        log("entered add vocab")
        self.window.clear_widgets()

        # Top-right: back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        center_center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=80 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(
            cols=1,
            spacing=15,
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
            size_hint_y=None,
        )
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Own language
        form_layout.add_widget(
            self.make_title_label(
                labels.add_own_language,
                size_hint_y=None,
                height=dp(40),
            )
        )
        form_layout.add_widget(Label(text=""))
        self.add_own_language = self.style_textinput(
            TextInput(
                size_hint_y=None,
                height=60,
                multiline=False,
            )
        )
        form_layout.add_widget(self.add_own_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Foreign language
        form_layout.add_widget(
            self.make_title_label(
                labels.add_foreign_language,
                size_hint_y=None,
                height=dp(40),
            )
        )
        form_layout.add_widget(Label(text=""))
        self.add_foreign_language = self.style_textinput(
            TextInput(
                size_hint_y=None,
                height=60,
                multiline=False,
            )
        )
        form_layout.add_widget(self.add_foreign_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Optional third column
        self.third_column_input = None
        if save.read_languages("vocab/" + stack)[3]:
            form_layout.add_widget(
                self.make_title_label(
                    labels.add_third_column,
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            form_layout.add_widget(Label(text=""))
            self.third_column_input = self.style_textinput(
                TextInput(
                    size_hint_y=None,
                    height=60,
                    multiline=False,
                )
            )
            form_layout.add_widget(self.third_column_input)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Additional info
        form_layout.add_widget(
            self.make_title_label(
                labels.add_additional_info,
                size_hint_y=None,
                height=dp(40),
            )
        )
        form_layout.add_widget(Label(text=""))
        self.add_additional_info = self.style_textinput(
            TextInput(
                size_hint_y=None,
                height=60,
                multiline=False,
            )
        )
        form_layout.add_widget(self.add_additional_info)

        # Add button
        form_layout.add_widget(Label(text="\n\n\n\n"))
        self.add_vocab_button = self.make_primary_button(
            labels.add_vocabulary_button_text,
            size_hint=(1, None),
            height=dp(48),
        )
        self.add_vocab_button.bind(
            on_press=lambda instance: self.add_vocab_button_func(
                vocab, stack
            )
        )
        form_layout.add_widget(self.add_vocab_button)

        if self.third_column_input:
            self.widgets_add_vocab = [
                self.add_own_language,
                self.add_foreign_language,
                self.third_column_input,
                self.add_additional_info,
                self.add_vocab_button,
            ]
        else:
            self.widgets_add_vocab = [
                self.add_own_language,
                self.add_foreign_language,
                self.add_additional_info,
                self.add_vocab_button,
            ]

        Window.bind(on_key_down=self.on_key_down)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


    def add_vocab_button_func(self, vocab, stack, instance=None):
        """Handle saving a new vocab entry from the add-vocab form."""
        add_vocab_own_language = self.add_own_language.text.strip()
        add_vocab_foreign_language = self.add_foreign_language.text.strip()
        if self.third_column_input:
            add_vocab_third_column = self.third_column_input.text.strip()
        else:
            add_vocab_third_column = ""
        add_vocab_additional_info = self.add_additional_info.text.strip()
        log("Adding Vocab. Loaded textbox content")

        # Keine halbleeren Einträge: beide Sprachen müssen gesetzt sein
        if not add_vocab_own_language or not add_vocab_foreign_language:
            log("add_vocab_button_func: incomplete vocab (one or both languages empty) -> not saved.")

            msg = getattr(
                labels,
                "add_vocab_both_languages_required",
                "Bitte fülle beide Sprachfelder aus.",
            )
            ok_text = getattr(labels, "ok", "OK")

            content = BoxLayout(
                orientation="vertical",
                spacing=dp(8),
                padding=dp(12),
            )
            content.add_widget(
                self.make_text_label(
                    msg,
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            ok_btn = self.make_primary_button(
                ok_text,
                size_hint=(1, None),
                height=dp(40),
            )
            content.add_widget(ok_btn)

            popup = Popup(
                title="",
                content=content,
                size_hint=(0.6, 0.3),
            )
            ok_btn.bind(on_press=lambda *_: popup.dismiss())
            popup.open()
            return

        if self.third_column_input:
            vocab.append(
                {
                    "own_language": add_vocab_own_language,
                    "foreign_language": add_vocab_foreign_language,
                    "latin_language": add_vocab_third_column,
                    "info": add_vocab_additional_info,
                    "knowledge_level": 0.0,
                }
            )
        else:
            vocab.append(
                {
                    "own_language": add_vocab_own_language,
                    "foreign_language": add_vocab_foreign_language,
                    "latin_language": "",
                    "info": add_vocab_additional_info,
                    "knowledge_level": 0.0,
                }
            )

        save.save_to_vocab(vocab, "vocab/" + stack)
        log("added to stack")
        self.clear_inputs()


    # ------------------------------------------------------------------
    # Edit stack metadata (languages, filename)
    # ------------------------------------------------------------------

    def edit_metadata(self, stack, instance=None):
        """Screen for editing metadata such as languages and stack name."""
        log("entered edit metadata menu")
        self.window.clear_widgets()
        metadata = save.read_languages("vocab/" + stack)

        center_center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=80 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(
            cols=1,
            spacing=15,
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
            size_hint_y=None,
        )
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Top-right: back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # spacer for save button
        spacer_label = Label(text="\n\n\n\n\n\n\n\n\n")
        form_layout.add_widget(spacer_label)

        # Own language name
        form_layout.add_widget(
            self.make_title_label(
                labels.add_own_language,
                size_hint_y=None,
                height=dp(40),
            )
        )
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_own_language_textbox = self.style_textinput(
            TextInput(
                size_hint_y=None,
                height=60,
                multiline=False,
                text=metadata[0],
            )
        )
        form_layout.add_widget(self.edit_own_language_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))

        # Foreign language name
        form_layout.add_widget(
            self.make_title_label(
                labels.add_foreign_language,
                size_hint_y=None,
                height=dp(40),
            )
        )
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_foreign_language_textbox = self.style_textinput(
            TextInput(
                size_hint_y=None,
                height=60,
                multiline=False,
                text=metadata[1],
            )
        )
        form_layout.add_widget(self.edit_foreign_language_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))

        # Stack filename (without extension)
        form_layout.add_widget(
            self.make_title_label(
                labels.add_stack_filename,
                size_hint_y=None,
                height=dp(40),
            )
        )
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_name_textbox = self.style_textinput(
            TextInput(
                size_hint_y=None,
                height=60,
                multiline=False,
                text=stack[:-4],
            )
        )
        form_layout.add_widget(self.edit_name_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))

        # Top-center: "Save all" button
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=[30, 30, 100, 30],
        )
        save_all_button = self.make_primary_button(
            labels.save,
            size_hint=(None, None),
            size=(dp(160), dp(48)),
        )
        save_all_button.bind(
            on_press=lambda instance: self.edit_metadata_func(stack)
        )
        top_center.add_widget(save_all_button)
        self.window.add_widget(top_center)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


    # ------------------------------------------------------------------
    # Edit vocab grid (bulk editing)
    # ------------------------------------------------------------------

    def edit_vocab(self, stack, vocab, instance=None):
        """Screen for editing all vocab entries of a stack in a grid."""
        log("entered edit vocab menu")
        self.window.clear_widgets()

        self.edit_vocab_original_list = vocab

        center_center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=80 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(
            cols=1,
            spacing=15,
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
            size_hint_y=None,
        )
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Top-right: back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        matrix = self.build_vocab_grid(
            form_layout, vocab, save.read_languages("vocab/" + stack)[3]
        )

        # Top-center: "Save all" button
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=[30, 30, 100, 30],
        )
        save_all_button = self.make_primary_button(
            labels.save,
            size_hint=(None, None),
            size=(dp(160), dp(48)),
        )
        save_all_button.bind(
            on_press=lambda instance: self.edit_vocab_func(matrix, stack)
        )
        top_center.add_widget(save_all_button)
        self.window.add_widget(top_center)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)

    def learn_vocab_stack(self, stack, instance=None):
        """
        Legacy learning entry point for a single stack using simple
        front/back flashcards.
        """
        log("entered learn vocab menu")
        # Legacy-Modus zählt ebenfalls zur Gesamtlernzeit
        self.session_start_time = datetime.now()

        self.window.clear_widgets()
        self.all_vocab_list = []
        self.current_vocab_index = 0
        self.is_back = False
        self.self_rating_enabled = False  # legacy mode, no self-rating UI

        stack_vocab = save.load_vocab("vocab/" + stack)
        if type(stack_vocab) == tuple:
            stack_vocab = stack_vocab[0]
        for i in stack_vocab:
            self.all_vocab_list.append(i)
        random.shuffle(self.all_vocab_list)
        self.max_current_vocab_index = len(self.all_vocab_list)

        # Top-right: back button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        self.max_current_vocab_index = len(self.all_vocab_list)

        current_vocab = self.all_vocab_list[self.current_vocab_index]
        front_text = current_vocab["own_language"]

        center_center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        self.front_side_label = RoundedButton(
            text=front_text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(0.6, 0.8),
        )

        self.front_side_label.bind(on_press=self.flip_card_learn_func)
        center_center.add_widget(self.front_side_label)
        self.window.add_widget(center_center)

    def edit_vocab_func(self, matrix, stack, instance=None):
        """Read the vocab grid back into a list and save it."""
        latin_active = save.read_languages("vocab/" + stack)[3]
        vocab = self.read_vocab_from_grid(
            matrix,
            latin_active,
            getattr(self, "edit_vocab_original_list", None),
        )
        save.save_to_vocab(vocab, "vocab/" + stack)
        log("saved vocab")
        self.select_stack(stack)


    def edit_metadata_func(self, stack, instance=None):
        """Persist edited metadata and rename the underlying CSV file."""
        save.change_languages(
            "vocab/" + stack,
            self.edit_own_language_textbox.text,
            self.edit_foreign_language_textbox.text,
            "Latein",
            save.read_languages("vocab/" + stack)[3],
        )
        os.rename("vocab/" + stack, "vocab/" + str(self.edit_name_textbox.text) + ".csv")
        stack = self.edit_name_textbox.text + ".csv"
        self.select_stack(stack)

    def clear_inputs(self):
        """Clear add-vocab form fields and focus the first input."""
        self.add_own_language.text = ""
        self.add_foreign_language.text = ""
        if self.third_column_input:
            self.third_column_input.text = ""
        self.add_additional_info.text = ""
        self.add_own_language.focus = True

    def delete_stack(self, stack, instance=None):
        """Delete a stack CSV from disk and return to the main menu."""
        os.remove("vocab/" + stack)
        log("deleted stack: " + stack)
        self.main_menu()

    # ------------------------------------------------------------------
    # Keyboard navigation and helpers
    # ------------------------------------------------------------------

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        """
        Simple keyboard navigation for the add-vocab form.

        Tab / Shift+Tab moves focus between fields.
        Enter presses the last widget (the add button).
        """
        focused_index = None
        for i, widget in enumerate(self.widgets_add_vocab):
            if hasattr(widget, "focus") and widget.focus:
                focused_index = i
                break

        if focused_index is None:
            for widget in self.widgets_add_vocab:
                if hasattr(widget, "focus"):
                    widget.focus = True
                    return True

        # Tab / Shift+Tab
        if key == 9:
            if focused_index is not None:
                if "shift" in modifiers:
                    next_index = (focused_index - 1) % len(
                        self.widgets_add_vocab
                    )
                else:
                    next_index = (focused_index + 1) % len(
                        self.widgets_add_vocab
                    )
                self.widgets_add_vocab[next_index].focus = True
            return True

        # Enter
        if key == 13:
            if focused_index is not None:
                current = self.widgets_add_vocab[focused_index]
                if isinstance(current, TextInput):
                    self.widgets_add_vocab[-1].trigger_action(duration=0.1)
            return True

        return False

    def read_vocab_from_grid(self, textinput_matrix, latin_active, original_vocab_list=None):
        """
        Convert a matrix of TextInputs back into a vocab list.

        original_vocab_list (optional) wird genutzt, um z.B. knowledge_level
        pro Zeile beizubehalten. Neue Zeilen bekommen 0.0.
        """
        vocab_list = []

        for idx, row in enumerate(textinput_matrix):
            if latin_active:
                own, foreign, latin, info = [ti.text.strip() for ti in row]
            else:
                own, foreign, info = [ti.text.strip() for ti in row]
                latin = ""

            # keine Vokabel ohne Sprachen speichern
            if not own and not foreign:
                # komplett leer oder nur Zusatzinfos -> ignorieren
                continue

            # nur eine Sprache gefüllt? -> auch ignorieren
            if not own or not foreign:
                log("read_vocab_from_grid: skipped row with only one language filled.")
                continue

            entry = {
                "own_language": own,
                "foreign_language": foreign,
                "latin_language": latin,
                "info": info,
            }

            # knowledge_level aus der alten Liste übernehmen (falls vorhanden),
            # sonst 0.0
            if original_vocab_list is not None and idx < len(original_vocab_list):
                entry["knowledge_level"] = original_vocab_list[idx].get("knowledge_level", 0.0)
            else:
                entry["knowledge_level"] = 0.0

            vocab_list.append(entry)

        return vocab_list


    def build_vocab_grid(self, parent_layout, vocab_list, latin_active):
        """
        Build a grid of TextInputs for bulk editing vocab entries.

        Returns a matrix of TextInputs with 3 or 4 columns (depending on
        whether a Latin column is active).
        """
        cols = 4 if latin_active else 3

        grid = GridLayout(cols=cols, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        textinput_matrix = []

        for vocab in vocab_list:
            row = []

            for key in ["own_language", "foreign_language"]:
                ti = self.style_textinput(TextInput(
                    text=vocab.get(key, ""),
                    multiline=False,
                    size_hint_y=None,
                    height=60,
                ))
                grid.add_widget(ti)
                row.append(ti)

            if latin_active:
                ti = self.style_textinput(TextInput(
                    text=vocab.get("latin_language", ""),
                    multiline=False,
                    size_hint_y=None,
                    height=60,
                ))
                grid.add_widget(ti)
                row.append(ti)

            ti = self.style_textinput(TextInput(
                text=vocab.get("info", ""),
                multiline=False,
                size_hint_y=None,
                height=60,
            ))
            grid.add_widget(ti)
            row.append(ti)

            textinput_matrix.append(row)

        parent_layout.add_widget(grid)
        return textinput_matrix

    def bind_keyboard(self, dt):
        """Bind the on_key_down handler once the window is ready."""
        Window.bind(on_key_down=self.on_key_down)

    def three_column_checkbox(self, instance=None, value=None):
        """Update the three_columns_check flag when the checkbox is toggled."""
        if value:
            three_columns_check = True
        else:
            three_columns_check = False

    def on_touch_move(self, touch):
        """
        Optional hook to limit touch handling to this widget.

        Note: this method only makes sense when mixed into a Widget subclass.
        """
        if self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        return False

    # ------------------------------------------------------------------
    # Learning mode configuration helpers
    # ------------------------------------------------------------------

    def recompute_available_modes(self):
        """Rebuild self.available_modes based on config and vocab counts."""
        global config

        if get_in(config, ["settings", "modes"]) is None:
            set_in(
                config,
                ["settings", "modes"],
                {
                    "front_back": True,
                    "back_front": True,
                    "multiple_choice": True,
                    "letter_salad": True,
                    "connect_pairs": True,
                    "typing": True,
                    "syllable_salad": True,
                },
            )
            save.save_settings(config)

        modes_cfg = get_in(config, ["settings", "modes"], {}) or {}

        vocab_len = len(getattr(self, "all_vocab_list", []))
        unique_len = self._count_unique_vocab_pairs()

        self.available_modes = []

        # non-dependable of vocab lengh
        if bool_cast(modes_cfg.get("front_back", True)):
            self.available_modes.append("front_back")
        if bool_cast(modes_cfg.get("back_front", True)):
            self.available_modes.append("back_front")
        if bool_cast(modes_cfg.get("letter_salad", True)):
            self.available_modes.append("letter_salad")
        if bool_cast(modes_cfg.get("typing", True)):
            self.available_modes.append("typing")

        # dependable of vocab lengh
        if bool_cast(modes_cfg.get("multiple_choice", True)) and vocab_len >= 5:
            self.available_modes.append("multiple_choice")
        if bool_cast(modes_cfg.get("connect_pairs", True)) and unique_len >= 5:
            self.available_modes.append("connect_pairs")
        if bool_cast(modes_cfg.get("syllable_salad", True)) and vocab_len >= 3:
            self.available_modes.append("syllable_salad")

        # Fallback, falls wirklich nichts übrig bleibt
        if not self.available_modes:
            log("recompute_available_modes: no active modes, using fallback ['front_back']")
            self.available_modes = ["front_back"]


    def on_mode_checkbox_changed(self, path):
        """
        Return a handler that toggles a learning mode in the config and
        recomputes available modes.
        """

        def _handler(instance, value):
            global config
            set_in(config, path, bool(value))
            save.save_settings(config)
            self.recompute_available_modes()

        return _handler


# ---------------------------------------------------------------------------
# Small dict helpers and bool helper
# ---------------------------------------------------------------------------


def get_in(dct, path, default=None):
    """Safely access a nested value inside a dict via `path`."""
    cur = dct
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def set_in(dct, path, value):
    """Set a nested value inside a dict, creating dicts along the path."""
    cur = dct
    for k in path[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[path[-1]] = value


def bool_cast(v):
    """Convert different value types into a boolean in a forgiving way."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(v)


if __name__ == "__main__":
    VokabaApp().run()
