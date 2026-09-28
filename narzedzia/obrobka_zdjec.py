#!/usr/bin/env python3
"""
Masowa obróbka zdjęć i filmów: autokontrast, subtelne ocieplenie,
vibrance ~15 %, delikatne wyostrzenie.
  • zdjęcia → JPG (q=95) w oryginalnej rozdzielczości,
  • filmy   → MP4 H.264 (CRF 18) w oryginalnej rozdzielczości i klatkażu, z dźwiękiem;
    nagrania HDR z iPhone'a (HLG / Dolby Vision) są konwertowane do SDR.

Użycie:
    python3 obrobka_zdjec.py [ZRODLO] [CEL] [--pomin-istniejace] [--procesy N]

Wymagane: Pillow, numpy. Opcjonalnie: pillow-heif (HEIC z iPhone'a),
rawpy (RAW: CR2, NEF, ARW, DNG…), imageio-ffmpeg lub systemowy ffmpeg (filmy).
"""
import argparse
import os
import re
import shutil
import subprocess
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

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

ZRODLO = "/Users/dariamalinowska/Desktop/Chemia Przyszłości 2026"
CEL = "/Users/dariamalinowska/Desktop/Po obróbce chemia"

ROZSZ_ZWYKLE = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
ROZSZ_HEIC = {".heic", ".heif"}
ROZSZ_WIDEO = {".mov", ".mp4", ".m4v"}
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
WIDEO_CRF = 18         # H.264: 18 ≈ wizualnie bezstratnie, pliki ~2× oryginału
WIDEO_PRESET = "medium"


def wczytaj(sciezka: Path) -> tuple[Image.Image, dict]:
    """Zwraca obraz RGB (8 bit) oraz metadane do zachowania (ICC, EXIF)."""
    meta = {}
    if sciezka.suffix.lower() in ROZSZ_HEIC and pillow_heif is None:
        raise RuntimeError("plik HEIC wymaga biblioteki pillow-heif (pip install pillow-heif)")
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
    ciemny, zakres = punkty_poziomow(luma)
    nowa = (luma - ciemny) * (255.0 / zakres)
    return a + (nowa - luma)[..., None]


def punkty_poziomow(luma: np.ndarray) -> tuple[float, float]:
    """Punkt czerni i szerokość zakresu tonalnego (wspólne dla zdjęć i filmów)."""
    ciemny = min(np.percentile(luma, KLIP_CIENIE), MAKS_PUNKT_CZERNI)
    jasny = max(np.percentile(luma, 100 - KLIP_SWIATLA), MIN_PUNKT_BIELI)
    return float(ciemny), float(max(jasny - ciemny, 255.0 / MAKS_ROZCIAGNIECIE))


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


# --- Filmy ------------------------------------------------------------------

def znajdz_ffmpeg() -> str | None:
    """Preferuje systemowy ffmpeg (np. z Homebrew), w razie braku — imageio-ffmpeg."""
    sciezka = shutil.which("ffmpeg")
    if sciezka:
        return sciezka
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def ma_filtr(ffmpeg: str, nazwa: str) -> bool:
    wyj = subprocess.run([ffmpeg, "-hide_banner", "-filters"],
                         capture_output=True, text=True).stdout
    return re.search(rf"\s{re.escape(nazwa)}\s", wyj) is not None


