from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.utils import platform
from kivy.resources import resource_add_path


import unicodedata

import save
import labels

from vokaba.theme.theme_manager import apply_theme_from_config
from vokaba.core.logging_utils import log
from vokaba.mixins.ocr_import import OcrImportMixin


from vokaba.ui.factories import UIFactoryMixin

from vokaba.mixins.stats_goal import StatsGoalMixin
from vokaba.mixins.main_menu import MainMenuMixin
from vokaba.mixins.settings import SettingsMixin
from vokaba.mixins.stacks import StacksMixin
from vokaba.mixins.add_stack import AddStackMixin
from vokaba.mixins.add_vocab import AddVocabMixin
from vokaba.mixins.edit_vocab import EditVocabMixin
from vokaba.mixins.about_dashboard import AboutDashboardMixin
from vokaba.mixins.learn import LearnMixin
from vokaba.core.paths import runtime_root


class VokabaApp(
    App,
    UIFactoryMixin,
    StatsGoalMixin,
    MainMenuMixin,
    SettingsMixin,
    StacksMixin,
    AddStackMixin,
    AddVocabMixin,
    OcrImportMixin,
    EditVocabMixin,
    AboutDashboardMixin,
    LearnMixin,
):
    """
    Modular Vokaba app (AI-friendly codebase).
    Logic is split into mixins: menu, stacks, settings, learning, etc.
    """

    def build(self):
        # Disable multitouch only on desktop
        resource_add_path(str(runtime_root()))
        if platform in ("win", "linux", "macosx"):
            Config.set("input", "mouse", "mouse,disable_multitouch")

        self.config_data = save.load_settings()
        self.colors = apply_theme_from_config(self.config_data)

        try:
            if platform in ("win", "linux", "macosx"):
                Window.size = (1280, 800)
        except Exception as e:
            log(f"Could not set window size: {e}")

        # Android/Tablet: ensure the system IME can appear (helps handwriting keyboards)
        if platform == "android":
            try:
                Window.softinput_mode = "below_target"
            except Exception:
                pass


        self.current_focus_input = None
        self._install_dead_key_composer()
        self.window = FloatLayout()

        # App-level state used by learning autosave
        self.all_vocab_list = []
        self.stack_vocab_lists = {}
        self.stack_meta_map = {}
        self.entry_to_stack_file = {}

        # Window/App title (desktop title bar)
        try:
            self.title = getattr(labels, "welcome_text", "Vokaba")
            Window.title = self.title
        except Exception:
            pass


        self.main_menu()
        return self.window

    def reload_config(self):
        """Reload config.yml and refresh theme colors."""
        new_cfg = save.load_settings()
        self.config_data.clear()
        self.config_data.update(new_cfg)
        self.colors = apply_theme_from_config(self.config_data)

    # ------------------------------------------------------------
    # Physical keyboard "dead key" composer (Android tablets etc.)
    # ------------------------------------------------------------
    def _install_dead_key_composer(self):
        # Some Kivy/Android combinations don't compose dead keys (´ + e => ´e).
        # We emulate a small subset of composition so users can type é/à/ü/etc.
        self._pending_dead_key = None
        try:
            Window.bind(on_textinput=self._on_window_textinput_deadkeys)
            Window.bind(on_key_down=self._on_window_key_down_deadkeys)
        except Exception as e:
            log(f"dead-key composer bind failed: {e}")

    def _on_window_key_down_deadkeys(self, _window, key, _scancode, _codepoint, _modifiers):
        # Clear pending dead key on "non text" actions.
        if getattr(self, "_pending_dead_key", None) and key in (8, 13, 27):  # backspace / enter / esc
            self._pending_dead_key = None
        return False

    def _on_window_textinput_deadkeys(self, _window, text):
        # Kivy passes "text" for actual text input. We intercept only when a
        # TextInput is focused and a dead key was pressed previously.
        ti = getattr(self, "current_focus_input", None)
        if not isinstance(ti, TextInput):
            return False

        dead_to_combining = {
            "´": "\u0301",  # acute
            "`": "\u0300",  # grave
            "^": "\u0302",  # circumflex
            "¨": "\u0308",  # diaeresis/umlaut
            "~": "\u0303",  # tilde
            "¸": "\u0327",  # cedilla
        }

        pending = getattr(self, "_pending_dead_key", None)

        if pending:
            # Pressing the same dead key twice should yield the literal character.
            if text == pending:
                ti.insert_text(pending)
                self._pending_dead_key = None
                return True

            # If user presses another dead key, output previous and keep new pending.
            if text in dead_to_combining:
                ti.insert_text(pending)
                self._pending_dead_key = text
                return True

            # Space after dead key should output the literal accent.
            if text == " ":
                ti.insert_text(pending)
                self._pending_dead_key = None
                return True

            comb = dead_to_combining.get(pending)
            self._pending_dead_key = None

            if comb and len(text) == 1:
                composed = unicodedata.normalize("NFC", text + comb)
                ti.insert_text(composed)
            else:
                ti.insert_text(pending + text)

            return True

        # No pending: if this key is a dead accent, start pending.
        if text in dead_to_combining:
            self._pending_dead_key = text
            return True

        return False

    def on_stop(self):
        # Persist time + vocab updates even if the window is closed during learning
        try:
            if hasattr(self, "_finalize_learning_time"):
                self._finalize_learning_time()
        except Exception:
            pass

        try:
            if hasattr(self, "persist_knowledge_levels"):
                self.persist_knowledge_levels()
        except Exception:
            pass


