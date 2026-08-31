# -*- coding: utf-8 -*-
"""El Niño — KÜRESEL KANAT: emtia, ABD enflasyonu, politika faizi.

NEDEN AYRI BİR KATMAN. Türkiye ölçümü (metrik.py) bir duvara çarpıyor: TÜFE
alt endeksleri 2006'da başlıyor, o pencerede yalnız İKİ güçlü El Niño
tamamlandı ve iki gözlemle yön iddia etmek istatistik değil hikâyedir. Ama
El Niño'nun Türkiye'ye geldiği yol zaten YEREL değil: küresel emtia fiyatı.
O halkanın verisi 1980'de başlıyor ve aynı epizot tanımı orada BEŞ gözlem
verir. Türkiye'de ölçülemeyen şey, şokun geldiği yerde ölçülebilir.

Bu katman dört soruyu ayrı ayrı ölçer:

  1. KÜRESEL GIDA EMTİASI. Güçlü El Niño zirvelerinden sonraki 18 ayda REEL
     gıda emtia fiyatının yıllık değişimi, koşulsuz ortalamadan farklı mı?
     Reel: IMF endeksi ABD TÜFE'siyle deflate edilir — nominal ölçmek şoku
     ABD'nin kendi enflasyonuyla karıştırırdı.
  2. ÜRÜN KIRILIMI. Hangi ürün ENSO'ya duyarlı? Palm yağı ve pirinç ENSO'nun
     doğrudan üzerine oturduğu coğrafyalardan gelir; buğday ve mısır gelmez.
     Kanal gerçekse sıralama bunu göstermeli — göstermiyorsa o da bir bulgudur.
  3. ABD. Türkiye ile AYNI yöntem: göreceli gıda enflasyonu (gıda − manşet),
     aynı epizot tanımı, aynı 18 aylık pencere. İki ülke aynı ölçütle yan yana
     konur. Ayrıca ABD'de şok ÇEKİRDEĞE ulaşıyor mu — bir merkez bankasının
     "bakma, geç" kararını veren asıl soru budur ve aynısı Türkiye için de
     ölçülür.
  4. FED. Epizot zirvelerinden sonraki 18 ayda politika faizi ne yaptı?
     BU ÖLÇÜM NEDENSEL DEĞİLDİR ve ortalaması ALINMAZ: dört epizodun her biri
     bambaşka bir şeyin gölgesinde (Volcker dezenflasyonu, Asya krizi, faiz
     artırım döngüsünün başlangıcı, Kovid sonrası indirim). Sayılar tek tek
     yazılır, ortalama alınıp "Fed'in El Niño tepkisi" diye sunulmaz.

KÜRESEL BLOK YUMUŞAK DÜŞER. data/kuresel.csv yoksa bu katman hiçbir şey
yazmaz ve 0 ile çıkar — Türkiye ölçümü kendi başına ayakta durur. Eski
kuresel.json bırakılmaz, SİLİNİR: bayat sayıyı taze göstermek en kötüsüdür.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from metrik import ASGARI_AY, ESIK_GUCLU, UFUK, capraz, epizotlar

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"

# Ürün kırılımında rapor edilecek seriler ve ENSO literatüründeki gerekçesi.
# "beklenen" alanı, kanalın ÖNCEDEN söylediğini kaydeder; ölçüm sonra gelir ve
# beklentiyi doğrulamak zorunda değildir.
URUNLER = {
    "palm":     ("Palm yağı", "Endonezya + Malezya dünya arzının ~%85'i; ENSO kuraklığı doğrudan"),
    "pirinc":   ("Pirinç", "Güneydoğu Asya muson rejimi; Hindistan ihracat kısıtları"),
    "seker":    ("Şeker", "Hindistan + Tayland muson; Brezilya kuraklığı"),
    "kahve":    ("Kahve (robusta)", "Vietnam ve Brezilya; ENSO kuraklığına duyarlı"),
    "kakao":    ("Kakao", "Batı Afrika; ENSO Gine Körfezi yağışını değiştirir"),
    "cay":      ("Çay", "Hindistan, Sri Lanka, Kenya — üçü de ENSO yağış rejiminde"),
    "muz":      ("Muz", "Ekvador ve Orta Amerika; El Niño'nun klasik coğrafyası"),
    "soya":     ("Soya", "Brezilya + Arjantin; El Niño Arjantin'e genelde YAĞIŞ getirir"),
    "misir":    ("Mısır", "ABD Mısır Kuşağı ENSO'ya zayıf bağlı"),
    "bugday":   ("Buğday", "Karadeniz havzası ENSO'nun dışında"),
    "portakal": ("Portakal", "Brezilya + Florida; ENSO bağı dolaylı"),
}
TOPLU = {
    "emtia_gida":     "Gıda endeksi",
    "emtia_yaglar":   "Yağlar ve küspeler",
    "emtia_tahil":    "Tahıllar",
    "emtia_icecek":   "İçecekler",
    "emtia_hammadde": "Tarımsal hammadde",
    "emtia_tarim":    "Tarım (toplam)",
    "emtia_yakitsiz": "Yakıt dışı emtia",
    "emtia_metal":    "Metal ve mineraller",
    "emtia_enerji":   "Enerji",
}
# Deflatörsüz sağlamlık: gıda − metal. İki endeks de aynı küresel talep ve
# dolar döngüsünü taşır; ENSO metalleri arz tarafından vurmaz. Fark, ortak
# faktör düşünce geriye kalan GIDAYA ÖZGÜ hareketi verir ve hiçbir deflatör
# varsayımına dayanmaz.
KONTROL = "emtia_metal"
ASGARI_EPIZOT = 3      # bunun altında YÖN hakkında hüküm kurulmaz
GEC_MAKS = 24

_UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def _r(x, n=2):
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) else round(v, n)


def _yillik(s: pd.Series) -> pd.Series:
    return (s / s.shift(12) - 1.0) * 100.0


def _aylik(s: pd.Series) -> pd.Series:
    return (s / s.shift(1) - 1.0) * 100.0


def epizot_calismasi(hedef: pd.Series, eps: list[dict], ufuk: int = UFUK) -> dict:
    """Zirveden sonraki `ufuk` ayın ortalaması vs koşulsuz ortalama.

    Kalıcılık yanlılığı bu ölçütten geçmez: karşılaştırılan şey iki ortalama,
    iki kalıcı serinin korelasyonu değil.
    """
    hedef = hedef.dropna()
    if hedef.empty:
        return {"kayitlar": [], "olculen": 0}
    kayit = []
    for e in eps:
        if e.get("suruyor"):
            continue
        pencere = hedef.loc[e["zirve"]:e["zirve"] + pd.DateOffset(months=ufuk)]
        if len(pencere) < 6:        # yarım pencere ölçüm sayılmaz
            continue
        kayit.append({"zirve": f"{e['zirve']:%Y-%m}", "zirve_oni": _r(e["zirve_deger"]),
                      "ortalama": _r(pencere.mean()), "ay": int(len(pencere))})
    out = {"kayitlar": kayit, "olculen": len(kayit),
           "kosulsuz": _r(hedef.mean()),
           "orneklem_bas": f"{hedef.index.min():%Y-%m}",
           "orneklem_son": f"{hedef.index.max():%Y-%m}"}
    if kayit:
        ort = float(np.mean([k["ortalama"] for k in kayit]))
        out["epizot_ortalama"] = _r(ort)
        out["fark"] = _r(ort - float(hedef.mean()))
    return out


def _regres(x: pd.Series, y: pd.Series) -> dict | None:
    ort = pd.concat([x, y], axis=1).dropna()
    if len(ort) < 48:
        return None
    a, b = ort.iloc[:, 0].to_numpy(), ort.iloc[:, 1].to_numpy()
    beta, sabit = np.polyfit(a, b, 1)
    r = float(np.corrcoef(a, b)[0, 1])
    return {"beta": _r(beta, 3), "sabit": _r(sabit, 3), "r2": _r(r * r, 3),
            "kor": _r(r, 3), "n": int(len(ort))}


def _en_iyi_gecikmeli(x: pd.Series, y: pd.Series, gec_maks: int = GEC_MAKS) -> dict | None:
    """y[t] ~ x[t−k]; k, açıklama gücüne göre seçilir. Seçilen k de raporlanır —
    'en iyi gecikme' bir SONUÇ değil, bir arama sonucudur ve öyle yazılır."""
    en = None
    profil = []
    for k in range(gec_maks + 1):
        d = _regres(x.shift(k), y)
        if not d:
            continue
        profil.append({"gecikme": k, "r2": d["r2"], "beta": d["beta"]})
        if en is None or (d["r2"] or 0) > (en["r2"] or 0):
            en = dict(d, gecikme=k)
    if en is not None:
        en["profil"] = profil
    return en


def main() -> int:
    print("── El Niño hattı · küresel kanat")
    kur_yol = DATA / "kuresel.csv"
    cikti = DATA / "kuresel.json"
    if not kur_yol.exists():
        if cikti.exists():
            cikti.unlink()
            print("  ! kuresel.csv yok — eski kuresel.json SİLİNDİ (bayat sayı yayılmasın)")
        print("  ! küresel blok bu koşuda üretilmiyor")
        return 0

    K = pd.read_csv(kur_yol, index_col=0, parse_dates=True).sort_index()
    oni = pd.read_csv(DATA / "oni.csv", index_col=0, parse_dates=True)["oni"]
    tufe = pd.read_csv(DATA / "tufe.csv", index_col=0, parse_dates=True)

    eps = epizotlar(oni, ESIK_GUCLU)
    S: dict = {
        "_tarih": f"{K.index.max():%d.%m.%Y}", "_ay": f"{K.index.max():%Y-%m}",
        "kur_bas": f"{K.index.min():%Y-%m}", "kur_son": f"{K.index.max():%Y-%m}",
        "esik": ESIK_GUCLU, "asgari_ay": ASGARI_AY, "ufuk": UFUK,
        "epizot_sayisi": len(eps),
    }

    # ── 1. REEL gıda emtiası. Deflatör ABD TÜFE'si: nominal ölçmek, arz şokunu
    # ABD'nin kendi para politikasıyla karıştırırdı.
    abd_tufe = K["abd_tufe"].dropna()
    reel_gida = (K["emtia_gida"] / abd_tufe * 100.0).dropna()
    reel_gida_y = _yillik(reel_gida).dropna()
    S["reel_gida_son"] = _r(reel_gida_y.iloc[-1])
    S["nominal_gida_son"] = _r(_yillik(K["emtia_gida"]).dropna().iloc[-1])
    ep_kur = epizot_calismasi(reel_gida_y, eps)
    S["kuresel"] = ep_kur
    for a in ("olculen", "kosulsuz", "epizot_ortalama", "fark", "orneklem_bas", "orneklem_son"):
        S[f"kur_{a}"] = ep_kur.get(a)
    print(f"   küresel reel gıda: örneklem {ep_kur['orneklem_bas']}→{ep_kur['orneklem_son']}, "
          f"ölçülen epizot {ep_kur['olculen']}, epizot ort. {ep_kur.get('epizot_ortalama')} "
          f"vs koşulsuz {ep_kur.get('kosulsuz')} → fark {ep_kur.get('fark')}")

    # gecikme profili (kalıcılık yanlısı — yalnız gecikmenin YERİ için)
    oni_m = oni.reindex(reel_gida_y.index.union(oni.index)).interpolate(limit=1)
    c = capraz(oni_m, reel_gida_y, GEC_MAKS)
    if c:
        en = max(c, key=lambda d: abs(d["korelasyon"]))
        S["kur_capraz"] = c
        S["kur_en_iyi_gecikme"] = en["gecikme"]
        S["kur_en_iyi_kor"] = en["korelasyon"]
        S["kur_capraz_n"] = en["n"]
        print(f"   küresel gecikme profili: en güçlü {en['gecikme']} ay, "
              f"r={en['korelasyon']}, n={en['n']}")

    # ── 2. ÜRÜN KIRILIMI
    tamam = [e for e in eps if not e.get("suruyor")]
    son_ep = tamam[-1] if tamam else None
    if son_ep is not None:
        S["son_epizot_zirve"] = f"{son_ep['zirve']:%Y-%m}"
        S["son_epizot_oni"] = _r(son_ep["zirve_deger"])
    kirilim = []
    for ad, (baslik, gerekce) in {**URUNLER,
                                  **{k: (v, "") for k, v in TOPLU.items()}}.items():
        if ad not in K.columns:
            uyar(f"ürün serisi yok, kırılımda atlanıyor: {ad}")
            continue
        reel = (K[ad] / abd_tufe * 100.0).dropna()
        e = epizot_calismasi(_yillik(reel).dropna(), eps)
        if e["olculen"] < ASGARI_EPIZOT:
            uyar(f"{ad}: ölçülebilir epizot {e['olculen']} < {ASGARI_EPIZOT}, "
                 "kırılımda hüküm yok")
        # SON EPİZODUN kendi hikâyesi. Basında "kakao %250 arttı" gibi
        # cümleler dolaşıyor; onları alıntılamak yerine KENDİ serimizden
        # ölçüyoruz: son tamamlanmış epizodun zirvesinden sonraki 18 ayda
        # nominal fiyatın zirveye çıkışı, aynı andaki seviyeye göre.
        tepe = None
        if son_ep is not None:
            pen = K[ad].loc[son_ep["zirve"]:son_ep["zirve"] + pd.DateOffset(months=UFUK)]
            pen = pen.dropna()
            if len(pen) >= 6 and pen.iloc[0]:
                tepe = _r((pen.max() / pen.iloc[0] - 1.0) * 100.0, 1)
        kirilim.append({"ad": ad, "baslik": baslik, "gerekce": gerekce,
                        "toplu": ad in TOPLU, "olculen": e["olculen"],
                        "epizot_ortalama": e.get("epizot_ortalama"),
                        "kosulsuz": e.get("kosulsuz"), "fark": e.get("fark"),
                        "son_epizot_tepe": tepe,
                        "bas": e.get("orneklem_bas")})
    kirilim.sort(key=lambda d: (d["fark"] is None, -(d["fark"] or 0)))
    S["kirilim"] = kirilim
    print("   ürün kırılımı (epizot sonrası reel yıllık − koşulsuz, puan):")
    for d in kirilim:
        print(f"     {d['baslik']:<34}{str(d['fark']):>9}  "
              f"(n_epizot {d['olculen']}, {d['bas']}, son epizot tepe "
              f"{d['son_epizot_tepe']}%)")

    # ── 1b. DEFLATÖRSÜZ SAĞLAMLIK: gıda − metal
    if KONTROL in K.columns:
        gor_emtia = (_yillik(K["emtia_gida"]) - _yillik(K[KONTROL])).dropna()
        e = epizot_calismasi(gor_emtia, eps)
        S["gor_emtia"] = e
        for a in ("olculen", "kosulsuz", "epizot_ortalama", "fark"):
            S[f"gor_emtia_{a}"] = e.get(a)
        S["gor_emtia_son"] = _r(gor_emtia.iloc[-1])
        print(f"   gıda−metal (deflatörsüz): epizot ort. {e.get('epizot_ortalama')} "
              f"vs koşulsuz {e.get('kosulsuz')} → fark {e.get('fark')} "
              f"(n_epizot {e['olculen']})")

    # ── 3. ABD: Türkiye ile AYNI ölçüt
    abd_y = {k: _yillik(K[k]).dropna() for k in ("abd_tufe", "abd_gida", "abd_cekirdek")
             if k in K.columns}
    if "abd_gida" in abd_y and "abd_tufe" in abd_y:
        abd_gor = (abd_y["abd_gida"] - abd_y["abd_tufe"]).dropna()
        e = epizot_calismasi(abd_gor, eps)
        S["abd"] = e
        for a in ("olculen", "kosulsuz", "epizot_ortalama", "fark", "orneklem_bas"):
            S[f"abd_{a}"] = e.get(a)
        S["abd_goreceli_son"] = _r(abd_gor.iloc[-1])
        S["abd_gida_12a"] = _r(abd_y["abd_gida"].iloc[-1])
        S["abd_tufe_12a"] = _r(abd_y["abd_tufe"].iloc[-1])
        print(f"   ABD göreceli gıda: ölçülen epizot {e['olculen']}, "
              f"epizot ort. {e.get('epizot_ortalama')} vs koşulsuz {e.get('kosulsuz')} "
              f"→ fark {e.get('fark')}")

    # geçiş katsayıları: manşet aylık ~ gıda aylık (Türkiye ile aynı denklem)
    g = _regres(_aylik(K["abd_gida"]), _aylik(K["abd_tufe"]))
    if g:
        S["abd_gecis_beta"], S["abd_gecis_r2"], S["abd_gecis_n"] = g["beta"], g["r2"], g["n"]
        print(f"   ABD geçiş katsayısı β={g['beta']} (R²={g['r2']}, n={g['n']})")

    # ÜÇ EKONOMİ, TEK DENKLEM: manşet yıllık ~ gıda yıllık. Aylık geçiş
    # katsayısı Euro Bölgesi için hesaplanamıyor (ECB serileri endeks değil,
    # zaten yıllık % değişim). Üçünü karşılaştırabilmek için hepsinde YILLIK
    # oran regresyonu ayrıca kurulur — farklı denklemlerle kurulan katsayıları
    # yan yana koymak, karşılaştırma değil kılık değiştirmiş uydurma olurdu.
    t_y = {k: _yillik(tufe[k]).dropna() for k in ("tufe", "gida") if k in tufe.columns}
    yillik_setleri = {}
    if "gida" in t_y and "tufe" in t_y:
        yillik_setleri["tr"] = (t_y["gida"], t_y["tufe"])
    if "abd_gida" in abd_y and "abd_tufe" in abd_y:
        yillik_setleri["abd"] = (abd_y["abd_gida"], abd_y["abd_tufe"])
    if "ea_gida_12a" in K.columns and "ea_tufe_12a" in K.columns:
        yillik_setleri["ea"] = (K["ea_gida_12a"].dropna(), K["ea_tufe_12a"].dropna())
    for ad, (gx, hy) in yillik_setleri.items():
        d = _regres(gx, hy)
        if not d:
            continue
        S[f"gecis_yillik_{ad}_beta"] = d["beta"]
        S[f"gecis_yillik_{ad}_r2"] = d["r2"]
        S[f"gecis_yillik_{ad}_n"] = d["n"]
        print(f"   yıllık geçiş [{ad}]: β={d['beta']} (R²={d['r2']}, n={d['n']})")

    # şok ÇEKİRDEĞE ulaşıyor mu — iki ülke, aynı denklem
    if "abd_cekirdek" in K.columns:
        cc = _en_iyi_gecikmeli(_aylik(K["abd_gida"]), _aylik(K["abd_cekirdek"]), 12)
        if cc:
            S["abd_cekirdek_beta"] = cc["beta"]
            S["abd_cekirdek_r2"] = cc["r2"]
            S["abd_cekirdek_gecikme"] = cc["gecikme"]
            S["abd_cekirdek_n"] = cc["n"]
            print(f"   ABD gıda→çekirdek: β={cc['beta']} (R²={cc['r2']}, "
                  f"gecikme {cc['gecikme']} ay, n={cc['n']})")
    if "cekirdek_c" in tufe.columns:
        tc = _en_iyi_gecikmeli(_aylik(tufe["gida"]), _aylik(tufe["cekirdek_c"]), 12)
        if tc:
            S["tr_cekirdek_beta"] = tc["beta"]
            S["tr_cekirdek_r2"] = tc["r2"]
            S["tr_cekirdek_gecikme"] = tc["gecikme"]
            S["tr_cekirdek_n"] = tc["n"]
            print(f"   TR gıda→çekirdek: β={tc['beta']} (R²={tc['r2']}, "
                  f"gecikme {tc['gecikme']} ay, n={tc['n']})")

    # ── 3b. EURO BÖLGESİ: üçüncü ölçek. ECB serileri zaten YILLIK % değişim
    # olarak geliyor; endeksten türetilmez, olduğu gibi farkı alınır.
    if "ea_gida_12a" in K.columns and "ea_tufe_12a" in K.columns:
        ea_gor = (K["ea_gida_12a"] - K["ea_tufe_12a"]).dropna()
        e = epizot_calismasi(ea_gor, eps)
        S["ea"] = e
        for a in ("olculen", "kosulsuz", "epizot_ortalama", "fark", "orneklem_bas"):
            S[f"ea_{a}"] = e.get(a)
        S["ea_goreceli_son"] = _r(ea_gor.iloc[-1])
        S["ea_gida_son"] = _r(K["ea_gida_12a"].dropna().iloc[-1])
        S["ea_tufe_son"] = _r(K["ea_tufe_12a"].dropna().iloc[-1])
        print(f"   Euro Bölgesi göreceli gıda: ölçülen epizot {e['olculen']}, "
              f"epizot ort. {e.get('epizot_ortalama')} vs koşulsuz "
              f"{e.get('kosulsuz')} → fark {e.get('fark')}")

    # ── 4. FED PATİKASI — betimsel, ortalaması ALINMAZ
    if "faiz_abd" in K.columns:
        ff = K["faiz_abd"].dropna()
        yol = []
        for e in eps:
            if e.get("suruyor"):
                continue
            z, son = e["zirve"], e["zirve"] + pd.DateOffset(months=UFUK)
            if z not in ff.index:
                continue
            pen = ff.loc[z:son]
            if len(pen) < 12:
                continue
            yol.append({"zirve": f"{z:%Y-%m}", "faiz_zirve": _r(pen.iloc[0]),
                        "faiz_18ay": _r(pen.iloc[-1]),
                        "degisim": _r(pen.iloc[-1] - pen.iloc[0]),
                        "ay": int(len(pen))})
        S["fed_yol"] = yol
        S["fed_olculen"] = len(yol)
        print("   Fed patikası (zirve → +18 ay, puan):")
        for d in yol:
            print(f"     {d['zirve']}  {d['faiz_zirve']:>6} → {d['faiz_18ay']:>6}  "
                  f"({d['degisim']:+})")
        # Kıyas noktası: aynı uzunlukta RASTGELE olmayan bir pencere değil,
        # bütün örneklemdeki 18 aylık değişimlerin ortalaması. Epizot
        # pencerelerinin "olağandışı" olup olmadığı ancak buna karşı okunur.
        d18 = (ff.shift(-UFUK) - ff).dropna()
        if len(d18) > 60:
            S["fed_kosulsuz_18ay"] = _r(d18.mean())
            print(f"     koşulsuz 18 aylık değişim ortalaması: "
                  f"{S['fed_kosulsuz_18ay']:+} puan (n={len(d18)})")
        S["fed_hukum"] = "nedensel_degil"
        S["fed_hukum_metin"] = (
            "Bu sayıların ortalaması ALINMAZ. Dört pencerenin her biri El Niño'yla "
            "ilgisi olmayan bir şeyin gölgesindedir: 1983 Volcker dezenflasyonu, "
            "1998 Asya krizi ve LTCM, 2016 faiz artırım döngüsünün ilk adımı, "
            "2024 Kovid sonrası indirim döngüsü. Tablo, El Niño'nun politika "
            "faizini ne yaptığını DEĞİL, epizotların hangi rejimlere denk "
            "geldiğini gösterir.")

    # ── 5. KÜRESEL → YEREL GEÇİŞ (yazının en zayıf halkasıydı, artık ölçülü)
    gec = {}
    if "abd_gida" in abd_y:
        d = _en_iyi_gecikmeli(reel_gida_y, abd_y["abd_gida"])
        if d:
            gec["abd"] = d
            S["gecis_abd_beta"], S["gecis_abd_r2"] = d["beta"], d["r2"]
            S["gecis_abd_gecikme"], S["gecis_abd_n"] = d["gecikme"], d["n"]
            print(f"   küresel→ABD gıda TÜFE'si: β={d['beta']} (R²={d['r2']}, "
                  f"gecikme {d['gecikme']} ay, n={d['n']})")
    tr_gor = (_yillik(tufe["gida"]) - _yillik(tufe["tufe"])).dropna()
    d = _en_iyi_gecikmeli(reel_gida_y, tr_gor)
    if d:
        gec["tr"] = d
        S["gecis_tr_beta"], S["gecis_tr_r2"] = d["beta"], d["r2"]
        S["gecis_tr_gecikme"], S["gecis_tr_n"] = d["gecikme"], d["n"]
        print(f"   küresel→TR göreceli gıda: β={d['beta']} (R²={d['r2']}, "
              f"gecikme {d['gecikme']} ay, n={d['n']})")
    S["gecis"] = gec

    # ── HÜKÜM. Aynı eşik, Türkiye ölçümüyle aynı gerekçe.
    n = S.get("kur_olculen") or 0
    if n >= ASGARI_EPIZOT:
        S["kur_hukum"] = "olculebilir"
        S["kur_hukum_metin"] = (
            f"Küresel gıda emtiasında {n} güçlü El Niño epizodu ölçülebiliyor "
            f"(örneklem {S.get('kur_orneklem_bas')}'den başlıyor). Türkiye'de bu "
            "sayı ikiydi; hüküm kurulamamasının sebebi kanalın yokluğu değil, "
            "yerel örneklemin kısalığıydı.")
    else:
        S["kur_hukum"] = "yetersiz"
        S["kur_hukum_metin"] = (
            f"Küresel tarafta da yalnız {n} ölçülebilir epizot var; yön hakkında "
            "hüküm kurulmuyor.")
    print(f"   KÜRESEL HÜKÜM: {S['kur_hukum']}")

    # grafik tarihçesi (05 numaralı şekil)
    S["reel_gida_tarihce"] = [{"ay": f"{t:%Y-%m}", "deger": _r(v)}
                              for t, v in reel_gida_y.items()]

    S["uyarilar"] = _UYARI
    S["yontem_notu"] = (
        "Emtia fiyatları ABD TÜFE'siyle deflate edilir (reel). Epizot tanımı, "
        "pencere uzunluğu ve göreceli enflasyon tanımı Türkiye ölçümüyle "
        "AYNIDIR; iki taraf aynı cetvelle ölçülmezse karşılaştırma anlamsız "
        "olurdu. Fed patikası betimseldir ve ortalaması alınmaz.")
    cikti.write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── küresel ölçüm yazıldı: {cikti}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
