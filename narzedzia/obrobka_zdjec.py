#!/usr/bin/env python3
"""
Masowa obróbka zdjęć: autokontrast, subtelne ocieplenie, vibrance ~15 %,
delikatne wyostrzenie; zapis w oryginalnej rozdzielczości jako JPG (q=95).

Użycie:
    python3 obrobka_zdjec.py [ZRODLO] [CEL] [--pomin-istniejace] [--procesy N]

Wymagane: Pillow, numpy. Opcjonalnie: rawpy (pliki RAW: CR2, NEF, ARW, DNG…).
"""
import argparse
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

try:
    import rawpy
except ImportError:
    rawpy = None

ZRODLO = "/Users/dariamalinowska/Desktop/Chemia Przyszłości 2026"
CEL = "/Users/dariamalinowska/Desktop/Po obróbce chemia"

ROZSZ_ZWYKLE = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
ROZSZ_RAW = {".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".dng",
             ".raf", ".orf", ".rw2", ".pef", ".srw", ".3fr", ".iiq", ".raw"}

# --- Parametry obróbki -------------------------------------------------------
KLIP_CIENIE = 0.3      # % najciemniejszych pikseli przycinanych do czerni
KLIP_SWIATLA = 0.3     # % najjaśniejszych pikseli przycinanych do bieli
MAKS_ROZCIAGNIECIE = 1.6  # ograniczenie wzmocnienia kontrastu (ochrona przed szumem)
MAKS_PUNKT_CZERNI = 40    # czerń nie wyżej niż 40/255 (zdjęcia celowo jasne)
MIN_PUNKT_BIELI = 215     # biel nie niżej niż 215/255 (zdjęcia celowo ciemne)
OCIEPLENIE_R = 1.025   # +2,5 % kanał czerwony
OCIEPLENIE_B = 0.97    # −3 % kanał niebieski (białe fartuchy nie żółkną)
VIBRANCE = 0.15        # +15 %, silniej dla słabo nasyconych pikseli
WYOSTRZ_PROMIEN = 1.2
WYOSTRZ_PROCENT = 60
WYOSTRZ_PROG = 3
JAKOSC_JPG = 95


def wczytaj(sciezka: Path) -> tuple[Image.Image, dict]:
    """Zwraca obraz RGB (8 bit) oraz metadane do zachowania (ICC, EXIF)."""
    meta = {}
    if sciezka.suffix.lower() in ROZSZ_RAW:
        if rawpy is None:
            raise RuntimeError("plik RAW wymaga biblioteki rawpy (pip install rawpy)")
        with rawpy.imread(str(sciezka)) as raw:
            rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False,
                                  output_bps=8)
        return Image.fromarray(rgb), meta

    im = Image.open(sciezka)
    im.load()
    if im.info.get("icc_profile"):
        meta["icc_profile"] = im.info["icc_profile"]
    try:
        exif = im.getexif()
        if exif:
            exif[0x0112] = 1  # orientacja zostanie „wypalona” w piksele
            meta["exif"] = exif.tobytes()
    except Exception:
        pass

    im = ImageOps.exif_transpose(im)

    # Obrazy 16-bitowe / zmiennoprzecinkowe (częste w TIFF) → 8 bit bez obcinania
    if im.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
        a = np.asarray(im, dtype=np.float64)
        maks = 65535.0 if a.max() > 255 else 255.0
        im = Image.fromarray(np.clip(a / maks * 255.0, 0, 255).astype(np.uint8))

    # Przezroczystość → białe tło (JPG nie obsługuje kanału alfa)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        tlo = Image.new("RGB", im.size, (255, 255, 255))
        tlo.paste(im, mask=im.getchannel("A"))
        im = tlo
    elif im.mode != "RGB":
        im = im.convert("RGB")
    return im, meta


def autokontrast(a: np.ndarray) -> np.ndarray:
    """Wyrównanie poziomów na luminancji (usuwa „mgłę”). Różnica jasności jest
    dodawana do każdego kanału, więc balans i nasycenie kolorów się nie zmieniają.
    Punkty czerni/bieli są ograniczone, by nie niszczyć zdjęć celowo jasnych
    lub ciemnych (np. high-key na tle białych fartuchów)."""
    luma = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    ciemny = min(np.percentile(luma, KLIP_CIENIE), MAKS_PUNKT_CZERNI)
    jasny = max(np.percentile(luma, 100 - KLIP_SWIATLA), MIN_PUNKT_BIELI)
    zakres = max(jasny - ciemny, 255.0 / MAKS_ROZCIAGNIECIE)
    nowa = (luma - ciemny) * (255.0 / zakres)
    return a + (nowa - luma)[..., None]


def ocieplenie(a: np.ndarray) -> np.ndarray:
    a = a.copy()
    a[..., 0] *= OCIEPLENIE_R
    a[..., 2] *= OCIEPLENIE_B
    return a


def vibrance(a: np.ndarray) -> np.ndarray:
    """Podbicie nasycenia ważone (1 − nasycenie): słabe kolory rosną ~15 %,
    już nasycone (np. skóra, czerwienie) prawie wcale."""
    a = np.clip(a, 0, 255)
    luma = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
    mx = a.max(axis=2, keepdims=True)
    mn = a.min(axis=2, keepdims=True)
    nas = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    wsp = 1.0 + VIBRANCE * (1.0 - nas)
    return luma + (a - luma) * wsp


