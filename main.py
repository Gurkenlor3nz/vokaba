"""------Import Python packages------"""
from datetime import datetime
import os
import os.path
import yaml
import random


"""------Import kivy widgets------"""
from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy.clock import Clock

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import *
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle



"""------Import files------"""""
import labels
import save


"""------Init Variables------"""
selected_stack = ""
global vocab_current
global title_size_slider
global three_columns_check
config = save.load_settings()


""" --- Farb- und Layout-Theme ---------------------------------"""
APP_COLORS = {
    "bg":          (18/255, 18/255, 26/255, 1),   # Hintergrund
    "primary":     (0.26, 0.60, 0.96, 1),         # Blau
    "primary_dark":(0.18, 0.45, 0.80, 1),
    "accent":      (1.00, 0.76, 0.03, 1),         # Gelb
    "text":        (1, 1, 1, 1),                  # Weiß
    "muted":       (0.75, 0.75, 0.80, 1),         # Grauer Text
    "card":        (0.16, 0.17, 0.23, 1),         # Karten
    "danger":      (0.90, 0.22, 0.21, 1),         # Rot (löschen)
}


class RoundedCard(BoxLayout):
    """Container mit abgerundeten Ecken als Hintergrund."""
    def __init__(self, bg_color=None, radius=None, **kwargs):
        self._bg_color_value = bg_color or APP_COLORS["card"]
        self._radius = radius or dp(18)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color = Color(*self._bg_color_value)
            self._bg_rect = RoundedRectangle(radius=[self._radius]*4)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class RoundedButton(Button):
    """Button mit abgerundeten Ecken und eigener Hintergrundfarbe."""
    def __init__(self, bg_color=None, radius=None, **kwargs):
        # Eigene Werte merken, bevor Kivy initialisiert
        self._bg_color_value = bg_color or APP_COLORS["primary"]
        self._radius = radius or dp(18)

        super().__init__(**kwargs)

        # Standard-Hintergrund komplett ausknipsen
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        # Alle bisherigen canvas.before-Instruktionen (inkl. Default) löschen
        self.canvas.before.clear()

        # Eigene runde Fläche zeichnen
        with self.canvas.before:
            self._bg_color_instr = Color(*self._bg_color_value)
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[self._radius] * 4
            )

        # Wenn Größe/Position sich ändern, Rechteck nachziehen
        self.bind(pos=self._update_bg, size=self._update_bg)

    def set_bg_color(self, rgba):
        """Falls du später dynamisch die Farbe ändern willst."""
        self._bg_color_value = rgba
        if hasattr(self, "_bg_color_instr"):
            self._bg_color_instr.rgba = rgba

    def _update_bg(self, *args):
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size


def log(text):
    print("LOG  time: " + str(datetime.now())[11:] + "; content: \"" + text + "\"")


