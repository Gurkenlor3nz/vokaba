import csv
import os
import yaml
import unicodedata
from typing import Dict, List, Tuple, Optional
from vokaba.core.paths import config_path, migrate_legacy_data, ensure_data_layout


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _normalize_knowledge_level(value) -> float:
    """
    Normalize knowledge_level to a float in [0.0, 1.0].

    Accepts:
    - None / empty -> 0.0
    - int/float
    - strings with "." or "," as decimal separator
    - out-of-range -> clamped to [0.0, 1.0]
    """
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        v = float(value)
    else:
        s = str(value).strip()
        if not s:
            return 0.0
        s = s.replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            return 0.0

    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _normalize_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _strip_outer_quotes_if_whole_line(line: str) -> str:
    """
    Your files sometimes store each CSV line as:
        "a,b,c,d"
    instead of:
        a,b,c,d

    If a line has exactly one leading and one trailing quote (count==2),
    we remove them to restore a normal CSV line.

    This keeps proper CSV quoting inside fields intact (if present).
    """
    s = line.strip("\n")
    if len(s) >= 2 and s.startswith('"') and s.endswith('"') and s.count('"') == 2:
        return s[1:-1]
    return s


def _read_file_lines_without_meta(filename: str) -> Tuple[List[str], Dict[str, str]]:
    """
    Reads file and returns:
      (csv_lines, meta_dict)

    meta lines look like:
      # own_language=Deutsch
    """
    meta: Dict[str, str] = {}
    csv_lines: List[str] = []

    with open(filename, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("# "):
                # meta
                if "=" in line:
                    key, val = line[2:].split("=", 1)
                    meta[key.strip()] = val.strip()
                continue
            csv_lines.append(raw)  # keep newline for csv module

    return csv_lines, meta


# ------------------------------------------------------------
# Unicode normalization (fix dead keys / combining marks)
# ------------------------------------------------------------

def _fix_leading_combining_marks(s: str) -> str:
    """
    Some external keyboards (dead keys) may emit combining marks BEFORE the base letter,
    e.g. '\\u0300e' instead of 'e\\u0300'. Many renderers show the combining mark as a
    "broken box" followed by the letter.

    This function reorders such sequences so NFC can compose them (-> 'è').
    """
    if not s:
        return s

    out: List[str] = []
    pending: List[str] = []

    for ch in s:
        # If string starts with combining marks, keep them pending until first base char
        if unicodedata.combining(ch) and not out:
            pending.append(ch)
            continue

        if not unicodedata.combining(ch):
            out.append(ch)
            if pending:
                out.extend(pending)
                pending.clear()
        else:
            out.append(ch)

    # If it ends with pending combining marks, just append (can't attach to a base char)
    if pending:
        out.extend(pending)

    return "".join(out)


def normalize_user_text(value) -> str:
    """
    Returns a safe, display-friendly string:
      - None -> ""
      - repairs dead-key ordering of combining marks
      - normalizes to NFC (composed form), so 'e' + combining_grave -> 'è'
    """
    if value is None:
        return ""
    s = str(value)
    if not s:
        return ""
    s = _fix_leading_combining_marks(s)
    return unicodedata.normalize("NFC", s)


def _normalize_row_text_fields(row: Dict) -> Dict:
    """
    Apply normalize_user_text to known text columns only (not numbers/dates).
    """
    if not isinstance(row, dict):
        return row

    for k in ("own_language", "foreign_language", "latin_language", "info"):
        if k in row:
            row[k] = normalize_user_text(row.get(k))

    return row


# ------------------------------------------------------------
# Vocab CSV
# ------------------------------------------------------------

VOCAB_FIELDNAMES = [
    "own_language",
    "foreign_language",
    "latin_language",
    "info",
    "knowledge_level",
    "srs_streak",
    "srs_last_seen",
    "srs_due",
    "daily_goal_anchor",
    "daily_goal_anchor_date",
]


def save_to_vocab(
    vocab: List[Dict],
    filename: str,
    own_lang: str = "Deutsch",
    foreign_lang: str = "Englisch",
    latin_lang: str = "Latein",
    latin_active: bool = False,
) -> None:
    """
    Writes vocab list to CSV with meta header lines.
    Output is normal CSV (NOT whole-line quoted).
    """
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        f.write(f"# own_language={own_lang}\n")
        f.write(f"# foreign_language={foreign_lang}\n")
        f.write(f"# latin_language={latin_lang}\n")
        f.write(f"# latin_active={str(bool(latin_active))}\n")

        writer = csv.DictWriter(
            f,
            fieldnames=VOCAB_FIELDNAMES,
            extrasaction="ignore",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        for row in vocab:
            if not isinstance(row, dict):
                continue

            row = dict(row)  # avoid mutating caller data

            # Normalize text fields (fix dead keys / combining marks)
            row = _normalize_row_text_fields(row)

            row.setdefault("latin_language", "")
            row.setdefault("info", "")

            row["knowledge_level"] = _normalize_knowledge_level(row.get("knowledge_level", 0.0))
            row["srs_streak"] = _normalize_int(row.get("srs_streak", 0), 0)

            last_seen = row.get("srs_last_seen") or ""
            due = row.get("srs_due") or ""
            row["srs_last_seen"] = str(last_seen) if last_seen else ""
            row["srs_due"] = str(due) if due else ""

            writer.writerow(row)


def load_vocab(filename: str):
    """
    Loads vocab from CSV.

    Returns:
        (vocab_list, own_lang, foreign_lang, latin_lang, latin_active)

    Compatible with:
    - normal CSV header line
    - whole-line-quoted CSV header line ("a,b,c")
    - whole-line-quoted data lines ("x,y,z")
    """
    vocab: List[Dict] = []
    csv_lines, meta = _read_file_lines_without_meta(filename)

    own_lang = meta.get("own_language")
    foreign_lang = meta.get("foreign_language")
    latin_lang = meta.get("latin_language")
    latin_active = (meta.get("latin_active", "false").strip().lower() == "true")

    # preprocess lines for the whole-line-quoted format
    cleaned_lines: List[str] = []
    for raw in csv_lines:
        fixed = _strip_outer_quotes_if_whole_line(raw)
        cleaned_lines.append(fixed + ("\n" if not fixed.endswith("\n") else ""))

    # Use DictReader
    reader = csv.DictReader(cleaned_lines)
    # If the header was "one field containing commas", DictReader will think there is 1 field.
    # But our preprocessing above should have converted it back to normal "a,b,c" -> OK.

    for row in reader:
        if not row:
            continue

        # Ensure all known fields exist
        if "latin_language" not in row:
            row["latin_language"] = ""
        if "info" not in row:
            row["info"] = ""

        # Normalize text fields (fix dead keys / combining marks)
        row = _normalize_row_text_fields(row)

        # Normalize types
        row["knowledge_level"] = _normalize_knowledge_level(row.get("knowledge_level"))
        row["srs_streak"] = _normalize_int(row.get("srs_streak", 0), 0)

        # keep srs strings as-is (isoformat or empty)
        row["srs_last_seen"] = (row.get("srs_last_seen") or "").strip()
        row["srs_due"] = (row.get("srs_due") or "").strip()

        vocab.append(row)

    return vocab, own_lang, foreign_lang, latin_lang, latin_active


def read_languages(filename: str) -> Tuple[Optional[str], Optional[str], Optional[str], bool]:
    """Reads only meta language settings."""
    own_lang = None
    foreign_lang = None
    latin_lang = None
    latin_active = False

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# own_language="):
                own_lang = normalize_user_text(line.strip().split("=", 1)[1])
            elif line.startswith("# foreign_language="):
                foreign_lang = normalize_user_text(line.strip().split("=", 1)[1])
            elif line.startswith("# latin_language="):
                latin_lang = normalize_user_text(line.strip().split("=", 1)[1])
            elif line.startswith("# latin_active="):
                latin_active = line.strip().split("=", 1)[1].lower() == "true"

    return own_lang, foreign_lang, latin_lang, latin_active


def change_languages(
    filename: str,
    new_own: str,
    new_foreign: str,
    new_latin: str,
    latin_active: bool = False,
) -> None:
    """Overwrites meta languages while keeping vocab entries unchanged."""
    vocab, _, _, _, _ = load_vocab(filename)
    save_to_vocab(
        vocab,
        filename,
        own_lang=new_own,
        foreign_lang=new_foreign,
        latin_lang=new_latin,
        latin_active=latin_active,
    )


# ------------------------------------------------------------
# Settings YAML
# ------------------------------------------------------------

def load_settings() -> dict:
    """
    Loads config.yml with sane defaults. Keeps your existing keys:
      settings.daily_target_cards
      settings.gui.(title_font_size, text_font_size, padding_multiplicator)
      settings.session_size
      settings.theme.(preset, base_preset, custom_colors)
      settings.modes.*
      stats.(daily_progress_date, daily_cards_done, total_learn_time_seconds)
    """
    default_config = {
        "settings": {
            "daily_target_cards": 50,
            "gui": {
                "title_font_size": 32,
                "text_font_size": 18,
                "padding_multiplicator": 1.0,
            },
            "session_size": 20,
            "theme": {
                "preset": "dark",
                "base_preset": "dark",
                "custom_colors": {},
            },
            "modes": {
                "front_back": True,
                "back_front": True,
                "multiple_choice": True,
                "letter_salad": True,
                "connect_pairs": True,
                "typing": True,
                "syllable_salad": True,
            },
        },
        "stats": {
            "daily_progress_date": None,
            "daily_cards_done": 0,
            "total_learn_time_seconds": 0,
        },
        "stack_sort_mode": "name",  # "name" | "language"
        "global_learn_languages": [],  # [] = alle
        "typing": {
            "require_self_rating": True,
        },
    }

    migrate_legacy_data()  # einmalig alte config/csvs rüberziehen
    ensure_data_layout()
    cfg_path = str(config_path())

    if not os.path.exists(cfg_path):
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_config, f, allow_unicode=True, sort_keys=False)
        return default_config

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    cfg = data

    settings = cfg.setdefault("settings", {})
    settings.setdefault("daily_target_cards", default_config["settings"]["daily_target_cards"])

    gui = settings.setdefault("gui", {})
    gui.setdefault("title_font_size", default_config["settings"]["gui"]["title_font_size"])
    gui.setdefault("text_font_size", default_config["settings"]["gui"]["text_font_size"])
    gui.setdefault("padding_multiplicator", default_config["settings"]["gui"]["padding_multiplicator"])

    settings.setdefault("session_size", default_config["settings"]["session_size"])

    theme = settings.setdefault("theme", {})
    theme.setdefault("preset", default_config["settings"]["theme"]["preset"])
    theme.setdefault("base_preset", default_config["settings"]["theme"]["base_preset"])
    theme.setdefault("custom_colors", dict(default_config["settings"]["theme"]["custom_colors"]))

    modes = settings.setdefault("modes", {})
    for k, v in default_config["settings"]["modes"].items():
        modes.setdefault(k, v)

    stats = cfg.setdefault("stats", {})
    for k, v in default_config["stats"].items():
        stats.setdefault(k, v)

    settings.setdefault("stack_sort_mode", "name")
    settings.setdefault("global_learn_languages", [])
    typing_cfg = settings.setdefault("typing", {})
    typing_cfg.setdefault("require_self_rating", True)

    save_settings(cfg)
    ensure_legal_defaults(cfg)
    return cfg


def save_settings(config: dict) -> None:
    ensure_data_layout()
    with open(str(config_path()), "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)



# ------------------------------------------------------------
# Persistence helpers (same API as before)
# ------------------------------------------------------------

def persist_all_stacks(stack_vocab_lists: dict, stack_meta_map: dict) -> None:
    if not stack_vocab_lists:
        return

    for filename, vocab_list in stack_vocab_lists.items():
        if vocab_list is None:
            continue

        meta = stack_meta_map.get(filename)
        if meta is None:
            own_lang, foreign_lang, latin_lang, latin_active = read_languages(filename)
        else:
            own_lang, foreign_lang, latin_lang, latin_active = meta

        save_to_vocab(
            vocab_list,
            filename,
            own_lang=own_lang or "Deutsch",
            foreign_lang=foreign_lang or "Englisch",
            latin_lang=latin_lang or "Latein",
            latin_active=bool(latin_active),
        )


def persist_single_entry(vocab: dict, stack_vocab_lists: dict, stack_meta_map: dict, entry_to_stack_file: dict) -> None:
    """
    Persist exactly one vocab entry by saving only its owning stack file.

    This is used for immediate autosave during learning updates.
    """
    if vocab is None:
        return

    filename = entry_to_stack_file.get(id(vocab))
    if not filename:
        return

    vocab_list = stack_vocab_lists.get(filename)
    if vocab_list is None:
        return

    meta = stack_meta_map.get(filename)
    if meta is None:
        own_lang, foreign_lang, latin_lang, latin_active = read_languages(filename)
    else:
        own_lang, foreign_lang, latin_lang, latin_active = meta

    save_to_vocab(
        vocab_list,
        filename,
        own_lang=own_lang or "Deutsch",
        foreign_lang=foreign_lang or "Englisch",
        latin_lang=latin_lang or "Latein",
        latin_active=bool(latin_active),
    )

def ensure_legal_defaults(cfg: dict) -> None:
    settings = cfg.setdefault("settings", {})
    legal = settings.setdefault("legal", {})
    legal.setdefault("accepted", False)
    legal.setdefault("accepted_at", None)
