#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reel sektör döviz pozisyonu — duman sınaması. Ağa çıkmaz, saniyeler sürer.

`guncelle.py` bu dosyayı hattın ADIMLARINDAN ÖNCE koşturur ve düşerse hat hiç
koşmaz, siteye kopyalama olmaz. Sınama `--denetle` yazan birinin eline
bırakılmaz: zamanlanmış koşu `--denetle` demez ve bozuk bir ölçüm katmanı
çıktısını siteye kopyalamış olurdu.

BURADAKİ HER MADDE BİR ARIZAYA KARŞILIK GELİR — her bloğun başında hangi
arızaya karşı çalıştığı yazılı. Bir sigortanın hangi arızaya karşı konduğu o
gün yazılmazsa, sonraki oturum onu her arızaya karşı sanır.

Çerçeve SENTETİKTİR ve depodaki o günkü veriyi OKUMAZ: kapı deponun bugünkü
dosyasına bakarsa, bugün tesadüfen temiz olan bir kusuru "yok" sayar ve yarın
veri değiştiğinde sessizce yanlış alarma döner.

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pandas as pd

import hesap

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
MDX = KOK / "site" / "src" / "content" / "projeler" / "reel-sektor-fx.mdx"

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}"
          + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def _ortak(ad: str):
    """`ortak/` modülünü içe aktarır (elle koşuda PYTHONPATH kurulmaz)."""
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(KOK / "ortak"))
        return __import__(ad)


okur_dili = _ortak("okur_dili")
# Sınama, sınananla AYNI tarih sözleşmesinden okur: ikinci bir ayrıştırıcı
# yazmak, bir gün sessizce ayrışacak ikinci bir tanım demek olurdu.
bicim = _ortak("bicim")


def cerceve(aylar: int = 30, bozuk: bool = False) -> pd.DataFrame:
    """Sentetik aylık tablo. `bozuk`: özdeşliği kıran bir kolon kayması."""
    idx = pd.date_range("2024-01-01", periods=aylar, freq="MS")
    varlik = pd.Series(range(180_000, 180_000 + aylar * 300, 300)[:aylar], index=idx, dtype=float)
    yukumluluk = pd.Series(range(380_000, 380_000 + aylar * 500, 500)[:aylar], index=idx, dtype=float)
    kv_varlik = varlik * 0.8
    kv_yuk = yukumluluk * 0.37
    d = pd.DataFrame({"varlik_toplam": varlik, "yukumluluk_toplam": yukumluluk,
                      "net_pozisyon": varlik - yukumluluk,
                      "kv_varlik": kv_varlik, "kv_yukumluluk": kv_yuk,
                      "kv_net": kv_varlik - kv_yuk})
    d.index.name = "tarih"
    if bozuk:
        d["net_pozisyon"] = d["net_pozisyon"] + 4_000     # 4 milyar dolar kayma
    return d


REZ = {"h_brut": 188.6, "h_tarih": "28.08.2026", "_tarih": "07.09.2026"}
D = cerceve()
O = hesap.ozetle(D, REZ)


# ── 1. OKUR DİLİ ────────────────────────────────────────────────────────────
# ARIZA: `_aciklama` alanı hattın dosya adını ve yapım ortamını anlatıyordu
# ("… veri_cek.py başarıyla koşunca …"). 09.09.2026'da ölçüldü:
# okur_dili.kosu_kaydi_tara o cümlede iki bulgu veriyordu ve biri ENGEL
# sınıfındaydı (kod dili). Alan yalnız VERİ YOKKEN yazıldığı için kusur o gün
# tetiklenmiyordu — yani ilk boş çekimde yayını durduracak bir mayındı.
# ozet.json'un cümle olan her metin alanı sayfaya OLDUĞU GİBİ basılır.
for _ad, _metin in okur_dili.ozet_cumleleri(hesap.bekliyor_ozet()):
    _b = okur_dili.kosu_kaydi_tara([_metin])
    sina(f"bekliyor özeti okur dilinde ({_ad})", not _b, f"{_b}")
for _ad, _metin in okur_dili.ozet_cumleleri(O):
    _b = okur_dili.kosu_kaydi_tara([_metin])
    sina(f"özet cümlesi okur dilinde ({_ad})", not _b, f"{_b}")


