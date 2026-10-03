#!/usr/bin/env python3
"""Canli ozet — index_history.json + sentiment_scores.json'dan, internetsiz."""
import datetime
import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import kalibrasyon_damga  # noqa: E402
try:
    import bicim  # noqa: E402  (ortak/; hat PYTHONPATH'inde)
except ImportError:
    sys.path.insert(0, os.path.join(BASE, "..", "..", "ortak"))
    import bicim  # noqa: E402
h = json.load(open(os.path.join(BASE, "data", "index_history.json")))
son = h[-1]


def _ayni_model(a: dict, b: dict) -> bool:
    """İki okuma AYNI kalibrasyonun parametreleriyle mi kuruldu? Değilse aradaki
    fark haberin değil modelin değişimidir ve hiçbir harekete, σ'ya ya da
    "önceki okumaya göre" örneğine girmez (bkz. kalibrasyon_damga)."""
    return kalibrasyon_damga.kimlik(a) == kalibrasyon_damga.kimlik(b)


# ── SAAT: bu dosyada iki ayrı ölçüm ve iki ayrı saat var ────────────────────
# Endeks değerleri (ust1/alt1… ve tarihçe) Google RSS akışından, koşu anından
# geriye 7 günlük pencereyle kuruluyor — saatleri `veri_sonu`, yani endekse
# giren en yeni haberin günü.
# Rejim büyüklükleri (rejim/spread/ort_korelasyon/pc1) GDELT haftalık
# önbelleğinden geliyor ve son TAM haftada bitiyor — saatleri `as_of`.
# 26.08 Çarşamba koşan bir hat, rejim panelinde 23.08 Pazar'ı ölçüyordu; tek
# bir `_tarih` ikisini de "26.08" diye gösteriyordu. Artık her anahtar kendi
# saatini `<anahtar>_tarih` geleneğiyle taşır (bkz. CLAUDE.md "Kurucu ilke —
# saat"); `_tarih` hattın ana saati olarak endeksin veri ucudur, koşu saati
# ise `_kosum` altında ayrı durur.
kosu = son["timestamp"][:16].replace("T", " ") + " UTC"


def _veri_ucu():
    """Son okumanın VERİ ucu: endekse giren en yeni haberin yayım zamanı.

    Önce snapshot'ın kendi kaydı (index_builder bunu yazar). Eski koşular bu
    alanı yazmıyordu; onlarda aynı büyüklük data/sentiment_scores.json'dan
    ÖLÇÜLEBİLİR — o dosya son koşunun skorladığı makaleleri tutar, uç da o
    makalelerin en yenisidir. İkisi de yoksa uydurmayız: koşu saatine döner
    ve `_tarih_kaynagi` ile bunu söyleriz.
    """
    uc = son.get("veri_sonu")
    if uc:
        return str(uc), None
    try:
        yayim = [m["published"] for v in sk.values()
                 for m in v.get("articles", [])
                 if "score" in m and m.get("published")]
        if yayim:
            return max(yayim), None
    except Exception:
        pass
    return son["timestamp"], "koşu saati (bu koşu veri ucunu kaydetmemiş)"


ozet = {"snapshot_sayisi": len(h), "varlik_sayisi": len(son.get("indices", {}))}
# Son okumanın kurulduğu kalibrasyon (snapshot kendi yazar; eskilerde tarihinden).
ozet["endeks_kalibrasyon"] = kalibrasyon_damga.ad(kalibrasyon_damga.kimlik(son))
sk = {}
try:
    sk = json.load(open(os.path.join(BASE, "data", "sentiment_scores.json")))
    ozet["makale_toplam"] = sum(len(v.get("articles", [])) for v in sk.values())
except Exception:
    pass

_uc, _kaynak = _veri_ucu()
ozet["_tarih"] = _uc[:16].replace("T", " ") + " UTC"
ozet["_kosum"] = kosu
if _kaynak:
    ozet["_tarih_kaynagi"] = _kaynak
