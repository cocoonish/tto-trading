#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörünün BACKTEST'i — gerçek barlar, dersin emir paketi, ablasyon.

NEDEN VAR. Sayfadaki emir mekaniğinin hiçbir sayısı ÖLÇÜLMEMİŞTİ: kaç işlem
üretir, kaçı kazanır, kenar var mı, hangi süzgeç ne katar. Rejim panosunun
beş bant işaretinin üçünün sabit olduğu ölçüldü ve kullanıcı aynı şeyi gözle
gördü; "daha fazla işlem üreten" bir indikatör istemeden önce mevcut kuralın
ne ürettiği sayıyla bilinmeli. Bu araç onu ölçer.

KURALLARIN KENDİSİ BURADA DEĞİL. Sinyal barı, kalite, always-in, yön
filtresi, rejim, barbwire ve dört emir paketi (`Kurulumlar`) brooks_referans'tan
içe aktarılır — Pine dosyalarının Python replikasyonu, kendi geleceğe-bakma
kapısıyla. Burada yalnız EMİR MEKANİĞİ ve ÖLÇÜM var.

EMİR MEKANİĞİ (dersin Bölüm 2.1 · 2.10 · 11.1 · 11.2 paketi; sayılar dersten):
  · Sinyal barı i KAPANMIŞ bardır. Emir bir bar ömürlüdür: i+1 barında
    dolmazsa iptal.
  · Giriş: sinyal ucunun BİR TİCK ötesine stop emri; i+1 barının ucu o
    seviyeye ulaşırsa dolar, dolum fiyatı emir fiyatı (kayma yok).
  · Koruyucu stop: karşı ucun bir tick ötesi. Risk = |giriş − stop| = 1R.
    Hedef = giriş + R·risk; R ∈ {1, 2} — "en az 1R, tercihen 2R".
  · ALTI TİCK KURALI (11.1): kâr-al limiti ancak fiyat hedefin BİR TİCK
    ötesine geçince dolmuş sayılır. Girişteki tick zaten emirde.
  · Dolum barından itibaren her bar (dolum barı dahil): stop görüldü → −1R;
    hedef+tick görüldü → +R; ikisi aynı barda → KAYIP (tutucu). 100 barda
    sonuç yoksa 100. barın kapanışından çıkılır (kesirli R); seri biterse son
    kapanıştan çıkılır ve ayrı sayılır.
  · YÖNETİM (11.2), açılıp kapanabilir: `sikilastir` — giriş barı işlem
    yönünde TREND BARIYSA (gövde ≥ menzilin yarısı, Bölüm 1 tanımı) stop
    giriş barının karşı ucunun bir tick ötesine ÇEKİLİR (yalnız daralır);
    doji/ters gövdeli giriş barında dokunulmaz. `basabas` — takip barı
    ölçütü: giriş barından sonraki İKİ barın hiçbiri giriş barının
    kapanışını işlem yönünde aşmadıysa stop giriş fiyatına çekilir
    (dersin "başabaş çıkış planı"; iki barlık pencere dersin '1–2 bar'
    cümlesinden).
  · KIRILIM MODU (2.5): iki taraflı stop; i+1'de hangi taraf tetiklenirse
    o pozisyon, öbür seviye koruyucu stop. İkisi aynı barda → emir sayılmaz
    (belirsiz, ayrıca sayılır).
  · BAŞARISIZ DÖNÜŞ (2.7): karşı dönüş barının ters tarafından giriş; i+1'de
    karşı uç da geçildiyse (ayı tarafı önce tetiklenmiş olabilir) sayılmaz.
    Karşı barın kalitesi K'yi geçmeli (Pine'da asgariKalite): süzgeçsiz hâli
    barların yarısında ateşler — ölçüldü, 5 dk'da 100 barda 53–57.
  · MALİYET: işlem başına gidiş-dönüş `maliyet` (fiyat birimi, seri başına);
    net R = R − maliyet/risk. Sıfır maliyet BRÜT'tür ve kenar iddiası
    taşımaz: 5 dk FX'te ölçüldü (15.09.2026), maliyetsiz +0,10…+0,16 R'nin
    tamamı medyanı 2,6 pip olan en küçük riskli işlemlerden geliyordu ve
    yarım pip maliyet on yapılandırmanın onunu da eksiye çeviriyordu.
  · Aynı seride aynı anda TEK pozisyon; pozisyondayken sinyal yok sayılır.
    Çıkış barı kapandıktan sonra o bar yeniden sinyal barı olabilir.
  · BANT KENARI (4.5/4.6/4.12): rejim BANT iken uç üçte birde dönüş barı,
    bant ≥ 3 × stop, 1R hedef bandın içinde, HO süzgeci; standart paket.
  · Aynı barda birden çok paket geçerliyse öncelik: kırılım modu (iki
    taraflı, yönsüz) > bant kenarı > ikinci giriş > başarısız dönüş > dönüş
    barı; aynı
    pakette iki yön birden geçerse kalitesi yüksek olan, eşitse bar atlanır
    ve sayılır (`belirsiz`).

ÖLÇÜLEN: yapılandırma başına N, kazanma oranı, ortalama R (brüt ve net),
bootstrap %95 güven aralığı (1.000 yeniden örnekleme), kâr faktörü, azami
geri çekilme (R), çift vuruş, seri dağılımı, zaman ayrımı (ilk/ikinci yarı),
risk büyüklüğü dilimleri ve RASTGELE TABAN: aynı emir sayısı, rastgele bar +
rastgele yön, AYNI paket ve AYNI yönetim, 300 tekrar → gerçek ortalamanın
yüzdeliği. Taban olmadan hiçbir isabet sayısı anlamlı değildir.

