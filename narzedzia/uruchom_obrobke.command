#!/bin/bash
# Uruchomienie na macOS: dwuklik w Finderze albo `bash uruchom_obrobke.command`.
# Tworzy izolowane środowisko Pythona (bez zmian w systemowym Pythonie),
# instaluje Pillow, numpy i rawpy, po czym przetwarza wszystkie zdjęcia.
set -e
KATALOG="$(cd "$(dirname "$0")" && pwd)"
VENV="${TMPDIR:-/tmp}/obrobka_zdjec_venv"

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet pillow numpy
"$VENV/bin/python" -m pip install --quiet rawpy || echo "UWAGA: rawpy nie zainstalowane — pliki RAW zostaną pominięte z błędem."

"$VENV/bin/python" "$KATALOG/obrobka_zdjec.py" \
  "$HOME/Desktop/Chemia Przyszłości 2026" \
  "$HOME/Desktop/Po obróbce chemia" "$@"

echo
read -n 1 -s -r -p "Naciśnij dowolny klawisz, aby zamknąć…"
