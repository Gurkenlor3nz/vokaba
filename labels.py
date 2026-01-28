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

settings_title_text = "Einstellungen"
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

#----------------------------------------------------------------------------
# Colour changer labels
#----------------------------------------------------------------------------
settings_theme_header = "Farbschema (Theme)"
settings_theme_dark = "Dark"
settings_theme_light = "Light"
settings_theme_custom_header = "Individuelle Farben (optional)"
settings_theme_primary = "Primärfarbe"
settings_theme_accent = "Akzentfarbe"
settings_theme_reset = "Zurücksetzen"

# ---------------------------------------------------------------------------
# Knowledge-level deltas für verschiedene Übungstypen
# ---------------------------------------------------------------------------

knowledge_delta_self_very_easy = 0.35
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


# ---------------------------------------------------------------------------
# About / Über Vokaba
# ---------------------------------------------------------------------------


about_title = "Über Vokaba"

about_intro = (
    "Vokaba ist ein super-minimalistischer Vokabeltrainer für Menschen, "
    "die lieber lernen als sich durch Menüs zu klicken.\n\n"
    "Kein Account, keine Werbung, kein Cloud-Zwang – nur deine Stacks, "
    "ein klares Interface und ein Lernsystem, das sich an dich anpasst."
)

about_heading_learning = "Was Vokaba unter der Haube macht"

about_bullet_adaptive = (
    "• Adaptive Wiederholung: Jede Vokabel hat einen unsichtbaren Wissens-Score. "
    "Was du sicher kannst, siehst du seltener – schwierige Wörter kommen "
    "automatisch öfter dran."
)

about_bullet_modes = (
    "• Abwechslungsreiche Lernmodi: klassische Karten, Multiple Choice, "
    "Buchstabensalat, Silben-Modus und Tipp-Eingabe. Vokaba wechselt die Modi "
    "für dich, damit dein Gehirn wach bleibt."
)

about_bullet_csv = (
    "• Offene Daten: Deine Vokabeln liegen in einfachen CSV-Dateien. "
    "Perfekt zum Versionieren, Teilen oder zum Bearbeiten mit eigenen Skripten."
)

about_bullet_design = (
    "• Fokus auf das Wesentliche: Dark/Light-Theme, ein paar Regler – "
    "der Rest ist Platz für deine Inhalte."
)

about_alpha_label = (
    "Diese Version ist ein früher Alpha-Release.\n"
    "Es kann also noch Ecken und Kanten geben – Feedback, Bugreports und "
    "Ideen sind ausdrücklich willkommen."
)

about_heading_discord = "Discord & Support"

about_discord_text = (
    "Wenn etwas crasht, sich komisch anfühlt oder du eine Idee für neue "
    "Funktionen hast, schreib uns gerne auf Discord. Dort gibt es Support, "
    "Bugreports, Feature-Vorschläge und ab und zu Sneak Peeks auf neue Features."
)

about_discord_button = "Zum Discord-Server"

about_discord_link_prefix = "Direkter Link:"

about_ai_disclaimer = "Hinweis: Bei der Entwicklung dieser App wurden KI-Tools verwendet."


# ---------------------------------------------------------------------------
# Statistics / Dashboard
# ---------------------------------------------------------------------------

# Dashboard / Stats
main_stats_label_template = "Stacks: {stacks}   Vokabeln: {total}   Einzigartige Paare: {unique}"
main_stats_hint = ""

# Settings: Sessiongröße
settings_session_size_slider = "Karten pro Lernsitzung"

# Session-Summary
session_summary_title = "Session abgeschlossen"
session_summary_text = (
    "Du hast {done} Karten in dieser Session abgeschlossen.\n"
    "Richtig: {correct}   Schwer / falsch: {wrong}\n"
    "Session-Ziel: {goal} Karten."
)
session_summary_continue_button = "Weiterlernen"
session_summary_back_button = "Zurück zum Hauptmenü"


# Settings: Sessiongröße
settings_session_size_label = "Karten pro Lernsitzung"
settings_session_size_unit = "Karten"

# Dashboard-Texte
dashboard_title = "Dashboard"
dashboard_overview_header = "Überblick"
dashboard_learning_header = "Lernfortschritt"
today_goal = "Heutiges Ziel"

dashboard_overview_stats = "Stapel: {stacks}   Vokabeln: {total}   Einzigartige Paare: {unique}"
dashboard_learned_progress = "Gelernte Vokabeln: {learned}/{total} ({percent:.0f} %)"
dashboard_average_knowledge = "Durchschnittlicher Wissensstand: {avg:.0f} %"
dashboard_time_spent = "Gesamtlernzeit: {time}"

dashboard_hint = "Tipp: Schau ab und zu ins Dashboard, um deinen Fortschritt im Blick zu behalten."

# ---------------------------------------------------------------------------
# Daily goal labels (used in main menu + learning header)
# ---------------------------------------------------------------------------

daily_goal_main_menu_label = "Heutiges Ziel: {done}/{target} Karten"
daily_goal_learn_label = "Heutiges Ziel: {done}/{target} Karten"

# Backwards compatibility (older code paths)
daily_progress_label = "Heutiges Ziel"

# Settings – neue Sektion
settings_stacks_header = "Stapel & Filter"
settings_sort_stacks_by_language = "Stapel nach Sprache sortieren"
settings_global_learn_languages = "Allgemeines Lernen: Sprachen"
settings_global_learn_languages_button = "Sprachen auswählen…"
settings_typing_require_self_rating = "Tippen: Selbstbewertung nach richtig"

# Typing – Auto-Scoring
knowledge_delta_typing_wrong_per_attempt = -0.06
knowledge_delta_typing_first_try_bonus = 0.03
knowledge_delta_typing_fail_penalty = 0.04

export_popup_title = "Export"
export_popup_intro = "Du kannst wählen, ob dein Lernfortschritt in der Exportdatei enthalten sein soll."
export_checkbox_include_progress = "Lernfortschritt (Lernlevel) mit exportieren"
export_hint_reset = (
    "Wenn deaktiviert, wird die Exportdatei zurückgesetzt: "
    "alle Datumswerte werden auf heute gesetzt und alle Lernlevel auf 0.\n"
    "Deine Daten in der App bleiben unverändert."
)
export_confirm_button = "Exportieren"