#Class for touch sliders
class NoScrollSlider(Slider):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
        # Touch für diesen Slider "festhalten" und normale Slider-Logik ausführen
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
    def build(self):
        Window.clearcolor = APP_COLORS["bg"]
        self.window = FloatLayout()
        self.scroll = ScrollView(size_hint=(1, 1))
        self.main_menu()
        return self.window

    # ----------------- Style-Helfer -----------------

    def make_title_label(self, text, **kwargs):
        lbl = Label(
            text=text,
            color=APP_COLORS["text"],
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            **kwargs
        )
        lbl.halign = "center"
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_text_label(self, text, **kwargs):
        lbl = Label(
            text=text,
            color=APP_COLORS["muted"],
            font_size=int(config["settings"]["gui"]["text_font_size"]),
            **kwargs
        )
        lbl.halign = kwargs.get("halign", "left")
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_primary_button(self, text, **kwargs):
        # Nutzer kann font_size überschreiben
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"])
        )
        return RoundedButton(
            text=text,
            bg_color=APP_COLORS["primary"],
            color=APP_COLORS["text"],
            font_size=font_size,
            **kwargs
        )

    def make_secondary_button(self, text, **kwargs):
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"])
        )
        return RoundedButton(
            text=text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=font_size,
            **kwargs
        )

    def make_danger_button(self, text, **kwargs):
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"])
        )
        return RoundedButton(
            text=text,
            bg_color=APP_COLORS["danger"],
            color=APP_COLORS["text"],
            font_size=font_size,
            **kwargs
        )

    def make_list_button(self, text, **kwargs):
        font_size = kwargs.pop(
            "font_size",
            int(config["settings"]["gui"]["text_font_size"])
        )
        btn = RoundedButton(
            text=text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=font_size,
            size_hint_y=None,
            height=dp(50),
            **kwargs
        )
        btn.halign = "left"
        btn.valign = "middle"
        btn.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return btn

    def make_icon_button(self, icon_path, on_press, size=dp(56), **kwargs):
        btn = Button(
            size_hint=(None, None),
            size=(size, size),
            background_normal=icon_path,
            background_down=icon_path,
            border=(0, 0, 0, 0),
            **kwargs
        )
        btn.bind(on_press=on_press)
        return btn

    def style_textinput(self, ti: TextInput) -> TextInput:
        ti.background_normal = ""
        ti.background_active = ""
        ti.background_color = (0.12, 0.12, 0.16, 1)
        ti.foreground_color = APP_COLORS["text"]
        ti.cursor_color = APP_COLORS["accent"]
        ti.padding = [dp(8), dp(8), dp(8), dp(8)]
        return ti

    def main_menu(self, instance=None):
        log("opened main menu")
        self.window.clear_widgets()
        config = save.load_settings()
        Config.window_icon = "assets/vokaba_icon.png"

        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # --- Header: Logo, Titel, Settings ---
        top_left = AnchorLayout(anchor_x="left", anchor_y="top",
                                padding=30 * padding_mul)
        vokaba_logo = self.make_icon_button(
            "assets/vokaba_logo.png",
            on_press=self.settings,
            size=dp(72)
        )
        top_left.add_widget(vokaba_logo)
        self.window.add_widget(top_left)

        top_center = AnchorLayout(anchor_x="center", anchor_y="top",
                                  padding=[0, 30 * padding_mul, 0, 0])
        welcome_label = self.make_title_label(
            labels.welcome_text,
            size_hint=(None, None),
            size=(dp(400), dp(60))
        )
        top_center.add_widget(welcome_label)
        self.window.add_widget(top_center)

        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * padding_mul)
        settings_button = self.make_icon_button(
            "assets/settings_icon.png",
            on_press=self.settings,
            size=dp(56)
        )
        top_right.add_widget(settings_button)
        self.window.add_widget(top_right)

        # --- Mitte: Karte mit Scroll-Liste der Vokabelstapel ---
        center_anchor = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=60 * padding_mul)

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.8, 0.8),
            padding=dp(12),
            spacing=dp(8)
        )

        # Scrollbare Liste
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

        # --- Bottom: Add + Lernen-Button ---
        bottom_right = AnchorLayout(anchor_x="right", anchor_y="bottom",
                                    padding=30 * padding_mul)
        add_stack_button = self.make_icon_button(
            "assets/add_stack.png",
            on_press=self.add_stack,
            size=dp(64)
        )
        bottom_right.add_widget(add_stack_button)
        self.window.add_widget(bottom_right)

        self.recompute_available_modes()
        bottom_center = AnchorLayout(anchor_x="center", anchor_y="bottom",
                                     padding=12 * padding_mul)

        learn_text = getattr(labels, "learn_stack_vocab_button_text", "Lernen")
        learn_button = self.make_primary_button(
            learn_text,
            size_hint=(None, None),
            size=(dp(220), dp(80)),
            font_size=dp(26)
        )
        learn_button.bind(on_press=lambda instance: self.learn(
            stack=None,
            mode=random.choice(self.available_modes)
        ))
        bottom_center.add_widget(learn_button)
        self.window.add_widget(bottom_center)

    def settings(self, instance):
        log("opened settings")
        self.window.clear_widgets()
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Back Button oben rechts
        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * padding_mul)
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Karten-Container in der Mitte
        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=40 * padding_mul)
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.85),
            padding=dp(16),
            spacing=dp(12)
        )

        scroll = ScrollView(size_hint=(1, 1))
        settings_content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(16),
            padding=dp(4)
        )
        settings_content.bind(minimum_height=settings_content.setter("height"))

        settings_definitions = [
            {
                "label": labels.settings_title_font_size_slider_test_label,
                "min": 10, "max": 80,
                "value": float(config["settings"]["gui"]["title_font_size"]),
                "callback": self.on_setting_changed(["settings", "gui", "title_font_size"], int)
            },
            {
                "label": labels.settings_font_size_slider,
                "min": 10, "max": 30,
                "value": float(config["settings"]["gui"]["text_font_size"]),
                "callback": self.on_setting_changed(["settings", "gui", "text_font_size"], int)
            },
            {
                "label": labels.settings_padding_multiplikator_slider,
                "min": 0.1, "max": 3,
                "value": float(config["settings"]["gui"]["padding_multiplicator"]),
                "callback": self.on_setting_changed(["settings", "gui", "padding_multiplicator"], float)
            },
        ]

        for setting in settings_definitions:
            # Mini-Card für jede Einstellung
            row_card = RoundedCard(
                orientation="vertical",
                size_hint_y=None,
                height=dp(110),
                padding=dp(8),
                spacing=dp(4)
            )

            lbl = self.make_text_label(
                setting["label"],
                size_hint_y=None,
                height=dp(40)
            )

            slider = NoScrollSlider(
                min=setting["min"], max=setting["max"],
                value=setting["value"],
                size_hint_y=None,
                height=dp(40)
            )
            slider.bind(value=setting["callback"])

            row_card.add_widget(lbl)
            row_card.add_widget(slider)
            settings_content.add_widget(row_card)

        # --- Lernmodi ---
        modes_header_text = getattr(labels, "settings_modes_header", "Lernmodi")

        settings_content.add_widget(self.make_title_label(
            modes_header_text,
            size_hint_y=None,
            height=dp(120 * float(config["settings"]["gui"]["padding_multiplicator"]))))

        modes_card = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(8),
            spacing=dp(8)
        )

        grid = GridLayout(cols=2, size_hint_y=None,
                          row_default_height=dp(50),
                          row_force_default=True,
                          spacing=dp(8))
        grid.bind(minimum_height=grid.setter("height"))

        def add_mode_row(mode_key, mode_label):
            current = bool_cast(get_in(config, ["settings", "modes", mode_key], True))
            lbl = self.make_text_label(
                mode_label,
                size_hint_y=None,
                height=dp(50)
            )
            cb = CheckBox(active=current, size_hint=(None, None), size=(dp(28), dp(28)))
            cb.bind(active=self.on_mode_checkbox_changed(["settings", "modes", mode_key]))
            return lbl, cb

        # front_back
        l1, c1 = add_mode_row("front_back", labels.learn_flashcards_front_to_back)
        grid.add_widget(l1);
        grid.add_widget(c1)

        # back_front
        l2, c2 = add_mode_row("back_front", labels.learn_flashcards_back_to_front)
        grid.add_widget(l2);
        grid.add_widget(c2)

        # multiple_choice
        vocab_len_in_settings = len(getattr(self, "all_vocab_list", []))
        l3, c3 = add_mode_row("multiple_choice", labels.learn_flashcards_multiple_choice)
        if vocab_len_in_settings < 5:
            c3.disabled = True
            l3.text += "  [size=12][i](mind. 5 Einträge nötig)[/i][/size]"
            l3.markup = True
        grid.add_widget(l3);
        grid.add_widget(c3)

        # letter salad
        l3, c3, = add_mode_row("letter_salad", labels.learn_flashcards_letter_salad)
        grid.add_widget(l3);
        grid.add_widget(c3)

        modes_card.add_widget(grid)
        settings_content.add_widget(modes_card)

        scroll.add_widget(settings_content)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)


    def select_stack(self, stack):
        vocab_file = str("vocab/" + stack)
        vocab_current = save.load_vocab(vocab_file)
        if "tuple" in str(type(vocab_current)):
            vocab_current = vocab_current[0]
        log("opened stack: " + stack)
        self.window.clear_widgets()
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Titel oben
        top_center = AnchorLayout(anchor_x="center", anchor_y="top",
                                  padding=15 * padding_mul)
        stack_title_label = self.make_title_label(
            stack[:-4],
            size_hint=(None, None),
            size=(dp(300), dp(40))
        )
        top_center.add_widget(stack_title_label)
        self.window.add_widget(top_center)

        # Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * padding_mul)
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Mitte: Karten-Container mit Buttons
        center_anchor = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=[30, 60, 100, 30])

        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.7),
            padding=dp(16),
            spacing=dp(12)
        )

        scroll = ScrollView(size_hint=(1, 1), do_scroll_y=True)
        grid = GridLayout(cols=1, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        # Delete Stack Button
        delete_stack_button = self.make_danger_button(
            labels.delete_stack_button,
            size_hint_y=None,
            height=dp(60)
        )
        delete_stack_button.bind(on_press=lambda instance: self.delete_stack_confirmation(stack))
        grid.add_widget(delete_stack_button)

        # Edit Metadata Button
        edit_metadata_button = self.make_secondary_button(
            labels.edit_metadata_button_text,
            size_hint_y=None,
            height=dp(60)
        )
        edit_metadata_button.bind(on_press=lambda instance: self.edit_metadata(stack))
        grid.add_widget(edit_metadata_button)

        # Add Vocab Button
        add_vocab_button = self.make_primary_button(
            labels.add_vocab_button_text,
            size_hint_y=None,
            height=dp(60)
        )
        add_vocab_button.bind(on_press=lambda instance: self.add_vocab(stack, vocab_current))
        grid.add_widget(add_vocab_button)

        # Edit Vocab Button
        edit_vocab_button = self.make_secondary_button(
            labels.edit_vocab_button_text,
            size_hint_y=None,
            height=dp(60)
        )
        edit_vocab_button.bind(on_press=lambda instance: self.edit_vocab(stack, vocab_current))
        grid.add_widget(edit_vocab_button)

        self.recompute_available_modes()
        learn_vocab_button = self.make_primary_button(
            labels.learn_stack_vocab_button_text,
            size_hint_y=None,
            height=dp(60)
        )
        learn_vocab_button.bind(on_press=lambda instance: self.learn(stack, mode=random.choice(self.available_modes)))
        grid.add_widget(learn_vocab_button)

        scroll.add_widget(grid)
        card.add_widget(scroll)
        center_anchor.add_widget(card)
        self.window.add_widget(center_anchor)



    def delete_stack_confirmation(self, stack, instance=None):
        log("Entered delete stack Confirmation")
        self.window.clear_widgets()
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * padding_mul)
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Mitte: Karte mit Warntext
        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=40 * padding_mul)
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.8, 0.6),
            padding=dp(16),
            spacing=dp(12),
            bg_color=(0.25, 0.10, 0.10, 1)   # leicht rötlicher Hintergrund
        )

        caution_text = self.make_title_label(
            labels.caution,
            size_hint_y=None,
            height=dp(40)
        )
        caution_text.markup = True

        deleting_text = self.make_text_label(
            labels.delete_stack_confirmation_text,
            size_hint_y=None,
            height=dp(60)
        )
        deleting_text.markup = True

        not_undone_text = self.make_text_label(
            labels.cant_be_undone,
            size_hint_y=None,
            height=dp(40)
        )
        not_undone_text.markup = True

        card.add_widget(caution_text)
        card.add_widget(deleting_text)
        card.add_widget(not_undone_text)

        # Buttons unten
        btn_row = BoxLayout(orientation="horizontal",
                            size_hint_y=None,
                            height=dp(60),
                            spacing=dp(12))

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



    def add_stack(self, instance):
        self.window.clear_widgets()
        log("opened add stack menu")
        padding_mul = float(config["settings"]["gui"]["padding_multiplicator"])

        # Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * padding_mul)
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        # Titel oben
        top_center = AnchorLayout(anchor_x="center", anchor_y="top",
                                  padding=30 * padding_mul)
        add_stack_label = self.make_title_label(
            labels.add_stack_title_text,
            size_hint=(None, None),
            size=(dp(300), dp(40))
        )
        top_center.add_widget(add_stack_label)
        self.window.add_widget(top_center)

        # Mitte: Karte mit Formular
        center_center = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=40 * padding_mul)
        card = RoundedCard(
            orientation="vertical",
            size_hint=(0.85, 0.7),
            padding=dp(16),
            spacing=dp(12)
        )

        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(cols=1, spacing=dp(10),
                                 padding=dp(8),
                                 size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # stack name
        form_layout.add_widget(self.make_text_label(
            labels.add_stack_filename,
            size_hint_y=None,
            height=dp(24)
        ))
        self.stack_input = TextInput(size_hint_y=None, height=dp(40), multiline=False)
        form_layout.add_widget(self.stack_input)

        # own language
        form_layout.add_widget(self.make_text_label(
            labels.add_own_language,
            size_hint_y=None,
            height=dp(24)
        ))
        self.own_language_input = TextInput(size_hint_y=None, height=dp(40), multiline=False)
        form_layout.add_widget(self.own_language_input)

        # foreign language
        form_layout.add_widget(self.make_text_label(
            labels.add_foreign_language,
            size_hint_y=None,
            height=dp(24)
        ))
        self.foreign_language_input = TextInput(size_hint_y=None, height=dp(40), multiline=False)
        form_layout.add_widget(self.foreign_language_input)

        # 3 columns
        row = BoxLayout(orientation="horizontal",
                        size_hint_y=None,
                        height=dp(40),
                        spacing=dp(10))
        row.add_widget(self.make_text_label(
            labels.three_digit_toggle,
            size_hint_y=None,
            height=dp(30)
        ))
        self.three_columns = CheckBox(active=False, size_hint=(None, None), size=(dp(28), dp(28)))
        self.three_columns.bind(active=self.three_column_checkbox)
        row.add_widget(self.three_columns)
        form_layout.add_widget(row)

        # add stack button
        add_stack_button = self.make_primary_button(
            labels.add_stack_button_text,
            size_hint=(1, None),
            height=dp(48)
        )
        add_stack_button.bind(on_press=self.add_stack_button_func)
        form_layout.add_widget(add_stack_button)

        scroll.add_widget(form_layout)
        card.add_widget(scroll)
        center_center.add_widget(card)
        self.window.add_widget(center_center)

        # Fehlermeldung unten
        self.bottom_center = AnchorLayout(anchor_x="center", anchor_y="bottom",
                                          padding=30 * padding_mul)
        self.add_stack_error_label = self.make_title_label(
            "",
            size_hint=(None, None),
            size=(dp(400), dp(40))
        )
        self.bottom_center.add_widget(self.add_stack_error_label)
        self.window.add_widget(self.bottom_center)


    def on_setting_changed(self, key_path, cast_type):
        def callback(instance, value):
            # Wert passend casten
            if cast_type == int:
                value = int(value)
            elif cast_type == float:
                value = float(value)

            # Key-Pfad wie ["settings","gui","title_font_size"] durchlaufen
            ref = config
            for key in key_path[:-1]:
                ref = ref[key]
            ref[key_path[-1]] = value

            log(f"{key_path[-1]} updated to {value}")
            save.save_settings(config)
            log("config saved")

        return callback

    def add_stack_button_func(self, instance=None):
        # reading textbox_content
        log("starting save")
        stackname = self.stack_input.text.strip()
        own_language = self.own_language_input.text.strip()
        foreign_language = self.foreign_language_input.text.strip()
        latin_active = self.three_columns.active  # Checkbox auslesen
        log("reading textbox finished")

        if stackname and own_language and foreign_language:
            # Checking for .csv
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
                    latin_active=latin_active)
                log("Added language info and Latin column state")
                self.main_menu()
            else:
                log("Saving failed, file already exists.")
                self.add_stack_error_label.text = labels.add_stack_title_text_exists
        else:
            log("Saving failed, one or more input boxes empty.")
            self.add_stack_error_label.text = labels.add_stack_title_text_empty

    def learn(self, stack=None, mode="front_back", instance=None):
        log(f"entered learn menu with mode={mode}")
        self.learn_mode = mode

        self.window.clear_widgets()

        # ==== Rahmen-Container (bleibt stabil): ====
        # Hauptbereich für den Screen
        self.learn_area = FloatLayout()  # FloatLayout = bequemes Überlagern
        self.window.add_widget(self.learn_area)

        # Content-Bereich (dieser wird bei jedem Screen geleert/neu befüllt)
        self.learn_content = AnchorLayout(
            anchor_x="center", anchor_y="center",
            padding=30 * float(config["settings"]["gui"]["padding_multiplicator"])
        )
        self.learn_area.add_widget(self.learn_content)

        # Header (Überschrift oben zentriert)
        self.header_anchor = AnchorLayout(
            anchor_x="center", anchor_y="top",
            padding=30 * float(config["settings"]["gui"]["padding_multiplicator"])
        )
        self.header_label = Label(
            text="",
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(None, None), size=(80, 40)
        )
        self.header_anchor.add_widget(self.header_label)
        self.learn_area.add_widget(self.header_anchor)

        # Back-Button (rechts oben) – Icon-Button im neuen Stil
        top_right = AnchorLayout(
            anchor_x="right", anchor_y="top",
            padding=30 * float(config["settings"]["gui"]["padding_multiplicator"])
        )
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=self.main_menu,
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.learn_area.add_widget(top_right)


        # Lernliste aufbauen (ohne Duplikations-Bug)
        all_vocab = []
        self.all_vocab_list = []
        self.is_back = False
        self.current_vocab_index = 0

        if stack:
            file = save.load_vocab("vocab/" + stack)
            if isinstance(file, tuple):
                file = file[0]
            all_vocab.append(file)  # nur einmal hinzufügen
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

        # Mindest-Check auf leere Liste
        if self.max_current_vocab_index == 0:
            log("no vocab to learn")
            self.window.clear_widgets()
            msg_anchor = AnchorLayout(anchor_x="center", anchor_y="center")
            msg_anchor.add_widget(Label(
                text="Keine Vokabeln vorhanden. Bitte füge zuerst Vokabeln hinzu.",
                font_size=int(config["settings"]["gui"]["title_font_size"])
            ))
            self.window.add_widget(msg_anchor)
            return

        # Verfügbare Modi – Multiple Choice nur, wenn genug Items
        self.recompute_available_modes()

        self.show_current_card()


    def show_current_card(self):
        self.learn_content.clear_widgets()
        """Wählt die Anzeige je nach Lernmodus"""
        current_vocab = self.all_vocab_list[self.current_vocab_index]

        if self.learn_mode == "front_back":
            text = current_vocab["own_language"] if not self.is_back else self._format_backside(current_vocab)
            self.show_button_card(text, self.flip_card_learn_func)

        elif self.learn_mode == "back_front":
            text = current_vocab["foreign_language"] if not self.is_back else current_vocab["own_language"]
            self.show_button_card(text, self.flip_card_learn_func)

        elif self.learn_mode == "multiple_choice":
            self.multiple_choice()

        elif self.learn_mode == "letter_salad":
            self.letter_salad()

        else:
            log(f"Unknown learn mode {self.learn_mode}, fallback to front_back")
            self.learn(None, "front_back")

    def show_button_card(self, text, callback):
        # Header leeren
        if hasattr(self, "header_label"):
            self.header_label.text = ""

        center_center = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=30 * float(config["settings"]["gui"]["padding_multiplicator"]))

        self.front_side_label = RoundedButton(
            text=text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(0.7, 0.6)
        )
        self.front_side_label.bind(on_press=callback)
        center_center.add_widget(self.front_side_label)
        self.learn_content.add_widget(center_center)


    def _format_backside(self, vocab):
        back = vocab.get("foreign_language", "")
        additional = vocab.get("info", "")
        latin = vocab.get("latin_language")  # None oder ""
        return f"{back}\n\n{additional}\n\n{latin}" if latin else f"{back}\n\n{additional}"

    def flip_card_learn_func(self, instance=None):
        if self.is_back:
            # Nächste Karte
            if self.current_vocab_index >= self.max_current_vocab_index - 1:
                self.current_vocab_index = 0
                random.shuffle(self.all_vocab_list)
            else:   self.current_vocab_index += 1

            self.is_back = False

            # Set random mode
            self.learn_mode = random.choice(self.available_modes)

        else:
            self.is_back = True

        self.show_current_card()

    def multiple_choice(self):
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
                a.get("own_language", "") == correct_vocab.get("own_language", "") and
                a.get("foreign_language", "") == correct_vocab.get("foreign_language", "")
                for a in answers
        ):
            answers.append(correct_vocab)

        random.shuffle(answers)

        scroll = ScrollView(size_hint=(1, 1))
        form_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[
                50 * float(config["settings"]["gui"]["padding_multiplicator"]),
                80 * float(config["settings"]["gui"]["padding_multiplicator"]),
                120 * float(config["settings"]["gui"]["padding_multiplicator"]),
                50 * float(config["settings"]["gui"]["padding_multiplicator"])
            ],
            size_hint_y=None
        )
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Überschrift: abgefragtes Wort (own_language)
        if hasattr(self, "header_label"):
            self.header_label.text = correct_vocab.get('own_language', '')

        for opt in answers:
            btn = RoundedButton(
                text=str(opt.get('foreign_language', '')),
                bg_color=APP_COLORS["card"],
                color=APP_COLORS["text"],
                font_size=config["settings"]["gui"]["title_font_size"],
                size_hint=(1, None),
                height=dp(70)
            )
            btn.bind(on_press=lambda instance, choice=opt: self.multiple_choice_func(correct_vocab, choice, instance))
            form_layout.add_widget(btn)

        scroll.add_widget(form_layout)
        self.learn_content.add_widget(scroll)



    def multiple_choice_func(self, correct_vocab, button_text, instance=None):
        if (button_text is correct_vocab) or (
                button_text.get("own_language", "") == correct_vocab.get("own_language", "") and
                button_text.get("foreign_language", "") == correct_vocab.get("foreign_language", "")
        ):
            if self.current_vocab_index >= self.max_current_vocab_index - 1:
                self.current_vocab_index = 0
            else:
                self.current_vocab_index += 1
            self.is_back = False
            self.learn_mode = random.choice(self.available_modes)
            self.show_current_card()

    def add_vocab(self, stack, vocab, instance=None):
        log("entered add vocab")
        self.window.clear_widgets()

        # Back Button (modern)
        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * float(config["settings"]["gui"]["padding_multiplicator"]))
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


        center_center = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=80*float(config["settings"]["gui"]["padding_multiplicator"]))
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(cols=1, spacing=15,
                                 padding=30*float(config["settings"]["gui"]["padding_multiplicator"]), size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Own language
        form_layout.add_widget(Label(text=labels.add_own_language,
                                     font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text=""))
        self.add_own_language = TextInput(size_hint_y=None, height=60, multiline=False)
        form_layout.add_widget(self.add_own_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Foreign language
        form_layout.add_widget(Label(text=labels.add_foreign_language,
                                     font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text=""))
        self.add_foreign_language = TextInput(size_hint_y=None, height=60, multiline=False)
        form_layout.add_widget(self.add_foreign_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Latin language
        self.third_column_input = None
        if save.read_languages("vocab/"+stack)[3]:
            form_layout.add_widget(Label(text=labels.add_third_column,
                                         font_size=int(config["settings"]["gui"]["title_font_size"])))
            form_layout.add_widget(Label(text=""))
            self.third_column_input = TextInput(size_hint_y=None, height=60, multiline=False)
            form_layout.add_widget(self.third_column_input)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Additional Info
        form_layout.add_widget(Label(text=labels.add_additional_info,
                                     font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text=""))
        self.add_additional_info = TextInput(size_hint_y=None, height=60, multiline=False)
        form_layout.add_widget(self.add_additional_info)


        # Add Button (modern, rund)
        form_layout.add_widget(Label(text="\n\n\n\n"))
        self.add_vocab_button = self.make_primary_button(
            labels.add_vocabulary_button_text,
            size_hint=(1, None),
            height=dp(48)
        )
        self.add_vocab_button.bind(on_press=lambda instance: self.add_vocab_button_func(vocab, stack))
        form_layout.add_widget(self.add_vocab_button)


        if self.third_column_input:
            self.widgets_add_vocab = [self.add_own_language, self.add_foreign_language, self.third_column_input,
                                      self.add_additional_info, self.add_vocab_button]
        else:
            self.widgets_add_vocab = [self.add_own_language, self.add_foreign_language, self.add_additional_info,
                                      self.add_vocab_button]

        Window.bind(on_key_down=self.on_key_down)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


    def add_vocab_button_func(self, vocab, stack, instance=None):
        add_vocab_own_lanauage = self.add_own_language.text
        add_vocab_foreign_language = self.add_foreign_language.text
        if self.third_column_input:  add_vocab_third_column = self.third_column_input.text
        else: add_vocab_third_column=None
        add_vocab_additional_info = self.add_additional_info.text
        log("Adding Vocab. Loaded textbox content")
        if self.third_column_input:
            vocab.append({'own_language' : add_vocab_own_lanauage,
                          'foreign_language' : add_vocab_foreign_language,
                          'latin_language' : add_vocab_third_column,
                          'info' : add_vocab_additional_info})
        else:
            vocab.append({
                'own_language': add_vocab_own_lanauage,
                'foreign_language': add_vocab_foreign_language,
                'latin_language': "",  # <-- neu: leerer Key für Robustheit
                'info': add_vocab_additional_info
            })

        save.save_to_vocab(vocab, "vocab/"+stack)
        log("added to stack")
        self.clear_inputs()

    def edit_metadata(self, stack, instance=None):
        log("entered edit metadata menu")
        self.window.clear_widgets()
        metadata = save.read_languages("vocab/"+stack)


        center_center = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=80*float(config["settings"]["gui"]["padding_multiplicator"]))
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(cols=1, spacing=15,
                                 padding=30*float(config["settings"]["gui"]["padding_multiplicator"]), size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Back Button (modern)
        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * float(config["settings"]["gui"]["padding_multiplicator"]))
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


        form_layout.add_widget(Label(text=labels.add_own_language,
                                     font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_own_language_textbox = TextInput(size_hint_y=None,
                                                   height=60, multiline=False, text=metadata[0])
        form_layout.add_widget(self.edit_own_language_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))

        form_layout.add_widget(Label(text=labels.add_foreign_language,
                                     font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_foreign_language_textbox = TextInput(size_hint_y=None,
                                                       height=60, multiline=False, text=metadata[1])
        form_layout.add_widget(self.edit_foreign_language_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))

        form_layout.add_widget(Label(text=labels.add_stack_filename,
                                     font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text="\n\n\n\n\n\n"))
        self.edit_name_textbox = TextInput(size_hint_y=None,
                                           height=60, multiline=False, text=stack[:-4])
        form_layout.add_widget(self.edit_name_textbox)
        form_layout.add_widget(Label(text="\n\n\n\n\n\n\n\n\n"))


        form_layout.add_widget(Label(text="\n\n\n\n"))
        add_vocab_button = Button(text=labels.save, size_hint_y=None)
        add_vocab_button.bind(on_press = lambda instance: self.edit_metadata_func(stack))
        form_layout.add_widget(add_vocab_button)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


    def edit_vocab(self, stack, vocab, instance=None):
        log("entered edit vocab menu")
        self.window.clear_widgets()
        center_center = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=80*float(config["settings"]["gui"]["padding_multiplicator"]))
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(cols=1, spacing=15,
                                 padding=30*float(config["settings"]["gui"]["padding_multiplicator"]),
                                 size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Back Button (modern)
        top_right = AnchorLayout(anchor_x="right", anchor_y="top",
                                 padding=30 * float(config["settings"]["gui"]["padding_multiplicator"]))
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56)
        )
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


        matrix = self.build_vocab_grid(form_layout, vocab, save.read_languages("vocab/"+stack)[3])


        # Save all button (modern, rund)
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=[30, 30, 100, 30])
        save_all_button = self.make_primary_button(
            labels.save,
            size_hint=(None, None),
            size=(dp(160), dp(48))
        )
        save_all_button.bind(on_press=lambda instance: self.edit_vocab_func(matrix, stack))
        top_center.add_widget(save_all_button)
        self.window.add_widget(top_center)



        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


    def learn_vocab_stack(self, stack, instance=None):
        log("entered learn vocab menu")
        self.window.clear_widgets()
        self.all_vocab_list=[]
        self.current_vocab_index = 0
        self.is_back = False

        stack_vocab = save.load_vocab("vocab/"+stack)
        if type(stack_vocab) == tuple:  stack_vocab = stack_vocab[0]
        for i in stack_vocab:   self.all_vocab_list.append(i)
        random.shuffle(self.all_vocab_list)
        self.max_current_vocab_index = len(self.all_vocab_list)


        # Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = self.make_icon_button(
            "assets/back_button.png",
            on_press=lambda instance: self.select_stack(stack),
            size=dp(56))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        self.max_current_vocab_index = len(self.all_vocab_list)

        # Erste Vokabel anzeigen (Vorderseite)
        current_vocab = self.all_vocab_list[self.current_vocab_index]
        front_text = current_vocab["own_language"]

        center_center = AnchorLayout(anchor_x="center", anchor_y="center",
                                     padding=30 * float(config["settings"]["gui"]["padding_multiplicator"]))
        self.front_side_label = RoundedButton(
            text=front_text,
            bg_color=APP_COLORS["card"],
            color=APP_COLORS["text"],
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(0.6, 0.8)
        )

        self.front_side_label.bind(on_press=self.flip_card_learn_func)
        center_center.add_widget(self.front_side_label)
        self.window.add_widget(center_center)


    def edit_vocab_func(self, matrix, stack, instance=None):
        vocab = self.read_vocab_from_grid(matrix, save.read_languages("vocab/"+stack)[3])
        save.save_to_vocab(vocab, "vocab/"+stack)
        log("saved vocab")
        self.select_stack(stack)

    def edit_metadata_func(self, stack, instance=None):
        save.change_languages("vocab/"+stack, self.edit_own_language_textbox.text,
                              self.edit_foreign_language_textbox.text, "Latein",
                              save.read_languages("vocab/"+stack)[3])
        os.rename("vocab/"+stack, "vocab/"+str(self.edit_name_textbox.text)+".csv")
        stack = self.edit_name_textbox.text+".csv"
        self.select_stack(stack)

    def clear_inputs(self):
        self.add_own_language.text = ""
        self.add_foreign_language.text = ""
        if self.third_column_input:
            self.third_column_input.text = ""
        self.add_additional_info.text = ""
        self.add_own_language.focus = True

    def delete_stack(self, stack, instance=None):
        os.remove("vocab/"+stack)
        log("deleted stack: "+stack)
        self.main_menu()

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        # Prüfe, ob ein TextInput fokussiert ist
        focused_index = None
        for i, widget in enumerate(self.widgets_add_vocab):
            if hasattr(widget, 'focus') and widget.focus:
                focused_index = i
                break

        # Wenn nichts fokussiert ist, fokus auf das erste TextInput
        if focused_index is None:
            for widget in self.widgets_add_vocab:
                if hasattr(widget, 'focus'):
                    widget.focus = True
                    return True

        # Tab / Shift+Tab Handling
        if key == 9:  # Tab
            if focused_index is not None:
                if 'shift' in modifiers:  # Shift+Tab rückwärts
                    next_index = (focused_index - 1) % len(self.widgets_add_vocab)
                else:
                    next_index = (focused_index + 1) % len(self.widgets_add_vocab)
                self.widgets_add_vocab[next_index].focus = True
            return True

        # Enter drücken
        if key == 13:  # Enter
            if focused_index is not None:
                current = self.widgets_add_vocab[focused_index]
                if isinstance(current, TextInput):
                    self.widgets_add_vocab[-1].trigger_action(duration=0.1)
            return True

        return False

    def read_vocab_from_grid(self, textinput_matrix, latin_active):
        vocab_list = []

        for row in textinput_matrix:
            # Werte holen
            if latin_active:
                own, foreign, latin, info = [ti.text.strip() for ti in row]
            else:
                own, foreign, info = [ti.text.strip() for ti in row]
                latin = ""

            # ✅ Leere Zeilen automatisch überspringen
            if not own and not foreign and not latin and not info:
                continue

            vocab_list.append({
                "own_language": own,
                "foreign_language": foreign,
                "latin_language": latin,
                "info": info
            })

        return vocab_list


    def build_vocab_grid(self, parent_layout, vocab_list, latin_active):
        """
        parent_layout = z.B. ein BoxLayout oder Screen, in den das Grid eingefügt wird
        latin_active = None -> KEINE latin-Spalte
        latin_active = "Latein" (oder egal was) -> Spalte anzeigen
        """

        # Spaltenanzahl bestimmen
        cols = 4 if latin_active else 3

        grid = GridLayout(cols=cols, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))  # wichtig für ScrollView

        textinput_matrix = []

        for vocab in vocab_list:
            row = []

            # Basis-Spalten
            for key in ["own_language", "foreign_language"]:
                ti = TextInput(text=vocab.get(key, ""), multiline=False,
                               size_hint_y=None, height=60)
                grid.add_widget(ti)
                row.append(ti)

            # Latein nur, wenn aktiv
            if latin_active:
                ti = TextInput(text=vocab.get("latin_language", ""), multiline=False,
                               size_hint_y=None, height=60)
                grid.add_widget(ti)
                row.append(ti)

            # Info-Feld immer zuletzt
            ti = TextInput(text=vocab.get("info", ""), multiline=False,
                           size_hint_y=None, height=60)
            grid.add_widget(ti)
            row.append(ti)

            textinput_matrix.append(row)

        parent_layout.add_widget(grid)
        return textinput_matrix

    def bind_keyboard(self, dt):
        Window.bind(on_key_down=self.on_key_down)


    def three_column_checkbox(self, instance=None, value=None):
        if value:
            three_columns_check=True
        else:
            three_columns_check=False

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        return False

    def recompute_available_modes(self):
        """ baut self.available_modes anhand der config + Anzahl Vokabeln """
        global config

        # Sicherstellen, dass die Struktur existiert
        if get_in(config, ["settings", "modes"]) is None:
            set_in(config, ["settings", "modes"], {
                "front_back": True,
                "back_front": True,
                "multiple_choice": True,
                "letter_salad": True,
            })
            save.save_settings(config)

        modes_cfg = get_in(config, ["settings", "modes"], {}) or {}

        # Falls all_vocab_list noch nicht existiert, leere Liste annehmen
        vocab_len = len(getattr(self, "all_vocab_list", []))

        self.available_modes = []
        if bool_cast(modes_cfg.get("front_back", True)):
            self.available_modes.append("front_back")
        if bool_cast(modes_cfg.get("back_front", True)):
            self.available_modes.append("back_front")
        if bool_cast(modes_cfg.get("multiple_choice", True)) and vocab_len >= 5:
            self.available_modes.append("multiple_choice")
        if bool_cast(modes_cfg.get("letter_salad", True)):
            self.available_modes.append("letter_salad")


    def on_mode_checkbox_changed(self, path):
        """ Factory: gibt einen Handler zurück, der config schreibt + neu berechnet """

        def _handler(instance, value):
            global config
            set_in(config, path, bool(value))
            save.save_settings(config)
            self.recompute_available_modes()

        return _handler


# NICHT IN KLASSE
def get_in(dct, path, default=None):
    cur = dct
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def set_in(dct, path, value):
    cur = dct
    for k in path[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[path[-1]] = value

def bool_cast(v):
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return bool(v)
    if isinstance(v, str): return v.strip().lower() in ("1","true","yes","y","on")
    return bool(v)


if __name__ == "__main__":
    VokabaApp().run()