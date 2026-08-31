#!/usr/bin/env python3
"""Sayfa metni icin canli ozet metrikleri (ozet.json) — CSV ciktilarindan, internetsiz."""
import json, os
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
oku = lambda ad: pd.read_csv(os.path.join(BASE, ad), encoding="utf-8-sig")

ih = oku("hazine_ihale_verileri.csv")
hg = oku("hazine_hedef_gerceklesme.csv")
va = oku("hazine_vade_analizi.csv")
pl = oku("hazine_planlanan_ihaleler.csv")
td = oku("hazine_tahmin_dogrulama.csv")

ih["t"] = pd.to_datetime(ih["İhale Tarihi"], dayfirst=True)
ih["ay"] = ih["t"].dt.to_period("M")
son_ay = ih["ay"].max()

def agirlikli_maliyet(g):
    g = g[~g["Senet Tanımı"].str.contains("TÜFE", na=False)].dropna(
        subset=["Ortalama Yıllık Bileşik(Gerçekleşme)", "Toplam(Gerçekleşme)"])
    if g.empty: return None
    return float((g["Ortalama Yıllık Bileşik(Gerçekleşme)"] * g["Toplam(Gerçekleşme)"]).sum()
                 / g["Toplam(Gerçekleşme)"].sum())

gercek = hg[pd.to_numeric(hg["Gerçekleşen Borçlanma (Milyar TL)"], errors="coerce") > 0]
son12 = ih[ih["ay"] > son_ay - 12]
sa = ih[ih["ay"] == son_ay]

td["t"] = pd.to_datetime(td["İhale Tarihi"], dayfirst=True)
td12 = td[td["t"] > td["t"].max() - pd.DateOffset(months=12)]
td["ayp"] = td["t"].dt.to_period("M")
aylik = td.groupby("ayp")[["Gerçek Gerçekleşme (Milyon TL)", "Tahmin-Ham (Milyon TL)"]].sum()
aylik = aylik[aylik["Gerçek Gerçekleşme (Milyon TL)"] > 0]
aylik_ham_mape = float((abs(aylik["Tahmin-Ham (Milyon TL)"] / aylik["Gerçek Gerçekleşme (Milyon TL)"] - 1)).mean() * 100)

pl_ihale = pl[pl["Yöntem"].astype(str).str.contains("hale", na=False)]
plt = pd.to_numeric(pl_ihale["Tahmini Gerçekleşme (Milyon TL)"], errors="coerce")

# ── SAYFANIN KULLANDIĞI AMA ÖZETTE OLMAYAN ALANLAR
# Sayfa bu on beş anahtarı <Deger> ile çağırıyordu; ozet.json'da olmadıkları
# için hepsi statik yedeklerinde DONMUŞTU — yani noktalı çizgiyle "canlı"
# görünüyor ama hiç tazelenmiyorlardı. Tanımlar, sayfadaki mevcut sayıları
# birebir üretecek şekilde seçildi (48,1 / 24,5 / 9,7 / 9,4 / 6,8 / 1,6 ·
# 27 çeyrek · 5,7 ihale/ay · %67 ham MAPE): yani bu bir yeniden tanımlama
# değil, elle hesaplanıp dondurulmuş bir sayının hattı kurmaktır.

# (a) Senet türü payları — toplam gerçekleşmeye göre.
_pay = (ih.groupby("Senet Tanımı")["Toplam(Gerçekleşme)"].sum()
        / ih["Toplam(Gerçekleşme)"].sum() * 100.0)
PAY_ADI = {
    "pay_sabit":    "Sabit Kuponlu Devlet Tahvili",
    "pay_tlref":    "TLREF'e Endeksli Devlet Tahvili",
    "pay_tufe":     "TÜFE'ye Endeksli Devlet Tahvili",
    "pay_bono":     "Hazine Bonosu",
    "pay_degisken": "Değişken Faizli Devlet Tahvili",
    "pay_kuponsuz": "Kuponsuz Devlet Tahvili",
}
paylar = {k: round(float(_pay.get(v, 0.0)), 1) for k, v in PAY_ADI.items()}