rej = son.get("regime")
if rej:
    ozet.update({"rejim": rej.get("label"), "spread": rej.get("basket_spread"),
                 "ort_korelasyon": rej.get("avg_correlation"), "pc1": rej.get("pc1_share")})
    # Rejim büyüklüklerinin KENDİ saati: haftalık önbelleğin ucu, koşu değil.
    if rej.get("as_of"):
        for anahtar in ("rejim", "spread", "ort_korelasyon", "pc1"):
            ozet[f"{anahtar}_tarih"] = rej["as_of"]

# ── Sayfa metnindeki uçlar ve makale sayıları: son snapshot'tan, elle yazılmaz ──
AD_TR = {"EURUSD": "EUR/USD", "USDJPY": "USD/JPY", "USDCHF": "USD/CHF", "GBPUSD": "GBP/USD",
         "AUDUSD": "AUD/USD", "NZDUSD": "NZD/USD", "USDCAD": "USD/CAD", "USDNOK": "USD/NOK",
         "USDSEK": "USD/SEK", "XAUUSD": "altın", "XAGUSD": "gümüş", "SPX": "S&P 500",
         "UST2Y": "ABD 2Y", "UST10Y": "ABD 10Y", "BIST100": "BIST 100"}
KAT_TR = {"Extremely Bullish": "Aşırı Alıcı", "Bullish": "Alıcı", "Neutral": "Nötr",
          "Bearish": "Satıcı", "Extremely Bearish": "Aşırı Satıcı"}
ind = son.get("indices", {})
# Grafik hover'ıyla AYNI tanım: yalnız "score" alanı olan (skorlanmış) makaleler
try:
    makale = {k: sum(1 for m in v.get("articles", []) if "score" in m) for k, v in sk.items()}
except Exception:
    makale = {}
sirali = sorted(((k, v["value"], v.get("category", "")) for k, v in ind.items()
                 if isinstance(v, dict) and v.get("value") is not None), key=lambda t: t[1])
if len(sirali) >= 4:
    for etiket, (k, v, kat) in zip(("ust1", "ust2"), (sirali[-1], sirali[-2])):
        ozet.update({f"{etiket}_ad": AD_TR.get(k, k), f"{etiket}_deger": round(v, 2),
                     f"{etiket}_kat": KAT_TR.get(kat, kat), f"{etiket}_makale": makale.get(k)})
    for etiket, (k, v, kat) in zip(("alt1", "alt2"), (sirali[0], sirali[1])):
        ozet.update({f"{etiket}_ad": AD_TR.get(k, k), f"{etiket}_deger": round(v, 2),
                     f"{etiket}_kat": KAT_TR.get(kat, kat), f"{etiket}_makale": makale.get(k)})
    # En düşük varlığın bir önceki okumadaki değeri (koşudan koşuya dönüş örneği).
    # Sayfa bunu TEK cümle anahtarıyla basar: önceki okuma başka bir kalibrasyondan
    # geliyorsa kıyas kurulamaz ve cümle bunun SEBEBİNİ yazar (boş sayı basılmaz).
    k0 = sirali[0][0]
    if len(h) >= 2 and not _ayni_model(h[-2], son):
        ozet["alt1_donus_cumle"] = (
            f"En düşük okumadaki {AD_TR.get(k0, k0)} bir önceki okumayla kıyaslanamaz: o okuma "
            f"{kalibrasyon_damga.ad(kalibrasyon_damga.kimlik(h[-2]))} kalibrasyonunun parametreleriyle, "
            f"bu okuma {kalibrasyon_damga.ad(kalibrasyon_damga.kimlik(son))} kalibrasyonununkiyle kuruldu.")
    elif len(h) >= 2 and k0 in h[-2].get("indices", {}):
        once = h[-2]["indices"][k0]["value"]
        ozet["alt1_onceki_deger"] = round(once, 2)
        ozet["alt1_onceki_tarih"] = ".".join(reversed(h[-2]["timestamp"][:10].split("-")))
        ozet["alt1_donus_cumle"] = (
            f"En düşük okumadaki {AD_TR.get(k0, k0)} bir önceki okumada ({ozet['alt1_onceki_tarih']}) "
            f"{bicim.sayi(round(once, 2), 2, True)} idi; iki okuma arasındaki fark "
            f"{bicim.sayi(round(abs(sirali[0][1] - once), 2), 2)} (endeks −1 ile +1 arasında).")
    else:
        ozet["alt1_donus_cumle"] = "Önceki okuma yok: kıyas kurulamadı."
    # En az makaleli varlık: "kategori etiketi değil makale sayısı okunur" örneği
    if makale:
        az = min(ind, key=lambda k: makale.get(k, 10**9))
        ozet.update({"az_ad": AD_TR.get(az, az), "az_makale": makale.get(az),
                     "az_deger": round(ind[az]["value"], 2),
                     "az_kat": KAT_TR.get(ind[az].get("category", ""), ind[az].get("category", ""))})
        # Aynı varlığın bir önceki snapshot'taki değeri (örneklem gürültüsü örneği)
        if len(h) >= 2 and az in h[-2].get("indices", {}) and _ayni_model(h[-2], son):
            ozet["az_onceki_deger"] = round(h[-2]["indices"][az]["value"], 2)
            ozet["az_onceki_tarih"] = h[-2]["timestamp"][:10]

