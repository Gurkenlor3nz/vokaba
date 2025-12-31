import os
from datetime import datetime
import save
import labels
from vokaba.core.logging_utils import log


class StatsGoalMixin:
    """
    Shared statistics + daily goal helpers.

    This is used by main menu, learning and dashboard.
    """

    def vocab_root(self) -> str:
        root = getattr(labels, "vocab_path", "vocab/")
        root = root.replace("\\", "/")
        if not root.endswith("/"):
            root += "/"
        os.makedirs(root, exist_ok=True)
        return root

    def _list_stack_files(self):
        root = self.vocab_root()
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if os.path.isfile(full) and name.lower().endswith(".csv"):
                yield full

    def _compute_overall_stats(self) -> dict:
        """
        Compute global stats over all stacks.
        Returns:
          stacks, total_vocab, unique_pairs, learned_vocab, avg_knowledge
        """
        stats = {
            "stacks": 0,
            "total_vocab": 0,
            "unique_pairs": 0,
            "learned_vocab": 0,
            "avg_knowledge": 0.0,
        }

        unique_pairs = set()
        total_knowledge = 0.0
        total_entries = 0

        for filename in self._list_stack_files():
            stats["stacks"] += 1
            data = save.load_vocab(filename)
            vocab_list = data[0] if isinstance(data, tuple) else data

            stats["total_vocab"] += len(vocab_list)

            for e in vocab_list:
                own = (e.get("own_language") or "").strip()
                foreign = (e.get("foreign_language") or "").strip()
                if own or foreign:
                    unique_pairs.add((own, foreign))

                try:
                    level = float(e.get("knowledge_level", 0.0) or 0.0)
                except Exception:
                    level = 0.0
                level = max(0.0, min(1.0, level))

                total_knowledge += level
                total_entries += 1

                if level >= 0.7:
                    stats["learned_vocab"] += 1

        stats["unique_pairs"] = len(unique_pairs)
        stats["avg_knowledge"] = (total_knowledge / total_entries) if total_entries else 0.0
        return stats

    def _get_vocab_counts_for_modes(self) -> tuple[int, int]:
        """
        Return (total_vocab_count, unique_pair_count) across ALL stacks.
        This fixes a real weakness of the old code which used self.all_vocab_list
        (empty in main menu).
        """
        total = 0
        unique = set()

        for filename in self._list_stack_files():
            try:
                data = save.load_vocab(filename)
                vocab_list = data[0] if isinstance(data, tuple) else data
            except Exception:
                continue

            total += len(vocab_list)
            for e in vocab_list:
                key = ((e.get("own_language") or ""), (e.get("foreign_language") or ""))
                unique.add(key)

        return total, len(unique)

    # ---------------------------
    # Daily goal (config-backed)
    # ---------------------------

    def _init_daily_goal_defaults(self):
        """
        Ensure daily goal exists; reset daily progress if day changed.
        Also applies daily knowledge decay once per day.
        """
        cfg = self.config_data
        settings = cfg.setdefault("settings", {})
        stats_cfg = cfg.setdefault("stats", {})

        # Default daily goal = 50 (one-time migration if old default 300)
        if "daily_target_cards" not in settings:
            settings["daily_target_cards"] = 50
        else:
            try:
                migrated = bool(stats_cfg.get("migrated_daily_goal_50", False))
                if (not migrated) and int(settings.get("daily_target_cards", 0) or 0) == 300:
                    settings["daily_target_cards"] = 50
                    stats_cfg["migrated_daily_goal_50"] = True
            except Exception:
                pass

        settings.setdefault("daily_goal_step", 0.10)

        today = datetime.now().date()
        today_iso = today.isoformat()

        # ----- daily decay -----
        last_decay_iso = stats_cfg.get("knowledge_decay_date")
        if last_decay_iso and last_decay_iso != today_iso:
            try:
                last_d = datetime.fromisoformat(str(last_decay_iso)).date()
                days = max(1, (today - last_d).days)
            except Exception:
                days = 1

            decay = 0.005 * days

            for filename in self._list_stack_files():
                try:
                    vocab_list, own, foreign, latin, latin_active = save.load_vocab(filename)
                except Exception:
                    continue

                changed = False
                for e in vocab_list:
                    try:
                        lvl = float(e.get("knowledge_level", 0.0) or 0.0)
                    except Exception:
                        lvl = 0.0
                    new_lvl = max(0.0, min(1.0, lvl - decay))
                    if new_lvl != lvl:
                        e["knowledge_level"] = new_lvl
                        changed = True

                if changed:
                    try:
                        save.save_to_vocab(
                            vocab_list,
                            filename,
                            own_lang=own or "Deutsch",
                            foreign_lang=foreign or "Englisch",
                            latin_lang=latin or "Latein",
                            latin_active=bool(latin_active),
                        )
                    except Exception:
                        pass

            stats_cfg["knowledge_decay_date"] = today_iso

        elif not last_decay_iso:
            stats_cfg["knowledge_decay_date"] = today_iso

        # ----- daily progress reset -----
        if stats_cfg.get("daily_progress_date") != today_iso:
            stats_cfg["daily_progress_date"] = today_iso
            stats_cfg["daily_cards_done"] = 0

        save.save_settings(cfg)


    def _get_daily_progress_values(self) -> tuple[int, int]:
        self._init_daily_goal_defaults()
        stats_cfg = self.config_data.get("stats", {}) or {}
        settings = self.config_data.get("settings", {}) or {}
        done = int(stats_cfg.get("daily_cards_done", 0) or 0)
        target = int(settings.get("daily_target_cards", 1) or 1)
        if target <= 0:
            target = 1
        return done, target

    def _update_daily_progress(self, steps: int = 1):
        """
        Increase daily done counter (used only when you decide something counts
        as a "completed" card for daily goal).
        """
        self._init_daily_goal_defaults()
        try:
            steps = int(steps)
        except Exception:
            steps = 1
        steps = max(1, steps)

        stats_cfg = self.config_data.setdefault("stats", {})
        today = datetime.now().date().isoformat()
        if stats_cfg.get("daily_progress_date") != today:
            stats_cfg["daily_progress_date"] = today
            stats_cfg["daily_cards_done"] = 0

        stats_cfg["daily_cards_done"] = int(stats_cfg.get("daily_cards_done", 0) or 0) + steps
        save.save_settings(self.config_data)

        # Refresh UI if present
        try:
            self._refresh_daily_progress_ui()
        except Exception as e:
            log(f"daily progress refresh failed: {e}")

    def _refresh_daily_progress_ui(self):
        """Update all progress bars/labels if they exist."""
        done, target = self._get_daily_progress_values()

        # main menu
        if hasattr(self, "daily_bar_main_menu") and self.daily_bar_main_menu:
            self.daily_bar_main_menu.max = max(1, target)
            self.daily_bar_main_menu.value = min(done, target)

        if hasattr(self, "daily_label_main_menu") and self.daily_label_main_menu:
            template = getattr(labels, "daily_goal_main_menu_label", "Today\'s goal: {done}/{target} cards")
            self.daily_label_main_menu.text = template.format(done=done, target=target)

        # learn screen
        if hasattr(self, "daily_bar_learn") and self.daily_bar_learn:
            self.daily_bar_learn.max = max(1, target)
            self.daily_bar_learn.value = min(done, target)

        if hasattr(self, "daily_label_learn") and self.daily_label_learn:
            template = getattr(labels, "daily_goal_learn_label", "Today: {done}/{target} cards")
            self.daily_label_learn.text = template.format(done=done, target=target)

    def _format_duration(self, total_seconds: int) -> str:
        try:
            s = int(total_seconds or 0)
        except Exception:
            s = 0
        s = max(0, s)

        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60

        if h > 0:
            return f"{h}h {m:02d}min"
        if m > 0:
            return f"{m}min {sec:02d}s"
        return f"{sec}s"

