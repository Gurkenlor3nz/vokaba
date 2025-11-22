import csv
import yaml

def save_to_vocab(vocab, filename, own_lang="Deutsch", foreign_lang="Englisch", latin_lang="Latein", latin_active=False):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        # Metadaten oben als Kommentarzeilen
        f.write(f"# own_language={own_lang}\n")
        f.write(f"# foreign_language={foreign_lang}\n")
        f.write(f"# latin_language={latin_lang}\n")
        f.write(f"# latin_active={str(latin_active)}\n")

        # jetzt 4 Spalten (latein optional)
        writer = csv.DictWriter(
            f,
            fieldnames=["own_language", "foreign_language", "latin_language", "info", "learn_level"]
        )
        writer.writeheader()

        for row in vocab:
            if "latin_language" not in row:
                row["latin_language"] = ""
            if "info" not in row:
                row["info"] = ""
            if "learn_level" not in row or row["learn_level"] == "":
                row["learn_level"] = "0"
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
        latin_active=latin_active
    )



def load_settings():
    #Load config from config.yml and set settings variables
    with open("config.yml", "r") as file:
        config_readable = yaml.safe_load(file)
    return config_readable


def save_settings(config):
    # Save Settings
    with open("config.yml", "w") as file:
        yaml.dump(config, file)
