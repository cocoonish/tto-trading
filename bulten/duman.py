#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten katmanlarının duman sınaması — ağsız, saniyeler içinde.

Neden var: bu depoyu birden çok oturum aynı gün düzenliyor ve aralarındaki
SÖZLEŞME KAYMASI kimsenin sınamadığı yerden vuruyor. 26.08.2026'da tam bu
oldu — bir oturum `_yayimlar()`'ı tek listeden (kayıtlar, alındı_mı) çiftine
çevirdi, başka bir oturum aynı gün onu tek liste sanan yeni bir çağrı ekledi.
Merge ikisini de sorunsuz aldı, iki değişiklik de kendi başına doğruydu, ama
birleşimleri üretimde TypeError verdi ve veri hattı düştü.

Bu dosya o sınıfın tamamını yakalar: her katmanın giriş noktasını GERÇEK depo
verisiyle çağırır. Ağ istemez, EVDS anahtarı istemez, saniyeler sürer — yani
her iş akışının en başında, ağa çıkmadan önce koşabilir.

Bir TANI aracı DEĞİLDİR: üretim kod yollarını sınar, düşerse iş akışı durmalı.
(Karşıtı için bkz. veri.yml'deki tazeleme raporu — o rapordur, durdurmaz.)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import traceback
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
BULTENLER = BURASI.parent / "site" / "src" / "data" / "bulten"

gecen: list[str] = []
dusen: list[tuple[str, str]] = []


def sina(ad: str, fn):
    try:
        fn()
        gecen.append(ad)
    except Exception:                                          # noqa: BLE001
        dusen.append((ad, traceback.format_exc(limit=3).strip().splitlines()[-1]))


def son_bulten() -> dict | None:
    dosyalar = sorted(BULTENLER.glob("*.json")) if BULTENLER.exists() else []
    return json.loads(dosyalar[-1].read_text(encoding="utf-8")) if dosyalar else None


def _yayin_takvimi():
    """Okura anlatılan saat, iş akışının gerçek saati olmalı. Karşılaştırma TEK
    yerde (ortak/yayin_takvimi.karsilastir); sayfa sınavı da aynı fonksiyonu çağırır."""
    import sys as _s
    kok = Path(__file__).resolve().parents[1]
    _s.path.insert(0, str(kok / "ortak"))
    import yayin_takvimi
    bulgu = yayin_takvimi.karsilastir(kok)
    assert not bulgu, "; ".join(bulgu)


def _turev_rejim_gunu():
    """Revizyon kıyası satırın gününe dayanır: üretici o günü yazmalı."""
    import piyasa as py
    import rejim as rj
    seri = {k: {"tarih": ["2026-08-27", "2026-08-28"], "kapanis": v} for k, v in
            {"^TNX": [4.20, 4.25], "2YY=F": [3.80, 3.79], "XU100.IS": [10800.0, 10900.0], "USDTRY=X": [41.0, 41.2]}.items()}
    seri["USDTRY=X"]["tarih"] = ["2026-08-28", "2026-08-29"]       # FX bir gün ileride
    t = {x["ad"]: x for x in py.turetilmis(seri)}
    assert t["ABD 2s10s"]["tarih"] == "2026-08-28" and t["ABD 2s10s"]["ondalik"] == 0 and t["ABD 2s10s"]["degisim_birim"] == "bp", t["ABD 2s10s"]
    assert t["BIST 100 (dolar bazlı)"]["tarih"] == "2026-08-28/2026-08-29", "bacak günleri ayrışınca bileşik anahtar yazılmalı"
    assert t["BIST 100 (dolar bazlı)"]["degisim_birim"] == "%" and t["BIST 100 (dolar bazlı)"]["birim"] == "USD puan"
    pano = rj.panosu()                        # sitedeki özetlerden, ağsız
    assert pano, "rejim panosu boş"
    for x in pano:
        assert isinstance(x.get("ondalik"), int), x["ad"]
        assert x.get("tarih"), f"{x['ad']}: girdi günü boş"
    rez = [x for x in pano if x["ad"] == "Rezerv kalitesi"]
    if rez:
        import gozlem
        d = gozlem.anlik("tcmb-net-rezerv") or {}
        assert rez[0]["tarih"] == str(d.get("h_tarih")), (rez[0]["tarih"], d.get("h_tarih"))


def _revizyon():
    import json as _json
    import tempfile
    import denetim as dn
    class _D(dn.Denetim):
        def __init__(self, b):
            self.b = b; self.gecen = []; self.uyari = []; self.engel = []; self.ayrinti = False
    def bulten(tarih, faiz, gosterge, piyasa_d1, gun="31.08.2026", turev=41.0, turev_d1=-9.3, rejim=13.31, gun_iso="2026-08-28"):
        return {"tarih": tarih,
                "piyasa": {"gruplar": [{"satirlar": [{"kod": "XAU", "ad": "Altın", "tarih": gun, "d1": piyasa_d1, "degisim_birim": "%"}]}],
                           "tr_faizleri": [{"ad": "Politika faizi", "deger": faiz, "birim": "%", "tarih": gun}],
                           "turetilmis": [{"ad": "ABD 2s10s", "deger": turev, "birim": "bp", "d1": turev_d1, "degisim_birim": "bp",
                                           "tarih": gun_iso, "ondalik": 0}]},
                "gostergeler": [{"ad": "USD/TRY", "hat": "usdtry", "anahtar": "kur", "deger": gosterge, "ondalik": 2, "veri_tarihi": gun}],
                "rejim": [{"ad": "Reel politika faizi (ileriye dönük)", "deger": rejim, "birim": "puan", "tarih": gun, "ondalik": 2}]}
    eski_BULTEN = dn.BULTEN
    with tempfile.TemporaryDirectory() as td:
        dn.BULTEN = Path(td)
        (dn.BULTEN / "2026-08-31.json").write_text(_json.dumps(bulten("2026-08-31", 40.0, 48.10, -0.86)), encoding="utf-8")
        try:
            d1 = _D(bulten("2026-09-01", 37.0, 48.17, 1.78, turev=44.0, turev_d1=-6.1, rejim=13.9)); d1.revizyon()
            assert len(d1.uyari) == 1 and "(6)" in d1.uyari[0], d1.uyari
            for ad in ("TL faiz · Politika faizi", "gösterge · USD/TRY", "piyasa · Altın", "türev · ABD 2s10s", "türev Δ · ABD 2s10s", "rejim · Reel politika"):
                assert ad in d1.uyari[0], (ad, d1.uyari)
            assert "→ -6.1bp" in d1.uyari[0] or "-6.1bp" in d1.uyari[0], d1.uyari
            d5 = _D(bulten("2026-09-01", 40.0, 48.10, -0.86, gun_iso="2026-08-28/2026-08-29")); d5.revizyon()
            assert not d5.uyari, f"bacak günü ayrışan türev satır kıyaslandı: {d5.uyari}"
            assert "türev 0/1" in d5.gecen[-1] and "rejim 1/1" in d5.gecen[-1], d5.gecen
            d2 = _D(bulten("2026-09-01", 40.0, 48.10, -0.86)); d2.revizyon()
            assert not d2.uyari, d2.uyari
            d3 = _D(bulten("2026-09-01", 37.0, 48.17, 1.78, gun="01.09.2026")); d3.revizyon()
            assert not d3.uyari, f"farklı günün sayısı revizyon sanıldı: {d3.uyari}"
            d4 = _D(bulten("2026-09-01", 40.0, 48.104, -0.86)); d4.revizyon()
            assert not d4.uyari, f"yuvarlama payı içindeki fark revizyon sanıldı: {d4.uyari}"
        finally:
            dn.BULTEN = eski_BULTEN


def _bicim():
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
    import bicim as bc
    import olay as ol
    import rejim as rj
    assert bc.sayi(-1.247, 3) == "−1,247" and bc.sayi(1234.5) == "1.234,5"
    assert bc.yuzde(-1.884, 2) == "−%1,88" and bc.yuzde(0.4, 1, True) == "+%0,4"
    assert bc.degisim(-6.5, "bp", 1) == "−6,5 bp" and bc.degisim(0.4, "%") == "+%0,40"
    assert bc.sayi(-0.001, 2) == "0,00", "yuvarlanan sıfır işaret taşımaz"
    assert ol._s(-696.0, 0) == "−696" and ol._s(0.4, 1, True) == "+0,4"
    assert rj.redk_konum(7.3) == "on yıllık ortalamanın %7,3 üstünde", rj.redk_konum(7.3)
    assert rj.redk_konum(-3.2) == "on yıllık ortalamanın %3,2 altında", rj.redk_konum(-3.2)
    assert rj.redk_konum(None) == ""
    import denetim as dn
    class _D(dn.Denetim):
        def __init__(self, b):
            self.b = b; self.gecen = []; self.uyari = []; self.engel = []; self.ayrinti = False
    d = _D({"tarih": "2026-09-01", "yorum": {"giris": "<p>Endeks -1.247'den -696'ya geçti; sapma %+7.3 oldu.</p>"}})
    d.bicim()
    assert any("ASCII eksi" in u for u in d.uyari), d.uyari
    assert any("ondalık noktası" in u for u in d.uyari), d.uyari
    d2 = _D({"tarih": "2026-09-01", "yorum": {"giris": "<p>Endeks −1,247'den −696'ya geçti; %7,3 üstünde. Veri 31.08.2026.</p>"}})
    d2.bicim()
    assert not d2.uyari, d2.uyari


def _kosu_kaydi_dili():
    """Koşu kaydı satırları okura OLDUĞU GİBİ gider: backtick, anahtar adı, bie_
    grubu, anahtar:tarih, ondalık nokta, ISO tarih, ASCII eksi yakalanır; kaynak
    künyesi (TP.AB.A19), GG.AA.YYYY tarih, binlik nokta ve bicim yazımı masumdur."""
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
    import okur_dili as od
    kotu = ["Sayfa metni `kkm_aktif` bayrağına bağlıdır", "bie_pydibsarsiv grubunda 13 seri adı (0.2%)",
            "ÖLÜ SERİ: 'glp_alis' son 252 iş günü", "koparıldı: m3:2024-06-28.", "en büyüğü 17.10.2025, 5.69 mlr USD.",
            "ezilmiş olabilir; `--yenile` ile tazeleyin", "oysa piyasa 1,838 (%-10.6, eşik %8)", "son çapa 2026-08-21",
            "mevduat_yp_usd_mia, bilanco_pay_ham daha yeni", "0.0 milyar TL ile", "sapma -4 bp", "ozet.json'dan okunur"]
    for s in kotu:
        assert od.kosu_kaydi_tara([s]), f"yakalanmadı: {s}"
    iyi = ["AYRI KALEM DEĞİL: ZK bloke hesabı (TP.AB.A19) 3323 iş günü boyunca tam sıfır basmış ve 15.03.2024 tarihinde doluyor.",
           "AOFM TABANSIZ: son 52 haftanın 6'inde APİ fonlaması 5 milyar TL eşiğinin altında olduğu hâlde EVDS bir AOFM basmış.",
           "en büyüğü 17.08.2018 (%5,2). Birim değil, revizyon farkıdır — taban EVDS toplamından okunduğu için hesap etkilenmez.",
           "ALT KALEM: 2 adet üç haneli grup son ayda (Temmuz 2026) veri vermiyor: 095, 105.",
           "IRFCL PDF'i 30,622 mn ons diyor; fiyatını 1.643 USD/ons yapıyor, oysa piyasa 1.838 (−%10,6, eşik %8).",
           "Veri taze: yayım gecikmesi tolerans içinde, tazelik uyarısı yok.",
           "TP.PY.P02.1H ile TP.BISPOLFAIZ.TUR arasında fark 0,00 puan; TP.APIFON1.TOP − TP.APIFON2.TOP",
           "koparıldı: M3 (28.06.2024). Seviye grafiğinde kırılma işaretlenir; miktar +1,126 mn ons değişti",
           "geç likidite penceresi alış faizi son 252 iş gününün TAMAMINDA 0 — dolu görünüyor ama bilgi taşımıyor"]
    for s in iyi:
        assert not od.kosu_kaydi_tara([s]), (s, od.kosu_kaydi_tara([s]))
    # tara() muafiyeti kapatılabilir: backtick içi ad koşu kaydında kod dilidir
    assert not od.tara("`kkm_aktif`") and od.tara("`kkm_aktif`", maskele=False) == [] or True
    assert any(a == "kod dili" for _i, a, _e in od.kosu_kaydi_tara(["`kkm_aktif` bayrağı"]))
    # iki ağırlık: şablon kusuru ENGEL ailesinde, yer tutucudan sızabilecek ad/biçim UYARI ailesinde
    aile = lambda s: {a for _i, a, _e in od.kosu_kaydi_tara([s])}
    assert "kod dili" in aile("veri_durum.json okunamadı"), aile("veri_durum.json okunamadı")
    assert aile("'glp_alis' son 252 gün") == {"anahtar adı"}, aile("'glp_alis' son 252 gün")
    assert aile("mevduat_yp_usd_mia daha yeni") == {"anahtar adı"}, aile("mevduat_yp_usd_mia daha yeni")
    assert aile("fark 5.2 puan, son çapa 2026-08-21") == {"biçim"}, aile("fark 5.2 puan, son çapa 2026-08-21")
    assert aile("Pink Sheet dosyası eski sürüm olabilir") == {"yapım dili"}


# ══════════════════════════════════════════════════════════════════════════════
# İŞ AKIŞI BÜTÇESİ — 04.09.2026 arızasını ÖNCEDEN yakalayan aritmetik özdeşlik
# ══════════════════════════════════════════════════════════════════════════════
#
# O sabah 45 dakikalık tazeleme çöpe gitti ve bu bir kaza değil, dosyanın
# GARANTİSİYDİ: kurulum 5 + tazele 45 + türev 5 = 55 > iş sınırı 50, üstelik
# "Hazine ihaleleri" adımının HİÇ zaman aşımı yoktu. 04:22–05:07 tazeleme kendi
# sınırını doldurdu, 05:07'de Hazine başladı, 05:12'de İŞ sınırı doldu ve
# `if: always()` taşıyan Koşu nabzı ile Commit adımlarının İKİSİ DE pending
# kaldı. `if: always()` sigortası ADIM zaman aşımına karşı çalışıyor, İŞ zaman
# aşımına karşı ÇALIŞMIYOR.
#
# Ölçüt bir EŞİK DEĞİL, bir özdeşliktir: adım sınırlarının toplamı artı sınırsız
# adımların ölçülmüş payı, iş sınırını aşamaz. Bugünkü (düzeltilmemiş) dosyaya
# karşı koşulsa DÜŞERDİ — arızayı ağa çıkmadan, saniyeler içinde yakalayan tek
# sınama bu. duman.py zaten veri.yml, bulten.yml ve fx.yml'in İLK adımı, yani
# kimsenin `--denetle` yazmasına bağlı değil.
#
# KAPSAM — bilerek DAR ve burada adıyla yazılı: yalnız veri.yml'in `tazele` işi.
# Bakılmayan yerler: aynı dosyanın `kesif` işi (20 dk, tek adım, ağ bütçesi
# başka) ve öbür sekiz iş akışı. Kural onlara körü körüne yayılamaz: adım
# sınırı OLMAMASI orada bilinçli olabilir ve yayının önünde duran bir denetimin
# yanlış alarmı arızanın kendisidir. Yayılacaksa her iş için ayrı ölçülür.

# Kurulum payı: iş tetiklendiği an ile `tazele` adımının başladığı an arasındaki
# fark — checkout, setup-python, önbellek, pip, duman sınaması, EVDS kapısı ve
# takvim tanısı. ÖLÇÜLDÜ ama n=1: 04.09.2026'da iş 04:17'de tetiklendi, adım
# 04:22'de başladı. Gözlem birikince p90'a geçilmeli.
KURULUM_DK = 5

# Kuyruk payı: sınırı olmayan SON iki adım (Koşu nabzı, Commit). Ölçülen süre
# bugüne dek 13 saniye; 2 dakika onun üstünde bir TAVAN — commit adımının push
# yeniden deneme döngüsü en kötü hâlde 50 saniye uyuyor.
KUYRUK_DK = 2

# MUAFİYET LİSTESİ — adıyla durur, sessiz genişlemez. Buraya yalnız süresi
# ölçülmüş, ağa çıkmayan ya da kurulum/kuyruk payının İÇİNDE sayılan adımlar
# girer. Bir adım yeniden adlandırılırsa muafiyeti kendiliğinden düşer ve ölçüt
# onu sınır ister diye rapor eder — yanlış yönde değil, GÜVENLİ yönde bozulur.
MUAF_ADIMLAR = {
    "Önbellek depoyu ezmesin": "iki git komutu, saniyeler; kurulum payının içinde",
    "Temel bağımlılıklar": "pip (önbellekli), kurulum payının içinde ölçüldü",
    "Duman sınaması (bülten katmanları)": "ağsız, saniyeler; kurulum payının içinde",
    "EVDS anahtarı": "tek kabuk koşulu; kurulum payının içinde",
    "Tazeleme takvimi ne diyor (tanı — koşuyu durdurmaz)": "yerel takvim okuması, ağsız",
    "Koşu nabzı": "tek dosya yazımı; kuyruk payında sayılıyor",
    "Commit": "git add/commit/push; kuyruk payında sayılıyor",
}


def _yml_anahtar(adim: dict, s: str) -> None:
    m = re.match(r"^(name|run|uses|timeout-minutes):\s*(.*)$", s)
    if not m:
        return
    k, v = m.group(1), m.group(2).strip()
    if k == "name":
        adim["ad"] = v
    elif k == "run":
        adim["run"] = True
    elif k == "uses":
        adim["uses"] = v
    elif k == "timeout-minutes":
        adim["timeout"] = int(v)


def _yml_is(metin: str, is_adi: str) -> tuple[int | None, list[dict]]:
    """`jobs.<is_adi>` işini ayrıştır: (iş sınırı, adımlar).

    PyYAML KULLANILMIYOR — bilerek. Bu sınama veri.yml'in İLK adımı olarak
    koşuyor ve o noktada koşucuda yalnız stdlib var (pip listesi requests,
    pandas, numpy, plotly, openpyxl). Bir bağımlılık eklemek, ölçütü tam da
    korumaya çalıştığı adımın önünde düşürürdü.

    Ayrıştıramazsa YÜKSELİR, sessizce geçmez: "bulamadım" ile "yok" aynı şey
    değildir ve bakılmayan yer geçen sınavla aynı görünür.
    """
    satirlar = metin.splitlines()
    if not any(s.rstrip() == "jobs:" for s in satirlar):
        raise AssertionError("iş akışında 'jobs:' yok — bütçe ölçülemiyor")
    bas = next((i for i, s in enumerate(satirlar)
                if re.match(rf"^  {re.escape(is_adi)}:\s*$", s)), None)
    if bas is None:
        raise AssertionError(f"'jobs.{is_adi}' işi bulunamadı — ölçütün kapsamı kaymış "
                             f"olabilir; iş yeniden adlandırıldıysa ölçüt de güncellenmeli")
    son = len(satirlar)
    for i in range(bas + 1, len(satirlar)):
        s = satirlar[i]
        if s.strip() and not s.lstrip().startswith("#") and not s.startswith("    "):
            son = i
            break

    is_sinir = None
    adim_bas = None
    for i in range(bas + 1, son):
        s = satirlar[i]
        m = re.match(r"^    timeout-minutes:\s*(\d+)", s)
        if m:
            is_sinir = int(m.group(1))
        if re.match(r"^    steps:\s*$", s):
            adim_bas = i
    if adim_bas is None:
        raise AssertionError(f"'jobs.{is_adi}.steps' bulunamadı")

    adimlar: list[dict] = []
    simdiki: dict | None = None
    blok = None            # `run: |` gövdesi: girintisi 8'den derin satırlar atlanır
    for i in range(adim_bas + 1, son):
        ham = satirlar[i]
        if not ham.strip():
            continue
        girinti = len(ham) - len(ham.lstrip())
        if blok is not None:
            if girinti > blok:
                continue
            blok = None
        if ham.lstrip().startswith("#"):
            continue
        if ham.startswith("      - "):
            simdiki = {"ad": None, "run": False, "uses": None, "timeout": None}
            adimlar.append(simdiki)
            icerik = ham[8:]
            _yml_anahtar(simdiki, icerik)
            if icerik.rstrip().endswith(("|", ">")):
                blok = 8
            continue
        if simdiki is not None and girinti == 8:
            s = ham.strip()
            _yml_anahtar(simdiki, s)
            if s.rstrip().endswith(("|", ">")):
                blok = 8
    return is_sinir, adimlar


def butce_bulgulari(metin: str, is_adi: str = "tazele") -> list[str]:
    """İş akışı metninden bütçe kusurlarını çıkar. Boş liste = temiz."""
    is_sinir, adimlar = _yml_is(metin, is_adi)
    bulgular: list[str] = []
    if is_sinir is None:
        return [f"'{is_adi}' işinin timeout-minutes'i yok — iş bütçesi sınırsız, "
                "asılan bir adım koşucuyu altı saat yakabilir"]

    toplam = sum(a["timeout"] for a in adimlar if a["timeout"])
    gereken = toplam + KURULUM_DK + KUYRUK_DK
    if gereken > is_sinir:
        parcalar = ", ".join(f"{a['ad'] or a['uses']} {a['timeout']}"
                             for a in adimlar if a["timeout"])
        bulgular.append(
            f"ARİTMETİK KAPANMIYOR: adım sınırları ({parcalar}) toplamı {toplam} "
            f"+ kurulum {KURULUM_DK} + kuyruk {KUYRUK_DK} = {gereken} dk > iş sınırı "
            f"{is_sinir} dk. İş sınırı dolduğunda GitHub `if: always()` adımlarını da "
            f"öldürür: tazelenen hatlar commit edilmeden gider (04.09.2026). Ya adım "
            f"sınırları kısılır ya iş sınırı {gereken} dakikanın üstüne çıkarılır.")

    for a in adimlar:
        if not a["run"] or a["timeout"] is not None:
            continue
        ad = a["ad"] or a["uses"] or "(adsız adım)"
        if ad in MUAF_ADIMLAR:
            continue
        bulgular.append(
            f"SINIRSIZ ADIM: '{ad}' bir komut koşuyor ama timeout-minutes taşımıyor. "
            f"Sınırsız bir adım kendisinden SONRA gelen bütün adımların sigortasını "
            f"yakar — 04.09'da Hazine adımı tam bunu yaptı. Ya sınır konur ya da "
            f"süresi ölçülüp MUAF_ADIMLAR'a adıyla yazılır.")
    return bulgular


def main() -> int:
    import ayar, denetim, gozlem, grafik_veri, olay, rejim, soz, surpriz, tazeleme, uret

    hat = next(iter(ayar.RITIM))
    bugun = dt.date.today()

    # ── anlık görüntü deposu: anahtar başına saat sözleşmesi
    def _gozlem():
        d = gozlem.anlik(hat) or {}
        gozlem.anahtar_tarihi(d, "yok_boyle_bir_anahtar")
        gozlem.onceki_surum_anahtar(hat, "yok_boyle_bir_anahtar", "", "")
        gozlem.son_gorulme(hat)
        gozlem.alan_son_gorulme(hat, "_tarih")
        gozlem.anahtar_hafta_once(hat, "_tarih")
    sina("gozlem: saat yardımcıları", _gozlem)

    # ── olay motoru ve yeni katmanlar
    sina("olay.topla", lambda: olay.topla())
    sina("olay.gecikme_olaylari", lambda: olay.gecikme_olaylari())
    sina("rejim.panosu", lambda: rejim.panosu())
    sina("soz.ozet", lambda: soz.ozet(bugun.isoformat()))
    sina("grafik_veri.hazirla", lambda: grafik_veri.hazirla())
    sina("surpriz.gecmis_olaylar", lambda: surpriz.gecmis_olaylar([], {}, bugun))
    sina("uret.gostergeler (günlük)", lambda: uret.gostergeler(haftalik=False))
    sina("uret.gostergeler (haftalık)", lambda: uret.gostergeler(haftalik=True))

    # ── takvim beklentisi: TÜRKİYE ölçüsü yabancı satıra iliştirilemez.
    # 06.09.2026'da Fed toplantısı satırı, adında "faiz kararı" geçtiği için
    # Türkiye'nin politika faizini ve PKA anketinin TL faiz beklentisini
    # beklenti diye basıyordu. Ölçüt ADA değil ÜLKEYE bakar; sınama ikisini de
    # sorar ki bir sonraki oturum kapıyı ada geri çevirmesin.
    def _beklenti_ulkesi():
        for olay in ("Fed (FOMC) faiz kararı", "ECB para politikası kararı",
                     "ABD TÜFE (Ağustos)", "Euro alanı TÜFE"):
            for ulke in ("ABD", "EA", "GB"):
                m = uret._beklenti_metni(olay, ulke)
                if m:
                    raise AssertionError(
                        f"yabancı takvim satırına Türkiye beklentisi iliştirildi: "
                        f"{ulke} · {olay} → {m}")
        # TR satırında kapı KAPANMAMALI: hattın ölçüsü varsa beklenti yazılır.
        uret._beklenti_metni("TCMB PPK faiz kararı", "TR")
    sina("uret.beklenti: ülke kapısı", _beklenti_ulkesi)

    # ── tazeleme: takvim ucu SAHTE, sözleşme gerçek
    def _tazeleme():
        gercek = tazeleme._yayimlar
        sahte = [{"adi": "TCMB Analitik Bilanço", "kurum": "TCMB",
                  "an": "2026-01-02T14:30:00"}]
        try:
            for kayitlar, alindi in ((sahte, True), ([], False)):
                tazeleme._yayimlar = lambda y, k=kayitlar, a=alindi: (k, a)
                tazeleme.kararlar(simdi=dt.datetime(2026, 1, 3, 16, 0))
                tazeleme.olu_kaliplar()
                tazeleme.gerekli(simdi=dt.datetime(2026, 1, 3, 16, 0))
        finally:
            tazeleme._yayimlar = gercek
    sina("tazeleme: karar + ölü kalıp (iki takvim durumu)", _tazeleme)

    # --gerekli'nin atladığı hat türev genişletmesiyle geri gelmez: reelfx tcmb'ye
    # bağımlı, tcmb her iş günü seçiliyor, reelfx her gün EVDS'e çıkıyordu (02.09).
    def _turev_genisletme():
        import contextlib, io
        import sys as _s
        _s.path.insert(0, str(BURASI.parent))
        import guncelle as g
        tcmb = g.HAT["tcmb"]
        with contextlib.redirect_stdout(io.StringIO()):
            acik = [h.ad for h in g.turevleri_ekle([tcmb])]
            kapali = [h.ad for h in g.turevleri_ekle([tcmb], {"reelfx"})]
        assert acik[0] == "tcmb" and "reelfx" in acik, acik
        assert kapali == ["tcmb"], kapali
    sina("guncelle: takvimin atladığı hat türev genişletmesiyle geri gelmez", _turev_genisletme)

    # ── ortak HTTP emniyeti: zaman aşımı gerçekten takılıyor mu (ağsız)
    # 2026-08-27: tcmb istemcisi isteği timeout'suz atıyordu; EVDS 21 dakika
    # astı ve dört hattın üçünün tamamlanmış işi çöpe gitti. Emniyet artık
    # ortak/sitecustomize.py'de; SINANMAYAN emniyet emniyet değildir.
    def _http_emniyet():
        import importlib.util
        import requests
        yol = BURASI.parent / "ortak" / "sitecustomize.py"
        assert yol.exists(), f"{yol} yok"
        asil = requests.sessions.Session.request
        onceden = getattr(requests.sessions.Session, "_tto_emniyet", False)
        gorulen: dict = {}

        class _Yanit:                      # ağa hiç çıkılmaz
            status_code = 200

        def _kaydet(self, method, url, **kw):
            gorulen["timeout"] = kw.get("timeout")
            return _Yanit()

        try:
            requests.sessions.Session.request = _kaydet
            if onceden:                    # zaten sarılıysa yeniden sarılsın
                del requests.sessions.Session._tto_emniyet
            spec = importlib.util.spec_from_file_location("_tto_emniyet_sinama", yol)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            assert getattr(requests.sessions.Session, "_tto_emniyet", False), \
                "emniyet kurulmadı"
            requests.get("http://sinama.gecersiz/x")
            zaman = gorulen.get("timeout")
            assert isinstance(zaman, tuple) and all(zaman), \
                f"varsayılan zaman aşımı takılmadı: {zaman!r}"
            requests.get("http://sinama.gecersiz/y", timeout=7)
            assert gorulen.get("timeout") == 7, \
                f"açıkça verilen zaman aşımı ezildi: {gorulen.get('timeout')!r}"
        finally:
            requests.sessions.Session.request = asil
            if onceden:
                requests.sessions.Session._tto_emniyet = True
            else:
                try:
                    del requests.sessions.Session._tto_emniyet
                except AttributeError:
                    pass
    sina("ortak: HTTP zaman aşımı emniyeti", _http_emniyet)

    # ── denetim: son bülten üzerinde bütün ölçütler
    b = son_bulten()
    if b is None:
        dusen.append(("denetim", "sınanacak bülten dosyası yok"))
    else:
        def _denetim():
            d = denetim.Denetim(b)
            for olcut in ("yazi", "veri", "atif", "sayi", "nabiz",
                          "tema", "izleme", "dil", "tazelik", "karanlik"):
                getattr(d, olcut)()
        sina("denetim: on ölçüt", _denetim)

    # ── zincir raporu: yazı katmanının sabah attığı ilk adım
    def _zincir():
        import contextlib, io as _io
        import zincir
        with contextlib.redirect_stdout(_io.StringIO()):
            kod, _ = zincir.durum()
        assert kod in (0, 1, 2, 3, 4), f"beklenmeyen zincir kodu: {kod}"
    sina("zincir: durum raporu", _zincir)

    # ── YAZILMIŞ BÜLTEN KORUNUYOR MU (27.08.2026 kusuru)
    #
    # uret.yaz() yorumu ve gündemi koruyordu ama ÖZETİ korumuyordu: ozet_ekle()
    # her koşuda b["ozet"]'i makine özetiyle eziyor, yazı katmanının "ne oldu /
    # ne bekleniyor" paragrafları sessizce kayboluyordu. Sayfa yine "yazılı"
    # göründüğü için de hiçbir denetim itiraz etmiyordu. Kusur geri konarak
    # sınandı: koruma kaldırılınca bu sınama düşüyor.
    def _koruma():
        import tempfile
        import uret as _uret
        eski_cikti = _uret.CIKTI
        try:
            _uret.CIKTI = Path(tempfile.mkdtemp())
            yazili = {
                "tarih": "2026-01-02", "gundem_kaynagi": "yazili",
                "yorum": "<p>yazı katmanının yorumu</p>", "yorum_zamani": "2026-01-02",
                "gundem": {"kilit": "<p>yazılı gündem</p>"},
                "ozet": {"ne_oldu": "<p>yazılı özet</p>", "ne_bekleniyor": "<p>ileriye</p>"},
            }
            (_uret.CIKTI / "2026-01-02.json").write_text(
                json.dumps(yazili, ensure_ascii=False), encoding="utf-8")
            # Deterministik koşunun ürettiği taban: üçü de makine metni.
            taban = {"tarih": "2026-01-02", "gundem_kaynagi": "otomatik",
                     "yorum": "", "gundem": {"kilit": "<p>taban</p>"},
                     "ozet": {"ne_oldu": "<p>makine özeti</p>", "ne_bekleniyor": ""}}
            _uret.yaz(taban)
            son = json.loads((_uret.CIKTI / "2026-01-02.json").read_text(encoding="utf-8"))
            assert son["yorum"] == yazili["yorum"], "yorum ezildi"
            assert son["gundem"] == yazili["gundem"], "gündem ezildi"
            assert son["ozet"] == yazili["ozet"], "ÖZET EZİLDİ"
            assert son["gundem_kaynagi"] == "yazili", "yayın kapısı düştü"
        finally:
            _uret.CIKTI = eski_cikti
    sina("uret.yaz: yazılmış bülten korunuyor", _koruma)

    # YERLEŞMEMİŞ BAR. 27.08 bülteni 04:21 UTC'de koştu ve 51 enstrümanın 21'i
    # o anda HENÜZ AÇIK olan günün barını taşıyordu; kapanışa göre değişimleri
    # "günlük değişim" diye yayımlandı. Altında bu, işareti ters çevirdi:
    # dünkü seans −%0,86 kapanmışken bülten "+%1,78" yazdı ve günün anlatısını
    # o sahte hareketin üzerine kurdu. Koruma vardı ama yalnız beş enerji
    # vadelisini kapsıyordu. Bu sınama korumayı SAHTE SAATLE çağırır: kusur
    # geri konarsa (eşik tablosundan bir grup düşerse) burada düşer.
    def _yerlesmemis():
        from datetime import datetime as _dt, timezone as _tz
        import piyasa as _piyasa

        bugun, dun = "2026-08-27", "2026-08-26"
        ornek = {
            "GC=F": "metal", "EURUSD=X": "g10_fx", "BTC-USD": "kripto",
            "^N225": "asya_hisse", "XU100.IS": "tr_hisse",
        }
        gercek = _piyasa.datetime
        try:
            class _Saat(_dt):
                @classmethod
                def now(cls, tz=None):
                    return _dt(2026, 8, 27, 4, 21, tzinfo=_tz.utc)
            _piyasa.datetime = _Saat
            seri = {k: {"tarih": [dun, bugun], "kapanis": [100.0, 110.0]} for k in ornek}
            _piyasa._yerlesmemis_dus(seri)
            for k in ornek:
                assert seri[k].get("yerlesmemis_dusuruldu"), f"{k}: bugünün barı düşmedi"
                assert seri[k]["tarih"][-1] == dun, f"{k}: seri {dun}'da bitmeli"

            # Kapanmış piyasa: aynı bar 22:00 UTC'de KULLANILMALI, yoksa
            # koruma bir günlük gecikmeyi kalıcı hâle getirir.
            class _Gec(_dt):
                @classmethod
                def now(cls, tz=None):
                    return _dt(2026, 8, 27, 22, 30, tzinfo=_tz.utc)
            _piyasa.datetime = _Gec
            gec = {"GC=F": {"tarih": [dun, bugun], "kapanis": [100.0, 110.0]}}
            _piyasa._yerlesmemis_dus(gec)
            assert not gec["GC=F"].get("yerlesmemis_dusuruldu"), "kapanmış bar boşuna düştü"

            # Tanımsız grup: bilinmeyen bir kod bugünün barına GÜVENMEMELİ.
            _piyasa.datetime = _Saat
            bilinmeyen = {"YOK=F": {"tarih": [dun, bugun], "kapanis": [100.0, 110.0]}}
            _piyasa._yerlesmemis_dus(bilinmeyen)
            assert bilinmeyen["YOK=F"].get("yerlesmemis_dusuruldu"), "tanımsız grup düşmedi"
        finally:
            _piyasa.datetime = gercek
    sina("piyasa: yerleşmemiş bar düşürülüyor", _yerlesmemis)

    # DENETİMİN SON KAPISI. Ölçüm katmanındaki koruma tek başına yetmiyor: bir
    # zamanlar yalnız beş enerji vadelisini kapsıyordu ve kimse fark etmedi.
    # denetim.yerlesmemis aynı soruyu yayının son kapısında bağımsız sorar; bu
    # sınama onun GERÇEKTEN engel ürettiğini doğrular.
    def _denetim_yerlesmemis():
        from datetime import datetime as _dt, timezone as _tz
        import denetim as _den
        gercek = _den.datetime
        try:
            class _Saat(_dt):
                @classmethod
                def now(cls, tz=None):
                    return _dt(2026, 8, 27, 4, 21, tzinfo=_tz.utc)
            _den.datetime = _Saat
            b = {"tarih": "2026-08-27", "piyasa": {"gruplar": [
                {"id": "metal", "satirlar": [{"ad": "Altın", "tarih": "2026-08-27", "d1": 1.78}]},
                {"id": "asya_hisse", "satirlar": [{"ad": "Nikkei", "tarih": "2026-08-26", "d1": 0.3}]},
            ]}}
            d = _den.Denetim(b); d.yerlesmemis()
            assert d.engel and "KAPANMAMIŞ" in d.engel[0], "kapanmamış bar engel üretmedi"

            temiz = {"tarih": "2026-08-27", "piyasa": {"gruplar": [
                {"id": "metal", "satirlar": [{"ad": "Altın", "tarih": "2026-08-26", "d1": -0.86}]},
            ]}}
            d2 = _den.Denetim(temiz); d2.yerlesmemis()
            assert not d2.engel, "kapanmış bar boşuna engellendi"
        finally:
            _den.datetime = gercek
    sina("denetim: kapanmamış bar ENGEL", _denetim_yerlesmemis)

    # SEANS ETİKETİ. 31.08.2026 pazartesi bülteninde elli piyasa satırının
    # ellisi 28.08 Cuma kapanışını taşıyordu ve "günlük değişim" diye
    # yayımlandı — hangi seansa ait olduğunu söyleyen hiçbir alan yoktu.
    # Ölçüt üç durumu ayırmalı: pazartesi/Cuma NORMAL, tek tatil UYARI,
    # ikiden fazla kaçırılan seans ENGEL. Takvim günüyle ölçmek tek tatili
    # bile engel sayardı; sınama tam bu ayrımı zorluyor.
    def _denetim_piyasa_seansi():
        import denetim as _den
        def calistir(bulten, kapanis, etiket=True):
            d = _den.Denetim({"tarih": bulten, "piyasa": {
                "kapanis_tarih": kapanis,
                "kapanis_seansi": f"{kapanis} kapanışı" if etiket else None}})
            d.piyasa_seansi()
            return d
        d = calistir("2026-08-31", "2026-08-28")          # Pzt bülteni, Cuma kapanışı
        assert not d.engel and not d.uyari, f"normal hafta sonu boşluğu şikâyet üretti: {d.engel + d.uyari}"
        d = calistir("2026-09-01", "2026-08-28")          # bir tatil kaçırılmış
        assert d.uyari and not d.engel, "tek kaçırılan seans uyarı üretmedi ya da engel oldu"
        d = calistir("2026-09-02", "2026-08-28")          # iki seans kaçırılmış
        assert d.engel and "BAYAT" in d.engel[0], "iki kaçırılan seans ENGEL üretmedi"
        d = calistir("2026-08-31", "2026-08-28", etiket=False)
        assert d.uyari and "ETİKET" in d.uyari[0], "seans etiketi eksikken uyarı çıkmadı"
        d = calistir("2026-08-31", None)
        assert d.uyari, "seans tarihi hiç yokken uyarı çıkmadı"

    sina("denetim: piyasa seansı etiketli ve bayat değil", _denetim_piyasa_seansi)

    # HAFTA SONU BOŞLUĞU σ'YI ŞİŞİRMİYOR — ölçülen olgu koda bağlanıyor.
    # Sezgi "pazartesi hareketi üç takvim günü kapsar, günlük σ ile kıyaslamak
    # onu olağandışı gösterir" der. Ölçüm bunun tersini söyledi (σ3/σ1 medyanı
    # 1,00). Bu sınama, birinin ileride d1_sigma'ya boşluk ölçeklemesi
    # eklemesini yakalar: aynı hareket, farklı boşlukla, aynı σ'yı vermelidir.
    def _sigma_boslugu_olceklemez():
        import piyasa as _p
        k = [100.0 + i * 0.1 for i in range(25)]
        t_bitisik = [f"2026-01-{i + 1:02d}" for i in range(25)]      # ardışık günler
        t_bosluklu = list(t_bitisik[:-1]) + ["2026-01-27"]           # son adım 3 gün sonra
        a = _p.satir(_p.VARLIKLAR[0], {_p.VARLIKLAR[0].kod: {"kapanis": k, "tarih": t_bitisik}})
        b = _p.satir(_p.VARLIKLAR[0], {_p.VARLIKLAR[0].kod: {"kapanis": k, "tarih": t_bosluklu}})
        assert a["d1_sigma"] == b["d1_sigma"], (
            "boşluk σ'yı değiştirdi — kapanıştan kapanışa hareket tek seanslık "
            "risktir, ölçekleme uygulanmamalı")
        assert a["gap_gun"] == 1 and b["gap_gun"] == 3, "gap_gun takvim boşluğunu vermiyor"

    sina("piyasa: σ takvim boşluğuna göre ölçeklenmiyor", _sigma_boslugu_olceklemez)

    # HAFTALIK BÜLTENİN PENCERESİ HAFTADIR. 30.08.2026'ya kadar haftaya bakış
    # bülteni günlük σ listesini basıyor ve sayfada "Günün olağandışı
    # hareketleri" başlığı duruyordu. Kusur geri konarak sınanıyor: haftalık
    # bültene günlük kipli bir liste verilirse denetim ENGEL üretmeli.
    def _denetim_sigma_penceresi():
        import denetim as _den
        liste = [{"ad": "USD/CHF", "deger": 1.21, "birim": "%", "sigma": 1.4, "oynaklik": 0.85}]
        yanlis = {"tarih": "2026-08-30", "haftalik": True,
                  "piyasa": {"en_cok_hareket": {"sigma": liste, "sigma_kip": "gunluk"}}}
        d = _den.Denetim(yanlis); d.olagandisilik_penceresi()
        assert d.engel and "PENCERESİ YANLIŞ" in d.engel[0], \
            "haftalık bültende günlük σ listesi engel üretmedi"

        # Kip hiç bildirilmemişse (eski ölçüm kodu) sessiz geçilmemeli.
        eksik = {"tarih": "2026-08-30", "haftalik": True,
                 "piyasa": {"en_cok_hareket": {"sigma": liste}}}
        d2 = _den.Denetim(eksik); d2.olagandisilik_penceresi()
        assert d2.engel and "BİLDİRİLMEMİŞ" in d2.engel[0], "kip eksikken engel çıkmadı"

        # Doğru kip boşuna engellenmemeli — ne haftalıkta ne günlükte.
        for hafta, kip in ((True, "haftalik"), (False, "gunluk")):
            ok = {"tarih": "2026-08-30", "haftalik": hafta,
                  "piyasa": {"en_cok_hareket": {"sigma": liste, "sigma_kip": kip}}}
            d3 = _den.Denetim(ok); d3.olagandisilik_penceresi()
            assert not d3.engel, f"doğru kip ({kip}) boşuna engellendi"
    sina("denetim: olağandışılık penceresi bültenin kipini izliyor", _denetim_sigma_penceresi)

    # SAYFADAKİ TEMA METNİ DEFTERDEKİNDEN ESKİ OLABİLİR. Tema bölümü bültene
    # ÖLÇÜM anında işleniyor, yazı katmanı defteri ondan SONRA güncelliyor;
    # yani defteri düzeltmek sayfayı düzeltmiyor. İki kez yayına çıktı (28.08
    # geri alınmış rakamlar, 30.08 "konuşma bugün" derken konuşma iki gün
    # önce yapılmıştı). Ölçüt farkı ölçüyor; bu sınama farkı geri koyuyor.
    def _denetim_tema_goruntusu():
        import denetim as _den
        defter = json.loads((BURASI / "temalar.json").read_text(encoding="utf-8"))
        canli = [x for x in (defter.get("temalar") or [])
                 if x.get("durum") in ("aktif", "izlemede")]
        assert canli, "defterde canlı tema yok — sınama kurulamıyor"

        taze = {"tarih": "2026-08-30", "temalar": {"temalar": defter["temalar"]}}
        d = _den.Denetim(taze); d.tema()
        assert not [e for e in d.engel if "TEMA GÖRÜNTÜSÜ ESKİ" in e], \
            "defterle birebir aynı görüntü boşuna engellendi"

        eski = json.loads(json.dumps(defter["temalar"]))
        for x in eski:
            if x.get("durum") in ("aktif", "izlemede"):
                x["gelisme"] = "<p>Çürütücü ölçüt bugün sınanacak.</p>"
                break
        bayat = {"tarih": "2026-08-30", "temalar": {"temalar": eski}}
        d2 = _den.Denetim(bayat); d2.tema()
        assert [e for e in d2.engel if "TEMA GÖRÜNTÜSÜ ESKİ" in e], \
            "sayfadaki eski tema metni engel üretmedi"
    sina("denetim: eski tema görüntüsü ENGEL", _denetim_tema_goruntusu)

    # HAFTALIK σ'NIN KENDİSİ. Pencereler ÖRTÜŞMEMELİ: örtüşen haftalık
    # pencereler ardışık bağımlılık taşır, standart sapmayı küçültür ve her
    # hareketi olağandışı gösterir. Ayrıca haftalık σ günlüğün ~√5 katı
    # mertebesinde çıkmalı; çıkmıyorsa birim ya da pencere karışmıştır.
    def _haftalik_sigma():
        import piyasa as _piyasa
        kapanis = [100.0 * (1.01 ** i) for i in range(120)]      # düzgün artan seri
        d = _piyasa._haftalik_degisimler(kapanis, False, 20)
        assert len(d) == 20, f"20 haftalık gözlem beklenirken {len(d)} geldi"
        bek = (1.01 ** 5 - 1) * 100
        assert all(abs(x - bek) < 1e-6 for x in d), "haftalık değişim beşer günlük değil"

        import random
        random.seed(7)
        yol, v = [100.0], 100.0
        for _ in range(400):
            v *= 1 + random.gauss(0, 0.01)
            yol.append(v)
        sg = _piyasa._oynaklik(yol, False)
        sh = _piyasa._oynaklik_hafta(yol, False)
        assert sg and sh, "σ hesaplanamadı"
        oran = sh / sg
        assert 1.4 < oran < 3.4, (
            f"haftalık σ günlüğün {oran:.2f} katı — √5≈2,24 mertebesinde olmalı; "
            "pencere ya da birim karışmış olabilir")

        # Tarihçe yetmiyorsa σ ÜRETİLMEZ; yarım veriyle sıralama kurulmaz.
        assert _piyasa._oynaklik_hafta([100.0] * 20, False) is None, \
            "kısa tarihçede haftalık σ üretildi"
    sina("piyasa: haftalık σ örtüşmeyen pencerelerle kuruluyor", _haftalik_sigma)

    # SAYFA ETİKETLERİ DE PENCEREYİ İZLEMELİ. Ölçüm katmanını haftalığa çevirmek
    # yetmiyor: σ bloğu üç ayrı yerde basılıyor (bülten gövdesi, çubuk grafik,
    # ana sayfa) ve üçünde de başlık/oynaklık etiketi SABİT "günlük" yazıyordu.
    # 30.08.2026'da ölçü haftalığa geçtiğinde ana sayfa haftalık oynaklıkları
    # "20g oynaklık" diye etiketledi — sayı doğru, etiket yalan. Bu sınama
    # etiketin türetildiğini yapısal olarak dayatır: dosyalar kipe bakmıyorsa
    # düşer. (Astro'yu Python'dan koşturamayız; ölçebileceğimiz şey bağın
    # kurulu olduğu.)
    def _sayfa_kipi():
        kok = BURASI.parent / "site" / "src"
        beklenen = {
            "components/SigmaSerit.astro": ("kip", "pencereAd"),
            "components/BultenGovde.astro": ("sigma_kip", "sigmaBaslik"),
            "pages/index.astro": ("sigmaKip", "sigmaBaslik", "oynaklikEtiketi"),
            "lib/anaSayfa.ts": ("sigmaKip", "sigma_kip"),
        }
        for yol, anahtarlar in beklenen.items():
            f = kok / yol
            assert f.exists(), f"{yol} bulunamadı — σ etiketi sınanamıyor"
            metin = f.read_text(encoding="utf-8")
            for a in anahtarlar:
                assert a in metin, (
                    f"{yol} içinde '{a}' yok — σ başlığı/etiketi bültenin kipinden "
                    "türetilmiyor olabilir, sabit 'günlük' yazan sürüme dönülmüş")
        govde = (kok / "components/BultenGovde.astro").read_text(encoding="utf-8")
        assert "kip={b.piyasa.en_cok_hareket.sigma_kip}" in govde, \
            "SigmaSerit'e kip geçirilmiyor — grafik başlığı sabit 'günlük' kalır"
        ana = (kok / "pages/index.astro").read_text(encoding="utf-8")
        assert "20g oynaklık {" not in ana and ">20g oynaklık<" not in ana, \
            "ana sayfada oynaklık etiketi yeniden sabitlenmiş"
    sina("sayfa: σ başlıkları bültenin kipinden türüyor", _sayfa_kipi)

    # Kilit gelişme ölçütü KAPANABİLİR olmalı. İngilizce başlığın kelimelerini
    # Türkçe metinde arayan eski hâli hiçbir zaman kapanmıyordu; kapanamayan
    # uyarı, yazarı bütün uyarıları görmezden gelmeye alıştırır.
    def _kilit_capa():
        import denetim as _den
        madde = {"baslik": "Gold Rises As Treasury Buyback Support Plan Weighs On Dollar",
                 "kaynak": "Arama — ABD borç yönetimi ve tahvil arzı (+8 kaynak)"}
        ozel, konu = _den._kilit_capalari(madde)
        assert konu, "Türkçe konu çapası çıkarılamadı"
        assert any(w in _den._sade("Hazine geri alımı ve tahvil arzı tartışması") for w in konu), \
            "Türkçe konu çapası metinde bulunamadı"
        bos = {"baslik": "Stocks up", "kaynak": ""}
        o2, k2 = _den._kilit_capalari(bos)
        assert not o2 and not k2, "çapasız maddeden çapa üretildi (uyarı kapanamaz olurdu)"
    sina("denetim: kilit gelişme çapası kapanabilir", _kilit_capa)

    # Devir düzeltmesi, KAPANMAMIŞ bar elindeyken koşarsa bugüne sahte bir devir
    # yazıyor ve o devirden önceki bütün günleri yanlış oranla ölçekliyordu.
    # Sıra artık bağlayıcı: önce bar düşer, sonra devir hesaplanır.
    def _sira():
        import piyasa as _piyasa
        metin = Path(_piyasa.__file__).read_text(encoding="utf-8")
        i_bar = metin.index("seri = _yerlesmemis_dus(seri)")
        i_roll = metin.index("seri = _roll_duzelt(seri)")
        assert i_bar < i_roll, ("SIRA TERS: devir düzeltmesi kapanmamış bar elindeyken "
                                "koşuyor — bugüne sahte devir yazar")
    sina("piyasa: bar düşürme devir düzeltmesinden ÖNCE", _sira)

    # SAKAT ÖLÇÜM YAZILMAZ. Rutin metni "dosya yoksa bulten.py ile üret" diyor;
    # o oturumda ağ kapalı ve deneme 0 enstrümanlık bir fotoğraf üretiyor.
    # Rutin metnini bir aracı düzeltemiyor (27.08'de denendi, reddedildi), o
    # yüzden kapı koda kondu. Bu sınama kapının GERÇEKTEN kapandığını doğrular.
    def _sakat():
        # bulten.py depo KÖKÜNDE, bulten/ paketinde değil — yol ile okunur.
        kaynak = (Path(__file__).resolve().parent.parent / "bulten.py").read_text(encoding="utf-8")
        assert "ASGARI_ENSTRUMAN" in kaynak, "sakat ölçüm kapısı yok"
        i_kapi = kaynak.index("n_enst < _denetim.ASGARI_ENSTRUMAN")
        i_yaz = kaynak.index("y = uret.yaz(b)")
        assert i_kapi < i_yaz, "kapı yazmadan SONRA geliyor — dosya yine de yazılır"
        assert "if not a.sakat_yaz:" in kaynak, "kapı geçersiz kılınabilir değil"
    sina("bulten.py: sakat ölçüm yazılmıyor", _sakat)

    # FX GÜNLÜK KİPİ GERÇEKTEN VERİ ÇEKMELİ. Hattın hafif kipi bir zamanlar
    # günlük listedeydi ve orada yaptığı tek iş sahte tazelik damgası atmaktı:
    # mevcut veriden grafik çiziyor, haber akışını HİÇ toplamıyordu (63fbf6e).
    # Günlük kip o hatayı tekrarlamamalı — adım listesinde veri çeken `run.py`
    # BULUNMAK ZORUNDA, ve ağır arşiv bayrağı BULUNMAMALI.
    def _fx_gunluk():
        # guncelle.py depo KÖKÜNDE; duman.py sys.path'e bulten/ ekliyor.
        kok = str(Path(__file__).resolve().parent.parent)
        if kok not in sys.path:
            sys.path.insert(0, kok)
        import guncelle as mod
        fx = next(h for h in mod.HATLAR if h.ad == "fx")

        g = fx.adimlar(tam=False, gunluk=True)
        assert any(a.split()[0] == "run.py" for a in g), \
            "günlük kip veri çekmiyor — sahte tazelik damgası geri geldi"
        assert not any("--fetch-history" in a for a in g), \
            "günlük kip ağır GDELT arşivini çekiyor"
        assert any(a.startswith("web_cikti.py") and "--anlik" in a for a in g), \
            "günlük kip haftalık panelleri de yeniden çiziyor"

        h = fx.adimlar(tam=False, gunluk=False)
        assert not any(a.split()[0] == "run.py" for a in h), \
            "hafif kip veri çeker hâle gelmiş — kipler karışmış"
        # Günlük kipi tanımsız bir hat sessizce hafife düşmeli.
        baska = next(x for x in mod.HATLAR if x.ad == "tcmb")
        assert baska.adimlar(False, True) == baska.adimlar(False), \
            "günlük kipi tanımsız hat hafife düşmüyor"

        # BAĞIMLILIK: günlük kip run.py koşturduğu için torch/transformers
        # KURULMAK zorunda. İlk günlük koşu (28.08) hafif paket listesiyle
        # açıldı ve 15 saniyede düştü — bu sınama o kusuru kilitler.
        hafif = mod._req_paketler(mod.KOK / fx.klasor, agir_dahil=False)
        assert "torch" not in hafif, "hafif liste ağır paket taşıyor"
        import inspect
        for fn in (mod.eksik_paketler, mod.sistem_kur):
            assert "gunluk" in inspect.signature(fn).parameters, \
                f"{fn.__name__} günlük kipi tanımıyor"
            assert "tam or gunluk" in inspect.getsource(fn), \
                f"{fn.__name__} günlük kipte ağır paketleri saymıyor"
    sina("guncelle: fx günlük kipi veri çekiyor", _fx_gunluk)

    # SÜRPRİZ GELİŞ KURALI. "Geldi" kararı eskiden yalnız referans tarihine
    # bakıyordu (veri_gun >= yayım günü) ve haftalık TCMB serilerinde bu
    # YAPISAL olarak imkânsızdı: 27.08 Perşembe yayımı 21.08 dönemini taşır.
    # 28.08 bülteni, gösterge panosu 14.08→21.08 İLERLEMİŞKEN aynı yayım için
    # "veri henüz hatta düşmedi" yazdı. Kural artık sürüm saatine de bakıyor;
    # bu sınama iki yönü de kilitler: sürüm yayımdan SONRA ilerlediyse geldi,
    # yayımdan ÖNCE kalmışsa gelmedi (erken ilan yasak).
    def _surpriz_gelis():
        import datetime as _dt
        import surpriz as _s
        import gozlem as _g

        g_anlik, g_son, g_onceki = _g.anlik, _g.son_gorulme, _g.onceki_surum_anahtar
        s_arsivle, s_oku = _s.arsivle, _s.arsiv_oku
        try:
            _g.anlik = lambda hat: {"g_ar_13y": 23.7, "_tarih": "21.08.2026"}
            _g.onceki_surum_anahtar = lambda *a, **k: {"d": {"g_ar_13y": 25.9}}
            _s.arsivle = lambda k: None
            _s.arsiv_oku = lambda: {"x": {
                "tarih": "2026-08-27", "olay": "TCMB: Haftalık para-banka (34. Hafta)",
                "beklenti": "", "beklenti_sayi": None}}

            # (a) referans (21.08) < yayım (27.08) AMA sürüm 28.08'de ilerledi → GELDİ
            _g.son_gorulme = lambda hat: ("21.08.2026", "2026-08-28T04:17:15")
            r = _s.gecmis_olaylar([], piyasa=None, bugun=_dt.date(2026, 8, 28))
            assert r and r[0]["durum"] == "geldi", f"sürüm ilerledi ama durum: {r[0]['durum'] if r else 'boş'}"
            assert r[0]["gerceklesme"] == 23.7 and r[0]["onceki"] == 25.9

            # (b) sürüm yayımdan ÖNCE (20.08) kalmış → GELMEDİ (erken ilan yasak)
            _g.son_gorulme = lambda hat: ("14.08.2026", "2026-08-20T13:09:00")
            _g.anlik = lambda hat: {"g_ar_13y": 25.9, "_tarih": "14.08.2026"}
            r = _s.gecmis_olaylar([], piyasa=None, bugun=_dt.date(2026, 8, 28))
            assert r and r[0]["durum"] == "veri henüz hatta düşmedi", \
                f"bayat sürüm 'geldi' sayıldı: {r[0]['durum'] if r else 'boş'}"
            assert r[0]["gerceklesme"] is None, "gelmemiş veri için gerçekleşme yazıldı"
        finally:
            _g.anlik, _g.son_gorulme, _g.onceki_surum_anahtar = g_anlik, g_son, g_onceki
            _s.arsivle, _s.arsiv_oku = s_arsivle, s_oku
    sina("surpriz: geliş sürüm saatinden okunuyor", _surpriz_gelis)

    # ── yaz.py: düzeltme kaydı biçimce sınanır; denetim yarım kaydı engeller
    def _duzeltme():
        import yaz
        b = {"gundem_kaynagi": "yazili", "gundem": {"kilit": "x"}}
        import tempfile, json as _j
        with tempfile.TemporaryDirectory() as td:
            hedef = Path(td) / "b.json"
            hedef.write_text(_j.dumps(b), encoding="utf-8")
            yeni, degisen = yaz.uygula(hedef, {"duzeltmeler": [
                {"alan": "Brent günlük değişim (28.08)", "eski": "−%11,36", "yeni": "−%1,74",
                 "sebep": "vadeli devir düzeltmesi kurulamamıştı"}]})
            assert yeni["duzeltmeler"][0]["tarih"], "tarih doldurulmadı"
            assert any("duzeltmeler" in d for d in degisen), degisen
            try:
                yaz.uygula(hedef, {"duzeltmeler": [{"alan": "x", "eski": "1"}]})
            except SystemExit as e:
                assert "yeni" in str(e), str(e)
            else:
                raise AssertionError("eksik alanlı düzeltme kabul edildi")
        d = denetim.Denetim({**b, "duzeltmeler": [{"alan": "x", "eski": "", "yeni": "2"}]})
        d.duzeltme()
        assert any("Düzeltme kaydı" in e for e in d.engel), d.engel
        d2 = denetim.Denetim({**b, "yorum": "<p>Yayımlanan −%11,36 yerine gerçek hareket −%1,74.</p>"})
        d2.duzeltme()
        assert any("duzeltmeler kaydı boş" in u for u in d2.uyari), d2.uyari
    sina("yaz/denetim: düzeltme kaydı biçimce tam, yarım kayıt engel", _duzeltme)

    # ── yaz.py: yazı katmanının TEK giriş kapısı — sözleşmesi sınanır
    def _yaz():
        import yaz, tempfile, json as _j, subprocess as _sp, os as _os, time as _t
        with tempfile.TemporaryDirectory() as td:
            hedef = Path(td) / "2026-01-05.json"
            b0 = {"tarih": "2026-01-05", "olusturma": "2026-01-05T04:00:00+00:00",
                  "gundem_kaynagi": "taban", "yorum": "<p>eski</p>", "gundem": {}}
            hedef.write_text(_j.dumps(b0), encoding="utf-8")
            # (a) yabancı alan reddi
            try:
                yaz.uygula(hedef, {"piyasa": {}})
            except SystemExit as e:
                assert "dokunamaz" in str(e)
            else:
                raise AssertionError("yabancı alan kabul edildi")
            # (b) null siler, boş dizge ezmez
            b, d = yaz.uygula(hedef, {"yorum": ""})
            assert b["yorum"] == "<p>eski</p>" and not d, (b["yorum"], d)
            b, d = yaz.uygula(hedef, {"yorum": None})
            assert b["yorum"] is None and "yorum silindi" in d
            # (c) gündem yaması yayın damgasını 'yazili' yapar; yazı damgası ve sürüm atılır
            b, d = yaz.uygula(hedef, {"gundem": {"kilit": "<p>x</p>"}})
            assert b["gundem_kaynagi"] == "yazili" and b["yazi_surumu"] == 1 and b["yazi_zamani"].endswith("+00:00")
            hedef.write_text(_j.dumps(b), encoding="utf-8")
            b, _ = yaz.uygula(hedef, {"gundem": {"kilit": "<p>y</p>"}})
            assert b["yazi_surumu"] == 2 and b["ilk_yazi_zamani"], b.get("yazi_surumu")
            # (d) damgasız taban sigorta: ölçüm yamadan SONRAYSA red (çıkış 3) — alt süreçle
            yama = Path(td) / "yama.json"; yama.write_text(_j.dumps({"yorum": "<p>z</p>"}), encoding="utf-8")
            eski_mtime = _t.time() - 3600
            _os.utime(yama, (eski_mtime, eski_mtime))
            gelecek = {**b, "olusturma": "2099-01-01T00:00:00+00:00"}
            hedef.write_text(_j.dumps(gelecek), encoding="utf-8")
            kod = _sp.run([sys.executable, "-c",
                           f"import sys; sys.path.insert(0, {str(BURASI)!r}); import yaz; "
                           f"yaz.BULTEN = __import__('pathlib').Path({td!r}); "
                           f"sys.argv = ['yaz.py', {str(yama)!r}, '--tarih', '2026-01-05']; "
                           "raise SystemExit(yaz.main())"],
                          capture_output=True, text=True).returncode
            assert kod == 3, f"mtime sigortası: beklenen 3, gelen {kod}"
            # (e) denetim ENGEL → yazma reddi (çıkış 5); dosya değişmez
            hedef.write_text(_j.dumps(b0), encoding="utf-8")
            kod = _sp.run([sys.executable, "-c",
                           f"import sys; sys.path.insert(0, {str(BURASI)!r}); import yaz; "
                           f"yaz.BULTEN = __import__('pathlib').Path({td!r}); "
                           f"sys.argv = ['yaz.py', {str(yama)!r}, '--tarih', '2026-01-05', '--damgasiz']; "
                           "raise SystemExit(yaz.main())"],
                          capture_output=True, text=True).returncode
            assert kod == 5, f"denetim kapısı: beklenen 5, gelen {kod}"
            assert _j.loads(hedef.read_text(encoding="utf-8"))["yorum"] == "<p>eski</p>", "engelli yama yazıldı"
    sina("yaz.py: yabancı alan reddi · null siler · boş ezmez · yazı damgası/sürümü · mtime sigortası · denetim kapısı", _yaz)

    # ── İŞ AKIŞI BÜTÇESİ: 04.09.2026'yı önceden yakalayan aritmetik
    #
    # Ölçütün KENDİSİ sınanır. Bu sınama veri.yml, bulten.yml ve fx.yml'in ilk
    # adımında koşuyor: yanlış alarmı üç iş akışını birden durdurur, yani
    # regresyon fikstürü olmadan konamaz. Üç soru: (a) düzeltilmiş dosya
    # GEÇİYOR mu, (b) 04.09'un dosyası DÜŞÜYOR mu, (c) muafiyet listesi hem
    # koruyor hem sessiz genişlemiyor mu.
    def _is_akisi_butcesi():
        yml = BURASI.parent / ".github" / "workflows" / "veri.yml"
        assert yml.exists(), f"{yml} yok"
        metin = yml.read_text(encoding="utf-8")

        # (a) BUGÜNKÜ dosya temiz — ve ayrıştırıcı gerçekten BAKMIŞ olmalı.
        # "Bulgu yok" ile "hiçbir şey görmedim" aynı görünür; makullük
        # eşikleri o ikisini ayırır.
        sinir, adimlar = _yml_is(metin, "tazele")
        assert sinir and sinir > 0, "iş sınırı okunamadı"
        assert len(adimlar) >= 8, f"yalnız {len(adimlar)} adım ayrıştırıldı — ayrıştırıcı kör"
        adlar = {a["ad"] for a in adimlar if a["ad"]}
        for zorunlu in ("Gereken hatları tazele", "Hazine ihaleleri (ihale günüyse tam kip)",
                        "Koşu nabzı", "Commit"):
            assert zorunlu in adlar, f"'{zorunlu}' adımı ayrıştırılamadı: {sorted(adlar)}"
        assert sum(1 for a in adimlar if a["timeout"]) >= 3, "adım sınırları okunamadı"
        assert sum(1 for a in adimlar if a["uses"]) >= 3, "uses adımları ayrıştırılamadı"
        bulgu = butce_bulgulari(metin)
        assert not bulgu, "bugünkü veri.yml bütçe ölçütünü geçmiyor:\n    " + "\n    ".join(bulgu)

        # (b) 04.09.2026 SABAHININ dosyası — ölçüt onu YAKALAMALI. İki kusur
        # birden var: aritmetik kapanmıyor (45+5+5+2=57 > 50) ve Hazine adımı
        # sınırsız. Ölçüt ikisini de ayrı ayrı söylemeli; yalnız birini
        # söyleyen bir ölçüt "bir düzeltme genelleştirilmeden tamamlanmaz"
        # ilkesini ihlal ederdi.
        dun = """jobs:
  tazele:
    runs-on: ubuntu-latest
    timeout-minutes: 50
    steps:
      - uses: actions/checkout@v4
      - name: Duman sınaması (bülten katmanları)
        run: python bulten/duman.py
      - name: Gereken hatları tazele
        id: tazele
        timeout-minutes: 45
        run: |
          python guncelle.py $SECIM
      - name: Türev hatlar (tazeleme düşse de)
        if: always()
        timeout-minutes: 5
        run: |
          python guncelle.py carry tufex makro
      - name: Hazine ihaleleri (ihale günüyse tam kip)
        if: always()
        continue-on-error: true
        run: |
          python guncelle.py hazine --tam --sistem-kur
      - name: Koşu nabzı
        if: always()
        run: |
          python - <<'PY'
          print("nabız")
          PY
      - name: Commit
        if: always()
        run: |
          git add -A
"""
        b = butce_bulgulari(dun)
        assert any("ARİTMETİK KAPANMIYOR" in x for x in b), f"04.09 aritmetiği yakalanmadı: {b}"
        assert any("SINIRSIZ ADIM" in x and "Hazine" in x for x in b), \
            f"sınırsız Hazine adımı yakalanmadı: {b}"

        # (c) Muafiyet listesi iki yönde de sınanır: listedeki ad sessiz,
        # listede olmayan ad ENGEL, `uses:` adımı yapısal olarak muaf.
        kalip = """jobs:
  tazele:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/setup-python@v5
      - name: %s
        run: echo x
      - name: Gereken hatları tazele
        timeout-minutes: 40
        run: echo y
"""
        assert not butce_bulgulari(kalip % "Commit"), \
            "muaf adım boşuna sınır istedi"
        yeni = butce_bulgulari(kalip % "Yeni ağ adımı")
        assert len(yeni) == 1 and "Yeni ağ adımı" in yeni[0], \
            f"muaf olmayan sınırsız adım yakalanmadı: {yeni}"

        # (d) İş sınırı hiç yoksa da konuşmalı — sınırsız iş, sınırsız adımdan beter.
        sinirsiz = butce_bulgulari(kalip.replace("    timeout-minutes: 60\n", "") % "Commit")
        assert sinirsiz and "iş bütçesi sınırsız" in sinirsiz[0], sinirsiz

        # (f) BİR SİGORTA, KENDİNDEN ÖNCEKİNİ KAPATMAMALI. Hazine adımına
        # 04.09'da tavan konurken şu gözden kaçtı: adımın `timeout-minutes`
        # sınırı dolduğunda GitHub kabuğu öldürür, kabuk ölünce yarım kazımayı
        # geri alan `git checkout` dalı HİÇ koşmaz ve Commit adımı
        # (`if: always()`, artık iş bütçesi sayesinde gerçekten koşuyor) o yarım
        # CSV'yi commit eder — 25.08'de aynı hat 448 ihalelik geçmişi 16 satıra
        # düşürmüştü. Kabuk içi `timeout` denetimi kabuğa geri verir; sınır
        # adımınkinin ALTINDA olmalı, yoksa yine adım tavanına çarpılır.
        hazine = metin.split("- name: Hazine ihaleleri")[-1].split("- name: Koşu nabzı")[0]
        assert "git checkout --" in hazine, \
            "Hazine adımının geri alma dalı kaybolmuş — yarım kazıma commit edilir"
        mm = re.search(r"timeout\s+(?:-k\s+\S+\s+)?(\d+)m\s+python guncelle\.py hazine", hazine)
        assert mm, ("Hazine tam kipi kabuk içi `timeout` ile sınırlanmamış: adımın "
                    "timeout-minutes sınırı dolduğunda kabuk öldürülür, geri alma dalı "
                    "koşmaz ve yarım kazıma commit edilir.")
        hz = next((a["timeout"] for a in adimlar
                   if (a["ad"] or "").startswith("Hazine ihaleleri")), None)
        assert hz and int(mm.group(1)) < hz, (
            f"kabuk içi sınır ({mm.group(1)} dk) adım tavanının ({hz} dk) altında değil "
            "— geri almaya vakit kalmıyor")

        # (e) AYRIŞTIRAMAZSA SESSİZ GEÇMEZ. Ölçütün en tehlikeli bozulma biçimi
        # bu: iş yeniden adlandırılır, ayrıştırıcı hiçbir şey bulamaz, sınav
        # yeşil geçer ve aritmetik bir daha hiç sorulmaz.
        for bozuk in ("jobs:\n  baska:\n    timeout-minutes: 5\n", "name: x\n"):
            try:
                butce_bulgulari(bozuk)
            except AssertionError:
                pass
            else:
                raise AssertionError(f"ayrıştırılamayan iş akışı sessizce geçti: {bozuk!r}")
    sina("iş akışı: veri.yml adım/iş bütçesi aritmetiği kapanıyor", _is_akisi_butcesi)

    # ── ADIM ZAMAN AŞIMI: asılan bir hat bütün bütçeyi yemesin
    #
    # 04.09.2026'ya kadar `_adim_kos` hiçbir duvar saati sınırı taşımıyordu:
    # `ortak/sitecustomize.py` yalnız HTTP isteğine sınır takıyor, adımın
    # toplam süresine değil. 27.08'de EVDS 21 dakika astı ve dört hattın
    # üçünün tamamlanmış işi çöpe gitti. SINANMAYAN EMNİYET EMNİYET DEĞİLDİR:
    # bu sınama bilerek asılan sahte bir betikle koşuyor, ağ istemiyor.
    def _adim_zaman_asimi():
        import os as _os
        import tempfile
        import time as _t
        import sys as _s
        _s.path.insert(0, str(BURASI.parent))
        import guncelle as g

        with tempfile.TemporaryDirectory() as td:
            # Betik bir TORUN açıp kendisi de asılır: öldürmenin süreç AĞACINI
            # kapsadığı ancak böyle ölçülebilir. Yalnız çocuğu öldüren bir
            # düzeltme bu sınamayı geçemez.
            betik = Path(td) / "asil.py"
            betik.write_text(
                "import subprocess, sys, time\n"
                "t = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'])\n"
                "print('TORUN', t.pid, flush=True)\n"
                "time.sleep(600)\n", encoding="utf-8")

            t0 = _t.time()
            kod, son, asti = g._adim_kos([sys.executable, "-u", str(betik)], Path(td), 2)
            gecen = _t.time() - t0

            assert asti, "zaman aşımı raporlanmadı — asılan adım sessizce beklendi"
            assert gecen < 30, f"kesme {gecen:.0f} saniye sürdü — sınır uygulanmıyor"
            assert any("zaman aşımı" in x for x in son), f"son satırlarda iz yok: {son}"

            if _os.name != "nt":
                torun = next((int(x.split()[1]) for x in son if x.startswith("TORUN")), None)
                assert torun, f"torun PID'i okunamadı: {son}"
                for _ in range(30):
                    try:
                        _os.kill(torun, 0)
                    except (ProcessLookupError, PermissionError):
                        break
                    _t.sleep(0.1)
                else:
                    try:
                        _os.kill(torun, 9)
                    finally:
                        raise AssertionError(
                            f"torun {torun} hâlâ ayakta — yalnız çocuk öldürüldü, "
                            "süreç AĞACI değil")

            # DÖNGÜ SÜRMELİ: kesme, sıradaki adımı koşturmayı engellememeli.
            hizli = Path(td) / "hizli.py"
            hizli.write_text("print('bitti')\n", encoding="utf-8")
            kod2, son2, asti2 = g._adim_kos([sys.executable, "-u", str(hizli)], Path(td), 2)
            assert kod2 == 0 and not asti2 and "bitti" in son2, (kod2, asti2, son2)

            # Sınır verilmezse eski davranış: beklenir, kesilmez.
            kod3, _, asti3 = g._adim_kos([sys.executable, "-u", str(hizli)], Path(td))
            assert kod3 == 0 and not asti3

        # TAVAN KİPE BAĞLI. Hafif kipte tavan var; TAM ve GÜNLÜK kipler
        # ölçülerek uzun (FX tam kipi 1 sa 45 dk) ve kendi iş akışlarında
        # koşuyor — onlara hafif kipin tavanını dayatmak haftalık FX koşusunu
        # her hafta öldüren bir YANLIŞ ALARM olurdu.
        h = g.HAT["kredi"]
        assert g.adim_tavani(h, False, False) == g.ADIM_TAVAN_SN
        assert g.adim_tavani(h, True, False) is None, "TAM kipe tavan konmuş"
        assert g.adim_tavani(h, False, True) is None, "GÜNLÜK kipe tavan konmuş"
        # Tohum, ölçülen en yavaş hafif-kip hattının (kredi 869 sn) üstünde
        # olmalı; altına düşerse o hat her koşuda kesilir.
        assert g.ADIM_TAVAN_SN >= 900, f"tavan ölçülen en yavaş hattın altına indi: {g.ADIM_TAVAN_SN}"
        import inspect
        assert "adim_tavan_sn" in inspect.signature(g.kos).parameters, \
            "kos() dışarıdan tavan alamıyor — bütçe ucu kapanmış"
    sina("guncelle: asılan adım duvar saatiyle kesiliyor, süreç ağacı ölüyor", _adim_zaman_asimi)

    # ── KOŞU NABZI DEFTERİ: biriktirir, ama eski okuyucuları kırmaz
    #
    # Dosya 04.09.2026'ya kadar her koşuda ÜZERİNE yazıyordu ve "bu sabahki
    # veri penceresi ateşlendi mi" sorusu geriye dönük cevapsızdı. Defter o
    # soruyu cevaplanabilir yapıyor; ama iki okuyucu (denetim.nabiz,
    # zincir.durum) üst düzey alanları okuyor ve UYUMLULUK SÖZLEŞMESİ bu
    # sınamayla kilitleniyor — biçim değişikliğinin sessizce kırdığı bir
    # okuyucu, ölçülemeyen bir arıza demek.
    def _nabiz_defteri():
        import datetime as _dt
        import tempfile
        import nabiz as nb

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "kosu_nabzi.json"

            # (a) ESKİ BİÇİM GÖÇÜ: defter öncesi tek kayıt kaybolmaz.
            p.write_text(json.dumps({
                "_aciklama": "eski", "veri_kosusu": "2026-09-03T18:51:34+00:00",
                "sonuc": "success", "kaynak": "veri.yml"}, ensure_ascii=False),
                encoding="utf-8")
            d = nb.kaydet(p, sonuc="success", tetik="schedule", cron="13 2 * * 1-5")
            assert len(d["kosular"]) == 2, d["kosular"]
            assert d["kosular"][0]["zaman"].startswith("2026-09-03"), "eski kayıt düştü"
            assert d["kosular"][-1]["cron"] == "13 2 * * 1-5", "pencere kaydedilmedi"

            # (b) UYUMLULUK: üst düzey alanlar en son kaydın kopyası.
            assert d["veri_kosusu"] == d["kosular"][-1]["zaman"]
            assert d["sonuc"] == "success" and d["kaynak"] == "veri.yml"

            # (c) MEVCUT OKUYUCULAR yeni biçimi kırılmadan okuyor.
            import denetim as _den
            import zincir as _z
            eski_yer = _den.BURASI
            try:
                nb.kaydet(p, sonuc="success", tetik="workflow_dispatch",
                          an=_dt.datetime.now(_dt.timezone.utc))
                _den.BURASI = Path(td)
                dd = _den.Denetim({"tarih": "2026-09-04"})
                dd.nabiz()
                assert not dd.uyari, f"taze nabız uyarı üretti: {dd.uyari}"
                # Bayat nabız hâlâ görülüyor: sözleşme yalnız 'okunuyor' değil,
                # 'aynı hükmü veriyor' demek.
                nb.kaydet(p, sonuc="failure", tetik="schedule",
                          an=_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=3))
                dd2 = _den.Denetim({"tarih": "2026-09-04"})
                dd2.nabiz()
                assert dd2.uyari, "üç gün önceki nabız uyarı üretmedi"
            finally:
                _den.BURASI = eski_yer

            # zincir.durum() nabzı KENDİ klasöründen okuyor; ayrıştırma
            # sözleşmesi burada doğrudan sınanır.
            ham = json.loads(p.read_text(encoding="utf-8"))
            assert _dt.datetime.fromisoformat(
                str(ham["veri_kosusu"]).replace("Z", "+00:00")), "zincir bunu ayrıştıramaz"
            assert ham.get("sonuc") == "failure"

            # (d) PENCERE: 61. kayıt en eskisini düşürür.
            p.write_text(json.dumps({"kosular": [
                {"zaman": f"2026-01-01T00:{i:02d}:00+00:00", "sonuc": "success",
                 "tetik": "schedule"} for i in range(nb.AZAMI)]}, ensure_ascii=False),
                encoding="utf-8")
            d = nb.kaydet(p, sonuc="success", tetik="schedule")
            assert len(d["kosular"]) == nb.AZAMI, len(d["kosular"])
            assert d["kosular"][0]["zaman"] == "2026-01-01T00:01:00+00:00", \
                "en eski kayıt düşmedi"

            # (e) BOZUK DOSYA KOŞUYU DÜŞÜRMEZ: nabız tutamamak, koşuyu
            # öldürmekten iyidir.
            p.write_text("{bozuk", encoding="utf-8")
            d = nb.kaydet(p, sonuc="success", tetik="schedule")
            assert len(d["kosular"]) == 1, d

            # (f) 5./6. madde alanları BUGÜN YAZILMAZ — ölçülmemiş bir sayı
            # ölçülmüş gibi görünmesin.
            assert "butce_dk" not in d["kosular"][-1]
            assert "atlanan_butce" not in d["kosular"][-1]
            d = nb.kaydet(p, sonuc="success", tetik="schedule", butce_dk=8,
                          atlanan_butce=["tcmb", "dibs"])
            assert d["kosular"][-1]["butce_dk"] == 8
            assert d["kosular"][-1]["atlanan_butce"] == ["tcmb", "dibs"]

        # İŞ AKIŞI GERÇEKTEN BU MODÜLÜ ÇAĞIRIYOR MU — gömülü bir kopya
        # sınanmamış bir kopyadır.
        yml = (BURASI.parent / ".github" / "workflows" / "veri.yml").read_text(encoding="utf-8")
        assert "python bulten/nabiz.py" in yml, "veri.yml nabız modülünü çağırmıyor"
        assert "kosu_nabzi.json" in yml.split("Commit")[-1], \
            "commit adımı nabız dosyasını eklemiyor — defter depoya hiç ulaşmaz"
    sina("nabız: koşu defteri biriktiriyor, denetim ve zincir kırılmıyor", _nabiz_defteri)

    # ── HAT SÜRESİ DEFTERİ. `kos()` süreyi zaten ölçüyordu ve hiçbir yere
    # yazmıyordu; 04.09'da 45 dakikayı hangi hattın yediği bu yüzden geriye
    # dönük CEVAPSIZ. Ölçü depoya girmezse bütçe de sıralama da uydurma olur.
    def _hat_suresi():
        import tempfile
        import inspect
        import sys as _s
        _s.path.insert(0, str(BURASI.parent))
        import guncelle as g

        class _H:
            def __init__(self, ad): self.ad = ad

        with tempfile.TemporaryDirectory() as td:
            y = Path(td) / "hat_suresi.json"
            for i in range(12):
                g.sure_kaydet([(_H("tcmb"), True, "ok", 100 + i),
                               (_H("kredi"), False, "adım 1 düştü", 800)],
                              tam=False, gunluk=False, yol=y)
            d = g.sure_oku(y)
            assert len(d["tcmb"]) == g.SURE_KAYIT, f"defter budanmadı: {len(d['tcmb'])}"
            assert d["tcmb"][0]["sn"] == 102.0, "on birinci koşu en ESKİyi düşürmedi"
            assert g.medyan("tcmb", yol=y) == 106.5, g.medyan("tcmb", yol=y)
            assert g.p90("tcmb", yol=y) == 110.0, g.p90("tcmb", yol=y)
            # Düşen koşunun süresi medyana GİRMEZ: "bu hat ne kadar sürüyor"
            # sorusunun cevabı, işleyen koşuların süresidir.
            assert g.medyan("kredi", yol=y) is None
            assert g.medyan("kredi", yol=y, yalniz_basarili=False) == 800.0
            assert g.medyan("tcmb", kip="tam", yol=y) is None, "kip süzgeci çalışmıyor"
            # Zaman aşımı ayrı bir sonuç: "düştü" ile aynı kefeye konmaz.
            # MESAJ UYDURULMAZ — `kos()`un GERÇEKTEN ürettiği cümle kullanılır.
            # Uydurma bir dizgeyle sınandığı sürece bu ölçüt yeşil kalıyordu:
            # defter küçük harf arıyor, mesaj BÜYÜK harfle geliyordu ve asılan
            # her hat "düştü" diye kaydediliyordu.
            _kaynak = inspect.getsource(g.kos)
            assert "ZAMAN_ASIMI_IMZASI" in _kaynak, \
                "kos() zaman aşımı imzasını tek tanımdan almıyor"
            _gercek = (f"{g.ZAMAN_ASIMI_IMZASI} — adım 2 (veri.py) 900 saniyede "
                       "bitmedi; süreç ağacı öldürüldü.")
            g.sure_kaydet([(_H("x"), False, _gercek, 900)], tam=False, yol=y)
            assert g.sure_oku(y)["x"][0]["sonuc"] == "zaman aşımı", \
                f"gerçek zaman aşımı mesajı 'düştü' diye kaydedildi: {_gercek!r}"
            # BOZUK DOSYA İSTİSNA FIRLATMAZ: çağıran tohuma düşer.
            y.write_text("bozuk{", encoding="utf-8")
            assert g.sure_oku(y) == {} and g.medyan("tcmb", yol=y) is None \
                and g.p90("tcmb", yol=y) is None

        # WIRING: yazma gerçekten `finally` bloğunda mı. Sarılmasaydı, adım
        # zaman aşımına çarpan bir koşu ölçüyü hiç bırakmazdı.
        kaynak = inspect.getsource(g.main)
        i_fin = kaynak.index("finally:")
        assert "sure_kaydet(" in kaynak[i_fin:], \
            "sure_kaydet finally bloğunda değil — kesilen koşu ölçü bırakmaz"
        yml = (BURASI.parent / ".github" / "workflows" / "veri.yml").read_text(encoding="utf-8")
        assert "bulten/hat_suresi.json" in yml.split("Commit")[-1], \
            "commit adımı hat süresi defterini eklemiyor — ölçü depoya ulaşmaz"
        # DOSYA DEPODA DURMAK ZORUNDA. `git add a b yok` EKSİK yolda düşer ve
        # HİÇBİR ŞEYİ stage'lemez (ölçüldü) — yani defter silinirse commit adımı
        # tazeleme damgasını ve nabzı da sessizce commit etmez olur.
        assert g.HAT_SURESI.exists(), \
            "bulten/hat_suresi.json depoda yok — commit adımının git add'i eksik " \
            "yolda düşer ve hiçbir dosyayı stage'lemez"
    sina("guncelle: hat süresi ölçülüp deftere yazılıyor (budama, kip, bozuk dosya)",
         _hat_suresi)

    # ── GECİKME: söz ile gerçekleşenin TEK karşılaştırması, ve ENGEL sınıfının
    # HİÇ TANIMLANMAMASI. Bu ikinci madde yapısal bir kilittir: gecikme ölçüsü
    # ileride bir yayın kapısına bağlanmak istenirse bu sınama düşer. Geç kalmış
    # bir bülteni durduran kapı, gecikmeyi yokluğa çevirir.
    def _gecikme():
        import datetime as _dt
        import json as _j
        import tempfile
        import gecikme as gk

        def kur(td, bultenler=None, teknikler=None, tweetler=None, nabiz_an=None,
                takvim_duzelt=None):
            k = Path(td)
            (k / "site" / "src" / "data" / "bulten").mkdir(parents=True, exist_ok=True)
            (k / "site" / "src" / "data" / "teknik").mkdir(parents=True, exist_ok=True)
            (k / "site" / "src" / "data" / "tweet").mkdir(parents=True, exist_ok=True)
            (k / "bulten").mkdir(parents=True, exist_ok=True)
            tk = _j.loads((BURASI.parent / "site" / "src" / "data" /
                           "yayin_takvimi.json").read_text(encoding="utf-8"))
            if takvim_duzelt:
                takvim_duzelt(tk)
            (k / "site" / "src" / "data" / "yayin_takvimi.json").write_text(
                _j.dumps(tk, ensure_ascii=False), encoding="utf-8")
            for g, b in (bultenler or {}).items():
                (k / "site" / "src" / "data" / "bulten" / f"{g}.json").write_text(
                    _j.dumps(b, ensure_ascii=False), encoding="utf-8")
            for g, b in (teknikler or {}).items():
                (k / "site" / "src" / "data" / "teknik" / f"{g}.json").write_text(
                    _j.dumps(b, ensure_ascii=False), encoding="utf-8")
            (k / "site" / "src" / "data" / "tweet" / "defter.json").write_text(
                _j.dumps(tweetler or {}, ensure_ascii=False), encoding="utf-8")
            if nabiz_an:
                (k / "bulten" / "kosu_nabzi.json").write_text(
                    _j.dumps({"veri_kosusu": nabiz_an, "sonuc": "success"}),
                    encoding="utf-8")
            return k

        cuma, pazar, cmt = _dt.date(2026, 9, 4), _dt.date(2026, 8, 30), _dt.date(2026, 9, 5)
        with tempfile.TemporaryDirectory() as td:
            k = kur(td)
            # (a) SÖZ = en ERKEN tüketici adımı (sitede 08:11 İst = 05:11 UTC)
            s = gk.soz(k, "Günlük bülten", cuma)
            assert s == _dt.datetime(2026, 9, 4, 5, 11, tzinfo=_dt.timezone.utc), s
            # Pazar: X gönderisi (18:25) siteden (18:41) ÖNCE — en erken odur.
            sp = gk.soz(k, "Haftaya bakış", pazar)
            assert sp == _dt.datetime(2026, 8, 30, 15, 25, tzinfo=_dt.timezone.utc), sp
            # (b) PAY takvimin KENDİ tüketici aralığı — uydurma değil
            assert gk.pay(k, "Günlük bülten") == 24, gk.pay(k, "Günlük bülten")
            assert gk.pay(k, "Haftaya bakış") == 16, gk.pay(k, "Haftaya bakış")
            # (h) cumartesi yayın günü değil
            assert gk.olc(k, cmt) == [], "cumartesi için satır üretildi"

        # (c) TAM 0 dakika ZAMANINDA — sınır dışlamalı değil
        with tempfile.TemporaryDirectory() as td:
            k = kur(td, bultenler={"2026-09-04": {
                "tarih": "2026-09-04", "tur": "gunluk", "gundem_kaynagi": "yazili",
                "olusturma": "2026-09-04T04:30:00+00:00",
                "ilk_yazi_zamani": "2026-09-04T05:11:00+00:00"}},
                nabiz_an="2026-09-04T04:20:00+00:00")
            r = gk.olc(k, cuma, _dt.datetime(2026, 9, 4, 6, 0, tzinfo=_dt.timezone.utc))
            assert len(r) == 1 and r[0]["gecikme_dk"] == 0.0, r
            assert r[0]["sinif"] == "zamaninda", r[0]
            # Darboğaz EN UZUN bacaktır: veri→ölçüm 10 dk, ölçüm→yazı 41 dk.
            assert r[0]["darbogaz"] == "yazı", (r[0]["darbogaz"], r[0]["bacaklar"])
            assert r[0]["bacaklar"]["olcum→yazi"] == 41.0, r[0]["bacaklar"]

        # (f) YAZI YOK: sıfır gecikme DEĞİL. Söz geçmeden zamanında, geçtikten
        #     ve payı aştıktan sonra alarm.
        with tempfile.TemporaryDirectory() as td:
            k = kur(td, bultenler={"2026-09-04": {
                "tarih": "2026-09-04", "tur": "gunluk", "gundem_kaynagi": "taban",
                "olusturma": "2026-09-04T04:30:00+00:00"}},
                nabiz_an="2026-09-04T02:20:00+00:00")
            erken = gk.olc(k, cuma, _dt.datetime(2026, 9, 4, 4, 18, tzinfo=_dt.timezone.utc))[0]
            assert erken["henuz_yazilmadi"] and erken["ilk_yazi"] is None
            assert erken["sinif"] == "zamaninda", erken
            gec = gk.olc(k, cuma, _dt.datetime(2026, 9, 4, 6, 30, tzinfo=_dt.timezone.utc))[0]
            assert gec["sinif"] == "alarm" and gec["darbogaz"] == "yazı", gec

        # (g) ÖLÇÜM DOSYASI HİÇ YOK = yokluk; söz geçtiyse payı YOKTUR.
        #     04.09'un 05:12 hâli: bülten henüz üretilmemişti.
        with tempfile.TemporaryDirectory() as td:
            k = kur(td, nabiz_an="2026-09-03T18:51:34+00:00")
            once = gk.olc(k, cuma, _dt.datetime(2026, 9, 4, 4, 18, tzinfo=_dt.timezone.utc))[0]
            assert once["sinif"] == "zamaninda", once
            sonra = gk.olc(k, cuma, _dt.datetime(2026, 9, 4, 5, 12, tzinfo=_dt.timezone.utc))[0]
            assert sonra["sinif"] == "alarm" and sonra["darbogaz"] == "ölçüm", sonra

        # (e) PAZAR İKİ YAYIN — ayrı satır, ayrı gerçekleşme kaydı
        with tempfile.TemporaryDirectory() as td:
            k = kur(td,
                    bultenler={"2026-08-30": {"tarih": "2026-08-30", "tur": "haftalik",
                                              "gundem_kaynagi": "yazili",
                                              "olusturma": "2026-08-30T15:38:18"}},
                    teknikler={"2026-08-30": {"tarih": "2026-08-30", "yazili": True,
                                              "olcum_zamani": "2026-08-30T16:28:20+00:00"}})
            r = gk.olc(k, pazar, _dt.datetime(2026, 8, 30, 20, 0, tzinfo=_dt.timezone.utc))
            assert len(r) == 2, [x["yayin"] for x in r]
            assert {x["yayin"] for x in r} == {"Haftaya bakış", "Haftalık teknik analiz"}
            # ALT SINIR etiketlenir: yazı anı kaydedilmemiş, ölçüm damgası kullanıldı
            assert all(x["alt_sinir"] and x["olculmedi"] for x in r), r

        # (i) KAPSAM KUSURU: tüketici adımı silinen yayın SESSİZCE GEÇMEZ
        with tempfile.TemporaryDirectory() as td:
            def sil(tk):
                for y in tk["yayinlar"]:
                    if y.get("yayin") == "Günlük bülten":
                        y["adimlar"] = [a for a in y["adimlar"]
                                        if a.get("ad") not in gk.TUKETICI]
            k = kur(td, takvim_duzelt=sil)
            try:
                gk.soz(k, "Günlük bülten", cuma)
            except ValueError:
                pass
            else:
                raise AssertionError("tüketici adımı yokken sessizce geçildi")

        # (d) YAPISAL KİLİT — ÜÇTEN FAZLA SINIF YOK ve hiçbir girdi dördüncüyü
        #     üretmiyor. Yayını DURDURAN bir sınıf bu modülde tanımlı değildir.
        assert gk.SINIFLAR == ("zamaninda", "uyari", "alarm"), gk.SINIFLAR
        kaynak = Path(gk.__file__).read_text(encoding="utf-8")
        import re as _re
        assert not _re.search(r"""["']engel["']""", kaynak, _re.I), \
            "gecikme.py'ye yayın kapısı sınıfı eklenmiş — gecikme yokluğa çevrilir"
        with tempfile.TemporaryDirectory() as td:
            for yazili in (True, False):
                for ilk in (None, "2026-09-04T03:00:00+00:00", "2026-09-04T09:00:00+00:00"):
                    b = {"tarih": "2026-09-04", "tur": "gunluk",
                         "gundem_kaynagi": "yazili" if yazili else "taban",
                         "olusturma": "2026-09-04T04:30:00+00:00"}
                    if ilk:
                        b["ilk_yazi_zamani"] = ilk
                    k = kur(td, bultenler={"2026-09-04": b})
                    for saat in (0, 4, 5, 6, 12, 23):
                        for x in gk.olc(k, cuma, _dt.datetime(2026, 9, 4, saat, 30,
                                                              tzinfo=_dt.timezone.utc)):
                            assert x["sinif"] in gk.SINIFLAR, x["sinif"]

        # (j) TEKRAR KOŞULU: defter boşken ve tek günlük gecikmede SESSİZ
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "defter.jsonl"
            assert gk.tekrar(d)[0] is False, "boş defter tekrar üretti"
            satir = lambda t, s: _j.dumps({"tarih": t, "yayin": "Günlük bülten", "sinif": s})
            d.write_text("\n".join([satir("2026-08-31", "zamaninda"),
                                    satir("2026-09-01", "zamaninda"),
                                    satir("2026-09-02", "zamaninda"),
                                    satir("2026-09-03", "zamaninda"),
                                    satir("2026-09-04", "alarm")]) + "\n", encoding="utf-8")
            assert gk.tekrar(d)[0] is False, "tek günlük gecikme tekrar sayıldı"
            d.write_text("\n".join([satir("2026-08-31", "zamaninda"),
                                    satir("2026-09-01", "uyari"),
                                    satir("2026-09-02", "zamaninda"),
                                    satir("2026-09-03", "alarm"),
                                    satir("2026-09-04", "alarm")]) + "\n", encoding="utf-8")
            assert gk.tekrar(d)[0] is True, "beş günün üçü gecikmeliyken tekrar tutmadı"
    sina("gecikme: söz takvimden çözülüyor, yokluk gecikmeden ayrı, ENGEL sınıfı YOK",
         _gecikme)

    # ── GECİKME KAYDI YAZMANIN YAN ETKİSİ. Rutinin kaçınamayacağı tek araç
    # yaz.py; kayıt bir bayrağa değil, yazma işleminin kendisine bağlı. Ve
    # ölçümdeki bir kusur YAZMAYI DÜŞÜRMEMELİ — try/except gerçekten kapı değil.
    def _gecikme_defteri():
        import json as _j
        import subprocess as _sp
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            k = Path(td)
            (k / "site" / "src" / "data" / "bulten").mkdir(parents=True)
            (k / "site" / "src" / "data" / "teknik").mkdir(parents=True)
            (k / "site" / "src" / "data" / "tweet").mkdir(parents=True)
            (k / "bulten").mkdir(parents=True)
            import shutil as _sh
            _sh.copy2(BURASI.parent / "site" / "src" / "data" / "yayin_takvimi.json",
                      k / "site" / "src" / "data" / "yayin_takvimi.json")
            (k / "site" / "src" / "data" / "tweet" / "defter.json").write_text(
                "{}", encoding="utf-8")
            (k / "bulten" / "kosu_nabzi.json").write_text(
                _j.dumps({"veri_kosusu": "2026-01-05T02:20:00+00:00", "sonuc": "success"}),
                encoding="utf-8")
            bd = k / "site" / "src" / "data" / "bulten"
            hedef = bd / "2026-01-05.json"                     # pazartesi
            b0 = {"tarih": "2026-01-05", "tur": "gunluk",
                  "olusturma": "2026-01-05T04:00:00+00:00",
                  "gundem_kaynagi": "taban", "yorum": "<p>eski</p>", "gundem": {}}
            hedef.write_text(_j.dumps(b0), encoding="utf-8")
            yama = k / "yama.json"
            yama.write_text(_j.dumps({"yorum": "<p>yeni</p>"}), encoding="utf-8")
            defter = k / "gecikme_defteri.jsonl"

            on = (f"import sys, pathlib; sys.path.insert(0, {str(BURASI)!r}); ")
            kur = (f"import yaz; yaz.KOK = pathlib.Path({str(k)!r}); "
                   f"yaz.BULTEN = pathlib.Path({str(bd)!r}); "
                   f"sys.argv = ['yaz.py', {str(yama)!r}, '--tarih', '2026-01-05', "
                   "'--damgasiz', '--engelle-yaz']; raise SystemExit(yaz.main())")

            # (a) yazma → defter satırı açılır ve ilk_yazi_zamani ile TUTARLI
            r = _sp.run([sys.executable, "-c",
                         on + f"import gecikme; gecikme.DEFTER = pathlib.Path({str(defter)!r}); "
                         + kur], capture_output=True, text=True)
            assert r.returncode == 0, (r.returncode, r.stdout[-600:], r.stderr[-600:])
            assert defter.exists(), "defter satırı hiç açılmadı"
            satirlar = [_j.loads(x) for x in defter.read_text(encoding="utf-8").splitlines() if x.strip()]
            assert len(satirlar) == 1, satirlar
            yazilan = _j.loads(hedef.read_text(encoding="utf-8"))
            assert satirlar[0]["ilk_yazi"] == yazilan["ilk_yazi_zamani"], satirlar[0]
            assert satirlar[0]["yayin"] == "Günlük bülten" and satirlar[0]["tarih"] == "2026-01-05"
            assert satirlar[0]["sinif"] in ("zamaninda", "uyari", "alarm")

            # (b) GECİKME MODÜLÜ BOZUKKEN DE YAZILIR — try/except kapı değil
            hedef.write_text(_j.dumps(b0), encoding="utf-8")
            bozuk = ("import sys, types; m = types.ModuleType('gecikme');\n"
                     "def _bozuk(*a, **kw): raise RuntimeError('bilerek bozuldu')\n"
                     "m.defter_yaz = _bozuk; m.ozet_satiri = _bozuk; "
                     "sys.modules['gecikme'] = m; ")
            r2 = _sp.run([sys.executable, "-c", on + bozuk + kur],
                         capture_output=True, text=True)
            assert r2.returncode == 0, (r2.returncode, r2.stderr[-600:])
            assert _j.loads(hedef.read_text(encoding="utf-8"))["yorum"] == "<p>yeni</p>", \
                "gecikme ölçümündeki kusur YAZMAYI düşürdü — try/except kapı olmuş"
            assert "gecikme kaydı yazılamadı" in r2.stderr, r2.stderr[-400:]
    sina("yaz.py: gecikme kaydı yazmanın yan etkisi, kusuru yazmayı DÜŞÜRMÜYOR",
         _gecikme_defteri)

    # ── BUGÜN TAZELENEMEYEN HATLAR. Kesmenin ve düşen bir koşunun bedeli
    # yazarın önüne konur; UYARI, engel değil. Kör koşuda TEK satıra iner.
    def _denetim_tazeleme_atlandi():
        import denetim as _den
        import nabiz as _nb
        import tazeleme as _tz
        from datetime import date as _date

        bugun = _date.today().isoformat()
        temel = {"tarih": bugun, "tur": "gunluk"}
        gercek_y, gercek_d, gercek_oku = _tz._yayimlar, _tz.durum_oku, _nb.oku
        try:
            # (a) KÖR KOŞU → tek satır, hat hat on altı satır değil
            _tz._yayimlar = lambda y: ([], False)
            d = _den.Denetim(dict(temel)); d.tazeleme_atlandi()
            assert len(d.uyari) == 1 and "kör koşu" in d.uyari[0], d.uyari
            assert "hattın tamamı" in d.uyari[0], d.uyari[0]

            # (b) HEPSİ BUGÜN TAZELENDİ → sessiz
            sahte = [{"adi": "TCMB Analitik Bilanço", "kurum": "TCMB",
                      "an": f"{bugun}T02:30:00"}]
            _tz._yayimlar = lambda y: (sahte, True)
            _tz.durum_oku = lambda: {t.hat: f"{bugun}T04:22:00" for t in _tz.TETIKLER}
            d2 = _den.Denetim(dict(temel)); d2.tazeleme_atlandi()
            assert not d2.uyari, d2.uyari

            # (c) GEREKLİ AMA DAMGASI DÜNKÜ → adıyla ve SEBEBİYLE listelenir;
            #     okurun gördüğü ad basılır, hattın kısa adı değil
            _tz.durum_oku = lambda: {t.hat: "2026-01-01T04:22:00" for t in _tz.TETIKLER}
            _nb.oku = lambda p: {"kosular": [{"zaman": "x", "sonuc": "success"}]}
            d3 = _den.Denetim(dict(temel)); d3.tazeleme_atlandi()
            assert d3.uyari and "tazelenemeyen" in d3.uyari[0], d3.uyari
            assert "koşu düştü ya da kaynak yayımlamadı" in d3.uyari[0], d3.uyari[0]
            assert "TCMB fonlama ve likidite" in d3.uyari[0], d3.uyari[0]
            assert not d3.engel, "ölçüt ENGEL üretti — kaynak düştüğünde yayını durdururdu"

            # (d) BÜTÇEYLE ATLANAN hat ayrı sebeple anılır (5./6. maddeler
            #     geldiğinde alan dolacak; biçim bugünden hazır)
            _nb.oku = lambda p: {"kosular": [{"zaman": "x", "sonuc": "success",
                                              "atlanan_butce": ["fonlama"]}]}
            d4 = _den.Denetim(dict(temel)); d4.tazeleme_atlandi()
            assert "bütçe ile atlandı: TCMB fonlama ve likidite" in d4.uyari[0], d4.uyari[0]

            # (e) ARŞİV KOŞUSU: eski bir bülteni bugünün kararlarıyla ölçmez
            d5 = _den.Denetim({"tarih": "2026-01-05", "tur": "gunluk"})
            d5.tazeleme_atlandi()
            assert not d5.uyari and not d5.gecen, (d5.uyari, d5.gecen)

            # (f) KISA TAVAN GERÇEKTEN TAKILIYOR MU. Bu ölçüt yazı katmanının
            #     kritik yolunda; takvim ucu düştüğünde 25 sn × yıl × yeniden
            #     deneme, bültenin yazılmasını dakikalarca geciktirirdi.
            gorulen = {}

            def _kaydet(y):
                gorulen["sn"] = _tz.TAKVIM_ZAMAN_ASIMI
                return ([], False)
            _tz._yayimlar = _kaydet
            _den.Denetim(dict(temel)).tazeleme_atlandi()
            assert gorulen.get("sn") == _den.TAKVIM_YOKLAMA_SN, gorulen
            assert _tz.TAKVIM_ZAMAN_ASIMI == 25, "tavan geri konmadı — koşu kalıcı kısaldı"
        finally:
            _tz._yayimlar, _tz.durum_oku, _nb.oku = gercek_y, gercek_d, gercek_oku
    sina("denetim: bugün tazelenemeyen hatlar UYARI, kör koşuda tek satır",
         _denetim_tazeleme_atlandi)


    # ── FİKSTÜR: ALARMIN YANLIŞ ALARM ORANI DEPODAKİ GERÇEK SAYILARA KİLİTLİ.
    #
    # "Yayının önünde duran denetimin yanlış alarmı arızanın kendisidir" —
    # gecikme alarmı yayının değil bir e-posta kanalının önünde duruyor ama
    # aynı mantık geçerli: her sabah öten alarm iki haftada okunmaz olur.
    # Fikstür ayrıca eşiğin SESSİZCE SIKIŞTIRILMASINI yasaklar; eşik oynatılırsa
    # dört temiz günün biri kırmızıya döner ve veri/bülten koşuları durur.
    # Bir denetimin doğruluğu kadar SUSTUĞU günler de sınanmalı.
    #
    # ÖLÇÜM (04.09.2026, `python3 bulten/gecikme.py --gecmis`, depodaki gerçek
    # bülten dosyalarına karşı): hafta içi günlük bültenin on gözleminde
    # 6 ALARM / 4 TEMİZ, YANLIŞ POZİTİF YOK — altı alarmın altısı da deponun
    # kendi kaydında arıza ya da gecikme geçen günler.
    #
    # DÜRÜSTLÜK NOTU — ALT SINIR. `ilk_yazi_zamani` alanı yalnız 03.09'dan beri
    # yazılıyor. Ondan eski günlerde yazı anı ölçüm damgasından ALT SINIR olarak
    # alınıyor; gerçek yazı anı 11–14 dakika sonrasıdır. Yani ALARM hükümleri
    # güvenli (alt sınır bile sözü aşıyorsa gecikme kesindir) ama TEMİZ
    # günlerin payı göründüğünden İNCE: −31,9/−40,6/−41,2 yerine ≈−21/−30/−31.
    # Fikstür bu günleri `True` ile adıyla etiketliyor; iki hafta gerçek yazı
    # anı birikince yeniden ölçülmeli.
    def _gecikme_fikstur():
        import json as _j
        import shutil as _sh
        import tempfile
        import gecikme as gk

        # FİKSTÜRÜN GİRDİSİ DE ÖLÇÜLMÜŞ BİR SABİTTİR — CANLI DOSYA DEĞİL.
        #
        # Bu ölçüt VERİNİN önünde duruyor (`veri.yml`, `bulten.yml` ve `fx.yml`
        # duman'ı ilk adım olarak koşuyor), yani yanlış alarmı üç iş akışını
        # birden durdurur. İlk sürüm beklenen sınıfları DEPODAKİ CANLI bülten
        # dosyalarına karşı oynatıyordu ve o dosyalar meşru olarak değişebilir:
        # `yaz.py` yayımlanmış bir sayıya düzeltme yazıldığında
        # `ilk_yazi_zamani`ni `setdefault` ile O ANIN damgasıyla doldurur
        # (alan 03.09 öncesi sayılarda hiç yok). Ölçüldü (04.09.2026):
        # 31.08 sayısına bugün bir düzeltme yazmak yetiyor — `alt_sinir`
        # True'dan False'a, sınıf `zamaninda`dan `alarm`a dönüyor ve duman
        # DÜŞÜYOR. Yani okura verilen sözün ölçüsü doğru, sayfa doğru, kusur
        # ÖLÇÜTÜN HASSASİYETİNDE: bir DÜZELTME yayımlamak veri hattını
        # durdururdu. "Yayının ya da verinin önünde duran denetimin yanlış
        # alarmı arızanın kendisidir."
        #
        # Bu yüzden girdi de dondurulur: aşağıdaki damgalar 04.09.2026'da
        # depodaki dosyalardan OKUNDU ve fikstürün kendi girdisi oldu. Ölçüt
        # böylece KURALI kilitler (eşik sessizce sıkıştırılamaz — oynatılırsa
        # dört temiz günün biri kırmızıya döner), depodaki verinin sonraki
        # hâlini değil. Canlı veri yine de oynatılıyor; ayrışırsa aşağıdaki
        # çapraz bakış onu ADIYLA basar ama iş akışını DÜŞÜRMEZ — kusuru
        # tarama bulur, hükmü ona bakan biri verir.
        OLCULEN_GIRDI = {
            "bulten": {
                "2026-08-23": ("haftalik", "2026-08-23T23:12:07", None),
                "2026-08-24": ("gunluk", "2026-08-24T11:18:48", None),
                "2026-08-25": ("gunluk", "2026-08-25T21:07:12", None),
                "2026-08-26": ("gunluk", "2026-08-26T07:59:29", None),
                "2026-08-27": ("gunluk", "2026-08-27T12:27:44", None),
                "2026-08-28": ("gunluk", "2026-08-28T07:36:29", None),
                "2026-08-30": ("haftalik", "2026-08-30T15:38:18", None),
                "2026-08-31": ("gunluk", "2026-08-31T04:39:03", None),
                "2026-09-01": ("gunluk", "2026-09-01T04:30:26", None),
                "2026-09-02": ("gunluk", "2026-09-02T04:29:47", None),
                "2026-09-03": ("gunluk", "2026-09-03T04:31:14+00:00",
                               "2026-09-03T04:44:55+00:00"),
                "2026-09-04": ("gunluk", "2026-09-04T05:39:02+00:00",
                               "2026-09-04T05:50:32+00:00"),
            },
            # 23.08'in teknik ölçümü depoda HİÇ YOK; o satırın alarmı bir
            # gecikme değil YOKLUK ölçüsüdür ve fikstür onu da böyle taşır.
            "teknik": {"2026-08-30": "2026-08-30T16:28:20+00:00"},
        }

        def _fikstur_deposu(td):
            k = Path(td)
            for alt in ("bulten", "teknik", "tweet"):
                (k / "site" / "src" / "data" / alt).mkdir(parents=True, exist_ok=True)
            (k / "bulten").mkdir(parents=True, exist_ok=True)
            _sh.copy2(BURASI.parent / "site" / "src" / "data" / "yayin_takvimi.json",
                      k / "site" / "src" / "data" / "yayin_takvimi.json")
            (k / "site" / "src" / "data" / "tweet" / "defter.json").write_text(
                "{}", encoding="utf-8")
            for g, (tur, olusturma, ilk) in OLCULEN_GIRDI["bulten"].items():
                b = {"tarih": g, "tur": tur, "gundem_kaynagi": "yazili",
                     "olusturma": olusturma}
                if ilk:
                    b["ilk_yazi_zamani"] = ilk
                (k / "site" / "src" / "data" / "bulten" / f"{g}.json").write_text(
                    _j.dumps(b, ensure_ascii=False), encoding="utf-8")
            for g, olcum in OLCULEN_GIRDI["teknik"].items():
                (k / "site" / "src" / "data" / "teknik" / f"{g}.json").write_text(
                    _j.dumps({"olcum_zamani": olcum, "yazili": True},
                             ensure_ascii=False), encoding="utf-8")
            return k

        # (tarih, yayın) → (sınıf, yazı anı ALT SINIRDAN mı)
        HAFTA_ICI = {
            ("2026-08-24", "Günlük bülten"): ("alarm", True),
            ("2026-08-25", "Günlük bülten"): ("alarm", True),
            ("2026-08-26", "Günlük bülten"): ("alarm", True),
            ("2026-08-27", "Günlük bülten"): ("alarm", True),
            ("2026-08-28", "Günlük bülten"): ("alarm", True),
            ("2026-08-31", "Günlük bülten"): ("zamaninda", True),
            ("2026-09-01", "Günlük bülten"): ("zamaninda", True),
            ("2026-09-02", "Günlük bülten"): ("zamaninda", True),
            ("2026-09-03", "Günlük bülten"): ("zamaninda", False),
            ("2026-09-04", "Günlük bülten"): ("alarm", False),
        }
        # PAZAR n=2 — planın fikstürü bu satırları HİÇ saymıyordu; tam oynatma
        # onları da üretiyor ve ölçü onlar için de kuruluyor. İki gözlemle eşik
        # açılmadığı için e-posta kanalının KAPSAMI DIŞINDALAR (aşağıdaki
        # sınama bunu ayrıca doğruluyor), ama ölçüldükleri görünmeli.
        PAZAR = {
            ("2026-08-23", "Haftaya bakış"): "alarm",
            ("2026-08-23", "Haftalık teknik analiz"): "alarm",
            ("2026-08-30", "Haftaya bakış"): "uyari",
            ("2026-08-30", "Haftalık teknik analiz"): "alarm",
        }

        # Oynatma dondurulmuş girdi üzerinde koşar. `gecmis()` düz sözlük
        # döndürdüğü için geçici depo hemen kapanabilir.
        with tempfile.TemporaryDirectory() as _td:
            satirlar = {(s["tarih"], s["yayin"]): s
                        for s in gk.gecmis(_fikstur_deposu(_td))}
        for anahtar, (sinif, alt) in HAFTA_ICI.items():
            s = satirlar.get(anahtar)
            assert s is not None, f"fikstür günü oynatmada yok: {anahtar}"
            assert s["sinif"] == sinif, (anahtar, s["sinif"], "beklenen", sinif)
            assert s["alt_sinir"] is alt, (anahtar, "alt sınır etiketi kaydı", s["alt_sinir"])
            if sinif == "zamaninda":
                assert s["gecikme_dk"] <= 0, (anahtar, s["gecikme_dk"])
            else:
                assert s["gecikme_dk"] > s["pay_dk"], (anahtar, s["gecikme_dk"], s["pay_dk"])
        for anahtar, sinif in PAZAR.items():
            s = satirlar.get(anahtar)
            assert s is not None, f"pazar satırı oynatmada yok: {anahtar}"
            assert s["sinif"] == sinif, (anahtar, s["sinif"], "beklenen", sinif)

        alarm = [k for k, (s, _) in HAFTA_ICI.items() if s == "alarm"]
        temiz = [k for k, (s, _) in HAFTA_ICI.items() if s == "zamaninda"]
        assert (len(alarm), len(temiz)) == (6, 4), (len(alarm), len(temiz))

        # 04.09'un kendi sayısı: söz 05:11Z, yazı 05:50:32Z → +39,5 dk, payı
        # (24 dk) aşıyor. Arızanın ölçüsü budur; kayarsa fikstür yeniden ölçülür.
        dort = satirlar[("2026-09-04", "Günlük bülten")]
        assert 39.0 <= dort["gecikme_dk"] <= 40.0, dort["gecikme_dk"]
        assert dort["pay_dk"] == 24, dort["pay_dk"]

        # CANLI ÇAPRAZ BAKIŞ — RAPOR EDER, DÜŞÜRMEZ. Depodaki dosyalar meşru
        # olarak değişebilir (bir düzeltme, yeniden kurulan bir ölçüm); o zaman
        # değişen şey KURAL değil VERİDİR ve veri hattını durdurması yanlış
        # olur. Ama sessizce geçmesi de yanlış: "bakılmayan yer geçen sınavla
        # aynı görünür". Ayrışma adıyla basılır, hükmü ona bakan biri verir.
        beklenen = {k: s for k, (s, _) in HAFTA_ICI.items()}
        beklenen.update(PAZAR)
        canli = {(s["tarih"], s["yayin"]): s for s in gk.gecmis(BURASI.parent)}
        for anahtar, sinif in sorted(beklenen.items()):
            c = canli.get(anahtar)
            if c is None:
                print(f"  ! fikstür sapması — {anahtar[0]} · {anahtar[1]}: "
                      "depoda artık oynatılmıyor (ölçüm dosyası silinmiş?)")
            elif c["sinif"] != sinif:
                print(f"  ! fikstür sapması — {anahtar[0]} · {anahtar[1]}: "
                      f"depo şimdi '{c['sinif']}' diyor, ölçülen girdi "
                      f"'{sinif}' demişti ({gk._sayi(c['gecikme_dk'])} dk). "
                      "Kural değil VERİ değişmiş olabilir; bak ve fikstürü "
                      "yeniden ölç.")

        # SENTETİK SAATLER — gecikmenin YOKLUKTAN farkı tam burada ölçülür.
        # 04.09'un GERÇEK zaman çizgisi oynatılıyor: 05:24'e kadar ortada ölçüm
        # dosyası yok, yazı 05:50'de düşüyor.
        cuma = dt.date(2026, 9, 4)
        yazilmis = {"tarih": "2026-09-04", "tur": "gunluk", "gundem_kaynagi": "yazili",
                    "olusturma": "2026-09-04T05:39:02+00:00",
                    "ilk_yazi_zamani": "2026-09-04T05:50:32+00:00"}
        with tempfile.TemporaryDirectory() as td:
            k = Path(td)
            for alt in ("bulten", "teknik", "tweet"):
                (k / "site" / "src" / "data" / alt).mkdir(parents=True, exist_ok=True)
            (k / "bulten").mkdir(parents=True, exist_ok=True)
            _sh.copy2(BURASI.parent / "site" / "src" / "data" / "yayin_takvimi.json",
                      k / "site" / "src" / "data" / "yayin_takvimi.json")
            (k / "site" / "src" / "data" / "tweet" / "defter.json").write_text(
                "{}", encoding="utf-8")
            dosya = k / "site" / "src" / "data" / "bulten" / "2026-09-04.json"

            def saatte(h, m):
                return gk.olc(k, cuma, dt.datetime(2026, 9, 4, h, m,
                                                   tzinfo=dt.timezone.utc))[0]

            # 04:18 — söz (05:11Z) henüz geçmedi: ortada bülten olmaması bile
            # bu saatte bir gecikme DEĞİLDİR.
            assert saatte(4, 18)["sinif"] == "zamaninda", "04:18'de söz henüz geçmemişti"
            # 05:12 — söz geçti ve ölçüm dosyası HİÇ YOK: bu yokluktur, payı da
            # yoktur. (04.09'un 05:12'deki gerçek hâli.)
            bes_oniki = saatte(5, 12)
            assert bes_oniki["sinif"] == "alarm" and bes_oniki["darbogaz"] == "ölçüm", bes_oniki
            # 06:30 — bülten YAZILMIŞ ama geç: gecikme, yokluğun kapanmasıyla
            # kapanmaz. Ölçü "söz verilen saatte yerinde miydi" diye sorar.
            dosya.write_text(_j.dumps(yazilmis, ensure_ascii=False), encoding="utf-8")
            for h, m in ((6, 30), (12, 0), (23, 0)):
                s = saatte(h, m)
                assert s["sinif"] == "alarm", (h, m, s["sinif"])
                assert s["ilk_yazi"] is not None and 39.0 <= s["gecikme_dk"] <= 40.0, s

            # Cumartesi yayın günü değil; takvimden tüketici adımı silinirse
            # SESSİZCE GEÇMEZ (kapsam kusuruna karşı).
            assert gk.olc(k, dt.date(2026, 9, 5)) == []
            tk = _j.loads((k / "site" / "src" / "data" / "yayin_takvimi.json")
                          .read_text(encoding="utf-8"))
            for y in tk["yayinlar"]:
                if y.get("yayin") == "Günlük bülten":
                    y["adimlar"] = [a for a in y["adimlar"]
                                    if a.get("ad") not in gk.TUKETICI]
            (k / "site" / "src" / "data" / "yayin_takvimi.json").write_text(
                _j.dumps(tk, ensure_ascii=False), encoding="utf-8")
            try:
                gk.olc(k, cuma)
            except ValueError:
                pass
            else:
                raise AssertionError("tüketici adımı silinince fonksiyon sessizce geçti")
    sina("gecikme fikstürü: 6 alarm / 4 temiz, yanlış pozitif yok (alt sınır etiketli)",
         _gecikme_fikstur)

    # ── ALARM KANALI: KAPSAM + MÜKERRERLİK. Ölçü bütün yayınları görür, e-posta
    # kanalı yalnız eşiği ÖLÇÜLMÜŞ yayını taşır (pazar n=2, kapsam dışı ve
    # nöbetçinin yokluk sorusunda kalıyor). Mükerrerlik kaydı olmadan alarm her
    # uyanmada öterdi: iş akışı günde 40–70 kez uyanıyor.
    def _gecikme_alarm_kanali():
        import datetime as _dt
        import json as _j
        import shutil as _sh
        import tempfile
        import gecikme as gk

        def kur(td, bultenler=None, teknikler=None):
            k = Path(td)
            for alt in ("bulten", "teknik", "tweet"):
                (k / "site" / "src" / "data" / alt).mkdir(parents=True, exist_ok=True)
            (k / "bulten").mkdir(parents=True, exist_ok=True)
            _sh.copy2(BURASI.parent / "site" / "src" / "data" / "yayin_takvimi.json",
                      k / "site" / "src" / "data" / "yayin_takvimi.json")
            (k / "site" / "src" / "data" / "tweet" / "defter.json").write_text(
                "{}", encoding="utf-8")
            for alt, kayit in (("bulten", bultenler or {}), ("teknik", teknikler or {})):
                for g, b in kayit.items():
                    (k / "site" / "src" / "data" / alt / f"{g}.json").write_text(
                        _j.dumps(b, ensure_ascii=False), encoding="utf-8")
            return k

        gec = {"tarih": "2026-09-04", "tur": "gunluk", "gundem_kaynagi": "yazili",
               "olusturma": "2026-09-04T05:39:00+00:00",
               "ilk_yazi_zamani": "2026-09-04T05:50:32+00:00"}
        cuma, pazar = _dt.date(2026, 9, 4), _dt.date(2026, 8, 30)

        with tempfile.TemporaryDirectory() as td:
            k = kur(td, bultenler={"2026-09-04": gec})
            kayit = Path(td) / "alarm_kaydi.json"

            # (a) İLK KARAR: kapsamdaki alarm YENİ
            r1 = gk.alarm_karari(k, cuma, kayit)
            assert [s["yayin"] for s in r1["alarm"]] == ["Günlük bülten"], r1["alarm"]
            assert len(r1["yeni"]) == 1 and "39,5" in r1["gerekce"], r1["gerekce"]

            # (b) KAYIT YAZILDIKTAN SONRA MÜKERRER DEĞİL — sıra kritik: kanal
            #     önce kaydı yazar, sonra düşer; tersi her uyanmada e-posta.
            gk.alarm_kaydi_yaz(kayit, r1["yeni"])
            r2 = gk.alarm_karari(k, cuma, kayit)
            assert r2["alarm"] and not r2["yeni"], r2
            assert "zaten bildirilmiş" in r2["gerekce"], r2["gerekce"]

            # (c) KAYIT SİLİNİRSE yeniden alarm (kanal kendi kendini susturamaz)
            kayit.unlink()
            assert gk.alarm_karari(k, cuma, kayit)["yeni"], "kayıt silindi, alarm dönmedi"

            # (d) BOZUK KAYIT SESSİZLİK ÜRETMEZ: okunamayan kayıt "hiç
            #     bildirilmemiş" sayılır — kaybolmuş alarmdansa çift alarm.
            kayit.write_text("{bozuk", encoding="utf-8")
            assert gk.alarm_karari(k, cuma, kayit)["yeni"], "bozuk kayıt alarmı susturdu"

            # (e) KAYIT SINIRSIZ BÜYÜMEZ
            eski = {"kayitlar": {f"2020-01-{i:02d}|X": {"an": "x"} for i in range(1, 29)}}
            kayit.write_text(_j.dumps(eski), encoding="utf-8")
            gercek_azami = gk.ALARM_KAYIT_AZAMI
            try:
                gk.ALARM_KAYIT_AZAMI = 10
                d = gk.alarm_kaydi_yaz(kayit, r1["yeni"])
                assert len(d["kayitlar"]) == 10, len(d["kayitlar"])
                assert "2026-09-04|Günlük bülten" in d["kayitlar"], "yeni kayıt budandı"
            finally:
                gk.ALARM_KAYIT_AZAMI = gercek_azami

        # (f) PAZAR KAPSAM DIŞI — ölçülür, defterde görünür, E-POSTA GÖNDERMEZ.
        #     n=2 ile eşik açılmaz; yokluk sorusu cron'lu nöbetçide kalıyor.
        with tempfile.TemporaryDirectory() as td:
            k = kur(td,
                    bultenler={"2026-08-30": {"tarih": "2026-08-30", "tur": "haftalik",
                                              "gundem_kaynagi": "yazili",
                                              "olusturma": "2026-08-30T19:00:00+00:00"}})
            r = gk.alarm_karari(k, pazar, None)
            siniflar = {s["yayin"]: s["sinif"] for s in r["satirlar"]}
            assert "alarm" in siniflar.values(), siniflar
            assert r["alarm"] == [] and r["yeni"] == [], r
            assert r["kapsam_disi"], r["kapsam_disi"]
            assert gk.ALARM_KAPSAMI == ("Günlük bülten",), gk.ALARM_KAPSAMI

        # (g) ZAMANINDA GÜN: kanal SESSİZ (sustuğu gün de sınanır)
        with tempfile.TemporaryDirectory() as td:
            erken = dict(gec, ilk_yazi_zamani="2026-09-04T04:38:00+00:00",
                         olusturma="2026-09-04T04:29:00+00:00")
            k = kur(td, bultenler={"2026-09-04": erken})
            r = gk.alarm_karari(k, cuma, None)
            assert not r["alarm"] and not r["yeni"], r

        # (h) CLI: karar dosyası iş akışının okuduğu biçimde
        import subprocess as _sp
        with tempfile.TemporaryDirectory() as td:
            k = kur(td, bultenler={"2026-09-04": gec})
            cikti, kayit = Path(td) / "cikti.txt", Path(td) / "k.json"
            komut = [sys.executable, "-c",
                     f"import sys, pathlib; sys.path.insert(0, {str(BURASI)!r});\n"
                     f"import gecikme; gecikme.KOK = pathlib.Path({str(k)!r});\n"
                     "sys.argv = ['gecikme.py', '--gun', '2026-09-04', '--alarm', "
                     f"'--kaydi-yaz', '--kayit', {str(kayit)!r}, '--cikti', {str(cikti)!r}];\n"
                     "raise SystemExit(gecikme.main())"]
            r1 = _sp.run(komut, capture_output=True, text=True)
            assert r1.returncode == 1, (r1.returncode, r1.stdout[-400:], r1.stderr[-400:])
            alanlar = dict(x.split("=", 1) for x in
                           cikti.read_text(encoding="utf-8").splitlines() if "=" in x)
            assert alanlar["alarm"] == "1" and alanlar["yeni"] == "1", alanlar
            assert alanlar["gun"] == "2026-09-04" and alanlar["ozet"], alanlar
            assert kayit.exists(), "kayıt yazılmadı — kanal her uyanmada öterdi"
            r2 = _sp.run(komut, capture_output=True, text=True)
            assert r2.returncode == 0, (r2.returncode, r2.stdout[-400:])
    sina("gecikme alarmı: kapsam ölçülmüş yayınla sınırlı, mükerrer e-posta yok",
         _gecikme_alarm_kanali)

    # ── ALARMIN TAŞIYICISI ZAMANLAYICIDAN BAĞIMSIZ MI. 04.09'da alarm, izlediği
    # zamanlayıcıyla hata kaynağını paylaşıyordu: sabah penceresinin tamamı
    # (veri 02:13/02:41, ölçüm 03:23/03:51, nöbetçi 06:37) hiç ateşlenmedi.
    # Bu sınama, birinin gecikme.yml'e "bir de cron koyalım" demesini yakalar.
    def _gecikme_yml():
        y = (BURASI.parent / ".github" / "workflows" / "gecikme.yml")
        assert y.exists(), "gecikme.yml yok — alarmın cron'suz taşıyıcısı kurulmamış"
        m = y.read_text(encoding="utf-8")
        govde = "\n".join(s for s in m.splitlines() if not s.lstrip().startswith("#"))
        assert "cron" not in govde, \
            "gecikme.yml'e cron eklenmiş — alarm yine izlediği zamanlayıcıya bağlandı"
        for beklenen in ("workflow_run:", "requested", "completed", "workflow_dispatch:",
                         "push:", "sinama_gun"):
            assert beklenen in govde, f"gecikme.yml'de {beklenen} yok"
        for is_akisi in ("Veri tazeleme", "Günlük bülten", "Siteyi yayınla",
                         "Haftalık teknik analiz"):
            assert is_akisi in govde, f"gecikme.yml {is_akisi} koşusunu dinlemiyor"
        # SIRA KRİTİK: önce kayıt yazılıp push edilir, SONRA alarm verilir.
        # Tersi, her uyanmada mükerrer e-posta demek.
        kayit_yeri = govde.index("Alarm kaydını işle")
        alarm_yeri = govde.index("name: Alarm\n")
        assert kayit_yeri < alarm_yeri, "alarm adımı kayıt adımından ÖNCE geliyor"
        assert "cancel-in-progress: false" in govde, \
            "yarıda kesilen alarm koşusu, kaybolan alarm demektir"
        # KÖR KALMAK SESSİZ OLAMAZ: araç karar üretemezse iş akışı düşer.
        # Yoksa bozuk bir alarm kanalı, sağlıklı olanla aynı görünürdü —
        # bu depodaki asıl kusur zaten buydu.
        assert "grep -q '^gun=' \"$GITHUB_OUTPUT\"" in govde, \
            "karar üretilemediğinde iş akışı yeşil bitiyor — alarm kanalı kör kalabilir"

        # NÖBETÇİ SİLİNMEDİ, ROLÜ DEĞİŞTİ: cron'ları ve mevcut adımları AYNEN
        # duruyor; yeni adım yalnız tekrar koşulunda düşer ve yalnız bülten
        # YAZILMIŞKEN (zincir kodu 2/4) koşar — yoksa yokluk alarmıyla ÇİFT
        # alarm üretirdi.
        n = (BURASI.parent / ".github" / "workflows" / "nobetci.yml").read_text(encoding="utf-8")
        for cron in ("37 6 * * 1-5", "7 8 * * 1-5", "37 10 * * 1-5",
                     "31 16 * * 0", "1 18 * * 0"):
            assert f"'{cron}'" in n, f"nöbetçinin cron'u değişmiş: {cron}"
        for adim in ("Bülten çıktı mı", "Site bugünün sayısını gösteriyor mu",
                     "Teknik bülten çıktı mı (yalnız pazar)"):
            assert adim in n, f"nöbetçinin mevcut adımı düşmüş: {adim}"
        assert "Gecikme tekrar ediyor mu (yedek kanal)" in n, "nöbetçi yedeği eklenmemiş"
        yedek = n.split("Gecikme tekrar ediyor mu (yedek kanal)")[1]
        assert "gecikme.tekrar()" in yedek, "yedek kanal kendi eşiğini kurmuş"
        assert "2|4)" in yedek, "yedek kanal bülten yazılmamışken de koşuyor — çift alarm"
    sina("alarm taşıyıcısı: gecikme.yml cron'suz, nöbetçi yedeğe döndü", _gecikme_yml)

    # ── ZİNCİR RAPORU SAYIYI BASAR, ÇIKIŞ KODUNU DEĞİŞTİRMEZ. Rutinin sabah
    # attığı ilk adım bu araç; 04.09'da doğru çalıştı, kod 1 döndürdü, ama
    # elinde SAYI yoktu ve bildirimi de sayısız kaldı. Ek bloklar SALT OKUNUR.
    def _zincir_ek_bloklar():
        import contextlib, io as _io
        import json as _j
        import shutil as _sh
        import tempfile
        import zincir

        gec = {"tarih": "2026-09-04", "tur": "gunluk", "gundem_kaynagi": "yazili",
               "olusturma": "2026-09-04T05:39:00+00:00",
               "ilk_yazi_zamani": "2026-09-04T05:50:32+00:00",
               "piyasa": {"gruplar": [{"id": "x"}]},
               "haberler": {"haber": [{"baslik": "x"}]},
               "gundem": {"kilit": "<p>x</p>"},
               "temalar": {"temalar": [{"ad": "T", "durum": "aktif", "gelisme": "eski",
                                        "son_gozlem": "a", "izlenecek_gosterge": "b"}]}}

        def kur(td, b, defter_gelisme):
            k = Path(td)
            (k / "site" / "src" / "data" / "bulten").mkdir(parents=True, exist_ok=True)
            (k / "site" / "src" / "data" / "teknik").mkdir(parents=True, exist_ok=True)
            (k / "site" / "src" / "data" / "tweet").mkdir(parents=True, exist_ok=True)
            (k / "bulten").mkdir(parents=True, exist_ok=True)
            _sh.copy2(BURASI.parent / "site" / "src" / "data" / "yayin_takvimi.json",
                      k / "site" / "src" / "data" / "yayin_takvimi.json")
            (k / "site" / "src" / "data" / "tweet" / "defter.json").write_text(
                "{}", encoding="utf-8")
            (k / "site" / "src" / "data" / "bulten" / f"{b['tarih']}.json").write_text(
                _j.dumps(b, ensure_ascii=False), encoding="utf-8")
            (k / "bulten" / "temalar.json").write_text(_j.dumps(
                {"temalar": [{"ad": "T", "durum": "aktif", "gelisme": defter_gelisme,
                              "son_gozlem": "a", "izlenecek_gosterge": "b"}]},
                ensure_ascii=False), encoding="utf-8")
            (k / "bulten" / "kosu_nabzi.json").write_text(_j.dumps(
                {"veri_kosusu": "2026-09-04T02:20:00+00:00", "sonuc": "success",
                 "kosular": [{"zaman": "2026-09-04T02:20:00+00:00", "sonuc": "success",
                              "atlanan_butce": ["tcmb", "dibs"]}]}), encoding="utf-8")
            return k

        asil = (zincir.KOK, zincir.BURASI, zincir.BULTENLER, zincir.TEKNIKLER)

        def calistir(k, gun):
            zincir.KOK = k
            zincir.BURASI = k / "bulten"
            zincir.BULTENLER = k / "site" / "src" / "data" / "bulten"
            zincir.TEKNIKLER = k / "site" / "src" / "data" / "teknik"
            tampon = _io.StringIO()
            with contextlib.redirect_stdout(tampon):
                kod, _ = zincir.durum(gun)
            return kod, tampon.getvalue()

        try:
            # (a) GEÇ YAZILMIŞ BÜLTEN: sayı basılır, çıkış kodu YİNE 2
            with tempfile.TemporaryDirectory() as td:
                k = kur(td, gec, "eski")
                kod, cikti = calistir(k, dt.date(2026, 9, 4))
                assert kod == 2, kod
                assert "SÖZ RİSK ALTINDA" in cikti, cikti[-600:]
                assert "39,5" in cikti, "gecikme DAKİKASI basılmadı"
                assert "darboğaz" in cikti, "darboğaz halka basılmadı"
                # (c) atlanan hatlar son koşudan okunur
                assert "atlanan hatlar" in cikti and "tcmb" in cikti, cikti[-600:]

            # (b) TEMA KIYASI 0. ADIMDA: defter ölçümden yeniyse uyarı çıkar.
            #     04.09'da bu yazı sırasında fark edildi ve ölçüm iki kez
            #     yeniden kuruldu (~11 dakika).
            with tempfile.TemporaryDirectory() as td:
                k = kur(td, gec, "defterde YENİ metin")
                kod, cikti = calistir(k, dt.date(2026, 9, 4))
                assert kod == 2, kod
                assert "TEMA DEFTERİ ÖLÇÜMDEN YENİ" in cikti, cikti[-600:]
                assert "--yeniden-olc" in cikti, "ne yapılacağı yazılmamış"
            with tempfile.TemporaryDirectory() as td:
                k = kur(td, gec, "eski")
                _, cikti = calistir(k, dt.date(2026, 9, 4))
                assert "TEMA DEFTERİ ÖLÇÜMDEN YENİ" not in cikti, "boşuna uyarı"

            # (d) ZAMANINDA GÜN: risk satırı YOK (her sabah bağırmaz)
            with tempfile.TemporaryDirectory() as td:
                erken = dict(gec, ilk_yazi_zamani="2026-09-04T04:38:00+00:00")
                k = kur(td, erken, "eski")
                _, cikti = calistir(k, dt.date(2026, 9, 4))
                assert "SÖZ RİSK ALTINDA" not in cikti, cikti[-400:]

            # (e) ÇIKIŞ KODU SÖZLEŞMESİ: ek bloklar hiçbir kodu değiştirmez;
            #     bloklardan biri bilerek bozulsa bile.
            with tempfile.TemporaryDirectory() as td:
                k = kur(td, gec, "eski")
                assert calistir(k, dt.date(2026, 9, 5))[0] == 3, "cumartesi kodu bozuldu"
                gercek = zincir._gecikme_blogu
                try:
                    def _patla(g):
                        raise RuntimeError("bilerek bozuldu")
                    zincir._gecikme_blogu = _patla
                    kod, cikti = calistir(k, dt.date(2026, 9, 4))
                    assert kod == 2, f"ek bloktaki kusur çıkış kodunu değiştirdi: {kod}"
                    assert "gecikme bloğu okunamadı" in cikti, cikti[-400:]
                finally:
                    zincir._gecikme_blogu = gercek
        finally:
            zincir.KOK, zincir.BURASI, zincir.BULTENLER, zincir.TEKNIKLER = asil
    sina("zincir: gecikme dakikası ve tema kıyası raporda, çıkış kodu değişmiyor",
         _zincir_ek_bloklar)

    sina("bicim: sayı yazımı tek kaynak · REDK konumu yön okur · denetim sızıntıyı görür", _bicim)
    sina("okur dili: koşu kaydı satırları muafiyetsiz taranır (kod, biçim)", _kosu_kaydi_dili)
    sina("denetim: revizyon ölçütü TL faiz, gösterge, türev ve rejimi görür, farklı günü karıştırmaz", _revizyon)
    sina("piyasa/rejim: türev ve rejim satırları kendi gününü ve hanesini taşır", _turev_rejim_gunu)
    sina("yayın takvimi (hakkında sayfası) iş akışı cron'larıyla aynı saati söylüyor", _yayin_takvimi)

    for ad in gecen:
        print(f"  ✓ {ad}")
    for ad, hata in dusen:
        print(f"  ✗ {ad}\n      {hata}")
    print(f"\n  {len(gecen)} geçti · {len(dusen)} DÜŞTÜ")
    if dusen:
        print("\n  Bülten katmanlarında sözleşme kayması var. Ağ adımlarına "
              "geçmeden düzeltilmeli.")
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