def wyostrz(im: Image.Image) -> Image.Image:
    """Maska wyostrzająca tylko na luminancji — bez kolorowych obwódek."""
    y, cb, cr = im.convert("YCbCr").split()
    y = y.filter(ImageFilter.UnsharpMask(radius=WYOSTRZ_PROMIEN,
                                         percent=WYOSTRZ_PROCENT,
                                         threshold=WYOSTRZ_PROG))
    return Image.merge("YCbCr", (y, cb, cr)).convert("RGB")


def obrob(zrodlo: str, cel: str) -> tuple[str, str | None]:
    try:
        im, meta = wczytaj(Path(zrodlo))
        rozmiar = im.size
        a = np.asarray(im, dtype=np.float32)
        a = autokontrast(a)
        a = ocieplenie(a)
        a = vibrance(a)
        im = Image.fromarray(np.clip(a + 0.5, 0, 255).astype(np.uint8), "RGB")
        im = wyostrz(im)
        assert im.size == rozmiar, "zmieniła się rozdzielczość"

        Path(cel).parent.mkdir(parents=True, exist_ok=True)
        tymcz = cel + ".part"
        im.save(tymcz, "JPEG", quality=JAKOSC_JPG, subsampling=0,
                optimize=True, **meta)
        os.replace(tymcz, cel)
        return zrodlo, None
    except Exception as e:
        return zrodlo, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=2)}"


def zbierz(zrodlo: Path, cel: Path) -> list[tuple[str, str]]:
    zadania, zajete = [], set()
    for p in sorted(zrodlo.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        rozsz = p.suffix.lower()
        if rozsz not in ROZSZ_ZWYKLE | ROZSZ_RAW:
            continue
        wzgl = p.relative_to(zrodlo)
        wyj = cel / wzgl.with_suffix(".jpg")
        # Kolizja nazw (np. foto.png i foto.jpg) → foto_png.jpg
        if str(wyj).lower() in zajete:
            wyj = cel / wzgl.with_name(f"{p.stem}_{rozsz[1:]}.jpg")
        zajete.add(str(wyj).lower())
        zadania.append((str(p), str(wyj)))
    return zadania


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zrodlo", nargs="?", default=ZRODLO)
    ap.add_argument("cel", nargs="?", default=CEL)
    ap.add_argument("--pomin-istniejace", action="store_true",
                    help="nie przetwarzaj ponownie plików, które już są w celu")
    ap.add_argument("--procesy", type=int, default=os.cpu_count() or 2)
    arg = ap.parse_args()

    zrodlo, cel = Path(arg.zrodlo).expanduser(), Path(arg.cel).expanduser()
    if not zrodlo.is_dir():
        print(f"BŁĄD: brak folderu źródłowego: {zrodlo}")
        return 2
    cel.mkdir(parents=True, exist_ok=True)

    zadania = zbierz(zrodlo, cel)
    licznik = {}
    for z, _ in zadania:
        k = Path(z).suffix.lower()
        k = "RAW" if k in ROZSZ_RAW else k.lstrip(".").upper().replace("JPEG", "JPG").replace("TIFF", "TIF")
        licznik[k] = licznik.get(k, 0) + 1
    print(f"Znaleziono {len(zadania)} plików graficznych: "
          + (", ".join(f"{k}: {v}" for k, v in sorted(licznik.items())) or "brak"))

    pominiete = 0
    if arg.pomin_istniejace:
        przed = len(zadania)
        zadania = [(z, c) for z, c in zadania if not Path(c).exists()]
        pominiete = przed - len(zadania)
    if rawpy is None and "RAW" in licznik:
        print("UWAGA: brak rawpy — pliki RAW zakończą się błędem (pip install rawpy).")

    t0, ok, bledy = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=max(1, arg.procesy)) as pula:
        fut = [pula.submit(obrob, z, c) for z, c in zadania]
        for i, f in enumerate(as_completed(fut), 1):
            z, blad = f.result()
            if blad:
                bledy.append((z, blad))
            else:
                ok += 1
            print(f"\r[{i}/{len(zadania)}] {Path(z).name[:60]:<60}", end="", flush=True)
    print()

    dziennik = cel / "_dziennik_obrobki.txt"
    with open(dziennik, "w", encoding="utf-8") as d:
        d.write(f"Źródło: {zrodlo}\nCel: {cel}\n")
        d.write(f"Przetworzono poprawnie: {ok}\nPominięto (istniały): {pominiete}\n")
        d.write(f"Błędy: {len(bledy)}\n\n")
        for z, b in bledy:
            d.write(f"{z}\n  {b}\n")

    print("=" * 60)
    print(f"Obrobiono poprawnie: {ok}")
    if pominiete:
        print(f"Pominięto (już istniały): {pominiete}")
    print(f"Błędy: {len(bledy)}")
    for z, b in bledy:
        print(f"  ✗ {Path(z).name}: {b.splitlines()[0]}")
    print(f"Czas: {time.time() - t0:.1f} s   Dziennik: {dziennik}")
    return 1 if bledy else 0


if __name__ == "__main__":
    sys.exit(main())