# (b) Planlı takvimin AYLIK kesiti. "İlk iki ay" derken kastedilen, ihale
# İÇEREN ilk iki ay: takvim çoğu zaman içinde bulunulan ayın yalnız doğrudan
# satışlarıyla başlıyor ve o ayı "ilk ay" saymak sayfada boş bir satır üretir.
pl = pl.copy()
pl["t"] = pd.to_datetime(pl["İhale Tarihi"], dayfirst=True, errors="coerce")
pl["ayp"] = pl["t"].dt.to_period("M")
pl["tahmin"] = pd.to_numeric(pl["Tahmini Gerçekleşme (Milyon TL)"], errors="coerce")
pl["hedef"] = pd.to_numeric(pl["Aylık Strateji Hedefi (Milyar TL)"], errors="coerce")
AY_ADI = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
          7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
# İç Borçlanma Stratejisi ÜÇ aylık bir dokümandır; takvim de üç ayı taşır.
# Sayfa uzun süre yalnız ilk iki ayı bastı, yani her yeni strateji yayımlandığında
# dokümanın GETİRDİĞİ ay (en uzak ay) sayfada hiç görünmüyordu. Ay sayısı artık
# takvimden okunur ve kaç ay varsa o kadar anahtar yazılır (plan_ay_adet).
plan_aylik = {}
_ihaleli = pl[pl["tahmin"].notna()]
_aylar = sorted(_ihaleli.groupby("ayp"), key=lambda x: x[0])
plan_aylik["plan_ay_adet"] = len(_aylar)
_hedef_ayi = {}
for i, (ayp, g) in enumerate(_aylar, start=1):
    ad = f"{AY_ADI[ayp.month]} {ayp.year}"
    plan_aylik[f"plan_ay{i}_ad"] = ad
    plan_aylik[f"plan_ay{i}_beklenen"] = round(float(g["tahmin"].sum()) / 1000.0, 1)
    hedefler = g["hedef"].dropna()
    if len(hedefler):
        plan_aylik[f"plan_ay{i}_hedef"] = round(float(hedefler.iloc[0]), 1)
        _hedef_ayi[ad] = float(hedefler.iloc[0])
if _hedef_ayi:
    plan_aylik["plan_hedef_toplam"] = round(sum(_hedef_ayi.values()), 1)

# (b1) Yürürlükteki strateji dokümanı ve onun getirdiği REVİZYON. Sayfada
# "strateji revizyonları" şekli var ama tek bir canlı sayı yoktu: yeni bir
# doküman çıktığında metin eski hedefleri anlatmaya devam ediyordu. Revizyon
# ancak aynı ay için ÖNCEKİ dokümanda da bir hedef varsa yazılır — ilk kez
# takvime giren ay için "revizyon" diye bir şey yoktur (uydurma yok).
_sh = os.path.join(BASE, ".strategy_history.json")
if os.path.exists(_sh):
    _h = json.load(open(_sh, encoding="utf-8"))
    _kaynak = {}
    for ad in _hedef_ayi:
        kayit = _h.get(ad) or {}
        gecmis = kayit.get("history") or []
        if kayit.get("source"):
            _kaynak[kayit["source"]] = _kaynak.get(kayit["source"], 0) + 1
        i = list(_hedef_ayi).index(ad) + 1
        if len(gecmis) >= 2:
            onceki = gecmis[-2]
            if onceki.get("target") is not None:
                plan_aylik[f"plan_ay{i}_onceki"] = round(float(onceki["target"]), 1)
                plan_aylik[f"plan_ay{i}_revizyon"] = round(
                    float(_hedef_ayi[ad]) - float(onceki["target"]), 1)
        else:
            plan_aylik[f"plan_ay{i}_yeni"] = 1   # takvime ilk kez giren ay
    if _kaynak:
        plan_aylik["plan_strateji"] = max(_kaynak, key=_kaynak.get)

