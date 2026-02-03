from __future__ import annotations

from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


class LockScrollTextInput(TextInput):
    """TextInput that blocks parent ScrollView scrolling while this input is focused.

    Why this works better than 'touch.grab' alone:
    - Some stylus/handwriting interactions trigger new touches/moves where ScrollView still
      decides to scroll.
    - If we disable ScrollView's do_scroll_* while ANY TextInput in it is focused, the
      ScrollView cannot start scrolling at all.

    Behavior:
    - When focused: find nearest parent ScrollView and set do_scroll_x/y = False.
      Uses a small ref-count on the ScrollView so multiple inputs can coexist.
    - When focus leaves and no other inputs are focused: restore previous do_scroll_x/y.
    - Additionally grabs touches that start inside the TextInput to keep gestures stable.
    """

    _ud_key = "__vokaba_lock_scroll_ti__"
    _vokaba_sv = None

    def _find_parent_scrollview(self):
        p = self.parent
        while p is not None:
            if isinstance(p, ScrollView):
                return p
            p = p.parent
        return None

    def on_focus(self, _instance, value: bool):
        # focus gained: lock nearest ScrollView
        if value:
            sv = self._find_parent_scrollview()
            if sv is not None:
                cnt = int(getattr(sv, "_vokaba_focus_lock_cnt", 0) or 0)
                if cnt == 0:
                    sv._vokaba_prev_do_scroll = (bool(sv.do_scroll_x), bool(sv.do_scroll_y))
                sv._vokaba_focus_lock_cnt = cnt + 1
                sv.do_scroll_x = False
                sv.do_scroll_y = False
                self._vokaba_sv = sv
            return

        # focus lost: unlock if we were the locker
        sv = getattr(self, "_vokaba_sv", None)
        if sv is None:
            return

        cnt = int(getattr(sv, "_vokaba_focus_lock_cnt", 1) or 1) - 1
        if cnt < 0:
            cnt = 0
        sv._vokaba_focus_lock_cnt = cnt

        if cnt == 0:
            prev = getattr(sv, "_vokaba_prev_do_scroll", (True, True))
            sv.do_scroll_x, sv.do_scroll_y = prev

        self._vokaba_sv = None

    def on_touch_down(self, touch):
        # ignore mouse wheel scroll events
        if getattr(touch, "is_mouse_scrolling", False):
            return super().on_touch_down(touch)

        if self.disabled:
            return super().on_touch_down(touch)

        if self.collide_point(*touch.pos):
            # Let TextInput do normal focus/cursor logic first
            super().on_touch_down(touch)

            # Consume & grab: prevents ScrollView from treating this touch as scroll start
            if self.focus:
                touch.grab(self)
                touch.ud[self._ud_key] = True
            return True

        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and touch.ud.get(self._ud_key):
            super().on_touch_move(touch)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self and touch.ud.get(self._ud_key):
            touch.ungrab(self)
            super().on_touch_up(touch)
            return True
        return super().on_touch_up(touch)