ÖLÇÜLMEYEN, adıyla:
  · Kayma yok; limit dolumu altı tick kuralıyla, stop dolumu tam fiyattan.
    Günlük barda gece boşluğu stop'un ötesine açılsa da −1R yazılır.
  · Seans saati, haber takvimi, pozisyon büyüklüğü, portföy etkisi yok.
  · Ortak başlangıç barı bütün yapılandırmalarda AYNI (göreli rejim
    tarihçesi + pencere + EMA); süzgeç kaldırılınca örneklem değişmesin.
  · Backtest örneklem İÇİDİR: ablasyon matrisinden "en iyi"yi seçip
    yayımlamak seçimi aynı veride yapmaktır; sıralama bir sonuçtur ve
    örneklem büyüyünce değişebilir.

    python3 site/tools/brooks_backtest.py            # ölçer, JSON yazar
    python3 site/tools/brooks_backtest.py --denetle  # yalnız mekanik sınamaları
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(SITE / "public" / "indikatorler"))
sys.path.insert(0, str(SITE.parent))

import brooks_ornek as O                                               # noqa: E402
import brooks_referans as R                                            # noqa: E402
from brooks_referans import FiyatPaneli, Kurulumlar, RejimPanosu, Seri  # noqa: E402
from ortak import bicim as B                                           # noqa: E402

KOK = SITE.parent
CIKTI = SITE / "src" / "data" / "brooks_backtest.json"

UFUK = 100
HEDEFLER = (1, 2)
BOOTSTRAP = 1000
RASTGELE_TEKRAR = 300
TOHUM = 20260915
YONETIM_SABIT = dict(sikilastir=False, basabas=False)
YONETIM_DERS = dict(sikilastir=True, basabas=True)

# Ortak başlangıç: rejim penceresinin dolduğu ilk bar (pencere + EMA). Her
# yapılandırma aynı bardan başlar — süzgeç kaldırıldığında örneklem değişmesin.
# GÖRELİ rejim ayrıca `tarihce` (280) bar ister; o dolana kadar göreli süzgeçli
# yapılandırmalar emir üretmez ve bu, seri başına `rejim_tanimsiz_bar` olarak
# YAZILIR. Başlangıcı 368'e çekmek yerel 420 barlık serileri 52 bara indirirdi;
# 5 dk'lık 16.000 barlık serilerde fark %2'nin altında.
BAS = int(R.SABIT_RP["pencere"]) + int(R.SABIT_RP["maUzunluk"]) - 2

# Ablasyon matrisi. `kurulum`: hangi paketler açık. `rejim`: "goreli" → göreli
# BANT'ta trend kurulumları kapalı, kırılım modu yalnız BANT'ta; "mutlak" →
# dersin Şekil 30 eşiği; None → süzgeç yok. Sıra sayfadaki tabloya gider.
YAPILANDIRMA: list[tuple[str, dict]] = [
    ("tam indikatör · göreli rejim",     dict(kurulum=("donus", "ikinci", "kirilim", "basarisiz", "bant"), rejim="goreli", ai=True, yon=True, bw=True, K=2)),
    ("tam indikatör · rejim yok",        dict(kurulum=("donus", "ikinci", "kirilim", "basarisiz", "bant"), rejim=None,     ai=True, yon=True, bw=True, K=2)),
    ("yalnız bant kenarı · BANT'ta",     dict(kurulum=("bant",),     rejim="goreli", ai=False, yon=True, bw=True, K=0)),
    ("yalnız dönüş barı · göreli rejim", dict(kurulum=("donus",),    rejim="goreli", ai=True, yon=True, bw=True, K=2)),
    ("yalnız dönüş barı · mutlak rejim", dict(kurulum=("donus",),    rejim="mutlak", ai=True, yon=True, bw=True, K=2)),
    ("yalnız dönüş barı · K≥3",          dict(kurulum=("donus",),    rejim="goreli", ai=True, yon=True, bw=True, K=3)),
    ("yalnız ikinci giriş (H2/L2)",      dict(kurulum=("ikinci",),   rejim="goreli", ai=True, yon=True, bw=True, K=0)),
    ("yalnız kırılım modu · BANT'ta",    dict(kurulum=("kirilim",),  rejim="goreli", ai=False, yon=False, bw=False, K=0)),
    ("yalnız kırılım modu · her yerde",  dict(kurulum=("kirilim",),  rejim=None,     ai=False, yon=False, bw=False, K=0)),
    ("yalnız başarısız dönüş · K≥2",     dict(kurulum=("basarisiz",), rejim="goreli", ai=True, yon=True, bw=True, K=2)),
    ("süzgeçsiz dönüş barı · K≥1",       dict(kurulum=("donus",),    rejim=None,     ai=False, yon=False, bw=False, K=1)),
]


