# -*- coding: utf-8 -*-
"""Büyüme (GSYH) hattı — VERİ katmanı (EVDS3).

Seri kodları KODA GÖMÜLMEZ: her veri grubunun içeriği EVDS'in kendi
`serieList` ucundan okunur ve o listedeki seriler çekilir. Sebebi iki katlı —
uydurma bir kod hatta giremez, ve TÜİK bir seri eklerse hat onu kendiliğinden
alır. Grup kodları keşifle ölçüldü (kesif.py, 31.08.2026).

Çekilen altı grup ve NİYE gerektikleri:

  harcama_takvim        takvim arındırılmış zincirlenmiş hacim — YILLIK
                        büyümenin ve bileşen büyümelerinin doğru tabanı.
  harcama_mevsim_takvim mevsim VE takvim arındırılmış — ÇEYREKLİK değişim
                        yalnız bununla ölçülür; ötekiyle ölçmek mevsimi
                        büyüme sanmaktır.
  harcama_cari          cari fiyatlarla harcama — katkı hesabının AĞIRLIĞI
                        buradan gelir (zincirlenmiş hacim toplanamaz).
  uretim_zincir         üretim yöntemi, zincirlenmiş hacim — sektör büyümesi.
  uretim_cari           üretim yöntemi, cari — sektör ağırlıkları.
  hanehalki_dayaniklilik  hanehalkı tüketiminin dayanıklılık kırılımı; faize
                        en duyarlı kalem (dayanıklı mal) burada görünür.

Boş tabloyla BAŞARILI çıkmak yasak (ReelSektorFX dersi): bir grup hiç satır
döndürmezse hat DURUR.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

import pandas as pd

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"
KOK = PROJE.parent.parent
BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
DEMET = 6

ANAHTAR_YOLLARI = (PROJE / ".evds_key", KOK / ".evds_key",
                   KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key")

GRUPLAR: dict[str, tuple[str, str]] = {
    "harcama_takvim":       ("bie_gsyzhtaken",
                             "Harcama yöntemi · takvim arındırılmış zincirlenmiş hacim (2009=100)"),
    "harcama_mevsim_takvim": ("bie_gsyzhend",
                              "Harcama yöntemi · mevsim ve takvim arındırılmış zincirlenmiş hacim"),
    "harcama_cari":         ("bie_gsyhhrccar", "Harcama yöntemi · cari fiyatlarla"),
    "uretim_zincir":        ("bie_gsyhuretzinc", "Üretim yöntemi (A10) · zincirlenmiş hacim"),
    "uretim_cari":          ("bie_gsyhuretcar", "Üretim yöntemi (A10) · cari fiyatlarla"),
    "hanehalki_dayaniklilik": ("bie_nihaitukh",
                               "Hanehalkı tüketimi · dayanıklılık türüne göre, cari"),
}

_UYARI: list[str] = []
_A: str | None = None


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def uyarilar() -> list[str]:
    return list(_UYARI)


def _anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    for y in ANAHTAR_YOLLARI:
        if y.exists():
            a = y.read_text(encoding="utf-8").strip()
            if a:
                return a
    raise SystemExit("EVDS anahtarı yok (TTO_EVDS_KEY ya da .evds_key)")


def _cek(url: str, deneme: int = 3):
    global _A
    if _A is None:
        _A = _anahtar()
    son = None
    for _ in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"key": _A, "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            son = ex
    raise RuntimeError(f"EVDS düştü: {url[:110]} — {son}")


def _seri_listesi(grup: str) -> list[tuple[str, str]]:
    """(kod, ad) — grubun İÇİNDEKİ seriler, EVDS'in kendi listesinden."""
    d = _cek(f"{BASE}/serieList/type=json&code={grup}")
    ham = d if isinstance(d, list) else (d.get("series") or d.get("Series") or [])
    out = []
    for s in ham:
        kod = str(s.get("SERIE_CODE") or "").strip()
        ad = str(s.get("SERIE_NAME_ENG") or s.get("SERIE_NAME") or "").strip()
        if kod:
            out.append((kod, ad))
    return out


def _ayristir(items, kolonlar: list[str]) -> pd.DataFrame:
    """EVDS çeyrek satırları → çeyrek SONU tarihli tablo."""
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    if "Tarih" not in df.columns:
        return pd.DataFrame()
    t = df["Tarih"].astype(str)
    idx = pd.PeriodIndex(t.str.replace("-", "", regex=False),
                         freq="Q").to_timestamp(how="end").normalize()
    out = {k: pd.to_numeric(df[k].replace("", None), errors="coerce")
           for k in kolonlar if k in df.columns}
    if not out:
        return pd.DataFrame()
    d = pd.DataFrame(out)
    d.index = pd.Index(idx)
    return d[~d.index.isna()].sort_index()


def _grup_cek(grup: str) -> tuple[pd.DataFrame, dict[str, str]]:
    seriler = _seri_listesi(grup)
    if not seriler:
        raise SystemExit(f"{grup}: serieList boş döndü — hat duruyor")
    kodlar = [k for k, _ in seriler]
    adlar = {k.replace(".", "_"): a for k, a in seriler}
    parcalar = []
    for i in range(0, len(kodlar), DEMET):
        demet = kodlar[i:i + DEMET]
        guvenli = [k.replace(".", "_") for k in demet]
        url = (f"{BASE}/series={'-'.join(demet)}"
               f"&startDate=01-01-1995&endDate=31-12-2030&type=json")
        try:
            p = _ayristir(_cek(url).get("items", []), guvenli)
        except Exception as ex:
            uyar(f"{grup}: demet düştü ({', '.join(demet)}) — {ex}; tek tek deneniyor")
            p = pd.DataFrame()
            for k in demet:
                try:
                    tek = _ayristir(_cek(
                        f"{BASE}/series={k}&startDate=01-01-1995"
                        f"&endDate=31-12-2030&type=json").get("items", []),
                        [k.replace(".", "_")])
                    p = tek if p.empty else p.join(tek, how="outer")
                except Exception as ex2:
                    uyar(f"{grup}: seri alınamadı {k} — {ex2}")
        if not p.empty:
            parcalar.append(p)
    if not parcalar:
        raise SystemExit(f"{grup}: hiçbir seri gelmedi — hat duruyor")
    tablo = parcalar[0]
    for p in parcalar[1:]:
        tablo = tablo.join(p, how="outer")
    return tablo.sort_index(), adlar


def main() -> int:
    DATA.mkdir(exist_ok=True)
    print("── Büyüme hattı · EVDS çekimi", flush=True)
    kunye: dict = {"gruplar": {}}
    for ad, (grup, baslik) in GRUPLAR.items():
        print(f"\n  {ad}  ({grup})")
        tablo, adlar = _grup_cek(grup)
        dolu = tablo.dropna(how="all")
        if dolu.empty:
            raise SystemExit(f"{ad}: tablo tamamen boş — hat duruyor")
        yol = DATA / f"{ad}.csv"
        tablo.to_csv(yol, encoding="utf-8")
        son = dolu.index.max()
        print(f"    {tablo.shape[1]} seri · {len(dolu)} dolu çeyrek · "
              f"son {son:%Y-%m-%d} ({son.to_period('Q')})")
        kunye["gruplar"][ad] = {
            "evds_grup": grup, "baslik": baslik,
            "seri_sayisi": int(tablo.shape[1]),
            "son_ceyrek": str(son.to_period("Q")),
            "adlar": adlar,
        }
    kunye["uyarilar"] = uyarilar()
    (DATA / "kunye.json").write_text(
        json.dumps(kunye, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n── veri yazıldı: {DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
