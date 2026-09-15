#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörünün BACKTEST'i — gerçek barlar, tek işlem kuralı, ablasyon.

NEDEN VAR. Sayfadaki "işlem mekaniği" bölümü bir emir kuralı anlatıyor ve o
kuralın hiçbir sayısı ÖLÇÜLMEMİŞTİ: kaç işlem üretir, kaçı kazanır, kenar
var mı, hangi süzgeç ne katar. Rejim panosunun beş bant işaretinin üçünün
sabit olduğu ölçüldü (örtüşme %90 açık, doji %0, kesişme %92) ve kullanıcı
aynı şeyi gözle gördü; "daha fazla işlem üreten" bir indikatör istemeden
önce mevcut kuralın ne ürettiği sayıyla bilinmeli. Bu araç onu ölçer.

KURALLARIN KENDİSİ BURADA DEĞİL. Sinyal barı, kalite, always-in, yön
filtresi, rejim ve barbwire `brooks_referans`ten içe aktarılır — Pine
dosyalarının Python replikasyonu, kendi geleceğe-bakma kapısıyla. Burada
yalnız EMİR MEKANİĞİ ve ÖLÇÜM var.

İŞLEM KURALI (sayfada yazılı emir mekaniği; burada değiştirilmez):
  · Sinyal barı i KAPANMIŞ bardır: boğa için `donus_bari(i, True)` ve
    `kalite(i, True) ≥ K`; ayı aynası.
  · Süzgeçler, her biri açılıp kapanabilir: (a) rejim ≠ BANT (pencere
    dolmadıysa bar atlanır) · (b) always-in yönü sinyal yönüyle aynı ·
    (c) yön filtresi o yönü yasaklamıyor · (d) barbwire yoksa · (e) K.
  · Giriş: boğada sinyal barının YÜKSEĞİNE stop emri; i+1 barının yükseği
    sinyal yükseğini KESİN aşarsa dolar, dolum fiyatı sinyal yükseği (kayma
    yok). Aşmazsa emir iptal. Ayıda ayna.
  · Stop: sinyal barının karşı ucu. Risk = giriş − stop. Hedef = giriş +
    R·risk; R ∈ {1, 2} ikisi de ölçülür.
  · Dolum barından itibaren her bar (dolum barı dahil): düşük ≤ stop → −1R;
    yüksek ≥ hedef → +R; ikisi aynı barda → KAYIP (tutucu). 100 barda sonuç
    yoksa 100. barın kapanışından çıkılır, kesirli R yazılır; seri daha önce
    biterse son kapanıştan çıkılır ve ayrı sayılır.
  · Aynı seride aynı anda TEK pozisyon; pozisyondayken sinyal yok sayılır.
    Çıkış barı kapandıktan sonra o bar yeniden sinyal barı olabilir.
  · Aynı barda iki yön birden geçerse kalitesi yüksek olan alınır; eşitse
    bar atlanır ve sayılır (`belirsiz`).

