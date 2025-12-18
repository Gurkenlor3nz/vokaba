from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle

class RoundedCard(BoxLayout):
    """Card-like container with rounded corners and solid background."""
    def __init__(self, bg_color=(0.16, 0.17, 0.23, 1), radius=None, **kwargs):
        self._bg_color_value = bg_color
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
    """Button with rounded corners and custom background color."""
    def __init__(self, bg_color=(0.26, 0.60, 0.96, 1), radius=None, **kwargs):
        self._bg_color_value = bg_color
        self._radius = radius or dp(18)
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        self.canvas.before.clear()
        with self.canvas.before:
            self._bg_color_instr = Color(*self._bg_color_value)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius] * 4)

        self.bind(pos=self._update_bg, size=self._update_bg)

    def set_bg_color(self, rgba):
        self._bg_color_value = rgba
        if hasattr(self, "_bg_color_instr"):
            self._bg_color_instr.rgba = rgba

    def _update_bg(self, *args):
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size