# ── Seri başına ölçüm: referans bir kez çağrılır, süzgeçler sonra sorulur ──
class SeriOlcum:
    """Bir serinin bar bar emir girdileri. Kural katmanı burada ÇAĞRILIR,
    yeniden yazılmaz."""

    def __init__(self, ad: str, s: Seri, tick: float | None = None, maliyet: float = 0.0):
        self.ad, self.s = ad, s
        self.tick = float(tick) if tick else R.tick_tahmini(s)
        self.maliyet = float(maliyet)
        ku = Kurulumlar(s, self.tick)
        rp = RejimPanosu(s)
        fp = ku.fp
        n = len(s)
        self.ai = ku.ai
        self.trend_bari = [fp.govde_orani(i) >= fp.k["trendGovde"] for i in range(n)]
        self.yasak = {1: [False] * n, -1: [False] * n}
        self.rejim_goreli: list[str | None] = [None] * n
        self.rejim_mutlak: list[str | None] = [None] * n
        self.bw = [False] * n
        self.paket: dict[str, list] = {k: [None] * n for k in ("donus_boga", "donus_ayi", "ikinci", "kirilim", "basarisiz", "bant")}
        for i in range(1, n):
            f = fp.yon_filtresi(i)
            self.yasak[-1][i] = f == "yalnız AL"
            self.yasak[1][i] = f == "yalnız SAT"
            o = rp.olcu(i)
            self.rejim_mutlak[i] = o["rejim"] if o else None
            g = rp.olcu_goreli(i)
            self.rejim_goreli[i] = g["rejim"] if g else None
            self.bw[i] = rp.barbwire(i)["var"]
            self.paket["donus_boga"][i] = ku.donus(i, True)
            self.paket["donus_ayi"][i] = ku.donus(i, False)
            self.paket["ikinci"][i] = ku.ikinci_giris(i)
            self.paket["kirilim"][i] = ku.kirilim(i)
            self.paket["basarisiz"][i] = ku.basarisiz_donus(i)
            self.paket["bant"][i] = ku.bant_kenari(i)

    def _rejim(self, i: int, ayar: dict) -> str | None:
        if ayar["rejim"] == "goreli":
            return self.rejim_goreli[i]
        if ayar["rejim"] == "mutlak":
            return self.rejim_mutlak[i]
        return "serbest"

    def emir(self, i: int, ayar: dict) -> tuple[dict | None, bool]:
        """(emir, belirsiz). Emir None = bu barda emir yok."""
        rej = self._rejim(i, ayar)
        if rej is None:
            return None, False                       # pencere dolmadı
        bant = rej == "BANT"
        kur = ayar["kurulum"]
        if "kirilim" in kur and self.paket["kirilim"][i] and (ayar["rejim"] is None or bant):
            return self.paket["kirilim"][i], False
        if "bant" in kur and self.paket["bant"][i] and (ayar["rejim"] is None or bant):
            e = self.paket["bant"][i]
            if not (ayar["yon"] and self.yasak[e["yon"]][i]):
                return e, False
        if ayar["rejim"] is not None and bant:
            return None, False                       # bantta trend kurulumu yok
        if ayar["bw"] and self.bw[i]:
            return None, False

        def uygun(e: dict | None) -> bool:
            if e is None:
                return False
            if ayar["ai"] and self.ai[i] != e["yon"]:
                return False
            if ayar["yon"] and self.yasak[e["yon"]][i]:
                return False
            return True

        if "ikinci" in kur and uygun(self.paket["ikinci"][i]):
            return self.paket["ikinci"][i], False
        # Başarısız dönüş: karşı dönüş barının kalitesi K'yi geçmeli — Pine'da
        # aynı eşik `asgariKalite`. Süzgeçsiz hâli barların yarısında ateşler ve
        # dersin "her barın ötesine körü körüne stop" yasağına düşer.
        if "basarisiz" in kur and uygun(self.paket["basarisiz"][i]) and self.paket["basarisiz"][i]["kalite"] >= ayar["K"]:
            return self.paket["basarisiz"][i], False
        if "donus" in kur:
            aday = [e for e in (self.paket["donus_boga"][i], self.paket["donus_ayi"][i])
                    if uygun(e) and e["kalite"] >= ayar["K"]]
            if not aday:
                return None, False
            if len(aday) == 2 and aday[0]["kalite"] == aday[1]["kalite"]:
                return None, True
            return max(aday, key=lambda e: e["kalite"]), False
        return None, False


