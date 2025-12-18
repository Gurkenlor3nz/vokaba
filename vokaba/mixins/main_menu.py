import os
import random

from kivy.config import Config
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView

import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard


class MainMenuMixin:
    """Main menu screen (stack list, stats, global learn button)."""

    def main_menu(self, _instance=None):
        log("opened main menu")
        self.reload_config()
        self._init_daily_goal_defaults()

        self.window.clear_widgets()
        Config.window_icon = "assets/vokaba_icon.png"

        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        colors = self.colors

        # Top-left: logo => about
        top_left = AnchorLayout(anchor_x="left", anchor_y="top", padding=30 * pad_mul)
        vokaba_logo = self.make_icon_button("assets/vokaba_logo.png", on_press=self.about, size=dp(104))
        top_left.add_widget(vokaba_logo)
        self.window.add_widget(top_left)

        # Top-right: settings
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        settings_button = self.make_icon_button("assets/settings_icon.png", on_press=self.settings, size=dp(56))
        top_right.add_widget(settings_button)
        self.window.add_widget(top_right)

        # Stats
        overall = self._compute_overall_stats()
        stats_cfg = self.config_data.get("stats", {}) or {}
        total_seconds = int(stats_cfg.get("total_learn_time_seconds", 0) or 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        time_str = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"

        learned = overall["learned_vocab"]
        total_vocab = overall["total_vocab"] or 1
        progress_percent = (learned / total_vocab) * 100.0
        avg_percent = overall["avg_knowledge"] * 100.0

        daily_done, daily_target = self._get_daily_progress_values()

        # Top-center: welcome + daily bar
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=[0, 120 * pad_mul, 0, 0])
        top_center_box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(dp(700), dp(90)), spacing=dp(8))

        welcome_label = self.make_title_label(labels.welcome_text, size_hint=(1, None), height=dp(45))
        welcome_label.halign = "center"
        welcome_label.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        progress_box = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(40), spacing=dp(4))
        self.daily_label_main_menu = self.make_text_label("", size_hint_y=None, height=dp(20))
        self.daily_label_main_menu.halign = "center"
        self.daily_label_main_menu.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        self.daily_bar_main_menu = ProgressBar(max=max(1, daily_target), value=min(daily_done, daily_target), size_hint=(1, None), height=dp(8))
        progress_box.add_widget(self.daily_label_main_menu)
        progress_box.add_widget(self.daily_bar_main_menu)

        top_center_box.add_widget(welcome_label)
        top_center_box.add_widget(progress_box)
        top_center.add_widget(top_center_box)
        self.window.add_widget(top_center)

        # Left side: stats card
        left_anchor = AnchorLayout(anchor_x="left", anchor_y="top", padding=[40 * pad_mul, 260 * pad_mul, 0, 0])
        left_box = BoxLayout(orientation="vertical", size_hint=(0.35, None), height=dp(260), spacing=dp(24))

        stats_card = RoundedCard(orientation="vertical", size_hint=(1, None), padding=dp(16), spacing=dp(20), bg_color=colors["card"])
        stats_card.bind(minimum_height=stats_card.setter("height"))

        stats_template = getattr(labels, "main_stats_label_template", "Stacks: {stacks}   Vokabeln: {total}   Einzigartige Paare: {unique}")
        stats_label = self.make_text_label(
            stats_template.format(stacks=overall["stacks"], total=overall["total_vocab"], unique=overall["unique_pairs"]),
            size_hint_y=None, height=dp(40)
        )
        stats_label.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        stats_card.add_widget(stats_label)

        progress_template = getattr(
            labels, "main_stats_progress_line",
            "Gelernte Vokabeln: {learned}/{total} ({percent:.0f} %) – Ø Wissen: {avg:.0f} %"
        )
        progress_label = self.make_text_label(
            progress_template.format(learned=learned, total=overall["total_vocab"], percent=progress_percent, avg=avg_percent),
            size_hint_y=None, height=dp(40)
        )
        progress_label.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        stats_card.add_widget(progress_label)

        time_template = getattr(labels, "main_stats_time_and_goal_line", "Gesamtlernzeit: {time}   •   Heutiges Ziel: {done}/{target} Karten")
        time_label = self.make_text_label(time_template.format(time=time_str, done=daily_done, target=daily_target), size_hint_y=None, height=dp(40))
        time_label.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        stats_card.add_widget(time_label)

        # Optional: dashboard entry
        dash_text = getattr(labels, "dashboard_title", "Dashboard")
        dash_btn = self.make_secondary_button(dash_text, size_hint_y=None, height=dp(52))
        dash_btn.bind(on_press=self.open_dashboard)
        stats_card.add_widget(dash_btn)

        left_box.add_widget(stats_card)
        left_anchor.add_widget(left_box)
        self.window.add_widget(left_anchor)

        # Right side: stack list card
        root = self.vocab_root()
        file_list = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        file_list.bind(minimum_height=file_list.setter("height"))

        stacks = []
        for full in self._list_stack_files():
            stacks.append(full)

        for full in sorted(stacks, key=lambda p: os.path.basename(p).lower()):
            name = os.path.basename(full)
            btn = self.make_list_button(name[:-4])
            btn.bind(on_release=lambda _btn, fname=name: self.select_stack(fname))
            file_list.add_widget(btn)

        if len(file_list.children) == 0:
            placeholder = self.make_text_label(
                getattr(labels, "main_menu_no_stacks_hint", "Noch keine Stapel.\nErstelle deinen ersten mit dem + unten rechts."),
                halign="center", size_hint_y=None, height=dp(120),
            )
            placeholder.bind(size=lambda inst, val: setattr(inst, "text_size", val))
            file_list.add_widget(placeholder)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_y=True)
        file_list.bind(minimum_width=file_list.setter("width"))
        scroll.add_widget(file_list)

        right_anchor = AnchorLayout(anchor_x="right", anchor_y="center", padding=[0, 200 * pad_mul, 140 * pad_mul, 60 * pad_mul])
        card = RoundedCard(orientation="vertical", size_hint=(0.6, 0.75), padding=dp(12), spacing=dp(8), bg_color=colors["card"])
        card.add_widget(scroll)

        right_anchor.add_widget(card)
        self.window.add_widget(right_anchor)

        # Bottom-right: add stack
        bottom_right = AnchorLayout(anchor_x="right", anchor_y="bottom", padding=30 * pad_mul)
        add_stack_button = self.make_icon_button("assets/add_stack.png", on_press=self.add_stack, size=dp(64))
        bottom_right.add_widget(add_stack_button)
        self.window.add_widget(bottom_right)

        # Bottom-center: learn random across stacks
        self.recompute_available_modes()
        bottom_center = AnchorLayout(anchor_x="center", anchor_y="bottom", padding=12 * pad_mul)

        learn_text = getattr(labels, "learn_stack_vocab_button_text", "Lernen")
        learn_button = self.make_primary_button(learn_text, size_hint=(None, None), size=(dp(220), dp(80)), font_size=dp(26))
        learn_button.bind(on_press=lambda _i: self.learn(stack=None))
        bottom_center.add_widget(learn_button)
        self.window.add_widget(bottom_center)

        self._refresh_daily_progress_ui()
