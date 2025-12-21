import webbrowser

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

import labels
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard


class AboutDashboardMixin:
    """About screen and dashboard screen."""

    def about(self, _instance=None):
        log("opened about screen")
        self.reload_config()
        self.window.clear_widgets()

        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        # Back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(self.make_icon_button("assets/back_button.png", on_press=self.main_menu, size=dp(56)))
        self.window.add_widget(top_right)

        # Title
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=[0, 30 * pad_mul, 0, 0])
        top_center.add_widget(self.make_title_label(getattr(labels, "about_title", "Über Vokaba"), size_hint=(None, None), size=(dp(400), dp(60))))
        self.window.add_widget(top_center)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.8), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(4))
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(self.make_text_label(getattr(labels, "about_intro", "Vokaba…"), size_hint_y=None, height=dp(160)))

        def h(txt):
            content.add_widget(self.make_title_label(txt, size_hint_y=None, height=dp(40)))

        def b(txt, hgt=dp(80)):
            content.add_widget(self.make_text_label(txt, size_hint_y=None, height=hgt))

        h(getattr(labels, "about_heading_learning", "Was Vokaba unter der Haube macht"))
        b(getattr(labels, "about_bullet_adaptive", "• Adaptive Wiederholung…"), dp(90))
        b(getattr(labels, "about_bullet_modes", "• Lernmodi…"), dp(90))
        b(getattr(labels, "about_bullet_csv", "• CSV…"), dp(90))
        b(getattr(labels, "about_bullet_design", "• Design…"), dp(90))
        b(getattr(labels, "about_alpha_label", "Alpha…"), dp(90))

        h(getattr(labels, "about_heading_discord", "Discord & Support"))
        b(getattr(labels, "about_discord_text", "Feedback…"), dp(90))

        DISCORD_URL = "https://discord.gg/zRRmfgt8Cn"
        btn = self.make_primary_button(getattr(labels, "about_discord_button", "Zum Discord-Server"), size_hint=(1, None), height=dp(50))
        btn.bind(on_press=lambda _i: webbrowser.open(DISCORD_URL))
        content.add_widget(btn)

        content.add_widget(self.make_text_label(f"{getattr(labels, 'about_discord_link_prefix', 'Direkter Link:')} {DISCORD_URL}", size_hint_y=None, height=dp(40)))

        scroll.add_widget(content)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)

    def open_dashboard(self, _instance=None):
        self.reload_config()
        self._init_daily_goal_defaults()

        self.window.clear_widgets()

        colors = self.colors
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        overall = self._compute_overall_stats()
        stats_cfg = self.config_data.get("stats", {}) or {}

        total_seconds = int(stats_cfg.get("total_learn_time_seconds", 0) or 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        time_str = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"

        learned = int(overall.get("learned_vocab", 0) or 0)
        total_vocab = int(overall.get("total_vocab", 0) or 0)
        unique_pairs = int(overall.get("unique_pairs", 0) or 0)
        stacks = int(overall.get("stacks", 0) or 0)
        avg = float(overall.get("avg_knowledge", 0.0) or 0.0) * 100.0

        daily_done, daily_target = self._get_daily_progress_values()
        daily_target = max(1, int(daily_target or 1))
        daily_done = int(daily_done or 0)

        top_left = AnchorLayout(anchor_x="left", anchor_y="top", padding=30 * pad_mul)
        back_btn = self.make_icon_button("assets/back_button.png", on_press=self.main_menu, size=dp(56))
        top_left.add_widget(back_btn)
        self.window.add_widget(top_left)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=dp(24) * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.92, 0.88), padding=dp(16), spacing=dp(10), bg_color=colors["card"])

        title = self.make_title_label(getattr(labels, "dashboard_title", "Dashboard"), size_hint_y=None, height=dp(44))
        title.halign = "center"
        title.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        card.add_widget(title)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=[dp(8), dp(8), dp(8), dp(8)])
        content.bind(minimum_height=content.setter("height"))

        def line(text):
            lbl = self.make_text_label(text, size_hint_y=None, height=dp(40))
            lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
            return lbl

        content.add_widget(line(
            getattr(labels, "dashboard_daily", "Heute: {done}/{target} Karten")
            .format(done=daily_done, target=daily_target)
        ))

        content.add_widget(line(
            getattr(labels, "dashboard_total_vocab", "Gesamtvokabeln: {total}")
            .format(total=total_vocab)
        ))

        content.add_widget(line(
            getattr(labels, "dashboard_learned_vocab", "Gelernte Vokabeln: {learned}/{total}")
            .format(learned=learned, total=max(1, total_vocab))
        ))

        content.add_widget(line(
            getattr(labels, "dashboard_unique_pairs", "Einmalige Paare: {pairs}")
            .format(pairs=unique_pairs)
        ))

        content.add_widget(line(
            getattr(labels, "dashboard_total_stacks", "Stapel: {stacks}")
            .format(stacks=stacks)
        ))

        content.add_widget(line(
            getattr(labels, "dashboard_average_knowledge", "Durchschnittlicher Wissensstand: {avg:.0f} %")
            .format(avg=avg)
        ))

        content.add_widget(line(
            getattr(labels, "dashboard_time_spent", "Gesamtlernzeit: {time}")
            .format(time=time_str)
        ))

        hint = self.make_text_label(getattr(labels, "dashboard_hint", "Tipp: Lieber regelmäßig kurze Sessions."), size_hint_y=None, height=dp(60), halign="center")
        hint.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        content.add_widget(hint)

        scroll.add_widget(content)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)
