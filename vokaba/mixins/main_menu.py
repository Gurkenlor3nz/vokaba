import os

from kivy.config import Config
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import labels
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

        # ------------------------------------------------------------
        # Shared stats + daily
        # ------------------------------------------------------------
        overall = self._compute_overall_stats()
        stats_cfg = self.config_data.get("stats", {}) or {}
        total_seconds = int(stats_cfg.get("total_learn_time_seconds", 0) or 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        time_str = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"

        learned = int(overall.get("learned_vocab", 0) or 0)
        total_vocab = int(overall.get("total_vocab", 0) or 0)
        total_vocab_safe = max(1, total_vocab)
        progress_percent = (learned / total_vocab_safe) * 100.0
        avg_percent = float(overall.get("avg_knowledge", 0.0) or 0.0) * 100.0

        daily_done, daily_target = self._get_daily_progress_values()
        daily_target = max(1, int(daily_target or 1))
        daily_done = int(daily_done or 0)

        # ------------------------------------------------------------
        # Stack list widget (reused for landscape + portrait)
        # ------------------------------------------------------------
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
                halign="center",
                size_hint_y=None,
                height=dp(120),
            )
            placeholder.bind(size=lambda inst, val: setattr(inst, "text_size", val))
            file_list.add_widget(placeholder)

        stack_scroll = ScrollView(size_hint=(1, 1), do_scroll_y=True)
        file_list.bind(minimum_width=file_list.setter("width"))
        stack_scroll.add_widget(file_list)

        portrait = Window.height > Window.width

        # ------------------------------------------------------------
        # Portrait: single-column scroll layout (fixes "janky" hochkant)
        # ------------------------------------------------------------
        if portrait:
            scroll = ScrollView(size_hint=(1, 1))
            content = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                padding=[dp(18) * pad_mul, dp(18) * pad_mul, dp(18) * pad_mul, dp(18) * pad_mul],
                spacing=dp(14) * pad_mul,
            )
            content.bind(minimum_height=content.setter("height"))
            scroll.add_widget(content)
            self.window.add_widget(scroll)

            # Header row: logo + settings
            header_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(72) * pad_mul, spacing=dp(12) * pad_mul)
            vokaba_logo = self.make_icon_button("assets/vokaba_logo.png", on_press=self.about, size=dp(72) * pad_mul)
            settings_button = self.make_icon_button("assets/settings_icon.png", on_press=self.settings, size=dp(56) * pad_mul)
            header_row.add_widget(vokaba_logo)
            header_row.add_widget(Widget())
            header_row.add_widget(settings_button)
            content.add_widget(header_row)

            # Title
            title = self.make_title_label(getattr(labels, "welcome_text", "Vokaba"), halign="center", size_hint_y=None, height=dp(42) * pad_mul)
            content.add_widget(title)

            # Daily progress card
            daily_card = RoundedCard(orientation="vertical", size_hint=(1, None), padding=dp(16), spacing=dp(8), bg_color=colors["card"])
            daily_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(52), spacing=dp(6))
            self.daily_label_main_menu = self.make_text_label("", halign="center", size_hint_y=None, height=dp(22))
            self.daily_label_main_menu.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
            self.daily_bar_main_menu = ProgressBar(max=daily_target, value=min(daily_done, daily_target), size_hint=(1, None), height=dp(10))
            daily_box.add_widget(self.daily_label_main_menu)
            daily_box.add_widget(self.daily_bar_main_menu)
            daily_card.add_widget(daily_box)
            daily_card.height = daily_box.height + dp(32)
            content.add_widget(daily_card)

            # Stats card (better ordered + bigger)
            stats_card = RoundedCard(orientation="vertical", size_hint=(1, None), padding=dp(16), spacing=dp(10), bg_color=colors["card"])
            stats_title = self.make_title_label(getattr(labels, "main_stats_title", "Statistik"), halign="left", size_hint_y=None, height=dp(34))
            stats_card.add_widget(stats_title)

            line1 = self.make_text_label(
                f"Stapel: {overall.get('stacks', 0)}   •   Vokabeln: {total_vocab}   •   Paare: {overall.get('unique_pairs', 0)}",
                size_hint_y=None,
                height=dp(28),
            )
            line1.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
            stats_card.add_widget(line1)

            line2 = self.make_text_label(
                f"Gelernte: {learned}/{total_vocab_safe} ({progress_percent:.0f} %)   •   Ø Wissen: {avg_percent:.0f} %",
                size_hint_y=None,
                height=dp(28),
            )
            line2.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
            stats_card.add_widget(line2)

            line3 = self.make_text_label(
                f"Gesamtlernzeit: {time_str}   •   Heute: {daily_done}/{daily_target}",
                size_hint_y=None,
                height=dp(28),
            )
            line3.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
            stats_card.add_widget(line3)

            dash_btn = self.make_secondary_button(getattr(labels, "dashboard_title", "Dashboard"), size_hint_y=None, height=dp(52))
            dash_btn.bind(on_press=self.open_dashboard)
            stats_card.add_widget(dash_btn)

            stats_card.height = dp(16) * 2 + stats_title.height + line1.height + line2.height + line3.height + dash_btn.height + dp(10) * 4
            content.add_widget(stats_card)

            # Stack list card
            stacks_card = RoundedCard(orientation="vertical", size_hint=(1, None), padding=dp(12), spacing=dp(8), bg_color=colors["card"])
            stacks_title = self.make_title_label(getattr(labels, "main_menu_stacks_title", "Stapel"), halign="left", size_hint_y=None, height=dp(34))
            stacks_card.add_widget(stacks_title)

            # Take a good chunk of the screen in portrait
            list_h = max(dp(240), min(dp(560), Window.height * 0.45))
            stack_scroll.size_hint = (1, None)
            stack_scroll.height = list_h
            stacks_card.add_widget(stack_scroll)
            stacks_card.height = dp(12) * 2 + stacks_title.height + list_h + dp(8)
            content.add_widget(stacks_card)

            # Actions row
            actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(82), spacing=dp(12))
            learn_text = getattr(labels, "learn_stack_vocab_button_text", "Lernen")
            learn_button = self.make_primary_button(learn_text, size_hint=(1, 1))
            learn_button.bind(on_press=lambda _i: self.learn(stack=None))

            add_stack_button = self.make_secondary_button("+ Stapel", size_hint=(None, 1), width=dp(160))
            add_stack_button.bind(on_press=self.add_stack)

            actions.add_widget(learn_button)
            actions.add_widget(add_stack_button)
            content.add_widget(actions)

            self.recompute_available_modes()
            self._refresh_daily_progress_ui()
            return

        # ------------------------------------------------------------
        # Landscape: keep the original "dashboard-like" layout, but
        # improve stats ordering + vertical centering.
        # ------------------------------------------------------------

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

        # Top-center: welcome + daily bar
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=[0, 120 * pad_mul, 0, 0])
        top_center_box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(dp(700), dp(90)), spacing=dp(8))

        welcome_label = self.make_title_label(getattr(labels, "welcome_text", "Vokaba"), size_hint=(1, None), height=dp(45))
        welcome_label.halign = "center"
        welcome_label.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        progress_box = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(40), spacing=dp(4))
        self.daily_label_main_menu = self.make_text_label("", size_hint_y=None, height=dp(20))
        self.daily_label_main_menu.halign = "center"
        self.daily_label_main_menu.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))

        self.daily_bar_main_menu = ProgressBar(max=daily_target, value=min(daily_done, daily_target), size_hint=(1, None), height=dp(8))
        progress_box.add_widget(self.daily_label_main_menu)
        progress_box.add_widget(self.daily_bar_main_menu)

        top_center_box.add_widget(welcome_label)
        top_center_box.add_widget(progress_box)
        top_center.add_widget(top_center_box)
        self.window.add_widget(top_center)

        # Left side: stats card (centered vertically, more space)
        left_anchor = AnchorLayout(anchor_x="left", anchor_y="center", padding=[40 * pad_mul, 0, 0, 0])
        left_box = BoxLayout(orientation="vertical", size_hint=(0.38, None), height=dp(300), spacing=dp(16))

        stats_card = RoundedCard(orientation="vertical", size_hint=(1, None), padding=dp(16), spacing=dp(12), bg_color=colors["card"])
        stats_card.bind(minimum_height=stats_card.setter("height"))

        stats_title = self.make_title_label(getattr(labels, "main_stats_title", "Statistik"), halign="left", size_hint_y=None, height=dp(34))
        stats_card.add_widget(stats_title)

        s1 = self.make_text_label(
            f"Stapel: {overall.get('stacks', 0)}   •   Vokabeln: {total_vocab}   •   Paare: {overall.get('unique_pairs', 0)}",
            size_hint_y=None, height=dp(34)
        )
        s1.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        stats_card.add_widget(s1)

        s2 = self.make_text_label(
            f"Gelernte: {learned}/{total_vocab_safe} ({progress_percent:.0f} %)   •   Ø Wissen: {avg_percent:.0f} %",
            size_hint_y=None, height=dp(34)
        )
        s2.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        stats_card.add_widget(s2)

        s3 = self.make_text_label(
            f"Gesamtlernzeit: {time_str}   •   Heute: {daily_done}/{daily_target}",
            size_hint_y=None, height=dp(34)
        )
        s3.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        stats_card.add_widget(s3)

        dash_btn = self.make_secondary_button(getattr(labels, "dashboard_title", "Dashboard"), size_hint_y=None, height=dp(52))
        dash_btn.bind(on_press=self.open_dashboard)
        stats_card.add_widget(dash_btn)

        left_box.add_widget(stats_card)
        left_anchor.add_widget(left_box)
        self.window.add_widget(left_anchor)

        # Right side: stack list card
        right_anchor = AnchorLayout(anchor_x="right", anchor_y="center", padding=[0, 200 * pad_mul, 140 * pad_mul, 60 * pad_mul])
        card = RoundedCard(orientation="vertical", size_hint=(0.6, 0.75), padding=dp(12), spacing=dp(8), bg_color=colors["card"])
        card.add_widget(stack_scroll)

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
        learn_button = self.make_primary_button(learn_text, size_hint=(None, None), size=(dp(220), dp(80)), font_size=sp(26))
        learn_button.bind(on_press=lambda _i: self.learn(stack=None))
        bottom_center.add_widget(learn_button)
        self.window.add_widget(bottom_center)

        self._refresh_daily_progress_ui()
