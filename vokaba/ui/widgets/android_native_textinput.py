from __future__ import annotations

"""
Android-native EditText overlay for Kivy TextInput.

Goal:
- On Android tablets (stylus handwriting / Ink-to-Text), Android needs a real
  android.widget.EditText with a proper InputConnection. Kivy's TextInput is
  not a native EditText, so ink-to-text can't commit reliably.
- This widget keeps a Kivy TextInput for layout + styling (background), but
  renders / edits text through a native EditText placed as an overlay in the
  Android view hierarchy.

How it works:
- On Android: creates an EditText and adds it to a shared overlay FrameLayout
  (attached to android.R.id.content).
- Synchronizes:
    * text  (Android -> Kivy, Kivy -> Android)
    * focus (Kivy focus -> Android focus + IME, Android focus -> Kivy focus)
    * submit (IME action / Enter -> dispatch on_text_validate)
- Keeps the Android view positioned over the Kivy widget (pos/size), including
  inside ScrollViews.
- Cleans up the native view when the Kivy widget is removed (screen switches).
"""

from kivy.utils import platform as kivy_platform

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import BooleanProperty, NumericProperty, ListProperty, ObjectProperty

from vokaba.ui.widgets.lock_textinput import LockScrollTextInput
from vokaba.core.logging_utils import log


if kivy_platform != "android":

    class AndroidNativeTextInput(LockScrollTextInput):
        """
        Desktop / non-Android fallback: behaves like normal Kivy TextInput.
        The 'native' methods are no-ops so the rest of the app can call them safely.
        """

        def apply_native_style(self, **_kwargs):
            return

