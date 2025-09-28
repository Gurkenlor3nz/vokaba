"""------Import Python packages------"""
from datetime import datetime
import os
import os.path
import yaml


"""------Import kivy widgets------"""
from kivy.app import App
from kivy.config import Config
from kivy.core.window import Window
from kivy.clock import Clock

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import *
from kivy.uix.textinput import TextInput



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
        if not os.path.exists("vocab"): os.makedirs("vocab")
        for i in os.listdir(labels.vocab_path):
            if os.path.isfile(os.path.join(labels.vocab_path, i)):
                voc_stacks = Button(text=i[:-4], size_hint_y=None, height=50)
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
        self.title_label = Label(text=labels.settings_title_font_size_slider_test_label,
                                 font_size = config["settings"]["gui"]["title_font_size"],
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
        if "tuple" in str(type(vocab_current)): vocab_current = vocab_current[0]
        log("opened stack: " + stack)
        self.window.clear_widgets()
        # Scrollable Grid in Center
        center_anchor = AnchorLayout(anchor_x="center", anchor_y="center", padding=[30, 60, 100, 30])
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        grid = GridLayout(cols=2, spacing=20, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))


        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding=15)
        stack_title_label = Label(text=stack[:-4], font_size=int(config["settings"]["gui"]["title_font_size"]), size_hint=(None, None), size=(40, 40))
        top_center.add_widget(stack_title_label)
        self.window.add_widget(top_center)


        # Back button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=self.main_menu)
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


        # Delete Stack Button
        delete_stack_button = Button(text=labels.delete_stack_button, size_hint_y=None, height=80)
        delete_stack_button.bind(on_press=lambda instance: self.delete_stack_confirmation(stack))
        grid.add_widget(delete_stack_button)


        # Edit Vocab Metadata
        edit_metadata_button = Button(text=labels.edit_metadata_button_text, size_hint_y=None, height=80)
        edit_metadata_button.bind(on_press=lambda instance: self.edit_metadata(stack))
        grid.add_widget(edit_metadata_button)


        # Add Vocab Button
        add_vocab_button = Button(text=labels.add_vocab_button_text, size_hint_y=None, height=80)
        add_vocab_button.bind(on_press=lambda instance: self.add_vocab(stack, vocab_current))
        grid.add_widget(add_vocab_button)


        # Edit Vocab Button
        edit_vocab_button = Button(text=labels.edit_vocab_button_text, size_hint_y=None, height=80)
        edit_vocab_button.bind(on_press=lambda instance: self.edit_vocab(stack, vocab_current))
        grid.add_widget(edit_vocab_button)


        scroll.add_widget(grid)
        center_anchor.add_widget(scroll)
        self.window.add_widget(center_anchor)


    def delete_stack_confirmation(self, stack, instance=None):
        log("Entered delete stack Confirmation")
        self.window.clear_widgets()

        #Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=lambda instance: self.select_stack(stack))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


        #Cancel
        top_right = AnchorLayout(anchor_x="center", anchor_y="top", padding=[30, 30, 100, 30])
        back_button = Button(font_size=50, size_hint_y=None, text=labels.cancel)
        back_button.bind(on_press=lambda instance: self.select_stack(stack))
        top_right.add_widget(back_button)

        center_center = AnchorLayout(anchor_x="left", anchor_y="top", padding=[30, 130, 30, 30])
        delete_button = Button(font_size=30, size_hint=(None, None), size=(150, 80), text=labels.delete, markup=True)
        delete_button.bind(on_press=lambda instance: self.delete_stack(stack))
        center_center.add_widget(delete_button)
        top_right.add_widget(center_center)

        self.window.add_widget(top_right)


        #Caution labels
        top_center = AnchorLayout(anchor_x="center", anchor_y="top")
        caution_labels = BoxLayout(orientation="vertical", padding = 30)
        cauton_text = Label(text=labels.caution, markup=True, size_hint_y=None,
                            font_size=int(config["settings"]["gui"]["title_font_size"]))
        deleting_text = Label(text=labels.delete_stack_confirmation_text, markup=True, size_hint_y=None,
                              font_size=int(config["settings"]["gui"]["title_font_size"]))
        not_undone_text = Label(text=labels.cant_be_undone, markup=True, size_hint_y=None,
                                font_size=int(config["settings"]["gui"]["title_font_size"]))
        caution_labels.add_widget(cauton_text)
        caution_labels.add_widget(deleting_text)
        caution_labels.add_widget(not_undone_text)


        top_center.add_widget(caution_labels)
        self.window.add_widget(top_center)


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
        log("starting save")
        stackname = self.stack_input.text.strip()
        own_language = self.own_language_input.text.strip()
        foreign_language = self.foreign_language_input.text.strip()
        latin_active = self.three_columns.active  # Checkbox auslesen
        log("reading textbox finished")

        if stackname and own_language and foreign_language:
            # Checking for .csv
            if stackname[-4:] == ".csv":
                actual_stackname = stackname
            else:
                actual_stackname = str(stackname + ".csv")

            if not os.path.isfile("vocab/" + actual_stackname):
                os.mknod("vocab/" + actual_stackname)
                log(f"Created file: {actual_stackname}")

                save.save_to_vocab(
                    vocab=[],
                    filename="vocab/" + actual_stackname,
                    own_lang=own_language,
                    foreign_lang=foreign_language,
                    latin_lang="Latein",
                    latin_active=latin_active)
                log("Added language info and Latin column state")
                self.main_menu()
            else:
                log("Saving failed, file already exists.")
                self.add_stack_error_label.text = labels.add_stack_title_text_exists
        else:
            log("Saving failed, one or more input boxes empty.")
            self.add_stack_error_label.text = labels.add_stack_title_text_empty


    def add_vocab(self, stack, vocab, instance=None):
        log("entered add vocab")
        self.window.clear_widgets()

        # Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=lambda instance: self.select_stack(stack))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        center_center = AnchorLayout(anchor_x="center", anchor_y="center", padding=80)
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(cols=1, spacing=15, padding=30, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        # Own language
        form_layout.add_widget(Label(text=labels.add_own_language, font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text=""))
        self.add_own_language = TextInput(size_hint_y=None, height=60, multiline=False)
        form_layout.add_widget(self.add_own_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Foreign language
        form_layout.add_widget(Label(text=labels.add_foreign_language, font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text=""))
        self.add_foreign_language = TextInput(size_hint_y=None, height=60, multiline=False)
        form_layout.add_widget(self.add_foreign_language)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Latin language
        self.third_column_input = None
        if save.read_languages("vocab/"+stack)[3]:
            form_layout.add_widget(Label(text=labels.add_third_column, font_size=int(config["settings"]["gui"]["title_font_size"])))
            form_layout.add_widget(Label(text=""))
            self.third_column_input = TextInput(size_hint_y=None, height=60, multiline=False)
            form_layout.add_widget(self.third_column_input)

        form_layout.add_widget(Label(text="\n\n\n\n"))

        # Additional Info
        form_layout.add_widget(Label(text=labels.add_additional_info, font_size=int(config["settings"]["gui"]["title_font_size"])))
        form_layout.add_widget(Label(text=""))
        self.add_additional_info = TextInput(size_hint_y=None, height=60, multiline=False)
        form_layout.add_widget(self.add_additional_info)


        # Add Button
        form_layout.add_widget(Label(text="\n\n\n\n"))
        self.add_vocab_button = Button(text=labels.add_vocabulary_button_text, size_hint_y=None)
        self.add_vocab_button.bind(on_press = lambda instance: self.add_vocab_button_func(vocab, stack))
        form_layout.add_widget(self.add_vocab_button)

        if self.third_column_input:
            self.widgets_add_vocab = [self.add_own_language, self.add_foreign_language, self.third_column_input, self.add_additional_info, self.add_vocab_button]
        else:
            self.widgets_add_vocab = [self.add_own_language, self.add_foreign_language, self.add_additional_info, self.add_vocab_button]

        Window.bind(on_key_down=self.on_key_down)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


    def add_vocab_button_func(self, vocab, stack, instance=None):
        add_vocab_own_lanauage = self.add_own_language.text
        add_vocab_foreign_language = self.add_foreign_language.text
        if self.third_column_input:  add_vocab_third_column = self.third_column_input.text
        else: add_vocab_third_column=None
        add_vocab_additional_info = self.add_additional_info.text
        log("Adding Vocab. Loaded textbox content")
        if self.third_column_input:
            vocab.append({'own_language' : add_vocab_own_lanauage,
                          'foreign_language' : add_vocab_foreign_language,
                          'latin_language' : add_vocab_third_column,
                          'info' : add_vocab_additional_info})
        else:
            vocab.append({'own_language' : add_vocab_own_lanauage,
                          'foreign_language' : add_vocab_foreign_language,
                          'info' : add_vocab_additional_info})

        save.save_to_vocab(vocab, "vocab/"+stack)
        print("added to stack")
        self.clear_inputs()

    def edit_metadata(self, stack, instance=None):
        log("entered edit metadata menu")
        self.window.clear_widgets()
        metadata = save.read_languages("vocab/"+stack)


        center_center = AnchorLayout(anchor_x="center", anchor_y="center", padding=80)
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(cols=1, spacing=15, padding=30, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        #Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=lambda instance: self.select_stack(stack))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)


        self.edit_own_language_textbox = TextInput(size_hint_y=None, height=60, multiline=False, text=metadata[0])
        form_layout.add_widget(self.edit_own_language_textbox)

        self.edit_foreign_language_textbox = TextInput(size_hint_y=None, height=60, multiline=False, text=metadata[1])
        form_layout.add_widget(self.edit_foreign_language_textbox)


        form_layout.add_widget(Label(text="\n\n\n\n"))
        add_vocab_button = Button(text=labels.save, size_hint_y=None)
        add_vocab_button.bind(on_press = lambda instance: self.edit_metadata_func(stack))
        form_layout.add_widget(add_vocab_button)

        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)


    def edit_vocab(self, stack, vocab, instance=None):
        log("entered edit vocab menu")
        self.window.clear_widgets()
        center_center = AnchorLayout(anchor_x="center", anchor_y="center", padding=80)
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = GridLayout(cols=1, spacing=15, padding=30, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))

        #Back Button
        top_right = AnchorLayout(anchor_x="right", anchor_y="top", padding=30)
        back_button = Button(font_size=40, size_hint=(None, None),
                             size=(64, 64), background_normal="assets/back_button.png")
        back_button.bind(on_press=lambda instance: self.select_stack(stack))
        top_right.add_widget(back_button)
        self.window.add_widget(top_right)

        matrix = self.build_vocab_grid(form_layout, vocab, save.read_languages("vocab/"+stack)[3])


        #Save all button
        top_center = AnchorLayout(anchor_x="center", anchor_y="top", padding = [30, 30, 100, 30])
        save_all_button = Button(text=labels.save, size_hint_y=0.08)
        save_all_button.bind(on_press=lambda instance: self.edit_vocab_func(matrix, stack))
        top_center.add_widget(save_all_button)
        self.window.add_widget(top_center)
        print(vocab)


        scroll.add_widget(form_layout)
        center_center.add_widget(scroll)
        self.window.add_widget(center_center)

    def edit_vocab_func(self, matrix, stack, instance=None):
        vocab = self.read_vocab_from_grid(matrix, save.read_languages("vocab/"+stack)[3])
        save.save_to_vocab(vocab, "vocab/"+stack)
        log("saved vocab")
        self.select_stack(stack)

    def edit_metadata_func(self, stack, instance=None):
        save.change_languages("vocab/"+stack, self.edit_own_language_textbox.text, self.edit_foreign_language_textbox.text, "Latein")
        self.select_stack(stack)

    def clear_inputs(self):
        self.add_own_language.text = ""
        self.add_foreign_language.text = ""
        if self.third_column_input:
            self.third_column_input.text = ""
        self.add_additional_info.text = ""
        self.add_own_language.focus = True

    def delete_stack(self, stack, instance=None):
        os.remove("vocab/"+stack)
        log("deleted stack: "+stack)
        self.main_menu()

    def on_key_down(self, window, key, scancode, codepoint, modifiers):
        # Prüfe, ob ein TextInput fokussiert ist
        focused_index = None
        for i, widget in enumerate(self.widgets_add_vocab):
            if hasattr(widget, 'focus') and widget.focus:
                focused_index = i
                break

        # Wenn nichts fokussiert ist, fokus auf das erste TextInput
        if focused_index is None:
            for widget in self.widgets_add_vocab:
                if hasattr(widget, 'focus'):
                    widget.focus = True
                    return True

        # Tab / Shift+Tab Handling
        if key == 9:  # Tab
            if focused_index is not None:
                if 'shift' in modifiers:  # Shift+Tab rückwärts
                    next_index = (focused_index - 1) % len(self.widgets_add_vocab)
                else:
                    next_index = (focused_index + 1) % len(self.widgets_add_vocab)
                self.widgets_add_vocab[next_index].focus = True
            return True

        # Enter drücken
        if key == 13:  # Enter
            if focused_index is not None:
                current = self.widgets_add_vocab[focused_index]
                if isinstance(current, TextInput):
                    self.widgets_add_vocab[-1].trigger_action(duration=0.1)
            return True

        return False

    def read_vocab_from_grid(self, textinput_matrix, latin_active):
        vocab_list = []

        for row in textinput_matrix:
            # Werte holen
            if latin_active:
                own, foreign, latin, info = [ti.text.strip() for ti in row]
            else:
                own, foreign, info = [ti.text.strip() for ti in row]
                latin = ""

            # ✅ Leere Zeilen automatisch überspringen
            if not own and not foreign and not latin and not info:
                continue

            vocab_list.append({
                "own_language": own,
                "foreign_language": foreign,
                "latin_language": latin,
                "info": info
            })

        return vocab_list


    def build_vocab_grid(self, parent_layout, vocab_list, latin_active):
        """
        parent_layout = z.B. ein BoxLayout oder Screen, in den das Grid eingefügt wird
        latin_active = None -> KEINE latin-Spalte
        latin_active = "Latein" (oder egal was) -> Spalte anzeigen
        """

        # Spaltenanzahl bestimmen
        cols = 4 if latin_active else 3

        grid = GridLayout(cols=cols, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))  # wichtig für ScrollView

        textinput_matrix = []

        for vocab in vocab_list:
            row = []

            # Basis-Spalten
            for key in ["own_language", "foreign_language"]:
                ti = TextInput(text=vocab.get(key, ""), multiline=False, size_hint_y=None, height=60)
                grid.add_widget(ti)
                row.append(ti)

            # Latein nur, wenn aktiv
            if latin_active:
                ti = TextInput(text=vocab.get("latin_language", ""), multiline=False, size_hint_y=None, height=60)
                grid.add_widget(ti)
                row.append(ti)

            # Info-Feld immer zuletzt
            ti = TextInput(text=vocab.get("info", ""), multiline=False, size_hint_y=None, height=60)
            grid.add_widget(ti)
            row.append(ti)

            textinput_matrix.append(row)

        parent_layout.add_widget(grid)
        return textinput_matrix

    def bind_keyboard(self, dt):
        Window.bind(on_key_down=self.on_key_down)


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