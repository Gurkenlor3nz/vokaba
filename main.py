"""------Import Python packages------"""
from datetime import datetime

"""------Import kivy widgets------"""
import kivy.core.window
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout


"""------Import files------"""""
from labels import *

def log(text):
    print("LOG  time: " + str(datetime.now())[11:] + "; content: \"" + text + "\"")


class VocabpyApp(App):
    def build(self):
        self.window = GridLayout()
        self.window.cols = 2
        self.window.rows = 2


        self.nein_text = Label(text="Nein")
        self.window.add_widget(self.nein_text)


        self.settings_button = Button(text="Settings")
        self.settings_button.bind(on_press=self.test)
        self.window.add_widget(self.settings_button)

        return self.window

    def test(self, instance):
        log("opened settings")



if __name__ == "__main__":
    VocabpyApp().run()
