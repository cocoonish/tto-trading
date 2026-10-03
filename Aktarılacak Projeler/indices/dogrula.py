"""FX haber endeksi — kalibrasyonun YAYIN KAPISI (sayfa sınavı 26 koşturur).

Ne sorar: yayımlanan parametre dosyası, karne, donmuş girdi, özet ve Şekil 09
AYNI kalibrasyonu mu anlatıyor; kural (correlation_optimizer başlığı, karar
03.10.2026) karnenin kendi sayılarına uygulandığında aynı hükmü mü veriyor.

Neden ayrı bir kapı: kalibrasyon elle ve seyrek koşar, sayfa ise her gün yeniden
derlenir. Parametre dosyası elle düzeltilirse, karne başka bir koşudan kalırsa ya
da özet eski karneden üretilmişse hiçbir veri koşusu bunu sormaz — sayfa bir
kalibrasyonun hükmünü, canlı endeks bir başkasının parametresini taşır.

YALNIZ STANDART KÜTÜPHANE: yayın koşucusunda pandas/numpy/scipy yok (21.09.2026
ilk yayın koşusu tam bu yüzden düştü). Kuralı yeniden HESAPLAMAZ — ölçüm ağır
ve ağa bağlı; karnenin yazdığı sayılara kuralı uygular, yani kuralın kendisini
sınar, ölçüyü değil. Ölçünün yeniden üretimi ayrı kapıdır
(`correlation_optimizer.py --arsivden`, kalibrasyon koşusunun parçası).
Ağa çıkmaz, duvar saati okumaz.
"""

from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.normpath(os.path.join(BURASI, "..", ".."))
sys.path.insert(0, BURASI)

import config                      # noqa: E402  (yalnız os içe aktarır)
import kalibrasyon_damga as kd     # noqa: E402

DATA = os.path.join(BURASI, "data")
SITE = os.path.join(KOK, "site", "public", "projeler", "fx-haber-endeksi")
AD_TR = {"EURUSD": "EUR/USD", "USDJPY": "USD/JPY", "USDCHF": "USD/CHF", "GBPUSD": "GBP/USD",
         "AUDUSD": "AUD/USD", "NZDUSD": "NZD/USD", "USDCAD": "USD/CAD", "USDNOK": "USD/NOK",
         "USDSEK": "USD/SEK", "XAUUSD": "altın", "XAGUSD": "gümüş", "SPX": "S&P 500",
         "UST2Y": "ABD 2Y", "UST10Y": "ABD 10Y", "BIST100": "BIST 100"}

hatalar: list[str] = []
sayac = 0


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    global sayac
    sayac += 1
    if not kosul:
        hatalar.append(f"{ad}{' — ' + ayrinti if ayrinti else ''}")


def _json(yol: str):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def _oz(yol: str) -> str:
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def izgara() -> list[dict]:
    """correlation_optimizer.izgara'nın eşi — sıra config.PARAM_GRID'in sırasıdır."""
    anahtar = [k for k in config.PARAM_GRID if k != "lag_days"]
    out = []
    for c in itertools.product(*(config.PARAM_GRID[k] for k in anahtar)):
        p = dict(config.DEFAULT_PARAMS)
        p.update(dict(zip(anahtar, c)))
        p["lag_days"] = 0
        out.append(p)
    return out


def beklenen_hukum(il: dict | None, aile_p, esik: float) -> str:
    """KURAL — correlation_optimizer.kalibre_et'teki dalın birebir eşi."""
    if not il:
        return "ölçülemedi"
    if (aile_p is not None and aile_p <= esik and il.get("oos") is not None
            and il.get("fiyat_rakibi") is not None
            and il["oos"] > 0 and il["oos"] > il["fiyat_rakibi"]):
        return "öngörüyor"
    return "öngörmüyor"


def tarih_kisa(iso) -> str:
    return ".".join(reversed(str(iso)[:10].split("-"))) if iso else "—"