def filtr_wstepny(ffmpeg: str, zrodlo: str) -> str:
    """HDR (HLG z iPhone'a lub PQ) → SDR BT.709; SDR pozostaje bez zmian."""
    info = subprocess.run([ffmpeg, "-hide_banner", "-i", zrodlo],
                          capture_output=True, text=True).stderr
    strumien = next((l for l in info.splitlines() if "Video:" in l), "")
    if "arib-std-b67" in strumien:
        tin = "arib-std-b67"
    elif "smpte2084" in strumien:
        tin = "smpte2084"
    else:
        return "format=yuv420p"
    if not ma_filtr(ffmpeg, "zscale"):
        raise RuntimeError("film HDR wymaga ffmpeg z filtrem zscale "
                           "(macOS: brew install ffmpeg)")
    return (f"zscale=tin={tin}:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=100,"
            "format=gbrpf32le,zscale=p=bt709,"
            "tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def poziomy_filmu(ffmpeg: str, zrodlo: str, wstepny: str) -> tuple[float, float]:
    """Jeden zestaw poziomów dla całego filmu (z ~2 klatek/s), żeby obraz
    nie „pulsował” jasnością między klatkami."""
    w, h = 256, 256
    wynik = subprocess.run(
        [ffmpeg, "-v", "error", "-i", zrodlo, "-vf",
         f"{wstepny},fps=2,scale={w}:{h},format=rgb24", "-f", "rawvideo", "-"],
        capture_output=True, check=True)
    klatki = np.frombuffer(wynik.stdout, np.uint8).reshape(-1, h, w, 3).astype(np.float32)
    luma = 0.299 * klatki[..., 0] + 0.587 * klatki[..., 1] + 0.114 * klatki[..., 2]
    return punkty_poziomow(luma)


def obrob_film(zrodlo: str, cel: str, ffmpeg: str) -> tuple[str, str | None]:
    try:
        wstepny = filtr_wstepny(ffmpeg, zrodlo)
        ciemny, zakres = poziomy_filmu(ffmpeg, zrodlo, wstepny)
        # Poziomy tylko na kanale Y (U, V bez zmian) — odpowiednik autokontrastu
        # zdjęć, który przesuwa jasność, nie ruszając barwy.
        k = 219.0 / zakres
        poziomy = f"lutyuv=y='clip(16+((val-16)*255/219-{ciemny:.3f})*{k:.5f},16,235)'"
        wyostrz = f"unsharp=5:5:{WYOSTRZ_PROCENT / 100:.2f}:5:5:0"
        filtry = ",".join([
            wstepny, poziomy,
            f"colorchannelmixer=rr={OCIEPLENIE_R}:bb={OCIEPLENIE_B}",
            f"vibrance=intensity={VIBRANCE}",
            wyostrz, "format=yuv420p"])
        Path(cel).parent.mkdir(parents=True, exist_ok=True)
        tymcz = cel + ".part.mp4"
        wynik = subprocess.run(
            [ffmpeg, "-v", "error", "-y", "-i", zrodlo,
             "-map", "0:v:0", "-map", "0:a:0?", "-map_metadata", "0",
             "-vf", filtry,
             "-c:v", "libx264", "-crf", str(WIDEO_CRF), "-preset", WIDEO_PRESET,
             "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tymcz],
            capture_output=True, text=True)
        if wynik.returncode != 0:
            raise RuntimeError(wynik.stderr.strip()[-500:])
        os.replace(tymcz, cel)
        return zrodlo, None
    except Exception as e:
        return zrodlo, f"{type(e).__name__}: {e}"


# --- Wspólne ----------------------------------------------------------------

def zbierz(zrodlo: Path, cel: Path) -> list[tuple[str, str]]:
    zadania, zajete = [], set()
    for p in sorted(zrodlo.rglob("*")):
        if not p.is_file() or p.name.startswith("."):
            continue
        rozsz = p.suffix.lower()
        if rozsz not in ROZSZ_ZWYKLE | ROZSZ_HEIC | ROZSZ_RAW | ROZSZ_WIDEO:
            continue
        nowe = ".mp4" if rozsz in ROZSZ_WIDEO else ".jpg"
        wzgl = p.relative_to(zrodlo)
        wyj = cel / wzgl.with_suffix(nowe)
        # Kolizja nazw (np. foto.png i foto.jpg) → foto_png.jpg
        if str(wyj).lower() in zajete:
            wyj = cel / wzgl.with_name(f"{p.stem}_{rozsz[1:]}{nowe}")
        zajete.add(str(wyj).lower())
        zadania.append((str(p), str(wyj)))
    return zadania


def rodzaj(sciezka: str) -> str:
    k = Path(sciezka).suffix.lower()
    if k in ROZSZ_RAW:
        return "RAW"
    if k in ROZSZ_WIDEO:
        return "WIDEO"
    return k.lstrip(".").upper().replace("JPEG", "JPG").replace("TIFF", "TIF").replace("HEIF", "HEIC")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zrodlo", nargs="?", default=ZRODLO)
    ap.add_argument("cel", nargs="?", default=CEL)
    ap.add_argument("--pomin-istniejace", action="store_true",
                    help="nie przetwarzaj ponownie plików, które już są w celu")
    ap.add_argument("--bez-filmow", action="store_true", help="obrabiaj tylko zdjęcia")
    ap.add_argument("--procesy", type=int, default=os.cpu_count() or 2)
    arg = ap.parse_args()

    zrodlo, cel = Path(arg.zrodlo).expanduser(), Path(arg.cel).expanduser()
    if not zrodlo.is_dir():
        print(f"BŁĄD: brak folderu źródłowego: {zrodlo}")
        return 2
    cel.mkdir(parents=True, exist_ok=True)

    zadania = zbierz(zrodlo, cel)
    if arg.bez_filmow:
        zadania = [(z, c) for z, c in zadania if rodzaj(z) != "WIDEO"]
    licznik = {}
    for z, _ in zadania:
        licznik[rodzaj(z)] = licznik.get(rodzaj(z), 0) + 1
    print(f"Znaleziono {len(zadania)} plików: "
          + (", ".join(f"{k}: {v}" for k, v in sorted(licznik.items())) or "brak"))

    pominiete = 0
    if arg.pomin_istniejace:
        przed = len(zadania)
        zadania = [(z, c) for z, c in zadania if not Path(c).exists()]
        pominiete = przed - len(zadania)
    if rawpy is None and "RAW" in licznik:
        print("UWAGA: brak rawpy — pliki RAW zakończą się błędem (pip install rawpy).")
    if pillow_heif is None and "HEIC" in licznik:
        print("UWAGA: brak pillow-heif — pliki HEIC zakończą się błędem (pip install pillow-heif).")

    zdjecia = [(z, c) for z, c in zadania if rodzaj(z) != "WIDEO"]
    filmy = [(z, c) for z, c in zadania if rodzaj(z) == "WIDEO"]
    t0, ok_zdj, ok_film, bledy = time.time(), 0, 0, []

    if zdjecia:
        print(f"Zdjęcia ({len(zdjecia)}):")
        with ProcessPoolExecutor(max_workers=max(1, arg.procesy)) as pula:
            fut = [pula.submit(obrob, z, c) for z, c in zdjecia]
            for i, f in enumerate(as_completed(fut), 1):
                z, blad = f.result()
                if blad:
                    bledy.append((z, blad))
                else:
                    ok_zdj += 1
                print(f"\r  [{i}/{len(zdjecia)}] {Path(z).name[:60]:<60}", end="", flush=True)
        print()

    if filmy:
        ffmpeg = znajdz_ffmpeg()
        print(f"Filmy ({len(filmy)}) — ffmpeg: {ffmpeg or 'BRAK'}")
        for i, (z, c) in enumerate(filmy, 1):
            print(f"  [{i}/{len(filmy)}] {Path(z).name} …", end="", flush=True)
            if ffmpeg is None:
                z, blad = z, "brak ffmpeg (pip install imageio-ffmpeg lub brew install ffmpeg)"
            else:
                t = time.time()
                z, blad = obrob_film(z, c, ffmpeg)
            if blad:
                bledy.append((z, blad))
                print(" BŁĄD")
            else:
                ok_film += 1
                print(f" gotowe ({time.time() - t:.0f} s)")

    dziennik = cel / "_dziennik_obrobki.txt"
    with open(dziennik, "w", encoding="utf-8") as d:
        d.write(f"Źródło: {zrodlo}\nCel: {cel}\n")
        d.write(f"Zdjęcia obrobione: {ok_zdj}\nFilmy obrobione: {ok_film}\n")
        d.write(f"Pominięto (istniały): {pominiete}\nBłędy: {len(bledy)}\n\n")
        for z, b in bledy:
            d.write(f"{z}\n  {b}\n")

    print("=" * 60)
    print(f"Zdjęcia obrobione poprawnie: {ok_zdj}")
    print(f"Filmy obrobione poprawnie:   {ok_film}")
    if pominiete:
        print(f"Pominięto (już istniały): {pominiete}")
    print(f"Błędy: {len(bledy)}")
    for z, b in bledy:
        print(f"  ✗ {Path(z).name}: {b.splitlines()[0][:200]}")
    print(f"Czas: {time.time() - t0:.1f} s   Dziennik: {dziennik}")
    return 1 if bledy else 0


if __name__ == "__main__":
    sys.exit(main())
