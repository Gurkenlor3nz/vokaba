from kivy.uix.slider import Slider

class NoScrollSlider(Slider):
    """
    Slider that grabs touch so dragging won't scroll parent ScrollView.
    """
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
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
