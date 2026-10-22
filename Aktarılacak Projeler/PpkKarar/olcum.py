#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""22 EKİM 2026 PPK KARARI — yazının bütün sayılarını üreten ölçüm katmanı.

GİRDİLER DONDURULUR. Yazı yayımlandığı günün metnidir (karar 08.09.2026) ve
sayıları MDX'e elle yazılır; o sayıların arkasındaki girdi bir sonraki veri
koşusunda değişir. Bu yüzden betik canlı dosyaları BİR KEZ okur, kullandığı
parçayı `veri/<çıpa>/` altına sıkıştırılmış kopya olarak yazar (gzip, mtime 0)
ve bütün hesabı o kopyadan yapar. Kapı (`dogrula.py`) yalnız kopyayı ve ölçüm
dosyasını okur; yarın tazelenen bir pano bu yazının kapısını düşürmez.

  ppk_<no>-TR.json        karar ve özet metinleri (bulten/veri/ppk arşivinden)
  karar_tablosu.json      2016'dan bugüne her faiz kararı: tarih, oran, değişim,
                          "Adımların büyüklüğü" kalıbı ve cümlesi, aranan ifadeler
  dibs_ozet.json          DİBS sıfır kuponlu eğri özeti (21.10 kapanışı)
  fonlama.csv             2026 gecelik fonlama tablosu (TLREF, koridor, AOFM)
  enflasyon_ozet.json     TÜFE özeti (Eylül 2026)
  pka_toplanti.json       Piyasa Katılımcıları Anketi, toplantı toplantı politika faizi
                          beklentisi (EVDS, bulut keşif koşusu; veri/kesif/ altında künyesiyle)
  takvim.json             TCMB toplantı ve yayım günleri (bulten/takvim_elle.json, kaynak
                          "TCMB 2026 Para Politikası metni, Ek 2")
  eylul_egri.json         DİBS hattının metrik tablosundan dört günün satırı (28.08, 04.09,
                          10.09, 16.09): 31 Ağustos, 6, 10 ve 17 Eylül yazılarının eğri
                          karşılaştırmasına yazılan düzeltmenin girdisi

CANLI KAYNAK BİR KEZ DONDURULUR. Pano özetleri, fonlama tablosu ve takvim her veri
koşusunda değişir; donmuş kopyası varsa betik onu YENİDEN YAZMAZ (`--yeniden` ile
bilerek yazılır). Arşivden türeyen dosyalar (karar metinleri, karar tablosu) ve depodaki
keşif kaydı değişmez kaynaklardan kurulduğu için her koşuda yeniden üretilir.

KONVANSİYON BU YAZININ ASIL SORUSU. Eğri getirileri ACT/365 yıllık BİLEŞİK,
politika faizi bir haftalık BASİT faizdir. İkisi doğrudan çıkarılırsa yaklaşık
7,6 puanlık bir konvansiyon farkı "vade primi" ya da "fiyatlanmayan indirim"
gibi okunur. Bu yüzden her karşılaştırma tek konvansiyonda yapılır: politika
faizi haftalık bileşiklenerek eğrinin diline çevrilir, eğri getirisi de aynı
kuralla "haftalık repo eşdeğeri" bir basit faize çevrilir. Formüller tek yerde:
`bilesik()` ve `haftalik_esdeger()`.

Koşum:  python3 olcum.py
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIPA = "2026-10-22"
VERI = BURASI / "veri" / CIPA
ARSIV = KOK / "bulten" / "veri" / "ppk"
DIBS = KOK / "site/public/projeler/dibs-verim-egrisi/ozet.json"
ENF = KOK / "site/public/projeler/enflasyon/ozet.json"
FONLAMA = KOK / "Aktarılacak Projeler/Fonlama/data/metrik.csv"
KESIF = BURASI / "veri" / "kesif" / "pka_toplanti_2026-10-22.json"
TAKVIM = KOK / "bulten" / "takvim_elle.json"
DIBS_METRIK = KOK / "Aktarılacak Projeler/DIBS/data/metrik.csv"
CANLI = ("dibs_ozet.json", "enflasyon_ozet.json", "fonlama.csv", "takvim.json", "eylul_egri.json")
# Düzeltilen yazıların veri günü (yazının kullandığı kapanış) → kısa ad. 22 Ekim için bir
# sonraki toplantı ve o toplantı için beklentiyi taşıyan anket ayı (ankette "ikinci toplantı").
DUZELTILEN = {"2026-08-28": "e0828", "2026-09-04": "e0904", "2026-09-10": "e0910", "2026-09-16": "e0916"}
EKIM_ANKETI = {"e0910": "2026-8", "e0916": "2026-9"}

BUGUN_NO, ONCEKI_NO = 45, 38          # 2026-45 (22.10) · 2026-38 (10.09)
OCAK_NO = 1                           # 2026-01 (22.01): bir önceki İNDİRİM metni
VADE_GUN, GUN = 7, 365                # politika faizi: bir hafta vadeli repo, ACT/365
KALIP = re.compile(r"(?i)ad[ıi]mlar[ıi]n b[üu]y[üu]kl[üu][ğg][üu]")
# Arşivde geçişi sorulan ifadeler (sayılar değil kalıplar). Arama BİREBİR dizgedir:
# anlamca yakın bir yazımı yakalamaz, o yüzden bilinen yakın yazımlar da listede durur.
IFADELER = [
    "zamanlaması",
    "gerilemeyi teyit etmektedir",
    "zayıf seyrin devam ettiğini göstermektedir",
    "zayıf seyrin sürdüğüne işaret etmektedir",
    "canlılığını koruyan jeopolitik gerilimler",
    "yukarı yönlü riskler sürmektedir",
    "ihtiyatlı duruşunu vurgulamıştır",
    "belirgin ve kalıcı bir bozulma",
    "görünümünde belirgin ve kalıcı bir bozulma olması durumunda",
    "ara hedeflerden belirgin bir biçimde ayrışması",
    "tüm para politikası araçları etkili şekilde kullanılacaktır",
    "duruşu sıkılaştırılacaktır",
    "Para politikası kararları enflasyon görünümü odaklı",
]


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 2, arti: bool = False) -> str:
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not sifir) else s


