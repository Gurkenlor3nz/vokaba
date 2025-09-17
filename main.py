from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window


class WelcomeApp(App):
    def build(self):
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(Label(text="Nein"))
        layout.add_widget(Button(text="klick"))

        Window.title = "Vocabpy"


        return layout


if __name__ == "__main__":
    WelcomeApp().run()
