#!/usr/bin/env python3
"""Przerabia krotkie ujecia na gladkie petle.

Wczesniej petla powstawala metoda "tam i z powrotem" (material grany
do przodu, potem do tylu). Przy ludzkim ruchu odtworzenie wstecz widac
od razu i wyglada karykaturalnie.

Tutaj koniec ujecia jest przenikany w jego poczatek: ostatnie N sekund
rozplywa sie w pierwsze N sekund, wiec gdy odtwarzacz wraca na start,
obraz juz tam jest. Zadnej klatki nie gramy wstecz.

Dodatkowo material jest lekko zwolniony (0,8x) z miekszeniem klatek
posrednich — ruch robi sie spokojniejszy.
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
FP = FF.replace("ffmpeg-", "ffprobe-")
UPL = Path("/root/.claude/uploads/1c4b41f1-e91d-5f47-b338-0a6ae7c67aba")
CEL = Path("/home/user/drk/assets/wideo")

ZADANIA = [
    ("c204a7a6-Shot_V10024.mp4",       "pediatria-mis"),
    ("d34b8af4-estetyczna__V10001.mp4", "estetyczna-01"),
    ("db618854-estetyczna__V10003.mp4", "estetyczna-02"),
    ("bef7d9e7-estetyczna__V10004.mp4", "estetyczna-03"),
]

SZEROKOSC = 900          # kadr pionowy 900x1600 — ostry takze na ekranach 2x
ZWOLNIENIE = 1.25        # 1/0.8 — material gramy o 20% wolniej
PRZENIKANIE = 0.8        # sekundy, przez ktore koniec przechodzi w poczatek
KLATKI = 30


def dlugosc(plik):
    out = subprocess.run(
        [FF, "-i", str(plik)], capture_output=True, text=True
    ).stderr
    for linia in out.splitlines():
        if "Duration:" in linia:
            czas = linia.split("Duration:")[1].split(",")[0].strip()
            g, m, s = czas.split(":")
            return int(g) * 3600 + int(m) * 60 + float(s)
    raise SystemExit("nie umiem odczytac dlugosci %s" % plik)


def zbuduj(zrodlo, nazwa):
    d_zrodla = dlugosc(zrodlo)
    d = d_zrodla * ZWOLNIENIE          # dlugosc po zwolnieniu
    n = min(PRZENIKANIE, d / 3)        # przenikanie nigdy dluzsze niz 1/3
    srodek = d - 2 * n                 # czesc grana bez przenikania
    if srodek <= 0.2:
        n = d / 3
        srodek = d - 2 * n

    wynik = CEL / (nazwa + ".mp4")
    plakat = CEL / (nazwa + ".jpg")

    filtr = (
        # wspolna obrobka: skala, zwolnienie, klatki posrednie
        "[0:v]scale={w}:-2:flags=lanczos,setpts={z}*PTS,"
        "minterpolate=fps={k}:mi_mode=blend,format=yuv420p[v];"
        # trzy kawalki: poczatek, srodek, koniec
        "[v]split=3[a][b][c];"
        # xfade wymaga stalej liczby klatek na sekunde na obu wejsciach,
        # stad fps= po kazdym przycieciu
        "[a]trim=0:{n},setpts=PTS-STARTPTS,fps={k}[glowa];"
        "[b]trim={n}:{do_konca},setpts=PTS-STARTPTS,fps={k}[srodek];"
        "[c]trim={do_konca}:{d},setpts=PTS-STARTPTS,fps={k}[ogon];"
        # ogon rozplywa sie w glowe
        "[ogon][glowa]xfade=transition=fade:duration={n}:offset=0[szew];"
        # Przenikanie idzie NA POCZATEK, nie na koniec. Wtedy w miejscu
        # zapetlenia stykaja sie dwie czyste klatki: ostatnia klatka
        # srodka i pierwsza klatka przenikania, ktora jest jeszcze w
        # 100% ogonem — czyli dokladnie nastepna klatka materialu.
        # Przy odwrotnej kolejnosci petla wracala z konca przenikania,
        # ktory nosi slad ogona, i bylo widac przeskok.
        "[szew][srodek]concat=n=2:v=1:a=0[out]"
    ).format(w=SZEROKOSC, z=ZWOLNIENIE, k=KLATKI,
             n=round(n, 3), do_konca=round(d - n, 3), d=round(d, 3))

    subprocess.run([
        FF, "-y", "-i", str(zrodlo),
        "-filter_complex", filtr, "-map", "[out]",
        "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "28",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(wynik),
    ], check=True, capture_output=True)

    subprocess.run([
        FF, "-y", "-i", str(wynik), "-frames:v", "1", "-q:v", "4", str(plakat),
    ], check=True, capture_output=True)

    d_wyn = dlugosc(wynik)
    print("%-15s %.2fs -> %.2fs petli, %.2f MB, plakat %.0f kB" % (
        nazwa, d_zrodla, d_wyn, wynik.stat().st_size / 1e6,
        plakat.stat().st_size / 1e3))


for plik, nazwa in ZADANIA:
    zbuduj(UPL / plik, nazwa)
