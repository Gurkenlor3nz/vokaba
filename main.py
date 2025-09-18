"""------Import Python packages------"""
from datetime import datetime
import os

import labels

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
from kivy.uix.scrollview import ScrollView


"""------Import files------"""""
from labels import *

def log(text):
    print("LOG  time: " + str(datetime.now())[11:] + "; content: \"" + text + "\"")


class VocabpyApp(App):
    def build(self):
        #Window init
        self.window = GridLayout()
        self.window.cols = 2
        self.window.rows = 2

        self.nein_text = Label(text="Nein")
        self.window.add_widget(self.nein_text)

        for i in labels.vocab_folder_content:
            if os.path.isfile(os.path.join(labels.vocab_path, i)):
                voc_stacks = Button(text=i, size_hint_y=None, height=40)
                voc_stacks.bind(on_release=lambda instance, fname=i: self.on_file_select(log("datei ausgewählt")))
                self.window.add_widget(voc_stacks)

        self.settings_button = Button(text="Settings")
        self.settings_button.bind(on_press=self.test)
        self.window.add_widget(self.settings_button)



        return self.window

    def test(self, instance):
        log("opened settings")



if __name__ == "__main__":
    VocabpyApp().run()