# (b2) Sayfa metni için TEK anahtar altında ay listesi. Neden birleşik metin:
# takvimdeki ay sayısı DEĞİŞKEN (çeyreğin sonuna doğru iki, yeni doküman
# inince üç). Sayfa plan_ay3_* diye ayrı bir <Deger> çağırsaydı, takvim iki
# aya düştüğü gün o anahtar ozet.json'dan kaybolur ve sayfa sınavı kırılırdı —
# yani metin, veriden daha katı bir şekle bağlanmış olurdu. Ay sayısı
# değişebilir, anahtar değişmez.
def _tr(x, n=1):
    return f"{x:,.{n}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")

_satir, _rev = [], []
for i in range(1, plan_aylik.get("plan_ay_adet", 0) + 1):
    ad = plan_aylik.get(f"plan_ay{i}_ad")
    bek, hed = plan_aylik.get(f"plan_ay{i}_beklenen"), plan_aylik.get(f"plan_ay{i}_hedef")
    if ad is None or bek is None:
        continue
    _satir.append(f"{ad} {_tr(bek)}" + (f" vs {_tr(hed)}" if hed is not None else ""))
    onc, fark = plan_aylik.get(f"plan_ay{i}_onceki"), plan_aylik.get(f"plan_ay{i}_revizyon")
    if onc is not None and hed is not None:
        isaret = "+" if (fark or 0) > 0 else "\u2212"
        _rev.append(f"{ad} {_tr(onc)} \u2192 {_tr(hed)} ({isaret}{_tr(abs(fark))})")
    elif plan_aylik.get(f"plan_ay{i}_yeni"):
        _rev.append(f"{ad} takvime ilk kez girdi \u2014 revizyonu yok")
# Hedefin NEDENİ: aylık iç borç servisi. Kasım hedefinin Eylül'ün üçte biri
# olması bir politika kararı değil, o ayın itfasının üçte bir olmasıdır —
# doküman bunu kendi tablosunda yazıyor. Satır okunamadıysa yazılmaz, boş
# bırakılıp sebebi söylenir.
_servis = []
if os.path.exists(_sh):
    _h2 = json.load(open(_sh, encoding="utf-8"))
    for ad in _hedef_ayi:
        sv = ((_h2.get(ad) or {}).get("servis") or {}).get("ic")
        if sv is not None:
            _servis.append(f"{ad} {_tr(float(sv))}")
plan_aylik["plan_servis_metin"] = (" \u00b7 ".join(_servis)
                                   or "belgenin borç servisi satırı okunmadı")

plan_aylik["plan_aylik_metin"] = " \u00b7 ".join(_satir) or "planlı takvim boş"
plan_aylik["plan_revizyon_metin"] = " \u00b7 ".join(_rev) or "önceki doküman elde yok"

# (b2) USD hacmi — grafiğin KENDİ çıktısından, ve yalnız seri SAĞLAMSA.
# ihrac_usd grafiği USD/TRY kurunu yfinance'ten çekiyor ve o çekim şu anda
# bozuk: elde yalnız 6 aylık kur var, son kur 32,89 (yıllar öncesinin
# seviyesi). Bu haliyle "son ayın USD hacmi" yanlış çıkar. Sayıyı yine de
# yazmak, donmuş bir yedeği yanlış bir canlı değerle değiştirmek olurdu —
# ikisi de kötü, ikincisi daha kötü çünkü yanlışlığı görünmez. Bu yüzden
# alan ancak kur serisi en az bir yılı kapsıyorsa yazılır; kapsamıyorsa
# yazılmaz ve sayfa sınavı eksik anahtarı bağırmaya devam eder.
def _vade_proj() -> dict:
    """vade_proj.py'nin ölçtüğü vade/maliyet/talep anahtarları.

    Ayrı dosyadan okunuyor çünkü o modül karşı olgu için TAKVİM ARŞİVİNİ de
    açıyor ve pano hattının geri kalanı bunu bilmek zorunda değil. Dosya yoksa
    sessizce boş dönülür — ama sayfa o anahtarları çağırıyorsa sayfa sınavı
    eksikliği bağırır; yani sessizlik denetimsiz kalmıyor.
    """
    yol = os.path.join(BASE, "vade_proj.json")
    if not os.path.exists(yol):
        print("  ! vade_proj.json yok — vade projeksiyonu anahtarları yazılmadı")
        return {}
    d = (json.load(open(yol, encoding="utf-8")) or {}).get("ozet") or {}
    return {k: v for k, v in d.items() if not k.startswith("_")}


