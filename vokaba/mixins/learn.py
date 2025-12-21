from __future__ import annotations

import os
import random
import re
import unicodedata
from datetime import datetime, timedelta

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

import labels
import save
from vokaba.core.logging_utils import log
from vokaba.ui.widgets.rounded import RoundedCard, RoundedButton


class LearnMixin:
    """
    Learning system:
      - builds a session list from one stack or all stacks
      - chooses next vocab by SRS due + knowledge weights
      - selects mode by knowledge_level bands
      - supports: flashcards, multiple choice, letter salad, connect pairs,
                 typing, syllable salad
    """

    # ------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------

    def learn(self, stack: str | None = None, _instance=None):
        """
        Start learning. If stack is None: learn across all stacks.
        """
        log(f"entered learn (stack={stack})")
        self.reload_config()
        self._init_daily_goal_defaults()
        self.recompute_available_modes()

        self.window.clear_widgets()
        self.session_start_time = datetime.now()

        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])
        self.learn_area = FloatLayout()
        self.window.add_widget(self.learn_area)

        # header
        self.header_anchor = AnchorLayout(
            anchor_x="center",
            anchor_y="top",
            size_hint=(1, 0.18 if Window.height > Window.width else 0.22),
            pos_hint={"x": 0, "top": 1},
            padding=30 * pad_mul,
        )
        header_box = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(dp(900), dp(110)),
            spacing=dp(6),
        )
        self.header_label = Label(
            text="",
            font_size=sp(int(self.config_data["settings"]["gui"]["title_font_size"])),
            size_hint=(1, None),
            height=dp(40),
            color=self.colors["text"],
        )
        self.header_label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        header_box.add_widget(self.header_label)

        self.daily_label_learn = self.make_text_label("", size_hint_y=None, height=dp(22))
        self.daily_bar_learn = ProgressBar(max=1, value=0, size_hint=(1, None), height=dp(8))
        daily_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(40), spacing=dp(4))
        daily_box.add_widget(self.daily_label_learn)
        daily_box.add_widget(self.daily_bar_learn)
        header_box.add_widget(daily_box)

        self.header_anchor.add_widget(header_box)
        self.learn_area.add_widget(self.header_anchor)

        # content
        self.learn_content = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint=(1, 0.78),
            pos_hint={"x": 0, "y": 0},
            padding=30 * pad_mul,
        )
        self.learn_area.add_widget(self.learn_content)

        # back button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30 * pad_mul)
        back_button = self.make_icon_button("assets/back_button.png", on_press=self.exit_learning, size=dp(56))
        top_right.add_widget(back_button)
        self.learn_area.add_widget(top_right)

        # -----------------------------
        # Daily pool: keep ONE stable vocab pool for the day/stack while the app runs.
        # - If daily goal <= 200: limit pool to that many cards.
        # - If daily goal > 200: include ALL vocab (full variety).
        # -----------------------------
        today = datetime.now().date().isoformat()
        daily_goal = int((self.config_data.get("settings", {}) or {}).get("daily_target_cards", 300) or 300)
        daily_goal = max(1, daily_goal)

        expected_mode = "all" if daily_goal > 200 else "limited"

        # Resolve the stack to a concrete CSV file path (if a stack was requested).
        stack_file = self._resolve_stack_file(stack)
        stack_key = stack_file if stack_file else None

        resume_pool = (
            getattr(self, "_daily_pool_date", None) == today
            and getattr(self, "_daily_pool_stack_key", None) == stack_key
            and getattr(self, "_daily_pool_mode", None) == expected_mode
            and isinstance(getattr(self, "all_vocab_list", None), list)
            and isinstance(getattr(self, "stack_vocab_lists", None), dict)
            and isinstance(getattr(self, "stack_meta_map", None), dict)
            and isinstance(getattr(self, "entry_to_stack_file", None), dict)
            and len(self.all_vocab_list or []) > 0
            and len(self.stack_vocab_lists or {}) > 0
        )

        if resume_pool and expected_mode == "limited":
            try:
                total_at_build = int(getattr(self, "_daily_pool_total_vocab_count", len(self.all_vocab_list)) or len(self.all_vocab_list))
            except Exception:
                total_at_build = len(self.all_vocab_list)
            expected_size = max(1, min(total_at_build, daily_goal))
            if len(self.all_vocab_list) != expected_size:
                resume_pool = False

        if not resume_pool:
            # Build vocab session list (fresh)
            self.all_vocab_list = []
            self.stack_vocab_lists = {}
            self.stack_meta_map = {}
            self.entry_to_stack_file = {}

            if stack is not None and stack_file is None:
                # A stack was requested but could not be resolved. Do not fall back to other stacks.
                self._show_no_vocab_screen()
                return

            if stack_file:
                filenames: list[str] = [stack_file]
            else:
                filenames = []
                for f in self._list_stack_files():
                    if os.path.isabs(f):
                        filenames.append(f)
                    else:
                        root = self.vocab_root()
                        filenames.append(f if f.startswith(root) else os.path.join(root, f))

            for filename in filenames:
                try:
                    data = save.load_vocab(filename)
                except Exception as e:
                    log(f"load_vocab failed for {filename}: {e}")
                    continue

                vocab_list = []
                own, foreign, latin = "German", "English", "Latin"
                latin_active = False

                if isinstance(data, (list, tuple)):
                    if len(data) == 5:
                        vocab_list, own, foreign, latin, latin_active = data
                    elif len(data) == 4:
                        vocab_list, own, foreign, latin = data
                    elif len(data) == 3:
                        vocab_list, own, foreign = data
                    elif len(data) >= 1:
                        vocab_list = data[0]
                elif isinstance(data, dict):
                    vocab_list = data.get("vocab_list", data.get("vocab", [])) or []
                    own = data.get("own_language", own)
                    foreign = data.get("foreign_language", foreign)
                    latin = data.get("latin_language", latin)
                    latin_active = bool(data.get("latin_active", latin_active))
                else:
                    vocab_list = data or []

                self.stack_vocab_lists[filename] = vocab_list
                self.stack_meta_map[filename] = (own, foreign, latin, latin_active)
                for entry in vocab_list:
                    if "knowledge_level" not in entry:
                        entry["knowledge_level"] = 0.0
                    self.entry_to_stack_file[id(entry)] = filename
                    self.all_vocab_list.append(entry)

            random.shuffle(self.all_vocab_list)

            total_vocab_count = len(self.all_vocab_list)

            # Limit pool only for smaller daily goals. Otherwise include all vocab.
            if daily_goal <= 200:
                pool_size = max(1, min(total_vocab_count, daily_goal))
                self.all_vocab_list = self.all_vocab_list[:pool_size]
                self._daily_pool_mode = "limited"
            else:
                self._daily_pool_mode = "all"

            self._daily_pool_date = today
            self._daily_pool_stack_key = stack_key
            self._daily_pool_stack = stack
            self._daily_pool_total_vocab_count = total_vocab_count

        self.max_current_vocab_index = len(self.all_vocab_list)

        if self.max_current_vocab_index == 0:
            self._show_no_vocab_screen()
            return

        # Session counters
        self.session_cards_total = int(self.config_data["settings"].get("session_size", 20) or 20)
        self.session_cards_total = max(1, min(5000, self.session_cards_total))

        if (not resume_pool) or (not bool(getattr(self, "_learn_session_active", False))):
            self.session_cards_done = 0
            self.session_correct = 0
            self.session_wrong = 0
            self._learn_session_active = True
        else:
            # Keep counters when resuming (so a short detour out of learning doesn't reset the session)
            if not hasattr(self, "session_cards_done"):
                self.session_cards_done = 0
            if not hasattr(self, "session_correct"):
                self.session_correct = 0
            if not hasattr(self, "session_wrong"):
                self.session_wrong = 0

        # Learning state
        if (not resume_pool) or (not bool(getattr(self, "_learn_session_active", False))) or (not hasattr(self, "current_vocab_index")):
            self.is_back = False
            self.current_vocab_index = 0  # initialisieren, damit _pick_next_vocab_index funktioniert
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=False)
            self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
            self.self_rating_enabled = True
        else:
            # Resume: keep current vocab + mode when you briefly leave learning.
            self.is_back = False
            try:
                idx = int(getattr(self, "current_vocab_index", 0) or 0)
            except Exception:
                idx = 0
            if not (0 <= idx < len(self.all_vocab_list)):
                self.current_vocab_index = self._pick_next_vocab_index(avoid_current=False)
            if not getattr(self, "learn_mode", None):
                self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
            if not hasattr(self, "self_rating_enabled"):
                self.self_rating_enabled = True

        self._refresh_daily_progress_ui()
        self.show_current_card()

    def _resolve_stack_file(self, stack: str | None) -> str | None:
        """Resolve a stack identifier to an absolute CSV file path inside vocab_root().

        The stack parameter may be:
          - None (meaning: learn across all stacks)
          - a filename like "French.csv"
          - a bare name like "French" (extension will be added)
          - a relative path inside vocab_root()
          - an absolute path to a CSV file
        """
        if not stack:
            return None

        try:
            s = str(stack).strip()
        except Exception:
            return None

        if not s:
            return None

        # Absolute path
        if os.path.isabs(s) and os.path.isfile(s) and s.lower().endswith(".csv"):
            return os.path.abspath(s)

        root = self.vocab_root()

        # Relative path / filename
        cand = os.path.join(root, s)
        if os.path.isfile(cand) and cand.lower().endswith(".csv"):
            return os.path.abspath(cand)

        # Missing extension
        if not s.lower().endswith(".csv"):
            cand2 = os.path.join(root, s + ".csv")
            if os.path.isfile(cand2):
                return os.path.abspath(cand2)

        # Fallback: match by basename against known stacks
        base = os.path.basename(s)
        stem = base[:-4] if base.lower().endswith(".csv") else base

        for f in self._list_stack_files():
            try:
                f_abs = f if os.path.isabs(f) else os.path.join(root, f)
                f_base = os.path.basename(f_abs)
                f_stem = f_base[:-4] if f_base.lower().endswith(".csv") else f_base
                if f_base.lower() == (stem + ".csv").lower() or f_stem.lower() == stem.lower():
                    return os.path.abspath(f_abs)
            except Exception:
                continue

        return None

    def recompute_available_modes(self):
        settings = (self.config_data or {}).get("settings", {}) or {}
        modes_cfg = settings.get("modes", {}) or {}

        order = [
            "front_back",
            "back_front",
            "multiple_choice",
            "connect_pairs",
            "letter_salad",
            "syllable_salad",
            "typing",
        ]
        self.available_modes = [m for m in order if bool(modes_cfg.get(m, False))]

        # Hard fallback
        if not self.available_modes:
            self.available_modes = ["front_back"]


    def _init_daily_goal_defaults(self):
        # settings defaults
        settings = (self.config_data or {}).setdefault("settings", {})
        settings.setdefault("daily_target_cards", 300)
        # How much a single vocab's knowledge_level must improve (accumulated) before
        # it contributes +1 to the daily goal counter.
        settings.setdefault("daily_goal_step", 0.10)

        # stats defaults + daily reset
        stats = (self.config_data or {}).setdefault("stats", {})
        today = datetime.now().date().isoformat()

        if stats.get("daily_progress_date") != today:
            stats["daily_progress_date"] = today
            stats["daily_cards_done"] = 0
            try:
                save.save_settings(self.config_data)
            except Exception as e:
                log(f"save_settings failed in daily reset: {e}")

        stats.setdefault("daily_cards_done", 0)


    def _refresh_daily_progress_ui(self):
        """
        Refresh the daily goal label and progress bar on the learn screen.

        The update is scheduled for the next UI frame to avoid timing issues
        when this is triggered from inside animations/callbacks.
        """

        def _apply(_dt=0):
            try:
                stats = (self.config_data or {}).get("stats", {}) or {}
                settings = (self.config_data or {}).get("settings", {}) or {}

                done = int(stats.get("daily_cards_done", 0) or 0)
                target = int(settings.get("daily_target_cards", 300) or 300)
                target = max(1, target)

                bar = getattr(self, "daily_bar_learn", None)
                if bar is not None:
                    bar.max = target
                    bar.value = max(0, min(done, target))

                lbl = getattr(self, "daily_label_learn", None)
                if lbl is not None:
                    label_text = getattr(labels, "daily_progress_label", "Daily goal")
                    lbl.text = f"{label_text}: {done}/{target}"
            except Exception as e:
                log(f"_refresh_daily_progress_ui failed: {e}")

        try:
            Clock.schedule_once(_apply, 0)
        except Exception:
            _apply(0)

    def _update_daily_progress(self, inc: int = 1):
        """
        Increment the daily goal counter and refresh the UI.

        Args:
            inc: How many completed "daily goal steps" to add.
        """
        try:
            inc = int(inc)
        except Exception:
            inc = 1
        inc = max(0, inc)

        stats = (self.config_data or {}).setdefault("stats", {})
        stats["daily_cards_done"] = int(stats.get("daily_cards_done", 0) or 0) + inc

        try:
            save.save_settings(self.config_data)
        except Exception as e:
            log(f"save_settings failed in _update_daily_progress: {e}")

        self._refresh_daily_progress_ui()

    def _show_no_vocab_screen(self):
        self.window.clear_widgets()
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.8, 0.5), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        msg = self.make_title_label(getattr(labels, "no_vocab_warning", "No vocabulary available."), size_hint_y=None, height=dp(60))
        card.add_widget(msg)

        hint = self.make_text_label(getattr(labels, "no_vocab_hint_create_stack", "Create a stack first."), size_hint_y=None, height=dp(40))
        card.add_widget(hint)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(12))
        back_btn = self.make_secondary_button(getattr(labels, "no_vocab_back_to_menu", "Back to main menu"), size_hint=(0.5, 1))
        back_btn.bind(on_press=lambda _i: self.main_menu())
        new_btn = self.make_primary_button(getattr(labels, "no_vocab_new_stack", "Create new stack"), size_hint=(0.5, 1))
        new_btn.bind(on_press=self.add_stack)
        row.add_widget(back_btn)
        row.add_widget(new_btn)
        card.add_widget(row)

        center.add_widget(card)
        self.window.add_widget(center)

    # ------------------------------------------------------------
    # Card routing
    # ------------------------------------------------------------

    def show_current_card(self):
        self.learn_content.clear_widgets()
        vocab = self._get_current_vocab()
        if vocab is None:
            self._show_no_vocab_screen()
            return

        # Daily goal: reset 'perfect' flag for this card/mini-game
        self._daily_goal_perfect = True

        mode = self.learn_mode

        if mode == "front_back":
            text = vocab.get("own_language", "") if not self.is_back else self._format_backside(vocab)
            self.show_button_card(text, self.flip_card_learn_func)

        elif mode == "back_front":
            text = vocab.get("foreign_language", "") if not self.is_back else vocab.get("own_language", "")
            self.show_button_card(text, self.flip_card_learn_func)

        elif mode == "multiple_choice":
            self.multiple_choice()

        elif mode == "letter_salad":
            self.letter_salad()

        elif mode == "connect_pairs":
            self.connect_pairs_mode()

        elif mode == "typing":
            self.typing_mode()

        elif mode == "syllable_salad":
            self.syllable_salad()

        else:
            self.learn_mode = "front_back"
            self.is_back = False
            self.show_current_card()

    def show_button_card(self, text: str, callback):
        self.learn_content.clear_widgets()
        self.header_label.text = ""

        center = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            padding=30 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]),
        )
        card = RoundedCard(orientation="vertical", size_hint=(0.7, 0.6), padding=dp(12), spacing=dp(8), bg_color=self.colors["card"])

        self.front_side_label = RoundedButton(
            text=text,
            bg_color=self.colors["card"],
            color=self.colors["text"],
            font_size=sp(int(self.config_data["settings"]["gui"]["title_font_size"])),
            size_hint=(1, 0.8),
        )
        self.front_side_label.bind(on_press=callback)
        card.add_widget(self.front_side_label)

        # Self-rating buttons for flashcards
        self.selfrating_box = None
        if self.self_rating_enabled and self.learn_mode in ("front_back", "back_front"):
            self.selfrating_box = BoxLayout(orientation="horizontal", size_hint=(1, 0.2), spacing=dp(8))

            buttons = [
                ("self_rating_very_easy", "very_easy"),
                ("self_rating_easy", "easy"),
                ("self_rating_hard", "hard"),
                ("self_rating_very_hard", "very_hard"),
            ]
            for label_name, quality in buttons:
                t = getattr(labels, label_name, quality)
                btn = self.make_secondary_button(t, size_hint=(0.25, 1))
                btn.bind(on_press=lambda _i, q=quality: self.self_rate_card(q))
                self.selfrating_box.add_widget(btn)

            self.selfrating_box.opacity = 0
            self.selfrating_box.disabled = True
            card.add_widget(self.selfrating_box)

        center.add_widget(card)
        self.learn_content.add_widget(center)

    # ------------------------------------------------------------
    # Flashcard flipping + rating
    # ------------------------------------------------------------

    def flip_card_learn_func(self, _instance=None):
        # Self-rating path: first tap shows back, then user must rate
        if self.self_rating_enabled and self.learn_mode in ("front_back", "back_front"):
            if not self.is_back:
                self.is_back = True
                self.animate_flip_current_card()
            return

        # Legacy path
        if not self.is_back:
            self.is_back = True
            self.animate_flip_current_card()
            return

        self._advance_to_next()

    def animate_flip_current_card(self):
        if not hasattr(self, "front_side_label"):
            self.show_current_card()
            return

        lbl = self.front_side_label
        vocab = self._get_current_vocab()
        if vocab is None:
            return

        if self.learn_mode == "front_back":
            new_text = self._format_backside(vocab)
        elif self.learn_mode == "back_front":
            new_text = vocab.get("own_language", "")
        else:
            new_text = lbl.text

        def set_text(*_a):
            lbl.text = new_text
            if self.self_rating_enabled and self.learn_mode in ("front_back", "back_front") and self.selfrating_box is not None:
                self.selfrating_box.disabled = False
                self.selfrating_box.opacity = 1
            Animation(opacity=1, duration=0.15).start(lbl)

        anim_out = Animation(opacity=0, duration=0.15)
        anim_out.bind(on_complete=set_text)
        anim_out.start(lbl)

    def self_rate_card(self, quality: str):
        vocab = self._get_current_vocab()
        if vocab is None:
            return

        # knowledge deltas
        if quality == "very_easy":
            delta = getattr(labels, "knowledge_delta_self_very_easy", 0.09)
            q_val, correct = 1.0, True
        elif quality == "easy":
            delta = getattr(labels, "knowledge_delta_self_easy", 0.05)
            q_val, correct = 0.75, True
        elif quality == "hard":
            delta = getattr(labels, "knowledge_delta_self_hard", -0.01)
            q_val, correct = 0.4, False
        else:
            delta = getattr(labels, "knowledge_delta_self_very_hard", -0.08)
            q_val, correct = 0.1, False

        self._adjust_knowledge_level(vocab, delta)
        self.update_srs(vocab, was_correct=correct, quality=q_val)

        if self._register_session_step(was_correct=correct):
            return

        self._advance_to_next()

    # ------------------------------------------------------------
    # Session tracking
    # ------------------------------------------------------------

    def _register_session_step(self, was_correct: bool | None = None, steps: int = 1) -> bool:
        try:
            steps = int(steps)
        except Exception:
            steps = 1
        steps = max(1, steps)

        self.session_cards_done += steps

        # Daily goal: only award points if the user was correct AND had no mistakes on this card/mini-game.
        if was_correct is True:
            self.session_correct += steps
            if getattr(self, "_daily_goal_perfect", True):
                try:
                    self._update_daily_progress(steps)
                except Exception:
                    pass
        elif was_correct is False:
            self.session_wrong += steps
            # Once a card is marked as incorrect, never award daily points for it.
            self._daily_goal_perfect = False

        if self.session_cards_done >= self.session_cards_total:
            self.show_session_summary()
            return True
        return False

    def show_session_summary(self):
        self.learn_content.clear_widgets()
        pad_mul = float(self.config_data["settings"]["gui"]["padding_multiplicator"])

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=40 * pad_mul)
        card = RoundedCard(orientation="vertical", size_hint=(0.8, 0.6), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        title = self.make_title_label(getattr(labels, "session_summary_title", "Session finished"), size_hint_y=None, height=dp(40))
        card.add_widget(title)

        txt = getattr(
            labels,
            "session_summary_text",
            "You completed {done} cards.\nCorrect: {correct}   Wrong/hard: {wrong}\nSession target: {goal} cards.",
        )
        body = self.make_text_label(
            txt.format(done=self.session_cards_done, correct=self.session_correct, wrong=self.session_wrong, goal=self.session_cards_total),
            size_hint_y=None,
            height=dp(120),
        )
        card.add_widget(body)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(12))
        back_btn = self.make_secondary_button(getattr(labels, "session_summary_back_button", "Back to main menu"), size_hint=(0.5, 1))
        cont_btn = self.make_primary_button(getattr(labels, "session_summary_continue_button", "Weiterlernen"), size_hint=(0.5, 1))

        def cont(*_a):
            self.session_cards_done = 0
            self.session_correct = 0
            self.session_wrong = 0
            self.show_current_card()

        back_btn.bind(on_press=lambda _i: self.exit_learning())
        cont_btn.bind(on_press=cont)

        row.add_widget(back_btn)
        row.add_widget(cont_btn)
        card.add_widget(row)

        center.add_widget(card)
        self.learn_content.add_widget(center)

    # ------------------------------------------------------------
    # Persistence + exit
    # ------------------------------------------------------------

    def _persist_single_entry(self, vocab: dict):
        fn = getattr(save, "persist_single_entry", None)
        if not callable(fn):
            return
        try:
            # New signature (stack-aware persistence).
            fn(vocab, self.stack_vocab_lists, self.stack_meta_map, self.entry_to_stack_file)
        except TypeError:
            # Old signature: persist_single_entry(vocab)
            try:
                fn(vocab)
            except Exception as e:
                log(f"persist_single_entry failed (fallback): {e}")
        except Exception as e:
            log(f"persist_single_entry failed: {e}")

    def persist_knowledge_levels(self):
        fn = getattr(save, "persist_all_stacks", None)
        if callable(fn):
            try:
                fn(self.stack_vocab_lists, self.stack_meta_map)
                return
            except TypeError:
                # Old signature without args
                try:
                    fn()
                    return
                except Exception as e:
                    log(f"persist_all_stacks failed (fallback): {e}")
            except Exception as e:
                log(f"persist_all_stacks failed: {e}")

        # letzte Fallback-Option: versuche save_vocab pro Datei (falls vorhanden)
        save_vocab = getattr(save, "save_vocab", None)
        if callable(save_vocab):
            try:
                for filename, vocab_list in (self.stack_vocab_lists or {}).items():
                    own, foreign, latin, latin_active = self.stack_meta_map.get(filename,
                                                                                ("German", "English", "Latin",
                                                                                 False))
                    save_vocab(filename, vocab_list, own, foreign, latin, latin_active)
            except Exception as e:
                log(f"persist via save_vocab failed: {e}")

    def exit_learning(self, _instance=None):
        try:
            self.persist_knowledge_levels()
        except Exception:
            pass

        # Update learning time
        try:
            start = getattr(self, "session_start_time", None)
            if start is not None:
                seconds = max(0, int((datetime.now() - start).total_seconds()))
                stats_cfg = self.config_data.setdefault("stats", {})
                stats_cfg["total_learn_time_seconds"] = int(stats_cfg.get("total_learn_time_seconds", 0) or 0) + seconds
                save.save_settings(self.config_data)
        except Exception as e:
            log(f"learning time update failed: {e}")

        self.main_menu()

    # ------------------------------------------------------------
    # Vocab selection and mode choice
    # ------------------------------------------------------------

    def _get_current_vocab(self):
        if not self.all_vocab_list:
            return None
        if not (0 <= self.current_vocab_index < len(self.all_vocab_list)):
            self.current_vocab_index = 0
        return self.all_vocab_list[self.current_vocab_index]

    def _compute_vocab_weight(self, entry: dict) -> float:
        try:
            lvl = float(entry.get("knowledge_level", 0.0) or 0.0)
        except Exception:
            lvl = 0.0
        lvl = max(0.0, min(1.0, lvl))
        w = 1.0 - lvl
        return max(0.05, w)

    def _pick_next_vocab_index(self, avoid_current=True) -> int:
        if not self.all_vocab_list:
            return 0
        n = len(self.all_vocab_list)
        if n <= 1:
            return 0

        now = datetime.now()
        due_indices = []
        for idx, e in enumerate(self.all_vocab_list):
            due_raw = e.get("srs_due")
            if not due_raw:
                continue
            try:
                due = datetime.fromisoformat(str(due_raw))
            except Exception:
                continue
            if due <= now:
                due_indices.append(idx)

        candidates = due_indices if due_indices else list(range(n))
        cur = getattr(self, "current_vocab_index", 0)

        if avoid_current and len(candidates) > 1 and cur in candidates:
            candidates = [i for i in candidates if i != cur]
        if not candidates:
            candidates = [i for i in range(n) if i != cur] or [0]

        weights = [self._compute_vocab_weight(self.all_vocab_list[i]) for i in candidates]
        total = sum(weights)
        if total <= 0:
            return random.choice(candidates)

        r = random.random() * total
        acc = 0.0
        for idx, w in zip(candidates, weights):
            acc += w
            if r <= acc:
                return idx
        return candidates[-1]

    def _get_mode_pool_for_level(self, level: float):
        lvl = max(0.0, min(1.0, float(level or 0.0)))
        if lvl <= 0.35:
            base = {"front_back", "back_front", "multiple_choice", "connect_pairs"}
        elif lvl <= 0.60:
            base = {"multiple_choice", "connect_pairs", "letter_salad", "syllable_salad"}
        else:
            base = {"multiple_choice", "connect_pairs", "letter_salad", "syllable_salad", "typing"}

        candidates = [m for m in getattr(self, "available_modes", ["front_back"]) if m in base]
        if not candidates:
            candidates = list(getattr(self, "available_modes", ["front_back"]))
        return candidates

    def _choose_mode_for_vocab(self, vocab: dict | None) -> str:
        if not vocab:
            return random.choice(getattr(self, "available_modes", ["front_back"]))
        pool = self._get_mode_pool_for_level(float(vocab.get("knowledge_level", 0.0) or 0.0))
        return random.choice(pool) if pool else "front_back"

    def _advance_to_next(self):
        if self.max_current_vocab_index > 1:
            self.current_vocab_index = self._pick_next_vocab_index(avoid_current=True)
        else:
            self.current_vocab_index = 0
        self.is_back = False
        self.learn_mode = self._choose_mode_for_vocab(self._get_current_vocab())
        self.show_current_card()

    # ------------------------------------------------------------
    # Knowledge + SRS
    # ------------------------------------------------------------

    def _adjust_knowledge_level(self, vocab: dict, delta: float, persist_immediately=True):
        if not vocab:
            return

        try:
            cur = float(vocab.get("knowledge_level", 0.0) or 0.0)
        except Exception:
            cur = 0.0
        try:
            d = float(delta)
        except Exception:
            d = 0.0

        new = max(0.0, min(1.0, cur + d))
        vocab["knowledge_level"] = new

        if persist_immediately:
            self._persist_single_entry(vocab)

    def update_srs(self, vocab: dict, was_correct: bool, quality: float = 0.5):
        if not vocab:
            return
        now = datetime.now()

        try:
            streak = int(vocab.get("srs_streak", 0) or 0)
        except Exception:
            streak = 0

        streak = streak + 1 if was_correct else 0
        vocab["srs_streak"] = streak
        vocab["srs_last_seen"] = now.isoformat()

        base = [1, 2, 4, 7, 14, 30]
        idx = min(streak, len(base) - 1)
        days = base[idx]

        try:
            q = float(quality)
        except Exception:
            q = 0.5
        q = max(0.0, min(1.0, q))
        factor = 0.75 + 0.5 * q
        days = max(1, int(days * factor))

        due = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days)
        vocab["srs_due"] = due.isoformat()

        self._persist_single_entry(vocab)

    # ------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------

    def _format_backside(self, vocab: dict) -> str:
        back = vocab.get("foreign_language", "") or ""
        info = vocab.get("info", "") or ""
        latin = vocab.get("latin_language", "") or ""
        if latin.strip():
            return f"{back}\n\n{info}\n\n{latin}"
        return f"{back}\n\n{info}"

    def _format_answer_lines(self, vocab: dict) -> str:
        foreign = (vocab.get("foreign_language") or "").strip()
        latin = (vocab.get("latin_language") or "").strip()
        info = (vocab.get("info") or "").strip()
        lines = []
        if foreign:
            lines.append(foreign)
        if latin:
            lines.append(latin)
        if info:
            lines.append(info)
        return "\n".join(lines)

    # ------------------------------------------------------------
    # Multiple choice
    # ------------------------------------------------------------

    def multiple_choice(self):
        self.learn_content.clear_widgets()
        vocab = self._get_current_vocab()
        if vocab is None:
            return

        correct = vocab
        pool = [w for w in self.all_vocab_list if w is not correct]
        wrong = random.sample(pool, min(4, len(pool))) if pool else []
        answers = wrong + [correct]

        # ensure uniqueness by pair
        uniq = []
        seen = set()
        for a in answers:
            key = (a.get("own_language", ""), a.get("foreign_language", ""))
            if key not in seen:
                uniq.append(a)
                seen.add(key)
        answers = uniq
        if correct not in answers:
            answers.append(correct)
        random.shuffle(answers)

        self.header_label.color = self.colors["text"]
        self.header_label.text = correct.get("own_language", "")

        self.multiple_choice_locked = False

        scroll = ScrollView(size_hint=(1, 1))
        layout = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[
                50 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]),
                80 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]),
                120 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]),
                50 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]),
            ],
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter("height"))

        for opt in answers:
            btn = RoundedButton(
                text=self._format_answer_lines(opt),
                bg_color=self.colors["card"],
                color=self.colors["text"],
                font_size=sp(int(self.config_data["settings"]["gui"]["title_font_size"])),
                size_hint=(1, None),
                height=dp(70),
            )
            btn.bind(on_press=lambda inst, choice=opt: self.multiple_choice_func(correct, choice, inst))
            layout.add_widget(btn)

        scroll.add_widget(layout)
        self.learn_content.add_widget(scroll)

    def multiple_choice_func(self, correct_vocab: dict, chosen: dict, button):
        if self.multiple_choice_locked:
            return
        self.multiple_choice_locked = True

        is_correct = (chosen is correct_vocab) or (
            chosen.get("own_language", "") == correct_vocab.get("own_language", "")
            and chosen.get("foreign_language", "") == correct_vocab.get("foreign_language", "")
        )

        if is_correct:
            delta = getattr(labels, "knowledge_delta_multiple_choice_correct", 0.07)
        else:
            delta = getattr(labels, "knowledge_delta_multiple_choice_wrong", -0.06)

        self._adjust_knowledge_level(correct_vocab, delta)
        self.update_srs(correct_vocab, was_correct=is_correct, quality=1.0 if is_correct else 0.0)

        if is_correct:
            if isinstance(button, RoundedButton):
                button.set_bg_color(self.colors["success"])
            Clock.schedule_once(lambda _dt: self._after_correct_generic(True), 0.25)
        else:
            self._daily_goal_perfect = False
            if isinstance(button, RoundedButton):
                button.set_bg_color(self.colors["danger"])

            def unlock(_dt):
                if isinstance(button, RoundedButton):
                    button.set_bg_color(self.colors["card"])
                self.multiple_choice_locked = False

            Clock.schedule_once(unlock, 0.35)

    def _after_correct_generic(self, was_correct=True, steps=1):
        if self._register_session_step(was_correct=was_correct, steps=steps):
            self.multiple_choice_locked = False
            return
        self._advance_to_next()
        self.multiple_choice_locked = False

    # ------------------------------------------------------------
    # Connect pairs (5 pairs)
    # ------------------------------------------------------------

    def connect_pairs_mode(self):
        self.learn_content.clear_widgets()

        uniq = {}
        for e in self.all_vocab_list:
            key = (e.get("own_language", ""), e.get("foreign_language", ""))
            if key not in uniq:
                uniq[key] = e
        items = list(uniq.values())
        if len(items) < 5:
            self.learn_mode = "front_back"
            self.show_current_card()
            return

        self.connect_pairs_items = random.sample(items, 5)
        self.connect_pairs_left_buttons = {}
        self.connect_pairs_right_buttons = {}
        self.connect_pairs_selected_left = None
        self.connect_pairs_selected_right = None
        self.connect_pairs_matched_count = 0
        self.connect_pairs_locked = False

        self.header_label.text = ""

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=20 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]))
        card = RoundedCard(orientation="vertical", size_hint=(0.9, 0.7), padding=dp(16), spacing=dp(16), bg_color=self.colors["card"])

        header = self.make_text_label(getattr(labels, "connect_pairs_header", "Match the correct pairs"), size_hint_y=None, height=dp(30))
        card.add_widget(header)

        row = BoxLayout(orientation="horizontal", spacing=dp(24))
        left_col = BoxLayout(orientation="vertical", spacing=dp(8))
        right_col = BoxLayout(orientation="vertical", spacing=dp(8))

        for entry in self.connect_pairs_items:
            btn = RoundedButton(
                text=entry.get("own_language", ""),
                bg_color=self.colors["card"],
                color=self.colors["text"],
                size_hint=(1, None),
                height=dp(48),
                font_size=sp(int(self.config_data["settings"]["gui"]["text_font_size"])),
            )
            btn._matched = False
            btn.bind(on_press=lambda inst, e=entry: self.on_connect_left_pressed(inst, e))
            self.connect_pairs_left_buttons[btn] = entry
            left_col.add_widget(btn)

        shuffled = self.connect_pairs_items[:]
        random.shuffle(shuffled)
        for entry in shuffled:
            btn = RoundedButton(
                text=self._format_answer_lines(entry),
                bg_color=self.colors["card"],
                color=self.colors["text"],
                size_hint=(1, None),
                height=dp(48),
                font_size=sp(int(self.config_data["settings"]["gui"]["text_font_size"])),
            )
            btn._matched = False
            btn.bind(on_press=lambda inst, e=entry: self.on_connect_right_pressed(inst, e))
            self.connect_pairs_right_buttons[btn] = entry
            right_col.add_widget(btn)

        row.add_widget(left_col)
        row.add_widget(right_col)
        card.add_widget(row)

        center.add_widget(card)
        self.learn_content.add_widget(center)

    def _clear_connect_selection(self, side="both"):
        if side in ("left", "both") and self.connect_pairs_selected_left and not getattr(self.connect_pairs_selected_left, "_matched", False):
            self.connect_pairs_selected_left.set_bg_color(self.colors["card"])
            self.connect_pairs_selected_left = None
        if side in ("right", "both") and self.connect_pairs_selected_right and not getattr(self.connect_pairs_selected_right, "_matched", False):
            self.connect_pairs_selected_right.set_bg_color(self.colors["card"])
            self.connect_pairs_selected_right = None

    def on_connect_left_pressed(self, button, _entry):
        if self.connect_pairs_locked or getattr(button, "_matched", False):
            return
        if self.connect_pairs_selected_left is not button:
            self._clear_connect_selection("left")
            self.connect_pairs_selected_left = button
            button.set_bg_color(self.colors["card_selected"])
        if self.connect_pairs_selected_right:
            self._check_connect_pair()

    def on_connect_right_pressed(self, button, _entry):
        if self.connect_pairs_locked or getattr(button, "_matched", False):
            return
        if self.connect_pairs_selected_right is not button:
            self._clear_connect_selection("right")
            self.connect_pairs_selected_right = button
            button.set_bg_color(self.colors["card_selected"])
        if self.connect_pairs_selected_left:
            self._check_connect_pair()

    def _check_connect_pair(self):
        left_btn = self.connect_pairs_selected_left
        right_btn = self.connect_pairs_selected_right
        if not left_btn or not right_btn:
            return

        left_entry = self.connect_pairs_left_buttons.get(left_btn)
        right_entry = self.connect_pairs_right_buttons.get(right_btn)
        if left_entry is None or right_entry is None:
            return

        left_key = (left_entry.get("own_language", ""), left_entry.get("foreign_language", ""))
        right_key = (right_entry.get("own_language", ""), right_entry.get("foreign_language", ""))

        if left_key == right_key:
            delta = getattr(labels, "knowledge_delta_connect_pairs_correct_word", 0.06)
            self._adjust_knowledge_level(left_entry, delta)
            self._adjust_knowledge_level(right_entry, delta)

            self.connect_pairs_locked = True
            for btn in (left_btn, right_btn):
                btn._matched = True
                btn.set_bg_color(self.colors["success"])
                Animation(opacity=0.95, duration=0.1).start(btn)

            self.connect_pairs_selected_left = None
            self.connect_pairs_selected_right = None
            self.connect_pairs_matched_count += 1
            self.connect_pairs_locked = False

            if self.connect_pairs_matched_count >= len(self.connect_pairs_items):
                Clock.schedule_once(lambda _dt: self._connect_pairs_finish(), 0.3)
        else:
            self._daily_goal_perfect = False
            delta_wrong = getattr(labels, "knowledge_delta_connect_pairs_wrong_word", -0.074)
            self._adjust_knowledge_level(left_entry, delta_wrong)
            self._adjust_knowledge_level(right_entry, delta_wrong)

            self.connect_pairs_locked = True
            for btn in (left_btn, right_btn):
                btn.set_bg_color(self.colors["danger"])
                Animation(opacity=0.6, duration=0.1).start(btn)

            def reset(_dt):
                if not getattr(left_btn, "_matched", False):
                    left_btn.set_bg_color(self.colors["card"])
                if not getattr(right_btn, "_matched", False):
                    right_btn.set_bg_color(self.colors["card"])
                self.connect_pairs_selected_left = None
                self.connect_pairs_selected_right = None
                self.connect_pairs_locked = False

            Clock.schedule_once(reset, 0.3)

    def _connect_pairs_finish(self):
        items = getattr(self, "connect_pairs_items", []) or []
        for e in items:
            self.update_srs(e, was_correct=True, quality=1.0)

        steps = len(items) if items else 1
        if self._register_session_step(was_correct=True, steps=steps):
            return
        self._advance_to_next()

    # ------------------------------------------------------------
    # Letter salad (click letters in order)
    # ------------------------------------------------------------

    def _clean_target_for_salad(self, raw: str) -> str:
        if not raw:
            return ""
        out = []
        in_parens = False
        for ch in raw:
            if ch == "(":
                in_parens = True
                continue
            if ch == ")":
                in_parens = False
                continue
            if in_parens or ch.isspace():
                continue
            out.append(ch)
        return "".join(out)

    def letter_salad(self):
        self.learn_content.clear_widgets()
        vocab = self._get_current_vocab()
        if vocab is None:
            return

        self.header_label.text = ""

        raw_target = (vocab.get("foreign_language", "") or "").strip()
        target = self._clean_target_for_salad(raw_target)
        if not target:
            self._advance_to_next()
            return

        letters = list(target)
        scrambled = letters[:]
        random.shuffle(scrambled)

        self.letter_salad_vocab = vocab
        self.letter_salad_target = target
        self.letter_salad_progress = 0
        self.letter_salad_typed = ""

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=30 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]))
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.55), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        card.add_widget(self.make_title_label(vocab.get("own_language", ""), size_hint_y=None, height=dp(40)))

        latin = (vocab.get("latin_language") or "").strip()
        if latin:
            card.add_widget(self.make_text_label(latin, size_hint_y=None, height=dp(30)))

        card.add_widget(self.make_text_label(getattr(labels, "letter_salad_instruction", "Tap the letters in order."), size_hint_y=None, height=dp(30)))

        self.letter_salad_progress_label = self.make_title_label("", size_hint_y=None, height=dp(40))
        card.add_widget(self.letter_salad_progress_label)

        from kivy.uix.gridlayout import GridLayout

        cols = max(1, min(len(scrambled), 10))
        grid = GridLayout(cols=cols, spacing=dp(8), size_hint_y=None, padding=(0, dp(4)))
        grid.bind(minimum_height=grid.setter("height"))

        self.letter_salad_buttons = []
        for ch in scrambled:
            btn = RoundedButton(
                text=ch,
                bg_color=self.colors["card"],
                color=self.colors["text"],
                font_size=sp(int(self.config_data["settings"]["gui"]["title_font_size"])),
                size_hint=(None, None),
                size=(dp(56), dp(56)),
            )
            btn.bind(on_press=self.letter_salad_letter_pressed)
            self.letter_salad_buttons.append(btn)

            wrapper = RoundedCard(orientation="vertical", size_hint=(None, None), padding=dp(3), bg_color=self.colors["card_selected"])
            wrapper.add_widget(btn)
            grid.add_widget(wrapper)

        letters_scroll = ScrollView(size_hint=(1, None), height=dp(210), do_scroll_y=True, do_scroll_x=True)
        letters_scroll.add_widget(grid)
        card.add_widget(letters_scroll)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(12))
        skip_btn = self.make_secondary_button(getattr(labels, "letter_salad_skip", "Skip"), size_hint=(0.5, 1))
        reshuffle_btn = self.make_secondary_button(getattr(labels, "letter_salad_reshuffle", "Reshuffle"), size_hint=(0.5, 1))
        skip_btn.bind(on_press=self.letter_salad_skip)
        reshuffle_btn.bind(on_press=lambda _i: self.letter_salad())
        row.add_widget(skip_btn)
        row.add_widget(reshuffle_btn)
        card.add_widget(row)

        center.add_widget(card)
        self.learn_content.add_widget(center)

    def letter_salad_letter_pressed(self, button, _instance=None):
        target = self.letter_salad_target
        idx = self.letter_salad_progress
        vocab = self.letter_salad_vocab

        if idx >= len(target) or button.disabled:
            return

        expected = target[idx]
        clicked = (button.text or "").strip()

        if clicked == expected:
            button.set_bg_color(self.colors["success"])
            button.disabled = True
            self._adjust_knowledge_level(vocab, getattr(labels, "knowledge_delta_letter_salad_per_correct_letter", 0.01))

            self.letter_salad_progress += 1
            self.letter_salad_typed += clicked
            self.letter_salad_progress_label.text = self.letter_salad_typed

            if self.letter_salad_progress >= len(target):
                Clock.schedule_once(lambda _dt: self._letter_salad_finish(), 0.3)
        else:
            self._daily_goal_perfect = False
            self._adjust_knowledge_level(vocab, getattr(labels, "knowledge_delta_letter_salad_wrong_letter", -0.025))
            button.set_bg_color(self.colors["danger"])
            Clock.schedule_once(lambda _dt, b=button: b.set_bg_color(self.colors["card"]), 0.25)

    def _letter_salad_finish(self):
        vocab = self.letter_salad_vocab
        if len(self.letter_salad_target) <= 4:
            self._adjust_knowledge_level(vocab, getattr(labels, "knowledge_delta_letter_salad_short_word_bonus", 0.02))
        self.update_srs(vocab, was_correct=True, quality=1.0)
        if self._register_session_step(was_correct=True):
            return
        self._advance_to_next()

    def letter_salad_skip(self, _instance=None):
        vocab = self.letter_salad_vocab
        self.update_srs(vocab, was_correct=False, quality=0.0)
        if self._register_session_step(was_correct=False):
            return
        self._advance_to_next()

    # ------------------------------------------------------------
    # Typing mode (answer typed)
    # ------------------------------------------------------------

    def _strip_accents(self, ch: str) -> str:
        decomposed = unicodedata.normalize("NFD", ch)
        return "".join(c for c in decomposed if not unicodedata.combining(c))

    def _remove_parenthetical(self, text: str) -> str:
        if not text:
            return ""
        out = []
        in_parens = False
        for ch in text:
            if ch == "(":
                in_parens = True
                continue
            if ch == ")":
                in_parens = False
                continue
            if not in_parens:
                out.append(ch)
        return "".join(out)

    def _normalize_for_compare(self, text: str) -> str:
        if not text:
            return ""
        no_par = self._remove_parenthetical(text)
        letters = []
        for ch in no_par:
            if ch.isalpha():
                letters.append(self._strip_accents(ch).lower())
        return "".join(letters)

    def _extract_main_lexeme(self, text: str) -> str:
        if not text:
            return ""
        no_par = self._remove_parenthetical(text).strip()
        parts = no_par.split()
        return parts[-1] if parts else no_par

    def _is_correct_typed_answer(self, typed: str, vocab: dict) -> bool:
        foreign = vocab.get("foreign_language", "") or ""
        parts = re.split(r"[;,/]", foreign)
        candidates = [p.strip() for p in parts if p.strip()] or [foreign]

        typed_norm = self._normalize_for_compare(typed)
        if not typed_norm:
            return False

        for cand in candidates:
            full = self._normalize_for_compare(cand)
            main = self._normalize_for_compare(self._extract_main_lexeme(cand))
            if typed_norm == full or typed_norm == main:
                return True
        return False

    def typing_mode(self):
        self.learn_content.clear_widgets()
        vocab = self._get_current_vocab()
        if vocab is None:
            return

        self.header_label.text = ""

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=30 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]))
        card = RoundedCard(orientation="vertical", size_hint=(0.85, 0.55), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        card.add_widget(self.make_title_label(vocab.get("own_language", ""), size_hint_y=None, height=dp(40)))
        card.add_widget(self.make_text_label(getattr(labels, "typing_mode_instruction", "Type the correct translation:"), size_hint_y=None, height=dp(30)))

        self.typing_input = self.style_textinput(TextInput(multiline=False, size_hint=(1, None), height=self.get_textinput_height()))
        self.typing_input.bind(on_text_validate=self.typing_check_answer)
        card.add_widget(self.typing_input)
        card.add_widget(self.create_accent_bar())

        self.typing_feedback_label = self.make_text_label("", size_hint_y=None, height=dp(110))
        self.typing_feedback_label.markup = True
        card.add_widget(self.typing_feedback_label)

        self.typing_selfrating_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        if self.self_rating_enabled:
            for label_name, quality in [
                ("self_rating_very_easy", "very_easy"),
                ("self_rating_easy", "easy"),
                ("self_rating_hard", "hard"),
                ("self_rating_very_hard", "very_hard"),
            ]:
                btn = self.make_secondary_button(
                    getattr(labels, label_name, quality),
                    size_hint=(0.25, 1),
                    font_size=sp(int(self.config_data["settings"]["gui"]["text_font_size"])),
                )
                btn.bind(on_press=lambda _i, q=quality: self.self_rate_card(q))
                self.typing_selfrating_box.add_widget(btn)

        self.typing_selfrating_box.opacity = 0
        self.typing_selfrating_box.disabled = True
        card.add_widget(self.typing_selfrating_box)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(12))
        check_btn = self.make_primary_button(getattr(labels, "typing_mode_check", "Check"), size_hint=(0.5, 1))
        skip_btn = self.make_secondary_button(getattr(labels, "typing_mode_skip", "Skip"), size_hint=(0.5, 1))
        check_btn.bind(on_press=self.typing_check_answer)
        skip_btn.bind(on_press=self.typing_skip)
        row.add_widget(check_btn)
        row.add_widget(skip_btn)
        card.add_widget(row)

        center.add_widget(card)
        self.learn_content.add_widget(center)
        Clock.schedule_once(lambda _dt: setattr(self.typing_input, "focus", True), 0.05)

    def typing_check_answer(self, _instance=None):
        vocab = self._get_current_vocab()
        if vocab is None:
            return
        user = (self.typing_input.text or "")
        if not user.strip():
            self.typing_feedback_label.text = getattr(labels, "typing_mode_empty", "Please enter an answer.")
            return

        is_correct = self._is_correct_typed_answer(user, vocab)
        if is_correct:
            self._adjust_knowledge_level(vocab, getattr(labels, "knowledge_delta_typing_correct", 0.093))
            self.update_srs(vocab, was_correct=True, quality=1.0)
            self.typing_feedback_label.color = self.colors["success"]
            self.typing_feedback_label.text = getattr(labels, "typing_mode_correct", "Correct!")
            self.typing_selfrating_box.disabled = False
            self.typing_selfrating_box.opacity = 1

            if self._register_session_step(was_correct=True):
                return
            Clock.schedule_once(lambda _dt: self._advance_to_next(), 0.35)
        else:
            self._daily_goal_perfect = False
            per_char = getattr(labels, "knowledge_delta_typing_wrong_per_char", -0.01)
            self._adjust_knowledge_level(vocab, per_char * len(user.strip()))
            self.update_srs(vocab, was_correct=False, quality=0.0)
            self.typing_feedback_label.color = self.colors["text"]
            self.typing_feedback_label.text = (
                f"{getattr(labels, 'typing_mode_wrong', 'Not quite. Correct answer:')}\n"
                f"{self._extract_main_lexeme(vocab.get('foreign_language', '') or '')}"
            )

    def typing_skip(self, _instance=None):
        vocab = self._get_current_vocab()
        if vocab is not None:
            self.update_srs(vocab, was_correct=False, quality=0.0)
        if self._register_session_step(was_correct=False):
            return
        self._advance_to_next()

    # ------------------------------------------------------------
    # Syllable salad (chunks)
    # ------------------------------------------------------------

    def _clean_target_for_syllables(self, raw: str) -> str:
        if not raw:
            return ""
        out = []
        in_parens = False
        for ch in raw:
            if ch == "(":
                in_parens = True
                continue
            if ch == ")":
                in_parens = False
                continue
            if in_parens:
                continue
            out.append(ch)
        return "".join(out)

    def _split_into_syllable_chunks(self, cleaned: str):
        cleaned = cleaned or ""
        n = len(cleaned)
        if n == 0:
            return []
        if n == 1:
            return [cleaned]
        if 2 <= n <= 5:
            first = n // 2
            return [cleaned[:first], cleaned[first:]]

        chunks = []
        i = 0
        while n - i > 4:
            remain = n - i
            size = 4 if remain - 3 == 1 else 3
            chunks.append(cleaned[i : i + size])
            i += size
        if i < n:
            chunks.append(cleaned[i:])
        return chunks

    def syllable_salad(self):
        self.learn_content.clear_widgets()
        if not self.all_vocab_list:
            return

        main = self._get_current_vocab()
        if main is None:
            return

        pool = [e for e in self.all_vocab_list if e is not main]
        extra = random.sample(pool, min(2, len(pool))) if pool else []
        selected = [main] + extra

        # unique by pair
        uniq = {}
        for e in selected:
            key = (e.get("own_language", ""), e.get("foreign_language", ""))
            if key not in uniq:
                uniq[key] = e
        selected = list(uniq.values())

        self.syllable_salad_items = []
        self.syllable_salad_buttons = []
        self.syllable_salad_finished_count = 0
        self.syllable_salad_active_word_index = None
        self.header_label.text = ""

        center = AnchorLayout(anchor_x="center", anchor_y="center", padding=30 * float(self.config_data["settings"]["gui"]["padding_multiplicator"]))
        card = RoundedCard(orientation="vertical", size_hint=(0.9, 0.6), padding=dp(16), spacing=dp(12), bg_color=self.colors["card"])

        card.add_widget(self.make_text_label(getattr(labels, "syllable_salad_instruction", "Build the word from syllables:"), size_hint_y=None, height=dp(30)))

        self.syllable_salad_progress_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(80), spacing=dp(4))

        for vocab in selected:
            raw = (vocab.get("foreign_language", "") or "").strip()
            clean = self._clean_target_for_syllables(raw)
            if not clean:
                continue
            chunks = self._split_into_syllable_chunks(clean)
            if not chunks:
                continue

            own = vocab.get("own_language", "") or ""
            third = (vocab.get("latin_language") or "").strip()
            base = f"[b]{own}[/b] ({third}): " if third else f"[b]{own}[/b]: "
            lbl = self.make_text_label(base, size_hint_y=None, height=dp(24))
            lbl.markup = True

            self.syllable_salad_items.append(
                {
                    "vocab": vocab,
                    "target_clean": clean,
                    "chunks": chunks,
                    "next_index": 0,
                    "built": "",
                    "base_text": base,
                    "label": lbl,
                    "finished": False,
                }
            )
            self.syllable_salad_progress_box.add_widget(lbl)

        if not self.syllable_salad_items:
            self._advance_to_next()
            return

        card.add_widget(self.syllable_salad_progress_box)

        # build buttons for all chunks
        all_buttons = []
        for w_i, item in enumerate(self.syllable_salad_items):
            for c_i, chunk in enumerate(item["chunks"]):
                btn = RoundedButton(
                    text=chunk,
                    bg_color=self.colors["card"],
                    color=self.colors["text"],
                    font_size=sp(int(self.config_data["settings"]["gui"]["title_font_size"])),
                    size_hint=(None, None),
                    size=(dp(80), dp(56)),
                )
                btn._word_index = w_i
                btn._chunk_index = c_i
                btn.bind(on_press=self.syllable_salad_segment_pressed)
                all_buttons.append(btn)

        random.shuffle(all_buttons)

        from kivy.uix.gridlayout import GridLayout

        cols = max(1, min(len(all_buttons), 6))
        grid = GridLayout(cols=cols, spacing=dp(8), size_hint_y=None, padding=(0, dp(4)))
        grid.bind(minimum_height=grid.setter("height"))

        for btn in all_buttons:
            wrapper = RoundedCard(orientation="vertical", size_hint=(None, None), padding=dp(3), bg_color=self.colors["card_selected"])
            wrapper.add_widget(btn)
            grid.add_widget(wrapper)
            self.syllable_salad_buttons.append(btn)

        scroll = ScrollView(size_hint=(1, None), height=dp(210), do_scroll_y=True, do_scroll_x=True)
        scroll.add_widget(grid)
        card.add_widget(scroll)

        # skip / reshuffle
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(12))
        skip_btn = self.make_secondary_button(getattr(labels, "letter_salad_skip", "Skip"), size_hint=(0.5, 1))
        reshuffle_btn = self.make_secondary_button(getattr(labels, "syllable_salad_reshuffle", "Reshuffle"), size_hint=(0.5, 1))
        skip_btn.bind(on_press=self.syllable_salad_skip)
        reshuffle_btn.bind(on_press=lambda _i: self.syllable_salad())
        row.add_widget(skip_btn)
        row.add_widget(reshuffle_btn)
        card.add_widget(row)

        center.add_widget(card)
        self.learn_content.add_widget(center)

    def _reset_syllable_word(self, word_index: int):
        if not (0 <= word_index < len(self.syllable_salad_items)):
            return
        item = self.syllable_salad_items[word_index]
        item["next_index"] = 0
        item["built"] = ""
        item["finished"] = False
        lbl = item["label"]
        lbl.text = item["base_text"]
        lbl.color = self.colors["muted"]
        lbl.markup = True

        for btn in self.syllable_salad_buttons:
            if getattr(btn, "_word_index", None) == word_index:
                btn.disabled = False
                btn.set_bg_color(self.colors["card"])
                btn.color = self.colors["text"]

    def syllable_salad_segment_pressed(self, button, _instance=None):
        if getattr(button, "disabled", False):
            return

        w_i = getattr(button, "_word_index", None)
        c_i = getattr(button, "_chunk_index", None)
        if w_i is None or c_i is None:
            return
        if not (0 <= w_i < len(self.syllable_salad_items)):
            return

        item = self.syllable_salad_items[w_i]
        if item["finished"]:
            return

        wrong_delta = getattr(labels, "knowledge_delta_syllable_wrong_word", -0.05)
        correct_delta = getattr(labels, "knowledge_delta_syllable_correct_word", 0.08)

        active = self.syllable_salad_active_word_index
        if active is None:
            self.syllable_salad_active_word_index = w_i
            active = w_i
        else:
            if active != w_i:
                # allow switching only if user clicks first chunk of another word
                if c_i == 0 and item["next_index"] == 0:
                    self._reset_syllable_word(active)
                    self.syllable_salad_active_word_index = w_i
                    active = w_i
                else:
                    button.set_bg_color(self.colors["danger"])
                    self._daily_goal_perfect = False
                    self._adjust_knowledge_level(item.get("vocab"), wrong_delta)
                    Clock.schedule_once(lambda _dt: button.set_bg_color(self.colors["card"]), 0.25)
                    return

        item = self.syllable_salad_items[w_i]
        expected = item["next_index"]

        if c_i == expected:
            button.set_bg_color(self.colors["success"])
            button.disabled = True
            item["next_index"] += 1
            item["built"] += button.text

            lbl = item["label"]
            lbl.text = item["base_text"] + item["built"]
            lbl.markup = True

            if item["next_index"] >= len(item["chunks"]):
                item["finished"] = True
                self.syllable_salad_finished_count += 1
                lbl.color = self.colors["success"]
                self._adjust_knowledge_level(item.get("vocab"), correct_delta)
                self.syllable_salad_active_word_index = None

                if self.syllable_salad_finished_count >= len(self.syllable_salad_items):
                    Clock.schedule_once(lambda _dt: self._syllable_salad_finish(), 0.3)
        else:
            button.set_bg_color(self.colors["danger"])
            self._daily_goal_perfect = False
            self._adjust_knowledge_level(item.get("vocab"), wrong_delta)
            Clock.schedule_once(lambda _dt: button.set_bg_color(self.colors["card"]), 0.25)

    def _syllable_salad_finish(self):
        items = getattr(self, "syllable_salad_items", []) or []
        for item in items:
            v = item.get("vocab")
            if v is not None:
                self.update_srs(v, was_correct=True, quality=1.0)

        steps = len(items) if items else 1
        if self._register_session_step(was_correct=True, steps=steps):
            return
        self._advance_to_next()

    def syllable_salad_skip(self, _instance=None):
        items = getattr(self, "syllable_salad_items", []) or []
        for item in items:
            v = item.get("vocab")
            if v is not None:
                self.update_srs(v, was_correct=False, quality=0.0)
        steps = len(items) if items else 1
        if self._register_session_step(was_correct=False, steps=steps):
            return
        self._advance_to_next()
