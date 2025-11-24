"""Variables"""
vocab_path = "vocab/"


"""Text labels for the Vokaba UI (German)."""

# ---------------------------------------------------------------------------
# Main / generic UI
# ---------------------------------------------------------------------------

welcome_text = "Vokaba"
save = "Speichern"
cancel = "Abbrechen"
delete = "löschen"
caution = "[color=ff0000]ACHTUNG[/color]"
cant_be_undone = "[color=ff0000]Dies kann nicht rückgängig gemacht werden![/color]"

# ---------------------------------------------------------------------------
# Settings screen
# ---------------------------------------------------------------------------

settings_title_text = "Settings"
settings_title_font_size_slider = "Titelgröße anpassen"
settings_title_font_size_slider_test_label = "Titelgröße"
settings_font_size_slider = "Textgröße anpassen"
settings_padding_multiplikator_slider = "Padding anpassen"

# Preferred key name (used im Code)
settings_modes_header = "Lernmodi"

# Backwards compatibility alias (falls noch irgendwo verwendet):
settings_mode_header = settings_modes_header

# ---------------------------------------------------------------------------
# Stack management (create / delete / metadata)
# ---------------------------------------------------------------------------

add_stack_title_text = "Stapel Hinzufügen"
add_stack_title_text_empty = "Fehler: Eine Box ist nicht ausgefüllt"
add_stack_title_text_exists = "Fehler: Dieser Stapelnahme ist schon vergeben"

add_stack_filename = "Stapelname:"
add_stack_button_text = "Stapel Hinzufügen"

delete_stack_button = "Stapel löschen"
delete_stack_confirmation_text = "Bist du dir sicher? Alle Vokabeln in diesem Stapel werden dauerhaft gelöscht!"

add_own_language = "Eigene Sprache:"
add_foreign_language = "Fremdsprache:"
add_third_column = "Dritte Spalte:"
three_digit_toggle = "            3-Spaltig:"

edit_metadata_button_text = "Metadaten Bearbeiten"

# ---------------------------------------------------------------------------
# Vocab editing / adding
# ---------------------------------------------------------------------------

add_additional_info = "Mehr Infos: "
add_vocabulary_button_text = "Vokabel Hinzufügen"
add_vocab_button_text = "Vokabeln hinzufügen"
edit_vocab_button_text = "Vokabeln Bearbeiten"

# ---------------------------------------------------------------------------
# Learning – general
# ---------------------------------------------------------------------------

learn_stack_vocab_button_text = "Stapel lernen\n(Karteikarten)"

learn_flashcards_front_to_back = (
    "Stapel mit Karteikarten lernen:\nVorderseite -> Hinterseite"
)
learn_flashcards_back_to_front = (
    "Stapel mit Karteikarten lernen:\nHinterseite -> Vorderseite"
)
learn_flashcards_multiple_choice = "Multiple Choice"
learn_flashcards_letter_salad = "Buchstaben Salat"
learn_flashcards_connect_pairs = "Wörter Verbinden"
learn_flashcards_typing_mode = "Übersetzung Eingeben"

no_vocab_warning = "Keine Vokabeln vorhanden. Bitte füge zuerst Vokabeln hinzu."
not_enougn_vocab_warning =  "  [size=12][i](mind. 5 Einträge nötig)[/i][/size]"

# ---------------------------------------------------------------------------
# Different Learning modes
# ---------------------------------------------------------------------------

letter_salad_instruction = "Tippe die Buchstaben in der richtigen Reihenfolge an."
letter_salad_skip = "Überspringen"
letter_salad_reshuffle = "Neu mischen"
connect_pairs_header = "Verbinde die passenden Wörter"
learn_flashcards_syllable_salad = "Silben-Modus"
syllable_salad_instruction = "Klicke die Silben in der richtigen Reihenfolge an."
syllable_salad_reshuffle = "Neu mischen"


# ---------------------------------------------------------------------------
# Knowledge-level deltas für verschiedene Übungstypen
# ---------------------------------------------------------------------------

knowledge_delta_self_very_easy = 0.09
knowledge_delta_self_easy = 0.05
knowledge_delta_self_hard = -0.01
knowledge_delta_self_very_hard = -0.08

knowledge_delta_multiple_choice_correct = 0.07
knowledge_delta_multiple_choice_wrong = -0.06

knowledge_delta_letter_salad_per_correct_letter = 0.01
knowledge_delta_letter_salad_short_word_bonus = 0.02
knowledge_delta_letter_salad_wrong_letter = -0.025

knowledge_delta_connect_pairs_correct_word = 0.06
knowledge_delta_connect_pairs_wrong_word = -0.074

knowledge_delta_typing_correct = 0.093
knowledge_delta_typing_wrong_per_char = -0.01

knowledge_delta_syllable_correct_word = 0.08
knowledge_delta_syllable_wrong_word = -0.05

# ---------------------------------------------------------------------------
# Texte für die Selbstkontrolle (Flashcards)
# ---------------------------------------------------------------------------

self_rating_very_easy = "Sehr einfach"
self_rating_easy = "Einfach"
self_rating_hard = "Schwierig"
self_rating_very_hard = "Sehr schwer"
