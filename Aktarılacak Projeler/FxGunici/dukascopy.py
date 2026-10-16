#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dukascopy'nin halka açık 1 dakikalık bid/ask mumları: indirme, çözme, arşiv.

KAYNAK. https://datafeed.dukascopy.com/datafeed/<SEMBOL>/<YYYY>/<AA−1>/<GG>/
<BID|ASK>_candles_min_1.bi5 — her UTC günü için bir dosya (ay klasörü SIFIRDAN
sayılır: Ocak = 00). Dosya LZMA ile sıkıştırılmış 24 baytlık kayıtlardan oluşur:

    büyük uçlu  int32 saniye (günün başından)  ·  int32 açılış  ·  int32 kapanış
                int32 düşük  ·  int32 yüksek  ·  float32 hacim

Alan SIRASI açılış–KAPANIŞ–düşük–yüksek'tir (OHLC değil). Sıra varsayılmaz,
sınanır: her dolu kayıtta düşük ≤ min(açılış, kapanış) ≤ max(açılış, kapanış)
≤ yüksek olmalı; sıra yanlış okunursa bu eşitsizlik kayıtların büyük kısmında
bozulur ve çözücü DÜŞER (sessizce yanlış fiyat üretmek yerine).

Fiyatlar NOKTA cinsinden tamsayıdır (EURUSD 1e-5, USDJPY 1e-3; ayar.toml).
Kotasyon olmayan dakikalar dosyada hacmi sıfır, fiyatı bir önceki kapanış olan
"dolgu" kayıtlarıdır; arşive yazılmaz (boşluk denetimi onları sayar).

HACİM. Dukascopy'nin hacmi, o dakikadaki kotasyonların en iyi fiyattaki
LİKİDİTE miktarlarının toplamıdır (milyon birim); gerçekleşmiş işlem hacmi
DEĞİLDİR ve FX'te merkezî bir işlem hacmi yoktur. Ders bunu açıkça yazar.

ARŞİV. Parite × yıl başına bir parquet: `veri/dukascopy/<SEMBOL>/<YYYY>.parquet`
  t            int64   dakikanın başlangıcı, UTC epoch saniye
  b_o b_h b_l b_c  int32  bid OHLC (nokta)
  d_o d_h d_l d_c  int32  ask − bid, alan alan (nokta; ask = bid + d)
  b_v a_v      float32 bid/ask hacmi
Yazım deterministiktir (sıralı satır, sabit şema, sabit sıkıştırma); künyedeki
sha256 aynı girdiden aynı dosyanın üretildiğini sınar.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import urllib3

KOK_URL = "https://datafeed.dukascopy.com/datafeed"
# ASCII başlık ŞART: http.client başlığı latin-1 ile kodlar; Türkçe bir harf
# isteği ağa çıkmadan düşürür (CLAUDE.md, TLREF uzantısı 23.09.2026).
BASLIK = {"User-Agent": "tto-trading-arastirma/1.0 (+https://cocoonish.github.io)"}

