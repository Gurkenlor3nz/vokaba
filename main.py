"""------Import Python packages------"""
from datetime import datetime
import os
import os.path
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
from kivy.config import Config
from kivy.uix.checkbox import CheckBox


"""------Import files------"""""
import labels
import save


"""------Init Variables------"""
selected_stack = ""
global vocab_current
global title_size_slider
global three_columns_check
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
        config = save.load_settings()
        Config.window_icon = "assets/vokaba_icon.png"


        #Welcome label text
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=30)
        welcome_label = Label(text=labels.welcome_text, size_hint = (None, None), size=(300, 40), font_size = config["settings"]["gui"]["title_font_size"])
        top_center.add_widget(welcome_label)
        self.window.add_widget(top_center)


        #Settings button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        settings_button = Button(size_hint = (None, None), size=(64, 64), background_normal="assets/settings_icon.png")
        settings_button.bind(on_press=self.settings)
        top_right.add_widget(settings_button)
        self.window.add_widget(top_right)


        #Vokaba Logo
        top_left = AnchorLayout(anchor_x="left", anchor_y="top")
        vokaba_logo = Button(size_hint = (None, None), size=(128, 128), background_normal="assets/vokaba_logo.png")
        vokaba_logo.bind(on_press=self.settings)
        top_left.add_widget(vokaba_logo)
        self.window.add_widget(top_left)


        #Add Stack Button
        bottom_right = AnchorLayout(anchor_x="right", anchor_y="bottom", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/add_stack.png")
        back_button.bind(on_press=self.add_stack)
        bottom_right.add_widget(back_button)
        self.window.add_widget(bottom_right)


        # File Selection
        center_anchor = AnchorLayout(anchor_x="center", anchor_y="center", padding=60)
        self.file_list = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.file_list.bind(minimum_height=self.file_list.setter("height"))
        for i in labels.vocab_folder_content:
            if os.path.isfile(os.path.join(labels.vocab_path, i)):
                voc_stacks = Button(text=i, size_hint_y=None, height=50)
                voc_stacks.bind(on_release=lambda btn, name=i: self.select_stack(name))
                self.file_list.add_widget(voc_stacks)
        self.scroll = ScrollView(size_hint=(0.7, 0.89), do_scroll_y=True)
        # Wichtig: Breite anpassen, damit kein horizontaler Scroll entsteht
        self.file_list.bind(minimum_width=self.file_list.setter("width"))
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
        self.title_label = Label(text=labels.settings_title_font_size_slider_test_label, font_size = config["settings"]["gui"]["title_font_size"],
                                 size_hint_y=None, height=80)
        title_size_slider = NoScrollSlider(min=10, max=80,
                                           value=int(config["settings"]["gui"]["title_font_size"]),
                                           size_hint_y=None, height=40)
        title_size_slider.bind(value=self.on_slider_value)
        settings_content.add_widget(self.title_label)
        settings_content.add_widget(title_size_slider)
        scroll.add_widget(settings_content)
        self.window.add_widget(scroll)


        #Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=self.main_menu)
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


    def select_stack(self, stack):
        vocab_file = str("vocab/" + stack)
        vocab_current = save.load_vocab(vocab_file)

        self.window.clear_widgets()
        self.scroll = ScrollView(size_hint=(1, 1))


        #Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=self.main_menu)
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


    def add_stack(self, instance):
        self.window.clear_widgets()
        log("opened add stack menu")


        #Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=self.main_menu)
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


        #Add label text
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=30)
        add_stack_label = Label(text=labels.add_stack_title_text,
                                font_size=int(config["settings"]["gui"]["title_font_size"]),
                                size_hint=(None, None), size=(80, 40))
        top_center.add_widget(add_stack_label)
        self.window.add_widget(top_center)

        # Scrollable list for entering stack name and languages
        center_center = AnchorLayout(anchor_x="center", anchor_y="center", padding=80)
        scroll = ScrollView(size_hint=(1, 1))

        form_layout = GridLayout(cols=1, spacing=15, padding=30, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # stack name
        form_layout.add_widget(Label(text=labels.add_stack_filename, size_hint_y=None, height=30))
        self.stack_input = TextInput(size_hint_y=None, height=60, multiline=False)
        stack_input_text = self.stack_input.text
        form_layout.add_widget(self.stack_input)

        # own language
        form_layout.add_widget(Label(text=labels.add_own_language, size_hint_y=None, height=30))
        self.own_language_input = TextInput(size_hint_y=None, height=60, multiline=False)
        own_language_input_text = self.own_language_input.text
        form_layout.add_widget(self.own_language_input)

        # foreign language
        form_layout.add_widget(Label(text=labels.add_foreign_language, size_hint_y=None, height=30))
        self.foreign_language_input = TextInput(size_hint_y=None, height=60, multiline=False)
        foreign_language_input_text = self.foreign_language_input.text
        form_layout.add_widget(self.foreign_language_input)

        # 3 columns
        row=GridLayout(cols=2, size_hint_y=None, height= 40, spacing=10)
        row.add_widget(Label(text=labels.three_digit_toggle, size_hint_y=None, height=30))
        self.three_columns = CheckBox(active=False, size_hint=(None, None), size=(45, 45))
        self.three_columns.bind(active=self.three_column_checkbox)
        row.add_widget(self.three_columns)
        form_layout.add_widget(row)

        #add stack button
        spacing=Label(text=" \n ")
        form_layout.add_widget(spacing)
        add_stack_button = Button(text=labels.add_stack_button_text,padding=30, size_hint=(1, None), height=70)
        add_stack_button.bind(on_press=self.add_stack_button_func)
        form_layout.add_widget(add_stack_button)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


        #Add label at bottom in case of error while adding stack
        self.bottom_center = AnchorLayout(anchor_x="center", anchor_y="bottom", padding=30)
        self.add_stack_error_label = Label(
            text="",
            font_size=int(config["settings"]["gui"]["title_font_size"]),
            size_hint=(None, None),
            size=(300, 40)
        )
        self.bottom_center.add_widget(self.add_stack_error_label)
        self.window.add_widget(self.bottom_center)


    def on_slider_value(self, instance, value):
        config["settings"]["gui"]["title_font_size"] = int(value)
        log("slider moved, config variable updated")
        save.save_settings(config)
        log("config variable saved to config.yml")


    def add_stack_button_func(self, instance=None):
        # reading textbox_content
        actual_stackname, actual_own_language, actual_foreign_language = "", "", ""
        log("loading, checkbox content")
        stackname = self.stack_input.text
        own_language = self.own_language_input.text
        foreign_language = self.foreign_language_input.text
        log("done.")
        log("saving file")
        if stackname and own_language and foreign_language:
            actual_own_language, actual_foreign_language = own_language, foreign_language
            if stackname[-4:] == ".csv":
                actual_stackname = stackname
            else:
                actual_stackname = str(stackname + ".csv")
            if os.path.isfile("vocab/" + actual_stackname) == False:
                os.mknod("vocab/" + actual_stackname)
                log("created file")
                save.change_languages("vocab/" + actual_stackname, str(actual_own_language),
                                      str(actual_foreign_language))
                log("added language info")
                log("creating finished")
                self.main_menu()
            else:
                log("saving failed, file already exists. trying again...")
                bottom_center = AnchorLayout(anchor_x="center", anchor_y="bottom", padding=30)
                add_stack_label = Label(text=labels.add_stack_title_text_exists,
                                        font_size=int(config["settings"]["gui"]["title_font_size"]),
                                        size_hint=(None, None), size=(80, 40))
                self.add_stack_error_label.text = labels.add_stack_title_text_exists
        else:
            log("saving failed, one or more box empty. trying again...")
            bottom_center = AnchorLayout(anchor_x="center", anchor_y="bottom", padding=30)
            add_stack_label = Label(text=labels.add_stack_title_text_empty,
                                    font_size=int(config["settings"]["gui"]["title_font_size"]),
                                    size_hint=(None, None), size=(80, 40))
            self.add_stack_error_label.text = labels.add_stack_title_text_empty


    def three_column_checkbox(self, instance=None, value=None):
        if value:
            three_columns_check=True
        else:
            three_columns_check=False


    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        return False



if __name__ == "__main__":
    VokabaApp().run()