#Pydroid run kivy
import os

# erzwingt den Android-tauglichen Window-Provider
os.environ["KIVY_WINDOW"] = "sdl2"

from vokaba.app import VokabaApp

if __name__ == "__main__":
    VokabaApp().run()
