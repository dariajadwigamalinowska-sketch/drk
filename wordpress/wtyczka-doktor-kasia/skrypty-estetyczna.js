/* Doktor Kasia Aesthetic
   Wygenerowane przez wordpress/build.py — nie poprawiaj tu recznie,
   tylko w pliku z blokami, i przebuduj.

   Wklej w dowolna wtyczke od fragmentow kodu (np. WPCode) jako
   JavaScript w stopce, albo dolacz plikiem w motywie potomnym.
   Kazdy fragment sam sprawdza, czy jego elementy sa na stronie,
   wiec nie przeszkadza na podstronach, gdzie ich nie ma. */

/* PETLA UJEC W RAMCE POWITALNEJ.

   Ujecia zmieniaja sie w takt tego, co naprawde gra, a nie w takt
   zegara animacji. Dzieki temu kazde ujecie widac raz, w calosci,
   od pierwszej klatki, i zaden nie wraca zaraz po sobie.

   Wczesniej robil to sam arkusz stylow, ale kazdy odtwarzacz mial
   wlasna petle, niezalezna od cyklu przenikania: material trwa
   2–4 s, cykl 8,5 s, wiec plik przewijal sie w tym czasie kilka razy
   i okno widocznosci lapalo go za kazdym razem w innym miejscu.

   Zeby dolozyc albo zdjac ujecie, wystarczy dodac lub usunac blok
   wideo z klasa "e-klatka" — skrypt sam je policzy. */
(function () {
  'use strict';
  try {
    var ramka = document.querySelector('.e-ramka-dwa');
    if (!ramka) { return; }

    var klatki = [].slice.call(ramka.querySelectorAll('.e-klatka'));
    if (klatki.length < 2) { return; }

    /* Kto wylaczyl animacje w systemie, zostaje przy jednym ujeciu
       w jego wlasnej petli — nie przelaczamy nic. */
    if (window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches) { return; }

    var PRZENIKANIE = 0.9;   /* sekundy — tyle samo, co transition w arkuszu */
    var biezaca = 0;
    var wTrakcie = false;

    function film(k) { return k.querySelector('video'); }

    function graj(v) {
      var obietnica = v.play();
      /* Przegladarka moze odmowic odtworzenia; nie ma sensu, zeby
         wywrocilo to cala petle. */
      if (obietnica && obietnica.catch) { obietnica.catch(function () {}); }
    }

    function nastepne() {
      if (wTrakcie) { return; }
      wTrakcie = true;

      var schodzi = klatki[biezaca];
      biezaca = (biezaca + 1) % klatki.length;
      var wchodzi = klatki[biezaca];

      var v = film(wchodzi);
      try { v.currentTime = 0; } catch (e) {}
      graj(v);
      wchodzi.classList.add('e-widoczna');
      schodzi.classList.remove('e-widoczna');

      /* Ujecie schodzace zatrzymujemy dopiero po przenikaniu — do tej
         chwili jeszcze je widac, wiec nie moze stanac w miejscu. */
      window.setTimeout(function () {
        var poprzedni = film(schodzi);
        poprzedni.pause();
        try { poprzedni.currentTime = 0; } catch (e) {}
        wTrakcie = false;
      }, PRZENIKANIE * 1000);
    }

    ramka.classList.add('e-petla-js');

    klatki.forEach(function (k, nr) {
      var v = film(k);
      /* Kolejnosc prowadzi skrypt, wiec odtwarzacz nie zapetla sie sam. */
      v.loop = false;
      v.muted = true;

      if (nr === 0) { k.classList.add('e-widoczna'); graj(v); }
      else { v.pause(); try { v.currentTime = 0; } catch (e) {} }

      /* Przelaczamy na tyle wczesniej, ile trwa rozplyniecie, zeby
         nastepne ujecie bylo juz w ruchu, zanim poprzednie zniknie. */
      v.addEventListener('timeupdate', function () {
        if (klatki[biezaca] !== k) { return; }
        if (!isFinite(v.duration) || v.duration <= 0) { return; }
        if (v.currentTime >= v.duration - PRZENIKANIE) { nastepne(); }
      });

      /* Zabezpieczenie: gdyby "timeupdate" nie zdazyl (bardzo krotkie
         ujecie, obciazone urzadzenie), koniec pliku i tak przesuwa
         petle dalej. */
      v.addEventListener('ended', function () {
        if (klatki[biezaca] === k) { nastepne(); }
      });
    });

    /* Po powrocie do karty przegladarka bywa, ze wstrzymala odtwarzanie.
       Wznawiamy to ujecie, ktore ma byc widoczne. */
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { return; }
      var v = film(klatki[biezaca]);
      if (v.paused) { graj(v); }
    });

    /* GDY ODTWARZANIE W OGOLE NIE RUSZY.
       Petla jest prowadzona zdarzeniem "timeupdate", czyli tym, co
       naprawde gra. Jesli przegladarka odmowi odtworzenia — tryb
       oszczedzania energii w telefonie, ustawienie "blokuj
       autoodtwarzanie", brak kodeka — zadne "timeupdate" nie przyjdzie
       i kadr zamarlby na pierwszym plakacie na zawsze. Sprawdzamy wiec
       po sekundzie, czy material ruszyl z miejsca; jesli nie, ujecia
       zmieniaja sie z zegara i widac przynajmniej kolejne plakaty. */
    window.setTimeout(function () {
      var v = film(klatki[biezaca]);
      if (v.currentTime > 0.05) { return; }   /* gra normalnie */
      var CZAS_PLAKATU = 4000;
      window.setInterval(function () {
        if (document.hidden) { return; }
        var biezacy = film(klatki[biezaca]);
        if (biezacy.currentTime > 0.05) { return; }  /* odtwarzanie wrocilo */
        wTrakcie = false;
        nastepne();
      }, CZAS_PLAKATU);
    }, 1000);
  } catch (err) {
    if (window.console && window.console.error) { window.console.error('e-petla:', err); }
  }
})();

/* ATRYBUTY WIDEO USTAWIANE Z KODU.
   Filtr kses przepuszcza <video>, ale tylko z lista atrybutow, na
   ktorej nie ma "playsinline". Bez niego iOS otwiera film na pelnym
   ekranie zamiast odtwarzac go w kadrze i nie startuje sam. Ustawiamy
   go wiec z JavaScriptu — tam zaden filtr nie siega. Przy okazji
   pilnujemy wyciszenia, bo bez niego przegladarki blokuja
   autoodtwarzanie. */
(function () {
  'use strict';
  function ustaw() {
    try {
      var filmy = document.querySelectorAll('.estet video');
      for (var i = 0; i < filmy.length; i++) {
        filmy[i].playsInline = true;
        filmy[i].setAttribute('playsinline', '');
        filmy[i].muted = true;
      }
    } catch (err) { /* film po prostu zostaje jak byl */ }
  }
  /* Czekamy na koniec wczytywania dokumentu. Skrypt stoi w tresci
     strony, wiec w chwili uruchomienia czesc filmow moze byc jeszcze
     nizej i querySelectorAll by ich nie zobaczylo. Wczytany z wtyczki
     w stopce dziala tak samo — warunek jest wtedy od razu spelniony. */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ustaw);
  } else {
    ustaw();
  }
})();
