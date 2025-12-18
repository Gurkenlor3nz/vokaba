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
        log("opened dashboard")
        self.reload_config()
        self.window.clear_widgets()

        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        # Back
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        top_right.add_widget(self.make_icon_button("assets/back_button.png", on_press=self.main_menu, size=dp(56)))
        self.window.add_widget(top_right)

        # Title
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=[0, 30 * pad_mul, 0, 0])
        top_center.add_widget(self.make_title_label(getattr(labels, "dashboard_title", "Dashboard"), size_hint=(None, None), size=(dp(400), dp(60))))
        self.window.add_widget(top_center)

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.8), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=dp(4))
        content.bind(minimum_height=content.setter("height"))

        overall = self._compute_overall_stats()
        stats_cfg = self.config_data.get("stats", {}) or {}

        total_seconds = int(stats_cfg.get("total_learn_time_seconds", 0) or 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        time_str = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"

        total_vocab = overall["total_vocab"] or 1
        learned = overall["learned_vocab"]
        progress_percent = (learned / total_vocab) * 100.0
        avg = overall["avg_knowledge"] * 100.0

        content.add_widget(self.make_title_label(getattr(labels, "dashboard_overview_header", "Überblick"), size_hint_y=None, height=dp(40)))
        content.add_widget(self.make_text_label(
            getattr(labels, "dashboard_overview_stats", "Stapel: {stacks}   Vokabeln: {total}   Einzigartige Paare: {unique}")
            .format(stacks=overall["stacks"], total=overall["total_vocab"], unique=overall["unique_pairs"]),
            size_hint_y=None, height=dp(40)
        ))

        content.add_widget(self.make_title_label(getattr(labels, "dashboard_learning_header", "Lernfortschritt"), size_hint_y=None, height=dp(40)))
        content.add_widget(self.make_text_label(
            getattr(labels, "dashboard_learned_progress", "Gelernte Vokabeln: {learned}/{total} ({percent:.0f} %)")
            .format(learned=learned, total=overall["total_vocab"], percent=progress_percent),
            size_hint_y=None, height=dp(40)
        ))
        content.add_widget(self.make_text_label(
            getattr(labels, "dashboard_average_knowledge", "Durchschnittlicher Wissensstand: {avg:.0f} %")
            .format(avg=avg),
            size_hint_y=None, height=dp(40)
        ))
        content.add_widget(self.make_text_label(
            getattr(labels, "dashboard_time_spent", "Gesamtlernzeit: {time}")
            .format(time=time_str),
            size_hint_y=None, height=dp(40)
        ))

        content.add_widget(self.make_text_label(getattr(labels, "dashboard_hint", "Tipp: Lieber regelmäßig kurze Sessions."), size_hint_y=None, height=dp(50)))

        scroll.add_widget(content)
        card.add_widget(scroll)
        center.add_widget(card)
        self.window.add_widget(center)
