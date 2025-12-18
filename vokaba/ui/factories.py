import os
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout

from vokaba.ui.widgets.rounded import RoundedButton
from vokaba.theme.theme_manager import get_icon_path


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
        lbl = Label(
            text=text,
            color=self.colors["text"],
            font_size=int(self.cfg_int(["settings", "gui", "title_font_size"], 32)),
            **kwargs,
        )
        lbl.halign = kwargs.get("halign", "center")
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_text_label(self, text, **kwargs):
        lbl = Label(
            text=text,
            color=self.colors["muted"],
            font_size=int(self.cfg_int(["settings", "gui", "text_font_size"], 18)),
            **kwargs,
        )
        lbl.halign = kwargs.get("halign", "left")
        lbl.valign = "middle"
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lbl

    def make_primary_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", int(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return RoundedButton(
            text=text,
            bg_color=self.colors["primary"],
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_secondary_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", int(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return RoundedButton(
            text=text,
            bg_color=self.colors["card"],
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_danger_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", int(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
        return RoundedButton(
            text=text,
            bg_color=self.colors["danger"],
            color=self.colors["text"],
            font_size=font_size,
            **kwargs,
        )

    def make_list_button(self, text, **kwargs):
        font_size = kwargs.pop("font_size", int(self.cfg_int(["settings", "gui", "text_font_size"], 18)))
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
        ti.padding = [dp(8), dp(8), dp(8), dp(8)]
        ti.font_size = int(self.cfg_int(["settings", "gui", "text_font_size"], 18))

        def _on_focus(instance, value):
            if value:
                self.current_focus_input = instance
        ti.bind(focus=_on_focus)
        return ti

    def get_textinput_height(self) -> float:
        base = int(self.cfg_int(["settings", "gui", "text_font_size"], 18))
        return dp(base * 2.0)

    def create_accent_bar(self):
        accents = ["é","è","ê","ë","à","â","î","ï","ô","ù","û","ç","œ","æ"]
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