def metin_bicimi(x: float, b: int, birim: str, arti: bool = False) -> str:
    if birim == "%":
        s = sayi(abs(x), b)
        sifir = float(s.replace(".", "").replace(",", ".")) == 0
        if x < 0 and not sifir:
            return "−%" + s
        return ("+%" if (arti and x > 0 and not sifir) else "%") + s
    if birim in ("puan", "bp", "gün"):
        return f"{sayi(x, b, arti)} {birim}"
    return sayi(x, b, arti)


D: dict[str, dict] = {}


def koy(ad: str, deger: float, b: int, birim: str = "", arti: bool = False, not_: str = "") -> float:
    D[ad] = {"deger": float(deger), "b": b, "birim": birim, "arti": arti,
             "metin": metin_bicimi(float(deger), b, birim, arti), "not": not_}
    return float(deger)


# ─────────────────────────────────────────────── konvansiyon
def bilesik(basit: float) -> float:
    """Bir haftalık BASİT faiz (yüzde) → aynı faizle bir yıl çevrilen repo'nun yıllık BİLEŞİK getirisi."""
    return ((1 + basit / 100 * VADE_GUN / GUN) ** (GUN / VADE_GUN) - 1) * 100


def haftalik_esdeger(yillik_bilesik: float) -> float:
    """Yıllık BİLEŞİK getiri (yüzde) → aynı getiriyi veren sabit bir haftalık BASİT repo faizi."""
    return ((1 + yillik_bilesik / 100) ** (VADE_GUN / GUN) - 1) * GUN / VADE_GUN * 100


def patika_getirisi(bas: float, son: float, hafta: int = 52) -> float:
    """BASİT faizin `bas`tan `son`a doğrusal indiği bir yıl boyunca haftalık çevrilen repo'nun
    yıllık BİLEŞİK getirisi. Doğrusal iniş bir VARSAYIMDIR: anket yalnız uç noktayı sorar."""
    g = 1.0
    for k in range(hafta):
        r = bas + (son - bas) * (k + 0.5) / hafta
        g *= 1 + r / 100 * VADE_GUN / GUN
    # 52 hafta 364 gündür; üs, sabit faizde `bilesik()` ile aynı sonucu verecek biçimde bir yıla tamamlar.
    return (g ** (GUN / VADE_GUN / hafta) - 1) * 100


# ─────────────────────────────────────────────── dondurma
def _yaz(ad: str, icerik: bytes) -> str:
    VERI.mkdir(parents=True, exist_ok=True)
    tampon = io.BytesIO()
    with gzip.GzipFile(fileobj=tampon, mode="wb", mtime=0) as g:
        g.write(icerik)
    (VERI / f"{ad}.gz").write_bytes(tampon.getvalue())
    return hashlib.sha256(icerik).hexdigest()


def _oku(ad: str) -> bytes:
    return gzip.decompress((VERI / f"{ad}.gz").read_bytes())


def _cumleler(p: str) -> list[str]:
    return [c for c in re.split(r"(?<=[.!?])\s+", p.strip()) if c]


def karar_tablosu() -> list[dict]:
    ks = []
    for yol in sorted(ARSIV.rglob("*-TR.json")):
        k = json.loads(yol.read_text(encoding="utf-8"))
        if k.get("tur") != "karar" or not k.get("tarih") or k.get("politika") is None:
            continue
        if k["tarih"] > CIPA:
            continue
        metin = " ".join(k["paragraflar"])
        kalip = [c for c in _cumleler(metin) if KALIP.search(c)]
        ks.append({"tarih": k["tarih"], "yil": k["yil"], "no": k["no"], "politika": k["politika"],
                   "kalip": bool(kalip), "kalip_cumle": kalip[0] if kalip else "",
                   "ifadeler": [i for i in IFADELER if i in metin],
                   "kaynak": str(yol.relative_to(KOK))})
    ks.sort(key=lambda k: k["tarih"])
    for i, k in enumerate(ks):
        k["degisim"] = None if i == 0 else round(k["politika"] - ks[i - 1]["politika"], 4)
    for i, k in enumerate(ks):
        k["sonraki_degisim"] = ks[i + 1]["degisim"] if i + 1 < len(ks) else None
    return ks


def _takvim_kesiti() -> bytes:
    """TCMB toplantı ve yayım günleri, çıpadan 2027 Ocak sonuna (elle tutulan resmî takvimin kesin kayıtları)."""
    t = json.loads(TAKVIM.read_text(encoding="utf-8"))
    kayit = [k for k in t["kesin"] if k.get("ulke") == "TR" and "TCMB" in k.get("olay", "")
             and CIPA <= k["tarih"] <= "2027-01-31"]
    return json.dumps({"kaynak": str(TAKVIM.relative_to(KOK)), "son_dogrulama": t.get("_son_dogrulama"),
                       "kayitlar": kayit}, ensure_ascii=False, indent=1).encode("utf-8")