usd = {}
_go = os.path.join(BASE, "grafik_ozet.json")
if os.path.exists(_go):
    _g = json.load(open(_go, encoding="utf-8")).get("ihrac_usd.html") or {}
    _ay = _g.get("ay_adet") or 0
    if _ay >= 12 and _g.get("son_ay_usd_mlr") is not None:
        usd["usd_son_ay_mlr"] = round(float(_g["son_ay_usd_mlr"]), 1)
        usd["usd_ay_adet"] = int(_ay)
    else:
        print(f"  ! usd_son_ay_mlr YAZILMADI — kur serisi {_ay} ay "
              f"(en az 12 gerekiyor); ihrac_usd grafiği bozuk.")

# (c) Tempo ve backtest sayımları.
ceyrek_adet = int(ih["t"].dt.to_period("Q").nunique())
ihale_ay_ort = round(len(ih) / ih["ay"].nunique(), 1)
ihale_ham_mape = round(float(abs(pd.to_numeric(
    td["Tutar Sapma % (ham)"], errors="coerce")).mean()), 1)

ozet = {
    "_tarih": ih["t"].max().strftime("%d.%m.%Y"),
    "n_ihale": int(len(ih)),
    "toplam_mlr": round(float(ih["Toplam(Gerçekleşme)"].sum()) / 1000, 1),
    "gerceklesme_ort": round(float(pd.to_numeric(gercek["Gerçekleşme Oranı (%)"], errors="coerce").mean()), 1),
    "n_ay": int(len(gercek)),
    "b2c_son": round(float(sa["Toplam(Teklif)"].sum() / sa["Toplam(Gerçekleşme)"].sum()), 2),
    "b2c_12ay": round(float(son12.groupby("ay").apply(
        lambda g: g["Toplam(Teklif)"].sum() / g["Toplam(Gerçekleşme)"].sum()).mean()), 2),
    "kabul_son": round(float(sa["Toplam(Gerçekleşme)"].sum() / sa["Toplam(Teklif)"].sum() * 100), 1),
    "kabul_tum": round(float(ih["Toplam(Gerçekleşme)"].sum() / ih["Toplam(Teklif)"].sum() * 100), 1),
    "maliyet_son": round(agirlikli_maliyet(sa), 2),
    "wam_son": round(float(va["Ağırlıklı Ortalama Vade (Yıl)"].iloc[-1]), 2),
    "wam_3ay": round(float(va["3 Aylık Ağırlıklı Ortalama Vade"].iloc[-1]), 2),
    "plan_adet": int(len(pl)),
    "plan_ihale_adet": int(len(pl_ihale)),
    "plan_toplam_mlr": round(float(plt.sum()) / 1000, 1),
    "plan_bas": str(pl["İhale Tarihi"].iloc[0]),
    "plan_son": str(pl["İhale Tarihi"].iloc[-1]),
    "backtest_n": int(len(td)),
    "medyan_sapma": round(float(abs(pd.to_numeric(td["Tutar Sapma % (düzeltilmiş)"], errors="coerce")).median()), 1),
    "son12_mape": round(float(abs(pd.to_numeric(td12["Tutar Sapma % (düzeltilmiş)"], errors="coerce")).mean()), 1),
    "b2c_mape": round(float(abs(pd.to_numeric(td["B2C Sapma %"], errors="coerce")).mean()), 1),
    "aylik_ham_mape": round(aylik_ham_mape, 1),
    "ceyrek_adet": ceyrek_adet,
    "ihale_ay_ort": ihale_ay_ort,
    "ihale_ham_mape": ihale_ham_mape,
    **paylar,
    **plan_aylik,
    **usd,
    **_vade_proj(),
}
yol = os.path.join(BASE, "ozet.json")
json.dump(ozet, open(yol, "w"), ensure_ascii=False, indent=1)
print("yazildi:", yol); print(json.dumps(ozet, ensure_ascii=False))
