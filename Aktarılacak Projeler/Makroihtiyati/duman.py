# -*- coding: utf-8 -*-
"""Makroihtiyati hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer, 0/1 döner.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur ve düşerse hat hiç
koşmaz. Hat türevdir (Kredi + Fonlama depo serileri), ağa zaten çıkmaz; sınama
gerçek dosyalarla koşar.

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR (09.09.2026'da ölçülenler)
--------------------------------------------------------------------------
 1. ÜÇ AYLIK SAAT — eğilim anketi çeyreğin İLK gününe damgalanıyordu ve sayfa
    "01.04.2026" basıyordu; okur 161 günlük bir yaş okuyordu, oysa anketin
    ölçtüğü çeyrek 30.06'da bitiyor (yaş 71 gün). Sözleşme: üç aylık saat
    çeyreğin SON AYI (AA.YYYY); çeyreğin adı bir ölçü değil ETİKETTİR ve ayrı
    anahtarda durur. Çeyrek kapanmadan saat yazılmaz (kapanmamış ayın son günü
    yarına düşer ve yayın kapısı onu haklı olarak engel sayar).
 2. BAYAT İŞARETİ — sayfadaki anket değerleri KALICI olarak bayat (°)
    işaretleniyordu: bileşenin öntanımlı eşiği 45 gün, üç aylık bir bacak ise
    tanımı gereği bundan uzun susar. Eşik sayfada açıkça yazılır ve KREDİ
    hattının kendi ölçtüğü toleranstan (110 gün, dönem sonundan sayılır)
    gelir; kapanamayan bir uyarı, okuru bütün uyarıları görmezden gelmeye
    alıştırır.
 3. BAYATLIK HÜKMÜ — özet `bayat` da `tazelik` de yazmıyordu, sayfanın veri
    durumu şeridi "bayatlık ölçülmüyor" basıyordu; oysa aynı serilerin
    tazeliği kredi hattında zaten ölçülüyor. Hüküm üç hâlli: ölçülemiyorsa
    yazılmaz (ölçmemişken "taze" demek, ölçmüş gibi davranmaktır).
 4. SAYFA SÖZLEŞMESİ — sayfanın adıyla çağırdığı her anahtar özette var;
    gömülü her figür şekil saat defterinde ve kopya sözleşmesinde.
 5. OKUR DİLİ — özetin cümle alanları sayfaya olduğu gibi basılır.
 6. YAPISAL KİLİT — defterde olmayan figür yazılamaz; `if __name__` kapısının
    altında tanım yok (kapının altına yazılan bir tanım betik koşarken
    NameError verir, içe aktarmada vermez).

Koşum:  python3 duman.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import pandas as pd

BURASI = pathlib.Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))

import hesap                                                       # noqa: E402
import grafik                                                      # noqa: E402

GECTI, DUSTU = 0, 0
_KUSUR: list[str] = []
_CACHE: dict = {}

GUN_RX = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
AY_RX = re.compile(r"^\d{2}\.\d{4}$")
# Deger.astro'nun TARIHSEL kalıbının eşi: tarih taşıyan ama tazelik saati
# OLMAYAN anahtarlar (bir zirvenin donuk olması normaldir).
TARIHSEL_RX = re.compile(r"(^|_)(maks|min|zirve|dip|cipa|bas|baslangic|rekor|referans)(_|$)")
MDX = KOK / "site" / "src" / "content" / "projeler" / "makroihtiyati.mdx"
SLUG = "makroihtiyati"


def _ortak(ad: str):
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(KOK / "ortak"))
        return __import__(ad)


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    global GECTI, DUSTU
    if kosul:
        GECTI += 1
        print(f"  ✓ {ad}")
    else:
        DUSTU += 1
        _KUSUR.append(ad)
        print(f"  ✗ {ad}" + (f"\n      {ayrinti}" if ayrinti else ""))


def _hesap():
    if "h" not in _CACHE:
        _CACHE["h"] = hesap.hesapla()
    return _CACHE["h"]


def _mdx() -> str:
    return MDX.read_text(encoding="utf-8") if MDX.exists() else ""


# ── 1. üç aylık saat ─────────────────────────────────────────────────────────
def bolum_ceyrek() -> None:
    print("\n▶ Üç aylık saat (çeyreğin SON ayı)")
    *_, o = _hesap()
    b = _ortak("bicim")
    saat, etiket = hesap.ceyrek_saati("2026-04-01", bugun="2026-09-09")
    sina("2. çeyrek anketi çeyreğin son ayıyla damgalanıyor", saat == "06.2026", saat)
    sina("çeyreğin adı ayrı anahtarda ve etiket biçiminde", etiket == "2026-Ç2", etiket)
    sina("4. çeyrek yıl sonuna demirleniyor",
         hesap.ceyrek_saati("2025-10-01", bugun="2026-09-09") == ("12.2025", "2025-Ç4"))
    sina("kapanmamış çeyrek için saat yazılmıyor (ileri tarih ilan edilmez)",
         hesap.ceyrek_saati("2026-07-01", bugun="2026-09-09")[0] == "",
         str(hesap.ceyrek_saati("2026-07-01", bugun="2026-09-09")))
    sina("çeyrek kapanınca saat kendiliğinden geliyor",
         hesap.ceyrek_saati("2026-07-01", bugun="2026-10-01")[0] == "09.2026")
    # ÇEYREK BAŞI YAZIMI GERİ GELMESİN: gün yazımı okura o GÜNÜN ölçümü gibi görünür.
    # BOŞ saat bir KUSUR DEĞİL, ölçülemediğinin ilanıdır (çeyrek kapanmadıysa):
    # burada engel sayılsaydı hattın koşusunu durduran bir yanlış alarm olurdu.
    anket = {k: v for k, v in o.items()
             if k.startswith("bkea_") and k.endswith("_tarih")}
    sina("anket saatleri AA.YYYY (gün yazılmıyor)",
         len(anket) >= 5 and all(AY_RX.match(str(v)) for v in anket.values() if v),
         str({k: v for k, v in anket.items() if v and not AY_RX.match(str(v))}))
    sina("anket bacağının saatleri tek ağızdan konuşuyor (hepsi dolu ya da hepsi boş)",
         len({bool(v) for v in anket.values()}) == 1, str(anket))
    sina("anket etiketi bir saat anahtarı değil",
         isinstance(o.get("bkea_ceyrek"), str) and not o["bkea_ceyrek"].endswith(".2026"),
         repr(o.get("bkea_ceyrek")))
    saatler = {k: v for k, v in o.items()
               if k.endswith("_tarih") and k != "_sekil_tarih" and v}
    sina("yazılmış her saat çözülüyor; ay adı ya da ISO yazım yok",
         all(b.tarihe_cevir(v) is not None
             and not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]|-", str(v)) for v in saatler.values()),
         str({k: v for k, v in saatler.items() if b.tarihe_cevir(v) is None}))
    sina("ana saat haftalık kredi bacağı (GG.AA.YYYY)",
         bool(GUN_RX.match(str(o.get("_tarih")))) and o["_tarih"] == o["g_ar_13y_tarih"],
         repr(o.get("_tarih")))
    yarin = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    sina("hiçbir saat yarından ileri değil",
         all(pd.Timestamp(b.tarihe_cevir(v)) <= yarin for v in saatler.values()))
    # HER BACAK KENDİ DOSYASININ SAATİNİ TAŞIR. Hacim (haftalık kredi tabloları)
    # ile faiz (haftalık akım faiz tabloları) EVDS'te ayrı ürünlerdir ve ayrı
    # düşebilir: 28.08.2026'da hacim 21.08'e geçmişken faiz 14.08'de kalmıştı.
    # Tek saatle yazılsaydı sayfa bir haftalık faizi bugünün faizi gibi
    # gösterirdi; ölçüt anahtarın saatini KENDİ kaynak dosyasından doğrular.
    h, f, _b = hesap.yukle()
    hacim = {"g_ar_13y", "g_tuketici_13y", "g_ticari_13y", "ayrisma", "kacak_bkk", "npl"}
    faiz = {"makas_ihtiyac", "makas_ticari_tl", "makas_mevduat", "f_ihtiyac",
            "f_ticari_tl", "mev_tl", "politika"}
    yanlis = []
    for kume, cerceve in ((hacim, h), (faiz, f)):
        for k in kume:
            beklenen = f"{cerceve[k].dropna().index[-1]:%d.%m.%Y}"
            if o.get(f"{k}_tarih") != beklenen:
                yanlis.append(f"{k}: {o.get(f'{k}_tarih')} ≠ {beklenen}")
    sina("hacim ve faiz bacakları KENDİ dosyalarının saatini taşıyor",
         not yanlis, " · ".join(yanlis))


# ── 2. bayat işareti eşiği ───────────────────────────────────────────────────
def bolum_bayat_isareti() -> None:
    print("\n▶ Sayfadaki bayat işareti (Deger eşiği)")
    *_, o = _hesap()
    b = _ortak("bicim")
    mdx = _mdx()
    hat = b.tarihe_cevir(o.get("_tarih"))
    # Bileşenin kendi kuralı: g = hattın saati − anahtarın saati; g > bayatGun
    # ise değer "bayat" işaretlenir. Öntanımlı 45 gün.
    cagri = re.findall(r'<Deger\s+proje="%s"\s+anahtar="([^"]+)"([^>]*)>' % SLUG, mdx)
    sina("sayfa çağrıları okunabildi", len(cagri) >= 15, str(len(cagri)))
    kalici: list[str] = []
    for anahtar, kuyruk in cagri:
        if TARIHSEL_RX.search(anahtar):
            continue
        kendi = b.tarihe_cevir(o.get(f"{anahtar}_tarih") or o.get("_tarih"))
        if kendi is None or hat is None:
            continue
        m = re.search(r"bayatGun=\{(\d+)\}", kuyruk)
        esik = int(m.group(1)) if m else 45
        if (hat - kendi).days > esik:
            kalici.append(f"{anahtar}: {(hat - kendi).days} gün > {esik}")
    sina("sayfada kalıcı bayat işaretli değer yok", not kalici, " · ".join(kalici))
    # Eşik KREDİ hattının ölçtüğü toleranstan gelir; sayfada elle büyütülmüş
    # bir sayı olmasın diye ikisi karşılaştırılır.
    tol = hesap.tolerans()
    esikler = {int(x) for x in re.findall(r"bayatGun=\{(\d+)\}", mdx)}
    sina("sayfadaki eşik kredi hattının üç aylık toleransıyla aynı",
         tol is not None and esikler == {tol["ceyrek"]},
         f"sayfa {sorted(esikler)} · tolerans {tol}")
    # ARIZAYA KARŞI: eşik kaldırılırsa ölçüt DÜŞMELİ.
    anket_gun = (hat - b.tarihe_cevir(o["bkea_std_isletme_tarih"])).days
    sina("öntanımlı eşik bu bacağa yetmiyor (ölçüt gerçekten bağlayıcı)",
         anket_gun > 45, f"anket bacağı {anket_gun} gün geride")


# ── 3. bayatlık hükmü ────────────────────────────────────────────────────────
def bolum_bayatlik() -> None:
    print("\n▶ Bayatlık hükmü (veri durumu şeridi)")
    *_, o = _hesap()
    sina("özet bir bayatlık hükmü taşıyor", isinstance(o.get("bayat"), bool),
         repr(o.get("bayat")))
    sina("hüküm tek cümleyle gerekçelendiriliyor",
         isinstance(o.get("bayat_cumlesi"), str) and len(o["bayat_cumlesi"]) > 20)
    tol = {"haftalik": 12, "ceyrek": 110}
    taze = {"_tarih": "04.09.2026", "bkea_std_isletme_tarih": "06.2026"}
    sina("taze veride hüküm 'taze'",
         hesap.bayatlik(taze, {"uyarilar": []}, tol, bugun="2026-09-09") == (
             False, "Veri taze: haftalık kredi ve faiz serileri ile üç aylık "
                    "eğilim anketi toleransın içinde."))
    bayat_h = hesap.bayatlik({"_tarih": "01.08.2026", "bkea_std_isletme_tarih": "06.2026"},
                             {"uyarilar": []}, tol, bugun="2026-09-09")
    sina("haftalık bacak durursa hüküm 'bayat'", bayat_h[0] is True and "haftalık" in bayat_h[1],
         str(bayat_h))
    bayat_c = hesap.bayatlik({"_tarih": "04.09.2026", "bkea_std_isletme_tarih": "03.2026"},
                             {"uyarilar": []}, tol, bugun="2026-09-09")
    sina("anket bacağı ölürse hüküm 'bayat'", bayat_c[0] is True and "anket" in bayat_c[1],
         str(bayat_c))
    kaynak = hesap.bayatlik(taze, {"uyarilar": ["TAZELİK: 'k_yi_toplam' serisi …"]},
                            tol, bugun="2026-09-09")
    sina("üst hattın tazelik uyarısı hükme geçiyor", kaynak[0] is True, str(kaynak))
    sina("uyarı metni okura KOPYALANMIYOR (operatör dili sızmaz)",
         "k_yi_toplam" not in kaynak[1], kaynak[1])
    sina("ölçülemeyen hâlde hüküm yazılmıyor (üç hâlli sözleşme)",
         hesap.bayatlik(taze, None, None) == (None, ""))


# ── 4. sayfa sözleşmesi ──────────────────────────────────────────────────────
def bolum_sozlesme() -> None:
    print("\n▶ Sayfa sözleşmesi")
    *_, o = _hesap()
    mdx = _mdx()
    sina("proje sayfası bulundu", bool(mdx), str(MDX))
    cagrilan = set(re.findall(r'proje="%s"\s+anahtar="([^"]+)"' % SLUG, mdx))
    eksik = sorted(k for k in cagrilan if k not in o)
    sina("sayfanın çağırdığı her anahtar özette var", bool(cagrilan) and not eksik,
         f"eksik: {eksik}")
    sina("çeyrek etiketi sayfada adıyla çağrılıyor", "bkea_ceyrek" in cagrilan)
    gomulu = set(re.findall(r'/projeler/%s/([^"\s]+\.html)' % SLUG, mdx))
    sina("gömülü her figür şekil saat defterinde", gomulu <= set(o["_sekil_tarih"]),
         str(sorted(gomulu - set(o["_sekil_tarih"]))))
    sina("defter ile figür listesi birebir", set(o["_sekil_tarih"]) == set(hesap.SEKILLER))
    acik = dict(re.findall(r'src="/projeler/%s/([^"]+)"[^>]*tarihAnahtari="([^"]+)"' % SLUG, mdx))
    sina("her figürün açık damga anahtarı defterle aynı bacağı gösteriyor",
         all(hesap.SEKILLER.get(f) == a for f, a in acik.items()), str(acik))
    sina("açık damga anahtarlarının hepsi özette çözülüyor",
         all(isinstance(o.get(a), str) and o[a] for a in acik.values()))
    try:
        sys.path.insert(0, str(KOK))
        import guncelle
        kopya = next(h for h in guncelle.HATLAR if h.ad == "makro").kopya
        sina("kopya sözleşmesindeki her figür defterde",
             set(hesap.SEKILLER) <= set(kopya),
             str(sorted(set(hesap.SEKILLER) - set(kopya))))
    except Exception as e:                                             # noqa: BLE001
        sina("kopya sözleşmesi okunabildi", False, f"{type(e).__name__}: {e}")


# ── 5. okur dili ─────────────────────────────────────────────────────────────
def bolum_okur_dili() -> None:
    print("\n▶ Okur dili (özetin cümle alanları)")
    *_, o = _hesap()
    try:
        od = _ortak("okur_dili")
    except ImportError:
        sina("okur_dili modülü bulundu", False)
        return
    # Sayfa sınavının 17. ölçütünün eşi: ozet.json'un CÜMLE olan metin alanları
    # okura OLDUĞU GİBİ basılır. Tarayıcı satır listesi ister ve (satır, aile,
    # eşleşme) üçlüleri döndürür; kod ve yapım dili ENGEL, anahtar adı ve biçim
    # uyarıdır. Sözlük verilirse ANAHTARLAR taranır ve ölçüt sessizce yanlış
    # yere bakar — bir denetimin bakmadığı yer, geçen sınavla aynı görünür.
    cumleler = [v for v in o.values()
                if isinstance(v, str) and " " in v.strip() and len(v) > 25]
    sina("özette taranacak cümle var", bool(cumleler), str(len(cumleler)))
    bulgu = od.kosu_kaydi_tara(cumleler)
    engel = [x for x in bulgu if x[1] in ("kod dili", "yapım dili")]
    sina("özetin cümle alanlarında kod ve yapım dili yok", not engel, str(engel)[:400])
    # ARIZAYA KARŞI: tarayıcı gerçekten bakıyor mu?
    sahte = od.kosu_kaydi_tara(["Bu koşuda `ozet.json` yazılamadı, metrik.py düştü."])
    sina("tarayıcı kod dilini gerçekten yakalıyor",
         any(x[1] == "kod dili" for x in sahte), str(sahte))


# ── 6. yapısal kilit ─────────────────────────────────────────────────────────
def bolum_yapi() -> None:
    print("\n▶ Yapısal kilit")
    try:
        grafik.yaz(None, "olmayan.html")
        sina("defterde olmayan figür yazılamıyor", False)
    except KeyError:
        sina("defterde olmayan figür yazılamıyor", True)
    for dosya in ("hesap.py", "grafik.py", "duman.py"):
        kaynak = (BURASI / dosya).read_text(encoding="utf-8")
        parcalar = re.split(r'^if __name__ == "__main__":', kaynak, maxsplit=1, flags=re.M)
        sina(f"{dosya}: kapının altında tanım yok",
             len(parcalar) == 2 and not re.search(r"^(def|class)\s", parcalar[1], re.M))
    dfr = hesap.defter()
    sina("düzenleme defteri okunabiliyor ve şeması yerinde",
         isinstance(dfr.get("kayitlar"), list) and "_sema" in dfr)
    *_, o = _hesap()
    kayit = dfr.get("kayitlar", [])
    sina("özetteki defter sayıları dosyayla birebir",
         o["defter_toplam"] == len(kayit)
         and o["defter_dogrulanmis"] == sum(1 for k in kayit
                                            if k.get("dogrulama") == "dogrulandi"),
         f"{o['defter_toplam']}/{o['defter_dogrulanmis']} ≠ {len(kayit)}")


def main() -> int:
    print("Makroihtiyati hattı — duman sınaması (ağa çıkmaz)")
    bolum_ceyrek()
    bolum_bayat_isareti()
    bolum_bayatlik()
    bolum_sozlesme()
    bolum_okur_dili()
    bolum_yapi()
    print(f"\n{GECTI} geçti · {DUSTU} düştü")
    if _KUSUR:
        print("Düşenler: " + " | ".join(_KUSUR))
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
