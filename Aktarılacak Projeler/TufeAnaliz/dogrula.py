#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EYLÜL 2026 TÜFE YAZISI (05.10.2026) — yayımlanan metni ölçüme karşı sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
pandas/numpy/plotly YOK: betik yalnız standart kütüphaneyle çalışır, ağa çıkmaz,
duvar saati okumaz (girdisi depodaki arşiv ve ölçüm dosyası). Beş soru sorar:

1. ARŞİV — `veri/<çıpa>/` altındaki her dosyanın sıkıştırılmamış içeriğinin özü
   künyedekiyle aynı mı; ölçüm dosyası bu özlerle ve BUGÜNKÜ `olcum.py` ile mi
   üretilmiş; ölçüm dosyasındaki her metin biçimi sözleşmeyle (ondalık virgül,
   eksi U+2212, yüzde önde, puan/bp arkada) yeniden yazılınca aynı mı?
2. FİGÜRLER — `sekil.py`nin listesindeki her figür yayın dizininde var mı, bugünkü
   ölçüm dosyasının özünü taşıyor mu, içindeki başlık "Şekil NN —" ile mi açılıyor
   ve başlık satırları telefonun gömme çerçevesine sığıyor mu (Makro dersinin
   ortak ölçüsü)? Metin varsa: her figürü sırayla ve doğru numarayla gömüyor mu?
3. ENVANTER — metindeki HER ondalık sayı ve yüzde/puan/bp taşıyan HER tam sayı ya
   ölçüm dosyasındaki bir değerin metin biçimine eşit (birim ve açık işaret
   dahil) ya da aşağıdaki DIS_KAYNAK listesinde adıyla bildirilmiş bir ifadenin
   içinde durmalı. Beklenen cümleler buraya ELLE yazılmaz: kapsam bir ifade
   listesinin tuttuğu kadar değil, metnin kendisi kadardır. Ön bilgi (başlık,
   açıklama, kart özeti, kaynak, güncelleme) ve figür gömmelerinin `baslik`
   alanı da okura basıldığı için taranır; formüllerin ({,} ondalıklı) sayıları
   da.
4. DIŞ KAYNAK — DIS_KAYNAK'taki her ifade metinde geçmeli ve kaynağın ADI aynı
   cümlede (en çok 300 karakter yakınında) anılmalı. İfade metinden kalkarsa
   kapı düşer: liste sessizce çürümez. Ölçüm dosyasında `dis_kaynak` işaretli
   değerler ölçülmüş sayılmaz, yalnız bu listeyle geçer.
5. BİÇİM — ASCII tire ile yazılmış eksi sayı, arkaya yazılmış yüzde ve analizde
   yasak olan canlı `<Deger>` etiketi yok (analizin sayıları SABİTTİR).
