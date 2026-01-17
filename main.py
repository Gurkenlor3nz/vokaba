# Pydroid run kivy
import os
import sys

# erzwingt den Android-/SDL2-tauglichen Window-Provider
os.environ["KIVY_WINDOW"] = "sdl2"

__version__ = "0.0.1"
__author__ = "Gurkenlorenz"
__email__ = "theo@theolemil.de"
__status__ = "Development"


def resource_path(relative_path: str) -> str:


    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


os.environ["VOKABA_ASSETS"] = resource_path("assets")

from vokaba.app import VokabaApp

if __name__ == "__main__":
    VokabaApp().run()
