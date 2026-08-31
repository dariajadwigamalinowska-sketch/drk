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

## 2. Import stron

**Narzędzia → Importuj → WordPress** i wskaż plik z `wordpress/import/`.

### Sprawdź od razu, czy treść przetrwała

Otwórz zaimportowaną stronę. Jeśli **nie ma żadnych kolorów ani
układu** — sam tekst jeden pod drugim — to znaczy, że WordPress usunął
arkusz stylów. Przejdź do punktu 3.

**Dlaczego tak się dzieje.** WordPress przepuszcza treść wpisu przez
filtr `wp_kses_post()` dla każdego, kto nie ma uprawnienia
`unfiltered_html`. Na liście dozwolonych znaczników nie ma `<style>`
ani `<script>`. Uprawnienie to mają administratorzy i redaktorzy
zwykłej instalacji, ale **nie mają go**:

- administratorzy instalacji wielowitrynowej (tam ma je tylko super
  admin),
- konta na hostingach, które je wyłączają (m.in. WordPress.com
  w niższych planach),
- wszyscy tam, gdzie odbiera je wtyczka bezpieczeństwa.

Importer WXR zapisuje strony przez `wp_insert_post()`, więc filtr
działa także w czasie importu. Na pediatrii dotyczy to **75%** treści,
na medycynie estetycznej **46%** — stąd wrażenie, że „część rzeczy nie
działa".

**Najprościej jest tego uniknąć**: zaimportować jako administrator
zwykłej (nie wielowitrynowej) instalacji, z chwilowo wyłączoną wtyczką
bezpieczeństwa. Wtedy wszystko wchodzi w całości i punkt 3 jest
niepotrzebny.

---

## 3. Jeśli style i skrypty zostały usunięte

Wszystko, co filtr wycina, leży też w osobnych plikach — te same treści,
tylko poza wpisem, więc filtr ich nie dotyczy.

### Arkusz stylów

**Wygląd → Dostosuj → Dodatkowy CSS** i wklej całą zawartość:

- `wordpress/style-pediatria.css`
- `wordpress/style-medycyna-estetyczna.css`

Oba można wkleić jeden pod drugim — klasy się nie mieszają
(`kb-` kontra `estet`). To miejsce nie przechodzi przez `kses`, więc
arkusz przetrwa.

### Skrypty

Kalkulator dawek, karuzela z filmami i pętla ujęć w oknie powitalnym
potrzebują JavaScriptu. Wklej do dowolnej wtyczki od fragmentów kodu
(np. WPCode), jako **JavaScript w stopce**:

- `wordpress/skrypty-pediatria.js`
- `wordpress/skrypty-estetyczna.js`

Każdy fragment sam sprawdza, czy jego elementy są na stronie, więc na
podstronach bez nich nic nie robi i niczego nie psuje.

### Czego to nie naprawi

Filtr usuwa także `<button>`, `<svg>` i `<iframe>` z treści. Jeśli
strona przeszła przez filtr, znikną razem z nimi: przyciski kalkulatora,
ikony profili, strzałki karuzeli i mapa dojazdu — a tego wklejenie
arkusza i skryptu nie przywróci, bo brakuje samego kodu strony.
Dlatego jeśli tylko się da, lepiej zaimportować bez filtru (punkt 2).

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

Wszystko inne — paczki XML, arkusze CSS, pliki JS — jest z nich
generowane. Po każdej poprawce:

```
python3 wordpress/build.py                       # bez podmiany adresów
python3 wordpress/build.py --media <adres>       # z podmianą
```

Nie poprawiaj `style-*.css` ani `skrypty-*.js` ręcznie — przy
najbliższym przebudowaniu zmiany zostaną nadpisane.
