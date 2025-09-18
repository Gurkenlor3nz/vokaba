"""------Import Python packages------"""
from datetime import datetime
import os
import labels
import save

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

"""------Init Variables------"""
selected_stack = ""

def log(text):
    print("LOG  time: " + str(datetime.now())[11:] + "; content: \"" + text + "\"")


class VocabpyApp(App):
    def build(self):
        #Window init
        self.window = GridLayout()
        self.window.cols = 2
        self.window.rows = 2
        self.scroll= ScrollView(size_hint=(1, 1))


        self.nein_text = Label(text=labels.welcome_text)
        self.window.add_widget(self.nein_text)


        self.file_list = GridLayout(cols=1, spacing=5, size_hint_y = None)
        self.file_list.bind(minimum_height=self.file_list.setter("height"))
        self.scroll.add_widget(self.file_list)
        self.window.add_widget((self.scroll))

        for i in labels.vocab_folder_content:
            if os.path.isfile(os.path.join(labels.vocab_path, i)):
                voc_stacks = Button(text=i, size_hint_y=None, height= 40)
                voc_stacks.bind(on_release=lambda btn, name=i: self.select_stack(name))
                self.file_list.add_widget(voc_stacks)


        self.settings_button = Button(text="Settings")
        self.settings_button.bind(on_press=self.test)
        self.window.add_widget(self.settings_button)

        return self.window

    def test(self, instance):
        log("opened settings")

    def select_stack(self, stack):
        print(stack)


if __name__ == "__main__":
    vocab = [{"own_language" : "Haus", "foreign_language" : "house", "info" : "Substantiv"},
             {"own_language" : "laufen", "foreign_language" : "(to) walk", "info" : "Verb"}]
    save.save_to_vocab(vocab, "vocab/test.csv")

    for i in vocab:
        for j in range (0, len(i)):
            print(list(i.keys())[j] +" - "+ list(i.values())[j])

    print(save.read_languages("vocab/test.csv"))


    VocabpyApp().run()
