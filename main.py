"""------Import Python packages------"""
from datetime import datetime
import os
import yaml

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
from kivy.uix.slider import *
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle



"""------Import files------"""""
import labels
import save


"""------Init Variables------"""
selected_stack = ""
global vocab_current
config = save.load_settings()


def log(text):
    print("LOG  time: " + str(datetime.now())[11:] + "; content: \"" + text + "\"")


#Class for touch sliders
class NoScrollSlider(Slider):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
        # Touch für diesen Slider "festhalten" und normale Slider-Logik ausführen
            touch.grab(self)
            return super().on_touch_down(touch)
        return False


    def on_touch_move(self, touch):
        if touch.grab_current is self:
            return super().on_touch_move(touch)
        return False


    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return super().on_touch_up(touch)
        return False



class VokabaApp(App):
    def build(self):
        self.window = FloatLayout()
        self.scroll= ScrollView(size_hint=(1, 1))
        self.main_menu()
        return self.window


    def main_menu(self, instance=None):
        #Window init
        log("opened main menu")
        self.window.clear_widgets()

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



    def settings(self, instance):
        log("opened settings")
        self.window.clear_widgets()

        #Title font size slider
        center_center = AnchorLayout(
            anchor_x="center", anchor_y = "center",
            padding=30, size_hint_y=None,height=60)
        scroll = ScrollView(size_hint=(1, 1))
        settings_content=BoxLayout(orientation="vertical", size_hint_y=None, spacing=16, padding=16)
        settings_content.bind(minimum_height=settings_content.setter("height"))
        self.title_label = Label(text=labels.settings_title_font_size_slider_test_label, font_size = 20,
                                 size_hint_y=None, height=80)
        title_size_slider = NoScrollSlider(min=10, max=80, value=20, size_hint_y=None, height=40)
        """for i in range(12):
            settings_content.add_widget(Label(text=f"Option {i + 1}", size_hint_y=None, height=40))"""
        settings_content.add_widget(self.title_label)
        settings_content.add_widget(title_size_slider)
        scroll.add_widget(settings_content)
        self.window.add_widget(scroll)


        #Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None), size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=self.main_menu)
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


    def select_stack(self, stack):
        vocab_file = str("vocab/" + stack)
        vocab_current = save.load_vocab(vocab_file)

        self.window.clear_widgets()
        self.scroll = ScrollView(size_hint=(1, 1))
        log("making vocab asking soon")

    def on_slider_value(self, instance, value):
        self.title_label.font_size = value
        self.title.label.height = max(40, value * 1.4)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        return False

if __name__ == "__main__":
    VokabaApp().run()