KAYIT = np.dtype([("s", ">i4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])
#: Aynı kayıt, makinenin bayt sırasında (pandas büyük uçlu tamponla birleştirme yapamıyor).
KAYIT_YEREL = KAYIT.newbyteorder("=")
SUTUNLAR = ["t", "b_o", "b_h", "b_l", "b_c", "d_o", "d_h", "d_l", "d_c", "b_v", "a_v"]
SEMA = pa.schema([
    ("t", pa.int64()),
    ("b_o", pa.int32()), ("b_h", pa.int32()), ("b_l", pa.int32()), ("b_c", pa.int32()),
    ("d_o", pa.int32()), ("d_h", pa.int32()), ("d_l", pa.int32()), ("d_c", pa.int32()),
    ("b_v", pa.float32()), ("a_v", pa.float32()),
])
SIKISTIRMA = {"compression": "zstd", "compression_level": 9}


class CozumHatasi(ValueError):
    pass


# ───────────────────────────────────────────────────────────── adresler
def dakika_url(sembol: str, gun: date, taraf: str) -> str:
    return f"{KOK_URL}/{sembol}/{gun.year:04d}/{gun.month - 1:02d}/{gun.day:02d}/{taraf}_candles_min_1.bi5"


def saatlik_url(sembol: str, yil: int, ay: int, taraf: str) -> str:
    """Ayın saatlik mumları (ay klasöründe tek dosya) — çapraz sınama için."""
    return f"{KOK_URL}/{sembol}/{yil:04d}/{ay - 1:02d}/{taraf}_candles_hour_1.bi5"


# ───────────────────────────────────────────────────────────── çözücü
def coz(ham: bytes, adim_sn: int = 60, azami: int = 1440) -> np.ndarray:
    """bi5 baytlarını kayıt dizisine çevirir ve yapıyı sınar.

    `adim_sn`: kayıtlar arası saniye (dakikalık 60, saatlik 3600).
    Boş dosya (0 bayt) boş dizi döner: kaynağın o gün için verisi yoktur.
    """
    if not ham:
        return np.empty(0, dtype=KAYIT_YEREL)
    acik = lzma.decompress(ham)
    if len(acik) % KAYIT.itemsize:
        raise CozumHatasi(f"kayıt boyu 24'ün katı değil: {len(acik)} bayt")
    k = np.frombuffer(acik, dtype=KAYIT).astype(KAYIT_YEREL)
    if len(k) > azami:
        raise CozumHatasi(f"beklenenden çok kayıt: {len(k)} > {azami}")
    s = k["s"].astype(np.int64)
    if (s % adim_sn).any() or (s < 0).any() or (s >= adim_sn * azami).any():
        raise CozumHatasi("zaman ofseti ızgaraya oturmuyor")
    if (np.diff(s) <= 0).any():
        raise CozumHatasi("zaman ofsetleri kesin artan değil")
    dolu = k["v"] > 0
    o, c, l, h = (k[x].astype(np.int64) for x in ("o", "c", "l", "h"))
    bozuk = dolu & ((l > np.minimum(o, c)) | (h < np.maximum(o, c)) | (l <= 0))
    if bozuk.any():
        raise CozumHatasi(
            f"OHLC eşitsizliği {int(bozuk.sum())}/{int(dolu.sum())} dolu kayıtta bozuk — "
            "alan sırası (açılış, kapanış, düşük, yüksek) tutmuyor olabilir"
        )
    return k


# ───────────────────────────────────────────────────────────── ağ
# İstekler urllib3 bağlantı havuzundan gider, `requests`ten DEĞİL. Sebep ölçüldü
# (16.10.2026, bulut koşusu): deponun ortak HTTP koruması (`ortak/sitecustomize.py`)
# requests'in her isteğini sarar ve aynı ana bilgisayarda iki ardışık tam
# başarısızlıkta 180 saniyelik bir DEVRE KESİCİ açar. O kural tek tek istek atan
# veri hatları için doğrudur; eşzamanlı binlerce dosya indiren bir arşivleyicide
# ise kaynağın birkaç geçici zaman aşımı kesiciyi açıyor ve kesik süresince BÜTÜN
# istekler denenmeden düşüyordu — iki yıllık birimde 16 ve 11 gün böyle kayboldu.
# Bu betik kendi zaman aşımını, yeniden denemesini ve bütçesini taşır.
_havuz_kilit = threading.Lock()
_HAVUZ = None


def _havuz(boyut: int = 16):
    global _HAVUZ
    with _havuz_kilit:
        if _HAVUZ is None:
            import os
            vekil = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            ortak = dict(num_pools=4, maxsize=boyut, block=True, headers=BASLIK, retries=False)
            _HAVUZ = urllib3.ProxyManager(vekil, **ortak) if vekil else urllib3.PoolManager(**ortak)
    return _HAVUZ


@dataclass
class Yanit:
    durum: str          # "tamam" · "bos" · "yok" (404) · "hata"
    ham: bytes = b""
    ayrinti: str = ""
    deneme: int = 0


class Hiz:
    """İş parçacıklarının PAYLAŞTIĞI istek başlatma hızı (pencereli uyarlama).

    Ölçüm (16.10.2026, bulut koşuları 38874324826 ve 38877633100): kaynak isteklerin
    üçte birine 503 ya da zaman aşımı döndürüyor ve bu oran istek hızından büyük ölçüde
    BAĞIMSIZ — saniyede 0,2 istekte de %33. Aynı dosyalar sonraki bir koşuda iniyor:
    ret çoğunlukla "şimdi değil" demek. İlk tasarım her rette bütün iş parçacıklarını
    10 sn durdurup hızı yarıya indiriyordu; o koşuda dört işin her biri saniyede ~0,24
    istek yapabildi ve iş zamanının çoğu beklemeyle geçti. Bu sınıf artık rete tek tek
    tepki vermez: son `pencere` isteğin ret oranı yüksekse hızı azaltır, düşükse artırır.
    Reddedilen dosyayı yeniden denemek çağıranın işidir (`toplu_getir`, ertelemeli kuyruk).
    Yalnız 429 (açık istek sınırı) ve Retry-After başlığı herkesi birlikte bekletir.
    """

    def __init__(self, baslangic: float = 3.0, taban: float = 0.5, tavan: float = 8.0, pencere: int = 40):
        self.hiz, self.taban, self.tavan, self.pencere = baslangic, taban, tavan, pencere
        self._kilit = threading.Lock()
        self._sonraki = time.monotonic()
        self._dur = 0.0
        self._son: list[bool] = []
        self.sayac = {"tamam": 0, "ret": 0, "ag": 0, "bekleme_sn": 0.0, "en_dusuk_hiz": baslangic,
                      "en_yuksek_hiz": baslangic}

    def bekle(self, son_an: float | None = None) -> bool:
        """Sıradaki isteğin başlama anını bekler; bütçe o andan önce dolacaksa False."""
        with self._kilit:
            simdi = time.monotonic()
            t = max(self._sonraki, self._dur, simdi)
            self._sonraki = t + 1.0 / self.hiz
        if son_an is not None and t > son_an:
            return False
        if t > simdi:
            time.sleep(t - simdi)
            with self._kilit:
                self.sayac["bekleme_sn"] += t - simdi
        return True

    def _kaydet(self, basari: bool) -> None:
        self._son.append(basari)
        if len(self._son) >= self.pencere:
            ret = 1.0 - sum(self._son) / len(self._son)
            if ret > 0.6:
                self.hiz = max(self.taban, self.hiz * 0.75)
            elif ret < 0.25:
                self.hiz = min(self.tavan, self.hiz * 1.15)
            self.sayac["en_dusuk_hiz"] = min(self.sayac["en_dusuk_hiz"], self.hiz)
            self.sayac["en_yuksek_hiz"] = max(self.sayac["en_yuksek_hiz"], self.hiz)
            self._son = []

    def basarili(self) -> None:
        with self._kilit:
            self.sayac["tamam"] += 1
            self._kaydet(True)

    def reddedildi(self, bekle_sn: float | None = None, ag: bool = False) -> None:
        with self._kilit:
            self.sayac["ag" if ag else "ret"] += 1
            self._kaydet(False)
            if bekle_sn:
                self._dur = max(self._dur, time.monotonic() + bekle_sn)


HIZ = Hiz()


def hiz_kur(**kw) -> Hiz:
    """Yeni bir paylaşılan hız sınırı kurar (koşu başına; ayar.toml [indirme])."""
    global HIZ
    HIZ = Hiz(**kw)
    return HIZ


def _retry_after(r) -> float | None:
    try:
        v = float(r.headers.get("Retry-After", ""))
        return min(60.0, max(1.0, v))
    except (TypeError, ValueError):
        return None


def tek(url: str, zaman_asimi: float = 20.0) -> Yanit:
    """Tek deneme. durum: tamam · bos · yok (404) · gecici (429/5xx/ağ — yeniden denenir) · hata (kalıcı)."""
    try:
        r = _havuz().request("GET", url, timeout=urllib3.Timeout(connect=10.0, read=zaman_asimi),
                             retries=False, preload_content=True)
    except urllib3.exceptions.HTTPError as e:
        HIZ.reddedildi(ag=True)
        return Yanit("gecici", ayrinti=type(e).__name__, deneme=1)
    if r.status == 200:
        HIZ.basarili()
        return Yanit("tamam" if r.data else "bos", r.data, deneme=1)
    if r.status == 404:
        HIZ.basarili()
        return Yanit("yok", deneme=1)
    if r.status in (429, 500, 502, 503, 504):
        HIZ.reddedildi(_retry_after(r) if r.status == 429 else None)
        return Yanit("gecici", ayrinti=f"HTTP {r.status}", deneme=1)
    return Yanit("hata", ayrinti=f"HTTP {r.status}", deneme=1)


def getir(url: str, deneme: int = 6, zaman_asimi: float = 20.0, son_an: float | None = None) -> Yanit:
    """Tek dosya, sırayla (az sayıda dosya için: saatlik çapraz sınama). Geçici hatada bekleyip yineler."""
    y = Yanit("hata", ayrinti="bütçe")
    for i in range(deneme):
        if (son_an is not None and time.monotonic() > son_an) or not HIZ.bekle(son_an):
            return Yanit("hata", ayrinti=f"bütçe ({y.ayrinti})", deneme=i)
        y = tek(url, zaman_asimi)
        y.deneme = i + 1
        if y.durum != "gecici":
            return y
        time.sleep(min(20.0, 2.0 * 2 ** i))
    return Yanit("hata", ayrinti=y.ayrinti, deneme=deneme)


def toplu_getir(urller: list[str], es_zamanli: int = 8, zaman_asimi: float = 20.0, son_an: float | None = None,
                tavan_deneme: int = 8, ara_sn: float = 60.0, olcum: dict | None = None) -> dict[str, Yanit]:
    """Çok dosya, ERTELEMELİ kuyrukla.

    Geçici hata (429 · 5xx · ağ) alan dosya beklemeye alınır ve en erken `ara_sn`
    (rastgele 1–2 kat) sonra yeniden istenir; öbür dosyalar beklemeden sürer. Bekleme
    süresi dolan dosyalar arasında LİSTE SIRASI önceliklidir: listenin başındaki birimin
    ertelenen dosyası, sonraki birimin ilk denemesinden önce gelir. Böylece birimler
    sırayla tamamlanır ve bütçe dolduğunda eksik kalan dosyalar listenin SONUNDA olur
    (yalnız ilk denemeleri sıraya koyan bir kuyruk, ertelenen her dosyayı bütün ilk
    denemelerin arkasına, yani bütçenin son dakikalarına iterdi).

    Bütçe dolunca tamamlanmamış dosyalar 'hata' döner; çağıran onları bir sonraki
    koşuya bırakır. `olcum` verilirse deneme sırasına göre sonuçlar, geçici hataların
    türü ve başarılı isteklerin süresi oraya yazılır (eşik ayarı ölçülmeden yapılmaz)."""
    import heapq
    import random
    hazir = list(range(len(urller)))           # süresi dolmuş: liste sırasıyla
    heapq.heapify(hazir)
    bekleyen: list[tuple[float, int]] = []     # (en erken an, sıra)
    deneme: dict[int, int] = {}
    sonuc: dict[str, Yanit] = {}
    son_hata: dict[int, str] = {}
    kilit = threading.Lock()
    rng = random.Random(len(urller))
    if olcum is not None:
        olcum.setdefault("deneme", {})
        olcum.setdefault("gecici", {})
        olcum.setdefault("sure_tamam", [])

    def al():
        """(sıra, None) ya da (None, bekleme) ya da (None, None) = iş bitti. Kilit altında çağrılır."""
        simdi = time.monotonic()
        while bekleyen and bekleyen[0][0] <= simdi:
            heapq.heappush(hazir, heapq.heappop(bekleyen)[1])
        if hazir:
            return heapq.heappop(hazir), None
        if bekleyen:
            return None, min(1.0, bekleyen[0][0] - simdi)
        return None, None

    def isci():
        while True:
            with kilit:
                if son_an is not None and time.monotonic() > son_an:
                    return
                sira, bekle = al()
            if sira is None:
                if bekle is None:
                    return
                time.sleep(max(0.0, bekle))
                continue
            if not HIZ.bekle(son_an):
                with kilit:
                    heapq.heappush(hazir, sira)
                return
            url = urller[sira]
            t1 = time.monotonic()
            y = tek(url, zaman_asimi)
            sure = time.monotonic() - t1
            with kilit:
                n = deneme[sira] = deneme.get(sira, 0) + 1
                if olcum is not None:
                    d = olcum["deneme"].setdefault(str(n), {})
                    d[y.durum] = d.get(y.durum, 0) + 1
                    if y.durum == "gecici":
                        olcum["gecici"][y.ayrinti] = olcum["gecici"].get(y.ayrinti, 0) + 1
                    elif y.durum in ("tamam", "bos", "yok"):
                        olcum["sure_tamam"].append(round(sure, 3))
                if y.durum == "gecici" and n < tavan_deneme:
                    son_hata[sira] = y.ayrinti
                    heapq.heappush(bekleyen, (time.monotonic() + ara_sn * (1.0 + rng.random()), sira))
                else:
                    y.deneme = n
                    sonuc[url] = y if y.durum != "gecici" else Yanit("hata", ayrinti=y.ayrinti, deneme=n)

    is_parcaciklari = [threading.Thread(target=isci, daemon=True) for _ in range(max(1, es_zamanli))]
    for t in is_parcaciklari:
        t.start()
    for t in is_parcaciklari:
        t.join()
    for i, u in enumerate(urller):
        if u not in sonuc:
            neden = son_hata.get(i, "")
            sonuc[u] = Yanit("hata", ayrinti=f"bütçe ({neden})" if neden else "bütçe", deneme=deneme.get(i, 0))
    return sonuc


# ───────────────────────────────────────────────────────────── gün → satırlar
def gun_cerceve(gun: date, bid: np.ndarray, ask: np.ndarray) -> pd.DataFrame:
    """Bir günün bid ve ask kayıtlarını birleştirir; iki tarafta da hacmi sıfır olan (dolgu) dakikaları atar."""
    t0 = int(datetime(gun.year, gun.month, gun.day, tzinfo=timezone.utc).timestamp())
    b = pd.DataFrame({"s": bid["s"].astype(np.int64), "b_o": bid["o"], "b_h": bid["h"], "b_l": bid["l"],
                      "b_c": bid["c"], "b_v": bid["v"]})
    a = pd.DataFrame({"s": ask["s"].astype(np.int64), "a_o": ask["o"], "a_h": ask["h"], "a_l": ask["l"],
                      "a_c": ask["c"], "a_v": ask["v"]})
    m = b.merge(a, on="s", how="inner")
    m = m[(m["b_v"] > 0) | (m["a_v"] > 0)]
    cikti = pd.DataFrame({
        "t": t0 + m["s"].to_numpy(np.int64),
        "b_o": m["b_o"].to_numpy(np.int32), "b_h": m["b_h"].to_numpy(np.int32),
        "b_l": m["b_l"].to_numpy(np.int32), "b_c": m["b_c"].to_numpy(np.int32),
        "d_o": (m["a_o"].to_numpy(np.int64) - m["b_o"].to_numpy(np.int64)).astype(np.int32),
        "d_h": (m["a_h"].to_numpy(np.int64) - m["b_h"].to_numpy(np.int64)).astype(np.int32),
        "d_l": (m["a_l"].to_numpy(np.int64) - m["b_l"].to_numpy(np.int64)).astype(np.int32),
        "d_c": (m["a_c"].to_numpy(np.int64) - m["b_c"].to_numpy(np.int64)).astype(np.int32),
        "b_v": m["b_v"].to_numpy(np.float32), "a_v": m["a_v"].to_numpy(np.float32),
    })
    return cikti


def gunler(bas: date, bit: date) -> list[date]:
    n = (bit - bas).days
    return [bas + timedelta(days=i) for i in range(n + 1)]


def istenecek(g: date) -> bool:
    """Cumartesi istenmez: FX cuma 17:00 ET'de kapanır, pazar 17:00 ET'de açılır; UTC
    cumartesi gününün bütün dakikaları kapalı piyasadır. İlk iki koşuda 2018–2019'un
    istenen her cumartesi dosyası boş döndü (künyede `gun_bos`), yani bu bir varsayım
    değil ölçümdür; isteği atlamak kaynağın hız sınırında indirmenin yedide birini geri kazanır."""
    return g.weekday() != 5


def gun_listesi(yil: int, bas: date, bit: date, yalniz: list[date] | None = None) -> list[date]:
    """Bir parite × yıl biriminin istenecek günleri (`yalniz` verilirse yalnız onlar)."""
    ilk = max(bas, date(yil, 1, 1))
    son = min(bit, date(yil, 12, 31))
    return [g for g in (yalniz if yalniz is not None else gunler(ilk, son)) if istenecek(g)]


def yil_kur(yil: int, bas: date, bit: date, liste: list[date], yanit) -> tuple[pd.DataFrame, dict]:
    """İndirilmiş yanıtlardan birimin çerçevesi ve künyesi. `yanit(gun, taraf)` → Yanit.

    Hatayla dönen gün künyede `gun_hata`da kalır; çağıran, var olan arşivle
    birleştirip bir sonraki koşuda yalnız o günleri yeniden ister."""
    ilk = max(bas, date(yil, 1, 1))
    son = min(bit, date(yil, 12, 31))
    parcalar, dolu, bos, yok, hata, dolgu, istek, ret = [], [], [], [], [], 0, 0, 0
    for g in liste:
        yb, ya = yanit(g, "BID"), yanit(g, "ASK")
        for y in (yb, ya):
            istek += y.deneme
            ret += y.deneme - (1 if y.durum in ("tamam", "bos", "yok") else 0)
        if "hata" in (yb.durum, ya.durum):
            hata.append(f"{g.isoformat()}: BID {yb.durum} {yb.ayrinti} · ASK {ya.durum} {ya.ayrinti}".strip())
            continue
        if yb.durum == "yok" or ya.durum == "yok":
            yok.append(g.isoformat())
            continue
        try:
            kb, ka = coz(yb.ham), coz(ya.ham)
        except (CozumHatasi, lzma.LZMAError) as e:
            # Bozuk dosya: gün HATA sayılır, birim tam değildir —
            # bozuk bir günü sessizce boş saymak bir boşluğu veri gibi gösterirdi.
            hata.append(f"{g.isoformat()}: çözülemedi — {e}")
            continue
        if len(kb) == 0 or len(ka) == 0:
            bos.append(g.isoformat())
            continue
        cer = gun_cerceve(g, kb, ka)
        dolgu += min(len(kb), len(ka)) - len(cer)
        if len(cer) == 0:
            bos.append(g.isoformat())
        else:
            parcalar.append(cer)
            dolu.append(g.isoformat())
    df = pd.concat(parcalar, ignore_index=True) if parcalar else pd.DataFrame(columns=SUTUNLAR)
    df = df.sort_values("t", kind="mergesort").reset_index(drop=True)
    kunye = {
        "ilk_gun": ilk.isoformat(), "son_gun": son.isoformat(), "gun": len(liste),
        "gun_dolu": len(parcalar), "gun_bos": bos, "gun_404": yok, "gun_hata": hata,
        "dolgu_dakika": int(dolgu), "satir": int(len(df)), "tam": not hata,
        "gun_dolu_liste": dolu, "istek": int(istek), "ret": int(ret),
    }
    return df, kunye


def yil_indir(sembol: str, yil: int, bas: date, bit: date, es_zamanli: int = 8,
              zaman_asimi: float = 20.0, yalniz: list[date] | None = None, son_an: float | None = None,
              tavan_deneme: int = 8, ara_sn: float = 60.0) -> tuple[pd.DataFrame, dict]:
    """Tek birim: günleri indirir ve kurar (`arsiv_dukascopy` birden çok birimi tek kuyrukta indirir)."""
    liste = gun_listesi(yil, bas, bit, yalniz)
    urller = [dakika_url(sembol, g, t) for g in liste for t in ("BID", "ASK")]
    yan = toplu_getir(urller, es_zamanli, zaman_asimi, son_an, tavan_deneme, ara_sn)
    return yil_kur(yil, bas, bit, liste, lambda g, t: yan[dakika_url(sembol, g, t)])


# ───────────────────────────────────────────────────────────── arşiv yazımı/okuması
def yaz(df: pd.DataFrame, yol: Path) -> str:
    """Deterministik parquet; dosyanın sha256'sını döner."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    tablo = pa.Table.from_pandas(df[SUTUNLAR], schema=SEMA, preserve_index=False)
    tablo = tablo.replace_schema_metadata(None)
    gecici = yol.with_suffix(".parquet.gecici")
    pq.write_table(tablo, gecici, use_dictionary=["d_o", "d_h", "d_l", "d_c"],
                   column_encoding={"t": "DELTA_BINARY_PACKED", "b_o": "DELTA_BINARY_PACKED",
                                    "b_h": "DELTA_BINARY_PACKED", "b_l": "DELTA_BINARY_PACKED",
                                    "b_c": "DELTA_BINARY_PACKED"},
                   write_statistics=False, row_group_size=1 << 20, **SIKISTIRMA)
    gecici.replace(yol)
    return oz(yol)


def oz(yol: Path) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


class ArsivOzuHatasi(RuntimeError):
    """Arşiv dosyası künyedeki özüyle (SHA-256) aynı değil: dosya indirildikten sonra değişmiş."""


def oku_ham(dizin: Path, sembol: str, yillar: list[int] | None = None, sina: bool = True) -> pd.DataFrame:
    """Arşivden ham (nokta cinsinden) çerçeve. Her yıl dosyası okunmadan önce künyedeki SHA-256 özüne karşı
    sınanır (`sina`): indirildikten sonra değişen ya da künyesi olmayan bir dosya ölçüme giremez."""
    dosyalar = sorted((dizin / sembol).glob("*.parquet"))
    if yillar is not None:
        dosyalar = [d for d in dosyalar if int(d.stem) in set(yillar)]
    if not dosyalar:
        raise FileNotFoundError(f"{sembol}: arşiv yok ({dizin / sembol})")
    if sina:
        birimler = kunye_oku(dizin).get("birimler", {})
        for d in dosyalar:
            k = birimler.get(f"{sembol}/{d.stem}") or {}
            if not k.get("sha256"):
                raise ArsivOzuHatasi(f"{sembol}/{d.stem}: künyede öz yok")
            if oz(d) != k["sha256"]:
                raise ArsivOzuHatasi(f"{sembol}/{d.stem}: dosyanın özü künyedekiyle aynı değil")
    return pd.concat([pq.read_table(d).to_pandas() for d in dosyalar], ignore_index=True)


def fiyatla(ham: pd.DataFrame, nokta: float) -> pd.DataFrame:
    """Ham arşiv → bid/ask/mid fiyatları ve makas (fiyat birimi), UTC dizinli."""
    ix = pd.to_datetime(ham["t"].to_numpy(np.int64), unit="s", utc=True)
    out = {}
    for a in "ohlc":
        b = ham[f"b_{a}"].to_numpy(np.int64)
        k = b + ham[f"d_{a}"].to_numpy(np.int64)
        out[f"bid_{a}"] = b * nokta
        out[f"ask_{a}"] = k * nokta
        out[a] = (b + k) * (nokta / 2.0)        # mid
    out["spr_o"] = ham["d_o"].to_numpy(np.int64) * nokta
    out["spr_c"] = ham["d_c"].to_numpy(np.int64) * nokta
    out["v"] = ham["b_v"].to_numpy(np.float64) + ham["a_v"].to_numpy(np.float64)
    return pd.DataFrame(out, index=pd.DatetimeIndex(ix, name="t"))


def kunye_dosyasi(dizin: Path, anahtar: str) -> Path:
    """Birim künyesinin yolu: `kunye/<SEMBOL>_<YYYY>.json`."""
    sembol, yil = anahtar.split("/")
    return dizin / "kunye" / f"{sembol}_{yil}.json"


def kunye_oku(dizin: Path) -> dict:
    """Künye BİRİM başına bir dosyadır (`kunye/<SEMBOL>_<YYYY>.json`); okuyucu hepsini birleştirir.

    Birim başına dosya, birimleri ayrı koşucularda AYNI ANDA indirmeye izin verir: her iş
    yalnız kendi birimlerinin dosyalarına yazar, dala gönderirken çakışma doğmaz (parite
    başına tek dosya, aynı paritenin iki yılını iki koşucuya bölmeyi engelliyordu). Ortak
    alanlar (kaynak, kapsam, nokta) her dosyada durur; en son yazılan dosyanınki geçer."""
    out: dict = {"birimler": {}}
    ortak: list[tuple[str, dict]] = []
    for yol in sorted((dizin / "kunye").glob("*.json")):
        k = json.loads(yol.read_text(encoding="utf-8"))
        out["birimler"].update(k.pop("birimler", {}))
        ortak.append((str(k.pop("yazim", "")), k))
    for _, k in sorted(ortak, key=lambda x: x[0]):
        out.update(k)
    return out


def kunye_yaz(dizin: Path, kunye: dict, anahtarlar: list[str]) -> None:
    """Yalnız verilen birimlerin künye dosyalarını yazar (ortak alanlar her dosyada)."""
    ortak = {a: v for a, v in kunye.items() if a != "birimler"}
    ortak["yazim"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for a in anahtarlar:
        v = kunye.get("birimler", {}).get(a)
        if v is None:
            continue
        yol = kunye_dosyasi(dizin, a)
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps({**ortak, "birimler": {a: v}}, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
