# Wdrożenie obu stron w WordPressie

Po zaimportowaniu paczki część rzeczy potrafi nie zadziałać — i to nie
na każdej instalacji tak samo. Przyczyny są trzy, wszystkie znane
i wszystkie do obejścia. Poniżej kolejność, która działa niezależnie od
tego, gdzie strona stoi.

Sprawdzian, co dokładnie jest zagrożone w bieżącej wersji plików:

```
python3 wordpress/przenosnosc.py
```

---

## 1. Najpierw media

Wgraj do **Media → Dodaj nowy** wszystkie pliki z `assets/wideo/`
i `assets/grafika/`. Potem kliknij dowolny z nich i skopiuj początek
adresu — będzie wyglądał tak:

```
https://twojadomena.pl/wp-content/uploads/2026/08/logo-pediatria.png
```

Interesuje Cię część **bez nazwy pliku**:

```
https://twojadomena.pl/wp-content/uploads/2026/08
```

Zbuduj paczki z tym adresem wstemplowanym:

```
python3 wordpress/build.py --media https://twojadomena.pl/wp-content/uploads/2026/08
```

**Dlaczego to trzeba zrobić.** W treści stron adresy stoją jako
`/wp-content/uploads/nazwa.jpg`, a WordPress domyślnie układa wgrane
pliki w podkatalogach rocznik/miesiąc. Bez podmiany zdjęcia i filmy
trafiają w pustkę — strona wygląda, jakby połowa jej zawartości
zniknęła.

Można też zamiast tego wyłączyć podkatalogi: **Ustawienia → Media →
odznacz „Porządkuj przesłane pliki…"** i wgrać media dopiero potem.
Wtedy domyślne adresy pasują bez żadnej podmiany.

---

## 2. Import stron — dwie drogi

Są dwie paczki na stronę. Wybierz jedną.

### A. Z wtyczką — działa wszędzie (zalecane)

1. **Wtyczki → Dodaj nową → Wyślij wtyczkę** i wskaż
   `wordpress/wtyczka-doktor-kasia.zip`. Włącz ją.
2. **Narzędzia → Importuj → WordPress** i wskaż paczkę **`-wtyczka`**:
   - `import/pediatria-wtyczka.wordpress.xml`
   - `import/medycyna-estetyczna-wtyczka.wordpress.xml`

W tym wariancie treść strony nie zawiera **nic**, co WordPress mógłby
wyciąć — sprawdzone maszynowo, zero znaczników z listy do usunięcia.
Arkusz, skrypty, kalkulator, karuzela, ikony profili i mapa siedzą we
wtyczce i wstawiają się przez krótkie znaczniki (`[dk_pedi_kalkulator]`
i podobne), które są zwykłym tekstem.

Treść wpisu jest przy tym pięć razy krótsza (17 kB zamiast 94 kB na
pediatrii), więc edytor działa płynnie, a strony łatwiej się redaguje.

### B. Bez wtyczki — wszystko w treści strony

**Narzędzia → Importuj → WordPress** i wskaż paczkę bez `-wtyczka`.
Zadziała **tylko wtedy**, gdy importujesz jako administrator zwykłej
(nie wielowitrynowej) instalacji, bez wtyczki bezpieczeństwa odbierającej
uprawnienie `unfiltered_html`.

Jak sprawdzić, czy się udało: otwórz zaimportowaną stronę. Jeśli **nie
ma kolorów ani układu** — sam tekst jeden pod drugim — to znaczy, że
WordPress usunął arkusz. Wróć do wariantu A.

### Dlaczego tak się dzieje

WordPress przepuszcza treść wpisu przez filtr `wp_kses_post()` dla
każdego, kto nie ma uprawnienia `unfiltered_html`. Na liście dozwolonych
znaczników nie ma `<style>`, `<script>`, `<iframe>`, `<button>`,
`<input>` ani `<svg>`. Uprawnienie to mają administratorzy i redaktorzy
zwykłej instalacji, ale **nie mają go**:

- administratorzy instalacji wielowitrynowej (tam ma je tylko super
  admin),
- konta na hostingach, które je wyłączają (m.in. WordPress.com
  w niższych planach),
- wszyscy tam, gdzie odbiera je wtyczka bezpieczeństwa.

Importer WXR zapisuje strony przez `wp_insert_post()`, więc filtr działa
także w czasie importu. W paczce bez wtyczki dotyczy to **75%** treści
pediatrii i **47%** medycyny estetycznej.

---

## 3. Jeśli mimo wszystko wolisz wariant B, a filtr zadziałał

Wszystko, co filtr wycina, leży też w osobnych plikach.

### Arkusz stylów

**Wygląd → Dostosuj → Dodatkowy CSS** i wklej całą zawartość:

- `wordpress/style-pediatria.css`
- `wordpress/style-medycyna-estetyczna.css`

Oba można wkleić jeden pod drugim — klasy się nie mieszają
(`kb-` kontra `estet`). To miejsce nie przechodzi przez `kses`.

### Skrypty

Do wtyczki od fragmentów kodu (np. WPCode), jako **JavaScript
w stopce**:

- `wordpress/skrypty-pediatria.js`
- `wordpress/skrypty-estetyczna.js`

### Czego to nie przywróci

Przycisków kalkulatora, pola na masę ciała, ikon profili, strzałek
karuzeli i mapy — bo filtr usunął sam kod strony, a nie tylko arkusz.
Dlatego istnieje wariant A.

---

## 4. Motyw

Sekcje idą na całą szerokość okna (`alignfull`). Działa to tylko
w motywie, który zgłasza obsługę szerokich wyrównań
(`add_theme_support('align-wide')`) — ma ją każdy motyw blokowy
i większość nowszych klasycznych. W motywie bez niej pasy skończą się
na szerokości treści; strona pozostanie czytelna, tylko węższa.

---

## 5. Kroje pisma

Fraunces, Cormorant Garamond i Inter wczytują się z Google Fonts
przez `@import` na początku arkusza. Jeśli u odwiedzającego są
zablokowane (wtyczka prywatności, firewall firmowy, sieć bez dostępu),
przeglądarka użyje zapasowych: Georgia i Times dla nagłówków, systemowej
bezszeryfowej dla tekstu. Strona nadal wygląda spójnie, tylko inaczej —
to zaplanowane zejście, nie awaria.

Kto woli nie zależeć od Google: pobrać pliki krojów, wgrać do Mediów
i zamienić `@import` na własne reguły `@font-face`.

---

## 6. Po każdej zmianie w plikach z blokami

Źródłem prawdy są dwa pliki:

```
wordpress/pediatria-gutenberg.html
wordpress/medycyna-estetyczna-gutenberg.html
```

Wszystko inne — paczki XML (obie wersje), arkusze CSS, pliki JS,
wtyczka i jej `.zip` — jest z nich generowane. Po każdej poprawce:

```
python3 wordpress/build.py                       # bez podmiany adresów
python3 wordpress/build.py --media <adres>       # z podmianą
```

Nie poprawiaj ręcznie `style-*.css`, `skrypty-*.js` ani niczego
w `wtyczka-doktor-kasia/` — przy najbliższym przebudowaniu zmiany
zostaną nadpisane.

Jeśli poprawka dotyczyła fragmentu obsługiwanego przez wtyczkę
(kalkulator, karuzela, ikony, mapa), po przebudowaniu wgraj wtyczkę
jeszcze raz — sama treść strony w WordPressie się nie zmienia, bo
zawiera tylko krótki znacznik.
