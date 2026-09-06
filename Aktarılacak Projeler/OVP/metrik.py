# -*- coding: utf-8 -*-
"""OVP hattı — ölçüm katmanı.

Girdi:  data/kur.csv · data/faiz.csv · data/tufe.csv · data/veri_durum.json
Çıktı:  data/metrik_ima.csv · data/metrik_zincir.csv · data/metrik_carry.csv
        data/metrik_revizyon.csv · data/metrik_ozet.json · <kök>/uyarilar.json

ÖLÇÜNÜN TANIMLARI — hepsi burada, tek yerde
-------------------------------------------
İMA EDİLEN ORTALAMA KUR
    ima(yıl) = GSYH(milyar TL) ÷ GSYH(milyar dolar)
    Program bir kur patikası yayımlamaz; iki GSYH satırının oranı onu ele
    verir. Bu bir tahmin değil, tablonun kendi ARİTMETİĞİDİR.

YÖNTEM SINAMASI — "ihmal edilebilir" bir hükümdür, varsayım değil
    Programın dipnotu milli gelir hesabında ihracat-ithalat AĞIRLIKLI kur
    kullanıldığını söylüyor, düz USD/TRY değil. Uyarı gerçek. Ama sınanabilir:
    KAPANMIŞ ve GERÇEKLEŞME olarak yayımlanmış bir yılda ima edilen kur ile o
    yılın günlük ortalaması karşılaştırılır. Sınama HER KOŞUDA yeniden yapılır
    ve sonucu yayımlanır; fark büyürse okur bunu görmeli.
    Sınamaya yalnız GERÇEKLEŞME sütunları girer: "gerçekleşme tahmini" (GT)
    sütunundaki fark yöntem farkı değil TAHMİN hatasıdır, program (P) sütunu
    ise henüz olmamış bir yıldır. Ayrım olmadan geçen yılın 2025 sütunundaki
    fark yöntem sapması sanılırdı.

İÇİNDE BULUNULAN YIL — cevabı HER GÜN DEĞİŞEN soru
    Yıl ortalaması gerçekleşen günlerin ve kalan günlerin ortalamasıdır:
        ort_hedef · (n_ger + n_kalan) = ort_ger · n_ger + ort_kalan · n_kalan
    Buradan "kalan günlerin tutturması gereken ortalama" tek bilinmeyen olarak
    çözülür. Kalan gün sayısı HAFTA İÇİ günlerdir ve resmî tatiller
    DÜŞÜLMEZ — çünkü gelecekteki tatilleri saymak bir varsayımdır. Etkisi
    ölçülüp ayrıca yazılır (`kalan_tatil_payi`): serinin KENDİ geçmişinde aynı
    takvim penceresinde kaç hafta içi günün gözlemsiz kaldığının ortancası.

İKİ PATİKA — sonucun kendisi bir sağlamlık ölçüsüdür
    Kalan günlerin ortalaması bilindiğinde yıl sonu SEVİYESİ hâlâ patika
    varsayımına bağlıdır. İkisi de hesaplanır ve İKİSİ DE yayımlanır:
      · doğrusal — kur bugünden yıl sonuna düz artar. Patika BUGÜNÜ İÇERMEZ
        (bugünkü seviye zaten gerçekleşen ortalamanın içinde), yani yıl sonu
        s0 + (ort_kalan − s0)·2n ÷ (n+1) olur; "uçların ortası" kestirmesi
        bugünü bir kez daha sayardı.
      · üstel — kur her gün sabit YÜZDE artar; ortalamayı tutturan günlük
        büyüme oranı ikiye bölme ile çözülür (kapalı çözümü yok).
    İki varsayım AYNI ortalamayı tutturur, yani fark yalnız patikanın
    bükümünden gelir. Birbirine yakın çıkmaları bir SONUÇTUR ve okur görmeli:
    yıl sonu iması patika varsayımına duyarlı değil.

ZİNCİRLEME — her yılın çıkışı sonrakinin girişi
    İçinde bulunulan yılın çıkışı yukarıdaki üstel patikadan gelir. Sonraki
    yıllarda giriş bellidir (önceki yılın çıkışı) ve ortalama bellidir
    (programın ima ettiği ortalama); yıl sonu aynı üstel çözümle bulunur.

REEL TL — ÇARPIMSAL, çıkarma değil
    reel = (1 + TÜFE) ÷ (1 + devalüasyon) − 1
    Yüzde otuzların üstündeki oranlarda "TÜFE − deval" ile çarpımsal ölçü
    puanlarca ayrışır. Aradaki puan farkı ayrıca yazılır ama manşet çarpımsaldır.

TAŞIMA (CARRY)
    Gerçekleşen: TL gecelik faizin BİLEŞİK getirisi eksi kur değişimi.
      TL faktörü = Π (1 + gecelik_i ÷ 100 ÷ 365)   — GÖZLEM GÜNLERİ üzerinden,
      yani her kotasyon bir günlük faiz taşır; hafta sonu ayrıca eklenmez.
      Kur faktörü = son ÷ yıl içi ilk gözlem.
      net = TL faktörü ÷ kur faktörü − 1; yıllıklandırma TAKVİM günüyle.
    İleriye dönük: BİR VARSAYIM TAŞIR — TL faizinin bugünkü seviyesinde SABİT
      kalması. Varsayım okura yazılır. İki konvansiyon birden verilir:
      · basit  = (1 + faiz) ÷ (1 + deval) − 1  — yıllık basit kotasyonun yıllık
        devalüasyona bölünmesi; ex-ante reel faizle AYNI konvansiyon, yani
        sayfadaki iki sayı birbiriyle kıyaslanabilir.
      · bileşik = Π(1 + faiz÷365) ÷ (1 + deval) − 1 — gecelikte dönen bir
        pozisyonun gerçekten biriktirdiği getiri; gerçekleşen bacakla AYNI
        konvansiyon.
      Tek konvansiyon yazılsaydı sayfadaki iki sayıdan biri öbürüyle
      kıyaslanamaz olurdu; hangisinin ne ölçtüğü adında duruyor.

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

import numpy as np
import pandas as pd

import veri
from veri import (PROJE, VERI, BLOK_OKUR, SAG_UC_IZI, YONTEM_ESIK_YUZDE,
                  TUTARLILIK_ESIK_PUAN)

_UYARI: list[str] = []


def _bicim():
    try:
        import bicim
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def _oku(ad: str, tarih_kolonu: str = None) -> pd.DataFrame:
    yol = VERI / ad
    if not yol.exists():
        return pd.DataFrame()
    return pd.read_csv(yol, index_col=0, parse_dates=True).sort_index()


# ===========================================================================
#  ÜSTEL PATİKA — kapalı çözümü yok, ikiye bölme ile çözülür
# ===========================================================================
def _ustel_ortalama(s0: float, g: float, n: int) -> float:
    t = np.arange(1, n + 1)
    return float((s0 * g ** t).mean())


def ustel_cikis(s0: float, hedef_ort: float, n: int) -> float | None:
    """`n` günde ortalaması `hedef_ort` olan SABİT YÜZDELİ patikanın son değeri.

    Ortalama g'de KESİN ARTANDIR, yani ikiye bölme her zaman yakınsar; ama
    hedef ortalamanın erişilebilir aralıkta olması gerekir (çok küçük bir
    hedef, negatif olmayan bir kurla tutturulamaz). Aralık dışıysa None:
    ölçülemeyen boş bırakılır.
    """
    if not (s0 and s0 > 0) or n <= 0 or not hedef_ort or hedef_ort <= 0:
        return None
    lo, hi = 0.5, 2.0
    if not (_ustel_ortalama(s0, lo, n) <= hedef_ort <= _ustel_ortalama(s0, hi, n)):
        return None
    for _ in range(200):
        m = (lo + hi) / 2
        if _ustel_ortalama(s0, m, n) < hedef_ort:
            lo = m
        else:
            hi = m
    return float(s0 * ((lo + hi) / 2) ** n)


def dogrusal_cikis(s0: float, hedef_ort: float, n: int) -> float | None:
    """`n` günde ortalaması `hedef_ort` olan DOĞRUSAL patikanın son değeri.

    GÜN SAYISI ARGÜMANDIR, çünkü patika BUGÜNÜ İÇERMEZ: bugünkü seviye zaten
    gerçekleşen ortalamanın içinde ve bir daha sayılamaz. Patika s0'dan
    başlayıp n adımda X'e varan doğru üzerindeki 1..n numaralı noktalardır:
        ortalama = s0 + (X − s0)·(n+1) ÷ (2n)
    "Ortalama uçların ortasıdır" kestirmesi (X = 2·ortalama − s0) bugünü de
    sayar ve kısıtı SAĞLAMAZ; üstel çözüm bugünü saymadığı için iki patika o
    hâlde farklı kısıtları tutturur ve sayfada "iki varsayım aynı sonucu
    veriyor" diye yayımlanan sağlamlık sonucu bir tesadüfe dönerdi.
    """
    if not (s0 and s0 > 0) or not hedef_ort or n <= 0:
        return None
    return float(s0 + (hedef_ort - s0) * 2 * n / (n + 1))


# ===========================================================================
#  KUR ÖLÇÜLERİ
# ===========================================================================
def yil_ozeti(kur: pd.Series, yil: int) -> dict | None:
    s = kur[kur.index.year == yil]
    if s.empty:
        return None
    return {"yil": yil, "n": int(len(s)), "ortalama": float(s.mean()),
            "ilk": float(s.iloc[0]), "son": float(s.iloc[-1]),
            "ilk_gun": s.index[0].strftime("%Y-%m-%d"),
            "son_gun": s.index[-1].strftime("%Y-%m-%d")}


def ima_kur(p: dict) -> dict[int, float]:
    """ima(yıl) = TL GSYH ÷ dolar GSYH. Her iki satır da olmayan yıl DÜŞER."""
    tl = veri.satir_serisi(p, "gsyh_tl")
    usd = veri.satir_serisi(p, "gsyh_usd")
    return {y: tl[y] / usd[y] for y in sorted(tl) if y in usd and usd[y]}


def yontem_sinamasi(kayit: dict, kur: pd.Series, bu_yil: int) -> list[dict]:
    """KAPANMIŞ ve GERÇEKLEŞME olarak yayımlanmış yıllarda ima ↔ gerçekleşen.

    Kapanmamış ya da tahmin/program olan sütun sınamaya GİRMEZ; girseydi
    ölçtüğümüz şey yöntem farkı değil tahmin hatası olurdu.
    """
    out: list[dict] = []
    for p in kayit["programlar"]:
        ima = ima_kur(p)
        for y in sorted(ima):
            if y >= bu_yil or veri.sutun_turu(p, y) != "gerceklesme":
                continue
            oz = yil_ozeti(kur, y)
            # Yılın TAMAMI elde değilse sınama kurulamaz: yarım yılın
            # ortalaması yıl ortalaması değildir.
            if oz is None or oz["n"] < 200:
                continue
            out.append({"program": p["kod"], "program_kisa": p["kisa"], "yil": y,
                        "ima": ima[y], "gerceklesen": oz["ortalama"],
                        "n": oz["n"],
                        "fark_yuzde": (ima[y] / oz["ortalama"] - 1) * 100})
    return out


def tatil_payi(kur: pd.Series, ay: int, gun: int, yil: int, geriye: int = 5) -> dict:
    """Yılın kalan penceresinde kaç hafta içi günün GÖZLEMSİZ kalacağı.

    Ölçüm, tahmin değil: aynı takvim penceresinde (ay/gün → 31 Aralık) geçmiş
    yıllarda hafta içi gün sayısı ile gerçekten gözlem düşen gün sayısının
    farkı alınır ve ORTANCASI yazılır. Gelecekteki tatilleri saymak bir
    varsayım olurdu; geçmişte kaç tane olduğunu saymak bir ölçümdür.
    """
    farklar: list[int] = []
    for y in range(yil - geriye, yil):
        try:
            bas = pd.Timestamp(year=y, month=ay, day=gun)
        except ValueError:
            continue
        son = pd.Timestamp(year=y + 1, month=1, day=1)
        hafta_ici = int(np.busday_count(bas.date(), son.date()))
        gozlem = int(((kur.index >= bas) & (kur.index < son)).sum())
        if hafta_ici > 0 and gozlem > 0:
            farklar.append(hafta_ici - gozlem)
    if not farklar:
        return {"ortanca": None, "n": 0, "yillar": []}
    return {"ortanca": int(np.median(farklar)), "n": len(farklar),
            "yillar": farklar}


def gozlem_gunu_ortancasi(kur: pd.Series, bu_yil: int, geriye: int = 5) -> int:
    """Bir yılda kaç gözlem düşüyor — GELECEK yılların gün sayısı için.

    Sabit 252 yazmak yerine ölçmenin sebebi: bu sayı hem takvimden hem resmî
    tatil sayısından geliyor ve ikisi de yıla göre değişiyor. Duyarlılığı
    küçük (yıl sonu seviyesi ±10 günde binde bir oynuyor) ama ölçmenin
    maliyeti sıfır.
    """
    say = [int((kur.index.year == y).sum()) for y in range(bu_yil - geriye, bu_yil)]
    say = [n for n in say if n > 200]
    return int(np.median(say)) if say else 250


def bu_yil_olc(p: dict, kur: pd.Series, bu_yil: int) -> dict | None:
    """İçinde bulunulan yıl: gerçekleşen, sapma, kalan, gereken, iki patika."""
    ima = ima_kur(p)
    if bu_yil not in ima:
        return None
    oz = yil_ozeti(kur, bu_yil)
    if oz is None:
        return None
    onceki = yil_ozeti(kur, bu_yil - 1)
    son_gun = pd.Timestamp(oz["son_gun"])
    kalan = int(np.busday_count((son_gun + pd.Timedelta(days=1)).date(),
                                dt.date(bu_yil + 1, 1, 1)))
    hedef = ima[bu_yil]
    d = {
        "yil": bu_yil,
        "ovp_ortalama": hedef,
        "gerceklesen_ortalama": oz["ortalama"],
        "n_gerceklesen": oz["n"],
        "son_kur": oz["son"],
        "son_gun": oz["son_gun"],
        "yil_basi": oz["ilk"],
        "yil_basi_gun": oz["ilk_gun"],
        "onceki_kapanis": None if onceki is None else onceki["son"],
        "onceki_kapanis_gun": None if onceki is None else onceki["son_gun"],
        "sapma_yuzde": (oz["ortalama"] / hedef - 1) * 100,
        "kalan_gun": kalan,
    }
    if onceki is not None and onceki["son"]:
        d["ytd_yuzde"] = (oz["son"] / onceki["son"] - 1) * 100
    d["yil_basindan_yuzde"] = (oz["son"] / oz["ilk"] - 1) * 100
    if kalan <= 0:
        # Yıl kapandı: kalan gün yoksa "gereken ortalama" diye bir soru yok.
        d["gereken_ortalama"] = None
        return d
    toplam = oz["n"] + kalan
    gereken = (hedef * toplam - oz["ortalama"] * oz["n"]) / kalan
    d["toplam_gun"] = toplam
    d["gereken_ortalama"] = gereken
    d["gereken_bugune_gore_yuzde"] = (gereken / oz["son"] - 1) * 100
    dogrusal = dogrusal_cikis(oz["son"], gereken, kalan)
    ustel = ustel_cikis(oz["son"], gereken, kalan)
    d["yil_sonu_dogrusal"] = dogrusal
    d["yil_sonu_ustel"] = ustel
    if dogrusal and ustel:
        d["patika_farki_yuzde"] = (ustel / dogrusal - 1) * 100
        d["yil_sonu_kalan_hareket_yuzde"] = (ustel / oz["son"] - 1) * 100
    # TATİL PAYI — kalan gün sayısının tek varsayımı; ölçülüp ayrıca yazılır.
    # Pencere, son gözlemin ERTESİ gününden yıl sonuna kadardır; ay/gün ikilisi
    # takvimden okunur, elle kaydırılmaz (31'inde bir gün eklemek 32 verirdi).
    ertesi = son_gun + pd.Timedelta(days=1)
    tp = tatil_payi(kur, int(ertesi.month), int(ertesi.day), bu_yil)
    d["kalan_tatil_payi"] = tp["ortanca"]
    d["kalan_tatil_ornek_yil"] = tp["n"]
    # SIFIR BİR ÖLÇÜM SONUCUDUR: geçmiş pencerelerde hiç tatil düşmediyse
    # ortanca 0'dır ve düzeltilmiş sayı ham sayıya EŞİTTİR. `if tp["ortanca"]`
    # yazmak o ölçümü ölçülmemiş sayar ve iki anahtar sessizce düşerdi.
    if tp["ortanca"] is not None and kalan - tp["ortanca"] > 0:
        kd = kalan - tp["ortanca"]
        d["kalan_gun_tatilsiz"] = kd
        d["gereken_ortalama_tatilsiz"] = (
            (hedef * (oz["n"] + kd) - oz["ortalama"] * oz["n"]) / kd)
    return d


def zincir_olc(p: dict, bu: dict, kur: pd.Series, bu_yil: int,
               yil_gun: int) -> list[dict]:
    """Zincirlenmiş patika: her yılın çıkışı sonrakinin girişi.

    İçinde bulunulan yılın çıkışı `bu_yil_olc`ün ÜSTEL çözümünden gelir;
    sonraki yıllarda giriş önceki çıkıştır ve çıkış aynı üstel çözümle
    bulunur. Program yılı ima edilen ortalama taşımıyorsa zincir orada BİTER
    — devam ettirmek, ölçülmemiş bir ortalamayı varsaymak olurdu.
    """
    ima = ima_kur(p)
    tufe = veri.satir_serisi(p, "tufe")
    out: list[dict] = []
    giris = bu.get("onceki_kapanis")
    cikis = bu.get("yil_sonu_ustel")
    for y in sorted(ima):
        if y < bu_yil:
            continue
        if y == bu_yil:
            g, c, n = giris, cikis, bu.get("kalan_gun")
        else:
            g = out[-1]["cikis"] if out else None
            c = ustel_cikis(g, ima[y], yil_gun) if g else None
            n = yil_gun
        if g is None or c is None:
            break
        deval = (c / g - 1) * 100
        satir = {"program": p["kod"], "yil": y, "giris": g, "ovp_ortalama": ima[y],
                 "cikis": c, "deval_yuzde": deval, "gun": n}
        if y in tufe:
            satir["tufe_yuzde"] = tufe[y]
            satir["reel_tl_yuzde"] = ((1 + tufe[y] / 100) / (1 + deval / 100) - 1) * 100
            satir["makas_puan"] = tufe[y] - deval
        out.append(satir)
    return out


def kumule_olc(zincir: list[dict]) -> dict:
    """Zincirin toplamı: kur, TÜFE ve reel TL — çarpımsal, yıl yıl birikerek."""
    if not zincir:
        return {}
    kf = zincir[-1]["cikis"] / zincir[0]["giris"]
    d = {"bas_yil": zincir[0]["yil"], "son_yil": zincir[-1]["yil"],
         "bas": zincir[0]["giris"], "son": zincir[-1]["cikis"],
         "kur_yuzde": (kf - 1) * 100}
    tf = 1.0
    tam = True
    for r in zincir:
        if "tufe_yuzde" not in r:
            tam = False
            break
        tf *= 1 + r["tufe_yuzde"] / 100
    if tam:
        d["tufe_yuzde"] = (tf - 1) * 100
        d["reel_tl_yuzde"] = (tf / kf - 1) * 100
    return d


# ===========================================================================
#  TAŞIMA
# ===========================================================================
def tl_getiri_faktoru(gecelik: pd.Series, endeks: pd.Series | None,
                      yil: int) -> tuple[float, str] | None:
    """Liranın bir yıl içinde biriktirdiği getiri faktörü ve HANGİ YOLDAN.

    GECELİK BİR FAİZ TAKVİM GÜNÜ TAŞIR, GÖZLEM GÜNÜ DEĞİL. Cuma kotasyonu
    pazartesiye kadar üç gün işler; kotasyonları teker teker 1/365 ile
    bileşiklemek hafta sonlarının ve tatillerin faizini tamamen düşürür.
    Ölçüldü (2026 yılı başı → 03.09.2026, 244 takvim günü / 167 gözlem):
    resmî endeks +%29,61, gözlem günüyle +%19,58 — 10,03 puan. Aradaki fark
    taşımanın kendisiyle aynı büyüklükte, yani konvansiyon bir ayrıntı değil
    ölçünün kendisi.

    İki yol var ve HANGİSİNİN kullanıldığı kayda geçer:
      · ENDEKS — BİST TLREF Endeksi. Bileşik getiriyi kaynağın kendisi
        hesaplamıştır; gün sayımı, tatil ve yuvarlama onun sözleşmesindedir.
        Elde varsa BU kullanılır.
      · KOTASYON — endeks yoksa gecelik faiz TAKVİM GÜNÜ üzerinden
        bileşiklenir: her kotasyon bir sonraki gözleme kadarki gün sayısını
        taşır. Endeksin ölçtüğü şeyin yaklaşığıdır, aynısı değildir.
    """
    if endeks is not None:
        e = endeks[endeks.index.year == yil].dropna()
        if len(e) >= 2:
            return float(e.iloc[-1] / e.iloc[0]), "endeks"
    r = gecelik[gecelik.index.year == yil].dropna()
    if len(r) < 2:
        return None
    # Her kotasyonun taşıdığı gün sayısı: bir SONRAKİ gözleme kadar. Son
    # kotasyon dönemi kapattığı için bir gün taşır.
    gun = np.diff(r.index.to_numpy()).astype("timedelta64[D]").astype(float)
    gun = np.append(gun, 1.0)
    return float(np.prod(1 + r.to_numpy() / 100 * gun / 365)), "kotasyon"


def carry_gerceklesen(kur: pd.Series, gecelik: pd.Series, yil: int,
                      endeks: pd.Series | None = None) -> dict | None:
    """Liranın biriktirdiği getiri eksi kurun hareketi — dolar bazında taşıma.

    Lira bacağı `tl_getiri_faktoru` ile ölçülür; gün sayımı konvansiyonunun
    neden ölçünün kendisi olduğu orada yazılı.
    """
    k = kur[kur.index.year == yil]
    r = gecelik[gecelik.index.year == yil].dropna()
    if len(k) < 2 or len(r) < 2:
        return None
    _tl = tl_getiri_faktoru(gecelik, endeks, yil)
    if _tl is None:
        return None
    tl_faktor, tl_yol = _tl
    kur_faktor = float(k.iloc[-1] / k.iloc[0])
    net = tl_faktor / kur_faktor - 1
    takvim = int((k.index[-1] - k.index[0]).days)
    d = {"yil": yil, "tl_yuzde": (tl_faktor - 1) * 100, "tl_yol": tl_yol,
         "ortalama_gecelik": float(r.mean()),
         "kur_yuzde": (kur_faktor - 1) * 100, "net_yuzde": net * 100,
         "gun": takvim, "n_faiz": int(len(r)),
         "bas_gun": k.index[0].strftime("%Y-%m-%d"),
         "son_gun": k.index[-1].strftime("%Y-%m-%d"),
         "faiz_son_gun": r.index[-1].strftime("%Y-%m-%d")}
    if takvim > 0:
        d["yillik_yuzde"] = ((1 + net) ** (365 / takvim) - 1) * 100
    return d


def carry_gunluk(kur: pd.Series, gecelik: pd.Series, yil: int,
                 endeks: pd.Series | None = None) -> pd.DataFrame:
    """Gerçekleşen taşımanın GÜNLÜK kümülatif izi — figürün çizdiği seri.

    Lira bacağı, ÖZETTEKİ sayıyla AYNI konvansiyondan gelir: figür ile sayfada
    yazan sayı ayrışırsa okur hangisinin doğru olduğunu bilemez.
    """
    k = kur[kur.index.year == yil]
    r = gecelik[gecelik.index.year == yil].dropna()
    if len(k) < 2 or len(r) < 2:
        return pd.DataFrame()
    ortak = k.index.intersection(r.index)
    if len(ortak) < 2:
        return pd.DataFrame()
    k, r = k.reindex(ortak), r.reindex(ortak)
    e = None
    if endeks is not None:
        e = endeks.reindex(ortak).ffill()
        if e.isna().any():
            e = None
    if e is not None:
        tl = (e / e.iloc[0]).to_numpy()
    else:
        gun = np.diff(ortak.to_numpy()).astype("timedelta64[D]").astype(float)
        gun = np.append(gun, 1.0)
        tl = np.cumprod(1 + r.to_numpy() / 100 * gun / 365)
    kf = (k / k.iloc[0]).to_numpy()
    return pd.DataFrame({"tl_yuzde": (tl - 1) * 100,
                         "kur_yuzde": (kf - 1) * 100,
                         "net_yuzde": (tl / kf - 1) * 100}, index=ortak)


def carry_ileri(zincir: list[dict], faiz: float, yil_gun: int) -> list[dict]:
    """İleriye dönük taşıma — TL FAİZİNİN SABİT KALMASI VARSAYIMIYLA.

    İki konvansiyon birden verilir; gerekçeleri modül başlığında. Ex-ante reel
    faiz de aynı basit konvansiyonla yazılır, yani sayfadaki iki sayı
    birbiriyle kıyaslanabilir.
    """
    if faiz is None:
        return []
    basit_f = 1 + faiz / 100
    bilesik_f = float(np.prod(np.full(yil_gun, 1 + faiz / 100 / 365)))
    out: list[dict] = []
    for r in zincir:
        d = {"yil": r["yil"], "faiz": faiz,
             "deval_yuzde": r["deval_yuzde"],
             "basit_yuzde": (basit_f / (1 + r["deval_yuzde"] / 100) - 1) * 100,
             "bilesik_yuzde": (bilesik_f / (1 + r["deval_yuzde"] / 100) - 1) * 100}
        if "tufe_yuzde" in r:
            d["reel_faiz_yuzde"] = (basit_f / (1 + r["tufe_yuzde"] / 100) - 1) * 100
        out.append(d)
    return out


# ===========================================================================
#  REVİZYON VE KAMU KESİMİ
# ===========================================================================
def revizyon_olc(kayit: dict, yeni_kod: str, eski_kod: str) -> list[dict]:
    """İki programın ORTAK yıllarında satır satır fark.

    Farkın birimi satırın birimine göre seçilir ve bu bir tercih değil
    zorunluluktur: %30,9 ile %28,5 arasındaki fark PUANDIR (2,4 puan), ama
    111.207 ile 89.406 arasındaki fark YÜZDEDİR. İkisini aynı ölçüyle yazmak
    ısı haritasında birini görünmez, ötekini devasa gösterirdi.
    """
    yeni, eski = veri.program(kayit, yeni_kod), veri.program(kayit, eski_kod)
    satir = kayit["satir"]
    ortak_yil = sorted({int(y) for y in yeni["sutun"]} & {int(y) for y in eski["sutun"]})
    out: list[dict] = []
    # İma edilen kur bir SATIR değil, tablodan türeyen bir ölçüdür; revizyon
    # haritasının başında durur çünkü hattın sorusu odur.
    kalemler = [("ima_kur", "İma edilen ortalama kur", "TL/dolar", 3)]
    kalemler += [(ad, satir[ad]["ad"], satir[ad]["birim"], satir[ad]["ondalik"])
                 for ad in yeni["deger"] if ad in eski["deger"]]
    iy, ie = ima_kur(yeni), ima_kur(eski)
    for ad, okur_ad, birim, ond in kalemler:
        sy = iy if ad == "ima_kur" else veri.satir_serisi(yeni, ad)
        se = ie if ad == "ima_kur" else veri.satir_serisi(eski, ad)
        for y in ortak_yil:
            if y not in sy or y not in se:
                continue
            puan_mi = birim in ("%", "puan")
            fark = (sy[y] - se[y]) if puan_mi else (
                (sy[y] / se[y] - 1) * 100 if se[y] else None)
            if fark is None:
                continue
            out.append({"kalem": ad, "ad": okur_ad, "birim": birim,
                        "ondalik": ond, "yil": y, "yeni": sy[y], "eski": se[y],
                        "fark": fark, "fark_birim": "puan" if puan_mi else "%"})
    return out


def faiz_gideri_olc(p: dict) -> list[dict]:
    """Faiz gideri artışı ile nominal GSYH artışının kıyası.

    Program sayısal bir faiz patikası yayımlamıyor. Ama bütçenin faiz gideri
    satırı bir izdir: faiz gideri nominal gelirden HIZLI artıyorsa, borcun
    ortalama maliyeti nominal büyümenin üstünde kalıyor demektir. Bu bir
    politika faizi tahmini DEĞİLDİR ve öyle sunulmaz; ölçülen şey iki
    yayımlanmış satırın büyüme farkıdır.
    """
    tl = veri.satir_serisi(p, "gsyh_tl")
    fz = veri.satir_serisi(p, "faiz_gideri")
    de = veri.satir_serisi(p, "deflator")
    tu = veri.satir_serisi(p, "tufe")
    out: list[dict] = []
    for y in sorted(tl):
        d = {"program": p["kod"], "yil": y}
        if y - 1 in tl:
            d["nominal_gsyh_yuzde"] = (tl[y] / tl[y - 1] - 1) * 100
        if y in fz and y - 1 in fz:
            d["faiz_gideri_yuzde"] = (fz[y] / fz[y - 1] - 1) * 100
        if "nominal_gsyh_yuzde" in d and "faiz_gideri_yuzde" in d:
            d["fark_puan"] = d["faiz_gideri_yuzde"] - d["nominal_gsyh_yuzde"]
        if y in de and y in tu:
            d["deflator_tufe_makasi_puan"] = de[y] - tu[y]
        out.append(d)
    return out


# ===========================================================================
#  BLOK SAATLERİ
# ===========================================================================
def blok_saatleri(K: pd.DataFrame, F: pd.DataFrame, T: pd.DataFrame,
                  kayit: dict) -> dict:
    """Her bacağın KENDİ saati. Hattın ana saati bunlardan türetilir (özet
    katmanında), çıpa değil — biri ilerlerken öteki donabilir."""
    o: dict = {}
    if "usdtry" in K.columns and not K["usdtry"].dropna().empty:
        o["kur_tarih"] = K["usdtry"].dropna().index[-1].strftime("%Y-%m-%d")
    if "tlref" in F.columns and not F["tlref"].dropna().empty:
        o["faiz_tarih"] = F["tlref"].dropna().index[-1].strftime("%Y-%m-%d")
    if "tufe_12a" in T.columns and not T["tufe_12a"].dropna().empty:
        o["tufe_tarih"] = T["tufe_12a"].dropna().index[-1].strftime("%Y-%m-%d")
    kodlar = veri.program_kodlari(kayit)
    if kodlar:
        g = veri.yayin_gunu(veri.program(kayit, kodlar[0]))
        if g:
            o["program_yeni_yayin"] = g.isoformat()
        g = veri.yayin_gunu(veri.program(kayit, kodlar[-1]))
        if g:
            o["program_eski_yayin"] = g.isoformat()
    # Taşıma figürünün BAĞLAYICI bacağı: iki canlı serinin en eskisi.
    # min() YAPISAL yazılır, bugünkü sıralamaya bakmaz.
    canli = [o[k] for k in ("kur_tarih", "faiz_tarih") if k in o]
    if len(canli) == 2:
        o["carry_tarih"] = min(canli)
    return o


# ===========================================================================
#  ANA AKIŞ
# ===========================================================================
def kos() -> int:
    b = _bicim()
    kayit = veri.programlar()
    K = _oku("kur.csv")
    F = _oku("faiz.csv")
    T = _oku("tufe.csv")
    if K.empty:
        raise SystemExit("DURDU — kur çerçevesi yok; önce veri.py koşmalı.")

    # ÇERÇEVEDEN TÜRETİLEBİLEN UYARI DEVRALINMAZ, YENİDEN ÖLÇÜLÜR.
    for u in veri.cerceve_uyarilari(K, F, T, kayit):
        uyar(u)
    # Devir yalnız çerçeveye bakarak bilinemeyen olaylar için (ağ düştü, seri
    # hiç gelmedi, önbellekten okundu) ve KÜNYE tutuyorsa.
    try:
        vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    except Exception as ex:                                        # noqa: BLE001
        uyar(f"ÖLÇÜM EKSİK: veri katmanının kaydı okunamadı ({type(ex).__name__}); "
             "o katmanın uyarıları bu koşuda devralınmadı.")
        vd = {}
    imza = veri.cerceve_imza(K)
    if vd and vd.get("cerceve_imza") != imza:
        uyar("ÖLÇÜM EKSİK: veri katmanının kaydı başka bir çerçeveyi anlatıyor; "
             "o katmanın uyarıları bu koşuda devralınmadı.")
    else:
        for u in (vd.get("uyarilar") or []):
            if u not in _UYARI:
                uyar(u)

    kur = K["usdtry"].dropna()
    gecelik = F["tlref"].dropna() if "tlref" in F.columns else pd.Series(dtype=float)
    # Endeks İSTEĞE BAĞLI: yoksa taşıma kotasyondan takvim günüyle kurulur ve
    # hangi yolun kullanıldığı özete yazılır. Hattın durması gerekmez —
    # kardeş bir hattın eksik sütunu bu hattın manşetini götürmemeli.
    endeks = (F["tlref_endeks"].dropna()
              if "tlref_endeks" in F.columns else None)
    bu_yil = int(pd.Timestamp(kur.index[-1]).year)
    kodlar = veri.program_kodlari(kayit)
    yeni = veri.program(kayit, kodlar[0])
    eski = veri.program(kayit, kodlar[-1])

    o: dict = {"bu_yil": bu_yil}
    o.update(blok_saatleri(K, F, T, kayit))
    o["program_yeni"] = {"kod": yeni["kod"], "kisa": yeni["kisa"], "ad": yeni["ad"],
                         "yayin_ay": yeni["yayin_ay"],
                         "yayin_yazi": veri.program_ay_yazi(yeni),
                         "kaynak": yeni["kaynak"]}
    o["program_eski"] = {"kod": eski["kod"], "kisa": eski["kisa"], "ad": eski["ad"],
                         "yayin_ay": eski["yayin_ay"],
                         "yayin_yazi": veri.program_ay_yazi(eski),
                         "kaynak": eski["kaynak"]}

    # ---------------------------------------------------------------- ima
    o["ima"] = {p["kod"]: {str(y): v for y, v in ima_kur(p).items()}
                for p in kayit["programlar"]}
    o["gerceklesen_yil"] = [d for d in
                            (yil_ozeti(kur, y) for y in sorted(set(kur.index.year)))
                            if d]

    # ------------------------------------------------------- yöntem sınaması
    ys = yontem_sinamasi(kayit, kur, bu_yil)
    o["yontem"] = ys
    o["yontem_esik_yuzde"] = YONTEM_ESIK_YUZDE
    if not ys:
        # SIFIR BİR ÖLÇÜM SONUCUDUR: sınanacak kapanmış gerçekleşme sütunu
        # yoksa "sapma yok" yazmak, koşmamış bir sınamanın sonucunu bildirmek
        # olurdu.
        uyar("Yöntem sınaması bu koşuda kurulamadı: kapanmış ve gerçekleşme "
             "olarak yayımlanmış bir yıl yok.")
    else:
        for r in ys:
            if abs(r["fark_yuzde"]) > YONTEM_ESIK_YUZDE:
                uyar(f"YÖNTEM: {r['program_kisa']} programının {r['yil']} yılında "
                     f"ima edilen ortalama kur ile gerçekleşen günlük ortalama "
                     f"{b.yuzde(r['fark_yuzde'], 2, isaret=True)} ayrışıyor "
                     f"(sınır %{b.sayi(YONTEM_ESIK_YUZDE, 1)}).")

    # ------------------------------------------------------- içinde bulunulan yıl
    yil_gun = gozlem_gunu_ortancasi(kur, bu_yil)
    o["yil_gun_ortancasi"] = yil_gun
    o["bu_yil_olcum"] = {}
    o["zincir"] = {}
    o["kumule"] = {}
    for p in (yeni, eski):
        bu = bu_yil_olc(p, kur, bu_yil)
        if bu is None:
            continue
        o["bu_yil_olcum"][p["kod"]] = bu
        z = zincir_olc(p, bu, kur, bu_yil, yil_gun)
        o["zincir"][p["kod"]] = z
        o["kumule"][p["kod"]] = kumule_olc(z)

    # ---------------------------------------------------------------- taşıma
    o["carry"] = {}
    if not gecelik.empty:
        cg = carry_gerceklesen(kur, gecelik, bu_yil, endeks)
        if cg:
            o["carry"]["gerceklesen"] = cg
        pol = F["politika"].dropna() if "politika" in F.columns else pd.Series(dtype=float)
        faiz = float(pol.iloc[-1]) if not pol.empty else None
        if faiz is not None:
            o["carry"]["faiz_varsayimi"] = faiz
            o["carry"]["faiz_varsayimi_gun"] = pol.index[-1].strftime("%Y-%m-%d")
            o["carry"]["ileri"] = carry_ileri(o["zincir"].get(yeni["kod"], []),
                                              faiz, yil_gun)
    else:
        o["carry"]["yok_sebep"] = ("TL gecelik faiz serisi bu koşuda elde yok; "
                                   "taşıma ölçülmedi.")

    # ------------------------------------------------------------- revizyon
    o["revizyon"] = revizyon_olc(kayit, yeni["kod"], eski["kod"])
    o["faiz_gideri"] = {p["kod"]: faiz_gideri_olc(p) for p in (yeni, eski)}
    o["tutarlilik"] = veri.program_tutarlilik(kayit)
    o["tutarlilik_esik_puan"] = TUTARLILIK_ESIK_PUAN

    # ------------------------------------------- gerçekleşen TÜFE karşılaştırması
    o["tufe_gerceklesen"] = {}
    if "tufe_12a" in T.columns:
        s = T["tufe_12a"].dropna()
        for y in sorted(set(s.index.year)):
            ara = s[(s.index.year == y) & (s.index.month == 12)]
            if len(ara):
                o["tufe_gerceklesen"][str(y)] = float(ara.iloc[-1])
        son = s.iloc[-1]
        o["tufe_son"] = float(son)
        o["tufe_son_ay"] = s.index[-1].strftime("%Y-%m-%d")

    o["uyarilar"] = list(_UYARI)
    o["cerceve_imza"] = imza

    # SIRA BAĞLAYICI: uyarilar.json HER HÂLDE ve ÖNCE yazılır (boş olsa bile).
    # Kopya sözleşmesinde düz yoldur; yoksa kopyalama tam orada kesilir ve
    # sözlükte ondan SONRA gelen hiçbir çıktı siteye gitmez.
    (PROJE / "uyarilar.json").write_text(
        json.dumps({"uyarilar": list(_UYARI)}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # ---------------------------------------------------------------- çerçeveler
    pd.DataFrame([{"program": kod, "yil": int(y), "ima": v}
                  for kod, d in o["ima"].items() for y, v in d.items()]
                 ).to_csv(VERI / "metrik_ima.csv", index=False)
    pd.DataFrame([r for z in o["zincir"].values() for r in z]
                 ).to_csv(VERI / "metrik_zincir.csv", index=False)
    pd.DataFrame(o["revizyon"]).to_csv(VERI / "metrik_revizyon.csv", index=False)
    cg = carry_gunluk(kur, gecelik, bu_yil, endeks) if not gecelik.empty else pd.DataFrame()
    if not cg.empty:
        cg.to_csv(VERI / "metrik_carry.csv")
    (VERI / "metrik_ozet.json").write_text(
        json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")

    # OPERATÖR DÖKÜMÜ — okura basılmaz; sabit genişlikli hizalama ve ISO tarih
    # taşır. Bu ayrım koda yazılıdır ki bir sonraki oturum kalıbı bir uyarı
    # şablonuna kopyalamasın.
    print(f"  bu yıl {bu_yil} · kur ucu {o.get('kur_tarih')} · "
          f"yıl gün ortancası {yil_gun}")
    for r in ys:
        print(f"  yontem {r['program']:<9} {r['yil']} ima={r['ima']:.4f} "
              f"ger={r['gerceklesen']:.4f} fark={r['fark_yuzde']:+.3f}%")
    for kod, bu in o["bu_yil_olcum"].items():
        print(f"  {kod:<9} ovp={bu['ovp_ortalama']:.4f} ger={bu['gerceklesen_ortalama']:.4f} "
              f"sapma={bu['sapma_yuzde']:+.2f}% kalan={bu['kalan_gun']} "
              f"gereken={bu.get('gereken_ortalama') or float('nan'):.4f} "
              f"ys_dogrusal={bu.get('yil_sonu_dogrusal') or float('nan'):.4f} "
              f"ys_ustel={bu.get('yil_sonu_ustel') or float('nan'):.4f}")
    for kod, z in o["zincir"].items():
        for r in z:
            print(f"  zincir {kod:<9} {r['yil']} {r['giris']:.2f} → {r['cikis']:.2f} "
                  f"deval={r['deval_yuzde']:+.2f}% "
                  f"reel={r.get('reel_tl_yuzde', float('nan')):+.2f}%")
    kotu = [r for r in o["tutarlilik"]
            if abs(r["sapma"]) > (TUTARLILIK_ESIK_PUAN if r["birim"] == "puan" else 0.06)]
    print(f"  tutarlilik {len(o['tutarlilik'])} kayit, {len(kotu)} sapma · "
          f"revizyon {len(o['revizyon'])} hucre")
    print(f"metrik_ozet.json yazıldı · {len(_UYARI)} uyarı")
    return 0


if __name__ == "__main__":
    raise SystemExit(kos())
