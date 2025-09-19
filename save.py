import csv
import yaml

def save_to_vocab(vocab, filename, own_lang="Deutsch", foreign_lang="Englisch"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        # Metadaten oben als Kommentarzeilen
        f.write(f"# own_language={own_lang}\n")
        f.write(f"# foreign_language={foreign_lang}\n")

        writer = csv.DictWriter(f, fieldnames=["own_language", "foreign_language", "info"])
        writer.writeheader()
        writer.writerows(vocab)


def load_vocab(filename):
    vocab = []
    own_lang = None
    foreign_lang = None
    with open(filename, "r", encoding="utf-8") as f:
        lines = []
        for line in f:
            if line.startswith("# own_language="):
                own_lang = line.strip().split("=")[1]
            elif line.startswith("# foreign_language="):
                foreign_lang = line.strip().split("=")[1]
            else:
                lines.append(line)

        reader = csv.DictReader(lines)
        for row in reader:
            vocab.append(row)

    return vocab, own_lang, foreign_lang


def read_languages(filename):
    """Nur die Sprach-Metadaten lesen"""
    own_lang = None
    foreign_lang = None
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# own_language="):
                own_lang = line.strip().split("=")[1]
            elif line.startswith("# foreign_language="):
                foreign_lang = line.strip().split("=")[1]
            if own_lang and foreign_lang:
                break
    return own_lang, foreign_lang


def change_languages(filename, new_own, new_foreign):
    """Sprach-Metadaten überschreiben, Vokabeln unverändert lassen"""
    vocab, _, _ = load_vocab(filename)
    save_to_vocab(vocab, filename, own_lang=new_own, foreign_lang=new_foreign)


def load_settings():
    #Load config from config.yml and set settings variables
    with open("config.yml", "r") as file:
        config_readable = yaml.safe_load(file)
    return config_readable

def save_settings(config):
    # Save Settings
    with open("config.yml", "w") as file:
        yaml.dump(config, file)