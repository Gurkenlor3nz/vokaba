# Pydroid run kivy
import os
import sys

# erzwingt den Android-/SDL2-tauglichen Window-Provider
os.environ["KIVY_WINDOW"] = "sdl2"
os.environ.setdefault("KIVY_NO_ARGS", "1")


def _is_android() -> bool:
    # p4a/buildozer setzen diese Variablen typischerweise
    return any(
        os.environ.get(k)
        for k in (
            "ANDROID_ARGUMENT",
            "ANDROID_PRIVATE",
            "ANDROID_STORAGE",
            "P4A_BOOTSTRAP",
            "P4A_BUILD_DIR",
        )
    )


# Wichtig für Tablets/Stift: System-IME nutzen (Handschrift in Tastatur/IME)
# ABER: auf Desktop führt 'systemanddock' oft zur hässlichen Kivy-Dock-Tastatur
# -> daher NUR auf Android setzen.
if _is_android():
    try:
        from kivy.config import Config

        # Nur System-Keyboard/IME (kein Kivy-Dock-Keyboard)
        Config.set("kivy", "keyboard_mode", "system")
    except Exception:
        pass


__version__ = "0.0.2"
__author__ = "Gurkenlorenz"
__email__ = "vokabaa@gmail.com"
__status__ = "Development"


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


if "--ocr-runner" in sys.argv:
    idx = sys.argv.index("--ocr-runner")
    sys.argv = [sys.argv[0]] + sys.argv[idx + 1 :]
    from vokaba.ocr_runner import main as ocr_main

    raise SystemExit(ocr_main())

os.environ["VOKABA_ASSETS"] = resource_path("assets")

from vokaba.app import VokabaApp

if __name__ == "__main__":
    VokabaApp().run()
