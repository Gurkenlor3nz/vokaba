from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.utils import platform

import save

from vokaba.theme.theme_manager import apply_theme_from_config
from vokaba.core.logging_utils import log

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


class VokabaApp(
    App,
    UIFactoryMixin,
    StatsGoalMixin,
    MainMenuMixin,
    SettingsMixin,
    StacksMixin,
    AddStackMixin,
    AddVocabMixin,
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
        if platform in ("win", "linux", "macosx"):
            Config.set("input", "mouse", "mouse,disable_multitouch")

        self.config_data = save.load_settings()
        self.colors = apply_theme_from_config(self.config_data)

        try:
            if platform in ("win", "linux", "macosx"):
                Window.size = (1280, 800)
        except Exception as e:
            log(f"Could not set window size: {e}")

        self.current_focus_input = None
        self.window = FloatLayout()

        # App-level state used by learning autosave
        self.all_vocab_list = []
        self.stack_vocab_lists = {}
        self.stack_meta_map = {}
        self.entry_to_stack_file = {}

        self.main_menu()
        return self.window

    def reload_config(self):
        """Reload config.yml and refresh theme colors."""
        new_cfg = save.load_settings()
        self.config_data.clear()
        self.config_data.update(new_cfg)
        self.colors = apply_theme_from_config(self.config_data)
