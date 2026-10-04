#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — işlem fikirleri: yazı katmanının yapılandırılmış alanı ve karnesi.

KARAR (04.10.2026, kullanıcı): "bültenlere yazdığımız bültene göre trade idea
ekleyebilir miyiz? … TRY OIS steepener, OIS–Londra bazı … fx veya rate
tarafında opsiyon, vanilla, spread … hisse tarafı da olabilir, bültendeki
yazılara senaryolara göre". Bülten piyasayı okur; işlem fikri o okumayı bir
YAPIYA çevirir: hangi bacaklar, hangi yön, referans seviye, hedef, stop, ufuk,
ve görüşü ne bozar.

Üç ilke bu modülün biçimini belirler.

(1) GİRİŞ SEVİYESİNİ YAZAR DEĞİL ÖLÇÜM VERİR. Yazar fikrin bacaklarını ve
seviyelerini yazar; referans seviye (`giris`) sayının ÖLÇÜLEN katmanından
okunur — fiyat bacağı piyasa fotoğrafının satırından, TL faiz bacağı DİBS
hattının sayının ölçüm anındaki görüntüsünden. Ölçülen katman ile yazı katmanı
çeliştiğinde hakem ölçülen katmandır; yazarın "giriş 49,03" demesi ölçünün
yerine geçmez.

(2) KARNE MEKANİKTİR VE KAPANIŞ BAZINDADIR. Söz defterinin isabeti yazarın
notudur (`izleme.json`, `isabet`); bir işlem fikrinin sonucu ise seriden
ÖLÇÜLÜR. Girişten sonraki her kapanışta yapının değeri kurulur; hedef ya da
stop bir kapanışta aşılırsa fikir o gün kapanır, ufuk dolarsa son kapanışla
kapanır. Gün içi dokunuş ölçülmez (kapanış bazında) ve bu sayfada söylenir.
Kapanış bir kez bir sayının ölçülen katmanına yazıldıktan sonra DONAR: sonraki
sayılar onu yeniden hesaplamaz, kaynağın sonradan düzelttiği bir kapanış
yayımlanmış sonucu değiştirmez.

(3) ÖLÇÜLEMEYEN UYDURULMAZ. Elimizde TRY OIS, çapraz kur swap bazı, örtük
oynaklık ve tek hisse fiyatı yok. Böyle bir fikir ya ölçülebilir bir VEKİLLE
yazılır (TRY OIS dikleştirici → DİBS spot eğrisi; karne "vekille ölçüldü" der
ve OIS–DİBS makasının ölçülmediğini söyler) ya da `olculemez` türüyle, sebebi
yazılarak yayımlanır ve karneye sonuçla girmez. Opsiyonun primi ölçülmez:
karne vade sonu ÖDEMESİNİ dayanağın kapanışından kurar ve net sonucu yazmaz.

Defter ayrı bir dosya DEĞİLDİR: fikirler açıldıkları sayının JSON'unda
(`fikirler`), yazarın erken kapattıkları kapattığı sayının JSON'unda
(`fikir_kapat`), mekanik kapanışlar ilk ölçüldükleri sayının ölçülen
katmanında (`fikir_karne`) durur. Defter yayımlanmış sayıların kendisidir —
ikinci bir kayıt bir gün sayılarla sessizce ayrışırdı.

Kullanım (yazı katmanı):
    python3 bulten/fikir.py --evren            # ölçülebilir seriler ve bugünkü seviyeleri
    python3 bulten/fikir.py --karne            # açık ve yeni kapanan fikirler
    python3 bulten/fikir.py --sina yama.json   # yamanın fikirlerini bugünkü sayıya karşı sına
