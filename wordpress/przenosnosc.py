#!/usr/bin/env python3
"""Sprawdza, co z zawartosci stron przetrwa import do WordPressa.

Po imporcie paczki WXR czesc tresci potrafi zniknac albo przestac
dzialac, i to nie na kazdej instalacji tak samo — stad wrazenie, ze
"na innym komputerze sie psuje". Sa trzy niezalezne przyczyny:

1. FILTR KSES.
   WordPress przepuszcza tresc wpisu przez wp_kses_post() dla kazdego,
   kto nie ma uprawnienia "unfiltered_html". Lista dozwolonych
   znacznikow nie zawiera <style> ani <script>. Uprawnienie to maja
   administratorzy i redaktorzy pojedynczej instalacji, ale NIE maja go:
     - administratorzy w trybie wielowitrynowym (multisite) — tam ma
       je tylko super admin,
     - uzytkownicy hostingow, ktore je wylaczaja (m.in. WordPress.com
       w nizszych planach),
     - wszyscy tam, gdzie wtyczka bezpieczenstwa je odbiera.
   Importer WXR zapisuje wpisy przez wp_insert_post(), wiec ten sam
   filtr dziala takze w czasie importu. Efekt: strona wchodzi bez
   arkusza stylow i bez kalkulatora — czyli "polowa rzeczy nie dziala".

2. SCIEZKI DO MEDIOW.
   W tresci stoi /wp-content/uploads/nazwa.jpg. WordPress domyslnie
   uklada wgrane pliki w podkatalogach rocznik/miesiac, wiec po wgraniu
   ten sam plik lezy pod /wp-content/uploads/2026/08/nazwa.jpg.
   Adres z tresci trafia w pustke i zdjecia oraz filmy sie nie
   pokazuja.

3. WYROWNANIE "alignfull".
   Sekcje na calą szerokosc dzialaja tylko w motywie, ktory zglasza
   obsluge szerokich wyrownan. W motywie bez niej pasy koncza sie na
   szerokosci tresci.

Skrypt nie zmienia plikow — wypisuje, co i gdzie jest zagrozone.

Uruchomienie:  python3 wordpress/przenosnosc.py
"""

import re
import sys
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
ZRODLA = KORZEN / "wordpress"

PLIKI = [
    ZRODLA / "pediatria-gutenberg.html",
    ZRODLA / "medycyna-estetyczna-gutenberg.html",
]

# Znaczniki, ktorych nie ma na liscie $allowedposttags WordPressa.
# Tresc w nich zawarta znika w calosci razem ze znacznikiem.
USUWANE = ("style", "script", "iframe", "form", "input", "button", "svg")


def bloki(tresc, nazwa):
    """Zwraca (numer_wiersza, dlugosc) dla kazdego wystapienia znacznika."""
    wynik = []
    for m in re.finditer(r"<%s\b[^>]*>(.*?)</%s>" % (nazwa, nazwa), tresc,
                         re.S | re.I):
        wiersz = tresc.count("\n", 0, m.start()) + 1
        wynik.append((wiersz, len(m.group(0))))
    return wynik


def sprawdz(sciezka):
    tresc = sciezka.read_text(encoding="utf-8")
    print("=" * 68)
    print(sciezka.name)
    print("=" * 68)

    print("\n1. Znaczniki usuwane przez filtr kses")
    lacznie = 0
    for nazwa in USUWANE:
        znalezione = bloki(tresc, nazwa)
        if not znalezione:
            continue
        znakow = sum(d for _, d in znalezione)
        lacznie += znakow
        wiersze = ", ".join(str(w) for w, _ in znalezione[:6])
        if len(znalezione) > 6:
            wiersze += ", ..."
        print("   <%-7s> %2d szt., %6d znakow  (wiersze %s)"
              % (nazwa, len(znalezione), znakow, wiersze))
    procent = 100.0 * lacznie / max(len(tresc), 1)
    print("   RAZEM do stracenia: %d z %d znakow tresci (%.0f%%)"
          % (lacznie, len(tresc), procent))

    print("\n2. Sciezki do mediow")
    media = sorted(set(re.findall(
        r"/wp-content/uploads/([\w-]+\.(?:jpg|jpeg|png|webp|gif|svg|mp4|webm))",
        tresc)))
    print("   %d plikow, wszystkie jako /wp-content/uploads/<nazwa>:" % len(media))
    for m in media:
        print("     ", m)
    print("   Po wgraniu do Biblioteki mediow WordPress domyslnie dopisze")
    print("   do sciezki rocznik i miesiac, wiec te adresy trzeba podmienic")
    print("   (build.py --media <adres> robi to jednym przebiegiem).")

    print("\n3. Wyrownanie na cala szerokosc")
    print("   alignfull: %d wystapien — wymaga motywu z obsluga szerokich"
          % tresc.count("alignfull"))
    print("   wyrownan (add_theme_support('align-wide')).")
    print()


def main():
    for p in PLIKI:
        if not p.is_file():
            print("brak pliku:", p, file=sys.stderr)
            return 1
        sprawdz(p)
    print("Co z tym zrobic — patrz wordpress/INSTRUKCJA.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
