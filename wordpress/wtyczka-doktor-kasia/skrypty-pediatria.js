/* Opieka Pediatryczna Doktor Kasi
   Wygenerowane przez wordpress/build.py — nie poprawiaj tu recznie,
   tylko w pliku z blokami, i przebuduj.

   Wklej w dowolna wtyczke od fragmentow kodu (np. WPCode) jako
   JavaScript w stopce, albo dolacz plikiem w motywie potomnym.
   Kazdy fragment sam sprawdza, czy jego elementy sa na stronie,
   wiec nie przeszkadza na podstronach, gdzie ich nie ma. */

(function () {
  'use strict';

  /* =====================================================================
     DANE DAWKOWANIA — jedyne miejsce, w którym zmienia się liczby
     ---------------------------------------------------------------------
     mgKg               – dawka jednorazowa w mg na kg masy ciała
     maxDobowaMg        – górna granica sumy z całej doby
     dawekNaDobe        – maksymalna liczba dawek w ciągu doby
     odstep             – minimalny odstęp między dawkami (tekst)
     preparaty          – lista konkretnych syropów; "mg" i "ml" opisują
                          stężenie z opakowania (np. 100 mg / 5 ml).
                          Stężenie liczymy jako mg na 1 ml, więc krople
                          100 mg / 1 ml liczą się tak samo poprawnie jak
                          syropy 100 mg / 5 ml.

     Granicy pojedynczej dawki nie zapisujemy osobno — wynika z dwóch
     powyższych (limit dobowy ÷ liczba dawek). Dzięki temu dawka i suma
     dobowa nie mogą sobie przeczyć: od pewnej masy ciała dawka
     zatrzymuje się na tej granicy i dalej już nie rośnie.

     Kalkulator liczy wyłącznie w przeglądarce odwiedzającego. Podana masa
     ciała nigdzie nie jest wysyłana ani zapisywana — to celowe, bo dane
     o zdrowiu podlegają art. 9 RODO i nie powinny opuszczać urządzenia.

     ŻEBY DODAĆ PREPARAT: dopisz wiersz do właściwej listy poniżej.
     Kolejność na liście jest alfabetyczna.
     ===================================================================== */
  var LEKI = {
    ibuprofen: {
      mgKg: 10, maxDobowaMg: 400,
      dawekNaDobe: 4, odstep: 'co 6 godz.',
      preparaty: [
        { nazwa: 'Axoprofen Forte',           mg: 200, ml: 5 },
        { nazwa: 'Babyfen',                   mg: 100, ml: 5 },
        { nazwa: 'Brufen',                    mg: 100, ml: 5 },
        { nazwa: 'Brufen Forte',              mg: 200, ml: 5 },
        { nazwa: 'Bufenik',                   mg: 100, ml: 5 },
        { nazwa: 'Bufenik Forte',             mg: 200, ml: 5 },
        { nazwa: 'Ibum',                      mg: 100, ml: 5 },
        { nazwa: 'Ibum Forte',                mg: 200, ml: 5 },
        { nazwa: 'Ibum Forte Pure',           mg: 200, ml: 5 },
        { nazwa: 'Ibufen dla dzieci',         mg: 100, ml: 5 },
        { nazwa: 'Ibufen dla dzieci Forte',   mg: 200, ml: 5 },
        { nazwa: 'Ibunid dla dzieci Forte',   mg: 200, ml: 5 },
        { nazwa: 'Ibuprom dla Dzieci',        mg: 100, ml: 5 },
        { nazwa: 'Ibuprom dla Dzieci Forte',  mg: 200, ml: 5 },
        { nazwa: 'Ibutact',                   mg: 200, ml: 5 },
        { nazwa: 'Kidofen',                   mg: 100, ml: 5 },
        { nazwa: 'Kidofen max',               mg: 250, ml: 5 },
        { nazwa: 'MIG dla dzieci',            mg: 100, ml: 5 },
        { nazwa: 'MIG dla dzieci Forte',      mg: 200, ml: 5 },
        { nazwa: 'Milifen',                   mg: 100, ml: 5 },
        { nazwa: 'Nurofen dla dzieci',        mg: 100, ml: 5 },
        { nazwa: 'Nurofen dla dzieci Forte',  mg: 200, ml: 5 },
        { nazwa: 'Nurofen dla dzieci JUNIOR', mg: 200, ml: 5 }
      ]
    },
    paracetamol: {
      mgKg: 15, maxDobowaMg: 500,
      dawekNaDobe: 5, odstep: 'co 4 godz.',
      preparaty: [
        { nazwa: 'APAP dla dzieci FORTE',     mg: 200, ml: 5 },
        { nazwa: 'Calpol',                    mg: 120, ml: 5 },
        { nazwa: 'Calpol 6 Plus',             mg: 250, ml: 5 },
        { nazwa: 'Panadol dla dzieci',        mg: 120, ml: 5 },
        { nazwa: 'Paracetamol Aflofarm',      mg: 120, ml: 5 },
        { nazwa: 'Paracetamol Galena',        mg: 120, ml: 5 },
        { nazwa: 'Paracetamol Hasco',         mg: 120, ml: 5 },
        { nazwa: 'Paracetamol Hasco Forte',   mg: 240, ml: 5 },
        { nazwa: 'Pedicetamol',               mg: 100, ml: 1 },
        { nazwa: 'Infacetamol',               mg: 100, ml: 1 }
      ]
    }
  };

  var WAGA_MIN = 3;
  var WAGA_MAX = 60;
  var WAGA_OSTRZEZENIE = 6;

  /* ================================================================= */

  try {
    var $ = function (id) { return document.getElementById(id); };
    var selStez = $('kbLeki'), inpWaga = $('kbWaga'), btnOblicz = $('kbOblicz');
    if (!selStez || !inpWaga || !btnOblicz) { return; }

    var btnIbu = $('kbBtnIbu'), btnPara = $('kbBtnPara');
    var blad = $('kbBlad'), bladTresc = $('kbBladTresc'), wynik = $('kbWynik');
    var uwagaWiek = $('kbUwagaWiek');
    var outDawka = $('kbDawka'), outOdstep = $('kbOdstep'),
        outLiczba = $('kbLiczba'), outDoba = $('kbDoba');

    var aktywny = 'ibuprofen';
    var policzono = false;

    function pl(n) { return (Math.round(n * 10) / 10).toFixed(1).replace('.', ','); }

    /* Lista preparatow jako karty do klikniecia. Pod spodem sa zwykle
       pola radio, wiec wybor dziala z klawiatury (strzalki) i czyta go
       czytnik ekranu — bez ani jednej linijki obslugi zdarzen. */
    function odswiezStezenia() {
      selStez.innerHTML = '';
      LEKI[aktywny].preparaty.forEach(function (s, i) {
        var etykieta = document.createElement('label');
        etykieta.className = 'kb-lek';

        var radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'kbLek';
        /* Wartoscia jest stezenie w mg na 1 ml — dzieki temu krople
           100 mg / 1 ml i syrop 100 mg / 5 ml licza sie tak samo. */
        radio.value = String(s.mg / s.ml);
        if (i === 0) { radio.checked = true; }
        radio.addEventListener('change', function () { if (policzono) { oblicz(); } });

        /* Miniatura rysowana na miejscu, bez pobierania czegokolwiek
           z sieci: buteleczka syropu albo waska buteleczka z kroplomierzem.
           Poziom plynu i odcien ida za stezeniem, wiec juz z samego
           obrazka widac, czy preparat jest slabszy, czy mocniejszy. */
        var mgNaMl = s.mg / s.ml;
        var moc = mgNaMl >= 50 ? 3 : (mgNaMl >= 40 ? 2 : 1);
        var krople = s.ml === 1;
        var ikona = document.createElement('span');
        ikona.className = 'kb-lek-ikona kb-lek-ikona--' + moc + (krople ? ' kb-lek-ikona--krople' : '');
        ikona.setAttribute('aria-hidden', 'true');
        ikona.innerHTML = krople
          ? '<svg viewBox="0 0 28 36" width="28" height="36">' +
            '<rect class="k" x="10" y="1" width="8" height="5" rx="1.4"/>' +
            '<path class="s" d="M11 6h6l2.4 4.2v22.4a2 2 0 0 1-2 2h-6.8a2 2 0 0 1-2-2V10.2z"/>' +
            '<path class="p" d="M8.6 21h10.8v11.6a2 2 0 0 1-2 2h-6.8a2 2 0 0 1-2-2z"/>' +
            '</svg>'
          : '<svg viewBox="0 0 28 36" width="28" height="36">' +
            '<rect class="k" x="9.5" y="1" width="9" height="5" rx="1.4"/>' +
            '<path class="s" d="M8 8.6a2.6 2.6 0 0 1 2.6-2.6h6.8A2.6 2.6 0 0 1 20 8.6v24a2.4 2.4 0 0 1-2.4 2.4h-7.2A2.4 2.4 0 0 1 8 32.6z"/>' +
            '<path class="p" d="M8 18h12v14.6a2.4 2.4 0 0 1-2.4 2.4h-7.2A2.4 2.4 0 0 1 8 32.6z"/>' +
            '</svg>';

        var nazwa = document.createElement('span');
        nazwa.className = 'kb-lek-nazwa';
        nazwa.textContent = s.nazwa;

        var stez = document.createElement('span');
        stez.className = 'kb-lek-stezenie';
        stez.textContent = s.mg + ' mg / ' + s.ml + ' ml';

        etykieta.appendChild(radio);
        etykieta.appendChild(ikona);
        etykieta.appendChild(nazwa);
        etykieta.appendChild(stez);
        selStez.appendChild(etykieta);
      });
    }

    function wybranyPreparat() {
      var r = selStez.querySelector('input[name="kbLek"]:checked');
      return r ? parseFloat(r.value) : NaN;
    }

    function ustawLek(nazwa) {
      aktywny = nazwa;
      btnIbu.setAttribute('aria-pressed',  nazwa === 'ibuprofen'   ? 'true' : 'false');
      btnPara.setAttribute('aria-pressed', nazwa === 'paracetamol' ? 'true' : 'false');
      odswiezStezenia();
      if (policzono) { oblicz(); }
    }

    function oblicz() {
      var waga = parseFloat(String(inpWaga.value).replace(',', '.').trim());

      if (!isFinite(waga) || waga < WAGA_MIN || waga > WAGA_MAX) {
        bladTresc.textContent = 'Podaj masę ciała dziecka w zakresie ' + WAGA_MIN + '–' + WAGA_MAX + ' kg.';
        blad.classList.add('kb-on');
        wynik.classList.remove('kb-on');
        policzono = false;
        return;
      }
      blad.classList.remove('kb-on');

      var lek = LEKI[aktywny];
      var mgNaMl = wybranyPreparat();
      if (!isFinite(mgNaMl) || mgNaMl <= 0) { return; }

      /* Pokazujemy samą górną granicę, nie zakres. Dawka jednorazowa
         rośnie z masą ciała, ale zatrzymuje się na wartości, przy
         której zaplanowana liczba dawek wyczerpuje limit dobowy. */
      var maxJednorazowaMg = lek.maxDobowaMg / lek.dawekNaDobe;
      var mgDawka = Math.min(lek.mgKg * waga, maxJednorazowaMg);
      var mgDoba  = mgDawka * lek.dawekNaDobe;
      var naMl    = function (mg) { return mg / mgNaMl; };

      outDawka.textContent  = pl(naMl(mgDawka)) + ' ml';
      outOdstep.textContent = lek.odstep;
      outLiczba.textContent = lek.dawekNaDobe;
      outDoba.textContent   = pl(naMl(mgDoba)) + ' ml';


      if (uwagaWiek) { uwagaWiek.hidden = waga >= WAGA_OSTRZEZENIE; }

      wynik.classList.add('kb-on');
      policzono = true;
    }

    if (btnIbu && btnPara) {
      btnIbu.addEventListener('click',  function () { ustawLek('ibuprofen'); });
      btnPara.addEventListener('click', function () { ustawLek('paracetamol'); });
    }
    btnOblicz.addEventListener('click', oblicz);
    inpWaga.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); oblicz(); }
    });

    odswiezStezenia();

  } catch (err) {
    if (window.console && window.console.error) { window.console.error('kb-kalkulator:', err); }
  }
})();

