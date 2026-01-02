# vokaba/core/paths.py
from __future__ import annotations

import os
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime


APP_FOLDER_NAME = "Vokaba"
VOCAB_DIRNAME = "vocab"
CONFIG_FILENAME = "config.yml"


def _is_android() -> bool:
    # Kivy setzt oft ANDROID_ARGUMENT; zusätzlich checken wir sys._MEIPASS/Platform nicht
    return "ANDROID_ARGUMENT" in os.environ


def runtime_root() -> Path:
    """
    Wo Assets liegen:
    - PyInstaller one-folder: neben der exe
    - PyInstaller one-file: in sys._MEIPASS
    - Source-run: Projektroot
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent

    # Source: .../vokaba/core/paths.py -> Projektroot ist parents[2]
    here = Path(__file__).resolve()
    if len(here.parents) >= 3:
        return here.parents[2]
    return here.parent


def _windows_documents_dir() -> Path:
    try:
        import ctypes
        from ctypes import wintypes

        CSIDL_PERSONAL = 5  # "My Documents"
        SHGFP_TYPE_CURRENT = 0

        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        if buf.value:
            return Path(buf.value)
    except Exception:
        pass

    home = Path.home()
    for cand in ("Documents", "Dokumente"):
        d = home / cand
        if d.exists():
            return d
    return home / "Documents"


def _linux_documents_dir() -> Path:
    home = Path.home()
    cfg = home / ".config" / "user-dirs.dirs"
    if cfg.exists():
        txt = cfg.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'XDG_DOCUMENTS_DIR=(?:"|\')?(.+?)(?:"|\')?\n', txt)
        if m:
            val = m.group(1).strip()
            val = val.replace("$HOME", str(home))
            return Path(os.path.expandvars(val))

    for cand in ("Documents", "Dokumente"):
        d = home / cand
        if d.exists():
            return d
    return home / "Documents"


def documents_dir_desktop() -> Path:
    if sys.platform.startswith("win"):
        return _windows_documents_dir()
    if sys.platform.startswith("darwin"):
        return Path.home() / "Documents"
    return _linux_documents_dir()


def data_dir() -> Path:
    """
    Wo CSVs + config.yml liegen sollen.
    Desktop: Documents/Vokaba
    Android: App.user_data_dir (scoped-storage-sicher)
    """
    if _is_android():
        # Kivy App.user_data_dir ist auf Android in einer writeable App-Dir (nicht mehr /sdcard)
        from kivy.app import App
        app = App.get_running_app()
        return Path(app.user_data_dir)

    return documents_dir_desktop() / APP_FOLDER_NAME


def vocab_dir() -> Path:
    return data_dir() / VOCAB_DIRNAME


def config_path() -> Path:
    return data_dir() / CONFIG_FILENAME


def ensure_data_layout() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    vocab_dir().mkdir(parents=True, exist_ok=True)


def migrate_legacy_data() -> None:
    ensure_data_layout()

    """
    Migriert alte Daten aus:
      - current working dir
      - runtime_root()
    nach Documents/Vokaba/...
    """

    new_cfg = config_path()
    new_vocab = vocab_dir()
    legacy_places = [Path.cwd(), runtime_root()]

    # config.yml migrieren, wenn neu nicht existiert
    if not new_cfg.exists():
        for base in legacy_places:
            old = base / CONFIG_FILENAME
            if old.exists():
                try:
                    shutil.copy2(old, new_cfg)
                except Exception:
                    pass
                break
    # CSVs: kopiere ALLE fehlenden (nicht nur wenn Ordner leer ist)
    for base in legacy_places:
        old_vocab = base / VOCAB_DIRNAME
        if not old_vocab.is_dir():
            continue

        for src in old_vocab.glob("*.csv"):
            dst = new_vocab / src.name
            if not dst.exists():
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass


def vocab_root_string() -> str:
    """
    Für deinen bestehenden Code: String mit trailing slash.
    """
    ensure_data_layout()
    root = str(vocab_dir()).replace("\\", "/")
    if not root.endswith("/"):
        root += "/"
    return root
