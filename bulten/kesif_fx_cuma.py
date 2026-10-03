#!/usr/bin/env python3
"""DÖVİZ CUMASI — `gunluk_duzelt`in CUMA değeri gerçekten cuma kapanışı mı?
Ölçüm, hüküm değil.

NEDEN. `ortak/fx_kapanis.gunluk_duzelt` saatlik barın ulaşmadığı eski geçmişi
Yahoo günlük barından kurar: kapanmış bir barın "Close" alanı o günün BAŞINDAKİ
(Londra gece yarısı) fiyattır, değer bardan önceki son hafta içi güne yazılır.
Cumartesi barı varsa cuma ondan gelir (başı cuma gecesi); YOKSA cumaya yazılan
tek bar PAZARTESİ barıdır ve onun başı pazartesi 00:00 Londra — pazar akşamki
hafta sonu açılışından SONRA. Bülten anlık görüntüsünde 51 sembolün 49'unda hiç
hafta sonu barı yok. Yani cuma değeri hafta sonu boşluğunu taşıyor olabilir;
OAT–Bund analizinde kaydırılmış seride ölçülen kaymanın üretimdeki eşi
(CLAUDE.md: "BİR DÖVİZ BARININ TARİHİ, KAPANIŞIN TARİHİ DEĞİLDİR"). Sezgi
ölçülmeden koda girmez; bu betik o ölçümü üretir.

NE ÖLÇER. Saatlik barın da günlük barın da bulunduğu örtüşme penceresinde
(üretimin `730d` saatlik çağrısı 18.12.2023'e iner), on beş sembolde:
  [1] hafta sonu barı: günlük geçmişte kaç cumartesi/pazar barı var (yıla göre)
      ve bülten çağrısında (`period="1y"`, çoklu sembol) kaç tane
  [2] her hafta içi gün için `gunluk_duzelt` değeri ile
        · saatlik kapanış (`saatlik_kapanislar`: İstanbul 18:00 · New York 17:00)
        · saatlik bardan Londra gece yarısı (gunluk_duzelt'in İLAN ETTİĞİ tanım)
      arasındaki fark (bp); cuma, cumartesi barı olan / pazar barı olan / hiç
      hafta sonu barı olmayan diye ayrı, pazartesi–perşembe taban olarak
  [3] mekanizma: barsız cumanın değeri pazartesi 00:00 Londra fiyatına (saatlik
      bardan) mı eşit, hafta sonu boşluğu ne kadar
  [4] aday kaynak: Yahoo HAFTALIK barının kapanışı gerçek cuma kapanışı mı
      (yoksa o da günün başını mı taşıyor)
  [5] etki: saatlik pencereden ESKİ geçmişte kaç cuma pazartesi barından geliyor

Yalnız bulutta, `veri.yml`in `kesif` girdisiyle koşar (bu oturumlardan Yahoo'ya
çıkılamıyor). Depoya YAZMAZ; cuma satırları `CUMA;` önekiyle, özet en sonda
`OZET_JSON ` önekiyle basılır ki arşive alınabilsin.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import fx_kapanis as F  # noqa: E402

# Bültenin on iki döviz sembolü + OAT–Bund analizinin üç G10 çaprazı.
SEMBOLLER = ["USDTRY=X", "EURTRY=X", "GBPTRY=X", "EURUSD=X", "USDJPY=X", "GBPUSD=X",
             "USDCHF=X", "AUDUSD=X", "NZDUSD=X", "USDCAD=X", "USDSEK=X", "USDNOK=X",
             "EURGBP=X", "EURCHF=X", "EURJPY=X"]
GUNLUK_BAS = "2005-01-01"          # ortak/usdtry.py'nin başlangıcı
# 429 bir ölçüm değildir: yeniden denenir (kesif_usdtry_haftasonu ile aynı pay).
BEKLEME = (0, 10, 30, 60)
LONDRA = "Europe/London"


def _dene(ad: str, fn):
    son = None
    for i, bekle in enumerate(BEKLEME, start=1):
        if bekle:
            print(f"    {bekle} sn bekleniyor ({ad}, deneme {i})…")
            time.sleep(bekle)
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            son = e
            print(f"  {ad} düştü (deneme {i}): {type(e).__name__}: {str(e)[:150]}")
    print(f"  ! {ad} ÖLÇÜLEMEDİ: {son!r}"[:200])
    return None


def _kapanis(ham: pd.DataFrame, sembol: str | None = None) -> pd.Series:
    """yfinance çerçevesinden 'Close' — tek ya da çok sembol, iki MultiIndex düzeni."""
    if isinstance(ham.columns, pd.MultiIndex):
        if sembol is not None and sembol in ham.columns.get_level_values(0):
            c = ham[sembol]["Close"]
        elif "Close" in ham.columns.get_level_values(0):
            c = ham["Close"]
            c = c[sembol] if (sembol is not None and isinstance(c, pd.DataFrame) and sembol in c.columns) \
                else (c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c)
        else:
            c = ham.xs("Close", axis=1, level=-1)
            c = c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
    else:
        c = ham["Close"]
    return pd.to_numeric(c, errors="coerce")


def _londra_gunu(s: pd.Series) -> pd.Series:
    """Günlük/haftalık barın günü Londra günüdür (ortak/usdtry._seri_temizle ile aynı kural)."""
    idx = pd.DatetimeIndex(pd.to_datetime(s.index))
    if idx.tz is not None:
        idx = idx.tz_convert(LONDRA).tz_localize(None)
    r = pd.Series(s.values, index=idx.normalize(), dtype="float64").dropna()
    return r[~r.index.duplicated(keep="last")].sort_index()


def gunluk_cek(sembol: str, aralik: str = "1d") -> pd.Series | None:
    """ortak/usdtry.py'nin çağrı biçimi (tek sembol, auto_adjust=False)."""
    import yfinance as yf
    bit = (dt.date.today() + dt.timedelta(days=1)).isoformat()

    def _cek():
        ham = yf.download(sembol, start=GUNLUK_BAS, end=bit, interval=aralik, progress=False,
                          auto_adjust=False, threads=False)
        if ham is None or len(ham) == 0:
            raise RuntimeError("boş çerçeve")
        return _londra_gunu(_kapanis(ham, sembol))
    return _dene(f"{sembol} {aralik}", _cek)