ÖLÇÜLEN: yapılandırma başına N, kazanma oranı (R > 0 payı), ortalama R,
ortalama R için bootstrap %95 güven aralığı (1.000 yeniden örnekleme), kâr
faktörü, R cinsinden azami geri çekilme (işlemler sinyal zamanına göre
sıralı, bütün seriler tek defterde), çift vuruş sayısı (kaybın kaçı "aynı
barda ikisi" hükmünden — tutucu kuralın payı), seri bazında dağılım, zaman ayrımı
(her serinin uygun aralığının ilk / ikinci yarısı) ve RASTGELE TABAN: her
seride gerçek koşunun EMİR sayısı kadar rastgele bar + rastgele yön, aynı
mekanik, 300 tekrar → gerçek ortalama R'nin bu dağılımdaki yüzdeliği. Bu
taban olmadan hiçbir isabet sayısı anlamlı değildir: rastgele girişin de
bir kazanma oranı vardır.

ÖLÇÜLMEYEN, adıyla:
  · Kayma, komisyon, spread YOK. Dolum tam sinyal ucundan; stop tam stop
    fiyatından. Günlük barlarda gece boşluğu stop'un ötesine açılsa da kayıp
    −1R yazılır — gerçek kayıp daha büyüktür. Kenar varsa bu ölçüm onu
    olduğundan İYİ gösterir.
  · Yalnız 1 saatlik, 4 saatlik ve günlük barlar; dersin eşikleri 5
    dakikalık barda kalibre. Kullanıcının gözlediği 5 dakikalık EUR/USD bu
    ölçümde YOK.
  · 13 seri, 4.574 bar; saatlik seriler Ağustos–Eylül 2026'nın üç haftası,
    günlükler bir yıl. Örneklem DAR ve tek bir rejim penceresi; N küçük
    kaldığında güven aralığı bunu söyler, sayıya eklenmez.
  · Ortak başlangıç barı bütün yapılandırmalarda AYNI: rejim penceresinin
    dolduğu ilk bar. Süzgeç kaldırıldığında örneklem değişmesin diye; bedeli
    her serinin ilk 88 barının hiçbir yapılandırmada sinyal üretmemesi.
  · Seans saati, haber takvimi, pozisyon büyüklüğü, portföy etkisi yok.
    Azami geri çekilme seriler arası zaman sırasına göre tek defterde
    ölçülür ve bir portföy eğrisinin kaba bir yaklaşımıdır.
  · Backtest örneklem İÇİDİR: kurallar bu barlara bakılarak seçilmedi ama
    ablasyon matrisindeki "en iyi" yapılandırmayı seçip yayımlamak, seçimi
    aynı veride yapmaktır. Sıralama da bir sonuçtur ve örneklem büyüyünce
    değişebilir.

ÇIKTI: site/src/data/brooks_backtest.json (künye + bütün yapılandırmalar +
işlem listeleri) ve stdout'ta ortak/bicim ile yazılmış tablo.

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

import brooks_ornek as O                                         # noqa: E402
import brooks_referans as R                                      # noqa: E402
from brooks_referans import FiyatPaneli, RejimPanosu, Seri       # noqa: E402
from ortak import bicim as B                                     # noqa: E402

KOK = SITE.parent
CIKTI = SITE / "src" / "data" / "brooks_backtest.json"

UFUK = 100              # dolumdan sonra en çok bu kadar bar; sonra kapanıştan çıkış
HEDEFLER = (1, 2)       # R katları — ikisi de ölçülür
BOOTSTRAP = 1000
RASTGELE_TEKRAR = 300
TOHUM = 20260915        # tekrarlanabilirlik: aynı veri, aynı sayı

# Ortak başlangıç: rejim penceresinin dolduğu ilk bar. `RejimPanosu.olcu`
# i+1 ≥ pencere ve ema[i−pencere+1] tanımlı ister; EMA maUzunluk−1'de başlar.
BAS = int(R.SABIT_RP["pencere"]) + int(R.SABIT_RP["maUzunluk"]) - 2

# Ablasyon matrisi. Sıra sayfadaki tabloya olduğu gibi gider.
YAPILANDIRMA: list[tuple[str, dict]] = [
    ("tam sistem · K≥3",        dict(rejim=True,  ai=True,  yon=True,  bw=True,  K=3)),
    ("tam sistem · K≥2",        dict(rejim=True,  ai=True,  yon=True,  bw=True,  K=2)),
    ("tam sistem · K=4",        dict(rejim=True,  ai=True,  yon=True,  bw=True,  K=4)),
    ("−rejim · K≥3",            dict(rejim=False, ai=True,  yon=True,  bw=True,  K=3)),
    ("−always-in · K≥3",        dict(rejim=True,  ai=False, yon=True,  bw=True,  K=3)),
    ("−yön filtresi · K≥3",     dict(rejim=True,  ai=True,  yon=False, bw=True,  K=3)),
    ("−barbwire · K≥3",         dict(rejim=True,  ai=True,  yon=True,  bw=False, K=3)),
    ("süzgeçsiz · K≥1",         dict(rejim=False, ai=False, yon=False, bw=False, K=1)),
    ("yalnız always-in · K≥1",  dict(rejim=False, ai=True,  yon=False, bw=False, K=1)),
]


# ── Seri başına ölçüm: referans bir kez çağrılır, süzgeçler sonra sorulur ──
class SeriOlcum:
    """Bir serinin bar bar sinyal girdileri. Kural katmanı burada ÇAĞRILIR,
    yeniden yazılmaz: dönüş barı, kalite, always-in, yön filtresi, rejim ve
    barbwire referanstan gelir."""

    def __init__(self, ad: str, s: Seri):
        self.ad, self.s = ad, s
        fp, rp = FiyatPaneli(s), RejimPanosu(s)
        n = len(s)
        self.ai, _, _ = fp.always_in()
        self.donus = {1: [False] * n, -1: [False] * n}
        self.kalite = {1: [0] * n, -1: [0] * n}
        self.yasak = {1: [False] * n, -1: [False] * n}
        self.rejim: list[str | None] = [None] * n
        self.bw = [False] * n
        for i in range(1, n):
            for yon, boga in ((1, True), (-1, False)):
                if fp.donus_bari(i, boga):
                    self.donus[yon][i] = True
                    self.kalite[yon][i] = fp.kalite(i, boga)
            f = fp.yon_filtresi(i)
            self.yasak[-1][i] = f == "yalnız AL"
            self.yasak[1][i] = f == "yalnız SAT"
            o = rp.olcu(i)
            self.rejim[i] = o["rejim"] if o else None
            self.bw[i] = rp.barbwire(i)["var"]

    def sinyal(self, i: int, ayar: dict) -> tuple[int, bool]:
        """(yön, belirsiz). Yön 0 = sinyal yok. Belirsiz = iki yön eşit kalite."""
        if ayar["rejim"]:
            if self.rejim[i] is None or self.rejim[i] == "BANT":
                return 0, False
        if ayar["bw"] and self.bw[i]:
            return 0, False
        aday = []
        for yon in (1, -1):
            if not self.donus[yon][i] or self.kalite[yon][i] < ayar["K"]:
                continue
            if ayar["ai"] and self.ai[i] != yon:
                continue
            if ayar["yon"] and self.yasak[yon][i]:
                continue
            aday.append((self.kalite[yon][i], yon))
        if not aday:
            return 0, False
        if len(aday) == 2 and aday[0][0] == aday[1][0]:
            return 0, True
        return max(aday)[1], False


# ── Emir mekaniği ───────────────────────────────────────────────────────────
def islem_kos(s: Seri, sinyal, hedef_r: float, bas: int = 0, ufuk: int = UFUK) -> dict:
    """Bir seriyi baştan sona dolaşır; `sinyal(i)` → +1 / −1 / 0.

    Döner: {"islemler": [...], "emir": n, "dolmayan": n}. Her işlem sinyal
    barı, dolum barı, çıkış barı, çıkış türü ve R taşır."""
    n = len(s)
    islemler: list[dict] = []
    emir = dolmayan = sifir_menzil = 0
    i = max(bas, 1)
    while i <= n - 2:
        yon = sinyal(i)
        if not yon:
            i += 1
            continue
        emir += 1
        j = i + 1
        if yon == 1:
            giris, stop, dolu = s.h[i], s.l[i], s.h[j] > s.h[i]
        else:
            giris, stop, dolu = s.l[i], s.h[i], s.l[j] < s.l[i]
        if not dolu:
            dolmayan += 1
            i = j
            continue
        risk = abs(giris - stop)
        if risk <= 0:
            sifir_menzil += 1
            i = j
            continue
        hedef = giris + yon * hedef_r * risk
        son = min(n, j + ufuk) - 1
        sonuc: tuple[float, str, int] | None = None
        cift = False                            # aynı barda hem hedef hem stop görüldü mü
        for k in range(j, son + 1):
            if yon == 1:
                stop_vurdu, hedef_vurdu = s.l[k] <= stop, s.h[k] >= hedef
            else:
                stop_vurdu, hedef_vurdu = s.h[k] >= stop, s.l[k] <= hedef
            if stop_vurdu:                      # ikisi aynı barda → kayıp (tutucu)
                sonuc = (-1.0, "stop", k)
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
            "giris": giris, "stop": stop, "tur": sonuc[1], "R": sonuc[0], "cift": cift,
        })
        i = sonuc[2]          # çıkış barı kapandı; yeniden sinyal barı olabilir
    return {"islemler": islemler, "emir": emir, "dolmayan": dolmayan, "sifir_menzil": sifir_menzil}


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
        return None            # kayıp yoksa oran tanımsız; sonsuz yazılmaz
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
    return {
        "n": n,
        "kazanma": round(sum(1 for r in rs if r > 0) / n, 4) if n else None,
        "ort_R": round(_ort(rs), 4) if n else None,
        "ca_alt": round(ca[0], 4) if ca else None,
        "ca_ust": round(ca[1], 4) if ca else None,
        "toplam_R": round(sum(rs), 3),
        "kar_faktoru": (round(kar_faktoru(rs), 3) if n and kar_faktoru(rs) is not None else None),
        "azami_geri_cekilme_R": round(azami_geri_cekilme(rs), 3) if n else None,
    }