# ── 2. SAYFANIN ÇAĞIRDIĞI ANAHTAR HER KOŞUDA YAZILIR ────────────────────────
# ARIZA (08.09.2026, DİBS): sayfa bir anahtarı adıyla çağırıyordu, ölçüm
# katmanı ölçemediği gün onu ATLIYORDU ve yayın kapısı eksik anahtarı ENGEL
# saydı — günün bülteni saatlerce çıkmadı. Aynı sınıf burada rezerve oranda
# duruyordu: TCMB özeti okunamazsa anahtar hiç yazılmıyor, sayfa MDX'teki
# statik yedeği (geçmiş bir ayın sayısı) canlı gibi gösteriyordu.
# KAPSAM SÖZLEŞMEDEN TÜRETİLİR, elle liste tutulmaz: sayfanın bu projeden
# çağırdığı her anahtar okunur.
_cagrilan = sorted(set(re.findall(
    r'<Deger\s+proje="reel-sektor-fx"\s+anahtar="([^"]+)"', MDX.read_text(encoding="utf-8"))))
_eksik = [a for a in _cagrilan if a not in O]
sina(f"sayfanın çağırdığı {len(_cagrilan)} anahtarın hepsi özette",
     not _eksik and len(_cagrilan) >= 7, f"eksik: {_eksik}")

_bos = hesap.ozetle(D, None)          # TCMB özeti okunamadı
_eksik_bos = [a for a in _cagrilan if a not in _bos]
sina("rezerv özeti YOKKEN de sayfanın anahtarları yazılıyor",
     not _eksik_bos, f"eksik: {_eksik_bos}")
# `.get` bilerek: anahtar hiç yazılmadığında bu satır KeyError ile ÇÖKMEMELİ.
# Arıza enjeksiyonunda tam olarak bu oldu ve raporun geri kalanı hiç
# koşmadı — düşen bir sınamanın geri kalanı da görünmeli, yoksa tek arıza
# ötekileri gizler.
sina("ölçülemeyen oran sayı değil, ölçülemedi işaretiyle yazılıyor",
     _bos.get("acik_rezerv_orani") == hesap.OLCULEMEDI
     and _bos.get("acik_rezerv_orani_tarih") == hesap.OLCULEMEDI,
     f"{_bos.get('acik_rezerv_orani')!r} · {_bos.get('acik_rezerv_orani_tarih')!r}")


# ── 3. ORANIN İKİ PARÇALI DAMGASI ───────────────────────────────────────────
# ARIZA: oranın kendi saati YOKTU. Bileşen sırayla `<anahtar>_tarih` → `_tarih`
# der; oran için ilki bulunmayınca hattın AYLIK ana saati basılıyordu ve okur
# haftalık paydayı da o ayın ölçümü sanıyordu. Ters yazım da yanlış olurdu:
# haftalık günü yazmak aylık payı iki ay taze gösterirdi. Sözleşme (CLAUDE.md)
# bu hâl için iki parçalı damgayı tarif ediyor.
_damga = str(O.get("acik_rezerv_orani_tarih", ""))
sina("oranın kendi saati var ve iki bacağı da adıyla yazıyor",
     "aylık" in _damga and "haftalık" in _damga
     and O["net_pozisyon_tarih"] in _damga and REZ["h_tarih"] in _damga, _damga)
# YAPISAL KİLİT: damga TEK BİR GÜNE ÇÖZÜLMEMELİ. Çözülseydi bileşen ve denetim
# onu bir ölçüm gününe demirler, yani iki bacaktan biri hakkında yanıltırdı;
# aynı ayrıştırıcı sayfa tarafında da (lib/bicim) kullanılıyor.
sina("iki parçalı damga tek bir güne ÇÖZÜLMÜYOR",
     bool(_damga) and bicim.tarihe_cevir(_damga) is None,
     str(bicim.tarihe_cevir(_damga)))
# Rezerv bacağının KENDİ saati ayrı anahtarda kalır: bültenin tazelik denetimi
# (ayar.RITIM_ALAN) onu adıyla izliyor, iki parçalı damgayı ayrıştıramaz.
sina("rezerv bacağının kendi saati ayrı anahtarda duruyor",
     O.get("acik_rezerv_tarih") == REZ["h_tarih"]
     and bicim.tarihe_cevir(O.get("acik_rezerv_tarih")) is not None,
     O.get("acik_rezerv_tarih"))


# ── 4. AYLIK SAAT GÜN YAZMAZ ────────────────────────────────────────────────
# ARIZA SINIFI: aylık bir gözlemi gün gibi yazmak ("01.06.2026") okura O GÜNÜN
# ölçümü gibi görünür. Sözleşme aylık saatleri AA.YYYY yazar; bu hatta bütün
# ana saatler aylıktır.
_aylik = [k for k in O if k.endswith("_tarih") and k != "acik_rezerv_tarih"
          and k != "acik_rezerv_orani_tarih"]