def bulten_cagrisi() -> dict:
    """Bültenin piyasa çağrısı (çoklu sembol, period=1y): sembol başına hafta sonu barı."""
    import yfinance as yf

    def _cek():
        ham = yf.download(SEMBOLLER, period="1y", interval="1d", progress=False, auto_adjust=False,
                          group_by="ticker", threads=True)
        if ham is None or len(ham) == 0:
            raise RuntimeError("boş çerçeve")
        out = {}
        for k in SEMBOLLER:
            try:
                s = _londra_gunu(_kapanis(ham, k))
            except Exception:  # noqa: BLE001
                continue
            out[k] = {"bar": int(len(s)), "cumartesi": int((s.index.dayofweek == 5).sum()),
                      "pazar": int((s.index.dayofweek == 6).sum())}
        return out
    return _dene("bülten çağrısı 1y", _cek) or {}


def saatlik_acilis() -> dict:
    """Saatlik barların AÇILIŞI (üretimin çağrısıyla aynı parametreler). Pazartesi
    00:00 Londra fiyatı içindir: Yahoo'nun saatlik döviz haftası o anda başlar
    (yerel arşivde ölçüldü: cuma 21:00 UTC barından sonraki ilk bar pazar 23:00
    UTC = pazartesi 00:00 BST), yani o anın fiyatı ilk barın açılışıdır."""
    import yfinance as yf

    def _cek():
        ham = yf.download(SEMBOLLER, period="730d", interval="60m", progress=False, auto_adjust=False,
                          group_by="ticker", threads=False)
        if ham is None or len(ham) == 0:
            raise RuntimeError("boş çerçeve")
        out = {}
        for k in SEMBOLLER:
            try:
                c = (ham[k]["Open"] if isinstance(ham.columns, pd.MultiIndex) else ham["Open"]).dropna()
            except Exception:  # noqa: BLE001
                continue
            idx = pd.DatetimeIndex(c.index)
            c.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
            out[k] = pd.to_numeric(c, errors="coerce").dropna().sort_index()
        return out
    return _dene("saatlik açılış 730d", _cek) or {}


