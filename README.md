# DoktorKasia.pl — strona pediatry dla WordPressa

Gotowy kod strony gabinetu pediatrycznego (wzorowany na typie strony doktorkasia.pl):
hero, o mnie, oferta, **interaktywny kalkulator dawek syropu przeciwgorączkowego**,
porady, opinie, FAQ, kontakt z mapą i stopka.

## Co jest w repozytorium

| Plik | Do czego służy |
|---|---|
| `gutenberg/doktorkasia-gutenberg.html` | **Wersja główna** — natywne bloki Gutenberga. Wszystko edytowalne klikiem w edytorze. |
| `embed/doktorkasia-embed.html` | Wersja alternatywna — jeden blok „HTML własny”. Przydatna, gdy nie chcesz ruszać bloków. |

---

## Instalacja wersji Gutenberg (zalecana)

1. **Strony → Dodaj nową**
2. Menu **⋮** w prawym górnym rogu → **Edytor kodu** (skrót `Ctrl + Shift + Alt + M`)
3. Wklej całą zawartość `gutenberg/doktorkasia-gutenberg.html`
4. Wróć do **Edytora wizualnego** tym samym skrótem
5. Ustaw szablon strony na pełną szerokość (bez paska bocznego) i opublikuj
6. **Ustawienia → Czytanie** → ustaw tę stronę jako stronę główną

Po wklejeniu edytujesz teksty normalnie — klikając w nagłówki, akapity i przyciski.
W blokach „HTML własny” są tylko trzy rzeczy, które wymagają kodu: arkusz stylów,
kalkulator dawek i mapa Google.

### Wymagania
- WordPress **6.4+** (blok „Szczegóły” użyty w sekcji FAQ)
- Motyw blokowy lub dowolny motyw z obsługą szerokości `alignfull`
- Konto z uprawnieniami administratora (blok „HTML własny” wymaga `unfiltered_html`)

---

## Co trzeba uzupełnić

W obu plikach miejsca do zmiany są oznaczone komentarzem `UZUPEŁNIJ`:

- **numer telefonu** — `+48 000 000 000` (występuje w hero, kontakcie, CTA i stopce)
- **adres e-mail** — `kontakt@doktorkasia.pl`
- **zdjęcia** — dwa zastępcze bloki `dk-photo`; zamień je na blok **Obraz** (hero: format pionowy 4:5, min. 900×1125 px)
- **godziny przyjęć** i **liczby w pasku zaufania** (15+ lat, 30 min itd.)
- **opinie** — obecne są przykładowe, wstaw prawdziwe (za zgodą pacjentów)
- **formularz kontaktowy** — wstaw blok **Shortcode** z Contact Form 7 / WPForms; sam HTML nie wyśle maila
- **wpisy w sekcji „Porady”** — podlinkuj własne artykuły lub filmy
- **mapa** — podmień adres w parametrze `q=` (działa bez klucza API)

## Zmiana kolorów

Wszystkie kolory siedzą w zmiennych CSS na początku bloku ze stylami:

```css
--dk-teal:#0f6f66;   /* kolor główny  */
--dk-sun:#f2a53c;    /* akcent        */
--dk-mint:#f4faf8;   /* tło sekcji    */
```

---

## Kalkulator dawek — założenia

- **Paracetamol**: 15 mg/kg na dawkę, co 4–6 h, maks. 4 dawki/dobę, maks. 60 mg/kg/dobę (do 4000 mg)
- **Ibuprofen**: 10 mg/kg na dawkę, co 6–8 h, maks. 3 dawki/dobę, maks. 30 mg/kg/dobę (do 1200 mg)
- Dawka jednorazowa ograniczona do 1000 mg (paracetamol) i 400 mg (ibuprofen)
- Ostrzeżenia: wiek < 3 mies., masa < 5 kg (ibuprofen), przekroczenie dawki maksymalnej