def main() -> int:
    yol_karne = os.path.join(DATA, "kalibrasyon_karne.json")
    yol_par = os.path.join(DATA, "optimized_params.json")
    try:
        karne, par = _json(yol_karne), _json(yol_par)
    except (OSError, ValueError) as e:
        print(f"✗ FX kalibrasyon kapısı: karne ya da parametre dosyası okunamadı ({e})")
        return 1

    yon = karne.get("yontem") or {}
    h0 = str((yon.get("ufuklar") or [None])[0])
    esik = yon.get("esik_p")
    aile = (karne.get("aile") or {}).get(h0) or {}
    varlik = karne.get("varlik") or {}
    grid = izgara()

    # 1 — kapsam ve yöntem
    sina("karne her varlığı taşır", set(varlik) == set(config.ASSETS),
         f"eksik {sorted(set(config.ASSETS) - set(varlik))} · fazla {sorted(set(varlik) - set(config.ASSETS))}")
    sina("parametre dosyası her varlığı taşır", set(par) == set(config.ASSETS),
         f"eksik {sorted(set(config.ASSETS) - set(par))}")
    sina("ızgara boyu karnedeki ile aynı", yon.get("izgara") == len(grid),
         f"karne {yon.get('izgara')} · config {len(grid)}")
    sina("birincil ufuk 5 gün", h0 == "5", h0)
    sina("eşik 0,05", esik == 0.05, str(esik))

    # 2 — donmuş girdi: karnenin künyesindeki öz
    g = karne.get("girdi") or {}
    for alan, oz_alan in (("arsiv", "arsiv_oz"), ("fiyat", "fiyat_oz")):
        ad = g.get(alan)
        yol = os.path.join(DATA, ad) if ad else None
        if not yol or not os.path.exists(yol):
            sina(f"donmuş girdi ({alan}) depoda", False, str(ad))
            continue
        sina(f"donmuş girdi ({alan}) özü karneyle aynı", _oz(yol) == g.get(oz_alan),
             f"{_oz(yol)[:12]} ≠ {str(g.get(oz_alan))[:12]}")
        try:
            with gzip.open(yol, "rt", encoding="utf-8") as f:
                icerik = json.load(f)
            sina(f"donmuş girdi ({alan}) her varlığı taşır", set(icerik) >= set(config.ASSETS),
                 f"eksik {sorted(set(config.ASSETS) - set(icerik))}")
        except (OSError, ValueError) as e:
            sina(f"donmuş girdi ({alan}) açılır", False, str(e))

    # 3 — kural, karnenin kendi sayılarına uygulanır
    for a in config.ASSETS:
        kv = varlik.get(a) or {}
        il = (kv.get("ileri") or {}).get(h0)
        bek = beklenen_hukum(il, aile.get("p"), esik if esik is not None else -1)
        sina(f"{a}: karnedeki hüküm kuraldan", kv.get("hukum") == bek, f"{kv.get('hukum')} ≠ {bek}")
        pv = par.get(a) or {}
        sina(f"{a}: parametre dosyasındaki hüküm karneyle aynı", pv.get("hukum") == bek,
             f"{pv.get('hukum')} ≠ {bek}")
        sina(f"{a}: kaynak hükümle tutarlı",
             pv.get("kaynak") == ("kalibrasyon" if bek == "öngörüyor" else "varsayılan"), str(pv.get("kaynak")))
        sina(f"{a}: ufuk birincil", str(pv.get("ufuk")) == h0, str(pv.get("ufuk")))
        if bek == "öngörüyor":
            s = il.get("kalibre_sira")
            ok = isinstance(s, int) and 0 <= s < len(grid)
            sina(f"{a}: kalibre sıra ızgarada", ok, str(s))
            if ok:
                sina(f"{a}: parametre ızgaranın {s}. seti", pv.get("params") == grid[s],
                     f"{pv.get('params')} ≠ {grid[s]}")
        else:
            bek_p = dict(config.DEFAULT_PARAMS)
            bek_p["lag_days"] = 0
            sina(f"{a}: parametre tek varsayılan", pv.get("params") == bek_p,
                 f"{pv.get('params')} ≠ {bek_p}")
        if il:
            K, taban = il.get("K"), il.get("p_taban")
            for alan in ("oos_p", "varsayilan_p"):
                p = il.get(alan)
                if p is not None and taban is not None:
                    sina(f"{a}: {alan} tabanın altına inmez", taban - 1e-9 <= p <= 1 + 1e-9,
                         f"{p} · taban {taban}")
            if isinstance(K, int) and K > 0 and taban is not None:
                sina(f"{a}: p tabanı 1/(1+K)", abs(taban - 1 / (1 + K)) < 1e-4, f"{taban} · K {K}")

    # 4 — aile sınaması karnenin kendi varlık sayılarından
    oos = [((varlik.get(a) or {}).get("ileri") or {}).get(h0, {}).get("oos") for a in config.ASSETS]
    oos = [o for o in oos if o is not None]
    sina("aile: varlık sayısı", aile.get("varlik") == len(oos), f"{aile.get('varlik')} ≠ {len(oos)}")
    sina("aile: artı sayısı", aile.get("pozitif") == sum(1 for o in oos if o > 0),
         f"{aile.get('pozitif')}")
    if oos and aile.get("istatistik") is not None:
        sina("aile: istatistik ortalamadır", abs(aile["istatistik"] - sum(oos) / len(oos)) < 1e-3,
             f"{aile['istatistik']} ≠ {sum(oos) / len(oos):.4f}")
    if aile.get("p") is not None and aile.get("K"):
        sina("aile: p tabanın altına inmez", 1 / (1 + aile["K"]) - 1e-9 <= aile["p"] <= 1 + 1e-9,
             f"{aile['p']}")

    # 5 — damga: tek kalibrasyon kimliği
    ts = {pv.get("timestamp") for pv in par.values() if isinstance(pv, dict)}
    sina("parametrelerin damgası tek", len(ts) == 1, str(sorted(ts))[:120])
    sina("damga karnenin ölçüm anı", ts == {karne.get("olcum_ani")}, f"{ts} · {karne.get('olcum_ani')}")
    sina("kalibrasyon kimliği karnenin ölçüm anı",
         kd.guncel(yol_par) == kd._saniye(karne.get("olcum_ani")),
         f"{kd.guncel(yol_par)} · {kd._saniye(karne.get('olcum_ani'))}")

    # 6 — özet (hat ve site kopyası) karnenin sayılarını taşır
    kal = tarih_kisa(karne.get("olcum_ani"))
    v = {k: x for k, x in varlik.items() if x.get("ileri")}
    ongoren = [k for k, x in v.items() if x.get("hukum") == "öngörüyor"]
    bek_ozet = {"kal_tarih": kal, "opt_kalibrasyon": kal, "kal_varlik": len(v),
                "kal_ongoren": len(ongoren), "kal_aile_rho": aile.get("istatistik"),
                "kal_aile_p": aile.get("p"), "kal_aile_k": aile.get("K"),
                "kal_aile_pozitif": aile.get("pozitif"), "kal_ufuk": int(h0),
                "kal_izgara": yon.get("izgara"), "kal_varsayilan": yon.get("varsayilan")}
    tep = sorted(((k, x["tepki"][h0]["rho"], x["tepki"][h0]["p"]) for k, x in v.items()
                  if x["tepki"][h0]["rho"] is not None), key=lambda t: -t[1])
    for i, (k, r, pp) in enumerate(tep[:3], start=1):
        bek_ozet.update({f"tepki{i}_ad": AD_TR.get(k, k), f"tepki{i}_rho": round(r, 2), f"tepki{i}_p": pp})
    bek_ozet["tepki_anlamli"] = sum(1 for *_, pp in tep if pp is not None and pp <= 0.05)
    od = sorted(((k, x["ileri"][h0]["oos"], x["ileri"][h0]["oos_p"]) for k, x in v.items()
                 if x["ileri"][h0]["oos"] is not None), key=lambda t: -t[1])
    if od:
        bek_ozet.update({"ongoru1_ad": AD_TR.get(od[0][0], od[0][0]), "ongoru1_rho": round(od[0][1], 2),
                         "ongoru1_p": od[0][2]})
    bek_ozet["ongoru_anlamli"] = sum(1 for *_, pp in od if pp is not None and pp <= 0.05)
    bek_ozet["ongoru_rakip_ustu"] = sum(
        1 for x in v.values() if x["ileri"][h0]["oos"] is not None and x["ileri"][h0]["fiyat_rakibi"] is not None
        and x["ileri"][h0]["oos"] > x["ileri"][h0]["fiyat_rakibi"])
    for ad, yol in (("hat", os.path.join(BURASI, "ozet.json")), ("site", os.path.join(SITE, "ozet.json"))):
        try:
            oz = _json(yol)
        except (OSError, ValueError) as e:
            sina(f"özet ({ad}) okunur", False, str(e))
            continue
        for k, b in bek_ozet.items():
            x = oz.get(k)
            esit = (abs(x - b) < 1e-9) if isinstance(x, (int, float)) and isinstance(b, (int, float)) else x == b
            sina(f"özet ({ad}) {k}", esit, f"{x!r} ≠ {b!r}")
        hk = oz.get("kal_hukum_cumle") or ""
        gecti = aile.get("p") is not None and aile["p"] <= esik
        sina(f"özet ({ad}) hüküm cümlesi aile sınamasının sonucunu söyler",
             hk.startswith("Aile sınaması geçti") if gecti else hk.startswith("Aile sınaması geçmedi"), hk[:80])
        sina(f"özet ({ad}) kalibrasyon saati kendi anahtarında",
             oz.get("kal_tarih_tarih") == kal and oz.get("opt_kalibrasyon_tarih") == kal,
             f"{oz.get('kal_tarih_tarih')} · {oz.get('opt_kalibrasyon_tarih')}")
        sina(f"özet ({ad}) Şekil 09'un defter tarihi kalibrasyon günü",
             (oz.get("_sekil_tarih") or {}).get("optimizasyon.html") in (str(karne.get("olcum_ani"))[:10], kal),
             str((oz.get("_sekil_tarih") or {}).get("optimizasyon.html")))

    # 7 — Şekil 09 aynı karneden çizildi
    f09 = os.path.join(SITE, "optimizasyon.html")
    try:
        with open(f09, encoding="utf-8") as f:
            html = f.read()
        sina("Şekil 09 kalibrasyon tarihini taşır", f"Kalibrasyon {kal}" in html, kal)
    except OSError as e:
        sina("Şekil 09 sitede", False, str(e))

    # 8 — Şekil 04/05 sayıları figürün kendi defterinden
    try:
        so = _json(os.path.join(BURASI, "cikti", "sekil_ozet.json"))
        oz = _json(os.path.join(SITE, "ozet.json"))
        s4 = (so.get("sekil04") or {}).get("varlik") or {}
        s5 = (so.get("sekil05") or {}).get("ort") or {}
        sina("Şekil 04 varlık sayısı özette", oz.get("s04_varlik") == len(s4), f"{oz.get('s04_varlik')} ≠ {len(s4)}")
        sina("Şekil 04 artı sayısı özette", oz.get("s04_pozitif") == sum(1 for x in s4.values() if x["rho"] > 0),
             str(oz.get("s04_pozitif")))
        sina("Şekil 05 varlık sayısı özette", oz.get("s05_varlik") == len(s5), f"{oz.get('s05_varlik')} ≠ {len(s5)}")
        if s5:
            sina("Şekil 05 5 günlük aralık özette",
                 oz.get("s05_5g_min") == round(min(x["5g"] for x in s5.values()), 2)
                 and oz.get("s05_5g_max") == round(max(x["5g"] for x in s5.values()), 2),
                 f"{oz.get('s05_5g_min')} · {oz.get('s05_5g_max')}")
    except (OSError, ValueError) as e:
        sina("Şekil 04/05 defteri okunur", False, str(e))

    if hatalar:
        for h in hatalar[:40]:
            print("  ✗", h)
        print(f"✗ FX kalibrasyon kapısı: {len(hatalar)}/{sayac} ölçüt düştü")
        return 1
    print(f"✓ FX kalibrasyon kapısı: {sayac} ölçüt geçti ({kal} kalibrasyonu, "
          f"{len(ongoren)}/{len(v)} varlık öngörüyor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