# ── Emir mekaniği ───────────────────────────────────────────────────────────
def islem_kos(s: Seri, emir, hedef_r: float, bas: int = 0, ufuk: int = UFUK,
              tick: float = 0.0, maliyet: float = 0.0, yonetim: dict | None = None,
              trend_bari: list[bool] | None = None) -> dict:
    """Bir seriyi baştan sona dolaşır; `emir(i)` → paket ya da None.

    Döner: {"islemler", "emir", "dolmayan", "sifir_menzil", "cift_belirsiz"}."""
    y = dict(YONETIM_SABIT, **(yonetim or {}))
    n = len(s)
    islemler: list[dict] = []
    emir_say = dolmayan = sifir = cift_belirsiz = 0
    i = max(bas, 1)
    while i <= n - 2:
        e = emir(i)
        if not e:
            i += 1
            continue
        emir_say += 1
        j = i + 1
        if e.get("cift"):
            alis_dolu, satis_dolu = s.h[j] >= e["alis"], s.l[j] <= e["satis"]
            if alis_dolu and satis_dolu:
                cift_belirsiz += 1
                i = j
                continue
            if not (alis_dolu or satis_dolu):
                dolmayan += 1
                i = j
                continue
            yon = 1 if alis_dolu else -1
            giris, stop = (e["alis"], e["satis"]) if alis_dolu else (e["satis"], e["alis"])
        else:
            yon, giris, stop = e["yon"], e["giris"], e["stop"]
            dolu = s.h[j] >= giris if yon == 1 else s.l[j] <= giris
            if dolu and e.get("sart_ters_uc"):
                # 2.7: karşı uç aynı barda geçildiyse önce hangisinin tetiklendiği bilinmez
                ters = s.l[j] <= stop if yon == 1 else s.h[j] >= stop
                if ters:
                    cift_belirsiz += 1
                    i = j
                    continue
            if not dolu:
                dolmayan += 1
                i = j
                continue
        risk = abs(giris - stop)
        if risk <= 0:
            sifir += 1
            i = j
            continue
        hedef = giris + yon * hedef_r * risk
        son = min(n, j + ufuk) - 1
        sonuc: tuple[float, str, int] | None = None
        cift = False
        stop_cari = stop
        for k in range(j, son + 1):
            # Yönetim: k barına GİRMEDEN önce, kapanmış barlardan karar.
            if k == j + 1 and y["sikilastir"] and trend_bari is not None and trend_bari[j] \
                    and ((yon == 1 and s.c[j] > s.o[j]) or (yon == -1 and s.c[j] < s.o[j])):
                yeni = s.l[j] - tick if yon == 1 else s.h[j] + tick
                stop_cari = max(stop_cari, yeni) if yon == 1 else min(stop_cari, yeni)
            if k == j + 3 and y["basabas"]:
                takip = (s.c[j + 1] > s.c[j] or s.c[j + 2] > s.c[j]) if yon == 1 \
                    else (s.c[j + 1] < s.c[j] or s.c[j + 2] < s.c[j])
                if not takip:
                    stop_cari = max(stop_cari, giris) if yon == 1 else min(stop_cari, giris)
            if yon == 1:
                stop_vurdu, hedef_vurdu = s.l[k] <= stop_cari, s.h[k] >= hedef + tick
            else:
                stop_vurdu, hedef_vurdu = s.h[k] >= stop_cari, s.l[k] <= hedef - tick
            if stop_vurdu:
                r = yon * (stop_cari - giris) / risk
                sonuc = (r, "stop" if abs(r + 1) < 1e-9 else "stop_cekilmis", k)
                cift = hedef_vurdu
                break
            if hedef_vurdu:
                sonuc = (float(hedef_r), "hedef", k)
                break
        if sonuc is None:
            r = yon * (s.c[son] - giris) / risk
            sonuc = (r, "zaman_asimi" if son == j + ufuk - 1 else "seri_sonu", son)
        islemler.append({
            "sinyal": i, "dolum": j, "cikis": sonuc[2], "yon": yon,
            "giris": giris, "stop": stop, "risk": risk, "tur": sonuc[1],
            "R": sonuc[0], "R_net": sonuc[0] - maliyet / risk, "cift": cift,
            "kurulum": e.get("kurulum", "?"), "kalite": e.get("kalite"),
        })
        i = sonuc[2]
    return {"islemler": islemler, "emir": emir_say, "dolmayan": dolmayan,
            "sifir_menzil": sifir, "cift_belirsiz": cift_belirsiz}


# ── Ölçüler ─────────────────────────────────────────────────────────────────
def _ort(x: list[float]) -> float | None:
    return sum(x) / len(x) if x else None


def bootstrap_ca(rs: list[float], rng: random.Random, tekrar: int = BOOTSTRAP) -> tuple[float, float] | None:
    if len(rs) < 2:
        return None
    n = len(rs)
    ortalar = sorted(sum(rng.choice(rs) for _ in range(n)) / n for _ in range(tekrar))
    return ortalar[int(0.025 * tekrar)], ortalar[min(tekrar - 1, int(0.975 * tekrar))]


def kar_faktoru(rs: list[float]) -> float | None:
    kazanc = sum(r for r in rs if r > 0)
    kayip = -sum(r for r in rs if r < 0)
    if kayip == 0:
        return None
    return kazanc / kayip


def azami_geri_cekilme(rs: list[float]) -> float:
    tepe = birikim = gc = 0.0
    for r in rs:
        birikim += r
        tepe = max(tepe, birikim)
        gc = max(gc, tepe - birikim)
    return gc


def ozet(rs: list[float], rng: random.Random | None = None) -> dict:
    n = len(rs)
    ca = bootstrap_ca(rs, rng) if rng is not None else None
    kf = kar_faktoru(rs) if n else None
    return {
        "n": n,
        "kazanma": round(sum(1 for r in rs if r > 0) / n, 4) if n else None,
        "ort_R": round(_ort(rs), 4) if n else None,
        "ca_alt": round(ca[0], 4) if ca else None,
        "ca_ust": round(ca[1], 4) if ca else None,
        "toplam_R": round(sum(rs), 3),
        "kar_faktoru": round(kf, 3) if kf is not None else None,
        "azami_geri_cekilme_R": round(azami_geri_cekilme(rs), 3) if n else None,
    }


# ── Rastgele taban ──────────────────────────────────────────────────────────
def rastgele_kos(so: SeriOlcum, m: int, hedef_r: float, rng: random.Random,
                 yonetim: dict | None = None, bas: int = BAS) -> dict:
    """Gerçek koşunun EMİR sayısı (m) kadar rastgele bar + rastgele yön,
    STANDART paket (uç ± tick), aynı mekanik ve yönetim."""
    s = so.s
    uygun = list(range(max(bas, 1), len(s) - 1))
    if m == 0 or not uygun:
        return {"islemler": [], "emir": 0, "dolmayan": 0, "sifir_menzil": 0, "cift_belirsiz": 0}
    rng.shuffle(uygun)
    secili: dict[int, int] = {}
    hedef, ptr, son = min(m, len(uygun)), 0, None

    def emir(i):
        yon = secili.get(i, 0)
        if not yon:
            return None
        return ({"yon": 1, "giris": s.h[i] + so.tick, "stop": s.l[i] - so.tick} if yon == 1
                else {"yon": -1, "giris": s.l[i] - so.tick, "stop": s.h[i] + so.tick})

    for _ in range(20):
        while len(secili) < hedef and ptr < len(uygun):
            secili[uygun[ptr]] = rng.choice((1, -1))
            ptr += 1
        son = islem_kos(s, emir, hedef_r, bas=bas, tick=so.tick, maliyet=so.maliyet,
                        yonetim=yonetim, trend_bari=so.trend_bari)
        if son["emir"] >= m or ptr >= len(uygun):
            break
        hedef += m - son["emir"]
    return son