def _pazartesi_acilisi(acilis: pd.Series | None, cuma: dt.date) -> float:
    """Cumadan sonraki pazartesi 00:00 Londra'da BAŞLAYAN ilk saatlik barın açılışı
    (en çok altı saat içinde; yoksa ölçülemez)."""
    if acilis is None or not len(acilis):
        return float("nan")
    bas = pd.Timestamp(dt.datetime.combine(cuma + dt.timedelta(days=3), dt.time(0)),
                       tz=LONDRA).tz_convert("UTC")
    o = acilis[(acilis.index >= bas) & (acilis.index < bas + pd.Timedelta(hours=6))]
    return float(o.iloc[0]) if len(o) else float("nan")


def _kapanis_ani_serisi(saatlik: pd.Series) -> pd.Series:
    """Saatlik bar kapanışları, barın KAPANIŞ anıyla (başlangıç + 1 saat), UTC."""
    s = pd.to_numeric(saatlik, errors="coerce").dropna()
    idx = pd.DatetimeIndex(s.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    s = pd.Series(s.values, index=idx + pd.Timedelta(hours=1), dtype="float64")
    return s[~s.index.duplicated(keep="last")].sort_index()


def _londra_gece(s: pd.Series, gun: dt.date) -> float:
    """`gun`ün Londra gece yarısı kapanışı: (gun+1) 00:00 Londra'da ya da ondan önce
    kapanan son saatlik bar (24 saat içinde) — gunluk_duzelt'in ilan ettiği tanım."""
    kes = pd.Timestamp(dt.datetime.combine(gun + dt.timedelta(days=1), dt.time(0)),
                       tz=LONDRA).tz_convert("UTC")
    o = s[(s.index <= kes) & (s.index > kes - pd.Timedelta(hours=24))]
    return float(o.iloc[-1]) if len(o) else float("nan")


def ozet(x) -> dict:
    a = np.abs(np.asarray([v for v in x if v == v], dtype="float64"))
    if not len(a):
        return {"n": 0}
    return {"n": int(len(a)), "medyan": round(float(np.median(a)), 2),
            "p90": round(float(np.quantile(a, 0.9)), 2), "azami": round(float(a.max()), 2),
            "ortalama": round(float(a.mean()), 2)}


def _bp(a: float, b: float) -> float:
    return (a / b - 1.0) * 1e4 if (a == a and b == b and b) else float("nan")


KATEGORI = ("cuma_cumartesi_bari", "cuma_pazar_bari", "cuma_hafta_sonu_barsiz", "pzt_prs")


def sembol_olc(k: str, saatlik: pd.Series, gunluk: pd.Series, haftalik: pd.Series | None,
               simdi: dt.datetime, acilis: pd.Series | None = None) -> dict:
    tur = F.kesim_turu(k)
    bugun_londra = pd.Timestamp(simdi).tz_convert(LONDRA).date()
    g = gunluk[gunluk.index.date < bugun_londra]          # bugünün barı canlı
    duz = F.gunluk_duzelt(g)
    kp = F.saatlik_kapanislar(saatlik, tur, simdi)
    s = _kapanis_ani_serisi(saatlik)
    gunler = set(g.index)
    out: dict = {"tur": tur, "gunluk_bar": int(len(g)),
                 "gunluk_ilk": str(g.index[0].date()) if len(g) else None,
                 "cumartesi_bar": int((g.index.dayofweek == 5).sum()),
                 "pazar_bar": int((g.index.dayofweek == 6).sum())}
    hs = g[g.index.dayofweek >= 5]
    out["hafta_sonu_yila_gore"] = {str(y): int(n) for y, n in hs.groupby(hs.index.year).size().items()}
    if not len(kp.seri):
        out["hata"] = "saatlik kapanış kurulamadı"
        return out
    ilk = kp.seri.index[0]
    out["saatlik_ilk"] = str(ilk.date())

    # [5] ETKİ — saatlik pencereden eski geçmişte cumanın kaynağı
    eski = duz[duz.index < ilk]
    cuma_eski = eski[eski.index.dayofweek == 4]
    kaynak = {"cumartesi": 0, "pazar": 0, "pazartesi_ya_da_sonrasi": 0}
    for t in cuma_eski.index:
        if (t + pd.Timedelta(days=1)) in gunler:
            kaynak["cumartesi"] += 1
        elif (t + pd.Timedelta(days=2)) in gunler:
            kaynak["pazar"] += 1
        else:
            kaynak["pazartesi_ya_da_sonrasi"] += 1
    out["eski_gecmis"] = {"gun": int(len(eski)), "cuma": int(len(cuma_eski)), "cuma_kaynagi": kaynak,
                          "ilk": str(eski.index[0].date()) if len(eski) else None,
                          "son": str(eski.index[-1].date()) if len(eski) else None}

    # [2]–[3] ÖRTÜŞME — ilk saatlik gün kısmi olabilir, bir gün sonrasından başlanır
    ortak = duz.index.intersection(kp.seri.index)
    ortak = ortak[ortak > ilk]
    kat: dict[str, dict[str, list]] = {a: {"saat": [], "londra": [], "pzt00": [], "bosluk": []}
                                       for a in KATEGORI}
    satirlar = []
    for t in ortak:
        gun = t.date()
        if t.dayofweek == 4:
            if (t + pd.Timedelta(days=1)) in gunler:
                ad = "cuma_cumartesi_bari"
            elif (t + pd.Timedelta(days=2)) in gunler:
                ad = "cuma_pazar_bari"
            else:
                ad = "cuma_hafta_sonu_barsiz"
        else:
            ad = "pzt_prs"
        d, h, lm = float(duz[t]), float(kp.seri[t]), _londra_gece(s, gun)
        r = kat[ad]
        r["saat"].append(_bp(d, h))
        r["londra"].append(_bp(d, lm))
        if t.dayofweek == 4:
            # Pazartesi 00:00 Londra fiyatı (haftanın ilk saatlik barının açılışı):
            # barsız cumanın değeri buna mı eşit, cuma kapanışından ne kadar uzak?
            p00 = _pazartesi_acilisi(acilis, gun)
            r["pzt00"].append(_bp(d, p00))
            r["bosluk"].append(_bp(p00, lm))
            satirlar.append(f"CUMA;{k};{gun};{ad};{d:.6g};{h:.6g};{lm:.6g};{p00:.6g};"
                            f"{_bp(d, h):.2f};{_bp(d, lm):.2f};{_bp(d, p00):.2f};{_bp(p00, lm):.2f}")
    out["ortusme"] = {"ilk": str(ortak[0].date()) if len(ortak) else None,
                      "son": str(ortak[-1].date()) if len(ortak) else None,
                      "kategori": {a: {"saatlik_kapanisa_karsi_bp": ozet(v["saat"]),
                                       "londra_gece_yarisina_karsi_bp": ozet(v["londra"]),
                                       **({"pazartesi_0000_londraya_karsi_bp": ozet(v["pzt00"]),
                                           "hafta_sonu_boslugu_bp": ozet(v["bosluk"])}
                                          if a.startswith("cuma") else {})}
                                   for a, v in kat.items()}}
    out["_ham"] = {a: {c: [round(x, 3) for x in v[c]] for c in ("saat", "londra", "pzt00", "bosluk")}
                   for a, v in kat.items()}

    # [4] HAFTALIK BAR — gerçek cuma kapanışı mı?
    if haftalik is not None and len(haftalik):
        bu_pzt = pd.Timestamp(bugun_londra) - pd.Timedelta(days=pd.Timestamp(bugun_londra).dayofweek)
        w = haftalik[(haftalik.index < bu_pzt) & (haftalik.index >= ilk)]
        out["haftalik_gun_dagilimi"] = {str(d): int(n) for d, n in
                                        pd.Series(haftalik.index.dayofweek).value_counts().items()}
        hk: dict[str, list] = {"saat": [], "londra": [], "cuma_gunluk_bar": [], "pazartesi_bari": [],
                               "persembe_kapanis": []}
        for m, wv in w.items():
            # Haftanın cuması: etiket pazartesiyse +4, pazarsa +5 gün (etiket günü ölçülüp yazılır).
            f = m + pd.Timedelta(days=(4 - m.dayofweek) % 7)
            if f not in kp.seri.index:
                continue
            wv = float(wv)
            lm = _londra_gece(s, f.date())
            pzt = f + pd.Timedelta(days=3)
            prs = f - pd.Timedelta(days=1)
            vals = {"saat": _bp(wv, float(kp.seri[f])), "londra": _bp(wv, lm),
                    "cuma_gunluk_bar": _bp(wv, float(g[f])) if f in g.index else float("nan"),
                    "pazartesi_bari": _bp(wv, float(g[pzt])) if pzt in g.index else float("nan"),
                    "persembe_kapanis": _bp(wv, float(kp.seri[prs])) if prs in kp.seri.index else float("nan")}
            for a, v in vals.items():
                hk[a].append(v)
        out["haftalik_kapanis_kime_esit_bp"] = {a: ozet(v) for a, v in hk.items()}
    out["_satirlar"] = satirlar
    return out


def main() -> int:
    t0 = time.time()
    simdi = dt.datetime.now(dt.timezone.utc)
    print("=" * 72)
    print(f"Döviz cuması keşfi · {simdi:%Y-%m-%d %H:%M} UTC · {len(SEMBOLLER)} sembol")
    print("=" * 72)
    try:
        import yfinance as yf
        print(f"yfinance {yf.__version__} · pandas {pd.__version__}")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"ENGEL · yfinance yok: {e}")

    print("\n[0] saatlik bar (üretimin çağrısı: fx_kapanis.yfinance_saatlik, 730d)…", flush=True)
    saatlik = _dene("saatlik 730d", lambda: F.yfinance_saatlik(SEMBOLLER, donem="730d")) or {}
    print("  " + ", ".join(f"{k} {len(v)}" for k, v in saatlik.items()))
    if not saatlik:
        raise SystemExit("ENGEL · saatlik bar alınamadı — örtüşme ölçülemez")
    time.sleep(2)
    print("\n[0b] saatlik barın AÇILIŞI (pazartesi 00:00 Londra fiyatı için)…", flush=True)
    acilis = saatlik_acilis()
    print("  " + (", ".join(f"{k} {len(v)}" for k, v in acilis.items()) or "ÖLÇÜLEMEDİ"))

    print("\n[1b] bülten çağrısı (period=1y, çoklu sembol) — hafta sonu barı:", flush=True)
    bulten = bulten_cagrisi()
    for k, v in bulten.items():
        print(f"  {k:9s} bar {v['bar']} · cumartesi {v['cumartesi']} · pazar {v['pazar']}")

    sonuc: dict = {"olcum_utc": simdi.isoformat(timespec="seconds"), "yfinance": yf.__version__,
                   "bulten_cagrisi_1y": bulten, "semboller": {}}
    satirlar: list[str] = []
    for k in SEMBOLLER:
        print(f"\n── {k}", flush=True)
        h = saatlik.get(k)
        if h is None or not len(h):
            print("  saatlik bar YOK — atlandı")
            sonuc["semboller"][k] = {"hata": "saatlik bar yok"}
            continue
        g = gunluk_cek(k, "1d")
        time.sleep(1)
        w = gunluk_cek(k, "1wk")
        time.sleep(1)
        if g is None or not len(g):
            sonuc["semboller"][k] = {"hata": "günlük bar yok"}
            continue
        r = sembol_olc(k, h, g, w, simdi, acilis.get(k))
        satirlar += r.pop("_satirlar", [])
        sonuc["semboller"][k] = r
        print(f"  günlük {r['gunluk_bar']} bar ({r.get('gunluk_ilk')} →) · cumartesi {r['cumartesi_bar']} · "
              f"pazar {r['pazar_bar']} · saatlik ilk {r.get('saatlik_ilk')}")
        if r.get("hafta_sonu_yila_gore"):
            print(f"  hafta sonu barı yıla göre: {r['hafta_sonu_yila_gore']}")
        for a, v in (r.get("ortusme", {}).get("kategori") or {}).items():
            print(f"  {a:24s} saatlik {v['saatlik_kapanisa_karsi_bp']} · Londra {v['londra_gece_yarisina_karsi_bp']}")
            if "pazartesi_0000_londraya_karsi_bp" in v:
                print(f"  {'':24s} pzt 00:00 {v['pazartesi_0000_londraya_karsi_bp']} · "
                      f"boşluk {v['hafta_sonu_boslugu_bp']}")
        if r.get("haftalik_kapanis_kime_esit_bp"):
            print(f"  haftalık bar günleri {r.get('haftalik_gun_dagilimi')}")
            for a, v in r["haftalik_kapanis_kime_esit_bp"].items():
                print(f"    haftalık kapanış − {a:18s} {v}")
        print(f"  eski geçmiş: {r.get('eski_gecmis')}")

    # HAVUZ — G10 (lira içermeyen) · TRY · USD/TRY tek başına
    havuz: dict = {}
    for grup, uye in (("g10", [k for k in SEMBOLLER if "TRY" not in k]),
                      ("try", [k for k in SEMBOLLER if "TRY" in k]), ("usdtry", ["USDTRY=X"])):
        for a in KATEGORI:
            for c, ad in (("saat", "saatlik_kapanisa_karsi_bp"), ("londra", "londra_gece_yarisina_karsi_bp"),
                          ("pzt00", "pazartesi_0000_londraya_karsi_bp"), ("bosluk", "hafta_sonu_boslugu_bp")):
                x = [v for k in uye for v in ((sonuc["semboller"].get(k) or {}).get("_ham", {}).get(a, {}).get(c) or [])]
                if x or c in ("saat", "londra"):
                    havuz.setdefault(grup, {}).setdefault(a, {})[ad] = ozet(x)
    for k in SEMBOLLER:
        (sonuc["semboller"].get(k) or {}).pop("_ham", None)
    sonuc["havuz"] = havuz
    sonuc["sure_sn"] = round(time.time() - t0, 1)

    print("\n" + "=" * 72)
    print("SATIRLAR (CUMA: sembol;gün;kategori;duz;saatlik;londra;pzt00;bp_saat;bp_londra;bp_pzt00;bp_bosluk)")
    for s in satirlar:
        print(s)
    print("\nHAVUZ:")
    for grup, v in havuz.items():
        for a, w in v.items():
            print(f"  {grup:6s} {a:24s} {w}")
    print("\nOZET_JSON " + json.dumps(sonuc, ensure_ascii=False, separators=(",", ":"), default=str))
    print(f"\nsüre {sonuc['sure_sn']} sn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