# ── Günün olağandışı haber hareketleri ────────────────────────────────────────
#
# EŞİK DEĞİL SIRALAMA. Sabit bir eşik burada işlemiyor: gerçek tarihçeyle
# ölçüldüğünde snapshot'tan snapshot'a 15 varlığın 9-12'si kategori değiştiriyor
# ve |Δ| medyanı 0,256 — bant genişliği (0,30) kadar. "Kategori değişti" ya da
# "0,3'ü aştı" diyen bir kural her gün on sahte olay üretir ve bülteni bloklardı.
#
# Piyasa katmanındaki kalıp doğru olan: en çok hareket edeni SIRALA. Günün en
# büyük hareketi her zaman tanımlıdır, sayısı sabittir, uydurma eşik gerekmez.
# Yeterli tarihçe biriktiğinde (>=OYNAKLIK_ASGARI değişim) hareket varlığın
# KENDİ oynaklığına da bölünür — yüzde büyüklüğü ile olağandışılık ayrı şeyler.
OYNAKLIK_ASGARI = 10       # bu kadar değişim yoksa σ hesaplanmaz, None yazılır
HAREKET_SAYISI = 3         # bültene giren en olağandışı hareket sayısı
MAKALE_ASGARI = 20         # bu kadar makalesi olmayan varlık gürültüdür

