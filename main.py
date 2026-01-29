# Pydroid run kivy
import os
import sys

# erzwingt den Android-/SDL2-tauglichen Window-Provider
os.environ["KIVY_WINDOW"] = "sdl2"
os.environ.setdefault("KIVY_NO_ARGS", "1")

__version__ = "0.0.1"
__author__ = "Gurkenlorenz"
__email__ = "vokabaa@gmail.com"
__status__ = "Development"


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if "--ocr-runner" in sys.argv:
    idx = sys.argv.index("--ocr-runner")
    sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    from vokaba.ocr_runner import main as ocr_main
    raise SystemExit(ocr_main())

os.environ["VOKABA_ASSETS"] = resource_path("assets")

from vokaba.app import VokabaApp

if __name__ == "__main__":
    VokabaApp().run()