6. BAĞLI İFADE — sayı envanteri bir sayının HANGİ ölçüm olduğunu sormaz (aynı
   çekirdek birden çok anahtarda bulunabilir: %1,90 hem momentum hem İTO tahmini,
   %2,14 hem C hem başka bir seri). Bu yüzden anlamı bir cümle kuruluşuna bağlı
   sayılar IFADELER'de ölçüm anahtarlarıyla kurulur ve metinde BİREBİR aranır:
   tablo satırları, "X'den beri" ay etiketleri, kesme ekli sayımlar ("35 ayın
   21'inde"), yer değiştirmesi anlamı bozan çiftler ("C %1,71, manşet %1,49").
7. HÜKÜM — sayıyı doğru yazıp hükmü yanlış kuran cümleler: sıralamanın yönü,
   reel faizin kaç ölçüde yükseldiği, Şekil 01'in sağ ucu, karnenin sayımı,
   kırpılmış ortalamanın aylık yönü, "tamamı baz" ve arındırılmış hızı ham eşikle
   kıyaslamak. Her biri ölçüm dosyasından hesaplanır, metinden değil.
8. ALINTI — metindeki her tırnak içi parça ya ALINTI listesinde durur ve kendi
   kaynağında (arşivlenmiş PPK metni ya da önceki yazı) BİREBİR bulunur, ya da
   TERIM listesinde adıyla bildirilmiş bir kendi ifademizdir (varsayımsal okur
   cümlesi). Listede olmayan yeni bir tırnak kapıyı düşürür.

MDX henüz yoksa 1 ve 2 koşar, betik "yazı yok" der ve DÜŞER: ölçüm katmanı
yazısıyla birlikte yayına girer; tek başına yayına giderse figürleri hiçbir
sayfada gömülü olmaz. (Yazı yazılırken `--olcum` yalnız 1 ve 2'yi sorar ve
geçerse 0 döner; sayfa sınavı bu bayrağı vermez.)

Yazar metne yeni bir DIŞ KAYNAK sayısı (haber, ajans anketi, resmî belge) koyarsa
onu aşağıdaki listeye ifadesi ve kaynağın adıyla ekler; ölçülmüş bir sayı
gerekiyorsa `olcum.py`ye eklenir, buraya değil.

Koşum:  python3 dogrula.py [--olcum]
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIPA = "2026-10-05"
VERI = BURASI / "veri" / CIPA
SLUG = "tufe-eylul-ppk-2026-10-05"
MDX = KOK / "site/src/content/analiz" / f"{SLUG}.mdx"
SEKIL = KOK / "site/public/analiz" / SLUG

# ─────────────────────────────────────────────── dış kaynak sayıları (adıyla)
# ifade: metinde BİREBİR geçmesi gereken parça (sayıyı içerir) · ad: kaynağın metinde
# ifadenin yakınında anılması gereken adı · kaynak: künye.
DIS_KAYNAK = [
    {"ifade": "%2,18", "ad": "AA Finans",
     "kaynak": "AA Finans Enflasyon Beklenti Anketi, Eylül aylık TÜFE beklentisinin ortalaması "
               "(5 Ekim 2026 sabah bülteninin aktarımı)"},
    {"ifade": "%1,90–2,60", "ad": "AA Finans",
     "kaynak": "AA Finans anketinde tahminlerin aralığı"},
    {"ifade": "20 ekonomist", "ad": "AA Finans",
     "kaynak": "AA Finans anketine katılan ekonomist sayısı"},
    {"ifade": "yaklaşık 0,25 puan", "ad": "TCMB",
     "kaynak": "TCMB PPK Toplantı Özeti (2026-42), 17 Eylül 2026: takvim kaymasının Ağustos enflasyonuna etkisi"},
]

# ─────────────────────────────────────────────── bağlı ifadeler (6)
# {anahtar} ölçüm dosyasındaki metin biçimiyle doldurulur; ifade metinde BİREBİR geçmeli.
IFADELER = [
    "önceki 35 ayın {pka_buyuk_hata_ay}'inde",
    "son 36 ayın {pka_fazla_tahmin_ay}'unda",
    "son 12 ayın da {pka_fazla_tahmin_12}'sında",
    "{politika_sabit_gun}dür değişmedi",
    "{ust30_ay_sayisi} ay kesintisiz",
    "(son kez {alti30_son_ay}'de, {alti30_son_deger})",
    "{alti30_son_ay}'den beri ilk kez",
    "{hizmet_yillik_dusuk_beri}'den ({hizmet_yillik_dusuk_beri_deger}) bu yana en düşük",
    "{kira_yillik_dusuk_beri}'den ({kira_yillik_dusuk_beri_deger}) bu yana en düşük",
    "{enerji_yillik_yuksek_beri}'dan ({enerji_yillik_yuksek_beri_deger}) bu yana en yüksek",
    "{hizmet_aylik_dusuk_beri}'dan ({hizmet_aylik_dusuk_beri_deger}) bu yana en düşük",
    "(C {c_aylik_sa}, manşet {tufe_aylik_sa}",
    "(B {b_aylik_sa})",
    "Ekim 2025'in {baz_10}'i",
    "Kasım 2025'in {baz_11}'si",
    "Aralık 2025'in {baz_12}'u",
    "arındırılmış hâlleri {baz_11_sa} ve {baz_12_sa}",
    "Eylül'de aylık {ito_aylik} arttı, ücretliler geçinme endeksi {uge_aylik}",
    "24 ayın {bc_ust_manset_ay}'unda B ve C manşetin üstünde",
    "manşet ({tufe_aylik}) ve B ({b_aylik}) anket halkasının altında",
    "({c_aylik}'e karşı {pka_eylul})",
    "45 grubun {kesit_n}'ü veri verdi",
    "manşetin {ana07_pay_agu}'uydu",
    "geçen Eylül {ana10_aylik_2025_09}",
    "| Momentum, 2025 mevsimselliği | {yol_momentum_mev25_ekim} | {yol_momentum_mev25_kasim} | "
    "{yol_momentum_mev25_aralik} | {yol_momentum_mev25_2027_09} |",
    "| Momentum, 2024 mevsimselliği | {yol_momentum_mev24_ekim} | {yol_momentum_mev24_kasim} | "
    "{yol_momentum_mev24_aralik} | {yol_momentum_mev24_2027_09} |",
    "| Son 12 ay, 2025 mevsimselliği | {yol_son12_mev25_ekim} | {yol_son12_mev25_kasim} | "
    "{yol_son12_mev25_aralik} | {yol_son12_mev25_2027_09} |",
    "| Anket patikası | {yol_anket_ekim} | {yol_anket_kasim} | {yol_anket_aralik} | {yol_anket_2027_09} |",
    "2023'ün çarpanlarıyla {yol_momentum_mev23_aralik}, 2022'ninkilerle {yol_momentum_mev22_aralik}",
    "| Ekim yıllığı %30'un altında | Ekim aylığı {esik_ekim_aylik} | {mom_ham25_ekim} (anket {pka_ekim}) |",
    "| Kasım yıllığı %30'un altında | Ekim–Kasım ortalaması {esik_kasim_aylik} | {mom_ham25_ekkas} |",
    "| Yıl sonu %30'un altında | Ekim–Aralık ortalaması {esik_aralik_aylik} | {mom_ham25_eka} |",
    "2025 çarpanlarıyla {esik_aralik_sa25}, 2024'ünkilerle {esik_aralik_sa24}, 2023'ünkilerle "
    "{esik_aralik_sa23}, 2022'ninkilerle {esik_aralik_sa22}",
    "ham aylık {karsi_olgu_aylik}, yıllık oran {karsi_olgu_12a} olurdu",
    "| Gerçekleşene göre | yıllık TÜFE ({tufe_12a}) | {reel_expost} | {reel_expost_agu} |",
    "| Eğilime göre | arındırılmış 3 ay yıllıklandırılmış ({tufe_3a_saar}) | {reel_egilim} | {reel_egilim_agu} |",
    "| Beklentiye göre | anketin 12 ay sonrası beklentisi ({pka_12a}) | {reel_exante} | {reel_exante_agu} |",
    "| {reel_ileri} | {reel_ileri_agu} |",
    "Ağustos'un hedef üstü kalem ağırlığı, Ağustos verisiyle 9 Eylül'de yapılan hesapta {difuzyon_hedef_agu_0909}'tü",
    "yaklaşık {tcmb_kayma_agu}lık takvim kayması",
]
# Kalıbın HER geçişi aynı ölçümü taşımalı (varlık değil tutarlılık): (düzenli ifade, anahtar). Grup, anahtarın
# metin biçiminin çekirdeğiyle (birim ve yüzde işareti atılmış) karşılaştırılır.
KALIPLAR = [
    (r"(\w+ \d{4})'den beri ilk kez", "alti30_son_ay"),
    (r"son kez (\w+ \d{4})'de", "alti30_son_ay"),
    (r"önceki 35 ayın (\d+)'", "pka_buyuk_hata_ay"),
    (r"son 36 ayın (\d+)'", "pka_fazla_tahmin_ay"),
    (r"son 12 ayın da (\d+)'", "pka_fazla_tahmin_12"),
    (r"(\d+) gündür değişmedi", "politika_sabit_gun"),
    (r"(\d+) gün sabit", "politika_sabit_gun"),
    (r"(\d+) gün sonra toplanıyor", "ppk_kalan_gun"),
    (r"(\d+) ay kesintisiz", "ust30_ay_sayisi"),
    (r"24 ayın (\d+)'", "bc_ust_manset_ay"),
    (r"45 grubun (\d+)'", "kesit_n"),
    (r"B ve C'nin yıllık oranları (\w+ \d{4})'den", "b_yillik_dusuk_beri"),
    (r"B ve C'nin yıllık oranları (\w+ \d{4})'den", "c_yillik_dusuk_beri"),
    (r"B ve C yıllıkları da (\w+ \d{4})'den", "b_yillik_dusuk_beri"),
    (r"[Hh]izmet yıllık %[\d,]+ ile (\w+ \d{4})'den", "hizmet_yillik_dusuk_beri"),
    (r"hizmet yıllığı (\w+ \d{4})'den", "hizmet_yillik_dusuk_beri"),
    (r"Kira yıllık %[\d,]+ ile (\w+ \d{4})'den", "kira_yillik_dusuk_beri"),
    (r"(\w+ \d{4})'dan \(%[\d,]+\) bu yana en yüksek", "enerji_yillik_yuksek_beri"),
]

# ─────────────────────────────────────────────── alıntılar (8)
# kaynak: arşivdeki dosya adı. PPK dosyalarında paragraflar, yazıda etiketsiz gövde aranır.
ALINTI = [
    ("enflasyon gerçekleşmelerini, ana eğilimini ve beklentilerini göz önünde bulundurarak", "ppk_2026-38-TR.json"),
    ("önemli ölçüde düşeceğine işaret", "ppk_2026-42-TR.json"),
    ("akaryakıt ve tüp gaz üzerinden enerji grubu yıllık enflasyonunu yukarı çekmeye devam", "ppk_2026-42-TR.json"),
    ("yavaşlamaya işaret", "ppk_2026-42-TR.json"),
    ("ılımlı seyrin süreceği", "ppk_2026-42-TR.json"),
    ("eğitim hizmetleri kaynaklı olarak mekanik biçimde aşağı çekecek", "ppk_2026-42-TR.json"),
    ("Enflasyon görünümünde belirgin ve kalıcı bir bozulma olması durumunda para politikası duruşu "
     "sıkılaştırılacaktır.", "ppk_2026-38-TR.json"),
    ("temkinli yaklaşmak önemli olacaktır", "ppk_2026-42-TR.json"),
    ("ana eğilim", "ppk_2026-42-TR.json"),
    ("enflasyonun ana eğiliminin gerilediğine işaret", "ppk_2026-38-TR.json"),
    ("iki sayı arasında geçiyor", "analiz_2026-09-03.mdx"),
    ("ihtimal azaldı, ama az", "analiz_2026-09-03.mdx"),
    ("yönetilen fiyatlar hariç", "analiz_2026-09-03.mdx"),
]
# kendi ifademiz: varsayımsal okur cümleleri ve okunuş etiketleri (alıntı değil)
TERIM = ["enflasyon kırıldı, indirim kapıda", "değişmedi", "belirgin yavaşladı",
         "piyasa şu kadar indirim fiyatlıyor"]

hatalar: list[str] = []
sayac = {"arsiv": 0, "bicim": 0, "sayi": 0, "dis": 0, "sekil": 0, "metin": 0}


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
    if birim in ("puan", "bp", "ay", "gün", "kat"):
        return f"{sayi(x, b, arti)} {birim}"
    return sayi(x, b, arti)


def _oz(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


# ─────────────────────────────────────────────── 1 · arşiv ve ölçüm
def arsiv() -> dict:
    kunye = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
    for ad, k in kunye["dosyalar"].items():
        sayac["arsiv"] += 1
        yol = VERI / f"{ad}.gz"
        if not yol.exists():
            hatalar.append(f"arşiv dosyası yok: {ad}.gz")
            continue
        if hashlib.sha256(gzip.decompress(yol.read_bytes())).hexdigest() != k["sha256"]:
            hatalar.append(f"arşiv özü künyeyle tutmuyor: {ad}")
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    sayac["arsiv"] += 2
    if o.get("arsiv") != {ad: k["sha256"] for ad, k in kunye["dosyalar"].items()}:
        hatalar.append("ölçüm dosyası bu arşivle üretilmemiş (özler ayrışıyor) — olcum.py yeniden koşulmalı")
    if o.get("olcum_py_oz") != _oz(BURASI / "olcum.py"):
        hatalar.append("ölçüm dosyası bugünkü olcum.py ile üretilmemiş — olcum.py yeniden koşulmalı")
    for k, v in o["degerler"].items():
        if "deger" not in v:
            continue
        sayac["bicim"] += 1
        bek = metin_bicimi(v["deger"], v["b"], v["birim"], v.get("arti", False))
        if bek != v["metin"]:
            hatalar.append(f"ölçüm dosyasında metin biçimi sözleşmeye uymuyor: {k}: {v['metin']!r} ≠ {bek!r}")
    return o


# ─────────────────────────────────────────────── 2 · figürler
def _ortak():
    """Başlık genişlik ölçüsü Makro dersinin ortak kuralıdır (çizim kütüphanesi istemez)."""
    spec = importlib.util.spec_from_file_location(
        "tufe_dogrula_sekil_ortak", KOK / "Aktarılacak Projeler/MakroKurFaiz/sekil_ortak.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sekil_listesi() -> list[str]:
    kaynak = (BURASI / "sekil.py").read_text(encoding="utf-8")
    bas = kaynak.index("SEKILLER =")
    return re.findall(r'"(\d\d_[a-z_]+)"', kaynak[bas:kaynak.index("]", bas)])


def figurler(liste: list[str]) -> None:
    oz = _oz(VERI / "olcum.json")
    ortak = _ortak()
    if len(liste) < 3:
        hatalar.append(f"figür listesi {len(liste)} öğe — en az 3 bekleniyor")
    for i, ad in enumerate(liste, 1):
        sayac["sekil"] += 1
        if not ad.startswith(f"{i:02d}_"):
            hatalar.append(f"figür listesi sıralı numaralı değil: {ad}")
        yol = SEKIL / f"{ad}.html"
        if not yol.exists():
            hatalar.append(f"figür yok: {yol.relative_to(KOK)}")
            continue
        h = yol.read_text(encoding="utf-8")
        x = re.search(r'<meta name="tto-olcum-ozu" content="([0-9a-f]{64})">', h)
        if not x or x.group(1) != oz:
            hatalar.append(f"figür bugünkü ölçüm dosyasından çizilmemiş — sekil.py yeniden koşulmalı: {ad}")
        if "tto-ev-stili" not in h:
            hatalar.append(f"figüre ev stili uygulanmamış: {ad}")
        # başlık nesnesinde anahtar sırası sabit değil ("pad" önce gelebilir): metni Şekil önekinden bul
        t = re.search(r'"text":("(?:\\u015e|Ş)ekil \d\d (?:[^"\\]|\\.)*")', h)
        if not t:
            hatalar.append(f"figürün başlığı okunamadı: {ad}")
            continue
        baslik = json.loads(t.group(1))
        if not baslik.startswith(f"Şekil {ad[:2]} —"):
            hatalar.append(f"figürün içindeki başlık 'Şekil {ad[:2]} —' ile açılmıyor: {ad}")
        for s in ortak.tasan_satirlar(baslik):
            hatalar.append(f"figür başlığı telefon çerçevesinde taşıyor: {ad}: {s}")


# ─────────────────────────────────────────────── 3–5 · metin
ETIKET = re.compile(r"</?[A-Za-z][^>]*>")      # etiket harfle ya da "/" ile başlar; "<" işaretine çarpmaz
SAYI = re.compile(
    r"(?<![\w.,/])(?P<isaret>[+−\-])?(?P<yuzde>%)?(?P<cekirdek>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    r"(?![\d])(?:(?P<sonra>\s?(?:baz puan|puan|bp|gün)(?=[a-zçğıöşüâî]*\b)))?")
# birim ekli yazılır ("1,78 puanlık", "0,81 puandan", "256 gündür"): ek birimi düşürmez.


def _norm(s: str) -> str:
    s = s.replace(" ", " ").replace("{,}", ",").replace("\\%", "%").replace("''", "'")
    return re.sub(r"[ \t]+", " ", s)


def bolumler(m: str) -> tuple[dict, str]:
    _, on, govde = m.split("---", 2)
    alan = {}
    for ad in ("title", "description", "ozet", "kaynak", "guncelleme"):
        x = re.search(rf"^{ad}: '((?:[^']|'')*)'$", on, re.M)
        alan[ad] = x.group(1).replace("''", "'") if x else ""
        if not x and ad in ("title", "description", "ozet"):
            hatalar.append(f"ön bilgi alanı okunamadı: {ad}")
    for ad, bek in (("pubDate", CIPA), ("veriTarihi", CIPA)):
        x = re.search(rf"^{ad}: (\S+)\s*$", on, re.M)
        if not x or x.group(1).strip("'\"") != bek:
            hatalar.append(f"ön bilgi {ad} {bek} değil: {x.group(1) if x else 'yok'}")
    return alan, govde


def taranan_metin(govde: str) -> tuple[str, str]:
    """(düz metin, formül metni). Kod blokları, import satırları ve figür gömmeleri ayıklanır
    (gömmenin `baslik`ı okura basıldığı için ayrıca eklenir); etiketler silinir, içerikleri kalır."""
    g = re.sub(r"```.*?```", " ", govde, flags=re.S)
    g = re.sub(r"`[^`\n]*`", " ", g)
    g = re.sub(r"^import .*$", " ", g, flags=re.M)
    basliklar = re.findall(r'<GrafikEmbed[^>]*\bbaslik="([^"]*)"', g)
    g = re.sub(r"<GrafikEmbed[^>]*/>", " ", g)
    formul = " ".join(re.findall(r"\$\$.*?\$\$", g, flags=re.S) + re.findall(r"(?<!\$)\$[^$\n]+\$(?!\$)", g))
    g = re.sub(r"\$\$.*?\$\$", " ", g, flags=re.S)
    g = re.sub(r"(?<!\$)\$[^$\n]+\$(?!\$)", " ", g)
    g = ETIKET.sub(" ", g)
    return _norm(g + "\n" + "\n".join(basliklar)), _norm(formul)


class Izin:
    """Ölçüm dosyasından kurulan izinli sayı kümesi: çekirdek (işaretsiz, sözleşme yazımı) →
    [(birim, işaret)]. `dis_kaynak` işaretli değerler buraya girmez."""

    def __init__(self, o: dict) -> None:
        self.k: dict[str, list[tuple[str, int]]] = {}
        for v in o["degerler"].values():
            if "deger" not in v or v.get("dis_kaynak"):
                continue
            c = sayi(abs(v["deger"]), v["b"])
            isaret = 0 if float(c.replace(".", "").replace(",", ".")) == 0 else (1 if v["deger"] > 0 else -1)
            self.k.setdefault(c, []).append((v["birim"], isaret))

    def var(self, cekirdek: str, birim: str, isaret: str | None) -> bool:
        for b, s in self.k.get(cekirdek, []):
            if birim and b != birim:
                continue
            if isaret in ("−", "-") and s >= 0:
                continue
            if isaret == "+" and s <= 0:
                continue
            return True
        return False


def envanter(ad: str, metin: str, izin: Izin, kapsam: list[tuple[int, int]]) -> None:
    for x in SAYI.finditer(metin):
        c, yuzde, sonra = x.group("cekirdek"), x.group("yuzde"), (x.group("sonra") or "").strip()
        ondalik = "," in c
        if not (ondalik or yuzde or sonra):
            continue                    # birimsiz tam sayı (tarih, sayım, şekil no) sınanmaz
        sayac["sayi"] += 1
        if any(a <= x.start() and x.end() <= b for a, b in kapsam):
            continue
        birim = "%" if yuzde else ("bp" if sonra == "bp" else ("gün" if sonra == "gün" else ("puan" if sonra else "")))
        if sonra == "baz puan":
            birim = "bp"
        if not izin.var(c, birim, x.group("isaret")):
            hatalar.append(f"ölçümde karşılığı olmayan sayı · {ad}: "
                           f"{metin[max(0, x.start() - 60):x.end() + 25]!r}")


def dis_kapsam(ad: str, metin: str, zorunlu: bool) -> list[tuple[int, int]]:
    kapsam = []
    for d in DIS_KAYNAK:
        i = metin.find(_norm(d["ifade"]))
        if i < 0:
            if zorunlu:
                hatalar.append(f"dış kaynak ifadesi metinde yok ({d['kaynak']}): {d['ifade']!r}")
            continue
        while i >= 0:
            sayac["dis"] += 1
            pencere = metin[max(0, i - 300):i + len(d["ifade"]) + 300]
            if d["ad"] not in pencere:
                hatalar.append(f"dış kaynak sayısı kaynağının adı ('{d['ad']}') anılmadan yazılmış · {ad}: "
                               f"{metin[max(0, i - 60):i + 40]!r}")
            kapsam.append((i, i + len(_norm(d["ifade"]))))
            i = metin.find(_norm(d["ifade"]), i + 1)
    return kapsam


def bicim(ad: str, metin: str) -> None:
    sayac["bicim"] += 1
    for x in re.finditer(r"(?<![\w/.\-–])-%?\d", metin):
        hatalar.append(f"ASCII tireli eksi sayı · {ad}: {metin[max(0, x.start() - 30):x.end() + 10]!r}")
    for x in re.finditer(r"\d[ \t]*%(?!\w)", metin):
        hatalar.append(f"arkaya yazılmış yüzde · {ad}: {metin[max(0, x.start() - 20):x.end() + 5]!r}")


def gommeler(govde: str, liste: list[str]) -> None:
    sayac["sekil"] += 1
    gomulu = re.findall(r'<GrafikEmbed src="/analiz/' + re.escape(SLUG) + r'/(\d\d_[a-z_]+)\.html"[^>]*no="(\d\d)"',
                        govde)
    if [a for a, _ in gomulu] != liste:
        hatalar.append(f"gömme sırası figür listesiyle aynı değil: {[a for a, _ in gomulu]} ≠ {liste}")
    for a, n in gomulu:
        if not a.startswith(n + "_"):
            hatalar.append(f"figür dosyasının öneki gömme numarasıyla aynı değil: {a} · no {n}")
    if len(re.findall(r"<GrafikEmbed", govde)) != len(gomulu):
        hatalar.append("ayrıştırılamayan figür gömmesi var (src ya da no biçimi)")


def zorunlu(alan: dict, govde_metin: str, o: dict) -> None:
    """Yazının manşeti ölçümle aynı yazılmış olmalı: aylık ve yıllık TÜFE açıklamada ve gövdede."""
    for k in ("tufe_aylik", "tufe_12a"):
        m = o["degerler"][k]["metin"]
        sayac["metin"] += 2
        if m not in _norm(alan["description"]):
            hatalar.append(f"açıklama manşet sayısını taşımıyor ({k}): {m}")
        if m not in govde_metin:
            hatalar.append(f"gövde manşet sayısını taşımıyor ({k}): {m}")


def bagli_ifadeler(duz: str, o: dict) -> None:
    d = o["degerler"]
    for sablon in IFADELER:
        sayac["metin"] += 1
        try:
            ifade = sablon.format(**{k: v["metin"] for k, v in d.items()})
        except KeyError as e:
            hatalar.append(f"bağlı ifadenin anahtarı ölçüm dosyasında yok ({e}): {sablon[:70]!r}")
            continue
        if _norm(ifade) not in duz:
            hatalar.append(f"bağlı ifade metinde birebir yok (ölçümle kurulan biçim): {ifade!r}")


def _cekirdek(m: str) -> str:
    return re.sub(r"\s(puan|bp|gün|ay|kat)$", "", m).replace("%", "")


def kaliplar(duz: str, o: dict) -> None:
    d = o["degerler"]
    for kalip, anahtar in KALIPLAR:
        bek = _cekirdek(d[anahtar]["metin"])
        bulundu = False
        for x in re.finditer(kalip, duz):
            bulundu = True
            sayac["metin"] += 1
            if x.group(1) != bek:
                hatalar.append(f"kalıp ölçümle çelişiyor ({anahtar} = {bek!r}): {duz[max(0, x.start() - 30):x.end() + 10]!r}")
        if not bulundu:
            hatalar.append(f"kalıp metinde hiç geçmiyor (ölçüt koşmadı): {kalip!r}")


def _cumleler(t: str) -> list[str]:
    return [c for c in re.split(r"(?<=[.;:])\s+|\n+", t) if c.strip()]


SAYI_SOZ = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6,
            "biri": 1, "ikisi": 2, "üçü": 3, "dördü": 4, "beşi": 5, "altısı": 6}


def hukumler(duz: str, ham_govde: str, o: dict) -> None:
    d = {k: v["deger"] for k, v in o["degerler"].items() if "deger" in v}

    def kural(kosul: bool, mesaj: str) -> None:
        sayac["metin"] += 1
        if not kosul:
            hatalar.append(f"hüküm ölçümle çelişiyor · {mesaj}")

    # (a) C–manşet sıralaması arındırılınca dönüyor mu
    ayni = (d["c_aylik"] - d["tufe_aylik"]) * (d["c_aylik_sa"] - d["tufe_aylik_sa"]) > 0
    kural(not (ayni and re.search(r"sıralama tersine dön\w*\s*\(C", duz)),
          "C ile manşetin sıralaması arındırılınca DEĞİŞMİYOR, metin 'tersine dönüyor' diyor")
    kural(not (not ayni and "sıralama değişmiyor (C" in duz), "C ile manşetin sıralaması arındırılınca dönüyor")
    # (b) reel faiz kaç ölçüde yükseldi
    yuk = sum(d[k] > d[k + "_agu"] for k in ("reel_expost", "reel_egilim", "reel_exante", "reel_ileri"))
    for x in re.finditer(r"\b(iki|üç|dört|her) ölçüde", duz):
        n = 4 if x.group(1) == "her" else SAYI_SOZ[x.group(1)]
        kural(n == yuk, f"reel faiz {x.group(0)!r} deniyor, ölçümde yükselen ölçü sayısı {yuk}")
    if "Beklentiye bakan ölçü yerinde" in duz:
        kural(abs(d["reel_exante"] - d["reel_exante_agu"]) < 0.05, "beklentiye bakan reel faiz 'yerinde' değil")
    # (c) Şekil 01'in sağ ucu
    ust = max(d["tufe_aylik"], d["b_aylik"], d["c_aylik"]) >= d["pka_eylul"]
    kural(not (ust and "üç çizginin de anket halkasının altında" in duz),
          "Şekil 01: çizgilerden biri anket halkasının üstünde bitiyor")
    if "C ise halkanın hemen üstünde" in duz:
        kural(d["c_aylik"] > d["pka_eylul"] > max(d["tufe_aylik"], d["b_aylik"]),
              "Şekil 01: 'C halkanın üstünde, manşet ve B altında' ölçümle tutmuyor")
    # (d) kırpılmış ortalamanın aylık yönü: aylığı gerilemediyse 'geriledi/indi' diyen cümle üç aylık ölçüyü anmalı
    if d["kirpma_aylik"] >= d["kirpma_aylik_agu"] - 0.005:
        for c in _cumleler(duz):
            if re.search(r"kırpılmış ortalama", c, re.I) and re.search(r"\b(geriledi|indi)\b", c):
                kural(bool(re.search(r"üç aylı|3 ay|yatay", c)),
                      f"kırpılmış ortalamanın aylığı gerilemedi, cümle yalnız 'geriledi' diyor: {c[:120]!r}")
    # (e) 'tamamı baz': karşı olguda eğilimin payı varsa kurulmaz
    if d["egilim_payi"] > 0.05:
        x = re.search(r"tamam[ıi]\w*\s+(baz|takvim)", duz)
        kural(x is None, f"yıllık düşüşün {o['degerler']['egilim_payi']['metin']}'ı eğilimden geliyor, metin "
                         f"{x.group(0) if x else ''!r} diyor")
    # (f) arındırılmış momentum ham eşikle kıyaslanmaz
    esik = o["degerler"]["esik_aralik_aylik"]["metin"]
    for c in _cumleler(duz):
        if "omentum" in c and esik in c:
            kural("ham" in c, f"arındırılmış momentum ham eşikle ({esik}) kıyaslanıyor: {c[:120]!r}")
    # (g) 'Ekim'de dip' yalnız mevsime tutarlı patikada Ekim gerçekten dipse
    yol = [d[f"yol_momentum_mev25_{a}"] for a in ("ekim", "kasim", "aralik")]
    kural(not ("Ekim'de dip" in duz and min(yol) != yol[0]),
          "momentum patikasında Ekim–Aralık'ın dibi Ekim değil, metin 'Ekim'de dip' diyor")
    # (h) karne sayımı: tablodan sayılır
    bas = ham_govde.find("| yön tuttu mu |")
    if bas < 0:
        kural(False, "karne tablosu bulunamadı ('yön tuttu mu' sütunu)")
        return
    satirlar = []
    for sat in ham_govde[bas:].split("\n")[2:]:
        if not sat.startswith("|"):
            break
        satirlar.append(sat.strip().strip("|").split("|")[-1].strip())
    tuttu = sum(1 for h in satirlar if re.match(r"(yön )?evet", h))
    x = re.search(r"(\w+) yön öngörüsünden (\w+) yön olarak tuttu", duz)
    kural(x is not None, "karne sayım cümlesi ('… yön öngörüsünden … yön olarak tuttu') yok")
    if x:
        kural(SAYI_SOZ.get(x.group(1)) == len(satirlar) and SAYI_SOZ.get(x.group(2)) == tuttu,
              f"karne cümlesi {x.group(0)!r}, tabloda {len(satirlar)} satır ve {tuttu} 'evet'")
    kural("sınanamadı" not in " ".join(satirlar), "karnede 'sınanamadı' satırı var — veri arşivde")


def _kaynak_metin(ad: str) -> str:
    b = gzip.decompress((VERI / f"{ad}.gz").read_bytes()).decode("utf-8")
    if ad.endswith(".json"):
        b = " ".join(json.loads(b)["paragraflar"])
    else:
        b = ETIKET.sub(" ", b)
    return re.sub(r"\s+", " ", b.replace("’", "'"))


def alintilar(duz: str) -> None:
    kaynak = {}
    for ifade, ad in ALINTI:
        sayac["metin"] += 1
        if ad not in kaynak:
            kaynak[ad] = _kaynak_metin(ad)
        if ifade not in kaynak[ad]:
            hatalar.append(f"alıntı kaynağında birebir yok ({ad}): {ifade!r}")
    bilinen = {i for i, _ in ALINTI} | set(TERIM)
    for x in re.finditer(r'"([^"\n]{2,400})"', duz):
        if x.group(1) not in bilinen:
            hatalar.append(f"tırnak içi parça ne ALINTI ne TERIM listesinde: {x.group(1)!r}")


def metin(o: dict, liste: list[str]) -> None:
    m = MDX.read_text(encoding="utf-8")
    if re.search(r"<Deger\b|import Deger", m):
        hatalar.append("analizde canlı <Deger> etiketi var — analizin sayıları sabittir (karar 08.09.2026)")
    alan, govde = bolumler(m)
    izin = Izin(o)
    duz, formul = taranan_metin(govde)
    dis_tum = dis_kapsam("gövde", duz, zorunlu=True)
    envanter("gövde", duz, izin, dis_tum)
    envanter("formül", formul, izin, [])
    bicim("gövde", duz)
    for ad in ("title", "description", "ozet", "kaynak", "guncelleme"):
        t = _norm(alan[ad])
        envanter(ad, t, izin, dis_kapsam(ad, t, zorunlu=False))
        bicim(ad, t)
    gommeler(govde, liste)
    zorunlu(alan, duz, o)
    bagli_ifadeler(duz, o)
    kaliplar(_norm(alan["description"] + "\n" + alan["ozet"] + "\n") + duz, o)
    tum = _norm(alan["description"] + "\n" + alan["ozet"] + "\n") + duz
    hukumler(tum, govde, o)
    alintilar(_norm(alan["title"] + "\n" + alan["description"] + "\n" + alan["ozet"] + "\n") + duz)


def main() -> int:
    o = arsiv()
    liste = sekil_listesi()
    figurler(liste)
    yalniz_olcum = "--olcum" in sys.argv
    if not yalniz_olcum:
        if not MDX.exists():
            hatalar.append(f"yazı yok: {MDX.relative_to(KOK)} — metin ölçütleri koşmadı")
        else:
            metin(o, liste)
    if hatalar:
        print(f"✗ Eylül TÜFE yazısı · {len(hatalar)} hata")
        for h in hatalar:
            print("  ·", h)
        print(f"✗ Eylül TÜFE yazısı · {len(hatalar)} hata (ilki: {hatalar[0][:140]})")
        return 1
    kapsam = "yalnız arşiv, ölçüm ve figürler (--olcum)" if yalniz_olcum else (
        f"{sayac['sayi']} sayının hepsi ölçümde ya da adıyla bildirilmiş dış kaynakta ({sayac['dis']} dış "
        "kaynak ifadesi)")
    print(f"✓ Eylül TÜFE yazısı · {sayac['arsiv']} arşiv ölçütü, {sayac['bicim']} biçim ölçütü, "
          f"{len(liste)} figür; {kapsam}; {sayac['metin']} bağlı ifade, kalıp, hüküm ve alıntı ölçütü")
    return 0


if __name__ == "__main__":
    sys.exit(main())