if len(h) >= 2:
    onceki_s, son_s = h[-2], h[-1]
    a_ind, b_ind = onceki_s.get("indices", {}), son_s.get("indices", {})

    def _degisimler(kod):
        """Bu varlığın tarihçe boyunca snapshot-snapshot değişimleri — YALNIZ son
        okumanın kalibrasyonu içinde (σ başka bir modelin farklarını karıştırmaz)."""
        out = []
        for i in range(1, len(h)):
            if not (_ayni_model(h[i - 1], h[i]) and _ayni_model(h[i], son)):
                continue
            x = h[i - 1].get("indices", {}).get(kod, {})
            y = h[i].get("indices", {}).get(kod, {})
            if x.get("value") is not None and y.get("value") is not None:
                out.append(y["value"] - x["value"])
        return out

    def _sigma(d):
        if len(d) < OYNAKLIK_ASGARI:
            return None
        ort = sum(d) / len(d)
        var = sum((v - ort) ** 2 for v in d) / (len(d) - 1)
        s = var ** 0.5
        return round(s, 4) if s else None

    hareketler = []
    for kod, y in b_ind.items():
        x = a_ind.get(kod)
        if not x or x.get("value") is None or y.get("value") is None:
            continue
        fark = y["value"] - x["value"]
        s = _sigma(_degisimler(kod))
        hareketler.append({
            "kod": kod,
            "ad": AD_TR.get(kod, kod),
            "deger": round(y["value"], 2),
            "onceki": round(x["value"], 2),
            "fark": round(fark, 2),
            "sigma": s,
            "z": round(fark / s, 1) if s else None,
            "kat": KAT_TR.get(y.get("category", ""), y.get("category", "")),
            "onceki_kat": KAT_TR.get(x.get("category", ""), x.get("category", "")),
            "makale": makale.get(kod),
        })
    # KALİBRASYON DEĞİŞTİYSE HAREKET YOK. Parametreler yenilendiği gün aynı haber
    # akışı başka bir sayı verir; o günün farkı haber değil modeldir. Bülten bunu
    # "haber tonunun olağandışı hareketi" diye basardı (olay.haber_endeksi_olaylari).
    if not _ayni_model(onceki_s, son_s):
        hareketler = []
        ozet["hareket_kesinti"] = (
            "kalibrasyon değişti (" + kalibrasyon_damga.degisim_metni(
                kalibrasyon_damga.kimlik(onceki_s), kalibrasyon_damga.kimlik(son_s))
            + "); fark modelden gelir")
    # Sıralama: σ varsa olağandışılığa, yoksa ham büyüklüğe göre.
    hareketler.sort(key=lambda m: abs(m["z"]) if m["z"] is not None else abs(m["fark"]),
                    reverse=True)
    # Az makaleli varlık gürültüdür; sayfada da böyle yazıyor. Elenmiş olması
    # SAKLANMAZ — kaç tanesinin elendiği ayrı alanda durur.
    guvenli = [m for m in hareketler if (m["makale"] or 0) >= MAKALE_ASGARI]
    ozet["hareket"] = guvenli[:HAREKET_SAYISI]
    ozet["hareket_elenen"] = len(hareketler) - len(guvenli)
    ozet["hareket_sigma_var"] = any(m["sigma"] for m in guvenli[:HAREKET_SAYISI])
    # σ ölçülemiyorsa SEBEBİ yazılır: bülten σ'sız hareketi olağandışı saymaz,
    # okur da "bülten neden haber tonu yazmıyor" sorusunun cevabını görsün.
    _cift = sum(1 for i in range(1, len(h)) if _ayni_model(h[i - 1], h[i]) and _ayni_model(h[i], son))
    ozet["hareket_sigma_neden"] = (
        "" if ozet["hareket_sigma_var"] or not ozet["hareket"] and not ozet.get("hareket_kesinti")
        else (f"Olağandışılık henüz ölçülemiyor: {kalibrasyon_damga.ad(kalibrasyon_damga.kimlik(son))} "
              f"kalibrasyonundan beri {_cift} okuma çifti var, oynaklık için en az {OYNAKLIK_ASGARI} gerekiyor."))
    # Kıyas noktası METİNDE gerekli: snapshot'lar arası mesafe sabit değil.
    ozet["hareket_kiyas_tarih"] = ".".join(reversed(onceki_s["timestamp"][:10].split("-")))
    ozet["hareket_gun"] = (
        (datetime.date.fromisoformat(son_s["timestamp"][:10])
         - datetime.date.fromisoformat(onceki_s["timestamp"][:10])).days)

# ── KALİBRASYON KARNESİ: data/kalibrasyon_karne.json (correlation_optimizer) ──
# Sayfanın çağırdığı her anahtar HER koşuda yazılır; karne okunamazsa hat DÜŞER
# (sessiz bir except, sayfanın anahtarlarını düşürüp yayını durdururdu).
# KARNENİN SAATİ KALİBRASYON GÜNÜDÜR, hattın ana saati değil: her anahtar kendi
# `<anahtar>_tarih`ini taşır (09.09.2026: okur 49 gün önceki ölçümü bugünün sanıyordu).
AGG_TR = {"weighted_mean": "ağırlıklı ortalama", "bull_bear_ratio": "boğa/ayı oranı",
          "intensity_ratio": "yoğunluk oranı", "directional_strength": "yön gücü"}
