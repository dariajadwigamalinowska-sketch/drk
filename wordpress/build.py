#!/usr/bin/env python3
"""Buduje pliki pochodne z dwoch zrodel blokow Gutenberga.

Zrodlem prawdy sa:
    wordpress/pediatria-gutenberg.html
    wordpress/medycyna-estetyczna-gutenberg.html

Skrypt wytwarza z nich:
  * wordpress/import/*.wordpress.xml  — paczki importu WXR dla WordPressa
  * wordpress/style-*.css             — arkusze do "Dodatkowy CSS"
  * wordpress/skrypty-*.js            — skrypty do wtyczki z fragmentami
  * podglady HTML (poza repozytorium) — samodzielne pliki z mediami
    wklejonymi jako data URI, do obejrzenia w przegladarce bez WordPressa

Arkusze i skrypty sa wydzielane, bo WordPress usuwa <style> i <script>
z tresci wpisu wszedzie tam, gdzie uzytkownik nie ma uprawnienia
"unfiltered_html" — a nie maja go m.in. administratorzy instalacji
wielowitrynowych i czesc hostingow. Wtedy strona wchodzi bez wygladu
i bez kalkulatora. Wklejone osobno, arkusz i skrypt sa od tego filtru
niezalezne. Szczegoly: wordpress/przenosnosc.py i INSTRUKCJA.md.

Uruchomienie:
    python3 wordpress/build.py [katalog_na_podglady]
    python3 wordpress/build.py --media https://adres/wp-content/uploads/2026/08
"""

import base64
import mimetypes
import shutil
import re
import sys
import xml.dom.minidom
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
ZRODLA = KORZEN / "wordpress"
MEDIA = [KORZEN / "assets" / "wideo", KORZEN / "assets" / "grafika"]
WERSJA_WTYCZKI = "1.0.0"