else:
    # Android-only imports
    from jnius import autoclass, cast, PythonJavaClass, java_method

    try:
        from android.runnable import run_on_ui_thread
    except Exception:  # pragma: no cover (depends on packaging)
        run_on_ui_thread = None

    # Java classes
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    _activity = PythonActivity.mActivity

    FrameLayoutParams = autoclass("android.widget.FrameLayout$LayoutParams")
    EditText = autoclass("android.widget.EditText")
    Color = autoclass("android.graphics.Color")
    TypedValue = autoclass("android.util.TypedValue")
    InputType = autoclass("android.text.InputType")
    EditorInfo = autoclass("android.view.inputmethod.EditorInfo")
    Context = autoclass("android.content.Context")
    KeyEvent = autoclass("android.view.KeyEvent")
    Gravity = autoclass("android.view.Gravity")
    View = autoclass("android.view.View")
    R_id = autoclass("android.R$id")
    InputMethodManager = autoclass("android.view.inputmethod.InputMethodManager")

    def _rgba_to_argb_int(rgba):
        try:
            r, g, b, a = rgba
        except Exception:
            r, g, b, a = (1, 1, 1, 1)
        r_i = max(0, min(255, int(float(r) * 255)))
        g_i = max(0, min(255, int(float(g) * 255)))
        b_i = max(0, min(255, int(float(b) * 255)))
        a_i = max(0, min(255, int(float(a) * 255)))
        return Color.argb(a_i, r_i, g_i, b_i)


    def _get_content_parent():
        """Return the Activity content ViewGroup to attach native views to."""
        try:
            parent = _activity.findViewById(R_id.content)
            if parent is None:
                parent = _activity.getWindow().getDecorView()
            return cast("android.view.ViewGroup", parent)
        except Exception as e:
            try:
                log(f"AndroidNativeTextInput: could not get content parent: {e}")
            except Exception:
                pass
            return None


    class _TextWatcher(PythonJavaClass):
        __javainterfaces__ = ["android/text/TextWatcher"]
        __javacontext__ = "app"

        def __init__(self, owner):
            super().__init__()
            self._owner = owner
            self._geom_ready = False

        @java_method("(Ljava/lang/CharSequence;III)V")
        def beforeTextChanged(self, _s, _start, _count, _after):
            return

        @java_method("(Ljava/lang/CharSequence;III)V")
        def onTextChanged(self, _s, _start, _before, _count):
            return

        @java_method("(Landroid/text/Editable;)V")
        def afterTextChanged(self, editable):
            try:
                owner = self._owner
                if owner is None:
                    return
                if bool(getattr(owner, "_ignore_android_text", False)):
                    return
                txt = editable.toString() if editable is not None else ""
                owner._on_android_text(str(txt))
            except Exception:
                return


    class _EditorActionListener(PythonJavaClass):
        __javainterfaces__ = ["android/widget/TextView$OnEditorActionListener"]
        __javacontext__ = "app"

        def __init__(self, owner):
            super().__init__()
            self._owner = owner
            self._geom_ready = False

        @java_method("(Landroid/widget/TextView;ILandroid/view/KeyEvent;)Z")
        def onEditorAction(self, _v, action_id, event):
            try:
                owner = self._owner
                if owner is None:
                    return False

                # IME action buttons
                if int(action_id) in (
                    int(EditorInfo.IME_ACTION_DONE),
                    int(EditorInfo.IME_ACTION_GO),
                    int(EditorInfo.IME_ACTION_SEND),
                    int(EditorInfo.IME_ACTION_NEXT),
                    int(EditorInfo.IME_ACTION_SEARCH),
                ):
                    owner._dispatch_text_validate()
                    return True

                # Physical enter key
                if event is not None:
                    try:
                        if int(event.getKeyCode()) == int(KeyEvent.KEYCODE_ENTER) and int(event.getAction()) == int(
                            KeyEvent.ACTION_UP
                        ):
                            owner._dispatch_text_validate()
                            return True
                    except Exception:
                        pass
            except Exception:
                return False
            return False


    class _FocusChangeListener(PythonJavaClass):
        __javainterfaces__ = ["android/view/View$OnFocusChangeListener"]
        __javacontext__ = "app"

        def __init__(self, owner):
            super().__init__()
            self._owner = owner
            self._geom_ready = False

            if self.disabled or self.opacity <= 0:
                self._set_android_visibility(False)
                self._geom_ready = False
                self._disable_native_kivy_mode()
                return

        @java_method("(Landroid/view/View;Z)V")
        def onFocusChange(self, _v, has_focus):
            try:
                owner = self._owner
                if owner is None:
                    return
                owner._on_android_focus(bool(has_focus))
            except Exception:
                return


    class AndroidNativeTextInput(LockScrollTextInput):
        """
        Kivy TextInput + Android EditText overlay.

        NOTE:
        - The Kivy TextInput draws the background (so it matches your theme).
        - The Android EditText draws the text, selection, cursor and receives handwriting.
        """

        # Public tuning
        update_interval = NumericProperty(1 / 20.0)

        # Internal
        _android_view = ObjectProperty(None, allownone=True)
        _android_created = BooleanProperty(False)
        _android_creating = BooleanProperty(False)
        _ignore_android_text = BooleanProperty(False)
        _ignore_kivy_text = BooleanProperty(False)
        _pending_focus_from_android = BooleanProperty(False)

        # Styling for native view (set by UIFactoryMixin.style_textinput)
        _native_text_rgba = ListProperty([1, 1, 1, 1])
        _native_hint_rgba = ListProperty([1, 1, 1, 0.6])
        _native_padding_dp = ListProperty([12, 10, 12, 10])  # L,T,R,B in dp units
        _native_font_sp = NumericProperty(18)

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._geom_ready = False
            if self.disabled or self.opacity <= 0:
                self._set_android_visibility(False)
                self._geom_ready = False
                self._disable_native_kivy_mode()
                return

            # IMPORTANT SAFETY:
            # Don't disable Kivy input until the native EditText was successfully created.
            # Otherwise a creation/positioning bug would make the whole app feel "dead".
            self._native_mode = False
            try:
                self._orig_readonly = bool(getattr(self, "readonly", False))
            except Exception:
                self._orig_readonly = False
            try:
                self._orig_foreground_color = tuple(getattr(self, "foreground_color", (1, 1, 1, 1)))
                self._orig_cursor_color = tuple(getattr(self, "cursor_color", (1, 1, 1, 1)))
                self._orig_selection_color = tuple(getattr(self, "selection_color", (1, 1, 1, 0.3)))
            except Exception:
                self._orig_foreground_color = None
                self._orig_cursor_color = None
                self._orig_selection_color = None

            self._last_geom = None
            self._geom_ev = None

            # Bind Kivy->Android sync
            self.bind(text=self._on_kivy_text_changed)
            self.bind(hint_text=self._on_kivy_hint_changed)
            self.bind(disabled=self._trigger_geom)
            self.bind(opacity=self._trigger_geom)

        # ------------- Kivy keyboard suppression -------------
        def keyboard_on_focus(self, _window, _focus):
            # Only suppress the Kivy keyboard once the native EditText is active.
            # Before that, keep normal Kivy behavior as a fallback.
            if bool(getattr(self, "_native_mode", False)):
                return None
            try:
                return super().keyboard_on_focus(_window, _focus)
            except Exception:
                return None

        def _enable_native_kivy_mode(self):
            """Make Kivy TextInput visually present (background), but let Android handle text."""
            if bool(getattr(self, "_native_mode", False)):
                return
            # Only enable if we really have the Android view
            if not (self._android_view is not None and bool(getattr(self, "_android_created", False))):
                return
            if not bool(getattr(self, "_geom_ready", False)):
                return
            self._native_mode = True

            # Hide Kivy text/cursor to prevent double rendering.
            try:
                self.readonly = True
            except Exception:
                pass
            try:
                self.foreground_color = (0, 0, 0, 0)
                self.cursor_color = (0, 0, 0, 0)
                self.selection_color = (0, 0, 0, 0)
            except Exception:
                pass

        def _disable_native_kivy_mode(self):
            self._native_mode = False
            self._geom_ready = False
            try:
                self.readonly = self._orig_readonly
            except Exception:
                pass
            try:
                if self._orig_foreground_color: self.foreground_color = self._orig_foreground_color
                if self._orig_cursor_color: self.cursor_color = self._orig_cursor_color
                if self._orig_selection_color: self.selection_color = self._orig_selection_color
            except Exception:
                pass

        # ------------- lifecycle -------------
        def on_parent(self, _inst, parent):
            # Added to widget tree
            if parent is not None:
                Clock.schedule_once(lambda _dt: self._ensure_android_view(), 0)
                self._start_geometry_updates()
            else:
                self._stop_geometry_updates()
                self._destroy_android_view()

        def on_pos(self, *_args):
            self._trigger_geom()

        def on_size(self, *_args):
            self._trigger_geom()

        def _start_geometry_updates(self):
            if self._geom_ev is None:
                self._geom_ev = Clock.schedule_interval(self._sync_geometry, float(self.update_interval))

        def _stop_geometry_updates(self):
            if self._geom_ev is not None:
                try:
                    self._geom_ev.cancel()
                except Exception:
                    pass
                self._geom_ev = None

        def _trigger_geom(self, *_args):
            # Run an update soon (avoid doing heavy work directly in property callbacks)
            Clock.schedule_once(lambda _dt: self._sync_geometry(0), 0)

        # ------------- focus sync -------------
        def on_focus(self, inst, value: bool):
            # Keep ScrollView lock behavior
            try:
                super().on_focus(inst, value)
            except Exception:
                pass

            # If focus was set because Android already focused, don't bounce back
            if bool(self._pending_focus_from_android):
                return

            self._ensure_android_view()
            self._sync_focus_to_android(bool(value))

        def _on_android_focus(self, has_focus: bool):
            # Android -> Kivy focus
            def _apply(_dt):
                self._pending_focus_from_android = True
                try:
                    self.focus = bool(has_focus)
                except Exception:
                    pass
                self._pending_focus_from_android = False

            Clock.schedule_once(_apply, 0)

        def _sync_focus_to_android(self, want_focus: bool):
            view = self._android_view
            if view is None:
                return

            def _do():
                try:
                    if want_focus:
                        imm = cast("android.view.inputmethod.InputMethodManager",
                                   _activity.getSystemService(Context.INPUT_METHOD_SERVICE))
                        try:
                            view.requestFocusFromTouch()
                        except Exception:
                            view.requestFocus()
                        imm.showSoftInput(view, 0)

                        if imm is not None:
                            imm.showSoftInput(view, 0)
                    else:
                        view.clearFocus()
                        imm = cast("android.view.inputmethod.InputMethodManager",
                                   _activity.getSystemService(Context.INPUT_METHOD_SERVICE))
                        if imm is not None:
                            imm.hideSoftInputFromWindow(view.getWindowToken(), 0)
                except Exception:
                    pass

            if run_on_ui_thread is not None:
                run_on_ui_thread(_do)()
            else:
                _do()

        # ------------- text sync -------------
        def _on_android_text(self, new_text: str):
            # Android UI thread -> schedule into Kivy thread
            def _apply(_dt):
                self._ignore_kivy_text = True
                try:
                    self.text = new_text
                except Exception:
                    pass
                self._ignore_kivy_text = False

            Clock.schedule_once(_apply, 0)

        def _on_kivy_text_changed(self, _inst, value):
            if bool(self._ignore_kivy_text):
                return
            self._set_android_text(value if value is not None else "")

        def _on_kivy_hint_changed(self, _inst, value):
            self._set_android_hint(value if value is not None else "")

        def _set_android_text(self, value: str):
            view = self._android_view
            if view is None:
                return

            def _do():
                try:
                    self._ignore_android_text = True
                    view.setText(str(value))
                    try:
                        view.setSelection(len(str(value)))
                    except Exception:
                        pass
                except Exception:
                    pass
                self._ignore_android_text = False

            if run_on_ui_thread is not None:
                run_on_ui_thread(_do)()
            else:
                _do()

        def _set_android_hint(self, value: str):
            view = self._android_view
            if view is None:
                return

            def _do():
                try:
                    view.setHint(str(value))
                except Exception:
                    pass

            if run_on_ui_thread is not None:
                run_on_ui_thread(_do)()
            else:
                _do()

        def _dispatch_text_validate(self):
            # Dispatch on Kivy thread
            Clock.schedule_once(lambda _dt: self.dispatch("on_text_validate"), 0)

        # ------------- styling -------------
        def apply_native_style(self, text_rgba=None, hint_rgba=None, padding_dp=None, font_sp=None, **_kwargs):
            """
            Called by UIFactoryMixin.style_textinput() on Android.
            """
            if text_rgba is not None:
                self._native_text_rgba = list(text_rgba)
            if hint_rgba is not None:
                self._native_hint_rgba = list(hint_rgba)
            if padding_dp is not None:
                self._native_padding_dp = list(padding_dp)
            if font_sp is not None:
                try:
                    self._native_font_sp = float(font_sp)
                except Exception:
                    pass

            # Only hide Kivy text/cursor once the native EditText exists.
            # Before that, keep normal Kivy behavior as a safety fallback.
            try:
                self._enable_native_kivy_mode()
            except Exception:
                pass

            self._apply_android_style()

        def _apply_android_style(self):
            view = self._android_view
            if view is None:
                return

            text_color = _rgba_to_argb_int(self._native_text_rgba)
            hint_color = _rgba_to_argb_int(self._native_hint_rgba)
            pad = list(self._native_padding_dp or [12, 10, 12, 10])
            font_sp = float(self._native_font_sp or 18)

            def _do():
                try:
                    # transparent background so Kivy draws the box
                    view.setBackgroundColor(Color.TRANSPARENT)

                    view.setTextColor(text_color)
                    try:
                        view.setHintTextColor(hint_color)
                    except Exception:
                        pass

                    # Padding (dp -> px)
                    dm = _activity.getResources().getDisplayMetrics()
                    density = float(getattr(dm, "density", 1.0) or 1.0)
                    pl = int(pad[0] * density)
                    pt = int(pad[1] * density)
                    pr = int(pad[2] * density)
                    pb = int(pad[3] * density)
                    view.setPadding(pl, pt, pr, pb)

                    # Font size in SP
                    view.setTextSize(TypedValue.COMPLEX_UNIT_SP, float(font_sp))

                    # Align similar to Kivy (left + centered vertically)
                    try:
                        view.setGravity(int(Gravity.START) | int(Gravity.CENTER_VERTICAL))
                    except Exception:
                        pass

                    # Optional: remove extra font padding (looks closer to Kivy)
                    try:
                        view.setIncludeFontPadding(False)
                    except Exception:
                        pass
                except Exception:
                    pass

            if run_on_ui_thread is not None:
                run_on_ui_thread(_do)()
            else:
                _do()

        # ------------- native view creation / destruction -------------
        def _ensure_android_view(self):
            if (self._android_created and self._android_view is not None) or bool(getattr(self, "_android_creating", False)):
                return

            # Attach the native EditText directly to the Activity content ViewGroup.
            # IMPORTANT: Do NOT create a full-screen overlay container, otherwise it will block
            # all touches to the Kivy view underneath.
            parent_vg = _get_content_parent()
            if parent_vg is None:
                Clock.schedule_once(lambda _dt: self._ensure_android_view(), 0.1)
                return

            self._android_creating = True

            def _create():
                try:
                    parent = _get_content_parent()
                    if parent is None:
                        try:
                            self._android_creating = False
                        except Exception:
                            pass
                        return

                    view = EditText(_activity)

                    # Input behavior
                    if bool(getattr(self, "multiline", False)):
                        # Multi-line
                        view.setSingleLine(False)
                        view.setImeOptions(int(EditorInfo.IME_ACTION_DONE))
                        view.setInputType(
                            int(InputType.TYPE_CLASS_TEXT)
                            | int(InputType.TYPE_TEXT_FLAG_MULTI_LINE)
                            | int(InputType.TYPE_TEXT_FLAG_CAP_SENTENCES)
                        )
                    else:
                        # Single-line (default)
                        view.setSingleLine(True)
                        view.setImeOptions(int(EditorInfo.IME_ACTION_DONE))
                        view.setInputType(int(InputType.TYPE_CLASS_TEXT) | int(InputType.TYPE_TEXT_FLAG_CAP_SENTENCES))

                    # No Kivy background: let Kivy render the box.
                    view.setBackgroundColor(Color.TRANSPARENT)

                    # Attach listeners
                    self._tw = _TextWatcher(self)
                    view.addTextChangedListener(self._tw)

                    self._editor_listener = _EditorActionListener(self)
                    view.setOnEditorActionListener(self._editor_listener)

                    self._focus_listener = _FocusChangeListener(self)
                    view.setOnFocusChangeListener(self._focus_listener)

                    # Initial text + hint
                    try:
                        view.setText(str(self.text or ""))
                        view.setHint(str(getattr(self, "hint_text", "") or ""))
                    except Exception:
                        pass

                    # Add to Activity content
                    lp = FrameLayoutParams(1, 1)
                    view.setLayoutParams(lp)
                    parent.addView(view)

                    # nach parent.addView(view)
                    try:
                        view.setFocusable(True)
                        view.setFocusableInTouchMode(True)
                        view.setClickable(True)
                        view.bringToFront()
                        parent.requestLayout()
                        parent.invalidate()
                    except Exception:
                        pass

                    self._android_view = view
                    self._android_created = True
                    self._android_creating = False

                    # After native view exists, hide Kivy text/cursor and suppress Kivy keyboard.
                    #Clock.schedule_once(lambda _dt: self._enable_native_kivy_mode(), 0)

                    # Apply style if already set
                    self._apply_android_style()

                except Exception as e:
                    try:
                        self._android_creating = False
                    except Exception:
                        pass
                    log(f"AndroidNativeTextInput: create view failed: {e}")

            if run_on_ui_thread is not None:
                run_on_ui_thread(_create)()
            else:
                _create()

            # Position it ASAP (after creation)
            Clock.schedule_once(lambda _dt: self._sync_geometry(0), 0)

        def _destroy_android_view(self):
            view = self._android_view
            if view is None:
                return

            def _do():
                try:
                    parent = cast("android.view.ViewGroup", view.getParent())
                    if parent is not None:
                        parent.removeView(view)
                except Exception:
                    pass

            if run_on_ui_thread is not None:
                run_on_ui_thread(_do)()
            else:
                _do()

            self._android_view = None
            self._android_created = False

        # ------------- geometry sync -------------
        def _sync_geometry(self, _dt):
            view = self._android_view
            if view is None:
                return

            try:
                if self.disabled or self.opacity <= 0:
                    self._set_android_visibility(False)
                    self._disable_native_kivy_mode()
                    return
            except Exception:
                pass

            # Kivy -> window coords (bottom-left origin)
            try:
                wx, wy = self.to_window(0, 0)
                w = float(self.width)
                h = float(self.height)
            except Exception:
                return

            # Android parent view size (Android px)
            try:
                parent_vg = cast("android.view.ViewGroup", view.getParent())
                if parent_vg is None:
                    return
                ow = float(parent_vg.getWidth())
                oh = float(parent_vg.getHeight())
            except Exception:
                return

            if ow <= 1 or oh <= 1:
                return

            # Kivy Window size (Kivy px)
            kw = float(Window.width or 1)
            kh = float(Window.height or 1)

            sx = ow / kw
            sy = oh / kh

            # Convert to Android px (top-left origin)
            left = int(wx * sx)
            top = int((kh - (wy + h)) * sy)
            width_px = max(1, int(w * sx))
            height_px = max(1, int(h * sy))

            # Hide if completely offscreen
            if (left + width_px) < 0 or (top + height_px) < 0 or left > ow or top > oh:
                self._set_android_visibility(False)
                self._disable_native_kivy_mode()
                return

            self._set_android_visibility(True)

            geom = (left, top, width_px, height_px)
            # nach width_px / height_px berechnet wurden und bevor du früh returnst
            if width_px >= 2 and height_px >= 2:
                self._geom_ready = True
                self._enable_native_kivy_mode()
            if geom == self._last_geom:
                return
            self._last_geom = geom

            def _do():
                try:
                    lp = view.getLayoutParams()
                    if lp is None or int(lp.width) != int(width_px) or int(lp.height) != int(height_px):
                        lp = FrameLayoutParams(int(width_px), int(height_px))
                        view.setLayoutParams(lp)
                    else:
                        lp.width = int(width_px)
                        lp.height = int(height_px)
                        view.setLayoutParams(lp)

                    # Position
                    view.setX(float(left))
                    view.setY(float(top))
                except Exception:
                    pass

            if run_on_ui_thread is not None:
                run_on_ui_thread(_do)()
            else:
                _do()

        def _set_android_visibility(self, visible: bool):
            view = self._android_view
            if view is None:
                return

            def _do():
                try:
                    view.setVisibility(int(View.VISIBLE if visible else View.GONE))
                except Exception:
                    pass

            if run_on_ui_thread is not None:
                run_on_ui_thread(_do)()
            else:
                _do()