karne = json.load(open(os.path.join(BASE, "data", "kalibrasyon_karne.json"), encoding="utf-8"))
_kal = ".".join(reversed(str(karne["olcum_ani"])[:10].split("-")))
_h = str(karne["yontem"]["ufuklar"][0])
_v = {k: v for k, v in karne["varlik"].items() if v.get("ileri")}
_a = karne["aile"][_h]
_ongoren = [k for k, v in _v.items() if v.get("hukum") == "öngörüyor"]
kal = {"kal_tarih": _kal, "kal_varlik": len(_v), "kal_ongoren": len(_ongoren),
       "kal_aile_rho": _a["istatistik"], "kal_aile_p": _a["p"], "kal_aile_k": _a["K"],
       "kal_aile_pozitif": _a["pozitif"], "kal_ufuk": int(_h),
       "kal_izgara": karne["yontem"]["izgara"]}
_p_taban = round(1 / (1 + _a["K"]), 3) if _a.get("K") else None
kal["kal_p_taban"] = _p_taban
if _a["p"] is not None and _a["p"] <= karne["yontem"]["esik_p"]:
    kal["kal_hukum_cumle"] = (
        f"Aile sınaması geçti (plasebo p {bicim.sayi(_a['p'], 3)}); kendi örnek dışı ölçüsü hem sıfırın "
        f"hem yalnız fiyattan kurulan rakibin üstünde olan {len(_ongoren)} varlık kendi parametresiyle "
        f"kuruluyor" + (f": {', '.join(AD_TR.get(k, k) for k in _ongoren)}." if _ongoren else "."))
else:
    kal["kal_hukum_cumle"] = (
        f"Aile sınaması geçmedi: {len(_v)} varlığın sonraki {_h} günle örnek dışı ρ ortalaması "
        f"{bicim.sayi(_a['istatistik'], 3, True)}, plasebo p {bicim.sayi(_a['p'], 3)}. Kural gereği bütün "
        f"varlıklar tek, önceden yazılmış varsayılan parametreyle kuruluyor.")
_vy = karne["yontem"]["varsayilan"]
kal["kal_varsayilan"] = _vy
_tepki = sorted(((k, v["tepki"][_h]["rho"], v["tepki"][_h]["p"]) for k, v in _v.items()
                 if v["tepki"][_h]["rho"] is not None), key=lambda t: -t[1])
for i, (k, r, pp) in enumerate(_tepki[:3], start=1):
    kal[f"tepki{i}_ad"], kal[f"tepki{i}_rho"], kal[f"tepki{i}_p"] = AD_TR.get(k, k), round(r, 2), pp
for i in range(len(_tepki[:3]) + 1, 4):              # sayfa üçünü de adıyla çağırır
    kal[f"tepki{i}_ad"], kal[f"tepki{i}_rho"], kal[f"tepki{i}_p"] = "—", "—", "—"
kal["tepki_anlamli"] = sum(1 for _, _, pp in _tepki if pp is not None and pp <= 0.05)
_oos = sorted(((k, v["ileri"][_h]["oos"], v["ileri"][_h]["oos_p"]) for k, v in _v.items()
               if v["ileri"][_h]["oos"] is not None), key=lambda t: -t[1])
if _oos:
    k, r, pp = _oos[0]
    kal.update({"ongoru1_ad": AD_TR.get(k, k), "ongoru1_rho": round(r, 2), "ongoru1_p": pp})
else:
    kal.update({"ongoru1_ad": "—", "ongoru1_rho": "—", "ongoru1_p": "—"})
kal["ongoru_anlamli"] = sum(1 for _, _, pp in _oos if pp is not None and pp <= 0.05)
kal["ongoru_beklenen"] = round(0.05 * len(_oos), 2)
_rakip_ustu = sum(1 for k, v in _v.items() if v["ileri"][_h]["oos"] is not None
                  and v["ileri"][_h]["fiyat_rakibi"] is not None
                  and v["ileri"][_h]["oos"] > v["ileri"][_h]["fiyat_rakibi"])