Kalkulator wyświetla widoczne zastrzeżenie, że ma charakter informacyjny i nie zastępuje
porady lekarskiej. **Przed publikacją warto, aby dawkowanie i treść zastrzeżenia
zaakceptował lekarz prowadzący stronę.**

## Uwaga o treści

Teksty opisowe (biogram, oferta, FAQ) zostały napisane na podstawie ogólnodostępnych
informacji o praktyce i wymagają weryfikacji przed publikacją. Opinie pacjentów są
oznaczone jako przykładowe — nie publikuj ich w obecnej formie.

---

# #nauka4future — III edycja (FutureLab PK)

Plik: `wordpress/nauka4future-edycja3-gutenberg.html` — jedna strona do wklejenia
w **Edytorze kodu** Gutenberga (blok „HTML własny”), w kolorystyce Politechniki
Krakowskiej (kolor podstawowy znaku PK: PANTONE 288 / RGB 0-53-113 / `#003571`).

## Co jest na stronie

| Sekcja | Co robi |
|---|---|
| **Interaktywna góra** | Warstwowa scena SVG (niebo, trzy pasma, szlak, mgła) reagująca na scroll i ruch kursora. Pięć świecących znaczników = pięć ścieżek tematycznych; kliknięcie filtruje program. Wyłącza się przy `prefers-reduced-motion`. |
| **Ścieżki tematyczne** | Architektura i budownictwo, Chemia, Design, Nowoczesne technologie, Smart city — te same obszary co w poprzednich edycjach. |
| **Kalendarz** | Miesięczna siatka od poniedziałku, kropki oznaczają typ zajęć, klik w dzień filtruje harmonogram. W trybie edycji `+` na kaflu dnia dodaje wydarzenie z tą datą. |
| **Harmonogram** | Ten sam program w układzie listy, pogrupowany po dniach. |
| **Rozwijane wydarzenia** | Każdy wykład/warsztat/pokaz rozwija się i przyjmuje **opis**, **dokumentację wideo** (YouTube, Vimeo, `.mp4`) i **dokumentację zdjęciową** (adres URL albo plik z dysku, z lightboxem). |

## Tryb edycji i zapisywanie programu

Przełącznik **„Tryb edycji programu”** odsłania formularze: dodawanie, edycję
i usuwanie wydarzeń oraz pola na opisy i media.

**Ważne:** program zapisuje się w `localStorage` przeglądarki, a nie na serwerze.
Oznacza to, że:

- zmiany widzi tylko ta przeglądarka, w której je wprowadzono — odwiedzający
  zobaczą program domyślny wpisany w kodzie strony,
- wyczyszczenie danych witryny kasuje zmiany.

Dlatego po ułożeniu programu zrób **Eksport JSON**. Plik można potem wczytać
przyciskiem **Import JSON** na innym komputerze, a docelowo — przenieść treść do
tablicy `DEFAULT_EVENTS` w kodzie strony, żeby program był widoczny publicznie.
Zdjęcia wgrane z dysku zapisują się jako `data:URI` (limit 1,2 MB na plik);
do publikacji lepiej wgrać je do biblioteki mediów WordPressa i wkleić adresy.

## Co trzeba uzupełnić przed publikacją

W pliku oznaczone jako `[DO UZUPEŁNIENIA]` i `[DO POTWIERDZENIA]`:

- **daty III edycji** — w kodzie są robocze terminy (29.09, 6.10, 13.10, 20.10.2026),
  wzorowane na rytmie II edycji (wrzesień–październik),
- **nazwiska prowadzących** przy wykładach i warsztatach,
- **sale i budynki**,
- **link do formularza zgłoszeniowego** (przycisk w sekcji „Zapisy”),
- **zdjęcia i filmy** z poprzednich edycji.

Treści opisowe (opisy wykładów i warsztatów) są propozycją napisaną na podstawie
publicznie dostępnych informacji o projekcie — przed publikacją wymagają
weryfikacji przez FutureLab PK.
