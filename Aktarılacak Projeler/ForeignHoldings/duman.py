#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yabancı pozisyonu (DİBS · hisse net işlem) — duman sınaması. Ağa çıkmaz.

`guncelle.py` bu dosyayı hattın ADIMLARINDAN ÖNCE koşturur ve düşerse hat hiç
koşmaz, siteye kopyalama olmaz. Sınama `--denetle` yazan birinin eline
bırakılmaz: zamanlanmış koşu `--denetle` demez ve bozuk bir özet katmanı
çıktısını siteye kopyalamış olurdu.

BURADAKİ HER MADDE BİR ARIZAYA KARŞILIK GELİR. Bir iddia ya bu depoda
gerçekten yanlış yayımlanmış bir sayıyı, ya yayını durdurmuş bir yanlış alarmı,
ya da bu hattın kodunda adı konmuş bir tuzağını kapatır — bir sigortanın hangi
arızaya karşı çalıştığı konduğu gün yazılmazsa, sonraki oturum onu her arızaya
karşı sanır.

ÇERÇEVE SENTETİKTİR VE DEPODAKİ ozet.json'u OKUMAZ. Sebebi ölçülmüş bir tuzak:
deponun o günkü çıktısını okuyan bir sınama, o çıktı bozukken düşer ve bozukluğu
temizleyecek koşuyu da başlatamaz. Çerçeve hattın GERÇEK yolundan geçer
(data_processor → ozet_uret), çünkü sınanan şeylerin bir kısmı tam o
dönüşümlerde doğuyor.

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import ast
import inspect
import re
import sys
from pathlib import Path

import pandas as pd

import ozet_uret
from data_processor import calculate_cumulative, process_data

KOK = Path(__file__).resolve().parents[2]
KLASOR = Path(__file__).resolve().parent
SLUG = "yabanci-pozisyon"

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


# ---------------------------------------------------------------------------
# SENTETİK ÇERÇEVE — haftalık(Cuma), serinin gerçek başlangıcından bugüne
# ---------------------------------------------------------------------------
BAS, SON = "2020-09-11", "2026-08-28"
_t = pd.date_range(BAS, SON, freq="W-FRI")
# ÇERÇEVE ZİRVE-SONRASI ÇEKİLME TAŞIR: son yirmi haftada DİBS akımı sert
# eksiye döner, yani kümülatif toplamın ZİRVESİ son gözlem DEĞİLDİR. Şart
# bilerek konuldu — düz artan bir çerçevede "ana saat son gözlemdir" ölçütü
# zirve tarihiyle çakışır ve `_tarih`i zirveden alan bir kusur SESSİZCE geçer
# (arıza enjeksiyonuyla ölçüldü: mutasyon arızayı üretmiyordu).
_son20 = len(_t) - 20
_ham = pd.DataFrame({
    "Tarih": _t,
    # Akımlar uydurma ama İŞARETLİ ve toplanabilir: kümülatif, YTD ve zirve
    # hesaplarının hepsi bu iki sütundan türüyor.
    "Hisse": [round(-40 + (i % 7) * 13.5, 2) for i in range(len(_t))],
    "DIBS": [round(120 - (i % 11) * 21.25, 2) if i < _son20 else -430.0
             for i in range(len(_t))],
})
DF = calculate_cumulative(process_data(_ham))
BUGUN = pd.Timestamp("2026-09-03")          # son gözlemden 6 gün sonra
O = ozet_uret.ozet_kur(DF, BUGUN)

print("\n── Sayfa sözleşmesi ─────────────────────────────────────────────────")

# (1) SAYFANIN ADIYLA ÇAĞIRDIĞI HER ANAHTAR ÖZETTE VAR.
# 08.09.2026'da ölçüldü: bir hat sayfanın çağırdığı anahtarı ATLAYINCA yayın
# kapısı ENGEL verdi ve site üç kez donuk kaldı. Soru hattın kendi koşusunda
# sorulur, yayın kapısında değil.
_kalip = re.compile(r'<Deger\s+proje="' + re.escape(SLUG) + r'"\s+anahtar="([^"]+)"')
_cagrilan: set[str] = set()
for _p in (KOK / "site" / "src" / "content").rglob("*.mdx"):
    _cagrilan |= set(_kalip.findall(_p.read_text(encoding="utf-8")))
_eksik = sorted(a for a in _cagrilan if a not in O)
sina("sayfaların çağırdığı her anahtar özette var",
     not _eksik and bool(_cagrilan),
     f"{len(_cagrilan)} çağrı · eksik: {_eksik}")

# (2) KOŞU ANINDA DONAN ÖZ-BİLDİRİM SAYFA SÖZLEŞMESİNDE DEĞİL.
# 09.09.2026'da ölçüldü: sayfa "(bugüne göre 6 gün gecikme, durum: güncel)"
# basıyordu; o 6, 03.09 koşusunda ölçülüp dosyaya DONMUŞ bir sayıydı ve verinin
# o günkü gerçek yaşı 12 gündü. Donmuş bir alan bugün hakkında konuşamaz.
_mdx = (KOK / "site" / "src" / "content" / "projeler" / f"{SLUG}.mdx").read_text(encoding="utf-8")
_yasak = sorted(a for a in ("gecikme_gun", "kosu_gecikme_gun", "tazelik") if a in _cagrilan)
sina("koşu-anı öz-bildirimi sayfada ÇAĞRILMIYOR (gecikme · tazelik)",
     not _yasak, f"sayfa hâlâ çağırıyor: {_yasak}")
