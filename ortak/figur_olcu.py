"""Gömülü figürün çerçeve yüksekliği — site/src/lib/grafikOlcu.ts'nin Python eşi.

Bileşen (`GrafikEmbed`) iframe yüksekliğini derleme anında bu kuralla kurar;
yayın kapısı (sayfa sınavı 3) ve hat koşusunun kopyalama uyarısı
(`guncelle.yukseklik_bulgulari`) aynı soruyu bu modülden sorar. İki dil, tek
sözleşme — `ortak/bicim.py` ↔ `lib/bicim.ts` gibi; biri değişirse öbürü de.

KURAL: sayfanın elle yazdığı yükseklik bir ALT SINIRDIR, figürün kendi ilan
ettiği yükseklik onu aşarsa figürünki geçer. Önceki kural "elle yazılan
KAZANIR"dı ve 25.09.2026'da ölçüldü: 483 gömmenin ikisi canlı sitede
kırpılıyordu (FX haber endeksi Şekil 10 · 430 piksel, YP mevduat Şekil 05 ·
26 piksel) ve bir hattın alt yazısı veriye bağlı olarak bir satır uzayıp
kısaldığında sayfa eski sayıyı ilan etmeye devam ediyor, yayın kapısı düşüyor
ve site donuyordu (fonlama Şekil 07 · 09.09, Şekil 04 · 25.09). Elle yazılan
sayı figürün yüksekliğinin ikinci bir kopyasıydı; iki kopya veri değiştikçe
ayrışır. Yeni kuralda kırpılma, figür yüksekliğini ilan ettiği sürece yapısal
olarak imkânsızdır; figür küçülürse aradaki fark yalnız boşluktur.

AYRIŞTIRMA figürün DÜZENİNDEN (Plotly.newPlot'un üçüncü argümanı) yapılır:
dosyadaki ilk "height" bir tablo izinin hücre yüksekliği olabilir (bütçe
Şekil 09'da ilk eşleşme 24 piksel, düzeninki 1227).
"""
from __future__ import annotations

import json
import re

ONTANIMLI = 540
EN_AZ = 260
# Emniyet tavanı: bozuk bir figür sayfayı ele geçirmesin. Sitedeki en uzun
# meşru figür 2.300 piksel (REDK 10 yıllık analiz); 1.600'lük eski tavan on üç
# gömülü figürün kendi ilanını görmezden geliyordu.
EN_COK = 2600

_ESKI = re.compile(r'"height"\s*:\s*(\d{2,4})\b')


def _deger_sonu(t: str, k: int) -> int:
    """t[k]'dan (boşluk atlanarak) başlayan JSON değerinin bittiği konum; -1 bozuk."""
    n = len(t)
    while k < n and t[k] in " \t\r\n":
        k += 1
    if k >= n:
        return -1
    c = t[k]
    if c == '"':
        k += 1
        while k < n:
            if t[k] == "\\":
                k += 2
                continue
            if t[k] == '"':
                return k + 1
            k += 1
        return -1
    if c in "[{":
        derin = 0
        while k < n:
            ch = t[k]
            if ch == '"':
                k += 1
                while k < n and t[k] != '"':
                    k += 2 if t[k] == "\\" else 1
            elif ch in "[{":
                derin += 1
            elif ch in "]}":
                derin -= 1
                if derin == 0:
                    return k + 1
            k += 1
        return -1
    while k < n and t[k] not in ",)]}":
        k += 1
    return k


def _duzen(t: str) -> dict | None:
    """Plotly.newPlot("kimlik", [veri], {düzen}, {ayar}) çağrısının düzen nesnesi."""
    i = t.find("Plotly.newPlot(")
    if i < 0:
        return None
    k = i + len("Plotly.newPlot(")
    for _ in range(2):                                   # kimlik, veri
        k = _deger_sonu(t, k)
        if k < 0:
            return None
        while k < len(t) and t[k] in " \t\r\n":
            k += 1
        if k >= len(t) or t[k] != ",":
            return None
        k += 1
    while k < len(t) and t[k] in " \t\r\n":
        k += 1
    son = _deger_sonu(t, k)
    if son < 0 or k >= len(t) or t[k] != "{":
        return None
    try:
        d = json.loads(t[k:son])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def ilan_edilen_yukseklik(metin: str) -> int | None:
    """Figür dosyasının metninden ilan ettiği yükseklik (piksel); yoksa None."""
    if "Plotly.newPlot(" in metin:
        d = _duzen(metin)
        h = d.get("height") if d else None
        if isinstance(h, bool) or not isinstance(h, (int, float)):
            return None
    else:
        # Plotly dışı bir gömme: tek ipucu düz metindeki ilk yükseklik.
        m = _ESKI.search(metin)
        if not m:
            return None
        h = int(m.group(1))
    return int(h) if EN_AZ <= h <= EN_COK else None


def cerceve_yuksekligi(acik: int | None, ilan: int | None) -> int:
    """iframe yüksekliği: elle yazılan ALT SINIR, figürün ilanı onu aşarsa ilan."""
    if acik is not None and ilan is not None:
        return max(acik, ilan)
    if acik is not None:
        return acik
    return ilan if ilan is not None else ONTANIMLI