kal["ongoru_rakip_ustu"] = _rakip_ustu
for _k in list(kal):
    kal[f"{_k}_tarih"] = _kal
ozet.update(kal)
ozet["opt_kalibrasyon"] = _kal                       # Şekil 09'un saati
ozet["opt_kalibrasyon_tarih"] = _kal

# ── Şekil 04/05'in metindeki sayıları: figürün KENDİ hesabından (cikti/sekil_ozet.json) ──
try:
    so = json.load(open(os.path.join(BASE, "cikti", "sekil_ozet.json"), encoding="utf-8"))
except (OSError, ValueError):
    so = {}
s4 = (so.get("sekil04") or {}).get("varlik") or {}
if s4:
    _uc4 = ".".join(reversed(str((so["sekil04"] or {}).get("uc") or "")[:10].split("-")))
    rh = sorted(v["rho"] for v in s4.values())
    s04 = {"s04_varlik": len(s4), "s04_pozitif": sum(1 for v in s4.values() if v["rho"] > 0),
           "s04_anlamli": sum(1 for v in s4.values() if v["p"] <= 0.05),
           "s04_medyan": round(rh[len(rh) // 2] if len(rh) % 2 else (rh[len(rh) // 2 - 1] + rh[len(rh) // 2]) / 2, 2),
           "s04_hafta": max(v["n"] for v in s4.values())}
    for _k in list(s04):
        s04[f"{_k}_tarih"] = _uc4
    ozet.update(s04)
else:
    # Sayfa bu anahtarlari adiyla cagirir: figur ciktisi yoksa yine YAZILIR, bos.
    ozet.update({k: "—" for k in ("s04_varlik", "s04_pozitif", "s04_anlamli", "s04_medyan", "s04_hafta")})
s5 = (so.get("sekil05") or {}).get("ort") or {}
if s5:
    _uc5 = ".".join(reversed(str((so["sekil05"] or {}).get("uc") or "")[:10].split("-")))
    bd = [v["bant_disi_5g"] for v in s5.values() if v.get("bant_disi_5g") is not None]
    s05 = {"s05_varlik": len(s5),
           "s05_1g_min": round(min(v["1g"] for v in s5.values()), 2),
           "s05_1g_max": round(max(v["1g"] for v in s5.values()), 2),
           "s05_5g_min": round(min(v["5g"] for v in s5.values()), 2),
           "s05_5g_max": round(max(v["5g"] for v in s5.values()), 2),
           "s05_bant_disi": round(100 * sum(bd) / len(bd), 1) if bd else "—"}
    for _k in list(s05):
        s05[f"{_k}_tarih"] = _uc5
    ozet.update(s05)
else:
    ozet.update({k: "—" for k in ("s05_varlik", "s05_1g_min", "s05_1g_max", "s05_5g_min",
                                  "s05_5g_max", "s05_bant_disi")})

# ── Rejim/korelasyon panellerinin veri sonu (önbellek ucu): web_cikti.py sidecar'ı ──
try:
    ro = json.load(open(os.path.join(BASE, "cikti", "rejim_ozet.json")))
    if ro.get("as_of"):
        ozet["veri_sonu"] = ".".join(reversed(ro["as_of"].split("-")))
    if ro.get("n_assets"):
        ozet["rejim_varlik"] = ro["n_assets"]
    # Sayfadaki rejim cümlesi Şekil 06'nın KENDİ dosyasından: snapshot'ın rejimi
    # koşu anında yazılır, şekil ise kalibrasyon değişince yeniden çizilir; ikisi
    # o gün ayrışır ve aynı tarihle iki ayrı sayı basılırdı.
    if ro.get("label"):
        ozet.update({"rejim": ro.get("label"), "spread": ro.get("basket_spread"),
                     "ort_korelasyon": ro.get("avg_correlation"), "pc1": ro.get("pc1_share")})
        if ro.get("as_of"):
            for anahtar in ("rejim", "spread", "ort_korelasyon", "pc1"):
                ozet[f"{anahtar}_tarih"] = ro["as_of"]
except Exception:
    pass
# ── ŞEKİL SAAT DEFTERİ: her figür KENDİ tarihiyle damgalansın ───────────────
# Sayfadaki her şeklin altında "veri <tarih>" yazar ve o tarih, MDX'te ayrı bir
# anahtar verilmemişse hattın ANA saatinden (`_tarih`) gelir. Bu hatta iki saat
# var ve tek damga ikisini birden anlatamıyordu: GDELT tabanlı dört panel
# günlerce eskiyken "bugün" diye damgalanıyor, okur da taze endeksin bayat
# olduğunu sanıyordu ("aşağıda haberler geliyor ama endeks yenilenmemiş gibi").
#
# Defterin ASIL kaynağı web_cikti.py'nin yazdığı cikti/sekil_tarih.json: orada
# her figürün ucu ÇİZİLDİĞİ ANDA, çizen kodun elindeki seriden yazılır. Burada
# yalnızca (a) o dosya henüz yokken bilinen saatlerden dolduruyoruz,
# (b) ölçülemeyen figürü None ile İŞARETLİYORUZ — uydurma bir tarih yerine
# sayfada hiç tarih çıkmasın diye (bkz. GrafikEmbed).
ANLIK = ("endeks_tarihce.html", "endeks_son.html", "son_mansetler.html")
# GDELT önbelleğinin ucuyla (as_of) BİREBİR biten figürler. Ölçüldü: rejim,
# rejim tarihçesi ve korelasyon matrisi matrisin son satırında bitiyor.
# fiyat_endeks KARMA — fiyat bacağı bugüne kadar gelir, duyarlılık bacağı
# as_of'ta durur; ortak ölçüm orada bittiği için ESKİ bacak damga olur.
HAFTALIK = ("rejim.html", "rejim_tarihce.html", "korelasyon_matrisi.html",
            "fiyat_endeks.html")
# UCU AS_OF'TAN DA GERİDE OLAN figürler: ileri getiri kaydırması son noktaları
# düşürür (yuvarlanan korelasyonda 20g pencere + shift, duyarlılık-getiride
# 5 günlük ileri pencere). Kaç gün geride olduklarını TÜRETMİYORUZ —
# web_cikti.py ölçüp deftere yazana kadar None kalırlar ve sayfa o şekillerin
# altına tarih basmaz. Az yanlış da yanlıştır: as_of'tan damgalamak
# yuvarlanan korelasyonda iki gün ileri bir tarih basmak olurdu.
sekil = {}
try:
    sekil = json.load(open(os.path.join(BASE, "cikti", "sekil_tarih.json")))
except Exception:
    pass


def _iso(m):
    """'03.09.2026' / '2026-08-30' / '2026-09-03 06:32 UTC' → 'YYYY-AA-GG'."""
    m = str(m or "")
    if len(m) >= 10 and m[4] == "-":
        return m[:10]
    if len(m) >= 10 and m[2] == ".":
        g, a, y = m[:10].split(".")
        return f"{y}-{a}-{g}"
    return None


_anlik = _iso(ozet.get("_tarih"))
_haftalik = _iso(ozet.get("rejim_tarih")) or _iso(ozet.get("veri_sonu"))
for _ad in ANLIK:
    sekil.setdefault(_ad, _anlik)
for _ad in HAFTALIK:
    sekil.setdefault(_ad, _haftalik)
sekil.setdefault("optimizasyon.html", _iso(ozet.get("opt_kalibrasyon")))
for _ad in ("duyarlilik_getiri.html", "yuvarlanan_korelasyon.html"):
    sekil.setdefault(_ad, None)
ozet["_sekil_tarih"] = dict(sorted(sekil.items()))

json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
