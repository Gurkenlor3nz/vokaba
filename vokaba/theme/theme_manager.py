import os
from kivy.core.window import Window
from .palettes import THEME_PRESETS

def apply_theme_from_config(config: dict) -> dict:
    """
    Build the effective color palette from config and apply Window.clearcolor.
    Supports:
      - preset: dark/light/custom
      - base_preset for custom
      - custom_colors partial overrides
    """
    settings = config.setdefault("settings", {})
    theme_cfg = settings.setdefault("theme", {})
    preset = theme_cfg.get("preset", "dark")

    if preset == "custom":
        base = theme_cfg.get("base_preset", "dark")
        palette = dict(THEME_PRESETS.get(base, THEME_PRESETS["dark"]))
        overrides = theme_cfg.get("custom_colors", {}) or {}
        for k, rgba in overrides.items():
            try:
                palette[k] = tuple(rgba)
            except Exception:
                pass
    else:
        palette = dict(THEME_PRESETS.get(preset, THEME_PRESETS["dark"]))
        theme_cfg.setdefault("base_preset", preset)
        theme_cfg.setdefault("custom_colors", {})

    try:
        Window.clearcolor = palette["bg"]
    except Exception:
        pass

    return palette


def get_icon_path(config: dict, icon_path: str) -> str:
    """
    If effective theme is light, prefer *_black.png variant if it exists.
    """
    try:
        theme_cfg = config.get("settings", {}).get("theme", {})
        preset = theme_cfg.get("preset", "dark")
        base = theme_cfg.get("base_preset", preset)
        effective = base if preset == "custom" else preset
    except Exception:
        effective = "dark"

    if effective == "light":
        root, ext = os.path.splitext(icon_path)
        alt = f"{root}_black{ext}"
        if os.path.exists(alt):
            return alt

    return icon_path