STRONY = [
    {
        "blok": ZRODLA / "pediatria-gutenberg.html",
        "xml": ZRODLA / "import" / "pediatria.wordpress.xml",
        "css": ZRODLA / "style-pediatria.css",
        "prefiks": "pedi",
        "js": ZRODLA / "skrypty-pediatria.js",
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
        "css": ZRODLA / "style-medycyna-estetyczna.css",
        "prefiks": "estet",
        "js": ZRODLA / "skrypty-estetyczna.js",
        "podglad": "medycyna-estetyczna-podglad.html",
        "artefakt": "artefakt-estetyczna.html",
        "tytul": "Doktor Kasia Aesthetic",
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


def wytnij(html, znacznik):
    """Zwraca zawartosc wszystkich <znacznik>...</znacznik>, po kolei."""
    return [m.group(1) for m in re.finditer(
        r"<%s\b[^>]*>(.*?)</%s>" % (znacznik, znacznik), html, re.S | re.I)]


def zapisz_arkusz(sciezka, kawalki, tytul):
    naglowek = (
        "/* %s\n"
        "   Wygenerowane przez wordpress/build.py — nie poprawiaj tu recznie,\n"
        "   tylko w pliku z blokami, i przebuduj.\n\n"
        "   Wklej calosc w Wyglad -> Dostosuj -> Dodatkowy CSS. To miejsce\n"
        "   nie przechodzi przez filtr kses, wiec arkusz przetrwa takze tam,\n"
        "   gdzie <style> w tresci wpisu jest usuwany. */\n\n" % tytul
    )
    sciezka.write_text(naglowek + "\n\n".join(k.strip() for k in kawalki) + "\n",
                       encoding="utf-8")


def zapisz_skrypty(sciezka, kawalki, tytul):
    naglowek = (
        "/* %s\n"
        "   Wygenerowane przez wordpress/build.py — nie poprawiaj tu recznie,\n"
        "   tylko w pliku z blokami, i przebuduj.\n\n"
        "   Wklej w dowolna wtyczke od fragmentow kodu (np. WPCode) jako\n"
        "   JavaScript w stopce, albo dolacz plikiem w motywie potomnym.\n"
        "   Kazdy fragment sam sprawdza, czy jego elementy sa na stronie,\n"
        "   wiec nie przeszkadza na podstronach, gdzie ich nie ma. */\n\n" % tytul
    )
    sciezka.write_text(naglowek + "\n\n".join(k.strip() for k in kawalki) + "\n",
                       encoding="utf-8")



# =========================================================================
#  WARIANT ODPORNY NA FILTR KSES
#
#  WordPress usuwa z tresci wpisu wszystko, czego nie ma na liscie
#  $allowedposttags: <style>, <script>, <iframe>, <button>, <input>
#  i <svg>. Na obu stronach cale to "wrazliwe" wnetrze siedzi wylacznie
#  w blokach wp:html — sprawdzone skryptem przenosnosc.py. Da sie wiec
#  zrobic rzecz czysta: przeniesc te fragmenty do wtyczki i zostawic
#  w tresci sam krotki shortcode, ktory jest zwyklym tekstem i filtr go
#  nie rusza. Wtyczka wypisuje fragment po stronie serwera, wiec
#  odtwarza sie w calosci niezaleznie od uprawnien uzytkownika.
# =========================================================================

BLOK_HTML = re.compile(r"<!-- wp:html -->(.*?)<!-- /wp:html -->", re.S)


def slug_fragmentu(html):
    """Nazwa shortcode wyprowadzona z pierwszej klasy we fragmencie,
    zeby byla czytelna i za kazdym razem taka sama."""
    m = re.search(r'class="([\w-]+)', html)
    podstawa = m.group(1) if m else "fragment"
    podstawa = re.sub(r"^(kb|e)-", "", podstawa)
    return podstawa.replace("-", "_")


def sam_markup(srodek):
    """Zdejmuje z bloku arkusz i skrypt — te ida osobnymi plikami —
    i zwraca to, co zostaje. Blok kalkulatora ma i jedno, i drugie
    obok wlasciwej tresci, wiec nie wolno pomijac calego bloku tylko
    dlatego, ze cos w nim jest.

    Zwraca pusty napis takze wtedy, gdy zostaly same komentarze:
    blok z arkuszem zaczyna sie dluga instrukcja dla edytora i bez
    tego sprawdzenia robil sie z niej osobny, pusty shortcode."""
    bez = re.sub(r"<style\b[^>]*>.*?</style>", "", srodek, flags=re.S | re.I)
    bez = re.sub(r"<script\b[^>]*>.*?</script>", "", bez, flags=re.S | re.I)
    bez = bez.strip()
    if not re.sub(r"<!--.*?-->", "", bez, flags=re.S).strip():
        return ""
    return bez


def fragmenty(html):
    """Zwraca [(slug, tresc, caly_blok)] dla blokow wp:html, w ktorych
    po zdjeciu arkusza i skryptu zostaje jeszcze jakas tresc."""
    wynik = []
    for m in BLOK_HTML.finditer(html):
        markup = sam_markup(m.group(1).strip())
        if not markup:
            continue
        wynik.append((slug_fragmentu(markup), markup, m.group(0)))
    return wynik


def tresc_na_shortcode(html, prefiks):
    """Zamienia bloki wp:html na bloki shortcode. Arkusze i skrypty
    znikaja z tresci zupelnie — dostarcza je wtyczka."""
    def zamien(m):
        markup = sam_markup(m.group(1).strip())
        if not markup:
            return ""
        nazwa = "dk_%s_%s" % (prefiks, slug_fragmentu(markup))
        return ("<!-- wp:shortcode -->\n[%s]\n<!-- /wp:shortcode -->" % nazwa)
    return BLOK_HTML.sub(zamien, html)


NAGLOWEK_WTYCZKI = """<?php
/**
 * Plugin Name: Doktor Kasia — bloki stron
 * Description: Arkusze, skrypty i te fragmenty stron, ktore WordPress
 *              usuwa z tresci wpisu (style, skrypty, przyciski, pola
 *              formularza, ikony SVG i ramki iframe). Wtyczka wypisuje
 *              je po stronie serwera, wiec dzialaja niezaleznie od
 *              uprawnien uzytkownika, ktory importowal strony.
 * Version:     %(wersja)s
 * Author:      Opieka Pediatryczna Doktor Kasi
 * License:     GPL-2.0-or-later
 *
 * PLIK JEST GENEROWANY przez wordpress/build.py — nie poprawiaj go
 * recznie, tylko zrodla w wordpress/*-gutenberg.html i przebuduj.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'DK_WERSJA', '%(wersja)s' );

/**
 * Arkusze i skrypty. Klasy sa nazwane z przedrostkami (kb- oraz estet),
 * wiec nie mieszaja sie z motywem ani ze soba; kazdy skrypt sam
 * sprawdza, czy jego elementy sa na stronie. Zeby wczytywac je tylko
 * na wybranych stronach, opakuj tresc ponizej warunkiem is_page().
 */
function dk_zasoby() {
	$baza = plugin_dir_url( __FILE__ );
%(zasoby)s}
add_action( 'wp_enqueue_scripts', 'dk_zasoby' );

/**
 * Wypisuje fragment strony trzymany w pliku obok wtyczki.
 * Nazwa pliku pochodzi wylacznie z kodu ponizej, ale basename()
 * zostaje jako zabezpieczenie na wypadek pozniejszych zmian.
 * Zwracana tresc jest naszym wlasnym kodem strony, wiec nie
 * przepuszczamy jej przez zadne czyszczenie — o to wlasnie chodzi.
 */
function dk_fragment( $plik ) {
	$sciezka = plugin_dir_path( __FILE__ ) . 'fragmenty/' . basename( $plik );
	if ( ! is_readable( $sciezka ) ) {
		return '';
	}
	return file_get_contents( $sciezka );
}

%(shortcode)s"""


def zbuduj_wtyczke(katalog, strony, wersja):
    """Sklada wtyczke: arkusze, skrypty i fragmenty jako shortcode."""
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "fragmenty").mkdir(exist_ok=True)

    zasoby, shortcode, ile = [], [], 0
    for strona in strony:
        html = strona["blok"].read_text(encoding="utf-8")

        for zrodlo, rodzaj in ((strona["css"], "style"), (strona["js"], "script")):
            if not zrodlo.is_file():
                continue
            cel = katalog / zrodlo.name
            cel.write_text(zrodlo.read_text(encoding="utf-8"), encoding="utf-8")
            uchwyt = "dk-" + zrodlo.stem
            if rodzaj == "style":
                zasoby.append(
                    "\twp_enqueue_style( '%s', $baza . '%s', array(), DK_WERSJA );"
                    % (uchwyt, zrodlo.name))
            else:
                zasoby.append(
                    "\twp_enqueue_script( '%s', $baza . '%s', array(), DK_WERSJA, true );"
                    % (uchwyt, zrodlo.name))

        for slug, tresc, _ in fragmenty(html):
            nazwa = "dk_%s_%s" % (strona["prefiks"], slug)
            plik = nazwa + ".html"
            (katalog / "fragmenty" / plik).write_text(tresc + "\n", encoding="utf-8")
            shortcode.append(
                "add_shortcode( '%s', function () {\n"
                "\treturn dk_fragment( '%s' );\n"
                "} );" % (nazwa, plik))
            ile += 1

    (katalog / "doktor-kasia.php").write_text(
        NAGLOWEK_WTYCZKI % {
            "wersja": wersja,
            "zasoby": "\n".join(zasoby) + "\n",
            "shortcode": "\n\n".join(shortcode) + "\n",
        }, encoding="utf-8")
    return ile



CZYTAJ_NAJPIERW = """# Doktor Kasia — komplet do wdrozenia

Wszystko, czego potrzeba, w jednym miejscu. Struktura:

    podglad/     dwie strony jako samodzielne pliki HTML — otwierasz
                 dwuklikiem w przegladarce, media sa w srodku, nie
                 trzeba niczego instalowac ani miec internetu
                 (poza krojami pisma z Google)

    import/      paczki do WordPressa, po dwie na strone:
                   *-wtyczka.wordpress.xml  — z wtyczka, dziala wszedzie
                   *.wordpress.xml          — wszystko w tresci strony

    wtyczka/     wtyczka-doktor-kasia.zip — wgrywasz przez
                 Wtyczki -> Dodaj nowa -> Wyslij wtyczke

    media/       zdjecia i filmy do wgrania w Media -> Dodaj nowy

    osobno/      arkusz CSS i skrypty JS na wypadek, gdyby trzeba
                 bylo wkleic je recznie

    zrodla/      pliki, z ktorych wszystko powyzsze jest generowane,
                 razem ze skryptem budujacym

## Najkrotsza droga

1. Wgraj do Mediow wszystko z `media/`.
2. Wtyczki -> Dodaj nowa -> Wyslij wtyczke -> `wtyczka/wtyczka-doktor-kasia.zip`,
   wlacz.
3. Narzedzia -> Importuj -> WordPress -> pliki `import/*-wtyczka.wordpress.xml`.
4. Jesli zdjecia sie nie pokazuja, przeczytaj punkt 1 instrukcji —
   chodzi o podkatalogi rocznik/miesiac w adresach mediow.

Pelna instrukcja: `INSTRUKCJA.md`.
"""


def zbuduj_pakiet(katalog_roboczy, katalog_podgladow):
    """Sklada jedno archiwum ze wszystkim: podglady, paczki importu,
    wtyczka, media, arkusze i skrypty osobno oraz zrodla."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        korzen = Path(tmp) / "doktor-kasia-pakiet"
        for nazwa in ("podglad", "import", "wtyczka", "media", "osobno", "zrodla"):
            (korzen / nazwa).mkdir(parents=True)

        (korzen / "CZYTAJ-TO-NAJPIERW.md").write_text(
            CZYTAJ_NAJPIERW, encoding="utf-8")
        instrukcja = ZRODLA / "INSTRUKCJA.md"
        if instrukcja.is_file():
            shutil.copy2(instrukcja, korzen / "INSTRUKCJA.md")

        for strona in STRONY:
            zrodlo = katalog_podgladow / strona["podglad"] if katalog_podgladow else None
            if zrodlo and zrodlo.is_file():
                shutil.copy2(zrodlo, korzen / "podglad" / strona["podglad"])
            shutil.copy2(strona["blok"], korzen / "zrodla" / strona["blok"].name)
            for klucz in ("css", "js"):
                if strona[klucz].is_file():
                    shutil.copy2(strona[klucz], korzen / "osobno" / strona[klucz].name)

        for x in sorted((ZRODLA / "import").glob("*.xml")):
            shutil.copy2(x, korzen / "import" / x.name)

        zip_wtyczki = ZRODLA / "wtyczka-doktor-kasia.zip"
        if zip_wtyczki.is_file():
            shutil.copy2(zip_wtyczki, korzen / "wtyczka" / zip_wtyczki.name)

        # Do pakietu ida tylko te pliki, do ktorych strony naprawde
        # sie odwoluja. Wczesniejsze wersje mialy w assets takze
        # material odlozony (ujecie z poczekalni, kadr z misiem,
        # zrodlowy gradient) — wrzucenie go do "media do wgrania"
        # kazaloby wgrywac pliki, ktorych nic nie uzywa.
        uzywane = set()
        for strona in STRONY:
            html = strona["blok"].read_text(encoding="utf-8")
            uzywane.update(re.findall(
                r"/wp-content/uploads/([\w-]+\.\w+)", html))
        pominiete = []
        for katalog in MEDIA:
            cel = korzen / "media" / katalog.name
            cel.mkdir(parents=True, exist_ok=True)
            for plik in sorted(katalog.iterdir()):
                if not plik.is_file():
                    continue
                if plik.name in uzywane:
                    shutil.copy2(plik, cel / plik.name)
                else:
                    pominiete.append(plik.name)
        if pominiete:
            print("      media pominiete (nieuzywane): %s"
                  % ", ".join(sorted(pominiete)))

        for narzedzie in ("build.py", "przenosnosc.py"):
            sciezka = ZRODLA / narzedzie
            if sciezka.is_file():
                shutil.copy2(sciezka, korzen / "zrodla" / narzedzie)

        cel_zip = katalog_roboczy / "doktor-kasia-pakiet"
        archiwum = shutil.make_archive(
            str(cel_zip), "zip", root_dir=str(korzen.parent),
            base_dir="doktor-kasia-pakiet")
        return Path(archiwum)


def main():
    baza_mediow = None
    argumenty = sys.argv[1:]
    if "--media" in argumenty:
        i = argumenty.index("--media")
        baza_mediow = argumenty[i + 1].rstrip("/")
        del argumenty[i:i + 2]
    katalog_podgladow = Path(argumenty[0]) if argumenty else None

    for strona in STRONY:
        bloki = strona["blok"].read_text(encoding="utf-8")

        arkusze = wytnij(bloki, "style")
        if arkusze:
            zapisz_arkusz(strona["css"], arkusze, strona["tytul"])
            print("CSS   %s (%d znakow)" % (
                strona["css"].name, strona["css"].stat().st_size))
        skrypty = wytnij(bloki, "script")
        if skrypty:
            zapisz_skrypty(strona["js"], skrypty, strona["tytul"])
            print("JS    %s (%d znakow)" % (
                strona["js"].name, strona["js"].stat().st_size))

        tresc_xml = bloki
        if baza_mediow:
            tresc_xml = tresc_xml.replace("/wp-content/uploads", baza_mediow)
            print("      media -> %s" % baza_mediow)
        zapisz_xml(strona["xml"], tresc_xml)
        print("XML   %s (%d znakow tresci)" % (strona["xml"].name, len(tresc_xml)))

        # Wariant na shortcode — tresc bez niczego, co wycina filtr kses.
        krotka = tresc_na_shortcode(tresc_xml, strona["prefiks"])
        sciezka_krotka = strona["xml"].with_name(
            strona["xml"].name.replace(".wordpress.xml", "-wtyczka.wordpress.xml"))
        if not sciezka_krotka.is_file():
            sciezka_krotka.write_text(
                strona["xml"].read_text(encoding="utf-8"), encoding="utf-8")
        zapisz_xml(sciezka_krotka, krotka)
        print("XML   %s (%d znakow — wariant dla wtyczki)"
              % (sciezka_krotka.name, len(krotka)))

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

    katalog_wtyczki = ZRODLA / "wtyczka-doktor-kasia"
    ile = zbuduj_wtyczke(katalog_wtyczki, STRONY, WERSJA_WTYCZKI)
    print("WTYCZKA %s (%d fragmentow)" % (katalog_wtyczki.name, ile))
    archiwum = shutil.make_archive(
        str(ZRODLA / "wtyczka-doktor-kasia"), "zip",
        root_dir=str(ZRODLA), base_dir="wtyczka-doktor-kasia")
    print("ZIP   %s (%.0f kB)"
          % (Path(archiwum).name, Path(archiwum).stat().st_size / 1024))

    if katalog_podgladow is not None:
        pakiet = zbuduj_pakiet(katalog_podgladow, katalog_podgladow)
        print("PAKIET %s (%.1f MB)" % (pakiet.name, pakiet.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