_kusur = [(k, O[k]) for k in _aylik if not re.fullmatch(r"\d{2}\.\d{4}", str(O[k]))]
sina(f"{len(_aylik)} aylık saatin hepsi AA.YYYY yazımında", not _kusur, f"{_kusur}")
sina("hattın ana saati net pozisyonun ayı",
     O["_tarih"] == O["net_pozisyon_tarih"], f"{O['_tarih']} ≠ {O['net_pozisyon_tarih']}")


# ── 5. EŞLEME ÖZDEŞLİĞİ HÂLÂ KAPI ───────────────────────────────────────────
# ARIZA: seri kolonları TCMB'nin seri ADINA göre eşleniyor; kalıp bir gün başka
# bir seriyi yakalarsa hat sessizce yanlış büyüklüğü okur. Tablonun kendi
# muhasebe kimliği bunu ölçer ve eşik aşılırsa hat DURUR. Ölçüm ayrı bir
# fonksiyona taşınırken bu kapının düşmesi en sessiz gerileme olurdu.
try:
    hesap.ozetle(cerceve(bozuk=True), REZ)
    _durdu = False
except SystemExit:
    _durdu = True
sina("özdeşlik bozulunca hat DURUYOR (yanlış kolonla sayfa üretilmiyor)", _durdu)
sina("temiz çerçevede özdeşlik ölçüsü yazılıyor",
     O.get("kimlik", {}).get("net", {}).get("maks_fark_mn") == 0.0
     and O.get("kimlik", {}).get("net", {}).get("n") == len(D),
     str(O.get("kimlik")))


# ── 6. BOŞ TABLO "VERİ VAR" DEĞİLDİR ────────────────────────────────────────
# ARIZA (26.08.2026): veri çekme katmanı yalnız BAŞLIK satırından ibaret bir
# CSV yazdı; hesap katmanı dosyanın varlığını veri sanıp `_tarih: ""` olan bir
# özet üretti — sayfa veri varmış gibi göründü ama hiçbir sayı yoktu.
_bos_cerceve = cerceve().iloc[0:0]
_ob = hesap.ozetle(_bos_cerceve, REZ)
sina("boş tablodan sayı üretilmiyor",
     "net_pozisyon" not in _ob and _ob.get("_tarih") == ""
     and _ob.get("acik_rezerv_orani") == hesap.OLCULEMEDI, str(_ob)[:120])


# ── 7. AĞA ÇIKAN İŞ HESAP KATMANINDA DURMAZ ─────────────────────────────────
# YAPISAL KİLİT: bu dosyanın sınayabildiği her şey ağsız olduğu için sınanıyor.
# Hesap katmanına bir gün ağ çağrısı girerse duman sınaması sessizce ağa çıkan
# bir kapıya döner ve zamanlanmış koşuyu ağ arızasında düşürür.
# Ölçü METİN TARAMASI DEĞİL, İÇE AKTARMA LİSTESİDİR: ilk yazımda kaynakta
# "evds" ve "http" aranıyordu ve arıza enjeksiyonu bunun yanlış alarmını
# gösterdi — yorumda geçen bir kaynak adı ("EVDS'ten çekilir") ağ çağrısı
# değildir ve bu kapı hattın ÖNÜNDE duruyor: yanlış alarmı hattı hiç
# koşturmaz. Ağ ancak bir modülle açılır; ölçüt onu sorar (fonksiyon
# içindeki gecikmeli içe aktarmalar dahil).
AG_MODULLERI = {"requests", "urllib", "http", "socket", "httpx", "aiohttp",
                "yfinance", "ftplib"}
_agac = ast.parse((BURASI / "hesap.py").read_text(encoding="utf-8"))
_iceri: set[str] = set()
for _d in ast.walk(_agac):
    if isinstance(_d, ast.Import):
        _iceri |= {a.name.split(".")[0] for a in _d.names}
    elif isinstance(_d, ast.ImportFrom) and _d.module:
        _iceri.add(_d.module.split(".")[0])
_ag = sorted(_iceri & AG_MODULLERI)
sina("hesap katmanı ağa çıkmıyor (ağ modülü içe aktarmıyor)", not _ag, f"içe aktarılan: {_ag}")


# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d_ in DUSTU:
        print(f"  ✗ {d_}")
    sys.exit(1)
print("  Duman sınaması temiz.")
