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

        # jetzt 5 Spalten: 3 Sprachen + info + knowledge_level
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "own_language",
                "foreign_language",
                "latin_language",
                "info",
                "knowledge_level",
            ],
        )
        writer.writeheader()

        for row in vocab:
            if "latin_language" not in row:
                row["latin_language"] = ""
            if "info" not in row:
                row["info"] = ""

            # NEU: knowledge_level immer setzen und normalisieren
            row["knowledge_level"] = _normalize_knowledge_level(
                row.get("knowledge_level", 0.0)
            )

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
