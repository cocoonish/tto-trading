#!/usr/bin/env python3
"""Canli ozet — index_history.json + sentiment_scores.json'dan, internetsiz."""
import datetime
import json, os
BASE = os.path.dirname(os.path.abspath(__file__))
h = json.load(open(os.path.join(BASE, "data", "index_history.json")))
son = h[-1]

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
    # En düşük varlığın bir önceki snapshot'taki değeri (koşudan koşuya dönüş örneği)
    k0 = sirali[0][0]
    if len(h) >= 2 and k0 in h[-2].get("indices", {}):
        ozet["alt1_onceki_deger"] = round(h[-2]["indices"][k0]["value"], 2)
        ozet["alt1_onceki_tarih"] = ".".join(reversed(h[-2]["timestamp"][:10].split("-")))
        ozet["alt1_donus_bp"] = int(round(abs(sirali[0][1] - h[-2]["indices"][k0]["value"]) * 100))
    # En az makaleli varlık: "kategori etiketi değil makale sayısı okunur" örneği
    if makale:
        az = min(ind, key=lambda k: makale.get(k, 10**9))
        ozet.update({"az_ad": AD_TR.get(az, az), "az_makale": makale.get(az),
                     "az_deger": round(ind[az]["value"], 2),
                     "az_kat": KAT_TR.get(ind[az].get("category", ""), ind[az].get("category", ""))})
        # Aynı varlığın bir önceki snapshot'taki değeri (örneklem gürültüsü örneği)
        if len(h) >= 2 and az in h[-2].get("indices", {}):
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
        """Bu varlığın tarihçe boyunca snapshot-snapshot değişimleri."""
        out = []
        for i in range(1, len(h)):
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
    # Sıralama: σ varsa olağandışılığa, yoksa ham büyüklüğe göre.
    hareketler.sort(key=lambda m: abs(m["z"]) if m["z"] is not None else abs(m["fark"]),
                    reverse=True)
    # Az makaleli varlık gürültüdür; sayfada da böyle yazıyor. Elenmiş olması
    # SAKLANMAZ — kaç tanesinin elendiği ayrı alanda durur.
    guvenli = [m for m in hareketler if (m["makale"] or 0) >= MAKALE_ASGARI]
    ozet["hareket"] = guvenli[:HAREKET_SAYISI]
    ozet["hareket_elenen"] = len(hareketler) - len(guvenli)
    ozet["hareket_sigma_var"] = any(m["sigma"] for m in guvenli[:HAREKET_SAYISI])
    # Kıyas noktası METİNDE gerekli: snapshot'lar arası mesafe sabit değil.
    ozet["hareket_kiyas_tarih"] = ".".join(reversed(onceki_s["timestamp"][:10].split("-")))
    ozet["hareket_gun"] = (
        (datetime.date.fromisoformat(son_s["timestamp"][:10])
         - datetime.date.fromisoformat(onceki_s["timestamp"][:10])).days)

# ── Grid search (optimizasyon) özeti: liderler, kalibrasyon tarihi, ufuk dağılımı ──
try:
    opt = json.load(open(os.path.join(BASE, "data", "optimized_params.json")))
    satir = [(k, v.get("rolling_mean_5d") if v.get("best_horizon") == "5d" else v.get("rolling_mean_1d"),
              v.get("best_horizon"), v.get("timestamp", "")) for k, v in opt.items() if isinstance(v, dict) and "params" in v]
    satir = [t for t in satir if t[1] is not None]
    if satir:
        lider = sorted(satir, key=lambda t: t[1], reverse=True)[:3]
        for i, (k, r, hz, _) in enumerate(lider, start=1):
            ozet[f"opt{i}_ad"] = AD_TR.get(k, k); ozet[f"opt{i}_kor"] = round(float(r), 2)
        ts = max(t[3] for t in satir)[:10]
        ozet["opt_kalibrasyon"] = ".".join(reversed(ts.split("-"))) if ts else None
        ozet["opt_varlik"] = len(satir)
        ozet["opt_5g"] = sum(1 for t in satir if t[2] == "5d")
        ozet["opt_istisna"] = ", ".join(AD_TR.get(t[0], t[0]) for t in satir if t[2] != "5d") or "—"
except Exception as e:
    print(f"optimized_params okunamadı: {e}")

# ── Rejim/korelasyon panellerinin veri sonu (önbellek ucu): web_cikti.py sidecar'ı ──
try:
    ro = json.load(open(os.path.join(BASE, "cikti", "rejim_ozet.json")))
    if ro.get("as_of"):
        ozet["veri_sonu"] = ".".join(reversed(ro["as_of"].split("-")))
    if ro.get("n_assets"):
        ozet["rejim_varlik"] = ro["n_assets"]
except Exception:
    pass
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
