#!/usr/bin/env bash
#
# dump_repo.sh
# Erstellt eine einzige strukturierte Textdatei
# mit allen Python-Dateien im Repository.
#
# usage: ./dump_repo.sh > repo_dump.txt
#

# Git-Pfad (falls du nicht im Repo bist)
REPO_ROOT="."

# Ausschluss-Pattern (optional erweitern)
EXCLUDES=(
  ".git"
  "__pycache__"
  "venv"
  ".venv"
  "env"
  "build"
  "dist"
)

# Erzeuge eine find-Filterkette
ignore_args=()
for ex in "${EXCLUDES[@]}"; do
  ignore_args+=(-path "*/$ex/*" -prune -o)
done

# Überschrift
echo "REPO DUMP"
echo "=========="
echo

# Durchsuche alle Python-Dateien
find "$REPO_ROOT" "${ignore_args[@]}" -type f -name "*.py" -print |
while IFS= read -r file; do
  echo
  echo "========================================"
  echo "FILE: $file"
  echo "========================================"
  cat "$file"
  echo
done

echo
echo "EOF"
