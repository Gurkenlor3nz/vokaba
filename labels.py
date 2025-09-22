import os

"""Variables"""
vocab_path = "vocab"
if not os.path.exists("vocab"): os.makedirs("vocab")
vocab_folder_content = os.listdir(vocab_path)


"""Texte"""
welcome_text = "Willkommen bei Vokaba"
settings_title_text = "Settings"
settings_title_font_size_slider = "Titelgröße anpassen"
settings_title_font_size_slider_test_label = "Titelgröße"
add_stack_title_text = "Stapel Hinzufügen"
add_stack_title_text_empty = "Fehler: Eine Box ist nicht ausgefüllt"
add_stack_title_text_exists = "Fehler: Dieser Stapelnahme ist schon vergeben"
add_stack_filename = "Stapelname:"
add_own_language = "Eigene Sprache:"
add_foreign_language = "Fremdsprache:"
three_digit_toggle = "            3-Spaltig:"
add_stack_button_text = "Stapel Hinzufügen"