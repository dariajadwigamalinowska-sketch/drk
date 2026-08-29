#!/usr/bin/env python3
"""Buduje pliki pochodne z dwoch zrodel blokow Gutenberga.

Zrodlem prawdy sa:
    wordpress/pediatria-gutenberg.html
    wordpress/medycyna-estetyczna-gutenberg.html

Skrypt wytwarza z nich:
  * wordpress/import/*.wordpress.xml  — paczki importu WXR dla WordPressa
  * podglady HTML (poza repozytorium) — samodzielne pliki z mediami
    wklejonymi jako data URI, do obejrzenia w przegladarce bez WordPressa

Uruchomienie:  python3 wordpress/build.py [katalog_na_podglady]
"""

import base64
import mimetypes
import re
import sys
import xml.dom.minidom
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
ZRODLA = KORZEN / "wordpress"
MEDIA = [KORZEN / "assets" / "wideo", KORZEN / "assets" / "grafika"]

STRONY = [
    {
        "blok": ZRODLA / "pediatria-gutenberg.html",
        "xml": ZRODLA / "import" / "pediatria.wordpress.xml",
        "podglad": "pediatria-podglad.html",
        "artefakt": "artefakt-pediatria.html",
        "tytul": "Opieka Pediatryczna Doktor Kasi",
        "tlo": "#F6E3D6",
        "fonty": (
            "https://fonts.googleapis.com/css2?"
            "family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;"
            "0,9..144,600;1,9..144,300;1,9..144,400&"
            "family=Inter:wght@300;400;500;600;700&display=swap"
        ),
    },
    {
        "blok": ZRODLA / "medycyna-estetyczna-gutenberg.html",
        "xml": ZRODLA / "import" / "medycyna-estetyczna.wordpress.xml",
        "podglad": "medycyna-estetyczna-podglad.html",
        "artefakt": "artefakt-estetyczna.html",
        "tytul": "Dr Kasia Aesthetic",
        "tlo": "#FBF8F3",
        "fonty": (
            "https://fonts.googleapis.com/css2?"
            "family=Cormorant+Garamond:wght@300;400;500&"
            "family=Inter:wght@300;400;500;600&display=swap"
        ),
    },
]

# Namiastka arkusza WordPressa. Podglad ma pokazywac to, co zobaczy
# uzytkownik po imporcie, wiec musi odtworzyc te reguly rdzenia, na
# ktorych opieraja sie bloki kolumn, przyciskow i wyrownania.
SHIM = """:root{ color-scheme: light; }
body{ margin:0; background:%(tlo)s; }
.wp-block-columns{ display:flex; gap:2em; flex-wrap:wrap; align-items:normal; }
.wp-block-column{ flex-grow:1; min-width:0; word-break:break-word; }
.wp-block-columns.are-vertically-aligned-center{ align-items:center; }
.wp-block-column.is-vertically-aligned-center{ align-self:center; }
/* Kolumny skladaja sie na telefonie dokladnie tak, jak w rdzeniu
   WordPressa — bez tego podglad klamie i uklad na telefonie wyglada
   inaczej niz na gotowej stronie. */
@media (max-width:781px){
  .wp-block-columns:not(.is-not-stacked-on-mobile)>.wp-block-column{ flex-basis:100%% !important; }
}
@media (min-width:782px){
  .wp-block-columns{ flex-wrap:nowrap !important; }
  .wp-block-columns:not(.is-not-stacked-on-mobile)>.wp-block-column{ flex-basis:0; flex-grow:1; }
  .wp-block-columns:not(.is-not-stacked-on-mobile)>.wp-block-column[style*="flex-basis"]{ flex-grow:0; }
}
.wp-block-columns.is-not-stacked-on-mobile{ flex-wrap:nowrap !important; }
.wp-block-columns.is-not-stacked-on-mobile>.wp-block-column{ flex-basis:0; flex-grow:1; }
.wp-block-columns.is-not-stacked-on-mobile>.wp-block-column[style*="flex-basis"]{ flex-grow:0; }
.has-text-align-center{ text-align:center; }
.has-text-align-right{ text-align:right; }
.alignfull{ width:100%%; }
.wp-block-buttons{ display:flex; gap:12px; flex-wrap:wrap; }
.wp-block-button__link{ display:inline-block; text-decoration:none; }
.wp-block-heading{ text-wrap:balance; }
@media (prefers-reduced-motion:reduce){ *{ animation:none !important; transition:none !important; } }"""