# ── Rastgele taban ──────────────────────────────────────────────────────────
def rastgele_kos(s: Seri, m: int, hedef_r: float, rng: random.Random, bas: int = BAS) -> dict:
    """Gerçek koşunun EMİR sayısı (m) kadar rastgele bar + rastgele yön, aynı
    mekanik. Pozisyon içine düşen aday emir üretmez; emir sayısı m'ye
    ulaşana kadar aday eklenir (en çok 20 tur — tam eşitlik şart değil,
    eşitsizlik kayda yazılır)."""
    uygun = list(range(max(bas, 1), len(s) - 1))
    if m == 0 or not uygun:
        return {"islemler": [], "emir": 0, "dolmayan": 0, "sifir_menzil": 0}
    rng.shuffle(uygun)
    secili: dict[int, int] = {}
    hedef, ptr, son = min(m, len(uygun)), 0, None
    for _ in range(20):
        while len(secili) < hedef and ptr < len(uygun):
            secili[uygun[ptr]] = rng.choice((1, -1))
            ptr += 1
        son = islem_kos(s, lambda i: secili.get(i, 0), hedef_r, bas=bas)
        if son["emir"] >= m or ptr >= len(uygun):
            break
        hedef += m - son["emir"]
    return son


# ── Bir yapılandırmanın tam ölçümü ──────────────────────────────────────────
def yapilandirma_olc(ad: str, ayar: dict, hedef_r: float, seriler: list[SeriOlcum],
                     rng: random.Random, tekrar: int = RASTGELE_TEKRAR) -> dict:
    islemler: list[dict] = []
    seri_ozet: dict[str, dict] = {}
    emir_seri: dict[str, int] = {}
    belirsiz = dolmayan = sifir = 0
    ilk: list[float] = []
    ikinci: list[float] = []
    for so in seriler:
        s = so.s
        sayac = {"belirsiz": 0}

        def sinyal(i, so=so, sayac=sayac):
            yon, b = so.sinyal(i, ayar)
            sayac["belirsiz"] += b
            return yon

        son = islem_kos(s, sinyal, hedef_r, bas=BAS)
        belirsiz += sayac["belirsiz"]
        dolmayan += son["dolmayan"]
        sifir += son["sifir_menzil"]
        emir_seri[so.ad] = son["emir"]
        rs = [t["R"] for t in son["islemler"]]
        orta = (BAS + len(s)) // 2
        for t in son["islemler"]:
            (ilk if t["sinyal"] < orta else ikinci).append(t["R"])
            islemler.append(dict(t, seri=so.ad, zaman=s.zaman[t["sinyal"]] if s.zaman else None,
                                 cikis_zaman=s.zaman[t["cikis"]] if s.zaman else None,
                                 kalite=so.kalite[t["yon"]][t["sinyal"]]))
        seri_ozet[so.ad] = dict(ozet(rs), emir=son["emir"],
                                bar=len(s) - BAS - 1,
                                tur={k: sum(1 for t in son["islemler"] if t["tur"] == k)
                                     for k in ("hedef", "stop", "zaman_asimi", "seri_sonu")})

    # Defter zaman sırasına dizilir; azami geri çekilme bu sıradan ölçülür.
    islemler.sort(key=lambda t: (t["zaman"] or "", t["seri"]))
    rs = [t["R"] for t in islemler]
    toplam_emir = sum(emir_seri.values())

    # Rastgele taban — aynı emir sayısı, aynı mekanik, `tekrar` kez.
    r_ort: list[float] = []
    r_n: list[int] = []
    r_emir: list[int] = []
    for _ in range(tekrar):
        hepsi: list[float] = []
        e = 0
        for so in seriler:
            son = rastgele_kos(so.s, emir_seri[so.ad], hedef_r, rng)
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

    return {
        "ad": ad, "suzgec": {k: v for k, v in ayar.items() if k != "K"}, "K": ayar["K"],
        "hedef_R": hedef_r,
        **ozet(rs, rng),
        "emir": toplam_emir, "dolmayan": dolmayan, "belirsiz": belirsiz, "sifir_menzil": sifir,
        "dolum_orani": round(len(rs) / toplam_emir, 3) if toplam_emir else None,
        "tur": {k: sum(1 for t in islemler if t["tur"] == k)
                for k in ("hedef", "stop", "zaman_asimi", "seri_sonu")},
        # Tutucu kuralın payı: kaybın kaçı "aynı barda ikisi" hükmünden geldi.
        # Bu sayı mekaniğin eksi eğiliminin ölçüsüdür; rastgele taban aynı
        # eğilimi taşır, o yüzden kıyas ona karşı yapılır.
        "cift_vurus": sum(1 for t in islemler if t.get("cift")),
        "ilk_yari": ozet(ilk, rng),
        "ikinci_yari": ozet(ikinci, rng),
        "seri": seri_ozet,
        "rastgele": rastgele,
        "islemler": [{"seri": t["seri"], "zaman": t["zaman"], "yon": t["yon"], "kalite": t["kalite"],
                      "giris": t["giris"], "stop": t["stop"], "tur": t["tur"], "cift": t["cift"],
                      "cikis_zaman": t["cikis_zaman"], "R": round(t["R"], 4)} for t in islemler],
    }


