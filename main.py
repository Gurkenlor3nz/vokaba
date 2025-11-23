"""Main UI module for the Vokaba vocabulary trainer (Kivy app)."""

# Standard library imports
from datetime import datetime
import os
import os.path
import random
import re
import unicodedata

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
from kivy.uix.widget import Widget

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

APP_COLORS = {
    "bg":            (18 / 255, 18 / 255, 26 / 255, 1),   # app background
    "primary":       (0.26, 0.60, 0.96, 1),               # main accent blue
    "primary_dark":  (0.18, 0.45, 0.80, 1),
    "accent":        (1.00, 0.76, 0.03, 1),               # secondary accent
    "text":          (1, 1, 1, 1),                        # white text
    "muted":         (0.75, 0.75, 0.80, 1),               # muted/secondary text
    "card":          (0.16, 0.17, 0.23, 1),               # card backgrounds
    "card_selected": (0.24, 0.25, 0.32, 1),               # selected card
    "danger":        (0.90, 0.22, 0.21, 1),               # destructive actions
    "success":       (0.20, 0.70, 0.30, 1),               # success/correct
}


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
        Window.clearcolor = APP_COLORS["bg"]
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

    def make_icon_button(self, icon_path, on_press, size=dp(56), **kwargs):
        """Create an icon-only button from an image asset."""
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
        """Apply a dark theme style to a TextInput."""
        ti.background_normal = ""
        ti.background_active = ""
        ti.background_color = (0.12, 0.12, 0.16, 1)
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

    # ------------------------------------------------------------------
    # Main menu
    # ------------------------------------------------------------------

    def main_menu(self, instance=None):
        """Build and display the main menu with the stack list and learn button."""
        log("opened main menu")
        self.window.clear_widgets()
        config = save.load_settings()
        Config.window_icon = "assets/vokaba_icon.png"

        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Top-left: logo button (opens settings)
        top_left = AnchorLayout(
            anchor_x="left",
            anchor_y="top",
            padding=30 * padding_mul,
        )
        vokaba_logo = self.make_icon_button(
            "assets/vokaba_logo.png",
            on_press=self.settings,
            size=dp(104),
        )
        top_left.add_widget(vokaba_logo)
        self.window.add_widget(top_left)

        # Top-center: welcome text
        top_center = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            padding=[0, 30 * padding_mul, 0, 0],
        )
        welcome_label = self.make_title_label(
            labels.welcome_text,
            size_hint=(None, None),
            size=(dp(400), dp(60)),
        )
        top_center.add_widget(welcome_label)
        self.window.add_widget(top_center)

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

        # Center: card with scrollable list of vocab stacks
        center_anchor = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=60 * padding_mul,
        )

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.8, 0.8),
            padding=dp(12),
            spacing=dp(8),
        )

        # Scrollable list of files in labels.vocab_path
        self.file_list = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.file_list.bind(minimum_height=self.file_list.setter("height"))

        if not os.path.exists("vocab"):
            os.makedirs("vocab")

        for i in os.listdir(labels.vocab_path):
            if os.path.isfile(os.path.join(labels.vocab_path, i)):
                btn = self.make_list_button(i[:-4])
                btn.bind(on_release=lambda btn, name=i: self.select_stack(name))
                self.file_list.add_widget(btn)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_y=True)
        self.file_list.bind(minimum_width=self.file_list.setter("width"))
        self.scroll.add_widget(self.file_list)
        card.add_widget(self.scroll)

        center_anchor.add_widget(card)
        self.window.add_widget(center_anchor)

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
                "max": 80,
                "value": float(config["settings"]["gui"]["title_font_size"]),
                "callback": self.on_setting_changed(
                    ["settings", "gui", "title_font_size"], int
                ),
            },
            {
                "label": labels.settings_font_size_slider,
                "min": 10,
                "max": 30,
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


        # Learning mode toggles
        modes_header_text = getattr(labels, "settings_modes_header")

        settings_content.add_widget(
            self.make_title_label(
                modes_header_text + "\n\n\n",
                size_hint_y=None,
                height=dp(
                    300
                    * float(config["settings"]["gui"]["padding_multiplicator"])
                ),
            )
        )

        modes_card = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(8),
            spacing=dp(8),
        )

        grid = GridLayout(
            cols=2,
            size_hint_y=None,
            row_default_height=dp(50),
            row_force_default=True,
            spacing=dp(8),
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
                size=(dp(28), dp(28)),
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
            l3.text += "  [size=12][i](mind. 5 Einträge nötig)[/i][/size]"
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
                "  [size=12][i](mind. 5 eindeutige Paare nötig)[/i][/size]"
            )
            l5.markup = True
        grid.add_widget(l5)
        grid.add_widget(c5)


        # typing input mode (Eingabe-Modus)
        typing_label_text = getattr(
            labels, "learn_flashcards_typing_mode",
        )
        l6, c6 = add_mode_row("typing", typing_label_text)
        grid.add_widget(l6)
        grid.add_widget(c6)

        # connect 5 pairs
        l5, c5 = add_mode_row(
            "connect_pairs",
            getattr(
                labels,
                "learn_flashcards_connect_pairs",
            ),
        )

        modes_card.add_widget(grid)
        settings_content.add_widget(modes_card)

        scroll.add_widget(settings_content)
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
            height=dp(40),
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
            height=dp(40),
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
            height=dp(40),
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
            size=(dp(28), dp(28)),
        )
        self.three_columns.bind(active=self.three_column_checkbox)
        row.add_widget(self.three_columns)
        form_layout.add_widget(row)

        # Submit button
        add_stack_button = self.make_primary_button(
            labels.add_stack_button_text,
            size_hint=(1, None),
            height=dp(48),
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

        Depending on `mode`, show_current_card() will render different
        interactions (flashcards, multiple choice, letter salad, connect pairs).
        """
        log(f"entered learn menu with mode={mode}")
        self.learn_mode = mode

        self.window.clear_widgets()

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

        # Top-right back button
        top_right = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56),
        )
        top_right.add_widget(back_button)
        self.learn_area.add_widget(top_right)

        # Build the vocab list for this session (single stack or all stacks)
        all_vocab = []
        self.all_vocab_list = []
        self.is_back = False
        self.current_vocab_index = 0

        if stack:
            file = save.load_vocab("vocab/" + stack)
            if isinstance(file, tuple):
                file = file[0]
            all_vocab.append(file)
        else:
            for i in os.listdir("vocab/"):
                file = save.load_vocab("vocab/" + i)
                if isinstance(file, tuple):
                    file = file[0]
                all_vocab.append(file)

        for vocab_list in all_vocab:
            for entry in vocab_list:
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

        # Only allow modes that are enabled and have enough data
        self.recompute_available_modes()

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

        else:
            log(f"Unknown learn mode {self.learn_mode}, fallback to front_back")
            self.learn(None, "front_back")

    def show_button_card(self, text, callback):
        """Simple flashcard screen: one big button that flips or advances."""
        if hasattr(self, "header_label"):
            self.header_label.text = ""

        center_center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(
                config["settings"]["gui"]["padding_multiplicator"]
            ),
        )

        self.front_side_label = RoundedButton(
            text=text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(0.7, 0.6),
        )
        self.front_side_label.bind(on_press=callback)
        center_center.add_widget(self.front_side_label)
        self.learn_content.add_widget(center_center)

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


    def flip_card_learn_func(self, instance=None):
        """
        Flip behavior for front_back / back_front.

        First tap: show the back side with a short animation.
        Second tap: advance to the next card and possibly switch mode.
        """
        # Animate only when flipping from front to back
        if not self.is_back and self.learn_mode in ("front_back", "back_front"):
            self.is_back = True
            self.animate_flip_current_card()
            return

        # Back side: advance to next card and randomize mode
        if self.is_back:
            if self.current_vocab_index >= self.max_current_vocab_index - 1:
                self.current_vocab_index = 0
                random.shuffle(self.all_vocab_list)
            else:
                self.current_vocab_index += 1

            self.is_back = False
            self.learn_mode = random.choice(self.available_modes)
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
                text=str(opt.get("foreign_language", "")),
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
        if self.current_vocab_index >= self.max_current_vocab_index - 1:
            self.current_vocab_index = 0
        else:
            self.current_vocab_index += 1

        self.is_back = False
        self.learn_mode = random.choice(self.available_modes)
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
            text = entry.get("foreign_language", "")
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
        if self.current_vocab_index >= self.max_current_vocab_index - 1:
            self.current_vocab_index = 0
        else:
            self.current_vocab_index += 1

        self.is_back = False
        self.learn_mode = random.choice(self.available_modes)
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

        # Clean target: strip spaces and content in parentheses
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

        target_clean = "".join(cleaned_chars)

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

        self.letter_salad_target_raw = raw_target
        self.letter_salad_target_clean = target_clean
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

        # Grid of letter tiles
        cols = max(1, min(len(scrambled_letters), 10))
        letters_layout = GridLayout(
            cols=cols,
            spacing=dp(8),
            size_hint_y=None,
            height=dp(70),
        )

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
            letters_layout.add_widget(btn)

        card.add_widget(letters_layout)

        # Bottom row: skip / reshuffle
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(12),
        )

        skip_text = getattr(labels, "letter_salad_skip")
        reshuffle_text = getattr(
            labels, "letter_salad_reshuffle")

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
        """After a correct word, go to the next vocab entry and mode."""
        if self.current_vocab_index >= self.max_current_vocab_index - 1:
            self.current_vocab_index = 0
        else:
            self.current_vocab_index += 1

        self.is_back = False
        self.learn_mode = random.choice(self.available_modes)
        self.show_current_card()

    def letter_salad_skip(self, instance=None):
        """Skip the current vocab entry in letter salad mode."""
        if self.current_vocab_index >= self.max_current_vocab_index - 1:
            self.current_vocab_index = 0
        else:
            self.current_vocab_index += 1

        self.is_back = False
        self.learn_mode = random.choice(self.available_modes)
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

        # Original-Lösung (nur der Teil vor der ersten Klammer ist relevant)
        # Original-Lösung: Hauptwort extrahieren (z.B. '(to) walk' -> 'walk')
        foreign_full = current_vocab.get("foreign_language", "") or ""
        solution_main = self._extract_main_lexeme(foreign_full)

        # Klassifikation + farbiges Rendering
        user_classes, sol_classes = self._classify_typed_vs_solution(
            solution_main, user_input
        )
        colored_user = self._colorize_with_classes(user_input, user_classes)
        colored_solution = self._colorize_with_classes(
            solution_main, sol_classes
        )

        # Korrektheit (ohne Akzente, ohne Formatierungszeichen, Klammern optional)
        is_correct = self._is_correct_typed_answer(user_input, current_vocab)
        has_accent_issue = any(v == "accent" for v in user_classes.values())


        self.typing_feedback_label.markup = True

        if is_correct:
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
                )
            else:
                success_text = getattr(
                    labels,
                    "typing_mode_correct",
                    "Richtig!",
                )
                self.typing_feedback_label.text = success_text

            anim = Animation(opacity=0.9, duration=0.1) + Animation(
                opacity=1, duration=0.1
            )
            anim.start(self.typing_feedback_label)

            Clock.schedule_once(lambda dt: self._typing_advance(), 0.35)

        else:
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
            )

            anim = Animation(opacity=0.6, duration=0.1) + Animation(
                opacity=1, duration=0.1
            )
            anim.start(self.typing_feedback_label)


    def _typing_advance(self):
        """After a correct typed answer, go to the next vocab entry/mode."""
        if self.current_vocab_index >= self.max_current_vocab_index - 1:
            self.current_vocab_index = 0
        else:
            self.current_vocab_index += 1

        self.is_back = False
        self.learn_mode = random.choice(self.available_modes)
        self.show_current_card()

    def typing_skip(self, instance=None):
        """Skip the current vocab entry in typing mode."""
        if self.current_vocab_index >= self.max_current_vocab_index - 1:
            self.current_vocab_index = 0
        else:
            self.current_vocab_index += 1

        self.is_back = False
        self.learn_mode = random.choice(self.available_modes)
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
            Label(
                text=labels.add_own_language,
                font_size=int(config["settings"]["gui"]["title_font_size"]),
            )
        )
        form_layout.add_widget(Label(text=""))
        self.add_own_language = self.style_textinput(TextInput(
            size_hint_y=None, height=60, multiline=False
        ))
        form_layout.add_widget(self.add_own_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Foreign language
        form_layout.add_widget(
            Label(
                text=labels.add_foreign_language,
                font_size=int(config["settings"]["gui"]["title_font_size"]),
            )
        )
        form_layout.add_widget(Label(text=""))
        self.add_foreign_language = self.style_textinput(TextInput(
            size_hint_y=None, height=60, multiline=False
        ))
        form_layout.add_widget(self.add_foreign_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Optional third column
        self.third_column_input = None
        if save.read_languages("vocab/" + stack)[3]:
            form_layout.add_widget(
                Label(
                    text=labels.add_third_column,
                    font_size=int(
                        config["settings"]["gui"]["title_font_size"]
                    ),
                )
            )
            form_layout.add_widget(Label(text=""))
            self.third_column_input = self.style_textinput(TextInput(
                size_hint_y=None, height=60, multiline=False
            ))
            form_layout.add_widget(self.third_column_input)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Additional info
        form_layout.add_widget(
            Label(
                text=labels.add_additional_info,
                font_size=int(config["settings"]["gui"]["title_font_size"]),
            )
        )
        form_layout.add_widget(Label(text=""))
        self.add_additional_info = self.style_textinput(TextInput(
            size_hint_y=None, height=60, multiline=False
        ))
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
        add_vocab_own_lanauage = self.add_own_language.text
        add_vocab_foreign_language = self.add_foreign_language.text
        if self.third_column_input:
            add_vocab_third_column = self.third_column_input.text
        else:
            add_vocab_third_column = None
        add_vocab_additional_info = self.add_additional_info.text
        log("Adding Vocab. Loaded textbox content")
        if self.third_column_input:
            vocab.append(
                {
                    "own_language": add_vocab_own_lanauage,
                    "foreign_language": add_vocab_foreign_language,
                    "latin_language": add_vocab_third_column,
                    "info": add_vocab_additional_info,
                }
            )
        else:
            vocab.append(
                {
                    "own_language": add_vocab_own_lanauage,
                    "foreign_language": add_vocab_foreign_language,
                    "latin_language": "",
                    "info": add_vocab_additional_info,
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
            Label(
                text=labels.add_own_language,
                font_size=int(config["settings"]["gui"]["title_font_size"]),
            )
        )
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_own_language_textbox = self.style_textinput(TextInput(
            size_hint_y=None, height=60, multiline=False, text=metadata[0]
        ))
        form_layout.add_widget(self.edit_own_language_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))

        # Foreign language name
        form_layout.add_widget(
            Label(
                text=labels.add_foreign_language,
                font_size=int(config["settings"]["gui"]["title_font_size"]),
            )
        )
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_foreign_language_textbox = self.style_textinput(TextInput(
            size_hint_y=None, height=60, multiline=False, text=metadata[1]
        ))
        form_layout.add_widget(self.edit_foreign_language_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))

        # Stack filename (without extension)
        form_layout.add_widget(
            Label(
                text=labels.add_stack_filename,
                font_size=int(config["settings"]["gui"]["title_font_size"]),
            )
        )
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_name_textbox = self.style_textinput(TextInput(
            size_hint_y=None, height=60, multiline=False, text=stack[:-4]
        ))
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
        self.window.clear_widgets()
        self.all_vocab_list = []
        self.current_vocab_index = 0
        self.is_back = False

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
        vocab = self.read_vocab_from_grid(
            matrix, save.read_languages("vocab/" + stack)[3]
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

    def read_vocab_from_grid(self, textinput_matrix, latin_active):
        """Convert a matrix of TextInputs back into a vocab list."""
        vocab_list = []

        for row in textinput_matrix:
            if latin_active:
                own, foreign, latin, info = [ti.text.strip() for ti in row]
            else:
                own, foreign, info = [ti.text.strip() for ti in row]
                latin = ""

            # Skip completely empty rows
            if not own and not foreign and not latin and not info:
                continue

            vocab_list.append(
                {
                    "own_language": own,
                    "foreign_language": foreign,
                    "latin_language": latin,
                    "info": info,
                }
            )

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
                },
            )
            save.save_settings(config)

        modes_cfg = get_in(config, ["settings", "modes"], {}) or {}

        vocab_len = len(getattr(self, "all_vocab_list", []))
        unique_len = self._count_unique_vocab_pairs()

        self.available_modes = []
        if bool_cast(modes_cfg.get("front_back", True)):
            self.available_modes.append("front_back")
        if bool_cast(modes_cfg.get("back_front", True)):
            self.available_modes.append("back_front")
        if bool_cast(modes_cfg.get("multiple_choice", True)) and vocab_len >= 5:
            self.available_modes.append("multiple_choice")
        if bool_cast(modes_cfg.get("letter_salad", True)):
            self.available_modes.append("letter_salad")
        if bool_cast(modes_cfg.get("connect_pairs", True)) and unique_len >= 5:
            self.available_modes.append("connect_pairs")
        if bool_cast(modes_cfg.get("typing", True)):
            self.available_modes.append("typing")

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
