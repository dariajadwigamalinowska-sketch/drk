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