# ── Kapılar: mekanik sentetik barlarla, rastgelelik kendi dağılımıyla ───────
def _seri(b: list[tuple]) -> Seri:
    return Seri([x[0] for x in b], [x[1] for x in b], [x[2] for x in b], [x[3] for x in b])


def kendini_sina() -> list[str]:
    """Kuralın İLAN ETTİĞİ hâllere koşulur. Her madde tek bir mekanik cümle."""
    hata: list[str] = []
    duz = (10.0, 10.2, 9.8, 10.0)                  # sinyal dışı dolgu barı
    sinyal = (10.0, 10.5, 10.0, 10.4)              # sinyal barı: giriş 10,5 · stop 10,0 · risk 0,5
    tek = lambda i: (lambda j: 1 if j == i else 0)   # noqa: E731

    # ① Bilinen kazanç: dolum barı 10,6'ya çıkar (kesin aşma), hedef R=1 → 11,0 sonraki barda.
    b = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 11.1, 10.4, 11.0), duz]
    son = islem_kos(_seri(b), tek(2), 1.0)
    t = son["islemler"]
    if len(t) != 1 or t[0]["tur"] != "hedef" or t[0]["R"] != 1.0 or t[0]["giris"] != 10.5 or t[0]["cikis"] != 4:
        hata.append(f"① bilinen kazanç +1R, çıkış 4. barda beklenirdi; {t}")

    # ② Bilinen kayıp: dolumdan sonra düşük stop'a değer.
    b2 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 10.7, 9.9, 10.0), duz]
    t = islem_kos(_seri(b2), tek(2), 1.0)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "stop" or t[0]["R"] != -1.0:
        hata.append(f"② bilinen kayıp −1R beklenirdi; {t}")

    # ③ Aynı barda ikisi: yüksek hedefi, düşük stop'u görür → KAYIP (tutucu).
    b3 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 11.2, 9.9, 10.8), duz]
    t = islem_kos(_seri(b3), tek(2), 1.0)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "stop" or t[0]["R"] != -1.0:
        hata.append(f"③ aynı barda hedef+stop kayıp sayılmalıydı; {t}")

    # ④ Dolmayan emir: sonraki barın yükseği sinyal yükseğine EŞİT (aşmıyor) → işlem yok.
    b4 = [duz, duz, sinyal, (10.4, 10.5, 10.3, 10.45), (10.45, 11.2, 10.4, 11.0), duz]
    son = islem_kos(_seri(b4), tek(2), 1.0)
    if son["islemler"] or son["emir"] != 1 or son["dolmayan"] != 1:
        hata.append(f"④ eşit yüksek dolum sayılmamalıydı; {son}")

    # ④b Ayı aynası: dolum barının düşüğü sinyal düşüğünün altına iner, hedef aşağıda.
    ayi = (10.0, 10.0, 9.5, 9.6)                    # giriş 9,5 · stop 10,0 · R=2 hedef 8,5
    b5 = [duz, duz, ayi, (9.6, 9.7, 9.4, 9.5), (9.5, 9.6, 8.4, 8.5), duz]
    t = islem_kos(_seri(b5), lambda j: -1 if j == 2 else 0, 2.0)["islemler"]
    if len(t) != 1 or t[0]["tur"] != "hedef" or t[0]["R"] != 2.0 or t[0]["giris"] != 9.5:
        hata.append(f"④b ayı aynası +2R beklenirdi; {t}")

    # ⑤ Zaman aşımı: 100 barda ne hedef ne stop → kapanıştan çıkış, kesirli R.
    b6 = [duz, duz, sinyal] + [(10.4, 10.6, 10.3, 10.45)] * 120
    t = islem_kos(_seri(b6), tek(2), 2.0)["islemler"]
    beklenen = (10.45 - 10.5) / 0.5
    if len(t) != 1 or t[0]["tur"] != "zaman_asimi" or abs(t[0]["R"] - beklenen) > 1e-9 or t[0]["cikis"] != 3 + UFUK - 1:
        hata.append(f"⑤ zaman aşımında kesirli R {beklenen:.2f} beklenirdi; {t}")

    # ⑥ Tek pozisyon: pozisyondayken gelen sinyal emir üretmez, çıkış barı üretebilir.
    b7 = [duz, duz, sinyal, (10.4, 10.6, 10.3, 10.5), (10.5, 10.6, 10.3, 10.5),
          (10.5, 11.1, 10.4, 11.0), (11.0, 11.6, 11.0, 11.5), (11.5, 11.7, 11.4, 11.6), duz]
    son = islem_kos(_seri(b7), lambda j: 1 if j in (2, 3, 4, 5) else 0, 1.0)
    if son["emir"] != 2 or len(son["islemler"]) != 2 or son["islemler"][1]["sinyal"] != 5:
        hata.append(f"⑥ pozisyondaki sinyaller (3, 4) atlanmalı, çıkış barı (5) yeni sinyal olmalıydı; {son}")

    # ⑦ Rastgele taban gerçekten rastgele mi: sürüklenmesiz sentetik seride
    #    300 tekrarın %95 bandı sıfırı KAPSAMALI. Mekanik simetrik DEĞİL —
    #    "ikisi aynı barda → kayıp" kuralı eksi eğilim taşır; ölçüldü
    #    (3.000 barlık sentetik seri, 120 emir, R=1): ortalama −0,17 R, bant
    #    [−0,43, +0,09]. Eğilim mekaniğin kendisidir ve gerçek sinyaller de
    #    aynı mekanikten geçer; rastgele tabanın gerekçesi tam olarak budur —
    #    "sıfırdan iyi" değil "aynı mekanikte rastgeleden iyi" sorulur.
    s = R._sentetik(3000, tohum=11)
    rng = random.Random(TOHUM)
    ortalar = []
    for _ in range(RASTGELE_TEKRAR):
        rs = [t["R"] for t in rastgele_kos(s, 120, 1.0, rng)["islemler"]]
        ortalar.append(_ort(rs) or 0.0)
    sirali = sorted(ortalar)
    alt, ust = sirali[int(0.025 * len(sirali))], sirali[int(0.975 * len(sirali)) - 1]
    if not (alt <= 0.0 <= ust):
        hata.append(f"⑦ rastgele taban sıfırı kapsamalıydı; %95 bant [{alt:.3f}, {ust:.3f}]")
    # ve yön dağılımı simetrik: iki yönün payı %40–60 arasında.
    yonler = []
    rng2 = random.Random(TOHUM + 1)
    for _ in range(30):
        yonler += [t["yon"] for t in rastgele_kos(s, 120, 1.0, rng2)["islemler"]]
    pay = sum(1 for y in yonler if y == 1) / len(yonler)
    if not 0.40 <= pay <= 0.60:
        hata.append(f"⑦ rastgele yön payı dengesiz: boğa {pay:.3f}")

    # ⑧ Tekrarlanabilirlik: aynı tohum aynı sonucu vermeli.
    a = rastgele_kos(s, 50, 1.0, random.Random(5))["islemler"]
    b = rastgele_kos(s, 50, 1.0, random.Random(5))["islemler"]
    if a != b:
        hata.append("⑧ aynı tohumla iki koşu ayrıştı")

    # ⑩ Ayna simetrisi: fiyat −fiyat, yön −yön → R listesi BİREBİR aynı.
    #    Boğa ve ayı kolu ayrı yazıldığı için biri sessizce ayrışabilir; bu
    #    madde iki kolu tek ölçüyle bağlar.
    ayna = Seri([-x for x in s.o], [-x for x in s.l], [-x for x in s.h], [-x for x in s.c])
    rng3 = random.Random(TOHUM + 2)
    secili = {i: rng3.choice((1, -1)) for i in rng3.sample(range(BAS, len(s) - 1), 150)}
    duz_r = [t["R"] for t in islem_kos(s, lambda i: secili.get(i, 0), 2.0, bas=BAS)["islemler"]]
    ayna_r = [t["R"] for t in islem_kos(ayna, lambda i: -secili.get(i, 0), 2.0, bas=BAS)["islemler"]]
    if len(duz_r) != len(ayna_r) or any(abs(a - b) > 1e-9 for a, b in zip(duz_r, ayna_r)):
        hata.append(f"⑩ ayna simetrisi bozuk: {len(duz_r)} ↔ {len(ayna_r)} işlem")

    # ⑨ Ortak başlangıç sözleşmesi: BAS rejim penceresinin dolduğu İLK bar.
    rp = RejimPanosu(R._sentetik(200))
    if rp.olcu(BAS) is None or rp.olcu(BAS - 1) is not None:
        hata.append(f"⑨ BAS={BAS} rejim penceresinin dolduğu ilk bar değil")

    return hata