def znajdz_media(nazwa):
    for katalog in MEDIA:
        sciezka = katalog / nazwa
        if sciezka.is_file():
            return sciezka
    return None


def data_uri(sciezka):
    typ = mimetypes.guess_type(sciezka.name)[0] or "application/octet-stream"
    dane = base64.b64encode(sciezka.read_bytes()).decode("ascii")
    return "data:%s;base64,%s" % (typ, dane)


def wstaw_media(html):
    """Zamienia sciezki /wp-content/uploads/... na data URI."""
    brakujace = []

    def zamien(dopasowanie):
        atrybut, nazwa = dopasowanie.group(1), dopasowanie.group(2)
        plik = znajdz_media(nazwa)
        if plik is None:
            brakujace.append(nazwa)
            return dopasowanie.group(0)
        return '%s="%s"' % (atrybut, data_uri(plik))

    wynik = re.sub(
        r'(src|poster)="/wp-content/uploads/([^"]+)"', zamien, html
    )
    return wynik, brakujace


def bez_mapy(html):
    """Wersja dla Artefaktu: ramka mapy nie laduje sie w piaskownicy,
    wiec zostawiamy w jej miejscu zwykly odnosnik."""
    return re.sub(
        r'<iframe[^>]*openstreetmap[^>]*></iframe>',
        '<p style="margin:0;padding:18px 0"><a href="https://www.openstreetmap.org/'
        'search?query=Stanis%C5%82awy+Daneckiej+4%2C+Miech%C3%B3w" '
        'target="_blank" rel="noopener">Zobacz lokalizację na mapie →</a></p>',
        html,
        flags=re.I,
    )


def zbuduj_podglad(strona, tresc):
    return (
        "<!doctype html>\n<html lang=\"pl\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title>\n"
        "<link rel=\"stylesheet\" href=\"%s\">\n"
        "<style>\n%s\n</style>\n</head>\n<body>\n%s\n</body>\n</html>\n"
    ) % (
        strona["tytul"],
        strona["fonty"],
        SHIM % {"tlo": strona["tlo"]},
        tresc,
    )


def zapisz_xml(sciezka_xml, tresc):
    """Podmienia zawartosc content:encoded w istniejacej paczce WXR."""
    paczka = sciezka_xml.read_text(encoding="utf-8")
    otw = "<content:encoded><![CDATA["
    zam = "]]></content:encoded>"
    i = paczka.index(otw) + len(otw)
    j = paczka.index(zam, i)
    if "]]>" in tresc:
        raise SystemExit("Tresc zawiera ]]> — rozbilaby sekcje CDATA.")
    nowy = paczka[:i] + tresc + paczka[j:]
    sciezka_xml.write_text(nowy, encoding="utf-8")
    # Import przerwie sie na niepoprawnym XML-u, wiec sprawdzamy od razu.
    xml.dom.minidom.parse(str(sciezka_xml))
    return nowy


def main():
    katalog_podgladow = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    for strona in STRONY:
        bloki = strona["blok"].read_text(encoding="utf-8")
        zapisz_xml(strona["xml"], bloki)
        print("XML   %s (%d znakow tresci)" % (strona["xml"].name, len(bloki)))

        if katalog_podgladow is None:
            continue
        katalog_podgladow.mkdir(parents=True, exist_ok=True)
        tresc, brakujace = wstaw_media(bloki)
        for nazwa in brakujace:
            print("  UWAGA: brak pliku media %s" % nazwa)

        podglad = katalog_podgladow / strona["podglad"]
        podglad.write_text(zbuduj_podglad(strona, tresc), encoding="utf-8")
        print("HTML  %s (%.1f MB)" % (podglad.name, podglad.stat().st_size / 1e6))

        artefakt = katalog_podgladow / strona["artefakt"]
        artefakt.write_text(
            zbuduj_podglad(strona, bez_mapy(tresc)), encoding="utf-8"
        )
        print("HTML  %s (%.1f MB)" % (artefakt.name, artefakt.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