# ── Bir yapılandırmanın tam ölçümü ──────────────────────────────────────────
def yapilandirma_olc(ad: str, ayar: dict, hedef_r: float, seriler: list[SeriOlcum],
                     rng: random.Random, tekrar: int = RASTGELE_TEKRAR,
                     yonetim: dict | None = None) -> dict:
    y = dict(YONETIM_SABIT, **(yonetim or {}))
    islemler: list[dict] = []
    seri_ozet: dict[str, dict] = {}
    emir_seri: dict[str, int] = {}
    belirsiz = dolmayan = sifir = cift_bel = 0
    ilk: list[float] = []
    ikinci: list[float] = []
    for so in seriler:
        s = so.s
        sayac = {"belirsiz": 0}

        def emir(i, so=so, sayac=sayac):
            e, b = so.emir(i, ayar)
            sayac["belirsiz"] += b
            return e

        son = islem_kos(s, emir, hedef_r, bas=BAS, tick=so.tick, maliyet=so.maliyet,
                        yonetim=y, trend_bari=so.trend_bari)
        belirsiz += sayac["belirsiz"]
        dolmayan += son["dolmayan"]
        sifir += son["sifir_menzil"]
        cift_bel += son["cift_belirsiz"]
        emir_seri[so.ad] = son["emir"]
        rs = [t["R"] for t in son["islemler"]]
        orta = (BAS + len(s)) // 2
        for t in son["islemler"]:
            (ilk if t["sinyal"] < orta else ikinci).append(t["R"])
            islemler.append(dict(t, seri=so.ad, zaman=s.zaman[t["sinyal"]] if s.zaman else None,
                                 cikis_zaman=s.zaman[t["cikis"]] if s.zaman else None,
                                 risk_tick=round(t["risk"] / so.tick, 1)))
        tanimsiz = (sum(1 for i in range(BAS, len(s)) if so.rejim_goreli[i] is None) if ayar["rejim"] == "goreli"
                    else sum(1 for i in range(BAS, len(s)) if so.rejim_mutlak[i] is None) if ayar["rejim"] == "mutlak" else 0)
        seri_ozet[so.ad] = dict(ozet(rs), emir=son["emir"], bar=len(s) - BAS - 1, rejim_tanimsiz_bar=tanimsiz,
                                ort_R_net=round(_ort([t["R_net"] for t in son["islemler"]]), 4) if rs else None,
                                tur={k: sum(1 for t in son["islemler"] if t["tur"] == k)
                                     for k in ("hedef", "stop", "stop_cekilmis", "zaman_asimi", "seri_sonu")})

    islemler.sort(key=lambda t: (t["zaman"] or "", t["seri"]))
    rs = [t["R"] for t in islemler]
    rs_net = [t["R_net"] for t in islemler]
    toplam_emir = sum(emir_seri.values())

    r_ort: list[float] = []
    r_n: list[int] = []
    r_emir: list[int] = []
    for _ in range(tekrar):
        hepsi: list[float] = []
        e = 0
        for so in seriler:
            son = rastgele_kos(so, emir_seri[so.ad], hedef_r, rng, yonetim=y)
            hepsi += [t["R"] for t in son["islemler"]]
            e += son["emir"]
        r_ort.append(_ort(hepsi) if hepsi else 0.0)
        r_n.append(len(hepsi))
        r_emir.append(e)
    gercek = _ort(rs)
    if gercek is None or not r_ort:
        yuzdelik = None
    else:
        alt = sum(1 for v in r_ort if v < gercek)
        esit = sum(1 for v in r_ort if v == gercek)
        yuzdelik = round(100.0 * (alt + 0.5 * esit) / len(r_ort), 1)
    sirali = sorted(r_ort)
    rastgele = {
        "tekrar": tekrar,
        "emir_ort": round(_ort(r_emir), 1) if r_emir else None,
        "n_ort": round(_ort(r_n), 1) if r_n else None,
        "ort_R_ort": round(_ort(r_ort), 4) if r_ort else None,
        "ort_R_yuzde2_5": round(sirali[int(0.025 * len(sirali))], 4) if sirali else None,
        "ort_R_yuzde97_5": round(sirali[min(len(sirali) - 1, int(0.975 * len(sirali)))], 4) if sirali else None,
        "yuzdelik": yuzdelik,
    }

    # Risk büyüklüğü dilimleri (tick cinsinden, seriler arası karışık — yalnız
    # "kenar küçük riskte mi toplanıyor" sorusu için).
    dilim: dict[str, dict] = {}
    if len(islemler) >= 8:
        sirali_risk = sorted(t["risk_tick"] for t in islemler)
        q1, q3 = sirali_risk[len(sirali_risk) // 4], sirali_risk[3 * len(sirali_risk) // 4]
        for adx, alt_s, ust_s in (("kucuk", 0, q1), ("orta", q1, q3), ("buyuk", q3, float("inf"))):
            sec = [t for t in islemler if alt_s <= t["risk_tick"] < ust_s]
            if sec:
                dilim[adx] = {"n": len(sec), "risk_tick_alt": alt_s, "risk_tick_ust": ust_s if ust_s != float("inf") else None,
                              "ort_R": round(_ort([t["R"] for t in sec]), 4),
                              "ort_R_net": round(_ort([t["R_net"] for t in sec]), 4)}

    return {
        "ad": ad, "ayar": {k: (list(v) if isinstance(v, tuple) else v) for k, v in ayar.items()},
        "hedef_R": hedef_r, "yonetim": y,
        **ozet(rs, rng),
        "ort_R_net": round(_ort(rs_net), 4) if rs_net else None,
        "ca_net": [round(x, 4) for x in bootstrap_ca(rs_net, rng)] if len(rs_net) >= 2 else None,
        "emir": toplam_emir, "dolmayan": dolmayan, "belirsiz": belirsiz, "cift_belirsiz": cift_bel,
        "sifir_menzil": sifir,
        "dolum_orani": round(len(rs) / toplam_emir, 3) if toplam_emir else None,
        "tur": {k: sum(1 for t in islemler if t["tur"] == k)
                for k in ("hedef", "stop", "stop_cekilmis", "zaman_asimi", "seri_sonu")},
        "kurulum_dagilimi": {k: sum(1 for t in islemler if t["kurulum"] == k)
                             for k in ("donus", "ikinci", "kirilim", "basarisiz", "bant")},
        "cift_vurus": sum(1 for t in islemler if t.get("cift")),
        "ilk_yari": ozet(ilk, rng),
        "ikinci_yari": ozet(ikinci, rng),
        "risk_dilimi": dilim,
        "seri": seri_ozet,
        "rastgele": rastgele,
        # İşlem listesi KISA tutulur (44 yapılandırma × yüzlerce işlem): seri,
        # sinyal zamanı, paket, risk (tick) ve R. Giriş/stop seviyeleri
        # yeniden üretilebilir; dosya sayfaya derleme zamanında giriyor.
        "islemler": [{"seri": t["seri"], "zaman": t["zaman"], "yon": t["yon"], "kurulum": t["kurulum"],
                      "risk_tick": t["risk_tick"], "tur": t["tur"], "R": round(t["R"], 3)} for t in islemler],
    }


# ── Kapılar: mekanik sentetik barlarla ──────────────────────────────────────
def _seri(b: list[tuple]) -> Seri:
    return Seri([x[0] for x in b], [x[1] for x in b], [x[2] for x in b], [x[3] for x in b])


def kendini_sina() -> list[str]:
    """Kuralın İLAN ETTİĞİ hâllere koşulur. Her madde tek bir mekanik cümle.
    tick = 0,01; sinyal barı H 10,50 · L 10,00 → giriş 10,51 · stop 9,99 ·
    risk 0,52 · 1R hedef 11,03 (dolum için 11,04 görülmeli)."""
    hata: list[str] = []
    T = 0.01
    duz = (10.0, 10.2, 9.8, 10.0)
    sinyal = (10.0, 10.5, 10.0, 10.4)
    paket = {"yon": 1, "giris": 10.51, "stop": 9.99}
    tek = lambda i, p=paket: (lambda j: p if j == i else None)   # noqa: E731

    # ① Bilinen kazanç: dolum 10,6 (≥ 10,51); hedef 11,03, bar 11,05'e çıkar (≥ 11,04) → +1R.
    b = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 11.05, 10.4, 11.0), duz]
    t = islem_kos(_seri(b), tek(2), 1.0, tick=T)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "hedef" or t[0]["R"] != 1.0 or abs(t[0]["giris"] - 10.51) > 1e-9 or t[0]["cikis"] != 4:
        hata.append(f"① bilinen kazanç +1R, giriş 10,51, çıkış 4. barda beklenirdi; {t}")

    # ② ALTI TİCK KURALI: bar tam hedefe (11,03) ulaşır ama bir tick ötesine geçmez → dolmaz.
    b2 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 11.03, 10.4, 11.0), duz]
    t = islem_kos(_seri(b2), tek(2), 1.0, tick=T)["islemler"]
    if len(t) != 1 or t[0]["tur"] == "hedef":
        hata.append(f"② hedefe tam dokunan bar limiti DOLDURMAMALI (altı tick kuralı); {t}")

    # ③ Bilinen kayıp: dolumdan sonra düşük 9,99'a değer → −1R.
    b3 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 10.7, 9.9, 10.0), duz]
    t = islem_kos(_seri(b3), tek(2), 1.0, tick=T)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "stop" or t[0]["R"] != -1.0:
        hata.append(f"③ bilinen kayıp −1R beklenirdi; {t}")

    # ④ Aynı barda ikisi → KAYIP (tutucu), çift işaretli.
    b4 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 11.2, 9.9, 10.8), duz]
    t = islem_kos(_seri(b4), tek(2), 1.0, tick=T)["islemler"]
    if len(t) != 1 or t[0]["R"] != -1.0 or not t[0]["cift"]:
        hata.append(f"④ aynı barda hedef+stop → kayıp ve çift beklenirdi; {t}")

    # ⑤ Dolmayan emir: sonraki bar 10,51'e ulaşmaz → işlem yok, emir 1, dolmayan 1.
    b5 = [duz, duz, sinyal, (10.4, 10.5, 10.3, 10.45), duz, duz]
    son = islem_kos(_seri(b5), tek(2), 1.0, tick=T)
    if son["islemler"] or son["emir"] != 1 or son["dolmayan"] != 1:
        hata.append(f"⑤ dolmayan emir sayılmalı, işlem üretmemeli; {son}")

    # ⑥ Ayı aynası: satış paketi (giriş 9,99 · stop 10,51 · hedef 9,47, dolum için 9,46).
    ayi = {"yon": -1, "giris": 9.99, "stop": 10.51}
    b6 = [duz, duz, sinyal, (10.4, 10.45, 9.95, 10.0), (10.0, 10.1, 9.45, 9.5), duz]
    t = islem_kos(_seri(b6), tek(2, ayi), 1.0, tick=T)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "hedef" or t[0]["R"] != 1.0 or t[0]["yon"] != -1:
        hata.append(f"⑥ ayı aynası +1R beklenirdi; {t}")

    # ⑦ Sıkılaştırma: giriş barı güçlü boğa trend barı (10,45 → 10,95, menzil 10,4–11,0) → stop 10,39;
    #    sonraki bar 10,35'e düşer → stop_cekilmis, R = (10,39 − 10,51)/0,52 ≈ −0,23.
    b7 = [duz, duz, sinyal, (10.45, 11.0, 10.4, 10.95), (10.95, 11.0, 10.35, 10.5), duz]
    tb = [False, False, False, True, False, False]
    t = islem_kos(_seri(b7), tek(2), 2.0, tick=T, yonetim=YONETIM_DERS, trend_bari=tb)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "stop_cekilmis" or abs(t[0]["R"] - (10.39 - 10.51) / 0.52) > 1e-6:
        hata.append(f"⑦ sıkılaştırılmış stop 10,39 ve kesirli kayıp beklenirdi; {t}")
    #    Aynı bar doji ise dokunulmaz: −1R.
    #    Aynı bar doji ise dokunulmaz: 4. bar 10,35'e iner ama 9,99'a değmez, 5. bar (düz, düşük 9,8) stop → −1R.
    t2 = islem_kos(_seri(b7), tek(2), 2.0, tick=T, yonetim=YONETIM_DERS, trend_bari=[False] * 6)["islemler"]
    if len(t2) != 1 or t2[0]["tur"] != "stop" or t2[0]["R"] != -1.0 or t2[0]["cikis"] != 5:
        hata.append(f"⑦b doji giriş barında stop sıkılaştırılmamalı (−1R, 5. bar); {t2}")

    # ⑧ Başabaş: giriş barından sonraki iki bar kapanışı aşamaz → stop girişe; 3. bar girişe değer → R=0.
    b8 = [duz, duz, sinyal, (10.45, 10.6, 10.4, 10.55), (10.55, 10.6, 10.52, 10.53), (10.53, 10.6, 10.52, 10.54),
          (10.54, 10.6, 10.5, 10.58), duz]
    t = islem_kos(_seri(b8), tek(2), 2.0, tick=T, yonetim=dict(basabas=True), trend_bari=[False] * 8)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "stop_cekilmis" or abs(t[0]["R"]) > 1e-9 or t[0]["cikis"] != 6:
        hata.append(f"⑧ başabaş stopu 6. barda 0R ile çıkmalıydı; {t}")

    # ⑨ Kırılım modu: iki taraflı; alış tarafı dolarsa stop = satış seviyesi; ikisi aynı barda → belirsiz.
    cift = {"cift": True, "alis": 10.51, "satis": 9.99}
    b9 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 11.05, 10.4, 11.0), duz]
    t = islem_kos(_seri(b9), tek(2, cift), 1.0, tick=T)["islemler"]
    if len(t) != 1 or t[0]["yon"] != 1 or abs(t[0]["stop"] - 9.99) > 1e-9 or t[0]["tur"] != "hedef":
        hata.append(f"⑨ kırılım modu alış tarafı dolmalı, stop 9,99; {t}")
    b9b = [duz, duz, sinyal, (10.4, 10.6, 9.9, 10.5), duz, duz]
    son = islem_kos(_seri(b9b), tek(2, cift), 1.0, tick=T)
    if son["islemler"] or son["cift_belirsiz"] != 1:
        hata.append(f"⑨b iki taraf aynı barda → belirsiz, işlem yok; {son}")

    # ⑩ Maliyet: 0,052 maliyet risk 0,52 → net R = R − 0,1.
    t = islem_kos(_seri(b), tek(2), 1.0, tick=T, maliyet=0.052)["islemler"]
    if len(t) != 1 or abs(t[0]["R_net"] - 0.9) > 1e-9:
        hata.append(f"⑩ net R 0,9 beklenirdi; {t}")

    # ⑪ Tek pozisyon: 3. bardaki sinyal pozisyon içinde yok sayılır; çıkış barı (4) yeniden
    #    sinyal barı olabilir (emir 4'te, 5. bar 10,51'e ulaşmaz → dolmayan); 5'teki sinyal 6'da dolar.
    b11 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 11.05, 10.4, 11.0), sinyal, (10.4, 10.6, 10.3, 10.5), duz]
    hep = lambda j: paket if j in (2, 3, 4, 5) else None   # noqa: E731
    son = islem_kos(_seri(b11), hep, 1.0, tick=T)
    if son["emir"] != 3 or son["dolmayan"] != 1 or len(son["islemler"]) != 2 or son["islemler"][1]["sinyal"] != 5:
        hata.append(f"⑪ pozisyondayken sinyal yok sayılmalı, çıkış barından sonra yeni emir; {son}")

    # ⑫ Tekrarlanabilirlik: aynı tohum aynı sayı (rastgele taban).
    sent = R._sentetik(300, tohum=3)
    so = SeriOlcum("sent", sent, tick=0.0001)
    a = rastgele_kos(so, 10, 1.0, random.Random(1), bas=1)
    b_ = rastgele_kos(so, 10, 1.0, random.Random(1), bas=1)
    if not a["islemler"] or [x["R"] for x in a["islemler"]] != [x["R"] for x in b_["islemler"]]:
        hata.append("⑫ rastgele taban aynı tohumla aynı (ve boş olmayan) sonucu vermeli")

    # ⑬ Rastgele taban kendi içinde: sentetik sürüklenmesiz seride ortalama R'nin %95 bandı sıfırı kapsamalı.
    rng = random.Random(TOHUM)
    ortalar = []
    for _ in range(60):
        son = rastgele_kos(so, 25, 1.0, rng, bas=1)
        rs = [x["R"] for x in son["islemler"]]
        if rs:
            ortalar.append(sum(rs) / len(rs))
    ortalar.sort()
    if not ortalar or not (ortalar[1] <= 0.0 <= ortalar[-2]):
        hata.append(f"⑬ sürüklenmesiz seride rastgele tabanın bandı sıfırı kapsamalı; {ortalar[:3]}…{ortalar[-3:]}")

    # ⑭ Ayna simetrisi: seri fiyatı yansıtılınca (p → 20 − p) uzun/kısa sonuçlar aynı.
    sent2 = R._sentetik(200, tohum=5)
    ayna = Seri([20 - x for x in sent2.o], [20 - x for x in sent2.l], [20 - x for x in sent2.h], [20 - x for x in sent2.c])
    duzs = islem_kos(sent2, lambda j: {"yon": 1, "giris": sent2.h[j] + T, "stop": sent2.l[j] - T} if j % 7 == 0 else None, 2.0, tick=T)
    ters = islem_kos(ayna, lambda j: {"yon": -1, "giris": ayna.l[j] - T, "stop": ayna.h[j] + T} if j % 7 == 0 else None, 2.0, tick=T)
    if [round(x["R"], 6) for x in duzs["islemler"]] != [round(x["R"], 6) for x in ters["islemler"]]:
        hata.append("⑭ ayna simetrisi bozuk: yansıtılmış seride kısa işlemler uzunları vermeli")
    return hata


