import csv
import yaml


def _normalize_knowledge_level(value):
    """
    Normalisiert die 'Wie gut kenne ich das Wort?'-Zahl.

    - fehlend / leer / ungültig -> 0.0
    - Komma wird als Dezimaltrenner akzeptiert
    - Werte außerhalb [0, 1] -> 0.0
    """
    if value is None:
        return 0.0

    # Bereits numerisch?
    if isinstance(value, (int, float)):
        v = float(value)
    else:
        s = str(value).strip()
        if not s:
            return 0.0
        # deutsches Komma zulassen
        s = s.replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            return 0.0

    if 0.0 <= v <= 1.0:
        return v
    return 0.0


def save_to_vocab(
    vocab,
    filename,
    own_lang="Deutsch",
    foreign_lang="Englisch",
    latin_lang="Latein",
    latin_active=False,
):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        # Metadaten oben als Kommentarzeilen
        f.write(f"# own_language={own_lang}\n")
        f.write(f"# foreign_language={foreign_lang}\n")
        f.write(f"# latin_language={latin_lang}\n")
        f.write(f"# latin_active={str(latin_active)}\n")

        # JETZT 8 Spalten: 3 Sprachen + info + knowledge_level + SRS
        fieldnames = [
            "own_language",
            "foreign_language",
            "latin_language",
            "info",
            "knowledge_level",
            "srs_streak",
            "srs_last_seen",
            "srs_due",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",  # falls später noch mehr Felder dazu kommen
        )
        writer.writeheader()

        for row in vocab:
            # fehlende Felder auffüllen
            if "latin_language" not in row:
                row["latin_language"] = ""
            if "info" not in row:
                row["info"] = ""

            # knowledge_level normalisieren
            row["knowledge_level"] = _normalize_knowledge_level(
                row.get("knowledge_level", 0.0)
            )

            # SRS-Felder robust setzen
            # streak: immer int, ansonsten 0
            try:
                streak = int(row.get("srs_streak", 0) or 0)
            except (TypeError, ValueError):
                streak = 0
            row["srs_streak"] = streak

            # Zeiten als Strings (ISO-Format oder leer)
            last_seen = row.get("srs_last_seen") or ""
            due = row.get("srs_due") or ""
            row["srs_last_seen"] = str(last_seen) if last_seen else ""
            row["srs_due"] = str(due) if due else ""

            writer.writerow(row)


def load_vocab(filename):
    vocab = []
    own_lang = None
    foreign_lang = None
    latin_lang = None
    latin_active = False

    with open(filename, "r", encoding="utf-8") as f:
        lines = []
        for line in f:
            if line.startswith("# own_language="):
                own_lang = line.strip().split("=", 1)[1]
            elif line.startswith("# foreign_language="):
                foreign_lang = line.strip().split("=", 1)[1]
            elif line.startswith("# latin_language="):
                latin_lang = line.strip().split("=", 1)[1]
            elif line.startswith("# latin_active="):
                latin_active = line.strip().split("=", 1)[1].lower() == "true"
            else:
                lines.append(line)

        reader = csv.DictReader(lines)
        for row in reader:
            if "latin_language" not in row:
                row["latin_language"] = ""
            if "info" not in row:
                row["info"] = ""

            # NEU: Failsafe für knowledge_level
            if "knowledge_level" in row:
                row["knowledge_level"] = _normalize_knowledge_level(
                    row.get("knowledge_level")
                )
            else:
                # alte CSVs ohne Spalte -> 0.0
                row["knowledge_level"] = 0.0

            vocab.append(row)

    return vocab, own_lang, foreign_lang, latin_lang, latin_active


def read_languages(filename):
    """Nur die Sprach-Metadaten lesen"""
    own_lang = None
    foreign_lang = None
    latin_lang = None
    latin_active = False

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# own_language="):
                own_lang = line.strip().split("=", 1)[1]
            elif line.startswith("# foreign_language="):
                foreign_lang = line.strip().split("=", 1)[1]
            elif line.startswith("# latin_language="):
                latin_lang = line.strip().split("=", 1)[1]
            elif line.startswith("# latin_active="):
                latin_active = line.strip().split("=", 1)[1].lower() == "true"
            if own_lang and foreign_lang and latin_lang:
                # trotzdem nicht abbrechen -> latin_active evtl. weiter unten
                continue

    return own_lang, foreign_lang, latin_lang, latin_active


def change_languages(filename, new_own, new_foreign, new_latin, latin_active=False):
    """Sprach-Metadaten überschreiben, Vokabeln unverändert lassen"""
    vocab, _, _, _, _ = load_vocab(filename)
    save_to_vocab(
        vocab,
        filename,
        own_lang=new_own,
        foreign_lang=new_foreign,
        latin_lang=new_latin,
        latin_active=latin_active,
    )


def load_settings():
    # Load config from config.yml and set settings variables
    with open("config.yml", "r") as file:
        config_readable = yaml.safe_load(file)
    return config_readable


def save_settings(config):
    # Save Settings
    with open("config.yml", "w") as file:
        yaml.dump(config, file)



def persist_single_entry(vocab, stack_vocab_lists, stack_meta_map, entry_to_stack_file):
    """
    Speichert genau den Stack, zu dem der gegebene Vokabel-Eintrag gehört.

    - vocab: das Dict der aktuellen Vokabel
    - stack_vocab_lists: dict[filename] -> Liste von Vokabel-Einträgen
    - stack_meta_map: dict[filename] -> (own_lang, foreign_lang, latin_lang, latin_active)
    - entry_to_stack_file: dict[id(entry)] -> filename
    """
    if vocab is None:
        return

    filename = entry_to_stack_file.get(id(vocab))
    if not filename:
        return

    vocab_list = stack_vocab_lists.get(filename)
    if vocab_list is None:
        return

    # evtl. alte Helper-Felder entfernen
    for entry in vocab_list:
        if isinstance(entry, dict):
            entry.pop("_stack_file", None)

    meta = stack_meta_map.get(filename)
    if meta is None:
        own_lang, foreign_lang, latin_lang, latin_active = read_languages(filename)
    else:
        own_lang, foreign_lang, latin_lang, latin_active = meta

    save_to_vocab(
        vocab_list,
        filename,
        own_lang=own_lang or "Deutsch",
        foreign_lang=foreign_lang or "Englisch",
        latin_lang=latin_lang or "Latein",
        latin_active=latin_active,
    )


def persist_all_stacks(stack_vocab_lists, stack_meta_map):
    """
    Speichert alle übergebenen Stacks zurück auf die Festplatte.

    - stack_vocab_lists: dict[filename] -> Liste von Vokabel-Einträgen
    - stack_meta_map: dict[filename] -> (own_lang, foreign_lang, latin_lang, latin_active)
    """
    if not stack_vocab_lists:
        return

    for filename, vocab_list in stack_vocab_lists.items():
        if vocab_list is None:
            continue

        for entry in vocab_list:
            if isinstance(entry, dict):
                entry.pop("_stack_file", None)

        meta = stack_meta_map.get(filename)
        if meta is None:
            own_lang, foreign_lang, latin_lang, latin_active = read_languages(filename)
        else:
            own_lang, foreign_lang, latin_lang, latin_active = meta

        save_to_vocab(
            vocab_list,
            filename,
            own_lang=own_lang or "Deutsch",
            foreign_lang=foreign_lang or "Englisch",
            latin_lang=latin_lang or "Latein",
            latin_active=latin_active,
        )

