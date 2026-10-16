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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

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
_yerel = threading.local()


def _oturum() -> requests.Session:
    if not hasattr(_yerel, "s"):
        s = requests.Session()
        s.headers.update(BASLIK)
        _yerel.s = s
    return _yerel.s


@dataclass
class Yanit:
    durum: str          # "tamam" · "bos" · "yok" (404) · "hata"
    ham: bytes = b""
    ayrinti: str = ""


def getir(url: str, deneme: int = 5, zaman_asimi: float = 30.0) -> Yanit:
    """Tek dosya; 429/5xx ve ağ hatasında üstel bekleyişle yeniden dener."""
    son = ""
    for i in range(deneme):
        try:
            r = _oturum().get(url, timeout=zaman_asimi)
            if r.status_code == 200:
                return Yanit("tamam" if r.content else "bos", r.content)
            if r.status_code == 404:
                return Yanit("yok")
            son = f"HTTP {r.status_code}"
            if r.status_code not in (429, 500, 502, 503, 504):
                return Yanit("hata", ayrinti=son)
        except requests.RequestException as e:
            son = f"{type(e).__name__}: {e}"[:200]
        time.sleep(min(30.0, 0.75 * 2 ** i))
    return Yanit("hata", ayrinti=son)


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


def yil_indir(sembol: str, yil: int, bas: date, bit: date, es_zamanli: int = 8,
              deneme: int = 5, zaman_asimi: float = 30.0) -> tuple[pd.DataFrame, dict]:
    """Bir parite × yıl birimini indirir. Birim ATOMİKtir: tek bir gün bile
    hatayla dönerse çerçeve döner ama künye `tam=False` der ve arşive yazılmaz."""
    ilk = max(bas, date(yil, 1, 1))
    son = min(bit, date(yil, 12, 31))
    liste = gunler(ilk, son)
    isler = [(g, t) for g in liste for t in ("BID", "ASK")]
    with ThreadPoolExecutor(max_workers=es_zamanli) as h:
        yanitlar = list(h.map(lambda gt: getir(dakika_url(sembol, gt[0], gt[1]), deneme, zaman_asimi), isler))
    sonuc = dict(zip(isler, yanitlar))
    parcalar, bos, yok, hata, dolgu = [], [], [], [], 0
    for g in liste:
        yb, ya = sonuc[(g, "BID")], sonuc[(g, "ASK")]
        if "hata" in (yb.durum, ya.durum):
            hata.append(f"{g.isoformat()}: BID {yb.durum} {yb.ayrinti} · ASK {ya.durum} {ya.ayrinti}".strip())
            continue
        if yb.durum == "yok" or ya.durum == "yok":
            yok.append(g.isoformat())
            continue
        try:
            kb, ka = coz(yb.ham), coz(ya.ham)
        except (CozumHatasi, lzma.LZMAError) as e:
            # Bozuk dosya: gün HATA sayılır, birim tam değildir ve yazılmaz —
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
    df = pd.concat(parcalar, ignore_index=True) if parcalar else pd.DataFrame(columns=SUTUNLAR)
    df = df.sort_values("t", kind="mergesort").reset_index(drop=True)
    kunye = {
        "ilk_gun": ilk.isoformat(), "son_gun": son.isoformat(), "gun": len(liste),
        "gun_dolu": len(parcalar), "gun_bos": bos, "gun_404": yok, "gun_hata": hata,
        "dolgu_dakika": int(dolgu), "satir": int(len(df)), "tam": not hata,
    }
    return df, kunye


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


def oku_ham(dizin: Path, sembol: str, yillar: list[int] | None = None) -> pd.DataFrame:
    """Arşivden ham (nokta cinsinden) çerçeve."""
    dosyalar = sorted((dizin / sembol).glob("*.parquet"))
    if yillar is not None:
        dosyalar = [d for d in dosyalar if int(d.stem) in set(yillar)]
    if not dosyalar:
        raise FileNotFoundError(f"{sembol}: arşiv yok ({dizin / sembol})")
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


def kunye_oku(dizin: Path) -> dict:
    yol = dizin / "kunye.json"
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else {}


def kunye_yaz(dizin: Path, kunye: dict) -> None:
    dizin.mkdir(parents=True, exist_ok=True)
    (dizin / "kunye.json").write_text(json.dumps(kunye, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