sina("sayfa metninde 'bugüne göre … gün gecikme' cümlesi YOK",
     not re.search(r"bugüne göre[^.]{0,80}gecikme", _mdx),
     "donmuş bir sayı 'bugüne göre' diye basılıyor")

# (3) ALAN ADI KOŞU-ANI ANLAMINI TAŞIR. Adı `gecikme_gun` olan bir alan,
# okuyanı "verinin gecikmesi" diye anlamaya davet eder; ölçtüğü şey KOŞU
# ANINDAKİ yaştır. Ad sözleşmenin parçası.
sina("gecikme alanı koşu-anı adıyla yazılıyor (kosu_gecikme_gun)",
     "kosu_gecikme_gun" in O and "gecikme_gun" not in O,
     f"{[k for k in O if 'gecikme' in k]}")

print("\n── Tazelik ölçüsü ───────────────────────────────────────────────────")

# (4) HÜKÜM GERÇEKTEN KOŞU ANINA BAĞLI. Aynı son gözlem iki farklı "bugün" ile
# sorulduğunda hüküm DEĞİŞMELİ; değişmiyorsa alan donmuş bir bayraktır ve
# tolerans hiç uygulanmıyordur.
_son = DF["Tarih"].iloc[-1]
_tol = ozet_uret.TAZELIK_ESIGI_GUN
_g_ic, _h_ic = ozet_uret.tazelik_hukmu(_son, _son + pd.Timedelta(days=_tol))
_g_dis, _h_dis = ozet_uret.tazelik_hukmu(_son, _son + pd.Timedelta(days=_tol + 1))
sina("tazelik hükmü koşu anına bağlı: tolerans içinde güncel, bir gün sonrası bayat",
     (_g_ic, _h_ic, _g_dis, _h_dis) == (_tol, "güncel", _tol + 1, "bayat"),
     f"{_g_ic}:{_h_ic} · {_g_dis}:{_h_dis}")

# (5) YAYIMLANAN TOLERANS, UYGULANAN TOLERANSTIR. İki ayrı sayı bir gün sessizce
# ayrışır; sayfa şeridi hükmü okur, tolerans onun tek doğrulanabilir dayanağı.
# Anahtarlar `get` ile okunur: adı değişmiş bir alan burada ÇÖKMEZ, RAPOR
# olur — çöken bir sınama geri kalan maddeleri hiç koşturmaz ve tek bir
# yeniden adlandırma bütün sayfayı kör eder.
sina("özetteki tolerans ile hükmü kuran eşik AYNI ve özdeşlik tutuyor",
     O.get("bayat_tolerans_gun") == _tol
     and (O.get("kosu_gecikme_gun", -1) <= _tol) == (O.get("tazelik") == "güncel"),
     f"{O.get('kosu_gecikme_gun')} · {O.get('bayat_tolerans_gun')} · {O.get('tazelik')}")

# (6) YAPISAL KİLİT — saat `ozet_kur`un İÇİNDEN okunmaz, argümanla girer.
# Saat gövdeye geri taşınırsa hüküm bir daha uydurma bir "bugün" ile
# sınanamaz ve yukarıdaki iki madde sessizce anlamsızlaşır.
_govde = inspect.getsource(ozet_uret.ozet_kur) + inspect.getsource(ozet_uret.tazelik_hukmu)
sina("ozet_kur/tazelik_hukmu saati KENDİ okumuyor (bugun argümandan gelir)",
     "today(" not in _govde and "now(" not in _govde,
     "gövdede doğrudan saat okuması var")

print("\n── Saat yazımı ──────────────────────────────────────────────────────")

# (7) HAFTALIK BACAK GÜNLÜK YAZILIR (GG.AA.YYYY). ISO ("2026-08-28") ve Türkçe
# ay adı SAAT anahtarında yasak; hattın bütün bacakları haftalık(Cuma) olduğu
# için gün YAZILABİLİR ve yazılmalıdır.
_gun = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
for _a in ("_tarih", "son_hafta", "baslangic", "kum_zirve_tarih"):
    sina(f"{_a} GG.AA.YYYY yazımında ve çözülüyor",
         isinstance(O.get(_a), str) and bool(_gun.match(O[_a]))
         and pd.notna(pd.to_datetime(O[_a], format="%d.%m.%Y", errors="coerce")),
         repr(O.get(_a)))

# (8) ANA SAAT SON GÖZLEMDİR. `_tarih` bir başka bacaktan (ör. zirve tarihi)
# gelirse pano tazeyken bayat, bayatken taze görünür.
sina("_tarih = son_hafta = serinin son gözlemi",
     O["_tarih"] == O["son_hafta"] == _son.strftime("%d.%m.%Y"),
     f"{O['_tarih']} · {O['son_hafta']} · {_son:%d.%m.%Y}")