# ── Çalıştırma ──────────────────────────────────────────────────────────────
def _tablo(satirlar: list[dict]) -> str:
    bas = f"{'yapılandırma':38s} {'R':>2s} {'yön.':5s} {'N':>5s} {'kaz.':>6s} {'ort R':>7s} {'CA95':>16s} {'KF':>5s} {'rast.%':>6s}"
    out = [bas, "─" * len(bas)]
    for y in satirlar:
        ca = f"[{B.sayi(y['ca_alt'], 2)}, {B.sayi(y['ca_ust'], 2)}]" if y["ca_alt"] is not None else "—"
        out.append(f"{y['ad']:38s} {int(y['hedef_R']):>2d} {'ders' if y['yonetim']['basabas'] else 'sabit':5s} {y['n']:>5d} "
                   f"{B.sayi(100 * (y['kazanma'] or 0), 1):>6s} {B.sayi(y['ort_R'] or 0, 3):>7s} {ca:>16s} "
                   f"{(B.sayi(y['kar_faktoru'], 2) if y['kar_faktoru'] is not None else '—'):>5s} "
                   f"{(B.sayi(y['rastgele']['yuzdelik'], 0) if y['rastgele']['yuzdelik'] is not None else '—'):>6s}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--denetle", action="store_true", help="yalnız mekanik sınamaları koştur")
    ap.add_argument("--tekrar", type=int, default=RASTGELE_TEKRAR)
    args = ap.parse_args()

    hata = kendini_sina()
    if hata:
        print("DENETİM DÜŞTÜ:")
        for h in hata:
            print("  ✗", h)
        return 1
    print("denetim · 14 madde GEÇTİ (kazanç · altı tick · kayıp · aynı bar · dolmayan · ayı aynası · "
          "sıkılaştırma · başabaş · kırılım modu · maliyet · tek pozisyon · tekrarlanabilirlik · "
          "rastgele taban · ayna simetrisi)")
    if args.denetle:
        return 0

    kaynaklar = [O.bar_oku(p) for p in sorted((SITE / "public" / "teknik").glob("*.html"))]
    seriler: list[SeriOlcum] = []
    dislanan: dict[str, dict] = {}
    for k in kaynaklar:
        g = O.govde_kunyesi(k.seri)
        if not g["gecti"]:
            dislanan[k.anahtar] = g
            continue
        seriler.append(SeriOlcum(k.anahtar, k.seri))
    rng = random.Random(TOHUM)
    sonuclar: list[dict] = []
    for ad, ayar in YAPILANDIRMA:
        for hr in HEDEFLER:
            for yon in (YONETIM_SABIT, YONETIM_DERS):
                y = yapilandirma_olc(ad, ayar, hr, seriler, rng, tekrar=args.tekrar, yonetim=yon)
                sonuclar.append(y)
                print(f"  {ad} · R={hr} · {'ders' if yon['basabas'] else 'sabit'} · N={y['n']} · ort {y['ort_R']}")
    print("\n" + _tablo(sonuclar))
    kunye = {
        "olcum_tarihi": date.today().isoformat(),
        "kaynak": "site/public/teknik/*.html (teknik/olc.py'nin kapanmış-bar disiplininden geçmiş OHLC)",
        "kural_kaynagi": "site/public/indikatorler/brooks_referans.py (Pine replikasyonu)",
        "seri": len(seriler), "bar": sum(len(s.s) for s in seriler),
        "seri_listesi": {s.ad: {"bar": len(s.s), "tick": s.tick, "bas": s.s.zaman[0] if s.s.zaman else None,
                                "son": s.s.zaman[-1] if s.s.zaman else None, "uygun_bar": len(s.s) - BAS - 1}
                         for s in seriler},
        "dislanan": dislanan,
        "ortak_baslangic": BAS, "ufuk": UFUK, "bootstrap": BOOTSTRAP, "rastgele_tekrar": args.tekrar,
        "tohum": TOHUM, "maliyet": "0 (brüt) — yerel serilerde spread ölçülmedi; 5 dk FX maliyet tablosu ayrı koşudan",
    }
    CIKTI.write_text(json.dumps({"kunye": kunye, "yapilandirma": sonuclar}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nyazıldı → {CIKTI.relative_to(KOK)} ({CIKTI.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
