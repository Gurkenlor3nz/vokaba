"""------Import Python packages------"""
from datetime import datetime
import os


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
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout



"""------Import files------"""""
import labels
import save


"""------Init Variables------"""
selected_stack = ""
global vocab_current


def log(text):
    print("LOG  time: " + str(datetime.now())[11:] + "; content: \"" + text + "\"")


class VocabpyApp(App):
    def build(self):
        #Window init
        self.window = FloatLayout()
        self.scroll= ScrollView(size_hint=(1, 1))


        #Welcome label text
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=30)
        welcome_label = Label(text=labels.welcome_text, size_hint = (None, None), size=(300, 40), font_size = 20)
        top_center.add_widget(welcome_label)
        self.window.add_widget(top_center)


        #Settings button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        settings_button = Button(size_hint = (None, None), size=(64, 64), background_normal="assets/settings_icon.png")
        settings_button.bind(on_press=self.settings)
        top_right.add_widget(settings_button)
        self.window.add_widget(top_right)


        #File Selection
        center_anchor=AnchorLayout(anchor_x="center", anchor_y="center", padding=30)
        self.file_list = GridLayout(cols=1, spacing=5, size_hint_y = None)
        self.file_list.bind(minimum_height=self.file_list.setter("height"))

        for i in labels.vocab_folder_content:
            if os.path.isfile(os.path.join(labels.vocab_path, i)):
                voc_stacks = Button(text=i, size_hint_y=None, height= 40)
                voc_stacks.bind(on_release=lambda btn, name=i: self.select_stack(name))
                self.file_list.add_widget(voc_stacks)

        self.scroll = ScrollView(size_hint=(None, None), size=(300, 400))
        self.scroll.add_widget(self.file_list)
        center_anchor.add_widget(self.scroll)
        self.window.add_widget(center_anchor)


        return self.window


    def settings(self, instance):
        log("opened settings")
        self.window.clear_widgets()

        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=30)
        settings_title = Label(text=labels.settings_title_text, font_size=20, size_hint=(None,None), size=(80, 50))
        top_center.add_widget(settings_title)
        self.window.add_widget(top_center)




    def select_stack(self, stack):
        vocab_file = str("vocab/" + stack)
        vocab_current = save.load_vocab(vocab_file)

        self.window.clear_widgets()
        self.scroll = ScrollView(size_hint=(1, 1))
        log("making vocab asking soon")



if __name__ == "__main__":

    VocabpyApp().run()