# (9) YIL BİR SAYI DEĞİL ETİKETTİR: sayı olarak yazılırsa sayfanın biçim
# sözleşmesi onu binlik ayracıyla "2.026" diye basar.
sina("yil ETİKET olarak yazılıyor (metin)",
     isinstance(O["yil"], str) and O["yil"] == "2026", repr(O["yil"]))

print("\n── Hesap sözleşmesi ─────────────────────────────────────────────────")

# (10) SAYFADA YAN YANA BASILAN ÜÇLÜ KÂĞIT ÜSTÜNDE TOPLANIR. Toplamı ham
# veriden ayrıca yuvarlamak sayfada toplanmayan üçlüler üretiyordu
# (39 + 806 = 845 iken toplam 844 basılıyordu).
for _ad in ("hafta", "4h", "13h", "ytd", "ytd_gecen", "kum"):
    sina(f"{_ad}: toplam = hisse + dibs (basılan sayılarla)",
         O[f"toplam_{_ad}"] == O[f"hisse_{_ad}"] + O[f"dibs_{_ad}"],
         f"{O[f'hisse_{_ad}']} + {O[f'dibs_{_ad}']} ≠ {O[f'toplam_{_ad}']}")

# (11) YTD EKSENİ "YILIN KAÇINCI CUMA'SI"DIR, ISO 8601 HAFTASI DEĞİL.
# 01.01.2021 Cuma'sının ISO numarası 2020'ye ait 53'tür; ISO ile çizilince
# 2021 çizgisi grafiğin sağ ucundan başlıyor ve yılın tamamı bir hafta kayıyordu.
_oc = process_data(pd.DataFrame({"Tarih": pd.to_datetime(["2021-01-01", "2021-01-08"]),
                                 "Hisse": [1.0, 1.0], "DIBS": [1.0, 1.0]}))
sina("hafta numarası yılın ilk Cuma'sından sayılıyor (ISO 53 değil)",
     list(_oc["Week"]) == [1, 2], f"{list(_oc['Week'])}")

# (12) GEÇEN YIL KIYASI AYNI HAFTA NUMARASINA KADAR. Bütün yıl toplanırsa
# YTD karşılaştırması yılın ilerlemesiyle sistematik olarak bozulur.
_gecen_tam = float(DF[DF["Year"] == 2025]["DIBS"].sum())
sina("ytd_gecen yılın TAMAMI değil, aynı hafta numarasına kadarki toplam",
     O["dibs_ytd_gecen"] != round(_gecen_tam),
     f"{O['dibs_ytd_gecen']} = tam yıl {round(_gecen_tam)}")

print("\n── Kopya sözleşmesi ─────────────────────────────────────────────────")


def _hat_kopya() -> dict[str, str]:
    """guncelle.py kütüğündeki bu hattın kopya sözlüğü — kaynaktan, çalıştırmadan."""
    agac = ast.parse((KOK / "guncelle.py").read_text(encoding="utf-8"))
    for d in ast.walk(agac):
        if (isinstance(d, ast.Call) and getattr(d.func, "id", "") == "Hat"
                and d.args and getattr(d.args[0], "value", None) == "yabanci"):
            return {k.value: v.value for k, v in zip(d.args[6].keys, d.args[6].values)}
    return {}


def _cizilen() -> set[str]:
    """visualizer.py'nin GERÇEKTEN yazdığı dosyalar — kaynaktan."""
    kaynak = (KLASOR / "visualizer.py").read_text(encoding="utf-8")
    agac = ast.parse(kaynak)
    adlar: set[str] = set()
    for d in ast.walk(agac):
        if (isinstance(d, ast.Assign) and getattr(d.targets[0], "id", "") == "categories"):
            adlar |= {e.elts[0].value.lower() for e in d.value.elts}
    return ({f"charts/ytd_{a}.html" for a in adlar}
            | ({"charts/cumulative_chart.html"} if '"cumulative_chart.html"' in kaynak
               else set()))


# 27.08.2026'da bir başka hatta ölçüldü: bir kipin ÜRETEMEDİĞİ dosya kopya
# sözleşmesinde durunca kopyalama tam o noktada kesiliyor ve sözlükte ondan
# SONRA gelen dosyalar (ozet.json dahil) siteye hiç gitmiyordu — grafikler
# tazeleniyor, sayfanın sayıları donuyordu. Bu hattın tek kipi var ve dört
# figürünü de main.py çiziyor; sözleşme ile üretim birebir örtüşmeli.
_kopya, _uretilen = _hat_kopya(), _cizilen()
sina("kütükteki kopya sözleşmesi = çizimin ürettiği dosya kümesi",
     set(_kopya) == _uretilen and len(_kopya) == 4,
     f"sözleşme {sorted(_kopya)} · üretim {sorted(_uretilen)}")
sina("kopyalanan her figürün hedefi sayfada gömülü",
     all(f'src="/projeler/{SLUG}/{h}"' in _mdx for h in _kopya.values()),
     f"{[h for h in _kopya.values() if f'src=/projeler/{SLUG}/{h}' not in _mdx]}")

# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
