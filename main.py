# ----------------------------- Standard Library -----------------------------
from datetime import datetime
import os
import random
from typing import Any, Dict, List, Optional, Sequence

# ------------------------------- Kivy Config --------------------------------
from kivy.config import Config
Config.set("kivy", "window_icon", "assets/vokaba_icon.png")

# --------------------------------- Kivy Core --------------------------------
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp

# --------------------------------- Kivy UI ----------------------------------
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

# ------------------------------ Kivy GFX/Props ------------------------------
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.properties import ListProperty, NumericProperty

# --------------------------------- Project ----------------------------------
import labels
import save


# =============================== Utilities ===================================

def log(text: str) -> None:
    now = str(datetime.now())[11:]
    print(f"[{now}] {text}")


def get_in(dct: Dict[str, Any], path: Sequence[str], default: Any = None) -> Any:
    cur = dct
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def set_in(dct: Dict[str, Any], path: Sequence[str], value: Any) -> None:
    cur = dct
    for k in path[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[path[-1]] = value


def bool_cast(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(v)


# ============================ Custom UI Widgets ==============================

class NoScrollSlider(Slider):
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


class RoundButton(Button):
    """Flat very-rounded button drawn via canvas (no white boxes)."""
    bg_color = ListProperty([0.22, 0.47, 0.98, 1])  # primary
    fg_color = ListProperty([1, 1, 1, 1])           # on_primary
    radius = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.radius = dp(26)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.border = (0, 0, 0, 0)
        self.color = self.fg_color
        with self.canvas.before:
            Color(rgba=self.bg_color)
            self._rr = RoundedRectangle(
                pos=self.pos, size=self.size,
                radius=[(self.radius, self.radius)] * 4
            )
        self.bind(pos=self._relayout, size=self._relayout,
                  bg_color=self._repaint, radius=self._repaint, fg_color=self._update_fg)

    def _relayout(self, *_):
        self._rr.pos = self.pos
        self._rr.size = self.size

    def _repaint(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(rgba=self.bg_color)
            self._rr = RoundedRectangle(
                pos=self.pos, size=self.size,
                radius=[(self.radius, self.radius)] * 4
            )

    def _update_fg(self, *_):
        self.color = self.fg_color


class RoundedTextInput(TextInput):
    """TextInput with very-rounded dark surface background."""
    # leicht heller als 'surface', damit sich die Felder abheben
    bg_color = ListProperty([0.22, 0.24, 0.30, 1])
    radius = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.radius = dp(24)
        self.background_normal = ""
        self.background_active = ""
        self.background_color = (0, 0, 0, 0)
        self.cursor_color = (1, 1, 1, 0.9)
        self.foreground_color = (1, 1, 1, 1)
        self.hint_text_color = (1, 1, 1, 0.4)
        self.padding = [dp(14), dp(12), dp(14), dp(12)]
        self.readonly = False
        self.disabled = False

        with self.canvas.before:
            Color(rgba=self.bg_color)
            self._rr = RoundedRectangle(
                pos=self.pos, size=self.size,
                radius=[(self.radius, self.radius)] * 4
            )
        self.bind(
            pos=self._relayout,
            size=self._relayout,
            bg_color=self._repaint,
            radius=self._repaint,
        )

    def _relayout(self, *_):
        self._rr.pos = self.pos
        self._rr.size = self.size

    def _repaint(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(rgba=self.bg_color)
            self._rr = RoundedRectangle(
                pos=self.pos, size=self.size,
                radius=[(self.radius, self.radius)] * 4
            )



# ================================ Main App ===================================

class VokabaApp(App):
    """Vocabulary trainer: menus, stack management, and learning modes."""

    def build(self):
        self.config: Dict[str, Any] = save.load_settings()
        self.theme = {
            "bg": (0.08, 0.09, 0.10, 1),
            "surface": (0.16, 0.18, 0.22, 1),
            "primary": (0.22, 0.47, 0.98, 1),
            "on_bg": (1, 1, 1, 1),
            "on_surface": (1, 1, 1, 1),
            "on_primary": (1, 1, 1, 1),
        }
        Window.clearcolor = self.theme["bg"]

        self.vocab_dir = getattr(labels, "vocab_path", "vocab")
        os.makedirs(self.vocab_dir, exist_ok=True)

        self.available_modes: List[str] = []
        self.all_vocab_list: List[Dict[str, str]] = []
        self.widgets_add_vocab: List[Any] = []
        self.learn_mode: str = "front_back"
        self.is_back: bool = False
        self.current_vocab_index: int = 0
        self.max_current_vocab_index: int = 0

        self.root_layout = FloatLayout()
        with self.root_layout.canvas.before:
            Color(rgba=self.theme["bg"])
            self._root_bg = Rectangle(pos=self.root_layout.pos, size=self.root_layout.size)
        self.root_layout.bind(pos=self._update_root_bg, size=self._update_root_bg)

        self.main_menu()
        return self.root_layout

    def _update_root_bg(self, *_):
        self._root_bg.pos = self.root_layout.pos
        self._root_bg.size = self.root_layout.size

    # ------------------------------ UI Helpers -------------------------------
    def _header_spacer_height(self) -> int:
        pad = 60 * float(self.config["settings"]["gui"]["padding_multiplicator"])
        return int(self.config["settings"]["gui"]["title_font_size"] + pad)

    def _fit_label(self, lbl: Label) -> None:
        lbl.size_hint_y = None
        lbl.halign = "center"
        lbl.valign = "middle"
        def _update_text_size(_inst, _w):
            lbl.text_size = (lbl.width, None)
        lbl.bind(width=_update_text_size)
        _update_text_size(lbl, lbl.width)
        def _update_height(_inst, ts):
            lbl.height = ts[1] + dp(6)
        lbl.bind(texture_size=_update_height)

    def _apply_rounded_panel(self, widget, color_key="surface", radius_dp=20):
        with widget.canvas.before:
            Color(rgba=self.theme[color_key])
            widget._panel_rr = RoundedRectangle(
                pos=widget.pos, size=widget.size,
                radius=[(dp(radius_dp), dp(radius_dp))] * 4
            )
        def _upd(*_):
            widget._panel_rr.pos = widget.pos
            widget._panel_rr.size = widget.size
        widget.bind(pos=_upd, size=_upd)

    # Small helper: create an image button placed directly on the root (no full-screen overlay)
    def _icon_button(self, img_path: str, size=(64, 64), on_press=None,
                     pos_hint=None) -> Button:
        # Padding abhängig vom GUI-Padding-Multiplikator
        pad_mul = float(self.config["settings"]["gui"]["padding_multiplicator"])
        pad = dp(8 * pad_mul)

        # eigentlicher Button
        btn = Button(
            size_hint=(None, None),
            size=size,
            background_normal=img_path,
            background_down=img_path,
            background_color=(1, 1, 1, 1),
            border=(0, 0, 0, 0),
        )
        if on_press:
            btn.bind(on_press=on_press)

        # KLEINER Container nur um den Button herum
        w, h = size
        anchor = AnchorLayout(
            size_hint=(None, None),
            size=(w + 2 * pad, h + 2 * pad),
            anchor_x="center",
            anchor_y="center",
            pos_hint=pos_hint or {},
            padding=[pad, pad, pad, pad],
        )

        anchor.add_widget(btn)
        self.root_layout.add_widget(anchor)
        return btn

    def _add_header(self, text: str) -> BoxLayout:
        header_height = self._header_spacer_height()
        bar = BoxLayout(orientation="vertical",
                        size_hint=(1, None), height=header_height,
                        pos_hint={"top": 1}, padding=[0, dp(10), 0, 0])
        lbl = Label(text=text,
                    font_size=int(self.config["settings"]["gui"]["title_font_size"]),
                    color=self.theme["on_bg"],
                    size_hint=(1, None))
        self._fit_label(lbl)
        bar.add_widget(lbl)
        self.root_layout.add_widget(bar)
        return bar

    def _keep_scroll_at_top(self, scroll: ScrollView) -> None:
        if getattr(scroll, "_top_fix_pending", False):
            return
        scroll._top_fix_pending = True
        def _set_top(_dt):
            scroll.scroll_y = 1
            scroll._top_fix_pending = False
        Clock.schedule_once(_set_top, 0)

    def _unbind_keyboard_if_bound(self) -> None:
        try:
            Window.unbind(on_key_down=self.on_key_down)
        except Exception:
            pass

    # -------------------------------- Screens --------------------------------
    def main_menu(self, _instance=None) -> None:
        log("open main menu")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        # Content center
        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=60 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        file_list = GridLayout(cols=1, spacing=8, size_hint_y=None)
        file_list.bind(minimum_height=file_list.setter("height"))
        for fname in os.listdir(self.vocab_dir):
            fpath = os.path.join(self.vocab_dir, fname)
            if os.path.isfile(fpath):
                btn = RoundButton(text=fname[:-4], size_hint_y=None, height=50,
                                  bg_color=self.theme["surface"], fg_color=self.theme["on_surface"])
                btn.bind(on_release=lambda _b, name=fname: self.select_stack(name))
                file_list.add_widget(btn)

        scroll = ScrollView(size_hint=(0.7, 0.89), do_scroll_x=False, do_scroll_y=True)
        scroll.add_widget(file_list)
        center.add_widget(scroll)
        self.root_layout.add_widget(center)
        self._keep_scroll_at_top(scroll)

        # Fixed bits (placed directly, no full-screen overlays)
        self._add_header(getattr(labels, "welcome_text", "Welcome to Vokaba"))
        # top-left logo
        self._icon_button("assets/vokaba_logo.png", size=(128, 128),
                          on_press=self.settings, pos_hint={"x": 0, "top": 1})
        # top-right settings
        self._icon_button("assets/settings_icon.png", size=(64, 64),
                          on_press=self.settings, pos_hint={"right": 1, "top": 1})
        # bottom-right add
        self._icon_button("assets/add_stack.png", size=(64, 64),
                          on_press=self.add_stack, pos_hint={"right": 1, "y": 0})
        # bottom-center learn
        learn_btn = RoundButton(text=getattr(labels, "learn", "Learn"),
                                size_hint=(None, None), size=(200, 80),
                                bg_color=self.theme["primary"], fg_color=self.theme["on_primary"])
        learn_btn.bind(on_press=lambda _i: self.learn(stack=None,
                                                      mode=random.choice(self.available_modes)))
        learn_btn.pos_hint = {"center_x": 0.5, "y": 0}
        self.root_layout.add_widget(learn_btn)

        self.recompute_available_modes()

    def settings(self, _instance=None) -> None:
        log("open settings")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        # Scrollable panel
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        pad_mul = float(self.config["settings"]["gui"]["padding_multiplicator"])
        panel_pad = [dp(24*pad_mul)] * 4
        content = BoxLayout(orientation="vertical", size_hint_y=None,
                            spacing=dp(16), padding=panel_pad)
        content.bind(minimum_height=content.setter("height"))
        self._apply_rounded_panel(content, color_key="surface", radius_dp=20)

        content.add_widget(Label(size_hint_y=None, height=dp(20), text=""))

        slider_defs = [
            {
                "label": getattr(labels, "settings_title_font_size_slider_test_label", "Title font size"),
                "min": 10, "max": 80,
                "value": float(self.config["settings"]["gui"]["title_font_size"]),
                "path": ["settings", "gui", "title_font_size"],
                "cast": int,
            },
            {
                "label": getattr(labels, "settings_font_size_slider", "Text font size"),
                "min": 10, "max": 30,
                "value": float(self.config["settings"]["gui"]["text_font_size"]),
                "path": ["settings", "gui", "text_font_size"],
                "cast": int,
            },
            {
                "label": getattr(labels, "settings_padding_multiplikator_slider", "Padding multiplier"),
                "min": 0.1, "max": 3.0,
                "value": float(self.config["settings"]["gui"]["padding_multiplicator"]),
                "path": ["settings", "gui", "padding_multiplicator"],
                "cast": float,
            },
        ]
        for sd in slider_defs:
            lbl = Label(text=sd["label"],
                        font_size=self.config["settings"]["gui"]["title_font_size"],
                        size_hint_y=None, height=dp(80), color=self.theme["on_surface"])
            self._fit_label(lbl)
            sld = NoScrollSlider(min=sd["min"], max=sd["max"], value=sd["value"],
                                 size_hint_y=None, height=dp(40))
            sld.bind(value=self._on_setting_changed(sd["path"], sd["cast"]))
            content.add_widget(lbl)
            content.add_widget(sld)

        modes_header_text = getattr(labels, "settings_modes_header", "Learning modes")
        modes_hdr = Label(text=modes_header_text,
                          font_size=self.config["settings"]["gui"]["title_font_size"],
                          size_hint_y=None, height=dp(80), color=self.theme["on_surface"])
        self._fit_label(modes_hdr)
        content.add_widget(modes_hdr)

        grid = GridLayout(cols=2, size_hint_y=None, row_default_height=dp(50),
                          row_force_default=True, spacing=dp(8))
        grid.bind(minimum_height=grid.setter("height"))

        def add_mode_row(mode_key: str, mode_label: str) -> None:
            current = bool_cast(get_in(self.config, ["settings", "modes", mode_key], True))
            lbl = Label(text=mode_label,
                        font_size=self.config["settings"]["gui"]["text_font_size"],
                        size_hint_y=None, height=dp(50), halign="left", valign="middle",
                        color=self.theme["on_surface"])
            lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
            cb = CheckBox(active=current, size_hint=(None, None), size=(dp(32), dp(32)))
            cb.bind(active=self._on_mode_checkbox_changed(["settings", "modes", mode_key]))
            grid.add_widget(lbl)
            grid.add_widget(cb)

        add_mode_row("front_back", getattr(labels, "learn_flashcards_front_to_back", "Front → Back"))
        add_mode_row("back_front", getattr(labels, "learn_flashcards_back_to_front", "Back → Front"))

        vocab_len = len(getattr(self, "all_vocab_list", []))
        lbl_text = getattr(labels, "learn_flashcards_multiple_choice", "Multiple choice")
        lbl_mc = Label(text=lbl_text,
                       font_size=self.config["settings"]["gui"]["text_font_size"],
                       size_hint_y=None, height=dp(50), halign="left", valign="middle",
                       color=self.theme["on_surface"])
        lbl_mc.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        cb_mc = CheckBox(
            active=bool_cast(get_in(self.config, ["settings", "modes", "multiple_choice"], True)),
            size_hint=(None, None), size=(dp(32), dp(32))
        )
        if vocab_len < 5:
            cb_mc.disabled = True
            lbl_mc.text += "  [size=12][i](needs at least 5 items)[/i][/size]"
            lbl_mc.markup = True
        else:
            cb_mc.bind(active=self._on_mode_checkbox_changed(["settings", "modes", "multiple_choice"]))

        grid.add_widget(lbl_mc)
        grid.add_widget(cb_mc)
        content.add_widget(grid)

        scroll.add_widget(content)
        self.root_layout.add_widget(scroll)
        self._keep_scroll_at_top(scroll)

        # Fixed bits
        self._add_header(getattr(labels, "settings_title", "Settings"))
        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=self.main_menu, pos_hint={"right": 1, "top": 1})

    def select_stack(self, stack: str, _instance=None) -> None:
        log(f"open stack: {stack}")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=[30, 60, 100, 30])
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        grid = GridLayout(cols=2, spacing=dp(20), size_hint_y=None,
                          padding=[dp(20)]*4)
        grid.bind(minimum_height=grid.setter("height"))
        self._apply_rounded_panel(grid, color_key="surface", radius_dp=20)

        vocab_file = os.path.join(self.vocab_dir, stack)
        vocab_list = save.load_vocab(vocab_file)
        if isinstance(vocab_list, tuple):
            vocab_list = vocab_list[0]

        def add_btn(txt, cb, color_key="surface"):
            b = RoundButton(text=txt, size_hint_y=None, height=dp(72),
                            bg_color=self.theme[color_key],
                            fg_color=self.theme["on_surface"] if color_key=="surface" else self.theme["on_primary"])
            b.bind(on_press=cb)
            grid.add_widget(b)

        add_btn(getattr(labels, "delete_stack_button", "Delete stack"),
                lambda _i: self.delete_stack_confirmation(stack))
        add_btn(getattr(labels, "edit_metadata_button_text", "Edit metadata"),
                lambda _i: self.edit_metadata(stack))
        add_btn(getattr(labels, "add_vocab_button_text", "Add vocabulary"),
                lambda _i: self.add_vocab(stack, vocab_list))
        add_btn(getattr(labels, "edit_vocab_button_text", "Edit vocabulary"),
                lambda _i: self.edit_vocab(stack, vocab_list))
        self.recompute_available_modes()
        add_btn(getattr(labels, "learn_stack_vocab_button_text", "Learn"),
                lambda _i: self.learn(stack, mode=random.choice(self.available_modes)),
                color_key="primary")

        scroll.add_widget(grid)
        center.add_widget(scroll)
        self.root_layout.add_widget(center)
        self._keep_scroll_at_top(scroll)

        self._add_header(stack[:-4])
        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=self.main_menu, pos_hint={"right": 1, "top": 1})

    def delete_stack_confirmation(self, stack: str, _instance=None) -> None:
        log("open delete confirmation")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        # info panel
        top_center = AnchorLayout(anchor_x="center", anchor_y="top")
        vbox = BoxLayout(orientation="vertical", padding=dp(24),
                         size_hint=(0.9, None))
        vbox.bind(minimum_height=vbox.setter("height"))
        self._apply_rounded_panel(vbox, color_key="surface", radius_dp=20)
        for txt_attr in ("caution", "delete_stack_confirmation_text", "cant_be_undone"):
            txt = getattr(labels, txt_attr, "")
            if not txt:
                continue
            lbl = Label(text=txt, markup=True,
                        font_size=int(self.config["settings"]["gui"]["title_font_size"]),
                        color=self.theme["on_surface"])
            self._fit_label(lbl)
            vbox.add_widget(lbl)
        top_center.add_widget(vbox)
        self.root_layout.add_widget(top_center)

        # actions
        cancel_btn = RoundButton(text=getattr(labels, "cancel", "Cancel"),
                                 size_hint=(None, None), size=(200, 70),
                                 bg_color=self.theme["primary"], fg_color=self.theme["on_primary"])
        cancel_btn.pos_hint = {"center_x": 0.5, "top": 0.9}
        cancel_btn.bind(on_press=lambda _i: self.select_stack(stack))
        self.root_layout.add_widget(cancel_btn)

        del_btn = RoundButton(text=getattr(labels, "delete", "Delete"),
                              size_hint=(None, None), size=(150, 70),
                              bg_color=[0.85, 0.2, 0.2, 1], fg_color=[1, 1, 1, 1])
        del_btn.pos_hint = {"x": 0, "top": 1}
        del_btn.bind(on_press=lambda _i: self.delete_stack(stack))
        self.root_layout.add_widget(del_btn)

        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=lambda _i: self.select_stack(stack),
                          pos_hint={"right": 1, "top": 1})

    def add_stack(self, _instance=None) -> None:
        log("open add stack")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=80 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        form = GridLayout(cols=1, spacing=dp(16), padding=dp(24), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        self._apply_rounded_panel(form, color_key="surface", radius_dp=20)
        form.add_widget(Label(size_hint_y=None, height=dp(20), text=""))

        def add_label(txt):
            form.add_widget(Label(text=txt, size_hint_y=None, height=dp(30),
                                  font_size=self.config["settings"]["gui"]["text_font_size"],
                                  color=self.theme["on_surface"]))

        add_label(getattr(labels, "add_stack_filename", "File name"))
        self.stack_name_input = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False)
        form.add_widget(self.stack_name_input)

        add_label(getattr(labels, "add_own_language", "Your language"))
        self.own_language_input = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False)
        form.add_widget(self.own_language_input)

        add_label(getattr(labels, "add_foreign_language", "Foreign language"))
        self.foreign_language_input = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False)
        form.add_widget(self.foreign_language_input)

        row = GridLayout(cols=2, size_hint_y=None, height=dp(42), spacing=dp(10))
        row.add_widget(Label(text=getattr(labels, "three_digit_toggle", "Enable Latin column"),
                             size_hint_y=None, height=dp(30),
                             font_size=self.config["settings"]["gui"]["text_font_size"],
                             color=self.theme["on_surface"]))
        self.three_columns_checkbox = CheckBox(active=False, size_hint=(None, None), size=(dp(45), dp(45)))
        row.add_widget(self.three_columns_checkbox)
        form.add_widget(row)

        submit = RoundButton(text=getattr(labels, "add_stack_button_text", "Create"),
                             size_hint=(1, None), height=dp(64),
                             bg_color=self.theme["primary"], fg_color=self.theme["on_primary"])
        submit.bind(on_press=self.add_stack_submit)
        form.add_widget(submit)

        # >>> NEU: Widgets für Tastatur-Navigation in diesem Screen
        self.widgets_add_vocab = [
            self.stack_name_input,
            self.own_language_input,
            self.foreign_language_input,
            submit,  # Enter löst diesen Button aus
        ]

        scroll.add_widget(form)
        center.add_widget(scroll)
        self.root_layout.add_widget(center)
        self._keep_scroll_at_top(scroll)

        self._add_header(getattr(labels, "add_stack_title_text", "Create new stack"))
        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=lambda _i: (self._unbind_keyboard_if_bound(), self.main_menu()),
                          pos_hint={"right": 1, "top": 1})

        self.bottom_error_anchor = AnchorLayout(anchor_x="center", anchor_y="bottom",
                                                padding=30 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        self.add_stack_error_label = Label(text="",
                                           font_size=int(self.config["settings"]["gui"]["title_font_size"]),
                                           color=self.theme["on_bg"])
        self._fit_label(self.add_stack_error_label)
        self.bottom_error_anchor.add_widget(self.add_stack_error_label)
        self.root_layout.add_widget(self.bottom_error_anchor)

        Window.bind(on_key_down=self.on_key_down)


    def add_stack_submit(self, _instance=None) -> None:
        log("create stack submit")
        stackname = self.stack_name_input.text.strip()
        own_language = self.own_language_input.text.strip()
        foreign_language = self.foreign_language_input.text.strip()
        latin_active = self.three_columns_checkbox.active

        if not (stackname and own_language and foreign_language):
            log("create stack failed: empty fields")
            self.add_stack_error_label.text = getattr(labels, "add_stack_title_text_empty", "Fill all fields.")
            return

        target_name = stackname if stackname.endswith(".csv") else f"{stackname}.csv"
        target_path = os.path.join(self.vocab_dir, target_name)

        if os.path.exists(target_path):
            log("create stack failed: file exists")
            self.add_stack_error_label.text = getattr(labels, "add_stack_title_text_exists", "File already exists.")
            return

        open(target_path, "a").close()
        save.save_to_vocab(
            vocab=[],
            filename=target_path,
            own_lang=own_language,
            foreign_lang=foreign_language,
            latin_lang="Latein",
            latin_active=latin_active,
        )
        log(f"stack created: {target_name}")
        self._unbind_keyboard_if_bound()
        self.main_menu()

    def learn(self, stack: Optional[str] = None, mode: str = "front_back", _instance=None) -> None:
        log(f"enter learn mode={mode}")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        self.learn_mode = mode
        self.all_vocab_list = []
        self.is_back = False
        self.current_vocab_index = 0

        if stack:
            file = save.load_vocab(os.path.join(self.vocab_dir, stack))
            if isinstance(file, tuple):
                file = file[0]
            source = [file]
        else:
            source = []
            for fname in os.listdir(self.vocab_dir):
                file = save.load_vocab(os.path.join(self.vocab_dir, fname))
                if isinstance(file, tuple):
                    file = file[0]
                source.append(file)

        for vocab_list in source:
            for entry in vocab_list:
                self.all_vocab_list.append(entry)

        random.shuffle(self.all_vocab_list)
        self.max_current_vocab_index = len(self.all_vocab_list)

        if self.max_current_vocab_index == 0:
            msg_anchor = AnchorLayout(anchor_x="center", anchor_y="center")
            msg = Label(
                text=getattr(labels, "learn_no_vocab", "No vocabulary found. Please add some first."),
                font_size=int(self.config["settings"]["gui"]["title_font_size"]),
                color=self.theme["on_bg"],
            )
            self._fit_label(msg)
            msg_anchor.add_widget(msg)
            self.root_layout.add_widget(msg_anchor)
            self._icon_button("assets/back_button.png", size=(64, 64),
                              on_press=self.main_menu, pos_hint={"right": 1, "top": 1})
            return

        # content
        self.learn_content = AnchorLayout(anchor_x="center", anchor_y="center",
                                          padding=30 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        self.root_layout.add_widget(self.learn_content)

        # header + back (fixed)
        self._add_header("")
        self.header_label = Label(text="",
                                  font_size=int(self.config["settings"]["gui"]["title_font_size"]),
                                  color=self.theme["on_bg"],
                                  size_hint=(1, None))
        self._fit_label(self.header_label)
        # place header label into a small bar directly under the top
        header_bar = BoxLayout(orientation="vertical",
                               size_hint=(1, None),
                               height=self._header_spacer_height(),
                               pos_hint={"top": 1})
        header_bar.add_widget(self.header_label)
        self.root_layout.add_widget(header_bar)

        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=self.main_menu, pos_hint={"right": 1, "top": 1})

        self.recompute_available_modes()   # <- missing () fixed
        self.show_current_card()

    def show_current_card(self) -> None:
        self.learn_content.clear_widgets()
        current = self.all_vocab_list[self.current_vocab_index]

        if self.learn_mode == "front_back":
            txt = current.get("own_language", "") if not self.is_back else self._format_backside(current)
            self._show_button_card(txt, self.flip_card)
        elif self.learn_mode == "back_front":
            txt = current.get("foreign_language", "") if not self.is_back else current.get("own_language", "")
            self._show_button_card(txt, self.flip_card)
        elif self.learn_mode == "multiple_choice":
            self._multiple_choice_screen()
        else:
            self.learn(None, "front_back")

    def _show_button_card(self, text: str, callback) -> None:
        if hasattr(self, "header_label"):
            self.header_label.text = ""
        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=30 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        btn = RoundButton(text=text,
                          size_hint=(0.7, 0.5),
                          bg_color=self.theme["surface"],
                          fg_color=self.theme["on_surface"])
        btn.bind(on_press=callback)
        center.add_widget(btn)
        self.learn_content.add_widget(center)

    def _format_backside(self, vocab: Dict[str, str]) -> str:
        back = vocab.get("foreign_language", "")
        additional = vocab.get("info", "")
        latin = vocab.get("latin_language")
        return f"{back}\n\n{additional}\n\n{latin}" if latin else f"{back}\n\n{additional}"

    def flip_card(self, _instance=None) -> None:
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

    # --------------------------- Multiple Choice -----------------------------
    def _multiple_choice_screen(self) -> None:
        self.learn_content.clear_widgets()
        if not self.all_vocab_list:
            self.main_menu()
            return

        correct = self.all_vocab_list[self.current_vocab_index]
        pool = [w for w in self.all_vocab_list if w is not correct]

        wrong: List[Dict[str, str]] = []
        if len(pool) >= 4:
            wrong = random.sample(pool, 4)
        else:
            picked = set()
            for _ in range(min(4, len(pool))):
                cand = random.choice(pool)
                key = (cand.get("own_language", ""), cand.get("foreign_language", ""))
                if key not in picked:
                    wrong.append(cand)
                    picked.add(key)
            while len(wrong) < 4:
                wrong.append(correct)

        answers: List[Dict[str, str]] = []
        seen = set()
        for cand in wrong + [correct]:
            key = (cand.get("own_language", ""), cand.get("foreign_language", ""))
            if key not in seen:
                answers.append(cand)
                seen.add(key)
        if not any(
            a.get("own_language", "") == correct.get("own_language", "")
            and a.get("foreign_language", "") == correct.get("foreign_language", "")
            for a in answers
        ):
            answers.append(correct)
        random.shuffle(answers)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        form = GridLayout(cols=1, spacing=dp(12),
                          padding=[dp(24),
                                   self._header_spacer_height(),
                                   dp(24),
                                   dp(24)],
                          size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        self._apply_rounded_panel(form, color_key="surface", radius_dp=20)

        if hasattr(self, "header_label"):
            self.header_label.text = correct.get("own_language", "")

        for opt in answers:
            btn = RoundButton(text=str(opt.get("foreign_language", "")),
                              size_hint=(1, None), height=dp(64),
                              bg_color=self.theme["surface"], fg_color=self.theme["on_surface"])
            btn.bind(on_press=lambda _i, choice=opt: self.multiple_choice_select(correct, choice))
            form.add_widget(btn)

        scroll.add_widget(form)
        self.learn_content.add_widget(scroll)
        self._keep_scroll_at_top(scroll)

    def multiple_choice_select(self, correct: Dict[str, str], choice: Dict[str, str]) -> None:
        ok = (
            (choice is correct)
            or (
                choice.get("own_language", "") == correct.get("own_language", "")
                and choice.get("foreign_language", "") == correct.get("foreign_language", "")
            )
        )
        if ok:
            if self.current_vocab_index >= self.max_current_vocab_index - 1:
                self.current_vocab_index = 0
            else:
                self.current_vocab_index += 1
            self.is_back = False
            self.learn_mode = random.choice(self.available_modes)
            self.show_current_card()

    # ------------------------- Add / Edit Vocabulary -------------------------
    def add_vocab(self, stack: str, vocab: List[Dict[str, str]], _instance=None) -> None:
        log("open add vocab")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=80 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        form = GridLayout(cols=1, spacing=dp(16), padding=dp(24), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        self._apply_rounded_panel(form, color_key="surface", radius_dp=20)
        form.add_widget(Label(size_hint_y=None, height=dp(20), text=""))

        def biglbl(txt):
            return Label(text=txt, font_size=int(self.config["settings"]["gui"]["title_font_size"]),
                         color=self.theme["on_surface"])

        form.add_widget(biglbl(getattr(labels, "add_own_language", "Your language")))
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
        self.add_own_language = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False)
        form.add_widget(self.add_own_language)
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))

        form.add_widget(biglbl(getattr(labels, "add_foreign_language", "Foreign language")))
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
        self.add_foreign_language = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False)
        form.add_widget(self.add_foreign_language)
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))

        self.third_column_input: Optional[RoundedTextInput] = None
        latin_active = save.read_languages(os.path.join(self.vocab_dir, stack))[3]
        if latin_active:
            form.add_widget(biglbl(getattr(labels, "add_third_column", "Latin (optional)")))
            form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
            self.third_column_input = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False)
            form.add_widget(self.third_column_input)
            form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))

        form.add_widget(biglbl(getattr(labels, "add_additional_info", "Additional info")))
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
        self.add_additional_info = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False)
        form.add_widget(self.add_additional_info)

        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
        add_btn = RoundButton(text=getattr(labels, "add_vocabulary_button_text", "Add"),
                              size_hint_y=None, height=dp(60),
                              bg_color=self.theme["primary"], fg_color=self.theme["on_primary"])
        add_btn.bind(on_press=lambda _i: self.add_vocab_submit(vocab, stack))
        form.add_widget(add_btn)

        if self.third_column_input:
            self.widgets_add_vocab = [
                self.add_own_language,
                self.add_foreign_language,
                self.third_column_input,
                self.add_additional_info,
                add_btn,
            ]
        else:
            self.widgets_add_vocab = [
                self.add_own_language,
                self.add_foreign_language,
                self.add_additional_info,
                add_btn,
            ]

        Window.bind(on_key_down=self.on_key_down)

        scroll.add_widget(form)
        center.add_widget(scroll)
        self.root_layout.add_widget(center)
        self._keep_scroll_at_top(scroll)

        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=lambda _i: (self._unbind_keyboard_if_bound(), self.select_stack(stack))),
        # extra header for spacing/consistency
        self._add_header(getattr(labels, "add_vocab_header", "Add vocabulary"))

    def add_vocab_submit(self, vocab: List[Dict[str, str]], stack: str) -> None:
        own = self.add_own_language.text.strip()
        foreign = self.add_foreign_language.text.strip()
        latin = self.third_column_input.text.strip() if getattr(self, "third_column_input", None) else ""
        info = self.add_additional_info.text.strip()

        if not own or not foreign:
            log("add vocab aborted: missing fields")
            return

        vocab.append({
            "own_language": own,
            "foreign_language": foreign,
            "latin_language": latin,
            "info": info,
        })
        save.save_to_vocab(vocab, os.path.join(self.vocab_dir, stack))
        log("vocab added")
        self._clear_add_vocab_inputs()

    def edit_metadata(self, stack: str, _instance=None) -> None:
        log("open edit metadata")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=80 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        form = GridLayout(cols=1, spacing=dp(16), padding=dp(24), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        self._apply_rounded_panel(form, color_key="surface", radius_dp=20)
        form.add_widget(Label(size_hint_y=None, height=dp(20), text=""))

        own_lang, foreign_lang, _latin_name, latin_active = save.read_languages(os.path.join(self.vocab_dir, stack))

        def biglbl(txt):
            return Label(text=txt, font_size=int(self.config["settings"]["gui"]["title_font_size"]),
                         color=self.theme["on_surface"])

        form.add_widget(biglbl(getattr(labels, "add_own_language", "Your language")))
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
        self.edit_own_language_input = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False, text=own_lang)
        form.add_widget(self.edit_own_language_input)
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))

        form.add_widget(biglbl(getattr(labels, "add_foreign_language", "Foreign language")))
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
        self.edit_foreign_language_input = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False, text=foreign_lang)
        form.add_widget(self.edit_foreign_language_input)
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))

        form.add_widget(biglbl(getattr(labels, "add_stack_filename", "File name")))
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))
        self.edit_name_input = RoundedTextInput(size_hint_y=None, height=dp(60), multiline=False, text=stack[:-4])
        form.add_widget(self.edit_name_input)
        form.add_widget(Label(text="", size_hint_y=None, height=dp(4)))

        save_btn = RoundButton(text=getattr(labels, "save", "Save"), size_hint_y=None, height=dp(60),
                               bg_color=self.theme["primary"], fg_color=self.theme["on_primary"])
        save_btn.bind(on_press=lambda _i: self.edit_metadata_submit(stack, latin_active))
        form.add_widget(save_btn)

        scroll.add_widget(form)
        center.add_widget(scroll)
        self.root_layout.add_widget(center)
        self._keep_scroll_at_top(scroll)

        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=lambda _i: self.select_stack(stack),
                          pos_hint={"right": 1, "top": 1})

    def edit_vocab(self, stack: str, vocab: List[Dict[str, str]], _instance=None) -> None:
        log("open edit vocab")
        self._unbind_keyboard_if_bound()
        self.root_layout.clear_widgets()

        center = AnchorLayout(anchor_x="center", anchor_y="center",
                              padding=80 * float(self.config["settings"]["gui"]["padding_multiplicator"]))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        form = GridLayout(cols=1, spacing=dp(16), padding=dp(24), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        self._apply_rounded_panel(form, color_key="surface", radius_dp=20)
        form.add_widget(Label(size_hint_y=None, height=dp(20), text=""))

        latin_active = save.read_languages(os.path.join(self.vocab_dir, stack))[3]
        matrix = self._build_vocab_grid(form, vocab, latin_active)

        scroll.add_widget(form)
        center.add_widget(scroll)
        self.root_layout.add_widget(center)
        self._keep_scroll_at_top(scroll)

        save_all = RoundButton(text=getattr(labels, "save", "Save"),
                               size_hint=(None, None), size=(200, 60),
                               bg_color=self.theme["primary"], fg_color=self.theme["on_primary"])
        save_all.pos_hint = {"center_x": 0.5, "top": 1}
        save_all.bind(on_press=lambda _i: self.edit_vocab_submit(matrix, stack, latin_active))
        self.root_layout.add_widget(save_all)

        self._icon_button("assets/back_button.png", size=(64, 64),
                          on_press=lambda _i: self.select_stack(stack),
                          pos_hint={"right": 1, "top": 1})

    # ------------------------------ Submitters / I-O --------------------------
    def edit_vocab_submit(self, matrix: List[List[TextInput]], stack: str, latin_active: bool) -> None:
        vocab = self._read_vocab_from_grid(matrix, latin_active)
        save.save_to_vocab(vocab, os.path.join(self.vocab_dir, stack))
        log("vocab saved")
        self.select_stack(stack)

    def edit_metadata_submit(self, stack: str, latin_active: bool) -> None:
        new_name = self.edit_name_input.text.strip()
        if not new_name:
            log("rename failed: empty name")
            return

        old_path = os.path.join(self.vocab_dir, stack)
        new_path = os.path.join(self.vocab_dir, f"{new_name}.csv")

        if os.path.exists(new_path) and new_path != old_path:
            log("rename failed: target exists")
            anchor = AnchorLayout(anchor_x="center", anchor_y="bottom")
            anchor.add_widget(Label(text=getattr(labels, "filename_exists", "Filename already exists."),
                                    font_size=int(self.config["settings"]["gui"]["text_font_size"]),
                                    color=self.theme["on_bg"]))
            self.root_layout.add_widget(anchor)
            return

        save.change_languages(
            old_path,
            self.edit_own_language_input.text,
            self.edit_foreign_language_input.text,
            "Latein",
            latin_active,
        )
        os.rename(old_path, new_path)
        self.select_stack(f"{new_name}.csv")

    def _read_vocab_from_grid(self, textinput_matrix: List[List[TextInput]], latin_active: bool) -> List[Dict[str, str]]:
        vocab_list: List[Dict[str, str]] = []
        for row in textinput_matrix:
            if latin_active:
                own, foreign, latin, info = [ti.text.strip() for ti in row]
            else:
                own, foreign, info = [ti.text.strip() for ti in row]
                latin = ""
            if not (own or foreign or latin or info):
                continue
            vocab_list.append({
                "own_language": own,
                "foreign_language": foreign,
                "latin_language": latin,
                "info": info,
            })
        return vocab_list

    def _build_vocab_grid(self, parent_layout: BoxLayout,
                          vocab_list: List[Dict[str, str]],
                          latin_active: bool) -> List[List[TextInput]]:
        cols = 4 if latin_active else 3
        grid = GridLayout(cols=cols, size_hint_y=None, spacing=dp(10))
        grid.bind(minimum_height=grid.setter("height"))

        matrix: List[List[TextInput]] = []
        for vocab in vocab_list:
            row: List[TextInput] = []
            for key in ("own_language", "foreign_language"):
                ti = RoundedTextInput(text=vocab.get(key, ""), multiline=False, size_hint_y=None, height=dp(60))
                grid.add_widget(ti)
                row.append(ti)
            if latin_active:
                ti_lat = RoundedTextInput(text=vocab.get("latin_language", ""), multiline=False, size_hint_y=None, height=dp(60))
                grid.add_widget(ti_lat)
                row.append(ti_lat)
            ti_info = RoundedTextInput(text=vocab.get("info", ""), multiline=False, size_hint_y=None, height=dp(60))
            grid.add_widget(ti_info)
            row.append(ti_info)
            matrix.append(row)

        parent_layout.add_widget(grid)
        return matrix

    # ---------------------------- Keyboard Nav --------------------------------
    # ---------------------------- Keyboard Nav --------------------------------
    def on_key_down(self, _window, key, _scancode, _codepoint, modifiers) -> bool:
        # Wenn es für diesen Screen keine Tastatur-Navigation gibt, nichts abfangen
        if not getattr(self, "widgets_add_vocab", None):
            return False

        focused_index = None
        for i, widget in enumerate(self.widgets_add_vocab):
            if hasattr(widget, "focus") and widget.focus:
                focused_index = i
                break

        # TAB: Fokus zwischen den Feldern wechseln
        if key == 9:  # Tab
            # wenn noch nichts fokussiert ist -> erstes fokussierbares Widget wählen
            if focused_index is None:
                for widget in self.widgets_add_vocab:
                    if hasattr(widget, "focus"):
                        widget.focus = True
                        break
            else:
                delta = -1 if "shift" in modifiers else 1
                next_index = (focused_index + delta) % len(self.widgets_add_vocab)
                if hasattr(self.widgets_add_vocab[next_index], "focus"):
                    self.widgets_add_vocab[next_index].focus = True
            return True  # Tab komplett von uns behandelt

        # ENTER: Falls aktuelles Feld TextInput ist -> "Submit"-Button auslösen
        if key == 13 and focused_index is not None:  # Enter
            current = self.widgets_add_vocab[focused_index]
            if isinstance(current, TextInput):
                last = self.widgets_add_vocab[-1]
                if isinstance(last, Button):
                    last.trigger_action(duration=0.1)
            return True  # Enter auch abgefangen

        # alle anderen Tasten normal durchlassen (damit TextInput schreiben kann)
        return False


    # ---------------------------- Settings Writers ----------------------------
    def _on_setting_changed(self, key_path: Sequence[str], cast_type):
        def _callback(_instance, value):
            value_cast = cast_type(value)
            ref = self.config
            for key in key_path[:-1]:
                ref = ref[key]
            ref[key_path[-1]] = value_cast
            log(f"{'.'.join(key_path)} = {value_cast}")
            save.save_settings(self.config)
        return _callback

    def recompute_available_modes(self) -> None:
        if get_in(self.config, ["settings", "modes"]) is None:
            set_in(self.config, ["settings", "modes"],
                   {"front_back": True, "back_front": True, "multiple_choice": True})
            save.save_settings(self.config)

        modes_cfg = get_in(self.config, ["settings", "modes"], {}) or {}
        vocab_len = len(getattr(self, "all_vocab_list", []))

        self.available_modes = []
        if bool_cast(modes_cfg.get("front_back", True)):
            self.available_modes.append("front_back")
        if bool_cast(modes_cfg.get("back_front", True)):
            self.available_modes.append("back_front")
        if bool_cast(modes_cfg.get("multiple_choice", True)) and vocab_len >= 5:
            self.available_modes.append("multiple_choice")

    def _on_mode_checkbox_changed(self, path: Sequence[str]):
        def _handler(_instance, value):
            set_in(self.config, path, bool(value))
            save.save_settings(self.config)
            self.recompute_available_modes()
        return _handler

    # ------------------------------ Misc -------------------------------------
    def _clear_add_vocab_inputs(self) -> None:
        self.add_own_language.text = ""
        self.add_foreign_language.text = ""
        if getattr(self, "third_column_input", None):
            self.third_column_input.text = ""
        self.add_additional_info.text = ""
        self.add_own_language.focus = True

    def delete_stack(self, stack: str, _instance=None) -> None:
        os.remove(os.path.join(self.vocab_dir, stack))
        log(f"deleted stack: {stack}")
        self.main_menu()


# -------------------------------- Entrypoint ---------------------------------
if __name__ == "__main__":
    VokabaApp().run()