"""
from __future__ import annotations

import json
import re
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTEN = KOK / "site" / "src" / "data" / "bulten"
HAM = BURASI / "onbellek" / "piyasa_ham.json"
DIBS_HAT = "dibs-verim-egrisi"
sys.path.insert(0, str(KOK / "ortak"))
import bicim  # noqa: E402  — tarih ve sayı yazımı TEK kaynaktan

# ─────────────────────────── evren: ölçülebilir seriler
#
# Fiyat bacakları piyasa fotoğrafının sembolleridir (piyasa.VARLIKLAR). Üçü
# DIŞARIDA ve sebebi adıyla: bir karne ancak doğru fiyatlanan bir seriyle
# tutulabilir.
DISLANAN = {
    "2YY=F": "ABD 2 yıllık satırı vadeli kotasyonundan geliyor ve haftalarca "
             "aynı kalan bayat kapanışlar taşıyor; karnesi tutulamaz",
    "^VIX": "örtük oynaklık endeksi doğrudan işlem görmez (vadeli ve opsiyonu ayrı enstrümandır)",
    "^MOVE": "örtük oynaklık endeksi doğrudan işlem görmez",
    # TL'Lİ DÖVİZ BACAĞININ SONUCU TAŞIMAYI İÇERMEK ZORUNDA: kısa USD/TRY bir TL
    # mevduatıdır ve yılda ~%33 faiz farkı taşır; spot getirisi tek başına onu
    # tersine gösterir (inceleme 04.10.2026: 49 günde spot −%2,62, taşımalı +%1,69).
    # USD/TRY'nin taşıması TLREF ve ABD 3 aylık faizden kurulur; euro ve sterlinin
    # kısa faizi ölçülen katmanda yok.
    "EURTRY=X": "euro kısa faizi ölçülen katmanda yok; TL taşıması kurulamaz ve spot sonucu yanıltır",
    "GBPTRY=X": "sterlin kısa faizi ölçülen katmanda yok; TL taşıması kurulamaz ve spot sonucu yanıltır",
}
# Taşımalı fiyat bacakları: (TL faizi, döviz faizi). Sonuç spot getirisi ARTI
# yönün taşımasıdır; hedef ve stop spot seviyesinde sorulur (masanın izlediği).
TASIMA = {"USDTRY=X": ("tlref", "^IRX")}

# TL faiz bacakları DİBS hattının düğümleridir. Bir yıllık reel getiri ve
# başabaş DIŞARIDA: o düğüm vade kaydığında tek günde kuruluş sıçraması yapıyor
# (28.09.2026: 9,06 → 6,42) ve karne sahte bir stop yazardı.
DIBS = {
    "gosterge_ytm": ("DİBS gösterge tahvil", 2.0),
    "spot_3a": ("DİBS 3 ay", 0.25), "spot_6a": ("DİBS 6 ay", 0.5),
    "spot_1y": ("DİBS 1 yıl", 1.0), "spot_2y": ("DİBS 2 yıl", 2.0),
    "spot_3y": ("DİBS 3 yıl", 3.0), "spot_5y": ("DİBS 5 yıl", 5.0),
    "spot_7y": ("DİBS 7 yıl", 7.0), "spot_9y": ("DİBS 9 yıl", 9.0),
    "forward_1y1y": ("DİBS 1y1y forward", 1.5), "forward_2y1y": ("DİBS 2y1y forward", 2.5),
    "forward_2y3y": ("DİBS 2y3y forward", 3.5),
    "reel_egri_2y": ("TÜFEX reel 2 yıl", 2.0), "reel_egri_3y": ("TÜFEX reel 3 yıl", 3.0),
    "reel_egri_5y": ("TÜFEX reel 5 yıl", 5.0), "reel_egri_7y": ("TÜFEX reel 7 yıl", 7.0),
    "basabas_2y": ("Başabaş enflasyon 2 yıl", 2.0), "basabas_3y": ("Başabaş enflasyon 3 yıl", 3.0),
    "basabas_5y": ("Başabaş enflasyon 5 yıl", 5.0), "basabas_7y": ("Başabaş enflasyon 7 yıl", 7.0),
}
# ABD getirilerinin vadesi (eğri yönünü — dikleştirici mi — bacakların vadesinden
# türetmek için).
ABD_VADE = {"^IRX": 0.25, "^FVX": 5.0, "^TNX": 10.0, "^TYX": 30.0}

TURLER = ("yalin", "egri", "kelebek", "goreli", "opsiyon", "olculemez")
# Karnenin kapanmış durumları (donar; bir sonraki sayı yeniden hesaplamaz).
KAPANMIS = ("hedef", "stop", "sure", "geri_cekildi", "vade", "olculemedi", "sure_olculemez",
            "giriste_gecersiz")
DONAN_ALANLAR = ("durum", "son", "son_tarih", "sonuc", "sonuc_turu", "kapanis_tarih",
                 "giris_fiili", "giris_fiili_tarih", "sebep", "sonuc_r", "spot_sonuc", "tasima",
                 "tasima_olculemedi", "giris_oncesi", "not")
SINIFLAR = ("faiz", "fx", "hisse", "emtia", "kredi")
OPSIYON_TIP = ("call", "put", "call_spread", "put_spread", "risk_reversal")
UFUK_ASGARI_GUN = 2
UFUK_AZAMI_GUN = 183
YONLER = ("yukari", "asagi")
# Yeni kapanan fikir sayfada bu kadar gün "kapanan" altında durur.
KAPANAN_PENCERE = {"gunluk": 10, "haftalik": 14}
# Ölçülemeyen fikir bu kadar gün sonra listeden düşer (sonucu yoktur, ufku vardır).
GRUP_SINIF = {"tr_fx": "fx", "g10_fx": "fx", "tr_hisse": "hisse", "abd_hisse": "hisse",
              "ab_hisse": "hisse", "asya_hisse": "hisse", "faiz": "faiz", "metal": "emtia",
              "enerji": "emtia", "kredi": "kredi", "kripto": "fx"}


# Kaydın OKURA GİDEN metin alanları — denetimin dil, biçim ve büyük harf
# ölçütleri bunları tarar (makine alanları taranmaz).
METIN_ALANLARI = ("baslik", "gerekce", "ne_bozar", "enstruman", "olculemez_sebep",
                  "senaryo", "yapi_metni", "yon_metni")


# Etiket: harfle ya da "/" ile başlayan "<…>". "<" tek başına (bir eşitsizlik,
# "%40 < %41") etiket sayılmaz.
ETIKET = re.compile(r"<[A-Za-z/][^<>]*>")


class FikirHatasi(ValueError):
    """Yazma kapısının reddi — mesaj yazara ne eksik olduğunu söyler."""


@dataclass(frozen=True)
class Seri:
    id: str
    ad: str
    tip: str              # "fiyat" | "getiri"
    sinif: str
    ondalik: int = 2
    vade: float | None = None   # getiri serilerinde yıl
    aile: str = ""              # getiride alt eğri: nominal · forward · reel · basabas · abd
    grup: str = ""              # kapanış saati için piyasa grubu ("dibs" TL faizi)


def evren() -> dict[str, Seri]:
    import piyasa
    out: dict[str, Seri] = {}
    for v in piyasa.VARLIKLAR:
        if v.kod in DISLANAN:
            continue
        out[v.kod] = Seri(v.kod, v.ad, v.tip, GRUP_SINIF.get(v.grup, "fx"), v.ondalik,
                          ABD_VADE.get(v.kod), "abd" if v.tip == "getiri" else "", v.grup)
    for k, (ad, vade) in DIBS.items():
        aile = ("forward" if k.startswith("forward_") else "reel" if k.startswith("reel_")
                else "basabas" if k.startswith("basabas_") else "nominal")
        out[f"dibs:{k}"] = Seri(f"dibs:{k}", ad, "getiri", "faiz", 2, vade, aile, "dibs")
    return out


# KAPANIŞ ANI (UTC saat). Fiili giriş "yazımdan SONRA kapanan ilk seans"tır;
# günü sormak yetmez — hafta içi 20:00 UTC'de yazılan bir fikir o günün BIST
# (15:00 UTC) ve İstanbul 18:00 kur kapanışını çoktan görmüştür (inceleme
# 04.10.2026). Bu tablo GÖRÜNÜRLÜK sorusudur ve TUTUCU yazılır: grubun EN ERKEN
# gerçek kapanışı, saate aşağı yuvarlanmış (yaz saati). piyasa.KAPANIS_UTC ise
# ölçüm katmanının "bar yerleşti mi" payını taşır (BIST 16, New York 22) ve
# burada kullanılsaydı 15:00–16:00 UTC arasında yazılan bir BIST fikri, yazarın
# gördüğü kapanışı giriş alırdı. Tutucu yönün bedeli yalnız girişin bir gün
# kaymasıdır. TL kuru İstanbul 18:00, G10 kuru New York 17:00 (yaz 21 UTC), TL
# faizi (DİBS) seans sonu; Tokyo 06:00, Avrupa 15:30, New York hisse 20:00,
# ABD tahvil 19:00, COMEX/NYMEX uzlaşması 18:30 UTC.
KAPANIS_SAAT = {"tr_fx": 15, "g10_fx": 21, "kripto": 24, "dibs": 15,
                "asya_hisse": 6, "tr_hisse": 15, "ab_hisse": 15, "abd_hisse": 20,
                "faiz": 19, "kredi": 20, "metal": 18, "enerji": 18}


def kapanis_ani(sid: str, gun: str, ev: dict[str, Seri]) -> datetime:
    import piyasa
    s = ev.get(sid)
    grup = s.grup if s else ""
    saat = KAPANIS_SAAT.get(grup, piyasa.KAPANIS_UTC.get(grup, 22))
    return datetime.fromisoformat(gun) + timedelta(hours=saat)


def _an(t) -> datetime | None:
    """UTC naif an (gozlem._an sözleşmesi)."""
    try:
        d = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if d.tzinfo is not None:
        from datetime import timezone as _tz
        d = d.astimezone(_tz.utc).replace(tzinfo=None)
    return d


def is_gunu_sayisi(bas: date, son: date) -> int:
    """(bas, son] aralığındaki hafta içi gün sayısı."""
    n, g = 0, bas
    while g < son:
        g += timedelta(days=1)
        n += g.weekday() < 5
    return n


def _yuvarla(v: float | None, n: int = 6) -> float | None:
    """Kayda giden sayı: kayan nokta artığı (−660,0000000000001) yazılmaz."""
    return None if v is None else round(float(v), n)


def _iso(t) -> str | None:
    g = bicim.tarihe_cevir(t)
    return g.isoformat() if g else None


def _sayi(v) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


# ─────────────────────────── ölçülen değerler

def piyasa_satiri(b: dict, kod: str) -> dict | None:
    for g in ((b.get("piyasa") or {}).get("gruplar") or []):
        for s in g.get("satirlar") or []:
            if s.get("kod") == kod:
                return s
    return None


def _dibs_an(b: dict, dibs_gecmis: list[dict] | None = None) -> dict:
    """DİBS hattının sayının ÖLÇÜM ANINDAKİ görüntüsü (sayfadaki TL faiz seti
    o anın görüntüsünden basıldı). Defter verilmezse depodakinden okunur."""
    import gozlem
    an = gozlem._an(b.get("olusturma") or "")
    kayitlar = dibs_gecmis if dibs_gecmis is not None else gozlem.gecmis_oku(DIBS_HAT)
    aday = None
    for k in kayitlar:
        t = gozlem._an(k.get("t", ""))
        if an is None or (t is not None and t <= an):
            aday = k
    return (aday or {}).get("d") or {}


def bacak_degeri(b: dict, sid: str, dibs_d: dict | None = None) -> tuple[float, str] | None:
    """(değer, ISO tarih) — sayının ölçülen katmanından. Yoksa None."""
    if sid.startswith("dibs:"):
        k = sid[5:]
        d = dibs_d if dibs_d is not None else _dibs_an(b)
        v = _sayi(d.get(k))
        t = _iso(d.get(f"{k}_tarih") or d.get("_tarih"))
        return (v, t) if v is not None and t else None
    s = piyasa_satiri(b, sid)
    if not s:
        return None
    v, t = _sayi(s.get("son")), _iso(s.get("tarih"))
    return (v, t) if v is not None and t else None


def sigma_gun(b: dict, sid: str) -> float | None:
    """Fiyat bacağında günlük σ (%), getiri bacağında (bp) — piyasa satırından."""
    s = piyasa_satiri(b, sid) if not sid.startswith("dibs:") else None
    return _sayi((s or {}).get("sigma_gun"))


# ─────────────────────────── yapı: değer, birim, sonuç

def birim(f: dict) -> str:
    """Yapının değerinin birimi: '%' (tek getiri) · 'bp' (getiri bileşimi) ·
    'fiyat' (tek fiyat ya da opsiyonun dayanağı) · 'oran' (iki fiyatın oranı)."""
    # Kayıtlı fikir birimini taşır; yeniden türetmek (tip bilgisi kayıtta yok)
    # tek getiri bacaklı fikri fiyat sanıp sonucu yüzdeyle yazardı.
    if f.get("birim") in ("%", "bp", "fiyat", "oran"):
        return f["birim"]
    tur = f["tur"]
    if tur in ("egri", "kelebek"):
        return "bp"
    if tur == "goreli":
        return "oran"
    if tur == "yalin" and f.get("_tipler", ["fiyat"])[0] == "getiri":
        return "%"
    return "fiyat"


def sonuc_birim(f: dict) -> str:
    return "bp" if birim(f) in ("bp", "%") else "%"


def yapi_degeri(f: dict, degerler: list[float]) -> float:
    tur = f["tur"]
    if tur in ("egri", "kelebek"):
        return sum(k * v for k, v in zip(f["katsayilar"], degerler)) * 100.0
    if tur == "goreli":
        return degerler[0] / degerler[1]
    return degerler[0]


def sonuc(f: dict, deger: float, baz: float | None = None) -> float:
    """Fikrin girişten bu değere kadarki sonucu: getiri yapılarında bp, fiyat
    yapılarında yüzde. İşaret fikrin yönünden: + kazanç. `baz` verilmezse
    referans seviye (`giris`) kullanılır — karne fiili girişi (yayımdan sonraki
    ilk kapanış) verir."""
    isaret = 1.0 if f["yon"] == "yukari" else -1.0
    g = float(f["giris"] if baz is None else baz)
    if birim(f) == "%":
        return isaret * (deger - g) * 100.0
    if birim(f) == "bp":
        return isaret * (deger - g)
    return isaret * (deger / g - 1.0) * 100.0


def opsiyon_odeme(f: dict, spot: float, s0: float | None = None) -> float:
    """Vade sonu ödemesi, dayanağın girişteki seviyesinin yüzdesi olarak (bir
    birim dayanak başına). PRİM DAHİL DEĞİL — örtük oynaklık ölçülmüyor."""
    o = f["opsiyon"]
    k = o["kullanim"]
    s0 = float(f["giris"] if s0 is None else s0)
    tip = o["tip"]
    if tip == "call":
        p = max(spot - k[0], 0.0)
    elif tip == "put":
        p = max(k[0] - spot, 0.0)
    elif tip == "call_spread":
        p = min(max(spot - k[0], 0.0), k[1] - k[0])
    elif tip == "put_spread":
        p = min(max(k[1] - spot, 0.0), k[1] - k[0])
    else:   # risk_reversal: yukarı = call al / put sat; aşağı = put al / call sat
        cagri, satim = max(spot - k[1], 0.0), max(k[0] - spot, 0.0)
        p = (cagri - satim) if f["yon"] == "yukari" else (satim - cagri)
    return p / s0 * 100.0


def _ad(sid: str, ev: dict[str, Seri]) -> str:
    s = ev.get(sid)
    return s.ad if s else sid


def yapi_metni(f: dict, ev: dict[str, Seri] | None = None) -> str:
    """Yapının okura yazılan formülü — "DİBS 9 yıl − DİBS 2 yıl"."""
    ev = ev or evren()
    if f["tur"] == "olculemez":
        return f.get("enstruman") or ""
    ids = [x["seri"] for x in f["bacaklar"]]
    if f["tur"] == "goreli":
        return f"{_ad(ids[0], ev)} / {_ad(ids[1], ev)}"
    if f["tur"] in ("egri", "kelebek"):
        parca = []
        for i, (sid, k) in enumerate(zip(ids, f["katsayilar"])):
            kat = abs(k)
            ad = _ad(sid, ev)
            terim = ad if kat == 1 else f"{bicim.sayi(kat, 0 if float(kat).is_integer() else 2)} × {ad}"
            if i == 0:
                parca.append(("−" if k < 0 else "") + terim)
            else:
                parca.append(("− " if k < 0 else "+ ") + terim)
        return " ".join(parca)
    return _ad(ids[0], ev)


def yon_metni(f: dict, ev: dict[str, Seri] | None = None) -> str:
    """Fikrin yönü okur diliyle — hangi hareketten kazanır."""
    ev = ev or evren()
    tur, yukari = f["tur"], f["yon"] == "yukari"
    if tur == "olculemez":
        return ""
    if tur == "opsiyon":
        # Yön metni kullanım fiyatından kurulur: kayan bir kurda "dayanak
        # yükselirse kazanır" temel patikada yanlış okunur — ileri kurun
        # altındaki her yükseliş sıfır öder (inceleme 04.10.2026).
        o = f["opsiyon"]
        k = [bicim.sayi(x, 2) for x in o["kullanim"]]
        tip = o["tip"]
        # Sayıya ek getirilmez (ek sayının okunuşuna göre değişir, üretici
        # bilemez): cümle sayıyı ekten ayırır.
        if tip == "call":
            return f"alım opsiyonu: dayanak vadede kullanım fiyatının ({k[0]}) üstünde kapanırsa öder"
        if tip == "put":
            return f"satım opsiyonu: dayanak vadede kullanım fiyatının ({k[0]}) altında kapanırsa öder"
        if tip == "call_spread":
            return (f"alım yayılımı: dayanak vadede alt kullanım fiyatının ({k[0]}) üstünde kapanırsa "
                    f"öder; ödeme üst kullanım fiyatında ({k[1]}) tavana ulaşır")
        if tip == "put_spread":
            return (f"satım yayılımı: dayanak vadede üst kullanım fiyatının ({k[1]}) altında kapanırsa "
                    f"öder; ödeme alt kullanım fiyatında ({k[0]}) tavana ulaşır")
        return (f"risk dönüşümü (alım alınır, satım yazılır): vadede üst kullanım fiyatının ({k[1]}) "
                f"üstünde kazanır, alt kullanım fiyatının ({k[0]}) altında kaybeder" if yukari else
                f"risk dönüşümü (satım alınır, alım yazılır): vadede alt kullanım fiyatının ({k[0]}) "
                f"altında kazanır, üst kullanım fiyatının ({k[1]}) üstünde kaybeder")
    if tur == "goreli":
        a, b_ = [_ad(x["seri"], ev) for x in f["bacaklar"]]
        return f"{a}, {b_} karşısında {'güçlenirse' if yukari else 'zayıflarsa'} kazanır"
    if tur == "yalin":
        sid = f["bacaklar"][0]["seri"]
        aile = ev[sid].aile if sid in ev else ""
        if aile == "basabas":
            return ("başabaş enflasyon genişlerse kazanır (TÜFEX'te uzun, nominalde kısa)" if yukari
                    else "başabaş enflasyon daralırsa kazanır (nominalde uzun, TÜFEX'te kısa)")
        if aile == "reel":
            return ("reel getiri yükselirse kazanır (TÜFEX'te kısa)" if yukari
                    else "reel getiri düşerse kazanır (TÜFEX'te uzun)")
        if aile == "forward":
            return ("ileri faiz yükselirse kazanır (ileri başlangıçlı swapta sabit ödeyen)" if yukari
                    else "ileri faiz düşerse kazanır (ileri başlangıçlı swapta sabit alan)")
        if f.get("_tipler", ["fiyat"])[0] == "getiri":
            return ("getiri yükselirse kazanır (tahvilde kısa · swapta sabit ödeyen)" if yukari
                    else "getiri düşerse kazanır (tahvilde uzun · swapta sabit alan)")
        return "yükselirse kazanır (uzun)" if yukari else "düşerse kazanır (kısa)"
    vadeler = [ev[x["seri"]].vade if x["seri"] in ev else None for x in f["bacaklar"]]
    if tur == "egri" and None not in vadeler:
        uzun = max(range(2), key=lambda i: vadeler[i])
        dik = (f["katsayilar"][uzun] > 0) == yukari
        ters = isinstance(f.get("giris"), (int, float)) and \
            (f["giris"] < 0) == (f["katsayilar"][uzun] > 0)
        not_ = ((" — ters eğride tersliğin azalması" if dik else " — ters eğride tersliğin derinleşmesi")
                if ters else "")
        return ("eğri dikleşirse kazanır (dikleştirici" + not_ + ")" if dik
                else "eğri yassılaşırsa kazanır (yassılaştırıcı" + not_ + ")")
    if tur == "kelebek" and None not in vadeler:
        govde = sorted(range(3), key=lambda i: vadeler[i])[1]
        ucuz = (f["katsayilar"][govde] > 0) == yukari
        return ("gövde kanatlara göre ucuzlarsa (getirisi göreli yükselirse) kazanır — gövdede ödeyen"
                if ucuz else
                "gövde kanatlara göre pahalanırsa (getirisi göreli düşerse) kazanır — gövdede alan")
    return "yapının değeri yükselirse kazanır" if yukari else "yapının değeri düşerse kazanır"


# ─────────────────────────── yazma kapısı

def _gun(t: str, alan: str) -> date:
    try:
        return date.fromisoformat(str(t)[:10])
    except ValueError:
        raise FikirHatasi(f"{alan}: tarih YYYY-MM-DD olmalı ({t!r})")


def dogrula(g: dict, b: dict, sira: int, ev: dict[str, Seri] | None = None,
            dibs_d: dict | None = None, bolumler: list[str] | None = None,
            seriler: tuple[dict, dict] | None = None, yazim_ani: str | None = None) -> dict:
    """Yazarın fikrini sına ve normalleştir; girişi ölçülen katmandan kur.
    Yapısal bir kusurda FikirHatasi — fikir yazılmaz."""
    ev = ev or evren()
    if not isinstance(g, dict):
        raise FikirHatasi(f"fikirler[{sira}] bir nesne değil")
    on = f"fikirler[{sira}]"
    # Metin alanları DÜZ METİNDİR: sayfa onları kaçırarak basar ve kaçmış bir
    # etiket yayın kapısında (sayfa sınavı 22) ENGEL olur — etiketli bir
    # gerekçe yazma kapısından geçerse siteyi durdurur (inceleme 04.10.2026).
    for alan in METIN_ALANLARI:
        if isinstance(g.get(alan), str) and ETIKET.search(g[alan]):
            raise FikirHatasi(f"{on}.{alan}: HTML etiketi taşıyor — fikir alanları düz metindir")
    # Tip sözleşmesi: liste ya da nesne beklenen yerde başka bir değer
    # yakalanmayan bir istisnayla değil, adıyla reddedilir (çıkış 2).
    for alan, tip, ad in (("bacaklar", list, "liste"), ("opsiyon", dict, "nesne")):
        if g.get(alan) is not None and not isinstance(g[alan], tip):
            raise FikirHatasi(f"{on}.{alan} bir {ad} olmalı")
    if isinstance(g.get("opsiyon"), dict) and g["opsiyon"].get("kullanim") is not None \
            and not isinstance(g["opsiyon"]["kullanim"], list):
        raise FikirHatasi(f"{on}.opsiyon.kullanim bir liste olmalı: [K] ya da [K1, K2]")
    tur = str(g.get("tur") or "").strip()
    if tur not in TURLER:
        raise FikirHatasi(f"{on}: tur {', '.join(TURLER)} olmalı ({tur!r})")
    baslik = " ".join(str(g.get("baslik") or "").split())
    if not baslik:
        raise FikirHatasi(f"{on}: baslik boş")
    for alan in ("gerekce", "ne_bozar"):
        if not str(g.get(alan) or "").strip():
            raise FikirHatasi(f"{on}: {alan} boş — her fikir dayandığı okumayı ve onu neyin "
                              "bozacağını yazar")
    bugun = _gun(b.get("tarih") or "", "sayının tarihi")
    ufuk = _gun(g.get("ufuk") or (g.get("opsiyon") or {}).get("vade") or "", f"{on}.ufuk")
    kalan = (ufuk - bugun).days
    # Asgari ufuk İŞ GÜNÜYLE: cuma açılıp ufku pazara düşen fikir sıfır
    # uzunluklu bir "ufuk doldu" kapanışı üretiyordu (inceleme 04.10.2026).
    if is_gunu_sayisi(bugun, ufuk) < UFUK_ASGARI_GUN or kalan > UFUK_AZAMI_GUN:
        raise FikirHatasi(f"{on}: ufuk en az {UFUK_ASGARI_GUN} iş günü, en çok {UFUK_AZAMI_GUN} "
                          f"gün ileride olmalı (şu an {kalan} gün)")
    dayanak = str(g.get("dayanak") or "").strip()
    if bolumler is not None and dayanak and dayanak not in bolumler + ["yorum"]:
        raise FikirHatasi(f"{on}: dayanak bu sayının bölümlerinden biri olmalı "
                          f"({', '.join(bolumler + ['yorum'])}); verilen {dayanak!r}")
    f = {
        "kimlik": f"{bugun.isoformat()}-{sira}",
        "acilis": bugun.isoformat(),
        "baslik": baslik,
        "tur": tur,
        "gerekce": str(g["gerekce"]).strip(),
        "ne_bozar": str(g["ne_bozar"]).strip(),
        "ufuk": ufuk.isoformat(),
        "dayanak": dayanak,
    }
    if yazim_ani:
        f["yazim_ani"] = yazim_ani
    for alan in ("enstruman", "senaryo"):
        if str(g.get(alan) or "").strip():
            f[alan] = " ".join(str(g[alan]).split())
    if tur == "olculemez":
        sebep = str(g.get("olculemez_sebep") or "").strip()
        if not sebep or not f.get("enstruman"):
            raise FikirHatasi(f"{on}: ölçülemeyen fikir enstrumani ve olculemez_sebep'i "
                              "yazar (ör. 'TRY OIS–Londra bazı' · 'çapraz kur swap kotasyonu "
                              "elimizde yok')")
        f.update({"olculemez_sebep": sebep, "sinif": str(g.get("sinif") or "faiz"),
                  "bacaklar": [], "yon": "", "giris": None,
                  "yapi_metni": f["enstruman"], "yon_metni": ""})
        if f["sinif"] not in SINIFLAR:
            raise FikirHatasi(f"{on}: sinif {', '.join(SINIFLAR)} olmalı")
        return f

    yon = str(g.get("yon") or "").strip()
    bacaklar = g.get("bacaklar")
    if not isinstance(bacaklar, list) or not bacaklar:
        raise FikirHatasi(f"{on}: bacaklar listesi boş")
    ids = []
    for i, x in enumerate(bacaklar, 1):
        sid = str((x or {}).get("seri") if isinstance(x, dict) else x or "").strip()
        if sid not in ev:
            neden = DISLANAN.get(sid)
            raise FikirHatasi(f"{on}.bacaklar[{i}]: '{sid}' ölçülebilir evrende yok"
                              + (f" ({neden})" if neden else "")
                              + " — liste için: python3 bulten/fikir.py --evren")
        ids.append(sid)
    tipler = [ev[s].tip for s in ids]
    beklenen = {"yalin": 1, "egri": 2, "kelebek": 3, "goreli": 2, "opsiyon": 1}[tur]
    if len(ids) != beklenen:
        raise FikirHatasi(f"{on}: {tur} yapısı {beklenen} bacak ister ({len(ids)} verildi)")
    if tur in ("egri", "kelebek") and set(tipler) != {"getiri"}:
        raise FikirHatasi(f"{on}: {tur} yalnız getiri bacaklarıyla kurulur")
    if tur in ("goreli", "opsiyon") and set(tipler) != {"fiyat"}:
        raise FikirHatasi(f"{on}: {tur} yalnız fiyat bacaklarıyla kurulur")
    # TL'li döviz bacağının sonucu taşımayı içerir ve taşıma yalnız YALIN yapıda
    # ölçülür: göreli bir yapıda (BIST 100 / USD/TRY) karne taşımasız oranı
    # yazar ve EUR/TRY'yi evrenden çıkaran yanılgının aynısını üretir. Rehber
    # bunu yasaklıyordu, kod sormuyordu (inceleme 04.10.2026).
    tasimali = [x for x in ids if x in TASIMA]
    if tasimali and tur not in ("yalin", "opsiyon"):
        raise FikirHatasi(f"{on}: {ev[tasimali[0]].ad} bacağı yalnız yalın yapıda ya da opsiyonda "
                          "kullanılır — sonucu TL taşımasını içerir ve taşıma yalnız orada ölçülür")
    if len(set(ids)) != len(ids):
        raise FikirHatasi(f"{on}: aynı seri iki bacakta")
    if tur in ("egri", "kelebek"):
        # Bir eğri yapısı TEK eğrinin düğümlerinden kurulur: TL düğümü ile ABD
        # getirisinin farkı bir ülke makasıdır ve "dikleştirici" etiketi onu
        # yanlış anlatır. Bacaklar kısadan uzuna yazılır: varsayılan katsayılar
        # (−1, +1 · −1, +2, −1) SIRAYA uygulanır ve sıra bozuksa +2 gövdeye düşmez.
        # Alt eğri de aynı olmalı: nominal spot ile başabaş ya da reel düğüm
        # farkı bir eğri değil, bir enflasyon ya da reel faiz görüşüdür.
        aileler = {ev[x].aile for x in ids}
        if len(aileler) != 1:
            raise FikirHatasi(f"{on}: {tur} yapısının bacakları aynı eğriden olmalı "
                              "(nominal DİBS · DİBS forward · TÜFEX reel · başabaş · ABD getirisi)")
        vadeler = [ev[x].vade for x in ids]
        if None in vadeler or any(a >= b_ for a, b_ in zip(vadeler, vadeler[1:])):
            raise FikirHatasi(f"{on}: {tur} bacakları kısadan uzuna yazılır "
                              f"({', '.join(ev[x].ad for x in ids)})")
    katsayilar = [1.0]
    if tur in ("egri", "kelebek"):
        varsayilan = [-1.0, 1.0] if tur == "egri" else [-1.0, 2.0, -1.0]
        katsayilar = []
        for i, x in enumerate(bacaklar):
            k = _sayi(x.get("katsayi")) if isinstance(x, dict) and "katsayi" in x else varsayilan[i]
            if k is None or k == 0:
                raise FikirHatasi(f"{on}.bacaklar[{i + 1}]: katsayi sıfırdan farklı bir sayı olmalı")
            katsayilar.append(k)
        # İşaret kuralı: eğri iki zıt işaretli bacaktır (aynı işaret bir
        # durasyon pozisyonudur, eğri değil); kelebekte gövde kanatların tersidir.
        if tur == "egri" and katsayilar[0] * katsayilar[1] >= 0:
            raise FikirHatasi(f"{on}: eğri yapısının katsayıları zıt işaretli olmalı")
        if tur == "kelebek" and not (katsayilar[0] * katsayilar[2] > 0
                                     and katsayilar[0] * katsayilar[1] < 0):
            raise FikirHatasi(f"{on}: kelebekte kanatlar aynı, gövde ters işaretli olmalı")
    if yon not in YONLER:
        raise FikirHatasi(f"{on}: yon 'yukari' ya da 'asagi' — yapının değeri yükselirse mi "
                          "düşerse mi kazanır")

    olc = []
    for sid in ids:
        r = bacak_degeri(b, sid, dibs_d)
        if r is None:
            raise FikirHatasi(f"{on}: '{sid}' bu sayının ölçülen katmanında yok ya da "
                              "ölçülemedi; giriş seviyesi uydurulmaz")
        olc.append(r)
    f.update({"bacaklar": [{"seri": s, "deger": v, "tarih": t} for s, (v, t) in zip(ids, olc)],
              "katsayilar": katsayilar, "yon": yon, "_tipler": tipler,
              "sinif": str(g.get("sinif") or ev[ids[0]].sinif)})
    if f["sinif"] not in SINIFLAR:
        raise FikirHatasi(f"{on}: sinif {', '.join(SINIFLAR)} olmalı")
    if tur == "goreli" and olc[1][0] == 0:
        raise FikirHatasi(f"{on}: göreli yapının paydası sıfır")
    f["giris"] = _yuvarla(yapi_degeri(f, [v for v, _ in olc]))
    # Bağlayıcı bacak: yapının referans günü bacakların EN ESKİSİDİR.
    f["giris_tarih"] = min(t for _, t in olc)
    f["birim"] = birim(f)
    f["sonuc_birim"] = sonuc_birim(f)
    f["ondalik"] = {"bp": 1, "%": 2, "oran": 4}.get(f["birim"], ev[ids[0]].ondalik)

    if tur == "opsiyon":
        o = g.get("opsiyon") or {}
        tip = str(o.get("tip") or "").strip()
        if tip not in OPSIYON_TIP:
            raise FikirHatasi(f"{on}: opsiyon.tip {', '.join(OPSIYON_TIP)} olmalı")
        kul = [_sayi(x) for x in (o.get("kullanim") or [])]
        gerek = 1 if tip in ("call", "put") else 2
        if len(kul) != gerek or None in kul or any(x <= 0 for x in kul):
            raise FikirHatasi(f"{on}: {tip} {gerek} kullanım fiyatı ister")
        if gerek == 2 and not kul[0] < kul[1]:
            raise FikirHatasi(f"{on}: kullanım fiyatları küçükten büyüğe yazılır")
        dogal = {"call": "yukari", "call_spread": "yukari", "put": "asagi", "put_spread": "asagi"}
        if tip in dogal and dogal[tip] != yon:
            raise FikirHatasi(f"{on}: {tip} yapısının yönü {dogal[tip]}")
        if _gun(o.get("vade") or f["ufuk"], f"{on}.opsiyon.vade") != ufuk:
            raise FikirHatasi(f"{on}: opsiyonun ufku vadesidir (opsiyon.vade = ufuk)")
        f["opsiyon"] = {"tip": tip, "kullanim": kul, "vade": ufuk.isoformat()}
        f["hedef"] = f["stop"] = None
    else:
        hedef, stop = _sayi(g.get("hedef")), _sayi(g.get("stop"))
        if hedef is None or stop is None:
            raise FikirHatasi(f"{on}: hedef ve stop yapının kendi biriminde yazılır "
                              f"({f['birim']}; giriş {f['giris']:.4f})")
        artis = yon == "yukari"
        if (hedef <= f["giris"]) if artis else (hedef >= f["giris"]):
            raise FikirHatasi(f"{on}: hedef girişin kazanç tarafında olmalı "
                              f"(giriş {f['giris']:.4f}, yön {yon}, hedef {hedef})")
        if (stop >= f["giris"]) if artis else (stop <= f["giris"]):
            raise FikirHatasi(f"{on}: stop girişin zarar tarafında olmalı "
                              f"(giriş {f['giris']:.4f}, yön {yon}, stop {stop})")
        f["hedef"], f["stop"] = hedef, stop
    f["yapi_metni"] = yapi_metni(f, ev)
    f["yon_metni"] = yon_metni(f, ev)
    if f.get("hedef") is not None:
        f["getiri_risk"] = round(abs(sonuc(f, f["hedef"])) / max(abs(sonuc(f, f["stop"])), 1e-12), 2)
        f["stop_mesafe"] = round(abs(sonuc(f, f["stop"])), 2)
        f["hedef_mesafe"] = round(abs(sonuc(f, f["hedef"])), 2)
        try:
            sg = yapi_sigma(f, ham_seriler() if seriler is None else seriler[0],
                            dibs_seriler() if seriler is None else seriler[1], ev)
        except Exception:                                      # noqa: BLE001
            sg = None
        if sg:
            # Ufka ölçekli mesafe: stop ve hedef, ufuk boyunca beklenen
            # dağılımın (σ·√iş günü) kaçta kaçı. Bir günlük σ tabanı tek
            # başına yanıltır: 20 günlük ufukta 1σ'lık stop rastgele yürüyüşte
            # ~%82 olasılıkla gürültüyle dokunulur.
            n = max(1, is_gunu_sayisi(bugun, ufuk))
            f.update({"sigma_gun": sg, "ufuk_is_gunu": n,
                      "stop_z": round(f["stop_mesafe"] / (sg * n ** 0.5), 2),
                      "hedef_z": round(f["hedef_mesafe"] / (sg * n ** 0.5), 2)})
    del f["_tipler"]
    return f


def dogrula_liste(liste, b: dict, dibs_d: dict | None = None,
                  yazim_ani: str | None = None) -> list[dict]:
    if not isinstance(liste, list):
        raise FikirHatasi("fikirler bir liste olmalı")
    import ayar
    bolumler = [x["id"] for x in (b.get("gundem_yazi_bolumleri") or ayar.yazi_bolumleri(b))]
    ev = evren()
    d = dibs_d if dibs_d is not None else _dibs_an(b)
    seriler = (ham_seriler(), dibs_seriler())
    return [dogrula(g, b, i, ev, d, bolumler, seriler, yazim_ani) for i, g in enumerate(liste, 1)]


# Bir fikrin KİMLİĞİNİ belirleyen alanlar: yapı ve seviyeler. Metin alanları
# (başlık, gerekçe) karneyi etkilemez; yazım hatası düzeltmesine açık kalır.
IMZA_ALANLARI = ("tur", "yon", "hedef", "stop", "ufuk", "katsayilar", "opsiyon",
                 "enstruman", "olculemez_sebep")


def imza(f: dict) -> str:
    return json.dumps({**{a: f.get(a) for a in IMZA_ALANLARI},
                       "seri": [x.get("seri") for x in f.get("bacaklar") or []]},
                      sort_keys=True, ensure_ascii=False)


def ekle_koru(eski: list[dict], yeni: list[dict]) -> list[dict]:
    """Yazılmış sayıya gelen liste: eski fikirlerin HEPSİ aynı imzayla bulunmalı
    (kimlik, giriş ve yazım anı korunur; metin alanları güncellenebilir), kalan
    yeniler sona, kimlik sırası sürerek eklenir. Eksik ya da değişmiş eski fikir
    FikirHatasi."""
    gelen = {imza(f): f for f in yeni}
    out = []
    for f in eski:
        g = gelen.pop(imza(f), None)
        if g is None:
            raise FikirHatasi(f"yazılmış fikir '{f.get('baslik')}' listede yok ya da seviyesi "
                              "değişmiş: yayımlanmış fikir değiştirilmez ve silinmez — görüş "
                              "değiştiyse sonraki sayıda fikir_kapat, yeni görüş yeni fikir")
        out.append({**f, **{a: g[a] for a in METIN_ALANLARI if a in g and a not in ("yapi_metni", "yon_metni")}})
    tarih, n = (eski[0]["kimlik"].rsplit("-", 1)[0], max(int(f["kimlik"].rsplit("-", 1)[1]) for f in eski))
    for i, g in enumerate(gelen.values(), 1):
        out.append({**g, "kimlik": f"{tarih}-{n + i}"})
    return out


def _tipler(f: dict, ev: dict[str, Seri]) -> list[str]:
    return [ev[x["seri"]].tip if x["seri"] in ev else "fiyat" for x in f.get("bacaklar") or []]


def _f(f: dict, ev: dict[str, Seri]) -> dict:
    """Kayıtlı bir fikre birim hesabının istediği tip bilgisini ekler."""
    return {**f, "_tipler": _tipler(f, ev)}


def kapat_dogrula(liste, b: dict, acik: dict[str, dict], dibs_d: dict | None = None,
                  yazim_ani: str | None = None) -> list[dict]:
    """Yazarın erken kapanışı bir ÇIKIŞ EMRİDİR. Kayıttaki `cikis` bu sayının
    ölçülen katmanındaki referans seviyedir (okura bilgi); karnenin çıkışı,
    girişle simetrik olarak, bu sayının yayımından sonraki ilk kapanıştır."""
    if not isinstance(liste, list):
        raise FikirHatasi("fikir_kapat bir liste olmalı: [{kimlik, sebep}]")
    ev = evren()
    d = dibs_d if dibs_d is not None else _dibs_an(b)
    out = []
    for i, x in enumerate(liste, 1):
        if not isinstance(x, dict):
            raise FikirHatasi(f"fikir_kapat[{i}] bir nesne değil")
        k = str(x.get("kimlik") or "").strip()
        sebep = str(x.get("sebep") or "").strip()
        if k not in acik:
            raise FikirHatasi(f"fikir_kapat[{i}]: '{k}' açık bir fikir değil "
                              f"(açık: {', '.join(sorted(acik)) or 'yok'})")
        if not sebep:
            raise FikirHatasi(f"fikir_kapat[{i}]: sebep boş — erken kapanış gerekçesini yazar")
        # Sebep de DÜZ METİNDİR: iki sayfa onu kaçırarak basar ve kaçmış etiket
        # yayın kapısını (sayfa sınavı 22) düşürür (inceleme 04.10.2026).
        if ETIKET.search(sebep):
            raise FikirHatasi(f"fikir_kapat[{i}].sebep: HTML etiketi taşıyor — sebep düz metindir")
        f = _f(acik[k], ev)
        kayit = {"kimlik": k, "sebep": sebep, "tarih": b.get("tarih")}
        if yazim_ani:
            kayit["yazim_ani"] = yazim_ani
        if f["tur"] != "olculemez":
            olc = [bacak_degeri(b, x["seri"], d) for x in f["bacaklar"]]
            if None in olc:
                raise FikirHatasi(f"fikir_kapat[{i}]: '{k}' bacaklarından biri bu sayıda "
                                  "ölçülemedi; çıkış seviyesi uydurulmaz")
            deger = yapi_degeri(f, [v for v, _ in olc])
            kayit.update({"cikis": _yuvarla(deger), "cikis_tarih": min(t for _, t in olc)})
        out.append(kayit)
    return out


# ─────────────────────────── defter: yayımlanmış sayılardan

def sayilar(bugun: str, kok: Path | None = None) -> list[dict]:
    """Bugünden ÖNCEKİ BÜTÜN sayılar (tarih sırasıyla).

    Defter KÜMÜLATİFTİR: ilk yazımda bir pencere vardı (ufuk + 30 gün) ve
    açıldığı sayı pencereden çıkan fikir, kapanış kaydı pencerede dursa bile
    defterden ve sayımdan sessizce düşüyordu — "şimdiye kadar" diyen sayım
    yedi ay sonra kendi geçmişini kaybedecekti (inceleme 04.10.2026)."""
    yol = (kok or KOK) / "site" / "src" / "data" / "bulten"
    out = []
    for p in sorted(yol.glob("20??-??-??.json")):
        if p.stem >= bugun:
            continue
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            continue
    return out


def defter(onceki: list[dict]) -> list[dict]:
    """Açılmış her fikir, üstüne bilinen kapanışı (yazarın ya da donmuş mekanik).

    Yalnız YAZILMIŞ sayıların fikirleri sayılır: yazılmamış bir sayı okura hiç
    çıkmadı. Donmuş mekanik kapanış ise herhangi bir sayının ölçülen
    katmanından okunur — ölçü veriden gelir, yayımdan bağımsızdır."""
    fikirler: dict[str, dict] = {}
    for b in onceki:
        if b.get("gundem_kaynagi") != "yazili":
            continue
        for f in b.get("fikirler") or []:
            if isinstance(f, dict) and f.get("kimlik"):
                fikirler[f["kimlik"]] = dict(f)
    for b in onceki:
        for x in (b.get("fikir_karne") or {}).get("kayitlar") or []:
            k = x.get("kimlik")
            if k in fikirler and x.get("durum") in KAPANMIS and "kapanis" not in fikirler[k]:
                fikirler[k]["kapanis"] = {a: x.get(a) for a in DONAN_ALANLAR}
        if b.get("gundem_kaynagi") != "yazili":
            continue
        # Yazarın erken kapanışı bir ÇIKIŞ EMRİDİR, çıkış fiyatı değil: çıkış,
        # kapatan sayının yayımından sonraki ilk kapanıştır (girişle simetrik).
        for x in b.get("fikir_kapat") or []:
            k = x.get("kimlik")
            if k in fikirler and "kapanis" not in fikirler[k] and "erken" not in fikirler[k]:
                fikirler[k]["erken"] = {"tarih": x.get("tarih"), "sebep": x.get("sebep"),
                                        "yazim_ani": x.get("yazim_ani")}
    return sorted(fikirler.values(), key=lambda f: f["kimlik"])


# ─────────────────────────── yol ve değerleme

def ham_seriler() -> dict:
    try:
        return json.loads(HAM.read_text(encoding="utf-8")).get("seri") or {}
    except (ValueError, OSError):
        return {}


# DİBS düğümlerinin GÜNLÜK serisi hattın kendi tarihçesinden. Bülten
# defterinin görüntüleri yalnız sabah ölçümünde ve içerik değiştiyse yazılıyor;
# ölçümün düştüğü iş günleri seride hiç yoktu (24.08 · 09.09 · 15.09) ve o
# günlerde aşılan bir seviye karnede görünmezdi (inceleme 04.10.2026).
DIBS_METRIK = KOK / "Aktarılacak Projeler" / "DIBS" / "data" / "metrik.csv"
DIBS_SUTUN = {"spot_3a": "n3a", "spot_6a": "n6a", "spot_1y": "n1y", "spot_2y": "n2y",
              "spot_3y": "n3y", "spot_5y": "n5y", "spot_7y": "n7y", "spot_9y": "n9y",
              "forward_1y1y": "f_1y1y", "forward_2y1y": "f_2y1y", "forward_2y3y": "f_2y3y"}
FONLAMA_GUNLUK = KOK / "Aktarılacak Projeler" / "Fonlama" / "data" / "gunluk.csv"


def _csv_seriler(yol: Path, sutunlar: dict[str, str], alt: str = "2025-01-01") -> dict[str, dict[str, float]]:
    import csv
    out: dict[str, dict[str, float]] = {}
    try:
        with yol.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                t = str(r.get("tarih") or "")[:10]
                if t < alt:
                    continue
                for anahtar, sutun in sutunlar.items():
                    v = _sayi(r.get(sutun))
                    if v is not None:
                        out.setdefault(anahtar, {})[t] = v
    except (OSError, ValueError):
        return {}
    return out


def dibs_seriler(dibs_gecmis: list[dict] | None = None, metrik: Path | None = DIBS_METRIK
                 ) -> dict[str, dict[str, float]]:
    """DİBS düğümlerinin günlük serisi: {anahtar: {iso: değer}}. Önce hattın
    günlük tarihçesi (metrik.csv), onda olmayan düğüm ve gün için bülten
    defterinin görüntüleri. Sınamalar `metrik=None` verir."""
    import gozlem
    kayitlar = dibs_gecmis if dibs_gecmis is not None else gozlem.gecmis_oku(DIBS_HAT)
    out: dict[str, dict[str, float]] = {}
    for k in kayitlar:
        d = k.get("d") or {}
        for a in DIBS:
            v, t = _sayi(d.get(a)), _iso(d.get(f"{a}_tarih") or d.get("_tarih"))
            if v is not None and t:
                out.setdefault(a, {})[t] = v
    if metrik is not None:
        for a, seri in _csv_seriler(metrik, DIBS_SUTUN).items():
            out.setdefault(a, {}).update(seri)
    return out


def faiz_serileri(ham: dict, fonlama: Path | None = FONLAMA_GUNLUK) -> dict[str, dict[str, float]]:
    """Taşıma için günlük faizler (yüzde): TLREF (Fonlama hattının günlük
    tablosu) ve ABD 3 aylık bono (piyasa ham önbelleği)."""
    out = _csv_seriler(fonlama, {"tlref": "tlref"}) if fonlama is not None else {}
    irx = ham.get("^IRX") or {}
    out["^IRX"] = {t: float(c) for t, c in zip(irx.get("tarih") or [], irx.get("kapanis") or [])
                   if _sayi(c) is not None}
    return out


def tasima(sid: str, yukari: bool, bas: str, son: str, faiz: dict) -> float | None:
    """[bas, son) takvim günleri boyunca biriken taşıma, yüzde: uzun dövizde
    (USD/TRY yukarı) TL faizi ödenir, döviz faizi alınır; kısa dövizde tersi.
    Her gün o güne kadar bilinen son oran kullanılır. Oran yoksa None."""
    if sid not in TASIMA:
        return 0.0
    tl, dv = (faiz.get(x) or {} for x in TASIMA[sid])
    if not tl or not dv:
        return None
    tl_g, dv_g = sorted(tl), sorted(dv)
    toplam, g, son_g = 0.0, date.fromisoformat(bas), date.fromisoformat(son)
    import bisect
    while g < son_g:
        i = g.isoformat()
        a = bisect.bisect_right(tl_g, i) - 1
        b_ = bisect.bisect_right(dv_g, i) - 1
        if a < 0 or b_ < 0:
            return None
        toplam += (tl[tl_g[a]] - dv[dv_g[b_]]) / 365.0
        g += timedelta(days=1)
    return round((-toplam if yukari else toplam), 4)


def _bacak_serisi(sid: str, ham: dict, dibs: dict) -> dict[str, float]:
    if sid.startswith("dibs:"):
        return dibs.get(sid[5:], {})
    s = ham.get(sid) or {}
    return {t: float(c) for t, c in zip(s.get("tarih") or [], s.get("kapanis") or [])
            if _sayi(c) is not None}


def yol(f: dict, ham: dict, dibs: dict, ev: dict[str, Seri]) -> list[tuple[str, float]]:
    """Girişten sonraki her ortak kapanışta yapının değeri.

    Fiyat bacağı GİRİŞ GÜNÜNE GÖRE GETİRİYLE ilerletilir, kayıtlı seviyeyle
    değil: vadeli seriler devir günlerinde geriye ölçekleniyor (piyasa
    `_roll_duzelt`) ve kayıtlı seviye ile ölçeklenmiş tarihçe devirden sonra
    ayrışır. Getiri bacağı fark olarak ilerletilir. Giriş günü seride yoksa
    kayıtlı seviye çıpa olur."""
    f = _f(f, ev)
    seriler, cipa = [], []
    for x in f["bacaklar"]:
        s = _bacak_serisi(x["seri"], ham, dibs)
        seriler.append(s)
        cipa.append(s.get(x["tarih"], x["deger"]))
    giris_gunu = max(x["tarih"] for x in f["bacaklar"])
    ortak = sorted(set.intersection(*[set(s) for s in seriler]))
    out = []
    for t in ortak:
        if t <= giris_gunu:
            continue
        v = []
        for x, s, c in zip(f["bacaklar"], seriler, cipa):
            if ev.get(x["seri"]) and ev[x["seri"]].tip == "getiri":
                v.append(float(x["deger"]) + (s[t] - c))
            else:
                v.append(float(x["deger"]) * (s[t] / c) if c else s[t])
        out.append((t, yapi_degeri(f, v)))
    return out


def yapi_sigma(f: dict, ham: dict, dibs: dict, ev: dict[str, Seri], n: int = 20) -> float | None:
    """Yapının girişten ÖNCEKİ son n ortak kapanıştaki günlük değişiminin
    standart sapması, sonucun biriminde (getiride bp, fiyatta yüzde). Stop
    mesafesi bununla kıyaslanır: bir günlük σ'nın altındaki stop gürültüde
    tetiklenir. Yeterli gözlem yoksa None (ölçülemeyen uydurulmaz)."""
    if f.get("tur") in ("olculemez", None) or not f.get("bacaklar"):
        return None
    ff = _f(f, ev)
    seriler = [_bacak_serisi(x["seri"], ham, dibs) for x in f["bacaklar"]]
    sinir = min(x["tarih"] for x in f["bacaklar"])
    ortak = sorted(t for t in set.intersection(*[set(s_) for s_ in seriler]) if t <= sinir)[-(n + 1):]
    if len(ortak) < max(6, n // 2):
        return None
    deg = [yapi_degeri(ff, [s_[t] for s_ in seriler]) for t in ortak]
    if birim(ff) == "%":
        fark = [(b_ - a) * 100 for a, b_ in zip(deg, deg[1:])]
    elif birim(ff) == "bp":
        fark = [b_ - a for a, b_ in zip(deg, deg[1:])]
    else:
        fark = [(b_ / a - 1) * 100 for a, b_ in zip(deg, deg[1:]) if a]
    if len(fark) < 5:
        return None
    ort = sum(fark) / len(fark)
    return round((sum((x - ort) ** 2 for x in fark) / (len(fark) - 1)) ** 0.5, 2)


# Ufuk günü kapanışı gelmeden ufuk kapanışı kurulmaz; bu kadar takvim günü
# beklenir, sonra son ölçülen kapanışla kapanır (kaynak o günü hiç vermeyebilir).
UFUK_BEKLEME_GUN = 5


def _ilk_kapanis_sonra(y: list[tuple[str, float]], an: datetime | None, taban: str,
                       f: dict, ev: dict[str, Seri]) -> tuple[str, float] | None:
    """Yazım anından SONRA kapanan ilk ortak seans: bütün bacakların o günkü
    kapanış anı `an`dan sonra olmalı. An bilinmiyorsa (eski kayıt) gün kuralı:
    tarihi `taban`dan küçük olmayan ilk kapanış."""
    for t, v in y:
        if t < taban:
            continue
        if an is None or all(kapanis_ani(x["seri"], t, ev) > an for x in f["bacaklar"]):
            return t, v
    return None


# Değerlenemeyen günde önceki ölçümden taşınan alanlar (kendi tarihleriyle).
TASINAN_ALANLAR = ("giris_fiili", "giris_fiili_tarih", "son", "son_tarih", "sonuc", "sonuc_r",
                   "spot_sonuc", "tasima", "tasima_olculemedi", "ic_deger")


def degerle(f: dict, bugun: str, ham: dict, dibs: dict, ev: dict[str, Seri],
            faiz: dict | None = None, onceki_kayit: dict | None = None) -> dict:
    """Bir fikrin bugünkü karne satırı. `onceki_kayit`: bir önceki sayının
    karnesindeki açık kayıt — fikir bugün değerlenemezse son ölçülen değerler
    oradan, KENDİ tarihleriyle taşınır."""
    ff = _f(f, ev)
    satir = {a: f.get(a) for a in ("kimlik", "acilis", "baslik", "tur", "sinif", "yon",
                                   "giris", "giris_tarih", "hedef", "stop", "ufuk",
                                   "yapi_metni", "yon_metni", "enstruman", "dayanak",
                                   "senaryo", "opsiyon", "olculemez_sebep", "ondalik",
                                   "getiri_risk")
             if f.get(a) is not None}
    kap = f.get("kapanis")
    erken = f.get("erken") or {}
    if f["tur"] == "olculemez":
        # Ölçülemeyen fikrin de yaşam döngüsü var: donmuş kapanış, yazarın erken
        # kapanışı ve ufuk. Sonucu yoktur ama kapanış tarihi ve sebebi yazılır
        # (ilk yazımda erken kapanış işlemiyor, ufku dolan fikir "kapananlar"a
        # hiç girmiyordu — inceleme 04.10.2026).
        if kap:
            satir.update({a: v for a, v in kap.items() if v is not None})
            return satir
        if erken.get("tarih"):
            satir.update({"durum": "geri_cekildi", "kapanis_tarih": erken["tarih"],
                          "sebep": erken.get("sebep")})
            return satir
        kalan = (date.fromisoformat(f["ufuk"]) - date.fromisoformat(bugun)).days
        if kalan >= 0:
            satir.update({"durum": "olculemez", "kalan_gun": kalan})
        else:
            satir.update({"durum": "sure_olculemez", "kapanis_tarih": f["ufuk"]})
        return satir
    satir.update({"birim": birim(ff), "sonuc_birim": sonuc_birim(ff)})
    if kap:
        satir.update({a: v for a, v in kap.items() if v is not None})
        satir.setdefault("kapanis_tarih", kap.get("son_tarih"))
        return satir
    # VADELİ DEVİR. Enerji vadelileri devir günlerinde geriye ölçekleniyor ve
    # yol getiriyle kuruluyor (bkz. `yol`), yani devir sonrası "son" GİRİŞ
    # KONTRATI cinsindendir — sayfadaki kotasyondan devir farkı kadar ayrışır
    # ve satır bunu devir günüyle söyler. Düzeltme o gün kurulamadıysa
    # (`roll_bilinmiyor`) seri kontrat atlaması taşıyabilir: fikir o gün
    # DEĞERLENMEZ, sahte bir stop donmasın.
    devir, bilinmiyor = [], []
    for x in f["bacaklar"]:
        h = ham.get(x["seri"]) or {}
        devir += [d for d in h.get("devir_gunleri") or [] if d > x["tarih"]]
        if h.get("roll_bilinmiyor"):
            bilinmiyor.append(x["seri"])
    if devir:
        satir["devir"] = sorted(set(devir))
    ufuk = f["ufuk"]
    kalan = (date.fromisoformat(ufuk) - date.fromisoformat(bugun)).days
    if bilinmiyor:
        # Fiili giriş ve son ölçülen değer KAYBOLMAZ: önceki ölçümün değerleri
        # kendi tarihleriyle taşınır, kayıt "değerlenmedi" der. Eskiden kayıt
        # yalnız durum ve kalan gün taşıyordu; sayfa girilmiş bir fikri "giriş
        # bekleniyor" diye basıyor, son değeri ve sonucu siliyordu (inceleme
        # 04.10.2026 — roll_bilinmiyor 31.08'de NG=F'te gerçekten görüldü).
        satir.update({"durum": "acik", "degerlenmedi": "vadeli devir düzeltmesi kurulamadı",
                      "kalan_gun": kalan})
        o = onceki_kayit if isinstance(onceki_kayit, dict) and onceki_kayit.get("durum") == "acik" else {}
        satir.update({a: o[a] for a in TASINAN_ALANLAR if o.get(a) is not None})
        if o.get("giris_bekleniyor"):
            satir["giris_bekleniyor"] = True
        return satir
    y = yol(f, ham, dibs, ev)
    opsiyon = f["tur"] == "opsiyon"
    sid0 = f["bacaklar"][0]["seri"]
    tasimali = f["tur"] == "yalin" and sid0 in TASIMA

    def taşıma_payi(t0: str, t: str) -> float | None:
        if not tasimali:
            return 0.0
        return tasima(sid0, f["yon"] == "yukari", t0, t, faiz or {})

    def risk_birimi(v0: float) -> float | None:
        if opsiyon or f.get("stop") is None:
            return None
        r = abs(sonuc(ff, f["stop"], v0))
        return r if r > 0 else None

    def yaz_sonuc(t0, v0, t, v):
        if opsiyon:
            return
        sp = sonuc(ff, v, v0)
        ts = taşıma_payi(t0, t)
        satir["sonuc"] = _yuvarla(sp + (ts or 0.0), 2)
        if tasimali:
            satir["spot_sonuc"] = _yuvarla(sp, 2)
            satir["tasima"] = _yuvarla(ts, 2) if ts is not None else None
            if ts is None:
                satir["tasima_olculemedi"] = True
        rb = risk_birimi(v0)
        if rb:
            satir["sonuc_r"] = _yuvarla(satir["sonuc"] / rb, 2)

    def kapat(durum, t0, v0, t, v):
        satir.update({"durum": durum, "son": _yuvarla(v), "son_tarih": t, "kapanis_tarih": t})
        if opsiyon:
            satir.update({"sonuc": _yuvarla(opsiyon_odeme(ff, v, v0), 2),
                          "sonuc_turu": "odeme" if durum == "vade" else "ic_deger"})
        else:
            yaz_sonuc(t0, v0, t, v)
        if durum == "geri_cekildi":
            satir["sebep"] = erken.get("sebep")
        return satir

    # FİİLİ GİRİŞ YAZIMDAN SONRA KAPANAN İLK SEANSTIR. Referans seviye bir önceki
    # seansın kapanışıdır ve yazar onu yazarken gece boyunca olanı görüyor (Asya
    # seansı, canlı kur): karne referanstan başlasaydı fikre kendisinin
    # yakalayamayacağı gecelik hareketi kazandırırdı. Gün değil SAAT sorulur:
    # hafta içi akşam yazılan fikir o günün kapanışını görmüştür. Hedef ve stop
    # fiili girişten SONRAKİ kapanışlarda sorulur.
    giris = _ilk_kapanis_sonra(y, _an(f.get("yazim_ani")), f["acilis"], f, ev)
    if giris is None or giris[0] > ufuk:
        # Ufuktan SONRA bir kapanış seride varsa, ufka kadar giriş gerçekten
        # olmadı: ölçülemedi ve donar. Hiç kapanış yoksa kaynak gecikmiş
        # olabilir — ufuk kapanışıyla aynı kural: UFUK_BEKLEME_GUN beklenir
        # (eskiden ufkun ertesi günü donuyordu; inceleme 04.10.2026).
        bekledi = (date.fromisoformat(bugun) - date.fromisoformat(ufuk)).days > UFUK_BEKLEME_GUN
        if bugun > ufuk and (giris is not None or bekledi):
            satir.update({"durum": "olculemedi", "kapanis_tarih": ufuk})
        else:
            satir.update({"durum": "acik", "giris_bekleniyor": True, "kalan_gun": kalan})
            if bugun > ufuk:
                satir["ufuk_bekleniyor"] = True
        return satir
    t0, v0 = giris
    satir.update({"giris_fiili": _yuvarla(v0), "giris_fiili_tarih": t0})
    yukari = f["yon"] == "yukari"
    if not opsiyon:
        if (v0 >= f["hedef"] or v0 <= f["stop"]) if yukari else (v0 <= f["hedef"] or v0 >= f["stop"]):
            # Giriş kapanışı seviyelerden birinin ötesinde: yapı kurulamadan
            # geçersiz kaldı. Sonucu yoktur ve kazanç oranına girmez.
            satir.update({"durum": "giriste_gecersiz", "son": _yuvarla(v0), "son_tarih": t0,
                          "kapanis_tarih": t0})
            return satir
    # Erken kapanış bir ÇIKIŞ EMRİDİR: kapatan sayının yazımından sonra kapanan
    # ilk seansta gerçekleşir (girişle simetrik).
    cikis = None
    if erken.get("tarih"):
        sonraki = [(t, v) for t, v in y if t >= t0]
        cikis = _ilk_kapanis_sonra(sonraki, _an(erken.get("yazim_ani")), erken["tarih"], f, ev)
        if cikis and cikis[0] == t0:
            # Çıkış emri girişle AYNI kapanışa düştü: yapı hiç taşınmadı. Mekanik
            # sonuç sıfırdır ama bu bir ölçüm değildir — "başabaş" diye basılıp
            # kazanç oranının paydasına ve R ortalamasına girerdi (inceleme
            # 04.10.2026). Sonucu yoktur; kapanışı ve sebebi yazılır.
            satir.update({"durum": "geri_cekildi", "son": _yuvarla(v0), "son_tarih": t0,
                          "kapanis_tarih": t0, "sebep": erken.get("sebep"), "giris_oncesi": True})
            return satir
    son = (t0, v0)
    ufku_gecen = False
    for t, v in y:
        if t <= t0:
            continue
        if t > ufuk:
            ufku_gecen = True
            break
        son = (t, v)
        if cikis and t >= cikis[0]:
            return kapat("geri_cekildi", t0, v0, t, v)
        if not opsiyon:
            hedefte = v >= f["hedef"] if yukari else v <= f["hedef"]
            stopta = v <= f["stop"] if yukari else v >= f["stop"]
            if hedefte or stopta:
                return kapat("hedef" if hedefte else "stop", t0, v0, t, v)
    if bugun > ufuk:
        # Ufuk kapanışı ancak ufuk gününün kapanışı geldiyse (ya da ufuktan
        # sonra bir kapanış seriye girdiyse) kurulur; yoksa ölçüm UFUK_BEKLEME_GUN
        # boyunca bekler, sonra son ölçülen kapanışla kapanır ve bunu yazar.
        bekledi = (date.fromisoformat(bugun) - date.fromisoformat(ufuk)).days > UFUK_BEKLEME_GUN
        if ufku_gecen or son[0] == ufuk or bekledi:
            kapat("vade" if opsiyon else "sure", t0, v0, son[0], son[1])
            if son[0] < ufuk and not ufku_gecen:
                satir["not"] = "ufuk günü kapanışı seride yok; son ölçülen kapanışla kapandı"
            return satir
        # Değerlenmemiş değil: son kapanışa kadar değerlendi, ufuk günü
        # kapanışını BEKLİYOR. İkisi tek alanda dururken sayfa "değerlenmedi"
        # yazıp yanında sonuç basıyordu (inceleme 04.10.2026).
        satir["ufuk_bekleniyor"] = True
    t, v = son
    satir.update({"durum": "acik", "son": _yuvarla(v), "son_tarih": t, "kalan_gun": kalan})
    if opsiyon:
        satir["ic_deger"] = _yuvarla(opsiyon_odeme(ff, v, v0), 2)
    else:
        yaz_sonuc(t0, v0, t, v)
    if erken.get("tarih"):
        satir["cikis_bekleniyor"] = True
    return satir


def karne(bugun: str, onceki: list[dict] | None = None, ham: dict | None = None,
          dibs_gecmis: list[dict] | None = None, haftalik: bool = False,
          metrik: Path | None = DIBS_METRIK, fonlama: Path | None = FONLAMA_GUNLUK,
          sabit: dict[str, dict] | None = None) -> dict:
    """Ölçülen katmanın fikir bloğu: açık fikirler (bugünkü değerleriyle), yeni
    kapananlar ve bütün kapanmış fikirlerin sayımı. AĞA ÇIKMAZ.

    `sabit`: AYNI sayının daha önceki bir ölçümünde KAPANMIŞ sayılan kayıtlar
    (kimlik → kayıt). Bir kapanış sayıya yazıldıktan sonra değişmez — aynı
    sayının içinde de: sabah 03:23 ölçümünde okura "stopta kapandı" denmiş bir
    kayıt, kaynak bir barı geri çektiği için 03:51 yedek ölçümünde "açık"a
    dönmemeli. Koruma eskiden yalnız YAZILMIŞ sayıda ve karne kurulduktan SONRA
    yapılıyordu: yazılmamış sayıda kapanış kayboluyor, yazılmış sayıda da sayım
    yeni ölçümden kalıyordu (kayıt "kapandı", sayım "açık" diyordu — inceleme
    04.10.2026). Sabit kayıt sayımdan ÖNCE yerine konur, tek hesap."""
    onceki = sayilar(bugun) if onceki is None else onceki
    ham = ham_seriler() if ham is None else ham
    dibs = dibs_seriler(dibs_gecmis, metrik)
    faiz = faiz_serileri(ham, fonlama)
    ev = evren()
    fikirler = defter(onceki)
    # Her fikrin en son ölçülen kaydı (sayı sırasıyla): değerlenemeyen günde
    # son değerler oradan taşınır (bkz. degerle).
    son_kayit: dict[str, dict] = {}
    for b in onceki:
        for x in (b.get("fikir_karne") or {}).get("kayitlar") or []:
            if isinstance(x, dict) and x.get("kimlik"):
                son_kayit[str(x["kimlik"])] = x
    kayitlar = [degerle(f, bugun, ham, dibs, ev, faiz, son_kayit.get(f["kimlik"])) for f in fikirler]
    sabit = {k: v for k, v in (sabit or {}).items()
             if isinstance(v, dict) and v.get("durum") in KAPANMIS}
    if sabit:
        gorulen = {k.get("kimlik") for k in kayitlar}
        kayitlar = [sabit.get(k.get("kimlik"), k) for k in kayitlar]
        kayitlar += [v for k, v in sorted(sabit.items()) if k not in gorulen]
    pencere = KAPANAN_PENCERE["haftalik" if haftalik else "gunluk"]
    sinir = (date.fromisoformat(bugun) - timedelta(days=pencere)).isoformat()
    # DONMA GÖSTERİMDEN BAĞIMSIZDIR: bugün İLK KEZ kapanmış sayılan kayıt
    # (önceki bir sayıda donmamış olan) kapanış tarihi gösterim penceresinden
    # eski olsa da bu sayının karnesine yazılır — yazılmasaydı hiçbir sayıda
    # donmaz, her gün kaynağın o günkü serisinden yeniden hesaplanırdı
    # (inceleme 04.10.2026: devir düzeltmesi bir hafta kurulamayan fikir).
    donmus = {f["kimlik"] for f in fikirler if "kapanis" in f}
    gosterilen = [k for k in kayitlar
                  if k.get("durum") in ("acik", "olculemez")
                  or (k.get("durum") in KAPANMIS and (str(k.get("kapanis_tarih") or "") >= sinir
                                                      or k.get("kimlik") not in donmus))]
    kapanan = [k for k in kayitlar if k.get("durum") in KAPANMIS]
    # Oran YALNIZ sonucu ölçülmüş, primi olmayan fikirlerden: opsiyonun ödemesi
    # primsiz olduğu için "kazandı" sayılamaz, ölçülemeyen fikrin sonucu yoktur.
    # Taşıması ölçülemeyen USD/TRY kaydı da girmez: sonucu yalnız spottur,
    # pozisyonun sonucu değildir (inceleme 04.10.2026).
    olculen = [k for k in kapanan if k.get("tur") not in ("opsiyon", "olculemez")
               and k.get("sonuc") is not None and not k.get("tasima_olculemedi")]
    sayim = {
        "acik": sum(1 for k in kayitlar if k.get("durum") == "acik"),
        "olculemez_acik": sum(1 for k in kayitlar if k.get("durum") == "olculemez"),
        "kapanan": len(kapanan),
        "olculen_kapanan": len(olculen),
        "kazanan": sum(1 for k in olculen if k["sonuc"] > 0),
        "hedef": sum(1 for k in kapanan if k.get("durum") == "hedef"),
        "stop": sum(1 for k in kapanan if k.get("durum") == "stop"),
        "sure": sum(1 for k in kapanan if k.get("durum") == "sure"),
        "geri_cekildi": sum(1 for k in kapanan if k.get("durum") == "geri_cekildi"),
        "giriste_gecersiz": sum(1 for k in kapanan if k.get("durum") == "giriste_gecersiz"),
        "vade": sum(1 for k in kapanan if k.get("durum") == "vade"),
        "olculemedi": sum(1 for k in kapanan if k.get("durum") == "olculemedi"),
        "sure_olculemez": sum(1 for k in kapanan if k.get("durum") == "sure_olculemez"),
    }
    # Ortalamalar birim birim (bp ile yüzde toplanmaz) ve RİSK KATI olarak (R =
    # sonuç / fiili girişten stop mesafesi): farklı oynaklıktaki yapıların bp'si
    # aynı ortalamada eşit ağırlık almasın — bir TL eğri stopu yedi ABD
    # hedefini silerdi (inceleme 04.10.2026).
    for ad, b_ in (("bp", "bp"), ("yuzde", "%")):
        grup = [k["sonuc"] for k in olculen if k.get("sonuc_birim") == b_]
        sayim[f"ortalama_{ad}"] = round(sum(grup) / len(grup), 2) if grup else None
        sayim[f"n_{ad}"] = len(grup)
    rler = [k["sonuc_r"] for k in olculen if isinstance(k.get("sonuc_r"), (int, float))]
    sayim["ortalama_r"] = round(sum(rler) / len(rler), 2) if rler else None
    sayim["n_r"] = len(rler)
    return {"kayitlar": gosterilen, "sayim": sayim, "kapanan_pencere_gun": pencere}


def acik_fikirler(bugun: str, onceki: list[dict] | None = None) -> dict[str, dict]:
    """Defterde kapanışı ve erken kapanış emri olmayan fikirler."""
    onceki = sayilar(bugun) if onceki is None else onceki
    return {f["kimlik"]: f for f in defter(onceki) if "kapanis" not in f and "erken" not in f}


def kapatilabilir(b: dict) -> dict[str, dict]:
    """Bu sayıda `fikir_kapat` ile kapatılabilecek fikirler: açık fikirler eksi
    bu sayının karnesinin mekanik olarak KAPANMIŞ saydıkları. Tek tanım: yazma
    kapısı ve `--sina` ön sınaması buradan okur (ikisi ayrı süzgeç kurunca ön
    sınama ✓ deyip yazma kapısı reddediyordu — inceleme 04.10.2026)."""
    kapali = {k.get("kimlik") for k in (b.get("fikir_karne") or {}).get("kayitlar") or []
              if k.get("durum") in KAPANMIS}
    return {k: v for k, v in acik_fikirler(str(b["tarih"])).items() if k not in kapali}


# ─────────────────────────── komut satırı

def _yaz_sonuc(v, birim_: str) -> str:
    return f"{bicim.sayi(v, 1)} bp" if birim_ == "bp" else bicim.yuzde(v, 2)


def _yaz_deger(v, birim_: str, ondalik: int = 2) -> str:
    if v is None:
        return "—"
    if birim_ == "%":
        return bicim.yuzde(v, 2)
    if birim_ == "bp":
        return f"{bicim.sayi(v, 0)} bp"
    if birim_ == "oran":
        return bicim.sayi(v, 4)
    return bicim.sayi(v, ondalik)


def main() -> int:
    import argparse
    sys.path.insert(0, str(BURASI))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evren", action="store_true")
    ap.add_argument("--karne", action="store_true")
    ap.add_argument("--sina", default=None, help="yama JSON'u: fikirlerini bugünkü sayıya karşı sına")
    ap.add_argument("--tarih", default=None)
    a = ap.parse_args()
    t = a.tarih or date.today().isoformat()
    yol_ = BULTEN / f"{t}.json"
    b = json.loads(yol_.read_text(encoding="utf-8")) if yol_.exists() else {}
    if a.evren:
        ev = evren()
        d = _dibs_an(b) if b else {}
        print(f"Ölçülebilir evren — {t} sayısının ölçülen katmanından (seri · ad · değer · tarih · günlük σ)")
        for sid, s in ev.items():
            r = bacak_degeri(b, sid, d) if b else None
            sg = sigma_gun(b, sid) if b else None
            deger = ("—" if not r else
                     (bicim.yuzde(r[0], 2) if s.tip == "getiri" else bicim.sayi(r[0], s.ondalik)))
            print(f"  {sid:22s} {s.ad:36s} {deger:>12s}  {r[1] if r else '':10s}"
                  + (f"  σ {bicim.sayi(sg, 2) + ' bp' if s.tip == 'getiri' else bicim.yuzde(sg, 2)}" if sg else ""))
        print("Dışarıda: " + " · ".join(f"{k} ({v})" for k, v in DISLANAN.items()))
        return 0
    if a.sina:
        yama = json.loads(Path(a.sina).read_text(encoding="utf-8"))
        try:
            for f in dogrula_liste(yama.get("fikirler") or [], b):
                rr = f.get("getiri_risk")
                print(f"✓ {f['kimlik']} {f['baslik']} — {f['yapi_metni']} · {f['yon_metni']} · "
                      f"giriş {_yaz_deger(f.get('giris'), f.get('birim', ''))}"
                      + (f" · getiri/risk {bicim.sayi(rr, 2)}" if rr else "")
                      + (f" · stop mesafesi {_yaz_sonuc(f['stop_mesafe'], f['sonuc_birim'])}"
                         f" (günlük σ {_yaz_sonuc(f['sigma_gun'], f['sonuc_birim'])})"
                         if f.get("sigma_gun") else ""))
            if yama.get("fikir_kapat"):
                for x in kapat_dogrula(yama["fikir_kapat"], b, kapatilabilir(b)):
                    print(f"✓ kapanış {x['kimlik']}: çıkış {x.get('cikis')}")
        except FikirHatasi as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2
        return 0
    k = (b.get("fikir_karne") if b.get("fikir_karne") else karne(t))
    for s in k.get("kayitlar") or []:
        print(f"  {s['kimlik']:14s} {s.get('durum', ''):12s} {s.get('baslik', '')}"
              f"  giriş {_yaz_deger(s.get('giris'), s.get('birim', ''))}"
              f" → {_yaz_deger(s.get('son'), s.get('birim', ''))}"
              f"  sonuç {bicim.degisim(s.get('sonuc'), s.get('sonuc_birim') or '%', 1) if s.get('sonuc') is not None else '—'}")
    print("  sayım:", json.dumps(k.get("sayim"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(BURASI))
    sys.exit(main())