(function () {
  'use strict';
  try {
    var karuzela = document.querySelector('[data-kb-karuzela]');
    if (!karuzela) { return; }
    var tor = karuzela.querySelector('[data-kb-tor]');

    /* Miniatury pobieramy z serwera YouTube. Gdy ktoras sie nie
       zaladuje (blokada sieci, film zdjety), przegladarka rysuje
       w rogu kafelka ikone zepsutego obrazka. Chowamy taki obrazek —
       zostaje lagodne tlo kafelka i przycisk odtwarzania, wiec
       karuzela dalej wyglada jak nalezy. */
    var miniatury = tor.querySelectorAll('.kb-film-karta img');
    for (var i = 0; i < miniatury.length; i++) {
      (function (obraz) {
        obraz.addEventListener('error', function () { obraz.hidden = true; });
        if (obraz.complete && obraz.naturalWidth === 0) { obraz.hidden = true; }
      })(miniatury[i]);
    }

    /* Klik w miniature podmienia ja na odtwarzacz. Do tego momentu
       zadne zapytanie do YouTube nie wychodzi. */
    tor.addEventListener('click', function (e) {
      var karta = e.target.closest ? e.target.closest('.kb-film-karta') : null;
      if (!karta) { return; }
      var id = karta.getAttribute('data-yt');
      if (!id) { return; }
      var ramka = document.createElement('iframe');
      ramka.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0';
      ramka.title = karta.getAttribute('aria-label') || 'Film';
      ramka.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture';
      ramka.allowFullscreen = true;
      ramka.loading = 'lazy';
      karta.parentNode.replaceChild(ramka, karta);
    });

    /* scrollBy z obiektem opcji dziala od Safari 14. Starsze wersje
       dostaja NaN i strzalki po prostu nic nie robia, wiec zostawiamy
       im zwykle przestawienie scrollLeft — bez plynnego przesuniecia,
       ale dzialajace. */
    var plynnie = false;
    try {
      var probny = { get behavior() { plynnie = true; return 'smooth'; } };
      tor.scrollBy(probny);
    } catch (e) { plynnie = false; }

    function przesun(kierunek) {
      var slajd = tor.querySelector('.kb-slajd');
      if (!slajd) { return; }
      var krok = slajd.getBoundingClientRect().width + 20;
      if (plynnie) { tor.scrollBy({ left: kierunek * krok, behavior: 'smooth' }); }
      else { tor.scrollLeft = tor.scrollLeft + kierunek * krok; }
    }
    karuzela.querySelector('[data-kb-poprzedni]').addEventListener('click', function () { przesun(-1); });
    karuzela.querySelector('[data-kb-nastepny]').addEventListener('click',  function () { przesun(1);  });

    /* Strzalki gasna na koncach toru, zeby nie obiecywaly ruchu,
       ktorego nie ma. */
    /* Luz musi byc wiekszy niz poziomy padding toru — przy dosunieciu
       do lewej scrollLeft nie wynosi 0, tylko tyle, ile ten padding. */
    var LUZ = 12;
    function odswiezStrzalki() {
      var doKonca = tor.scrollWidth - tor.clientWidth - tor.scrollLeft;
      karuzela.querySelector('[data-kb-poprzedni]').disabled = tor.scrollLeft <= LUZ;
      karuzela.querySelector('[data-kb-nastepny]').disabled  = doKonca <= LUZ;
    }
    tor.addEventListener('scroll', odswiezStrzalki, { passive: true });
    window.addEventListener('resize', odswiezStrzalki);
    odswiezStrzalki();
  } catch (err) {
    if (window.console && window.console.error) { window.console.error('kb-karuzela:', err); }
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
      var filmy = document.querySelectorAll('.kb-sekcja video, .kb-film-ramka video');
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