# ── Okunur tablo ────────────────────────────────────────────────────────────
def _tablo(yapilar: list[dict]) -> str:
    bas = (f"{'yapılandırma':26s} {'R':>2s} {'N':>4s} {'kazan':>7s} {'ort R':>7s} "
           f"{'%95 CA':>16s} {'KF':>6s} {'azGÇ':>6s} {'rast.%':>7s} {'ilk/ikinci':>16s}")
    satir = [bas, "─" * len(bas)]
    for y in yapilar:
        ca = (f"[{B.sayi(y['ca_alt'], 2, True)}, {B.sayi(y['ca_ust'], 2, True)}]"
              if y["ca_alt"] is not None else "—")
        ilk, iki = y["ilk_yari"], y["ikinci_yari"]
        yari = f"{B.sayi(ilk['ort_R'], 2, True)}/{B.sayi(iki['ort_R'], 2, True)}"
        satir.append(
            f"{y['ad']:26s} {y['hedef_R']:>2.0f} {y['n']:4d} "
            f"{B.yuzde((y['kazanma'] or 0) * 100, 1) if y['n'] else '—':>7s} "
            f"{B.sayi(y['ort_R'], 2, True):>7s} {ca:>16s} "
            f"{B.sayi(y['kar_faktoru'], 2):>6s} {B.sayi(y['azami_geri_cekilme_R'], 1):>6s} "
            f"{B.sayi(y['rastgele']['yuzdelik'], 0):>7s} {yari:>16s}")
    kucuk = [f"{y['ad']} R={y['hedef_R']:.0f} (N={y['n']})" for y in yapilar if y["n"] < 30]
    if kucuk:
        satir.append("N < 30 — bu satırlarda hiçbir ölçü hüküm taşımaz: " + " · ".join(kucuk))
    satir.append("rast.% = gerçek ortalama R'nin, aynı emir sayısıyla rastgele bar + rastgele yönün "
                 "300 tekrarlık dağılımındaki yüzdeliği; %95 CA sıfırı kapsıyorsa kenar ölçülemedi.")
    return "\n".join(satir)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--denetle", action="store_true", help="yalnız mekanik sınamaları koştur")
    ap.add_argument("--tekrar", type=int, default=RASTGELE_TEKRAR, help="rastgele taban tekrar sayısı")
    a = ap.parse_args()

    hata = kendini_sina()
    if hata:
        print("DENETİM DÜŞTÜ:", file=sys.stderr)
        for h in hata:
            print("  ✗", h, file=sys.stderr)
        raise SystemExit(1)
    print("denetim · 10 madde GEÇTİ (kazanç · kayıp · aynı bar · dolmayan · ayı aynası · "
          "zaman aşımı · tek pozisyon · rastgele taban · tekrarlanabilirlik · ayna simetrisi)")
    if a.denetle:
        return

    yollar = sorted((SITE / "public" / "teknik").glob("*.html"))
    hepsi = [O.bar_oku(y) for y in yollar]
    gecen = [k for k in hepsi if O.govde_kunyesi(k.seri)["gecti"]]
    dislanan = [k.anahtar for k in hepsi if not O.govde_kunyesi(k.seri)["gecti"]]
    seriler = [SeriOlcum(k.anahtar, k.seri) for k in gecen]
    print(f"veri · {len(seriler)} seri, {sum(len(s.s) for s in seriler)} bar, "
          f"ortak başlangıç barı {BAS}; dışlanan: {', '.join(dislanan) or '—'}")

    rng = random.Random(TOHUM)
    yapilar: list[dict] = []
    for ad, ayar in YAPILANDIRMA:
        for hedef_r in HEDEFLER:
            y = yapilandirma_olc(ad, ayar, float(hedef_r), seriler, rng, a.tekrar)
            yapilar.append(y)
            print(f"  ölçüldü · {ad:26s} R={hedef_r}  N={y['n']:4d}  emir={y['emir']:4d}", file=sys.stderr)

    kunye = {
        "olcum_tarihi": date.today().isoformat(),
        "kaynak": "site/public/teknik/*.html (teknik/olc.py'nin kapanmış-bar disiplininden geçmiş OHLC)",
        "kural_kaynagi": "site/public/indikatorler/brooks_referans.py (Pine replikasyonu)",
        "seri": len(seriler),
        "bar": sum(len(s.s) for s in seriler),
        "seri_listesi": {s.ad: {"bar": len(s.s), "bas": s.s.zaman[0], "son": s.s.zaman[-1],
                                "uygun_bar": len(s.s) - BAS - 1} for s in seriler},
        "dislanan": dislanan,
        "ortak_baslangic_bari": BAS,
        "ufuk_bar": UFUK,
        "hedef_R": list(HEDEFLER),
        "bootstrap": BOOTSTRAP,
        "rastgele_tekrar": a.tekrar,
        "tohum": TOHUM,
        "kural": {
            "sinyal": "kapanmış bar i: donus_bari(i, yön) ve kalite(i, yön) ≥ K",
            "giris": "sinyal barının yönündeki ucuna stop emri; i+1 barı o ucu KESİN aşarsa "
                     "dolar, dolum fiyatı sinyal ucu (kayma yok); aşmazsa iptal",
            "stop": "sinyal barının karşı ucu; risk = giriş − stop",
            "hedef": "giriş + R·risk",
            "cikis": "dolum barından itibaren (dolum barı dahil) stop → −1R, hedef → +R, "
                     "ikisi aynı barda → kayıp; 100 barda sonuç yoksa kapanıştan kesirli R; "
                     "seri biterse son kapanıştan (seri_sonu)",
            "pozisyon": "seri başına tek pozisyon; pozisyondayken sinyal yok sayılır; "
                        "çıkış barı yeniden sinyal barı olabilir",
            "belirsiz": "aynı barda iki yön eşit kaliteyle geçerse bar atlanır",
            "kazanma": "R > 0 payı (kesirli çıkışlar dahil)",
            "zaman_ayrimi": "her serinin uygun aralığı [BAS, son) ikiye bölünür; sinyal barına göre",
            "rastgele_taban": "her seride gerçek koşunun emir sayısı kadar rastgele bar + rastgele "
                              "yön, aynı mekanik; yüzdelik = rastgele ortalama R'lerin gerçek "
                              "ortalamanın altında kalan payı",
        },
        "olculmeyen": [
            "kayma, komisyon, spread yok; gece boşluğu stop'un ötesine açılsa da kayıp −1R yazılır",
            "yalnız 1 saatlik ve üstü barlar; dersin eşikleri 5 dakikalıkta kalibre",
            "13 seri; saatlik seriler Ağustos–Eylül 2026'nın üç haftası — tek rejim penceresi",
            "her serinin ilk 88 barı hiçbir yapılandırmada sinyal üretmez (ortak başlangıç)",
            "seans saati, haber takvimi, pozisyon büyüklüğü, portföy etkisi yok",
            "örneklem içi: ablasyondan 'en iyi'yi seçmek seçimi aynı veride yapmaktır",
        ],
    }
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps({"kunye": kunye, "yapilandirma": yapilar},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(_tablo(yapilar))
    print(f"\nyazıldı · {CIKTI.relative_to(KOK)}")


if __name__ == "__main__":
    main()