def dondur(yeniden: bool = False) -> dict:
    eski = {}
    if (VERI / "kunye.json").exists():
        eski = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))["dosyalar"]
    kunye = {}
    # Arşivden: karar ve özet metinleri. 2016-49 "zamanlaması"nın bir faiz kararındaki son önceki
    # geçişi; 2025-41 döngünün ilk indirimi; 2026-14 ve 2026-42 repo ihalelerine ara verilmesini
    # ve yeniden başlanmasını yazan toplantı özetleri (alıntı kaynakları).
    metinler = [(2026, n) for n in (BUGUN_NO, ONCEKI_NO, OCAK_NO, 12, 14, 17, 23, 28, 42)] + [(2025, 41), (2016, 49)]
    for yil, no in metinler:
        yol = ARSIV / str(yil) / f"{yil}-{no:02d}-TR.json"
        kunye[f"ppk_{yil}-{no:02d}-TR.json"] = {"kaynak": str(yol.relative_to(KOK)),
                                               "sha256": _yaz(f"ppk_{yil}-{no:02d}-TR.json", yol.read_bytes())}
    tablo = json.dumps(karar_tablosu(), ensure_ascii=False, indent=1).encode("utf-8")
    kunye["karar_tablosu.json"] = {"kaynak": "bulten/veri/ppk (2016–2026, TR faiz kararları)",
                                   "sha256": _yaz("karar_tablosu.json", tablo)}
    kunye["pka_toplanti.json"] = {"kaynak": str(KESIF.relative_to(KOK)),
                                  "sha256": _yaz("pka_toplanti.json", KESIF.read_bytes())}

    def canli(ad: str, kaynak: str, icerik) -> None:
        if not yeniden and ad in eski and (VERI / f"{ad}.gz").exists():
            kunye[ad] = eski[ad]                 # donmuş kopya kalır; canlı dosya bugün değişmiş olabilir
            return
        kunye[ad] = {"kaynak": kaynak, "sha256": _yaz(ad, icerik())}

    canli("dibs_ozet.json", str(DIBS.relative_to(KOK)), DIBS.read_bytes)
    canli("enflasyon_ozet.json", str(ENF.relative_to(KOK)), ENF.read_bytes)

    def fonlama_csv() -> bytes:
        M = pd.read_csv(FONLAMA, index_col=0, parse_dates=True)
        sut = ["tlref", "politika", "koridor_ust", "koridor_alt", "aofm", "aofm_gecerli"]
        return M.loc["2026-01-01":CIPA, sut].to_csv(float_format="%.6g").encode("utf-8")

    canli("fonlama.csv", str(FONLAMA.relative_to(KOK)) + " (2026, altı sütun)", fonlama_csv)
    canli("takvim.json", str(TAKVIM.relative_to(KOK)) + " (TCMB kayıtları, 22.10.2026–31.01.2027)", _takvim_kesiti)

    def eylul_egri() -> bytes:
        M = pd.read_csv(DIBS_METRIK, index_col=0, parse_dates=True)
        sut = ["n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y", "f_1y1y", "f_2y1y", "f_2y3y",
               "be_1y", "r1y", "r2y", "politika"]
        return json.dumps({g: {k: float(M.loc[g, k]) for k in sut} for g in DUZELTILEN},
                          ensure_ascii=False, indent=1).encode("utf-8")

    canli("eylul_egri.json", str(DIBS_METRIK.relative_to(KOK)) + " (dört günün satırı)", eylul_egri)
    (VERI / "kunye.json").write_text(json.dumps({"cipa": CIPA, "dosyalar": kunye}, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    return kunye


# ─────────────────────────────────────────────── ölçüm
def metin_olcumu(bugun: dict, onceki: dict, yil: list[dict]) -> dict:
    a, b = onceki["paragraflar"], bugun["paragraflar"]
    rol = {3: "kurul üyeleri", 4: "karar", 5: "teşhis", 6: "duruş", 7: "makroihtiyati", 8: "hedef", 9: "özet notu"}
    paragraflar = []
    # İçerik paragrafları 3–9'dur (1 başlık, 2 "Toplantıya Katılan Kurul Üyeleri" satırı); 10 Eylül
    # yazısı da duyuruyu bu yedi paragrafla saydı.
    for i, (x, y) in enumerate(zip(a, b), 1):
        if i in rol:
            paragraflar.append({"no": i, "rol": rol[i], "ayni": x == y})
    koy("paragraf_sayisi", len(paragraflar), 0)
    koy("degisen_paragraf", sum(1 for p in paragraflar if not p["ayni"]), 0)
    koy("ayni_paragraf", sum(1 for p in paragraflar if p["ayni"]), 0)
    cumle = {}
    for i, ad in ((5, "teshis"), (6, "durus")):
        ca, cb = _cumleler(a[i - 1]), _cumleler(b[i - 1])
        ayni = [c for c in cb if c in ca]
        koy(f"{ad}_cumle", len(cb), 0)
        koy(f"{ad}_ayni_cumle", len(ayni), 0)
        koy(f"{ad}_degisen_cumle", len(cb) - len(ayni), 0)
        cumle[ad] = {"onceki": ca, "bugun": cb, "ayni": ayni,
                     "yeni": [c for c in cb if c not in ca], "kalkan": [c for c in ca if c not in cb]}
    # 2026'da paragraf paragraf kaç geçişte değişti
    gecis = []
    for x, y in zip(yil, yil[1:]):
        gecis.append({"bas": x["tarih"], "son": y["tarih"],
                      "degisen": [rol[i] for i in range(3, 10) if x["paragraflar"][i - 1] != y["paragraflar"][i - 1]]})
    koy("gecis_sayisi", len(gecis), 0)
    for r in ("teşhis", "duruş", "kurul üyeleri", "karar", "makroihtiyati", "hedef", "özet notu"):
        anahtar = {"teşhis": "teshis", "duruş": "durus", "kurul üyeleri": "uye", "karar": "karar",
                   "makroihtiyati": "makro", "hedef": "hedef", "özet notu": "ozet"}[r]
        koy(f"gecis_{anahtar}", sum(1 for g in gecis if r in g["degisen"]), 0)
    # Duruş paragrafı bir önceki İNDİRİM metniyle (22 Ocak) karşılaştırıldığında
    ocak = next(x for x in yil if x["no"] == OCAK_NO)
    co, cb = _cumleler(ocak["paragraflar"][5]), _cumleler(b[5])
    koy("ocak_durus_cumle", len(co), 0)
    koy("ocak_durus_ayni", sum(1 for c in cb if c in co), 0)
    koy("ocak_durus_yeni", sum(1 for c in cb if c not in co), 0)
    cumle["durus_ocak"] = {"ocak": co, "bugun": cb, "ayni": [c for c in cb if c in co],
                           "yeni": [c for c in cb if c not in co], "kalkan": [c for c in co if c not in cb]}
    return {"paragraflar": paragraflar, "cumle": cumle, "gecis": gecis}


def arsiv_olcumu(ks: list[dict]) -> dict:
    def tur(k):
        d = k["degisim"]
        return None if d is None else ("indirim" if d < 0 else "artirim" if d > 0 else "sabit")
    sayim = {t: sum(1 for k in ks if tur(k) == t) for t in ("indirim", "sabit", "artirim")}
    koy("arsiv_karar", len(ks), 0)
    for t, n in sayim.items():
        koy(f"arsiv_{t}", n, 0)
    kalipli = [k for k in ks if k["kalip"]]
    koy("kalipli_karar", len(kalipli), 0)
    koy("kalipli_indirim", sum(1 for k in kalipli if tur(k) == "indirim"), 0)
    koy("kalipsiz_indirim", sayim["indirim"] - sum(1 for k in kalipli if tur(k) == "indirim"), 0)
    onceki = [k for k in kalipli if k["sonraki_degisim"] is not None]
    koy("kalipli_onceki", len(onceki), 0)
    koy("kalipli_sonraki_indirim", sum(1 for k in onceki if k["sonraki_degisim"] < 0), 0)
    koy("kalipli_sonraki_sabit", sum(1 for k in onceki if k["sonraki_degisim"] == 0), 0)
    ifade = {}
    for i in IFADELER:
        gecen = [k for k in ks if i in k["ifadeler"]]
        ifade[i] = {"sayi": len(gecen), "ilk": gecen[0]["tarih"] if gecen else None,
                    "tarihler": [k["tarih"] for k in gecen]}
    # 2025–2026 döngüsü: son artırımdan bugüne
    son_art = max(i for i, k in enumerate(ks) if tur(k) == "artirim")
    dongu = [{"tarih": k["tarih"], "politika": k["politika"], "degisim": k["degisim"]} for k in ks[son_art:]]
    koy("dongu_tepe", ks[son_art]["politika"], 1, "%")
    koy("dongu_toplam_puan", ks[-1]["politika"] - ks[son_art]["politika"], 1, "puan", arti=True)
    dongu_ind = [k for k in ks[son_art + 1:] if tur(k) == "indirim"]
    koy("dongu_indirim_sayisi", len(dongu_ind), 0)
    for i, k in enumerate(ks[son_art:], 1):                # döngü tablosunun satırları
        koy(f"dongu{i}_politika", k["politika"], 1, "%")
        koy(f"dongu{i}_degisim_bp", k["degisim"] * 100, 0, "bp", arti=True)
    for i, k in enumerate(kalipli, 1):                     # kalıp tablosunun satırları
        koy(f"kalip{i}_degisim_bp", k["degisim"] * 100, 0, "bp", arti=True)
        if k["sonraki_degisim"] is not None:
            koy(f"kalip{i}_sonraki_bp", k["sonraki_degisim"] * 100, 0, "bp", arti=True)
    # Sıkılaştırma cümlesi: döngünün indirimlerinde VAR MI ve KOŞULU nasıl yazılmış. Koşul tek bir
    # dizgeyle sayılırsa yazımı değişen aynı cümle "yok" görünür; bu yüzden fiil ve koşul ayrı sorulur.
    def kosul_yazimi(k):
        if "belirgin ve kalıcı bir bozulma" in k["ifadeler"] and "duruşu sıkılaştırılacaktır" in k["ifadeler"]:
            return "bozulma"
        if "ara hedeflerden belirgin bir biçimde ayrışması" in k["ifadeler"]:
            return "ara_hedef"
        if "tüm para politikası araçları etkili şekilde kullanılacaktır" in k["ifadeler"]:
            return "araclar"
        return "yok"
    koy("dongu_sikilastirma_cumlesi", sum(1 for k in dongu_ind if "duruşu sıkılaştırılacaktır" in k["ifadeler"]), 0)
    koy("dongu_ara_hedef_yazimi", sum(1 for k in dongu_ind if kosul_yazimi(k) == "ara_hedef"), 0)
    koy("dongu_ihtiyatli_indirim", sum(1 for k in dongu_ind if "ihtiyatlı duruşunu vurgulamıştır" in k["ifadeler"]), 0)
    # Taban oran: bir indirimden sonra gelen karar yine indirim mi ("önceki yönü tekrarla")
    sonrasi = [k for k in ks if tur(k) == "indirim" and k["sonraki_degisim"] is not None]
    koy("indirim_sonrasi_n", len(sonrasi), 0)
    koy("indirim_sonrasi_indirim", sum(1 for k in sonrasi if k["sonraki_degisim"] < 0), 0)
    koy("israr_orani", 100 * D["indirim_sonrasi_indirim"]["deger"] / len(sonrasi), 1, "%")
    koy("kalipli_sonraki_oran", 100 * D["kalipli_sonraki_indirim"]["deger"] / len(onceki), 1, "%")
    # "zamanlaması"nın 2016'daki geçişinden sonraki karar
    z = [k for k in ks if "zamanlaması" in k["ifadeler"] and k["tarih"] < CIPA]
    koy("zamanlama_2016_sonraki_bp", z[-1]["sonraki_degisim"] * 100, 0, "bp", arti=True)
    # Kalıbın fiil biçimleri: hangi kararda hangi yazım
    bicimler = {}
    for k in kalipli:
        f = re.search(r"(gözden geçirilecektir|gözden geçirilmektedir|belirlenecektir)", k["kalip_cumle"])
        bicimler.setdefault(f.group(1) if f else "?", []).append(k["tarih"])
    return {"ilk": ks[0]["tarih"], "son": ks[-1]["tarih"], "kalipli": [
        {"tarih": k["tarih"], "degisim": k["degisim"], "sonraki": k["sonraki_degisim"], "cumle": k["kalip_cumle"],
         "ihtiyatli": "ihtiyatlı duruşunu vurgulamıştır" in k["ifadeler"]}
        for k in kalipli], "ifade": ifade, "dongu": dongu,
        "dongu_kosul": [{"tarih": k["tarih"], "yazim": kosul_yazimi(k)} for k in dongu_ind],
        "kalip_bicimleri": bicimler, "son_artirim": ks[son_art]["tarih"], "zamanlama_2016": z[-1]["tarih"]}


def karar_olcumu(bugun: dict, onceki_karar: dict) -> dict:
    o = bugun["oranlar"]           # [önceki politika, yeni politika, önceki üst, yeni üst, önceki alt, yeni alt]
    koy("politika_onceki", o[0], 1, "%")
    koy("politika_yeni", o[1], 1, "%")
    koy("ust_onceki", o[2], 1, "%")
    koy("ust_yeni", o[3], 1, "%")
    koy("alt_onceki", o[4], 1, "%")
    koy("alt_yeni", o[5], 1, "%")
    koy("indirim_bp", (o[1] - o[0]) * 100, 0, "bp", arti=True)
    koy("koridor_genislik", o[3] - o[5], 1, "puan")
    koy("ust_mesafe", o[3] - o[1], 1, "puan")
    koy("alt_mesafe", o[1] - o[5], 1, "puan")
    gun = (date.fromisoformat(bugun["tarih"]) - date.fromisoformat(onceki_karar["tarih"])).days
    koy("indirimsiz_gun", gun, 0, "gün")
    return {"onceki_indirim": onceki_karar["tarih"]}


def egri_olcumu(d: dict) -> dict:
    koy("politika_bilesik_onceki", bilesik(D["politika_onceki"]["deger"]), 2, "%")
    koy("politika_bilesik_yeni", bilesik(D["politika_yeni"]["deger"]), 2, "%")
    koy("bilesik_indirim_bp", (D["politika_bilesik_yeni"]["deger"] - D["politika_bilesik_onceki"]["deger"]) * 100,
        0, "bp", arti=True)
    koy("konvansiyon_farki", D["politika_bilesik_onceki"]["deger"] - D["politika_onceki"]["deger"], 2, "puan")
    for v in ("3a", "6a", "1y", "2y", "3y", "5y", "7y"):
        y = koy(f"spot_{v}", d[f"spot_{v}"], 2, "%")
        koy(f"ima_{v}", haftalik_esdeger(y), 2, "%")
        koy(f"basit_fark_{v}", (y - D["politika_onceki"]["deger"]) * 100, 0, "bp", arti=True)
        koy(f"bilesik_fark_{v}", (y - D["politika_bilesik_onceki"]["deger"]) * 100, 0, "bp", arti=True)
    for v in ("1y1y", "2y1y"):
        y = koy(f"fwd_{v}", d[f"forward_{v}"], 2, "%")
        koy(f"ima_fwd_{v}", haftalik_esdeger(y), 2, "%")
    for k in ("pka_faiz_12a", "pka_faiz_24a", "pka_12a", "pka_24a"):
        koy(k, d[k], 2, "%")
    koy("pka_katilimci", d["pka_katilimci"], 0)
    # ikinci yıl: anketin 12 ve 24 ay uçları arasında doğrusal patika — VARSAYIM, metinde öyle yazılır
    p1, p2 = d["pka_faiz_12a"], d["pka_faiz_24a"]
    koy("anket_ort_2y", (p1 + p2) / 2, 2, "%")
    koy("fark_2y_ima_anket", D["ima_fwd_1y1y"]["deger"] - D["anket_ort_2y"]["deger"], 2, "puan", arti=True)
    # Yıl içi ileri oranlar: 0–3 ay, 3–6 ay, 6–12 ay (spotlardan; haftalık repo karşılığına çevrilir)
    s3, s6, s1 = (d[f"spot_{v}"] / 100 for v in ("3a", "6a", "1y"))
    for ad, f in (("3a6a", ((1 + s6) ** 0.5 / (1 + s3) ** 0.25) ** (1 / 0.25) - 1),
                  ("6a1y", ((1 + s1) / (1 + s6) ** 0.5) ** (1 / 0.5) - 1)):
        y = koy(f"fwd_{ad}", f * 100, 2, "%")
        koy(f"ima_fwd_{ad}", haftalik_esdeger(y), 2, "%")
    for k, ad in (("kiyas_1ay_1y_degisim_bp", "ay_1y"), ("kiyas_1ay_2y_degisim_bp", "ay_2y"),
                  ("kiyas_3ay_1y_degisim_bp", "ceyrek_1y"), ("kiyas_3ay_2y_degisim_bp", "ceyrek_2y")):
        koy(f"degisim_{ad}", d[k], 0, "bp", arti=True)
    koy("reel_ileri", d["reel_ileri"], 2, "%")
    koy("reel_ileri_2y", d["reel_ileri_2y"], 2, "%")
    koy("reel_geriye", d["reel_geriye"], 2, "%")
    koy("reel_tufex_1y", d["reel_egri_1y"], 2, "%")
    koy("reel_tufex_2y", d["reel_egri_2y"], 2, "%")
    koy("basabas_1y", d["basabas_1y"], 2, "%")
    koy("basabas_2y", d["basabas_2y"], 2, "%")
    koy("basabas_anket_fark", d["basabas_1y"] - d["pka_12a"], 2, "puan")
    koy("tlref_bilesik", d["tlref_bilesik"], 2, "%")
    # Politika faizinin reel karşılığı, Ekim anketinin 12 ay sonrası TÜFE beklentisiyle: ilan edildiği
    # hâliyle ve bir yıl çevrilen haftalık reponun yıllık getirisiyle (bileşik) — iki tanım iki sayı verir.
    pi = d["pka_12a"] / 100
    for ad, i in (("ilan_onceki", D["politika_onceki"]["deger"]), ("ilan_yeni", D["politika_yeni"]["deger"]),
                  ("bilesik_onceki", D["politika_bilesik_onceki"]["deger"]),
                  ("bilesik_yeni", D["politika_bilesik_yeni"]["deger"])):
        koy(f"reel_pol_{ad}", ((1 + i / 100) / (1 + pi) - 1) * 100, 2, "%")
    return {"egri_tarihi": d["_tarih"], "anket_ayi": d["pka_faiz_12a_ay_ad"], "kiyas_1ay": d["kiyas_1ay"],
            "kiyas_3ay": d["kiyas_3ay"]}


def anket_olcumu(pka: dict, takvim: dict, d: dict) -> dict:
    """Ekim anketinin toplantı toplantı politika faizi beklentisi: sürpriz ve yıl içi patika.

    Patika günlük kurulur: çıpadan (eğri günü) ilk kararın geçerli olduğu güne kadar eski faiz,
    sonra ilk, ikinci ve üçüncü toplantının beklentisi; üçüncü toplantıdan 12 ay ucuna DOĞRUSAL
    ara değer (VARSAYIM — anket aradaki toplantıları sormuyor). Toplantı günleri resmî takvimden;
    karar ertesi gün geçerli sayılır."""
    from datetime import timedelta
    satirlar = [s.split(";") for s in pka["csv"].strip().splitlines()]
    bas, govde = satirlar[0], satirlar[1:]
    ay = {r[0]: dict(zip(bas[1:], r[1:])) for r in govde}["2026-10"]
    if abs(float(ay["faiz_12a"]) - d["pka_faiz_12a"]) > 1e-9 or abs(float(ay["faiz_24a"]) - d["pka_faiz_24a"]) > 1e-9:
        raise SystemExit("anket kaydı DİBS özetindeki Ekim anketiyle aynı değil (12/24 ay ayrışıyor)")
    koy("anket_ilk", float(ay["ilk_toplanti"]), 2, "%")
    koy("anket_ikinci", float(ay["ikinci_toplanti"]), 2, "%")
    koy("anket_ucuncu", float(ay["ucuncu_toplanti"]), 2, "%")
    koy("anket_yilsonu", float(ay["yilsonu"]), 2, "%")
    koy("surpriz_bp", (D["politika_yeni"]["deger"] - D["anket_ilk"]["deger"]) * 100, 0, "bp", arti=True)
    koy("anket_aralik_bp", (D["anket_ikinci"]["deger"] - D["anket_ilk"]["deger"]) * 100, 0, "bp", arti=True)
    kararlar = sorted(k["tarih"] for k in takvim["kayitlar"] if "PPK faiz kararı" in k["olay"])
    if kararlar[0] != CIPA or len(kararlar) < 3:
        raise SystemExit(f"takvim beklenen üç kararı taşımıyor: {kararlar}")
    t0 = date(*map(int, reversed(d["_tarih"].split("."))))
    gecerli = [date.fromisoformat(t) + timedelta(days=1) for t in kararlar[:3]]
    beklenti = [D["anket_ilk"]["deger"], D["anket_ikinci"]["deger"], D["anket_ucuncu"]["deger"]]
    t12 = t0 + timedelta(days=365)

    def oran(g: date) -> float:
        if g < gecerli[0]:
            return D["politika_onceki"]["deger"]
        if g < gecerli[1]:
            return beklenti[0]
        if g < gecerli[2]:
            return beklenti[1]
        w = (g - gecerli[2]).days / (t12 - gecerli[2]).days
        return beklenti[2] + (d["pka_faiz_12a"] - beklenti[2]) * w

    gunluk = [oran(t0 + timedelta(days=i)) for i in range(365)]
    ort = lambda a, b: sum(gunluk[a:b]) / (b - a)                       # noqa: E731
    koy("anket_yol_3a", ort(0, 91), 2, "%")
    koy("anket_yol_3a6a", ort(91, 182), 2, "%")
    koy("anket_yol_6a1y", ort(182, 365), 2, "%")
    koy("anket_yol_1y", ort(0, 365), 2, "%")
    for ad, egri in (("3a", "ima_3a"), ("3a6a", "ima_fwd_3a6a"), ("6a1y", "ima_fwd_6a1y"), ("1y", "ima_1y")):
        koy(f"makas_{ad}_bp", (D[egri]["deger"] - D[f"anket_yol_{ad}"]["deger"]) * 100, 0, "bp", arti=True)
    koy("fark_1y_yol", D["ima_1y"]["deger"] - D["anket_yol_1y"]["deger"], 2, "puan", arti=True)
    koy("makas_2y_bp", D["fark_2y_ima_anket"]["deger"] * 100, 0, "bp", arti=True)
    # 3 aylık düğüm saf bir faiz beklentisi olsaydı: karar beklendiği gibi gelir ve 10 Aralık'a kadar
    # sürerse, kalan günlerde faizin ne olması gerekirdi.
    n0, n1 = (gecerli[0] - t0).days, (gecerli[1] - gecerli[0]).days
    x = (91 * D["ima_3a"]["deger"] - n0 * D["politika_onceki"]["deger"] - n1 * beklenti[0]) / (91 - n0 - n1)
    koy("ima_3a_aralik_sonrasi", x, 2, "%")
    return {"anket_ayi": "2026-10", "kararlar": kararlar, "gecerli": [g.isoformat() for g in gecerli],
            "gun": {"eski": n0, "ilk": n1, "ikinci": 91 - n0 - n1}, "t12": t12.isoformat(),
            "varsayim": "üçüncü toplantıdan 12 ay ucuna doğrusal ara değer"}


def fonlama_olcumu(M: pd.DataFrame) -> dict:
    G = M[M["tlref"].notna()]
    mesafe = pd.DataFrame({c: (G["tlref"] - G[c]).abs() for c in ("politika", "koridor_ust", "koridor_alt")})
    cipa = mesafe.idxmin(axis=1)
    blok = (cipa != cipa.shift()).cumsum()
    bloklar = []
    for _, x in cipa.groupby(blok):
        idx = x.index
        tl = G.loc[idx, "tlref"]
        bloklar.append({"cipa": str(x.iloc[0]), "bas": idx[0].strftime("%d.%m.%Y"), "son": idx[-1].strftime("%d.%m.%Y"),
                        "gun": len(idx), "tlref_ort": round(float(tl.mean()), 2),
                        "makas": round(float((tl - G.loc[idx, "politika"]).mean()), 2)})
    for i, b in enumerate(bloklar, 1):
        koy(f"blok{i}_gun", b["gun"], 0, "gün")
        koy(f"blok{i}_tlref", b["tlref_ort"], 2, "%")
        koy(f"blok{i}_makas", b["makas"], 2, "puan", arti=True)
    son = G.index[-1]
    koy("tlref_son", G["tlref"].iloc[-1], 2, "%")
    koy("tlref_politika_bp", (G["tlref"].iloc[-1] - G["politika"].iloc[-1]) * 100, 0, "bp", arti=True)
    koy("fiili_gevseme_bp", (bloklar[-1]["tlref_ort"] - bloklar[-2]["tlref_ort"]) * 100, 0, "bp", arti=True)
    # Mart'taki fiilî sıkılaştırmanın geri alınmasından sonra: bugünkü blok Ocak–Şubat'a göre
    koy("net_ocak_subat_bp", (bloklar[-1]["tlref_ort"] - bloklar[0]["tlref_ort"]) * 100, 0, "bp", arti=True)
    koy("tlref_maks", G["tlref"].max(), 2, "%")
    koy("tlref_min", G["tlref"].min(), 2, "%")
    return {"bloklar": bloklar, "son_gun": son.strftime("%d.%m.%Y")}


def enflasyon_olcumu(e: dict) -> dict:
    koy("tufe_aylik", e["tufe_aylik"], 2, "%")
    koy("tufe_aylik_sa", e["tufe_aylik_sa"], 2, "%")
    # Ana eğilim: mevsimsellikten arındırılmış üç aylık yıllıklandırılmış TÜFE ve çekirdek B, C
    # (arındırma Enflasyon hattının kendi STL yöntemidir; resmî bir arındırılmış seri değildir).
    for ad, k in (("tufe_3a_saar", "tufe_3a"), ("b_3a_saar", "b_3a"), ("c_3a_saar", "c_3a")):
        koy(ad, e[k], 2, "%")
    return {"donem": e["_tarih"], "sa_yontem": e.get("sa_yontem")}


def duzeltme_olcumu(rows: dict, pka: dict) -> dict:
    """31 Ağustos, 6, 10 ve 17 Eylül yazılarının eğri–politika faizi karşılaştırması, AYNI dilde.

    O yazılar yıllık bileşik DİBS getirisini basit ilan edilen politika faiziyle doğrudan
    kıyaslıyordu. Burada her düğüm haftalık repo karşılığına çevrilir, politika faizi de
    bileşiğe; anketin patikası (o yazının kendi tanımıyla) haftalık repoyla bir yıl çevrilir.
    Kısa uç sınaması `anket_olcumu` ile aynı kuraldır: 3 aylık düğüm saf beklenti olsaydı,
    faiz bir sonraki karara (22 Ekim, ertesi gün geçerli) kadar %37,0'de kalırsa kalan
    günlerde ne olması gerekirdi."""
    from datetime import timedelta
    satirlar = [s.split(";") for s in pka["csv"].strip().splitlines()]
    bas, govde = satirlar[0], satirlar[1:]
    anket = {r[0]: dict(zip(bas[1:], r[1:])) for r in govde}
    P = D["politika_onceki"]["deger"]
    PB = D["politika_bilesik_onceki"]["deger"]
    adlar = {"n3a": "3a", "n6a": "6a", "n1y": "1y", "n2y": "2y", "n3y": "3y", "n5y": "5y", "n7y": "7y",
             "f_1y1y": "fwd_1y1y", "f_2y1y": "fwd_2y1y", "f_2y3y": "fwd_2y3y"}
    for gun, k in DUZELTILEN.items():
        r = rows[gun]
        if abs(r["politika"] - P) > 1e-9:
            raise SystemExit(f"{gun}: politika faizi {r['politika']} — düzeltme %{P} varsayıyor")
        for sut, ad in adlar.items():
            y = koy(f"{k}_spot_{ad}", r[sut], 2, "%")
            h = koy(f"{k}_ima_{ad}", haftalik_esdeger(y), 2, "%")
            koy(f"{k}_bilesik_fark_{ad}", (y - PB) * 100, 0, "bp", arti=True)
            koy(f"{k}_ima_fark_{ad}", (h - P) * 100, 0, "bp", arti=True)
    # 10.09 ve 16.09: kısa uç beklenti olamaz (22 Ekim kararı ertesi gün geçerli)
    gecerli = date(2026, 10, 23)
    for k, ay in EKIM_ANKETI.items():
        t0 = date.fromisoformat(next(g for g, kk in DUZELTILEN.items() if kk == k))
        n0 = (gecerli - t0).days
        x = (91 * D[f"{k}_ima_3a"]["deger"] - n0 * P) / (91 - n0)
        koy(f"{k}_ima_3a_ekim_sonrasi", x, 2, "%")
        koy(f"{k}_anket_ekim", float(anket[ay]["ikinci_toplanti"]), 2, "%")
    # 10.09: eğrinin reel getirisi ile bir yıl çevrilen reponun reel getirisi (aynı başabaşla)
    r = rows["2026-09-10"]
    koy("e0910_reel_dibs_1y", r["r1y"], 2, "%")
    koy("e0910_reel_dibs_2y", r["r2y"], 2, "%")
    koy("e0910_basabas_1y", r["be_1y"], 2, "%")
    koy("e0910_reel_repo_bilesik", ((1 + PB / 100) / (1 + r["be_1y"] / 100) - 1) * 100, 2, "%")
    # 28.08 ve 16.09: o yazıların anket patikası (bugünden 12 ayda doğrusal), haftalık repoyla
    for k, ay in (("e0828", "2026-8"), ("e0916", "2026-9")):
        son = koy(f"{k}_pka_faiz_12a", float(anket[ay]["faiz_12a"]), 2, "%")
        g = koy(f"{k}_patika_getirisi", patika_getirisi(P, son), 2, "%")
        koy(f"{k}_spot_eksi_patika_bp", (D[f"{k}_spot_1y"]["deger"] - g) * 100, 0, "bp", arti=True)
    return {"gunler": DUZELTILEN, "ekim_karari_gecerli": gecerli.isoformat(),
            "ekim_anketi": EKIM_ANKETI, "patika": "bugünden 12 ayda doğrusal (o yazıların kendi tanımı)"}


def main() -> int:
    dondur(yeniden="--yeniden" in sys.argv)
    bugun = json.loads(_oku(f"ppk_2026-{BUGUN_NO:02d}-TR.json"))
    onceki = json.loads(_oku(f"ppk_2026-{ONCEKI_NO:02d}-TR.json"))
    yil = [json.loads(_oku(f"ppk_2026-{n:02d}-TR.json")) for n in (OCAK_NO, 12, 17, 23, 28, ONCEKI_NO, BUGUN_NO)]
    ks = json.loads(_oku("karar_tablosu.json"))
    d = json.loads(_oku("dibs_ozet.json"))
    e = json.loads(_oku("enflasyon_ozet.json"))
    pka = json.loads(_oku("pka_toplanti.json"))
    takvim = json.loads(_oku("takvim.json"))
    M = pd.read_csv(io.BytesIO(_oku("fonlama.csv")), index_col=0, parse_dates=True)

    son_indirim = [k for k in ks if k["degisim"] is not None and k["degisim"] < 0 and k["tarih"] < CIPA][-1]
    yapi = {
        "karar": karar_olcumu(bugun, son_indirim),
        "metin": metin_olcumu(bugun, onceki, yil),
        "arsiv": arsiv_olcumu(ks),
        "egri": egri_olcumu(d),
        "fonlama": fonlama_olcumu(M),
        "enflasyon": enflasyon_olcumu(e),
    }
    yapi["anket"] = anket_olcumu(pka, takvim, d)
    yapi["duzeltme"] = duzeltme_olcumu(json.loads(_oku("eylul_egri.json")), pka)
    koy("tufe_yillik", d["tufe_yillik"], 2, "%")
    koy("sabit_toplanti", sum(1 for k in ks if k["tarih"] > son_indirim["tarih"] and k["degisim"] == 0), 0)
    kunye = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
    cikti = {
        "cipa": CIPA,
        "arsiv": {ad: k["sha256"] for ad, k in kunye["dosyalar"].items()},
        "olcum_py_oz": hashlib.sha256((BURASI / "olcum.py").read_bytes()).hexdigest(),
        "degerler": D,
        "yapi": yapi,
    }
    (VERI / "olcum.json").write_text(json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ölçüm yazıldı: {len(D)} değer · {VERI.relative_to(KOK)}/olcum.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
