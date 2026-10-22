#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""22 EKİM 2026 PPK YAZISI — yayımlanan metni ölçüme ve kaynak metne karşı sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
pandas/numpy/plotly YOK: betik yalnız standart kütüphaneyle çalışır, ağa çıkmaz,
duvar saati okumaz (girdisi `veri/<çıpa>/` altındaki donmuş arşiv ve ölçüm dosyası).
Yarın tazelenen bir pano bu kapıyı düşürmez; düşürebilecek tek şey yazının kendisi,
ölçüm dosyası ya da `olcum.py`nin değişmesidir.

1. ARŞİV — her donmuş dosyanın sıkıştırılmamış içeriğinin özü künyedekiyle aynı mı;
   ölçüm dosyası bu özlerle ve BUGÜNKÜ `olcum.py` ile mi üretilmiş; her değerin metin
   biçimi sözleşmeyle (ondalık virgül, eksi U+2212, yüzde önde, bp/puan/gün arkada)
   yeniden yazılınca aynı mı?
2. ÖN BİLGİ — pubDate ve veriTarihi çıpa günü mü, zorunlu alanlar okunuyor mu?
3. ENVANTER — metindeki HER ondalık sayı ve yüzde/puan/bp/gün taşıyan HER tam sayı,
   ölçüm dosyasındaki bir değerin metin biçimine (birim ve açık işaret dahil) eşit
   olmalı. Kapsam bir ifade listesinin tuttuğu kadar değil, metnin kendisi kadardır;
   ön bilgi (başlık, açıklama, kart özeti, kaynak) ve figür gömmelerinin `baslik`ı da
   taranır.
4. ALINTI — tırnak içindeki her parça ve her blok alıntı, donmuş TCMB metinlerinde
   (ve "Adımların büyüklüğü" cümlelerinin karar tablosunda) BİREBİR geçmeli; "…" ile
   kısaltılmış alıntının parçaları kaynakta aynı sırayla geçmeli. Kendi okunuş
   etiketlerimiz TERIM listesinde adıyla durur. Listede olmayan yeni bir tırnak kapıyı
   düşürür.
5. BİÇİM — ASCII tireyle yazılmış eksi sayı, arkaya yazılmış yüzde ve analizde yasak olan
   canlı `<Deger>` etiketi yok.
6. HÜKÜM — sayıyı doğru yazıp hükmü yanlış kuran cümleler: "altısı da indirim", "bütün
   düğümler altında", "en yakını 2 yıllık", "aralığın tam ortasında", "aralığın tamamının
   üstünde", "beşin dördü". Her biri ölçüm dosyasından hesaplanır, metinden değil.
7. DÜZELTME — 31 Ağustos, 6, 10 ve 17 Eylül yazılarında bugün tarihli düzeltme kaydı var
   mı; kaydın yeni değeri o yazının kendi veri gününün ölçümünde karşılık buluyor mu; eski
   hüküm gövdeden çıktı mı, düzeltilmiş ölçüm gövdede duruyor mu. Düzeltilmiş paragrafların
   BÜTÜN sayıları ayrıca sorulmaz: o paragraflar yazının kendi, düzeltilmeyen sayılarını da
   taşır (tablo satırları, rakam şeridinin öbür kalemleri) ve envanter onları gürültüye boğar.

Koşum:  python3 dogrula.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIPA = "2026-10-22"
VERI = BURASI / "veri" / CIPA
SLUG = "ppk-karari-2026-10-22"
MDX = KOK / "site/src/content/analiz" / f"{SLUG}.mdx"

# Kendi ifademiz (alıntı değil): okunuş etiketleri ve bölüm başlıklarındaki adlar.
TERIM = ["eğri indirim fiyatlamıyor", "ilk kez", "piyasa ankete inanmıyor"]

hatalar: list[str] = []
sayac = {"arsiv": 0, "bicim": 0, "sayi": 0, "alinti": 0, "hukum": 0}


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
        sayac["bicim"] += 1
        bek = metin_bicimi(v["deger"], v["b"], v["birim"], v.get("arti", False))
        if bek != v["metin"]:
            hatalar.append(f"ölçüm dosyasında metin biçimi sözleşmeye uymuyor: {k}: {v['metin']!r} ≠ {bek!r}")
    return o


def kaynak_metinleri() -> list[str]:
    """Donmuş TCMB metinleri (paragrafları birleştirilmiş) ve karar tablosundaki kalıp cümleleri."""
    out = []
    for yol in sorted(VERI.glob("ppk_*-TR.json.gz")):
        d = json.loads(gzip.decompress(yol.read_bytes()))
        out.append(" ".join(d["paragraflar"]))
    tablo = json.loads(gzip.decompress((VERI / "karar_tablosu.json.gz").read_bytes()))
    out += [k["kalip_cumle"] for k in tablo if k["kalip_cumle"]]
    return [_bosluk(m) for m in out]


# ─────────────────────────────────────────────── 2 · ön bilgi
def _bosluk(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def bolumler(m: str) -> tuple[dict, str]:
    _, on, govde = m.split("---", 2)
    alan = {}
    for ad in ("title", "description", "ozet", "kaynak"):
        x = re.search(rf"^{ad}: '((?:[^']|'')*)'$", on, re.M)
        alan[ad] = x.group(1).replace("''", "'") if x else ""
        if not x:
            hatalar.append(f"ön bilgi alanı okunamadı: {ad}")
    for ad in ("pubDate", "veriTarihi"):
        x = re.search(rf"^{ad}: (\S+)\s*$", on, re.M)
        if not x or x.group(1).strip("'\"") != CIPA:
            hatalar.append(f"ön bilgi {ad} {CIPA} değil: {x.group(1) if x else 'yok'}")
    return alan, govde


# ─────────────────────────────────────────────── 3 · envanter
ETIKET = re.compile(r"</?[A-Za-z][^>]*>")      # etiket harfle ya da "/" ile başlar; "<" işaretine çarpmaz
SAYI = re.compile(
    r"(?<![\w.,/])(?P<isaret>[+−\-])?(?P<yuzde>%)?(?P<cekirdek>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    r"(?![\d])(?:(?P<sonra>\s?(?:baz puan|puan|bp|gün)(?=[a-zçğıöşüâî]*\b)))?")


def _norm(s: str) -> str:
    s = s.replace(" ", " ").replace("{,}", ",").replace("\\%", "%")
    return re.sub(r"[ \t]+", " ", s)


def taranan_metin(govde: str) -> tuple[str, str]:
    """(düz metin, formül metni). Kod, import satırları ve figür gömmeleri ayıklanır
    (gömmenin `baslik`ı okura basıldığı için ayrıca eklenir); etiketler silinir."""
    g = re.sub(r"```.*?```", " ", govde, flags=re.S)
    g = re.sub(r"`[^`\n]*`", " ", g)
    g = re.sub(r"^import .*$", " ", g, flags=re.M)
    g = re.sub(r"\{/\*.*?\*/\}", " ", g, flags=re.S)
    basliklar = re.findall(r'<GrafikEmbed[^>]*\bbaslik="([^"]*)"', g)
    g = re.sub(r"<GrafikEmbed[^>]*/>", " ", g)
    formul = " ".join(re.findall(r"\$\$.*?\$\$", g, flags=re.S) + re.findall(r"(?<!\$)\$[^$\n]+\$(?!\$)", g))
    g = re.sub(r"\$\$.*?\$\$", " ", g, flags=re.S)
    g = re.sub(r"(?<!\$)\$[^$\n]+\$(?!\$)", " ", g)
    g = ETIKET.sub(" ", g)
    return _norm(g + "\n" + "\n".join(basliklar)), _norm(formul)


class Izin:
    def __init__(self, o: dict) -> None:
        self.k: dict[str, list[tuple[str, int]]] = {}
        for v in o["degerler"].values():
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


def envanter(ad: str, metin: str, izin: Izin) -> None:
    for x in SAYI.finditer(metin):
        c, yuzde, sonra = x.group("cekirdek"), x.group("yuzde"), (x.group("sonra") or "").strip()
        if not ("," in c or yuzde or sonra):
            continue                    # birimsiz tam sayı (tarih, sayım, toplantı) sınanmaz
        sayac["sayi"] += 1
        birim = "%" if yuzde else {"bp": "bp", "baz puan": "bp", "gün": "gün", "puan": "puan"}.get(sonra, "")
        if not izin.var(c, birim, x.group("isaret")):
            hatalar.append(f"ölçümde karşılığı olmayan sayı · {ad}: "
                           f"{metin[max(0, x.start() - 60):x.end() + 25]!r}")


# ─────────────────────────────────────────────── 4 · alıntı
def alintilar(metin: str, kaynak: list[str]) -> None:
    # Satır sonları paragrafın içindedir: önce boşluklar tekleşir, sonra tırnaklar soldan
    # sağa çiftlenir (bir satırı aşan alıntı çiftlemeyi kaydırmasın).
    for x in re.finditer(r'"([^"]{2,400})"', _bosluk(metin)):
        parca = _bosluk(x.group(1))
        sayac["alinti"] += 1
        if parca in TERIM:
            continue
        parcalar = [p.strip(" .") for p in parca.split("…") if p.strip(" .")]
        if not parcalar:
            continue
        # cümle başındaki büyük harf alıntının parçası değildir ("Zamanlaması" sözcüğü …)
        kucuk = [parcalar[0][:1].lower() + parcalar[0][1:]] + parcalar[1:]
        if not any(_sirali(parcalar, m) or _sirali(kucuk, m) for m in kaynak):
            hatalar.append(f"tırnak içindeki parça kaynak metinlerde birebir yok: {parca!r}")


def _sirali(parcalar: list[str], metin: str) -> bool:
    i = 0
    for p in parcalar:
        j = metin.find(p, i)
        if j < 0:
            return False
        i = j + len(p)
    return True


def blok_alintilar(govde: str, kaynak: list[str]) -> None:
    blok, bloklar = [], []
    for satir in govde.splitlines() + [""]:
        if satir.startswith(">"):
            blok.append(satir[1:].strip())
        elif blok:
            bloklar.append(_bosluk(" ".join(blok)))
            blok = []
    for b in bloklar:
        sayac["alinti"] += 1
        if not any(b in m for m in kaynak):
            hatalar.append(f"blok alıntı kaynak metinlerde birebir yok: {b[:120]!r}")


# ─────────────────────────────────────────────── 5 · biçim
def bicim(ad: str, metin: str) -> None:
    sayac["bicim"] += 1
    for x in re.finditer(r"(?<![\w/.\-–(])-%?\d", metin):
        hatalar.append(f"ASCII tireli eksi sayı · {ad}: {metin[max(0, x.start() - 30):x.end() + 10]!r}")
    for x in re.finditer(r"\d[ \t]*%(?!\w)", metin):
        hatalar.append(f"arkaya yazılmış yüzde · {ad}: {metin[max(0, x.start() - 20):x.end() + 5]!r}")


# ─────────────────────────────────────────────── 6 · hüküm
def dogru(kosul: bool, ne: str) -> None:
    sayac["hukum"] += 1
    if not kosul:
        hatalar.append(f"hüküm ölçümle tutmuyor: {ne}")


def hukumler(o: dict, govde: str) -> None:
    d = {k: v["deger"] for k, v in o["degerler"].items()}
    y = o["yapi"]
    dogru(d["kalipli_indirim"] == d["kalipli_karar"], "kalıplı kararların hepsi indirim ('altısı da indirim')")
    dogru(d["arsiv_indirim"] + d["arsiv_sabit"] + d["arsiv_artirim"] + 1 == d["arsiv_karar"],
          "arşiv sayımı: indirim + sabit + artırım + ilk karar = toplam")
    tablo = json.loads(gzip.decompress((VERI / "karar_tablosu.json.gz").read_bytes()))
    dogru(all(not k["kalip"] for k in tablo if k["degisim"] is not None and k["degisim"] >= 0),
          "kalıp hiçbir sabit ya da artırım kararında geçmiyor")
    # "Nisan 2025 artırımından sonra yeniden başlayan döngü" ve "ilk ayağın üç indirimi"
    ilk_ayak = [k for k in tablo if "2024-12-01" <= k["tarih"] < "2025-04-01" and (k["degisim"] or 0) < 0]
    dogru(len(ilk_ayak) == 3 and all("belirgin ve kalıcı bir bozulma" in k["ifadeler"] for k in ilk_ayak),
          "ilk ayağın (Aralık 2024–Mart 2025) üç indiriminin üçünde de sıkılaştırma koşulu var")
    dogru([k["degisim"] for k in tablo if "2025-04-01" <= k["tarih"] < "2025-07-24"] == [3.5, 0.0],
          "Nisan 2025 artırımı ve Haziran sabiti, Temmuz 2025'teki yeniden başlangıçtan önce")
    dugum = ("3a", "6a", "1y", "2y", "3y", "5y", "7y")
    dogru(all(d[f"bilesik_fark_{v}"] < 0 for v in dugum), "bütün düğümler bileşiğe çevrilmiş politika faizinin altında")
    dogru(max(dugum, key=lambda v: d[f"bilesik_fark_{v}"]) == "2y", "politika faizine en yakın düğüm 2 yıllık")
    dogru([v for v in dugum if d[f"basit_fark_{v}"] > 0] == ["6a", "1y", "2y", "3y"],
          "basit farkla yalnız 6 ay, 1, 2 ve 3 yıllık düğümler politika faizinin üstünde görünüyor")
    # sürpriz ve anketin toplantı toplantı beklentisi
    dogru(d["anket_ilk"] == d["politika_yeni"] and d["surpriz_bp"] == 0, "karar Ekim anketinin beklentisiyle birebir aynı")
    dogru(y["anket"]["kararlar"][:3] == [CIPA, "2026-12-10", "2027-01-21"], "anketin üç toplantısı takvimdeki günler")
    # eğri ile anket: ilk yıl yakınlığı iki ters sapmanın toplamı; kısa uç beklenti olamaz
    dogru(d["makas_3a_bp"] < -300 and d["makas_6a1y_bp"] > 300 and abs(d["makas_1y_bp"]) < 100,
          "ilk yıl yakınlığı kısa uçta eksi, 6–12 ayda artı iki büyük sapmanın toplamı")
    dogru(d["ima_3a_aralik_sonrasi"] < d["anket_ikinci"] - 5, "3 aylık düğüm 10 Aralık'ta beklentiden çok derin bir indirim gerektiriyor")
    dogru(d["ima_fwd_1y1y"] > max(d["pka_faiz_12a"], d["pka_faiz_24a"]),
          "ikinci yıl karşılığı anketin ikinci yıl aralığının tamamının üstünde")
    dogru(d["kalipli_sonraki_indirim"] == 4 and d["kalipli_sonraki_sabit"] == 1 and d["kalipli_onceki"] == 5,
          "kalıplı önceki beş kararın dördünü indirim, birini sabit izledi")
    dogru(d["indirim_sonrasi_indirim"] == 20 and d["indirim_sonrasi_n"] == 26
          and 0 < d["kalipli_sonraki_oran"] - d["israr_orani"] < 5,
          "kalıp, indirimden sonra indirim taban oranına neredeyse bilgi eklemiyor (26 kararın 20'si)")
    dogru(d["zamanlama_2016_sonraki_bp"] > 0, "2016'daki 'zamanlaması' metnini bir artırım izledi")
    # sıkılaştırma cümlesi döngü boyunca vardı, KOŞULU değişti (yazım yazım)
    yazim = {k["tarih"]: k["yazim"] for k in y["arsiv"]["dongu_kosul"]}
    dogru(yazim == {"2025-07-24": "araclar", "2025-09-11": "ara_hedef", "2025-10-23": "ara_hedef",
                    "2025-12-11": "ara_hedef", "2026-01-22": "ara_hedef", CIPA: "bozulma"},
          "sıkılaştırma koşulunun döngüdeki yazımları")
    dogru(d["dongu_sikilastirma_cumlesi"] == 5, "döngünün altı indiriminin beşinde sıkılaştırma cümlesi var")
    ifade = y["arsiv"]["ifade"]
    kosul = ifade["görünümünde belirgin ve kalıcı bir bozulma olması durumunda"]["tarihler"]
    dogru(kosul[0] == "2026-03-12" and kosul[-1] == CIPA, "bugünkü koşul yazımı Mart 2026'daki sabit kararla geldi")
    ihtiyat = ifade["ihtiyatlı duruşunu vurgulamıştır"]["tarihler"]
    karar_2026 = sorted(k["tarih"] for k in tablo if k["tarih"].startswith("2026-"))
    dogru(ihtiyat == [t for t in karar_2026 if t >= "2026-04-22"],
          "'ihtiyatlı duruş' cümlesi 22 Nisan'dan beri HER kararda var")
    # yıl içi geçişler: hangi paragraf kaç geçişte değişti
    gecis = y["metin"]["gecis"]
    kac = lambda rol: sum(rol in g["degisen"] for g in gecis)
    dogru(len(gecis) == 6 and kac("teşhis") == 6 and kac("duruş") == 4 and kac("kurul üyeleri") == 3
          and not any(kac(r) for r in ("makroihtiyati", "hedef", "özet notu")),
          "2026'nın altı geçişi: teşhis altısında, rehberlik dördünde, kurul üyeleri üçünde değişti")
    dogru([g["son"] for g in gecis if "duruş" not in g["degisen"]] == ["2026-07-23", "2026-09-10"],
          "rehberlik 11 Haziran, 23 Temmuz ve 10 Eylül'de aynı")
    dogru(ihtiyat[0] == "2026-04-22" and ihtiyat[-1] == CIPA and d["dongu_ihtiyatli_indirim"] == 1
          and not any(k["ihtiyatli"] for k in y["arsiv"]["kalipli"] if k["tarih"] != CIPA),
          "'ihtiyatlı duruş' cümlesi 22 Nisan'dan beri var, önceki beş indirim metninde yok")
    dogru(d["ocak_durus_ayni"] == 2 and d["ocak_durus_yeni"] == 3 and d["ocak_durus_cumle"] == 4,
          "son indirim metnine göre duruş paragrafı üç yerde ayrılıyor")
    dogru(d["degisen_paragraf"] == 3 and d["ayni_paragraf"] == 4 and d["paragraf_sayisi"] == 7,
          "yedi paragrafın üçü değişti, dördü aynı")
    dogru(d["teshis_degisen_cumle"] == 3 and d["durus_degisen_cumle"] == 1,
          "teşhiste üç, rehberlikte bir cümle değişti")
    for i in ("gerilemeyi teyit etmektedir", "zayıf seyrin devam ettiğini göstermektedir",
              "canlılığını koruyan jeopolitik gerilimler", "yukarı yönlü riskler sürmektedir"):
        dogru(ifade[i]["sayi"] == 1 and ifade[i]["ilk"] == CIPA, f"ilk kez geçen ifade: {i}")
    dogru(ifade["zayıf seyrin sürdüğüne işaret etmektedir"]["tarihler"] == ["2026-06-11"],
          "talep hükmünün anlamca yakın yazımı 11 Haziran'da")
    # "teyit" yer değiştirdi: Eylül'de talep cümlesinde, Ekim'de dezenflasyon cümlesinde
    ts = y["metin"]["cumle"]["teshis"]
    dogru("teyit etmektedir" in ts["onceki"][1] and "gerilediğine işaret" in ts["onceki"][0]
          and "teyit etmektedir" in ts["bugun"][0] and "teyit" not in ts["bugun"][1],
          "'teyit' talep cümlesinden dezenflasyon cümlesine geçti")
    dogru(ifade["zamanlaması"]["tarihler"] == ["2016-10-20", CIPA], "'zamanlaması' son kez 20 Ekim 2016'da geçti")
    dogru(ifade["Para politikası kararları enflasyon görünümü odaklı"]["sayi"] == 5,
          "kalkan cümle yalnız beş sabit kararda geçti")
    # fonlama: Mart sıkılaştırmasının geri alınması; Ocak–Şubat'a göre net fark küçük
    dogru(abs(d["net_ocak_subat_bp"]) < 50 and abs(d["blok3_makas"] - d["blok1_makas"]) < 0.1,
          "bugünkü blok Ocak–Şubat'la aynı yerde: net gevşeme bugünkü indirim")
    for a, b in (("reel_ileri", "reel_tufex_1y"), ("reel_ileri_2y", "reel_tufex_2y")):
        dogru(1.7 < d[a] / d[b] < 2.4, f"ankete göre reel getiri TÜFEX'inkinin yaklaşık iki katı ({a})")
    if "yaklaşık iki katı" not in govde:
        hatalar.append("hüküm cümlesi metinde yok: 'yaklaşık iki katı'")


# ─────────────────────────────────────────────── 7 · Eylül yazılarının düzeltmesi
# Bu yazının Bölüm 3'ü dört eski yazının eğri karşılaştırmasının konvansiyon farkını hesaba
# katmadığını söylüyor; o yazılara aynı gün tarihli düzeltme kaydı ve düzeltilmiş metin girdi.
# Kapı üç şeyi sorar: kayıt var mı (ve sayfanın güncelleme günü bugün mü), kaydın yeni değeri
# o yazının KENDİ veri gününün ölçümünde karşılık buluyor mu (`olcum.duzeltme_olcumu`), ve
# eski hüküm gövdeden gerçekten çıktı mı — çıkmadıysa sayfa iki zıt hükmü yan yana taşır.
DUZELTILEN = {
    "borclanma-programi-vade-2026-08-31": {
        "veri": "e0828",
        "yok": ["290 bp üstünde", "~290 baz puan üstünde", "indirim fiyatlamıyor", "ancak iki yıl sonrasına koyuyor"],
        "var": ["e0828_ima_1y", "e0828_patika_getirisi", "e0828_ima_fwd_1y1y", "e0828_ima_fwd_2y1y",
                "e0828_ima_fwd_2y3y"]},
    "ovp-2026-09-06": {
        "veri": "e0904",
        "yok": ["Kısa uç politika faizinin üstünde"],
        "var": ["e0904_ima_1y", "e0904_ima_2y", "e0904_ima_5y"]},
    "ppk-karari-2026-09-10": {
        "veri": "e0910", "yanit": True,
        "yok": ["+207 bp", "indirim fiyatlamıyor", "piyasa henüz fiyatlamıyor", "politika faizine göre şöyle",
                "bileşiklendirme sözleşmelerindeki fark", "politika faizinden daha yüksek"],
        "var": [f"e0910_{t}_{v}" for t in ("ima", "bilesik_fark") for v in
                ("3a", "6a", "1y", "2y", "3y", "5y", "7y", "fwd_1y1y")]
               + ["e0910_ima_3a_ekim_sonrasi", "e0910_anket_ekim", "e0910_reel_repo_bilesik"]},
    "ppk-ozeti-2026-09-17": {
        "veri": "e0916", "yanit": True,
        "yok": ["615 baz puan", "konvansiyon seçiminden gelmiyor", "Anket ile eğri uyuşmuyor"],
        "var": ["e0916_patika_getirisi", "e0916_ima_3a", "e0916_ima_3a_ekim_sonrasi", "e0916_anket_ekim"]},
}
ORTAK = ("politika_onceki", "politika_bilesik_onceki", "konvansiyon_farki")
KAYIT = re.compile(r"^  - tarih: '([^']*)'\n    alan: '((?:[^']|'')*)'\n    eski: '((?:[^']|'')*)'\n"
                   r"    yeni: '((?:[^']|'')*)'\n    sebep: '((?:[^']|'')*)'$", re.M)
# X'e düzeltme yanıtı (tweet/duzeltme.py): kaydın sonunda gonderi + gonderi_metni.
YANIT = re.compile(r"^  - tarih: '([^']*)'\n    alan: '(?:[^']|'')*'\n    eski: '((?:[^']|'')*)'\n"
                   r"    yeni: '(?:[^']|'')*'\n    sebep: '(?:[^']|'')*'\n"
                   r"    gonderi: '([^']*)'\n    gonderi_metni: '((?:[^']|'')*)'$", re.M)


class _EskiIzni:
    """Yanıt metni eski değeri "değil" diye anar ("+207 bp değil"): kaydın kendi
    `eski` alanındaki sayılar izinlidir; işaret sorulmaz, birim sorulur."""

    def __init__(self, metin: str, izin: Izin) -> None:
        self.izin, self.k = izin, set()
        for x in SAYI.finditer(metin):
            sonra = (x.group("sonra") or "").strip()
            self.k.add((x.group("cekirdek"), "%" if x.group("yuzde") else
                        {"bp": "bp", "baz puan": "bp", "gün": "gün", "puan": "puan"}.get(sonra, "")))

    def var(self, cekirdek: str, birim: str, isaret: str | None) -> bool:
        return self.izin.var(cekirdek, birim, isaret) or (cekirdek, birim) in self.k


def duzeltmeler(o: dict, govde_yeni: str) -> None:
    for slug, k in DUZELTILEN.items():
        m = (KOK / "site/src/content/analiz" / f"{slug}.mdx").read_text(encoding="utf-8")
        _, on, govde = m.split("---", 2)
        sayac["hukum"] += 1
        if not re.search(rf"^updatedDate: {CIPA}\s*$", on, re.M):
            hatalar.append(f"düzeltilen yazının güncelleme günü {CIPA} değil: {slug}")
        bugun = [r for r in KAYIT.findall(on) if r[0] == CIPA]
        if not bugun:
            hatalar.append(f"düzeltilen yazıda {CIPA} tarihli düzeltme kaydı yok: {slug}")
        izin = Izin({"degerler": {a: v for a, v in o["degerler"].items()
                                  if a.startswith(k["veri"] + "_") or a in ORTAK}})
        for r in bugun:
            for ad, metin in (("yeni", r[3]), ("sebep", r[4])):
                metin = _norm(metin.replace("''", "'"))
                envanter(f"düzeltme kaydı · {slug} · {ad}", metin, izin)
                bicim(f"düzeltme kaydı · {slug} · {ad}", metin)
        # X yanıtı yalnız ilan edilen yazıda ve yalnız o yazının kendi gönderisine.
        yanitlar = [y for y in YANIT.findall(on) if y[0] == CIPA]
        sayac["hukum"] += 1
        if len(yanitlar) != (1 if k.get("yanit") else 0):
            hatalar.append(f"X düzeltme yanıtı sayısı {len(yanitlar)} · {slug} "
                           f"(beklenen {1 if k.get('yanit') else 0})")
        for _, eski, hedef, govde_x in yanitlar:
            if hedef != f"analiz:{slug}":
                hatalar.append(f"X düzeltme yanıtı başka bir gönderiye gidiyor · {slug}: {hedef}")
            metin = _norm(govde_x.replace("''", "'"))
            envanter(f"X düzeltme yanıtı · {slug}", metin, _EskiIzni(eski.replace("''", "'"), izin))
            bicim(f"X düzeltme yanıtı · {slug}", metin)
        duz = _norm(govde)
        for x in k["yok"]:
            sayac["hukum"] += 1
            if x in duz:
                hatalar.append(f"düzeltilen hüküm gövdede hâlâ duruyor · {slug}: {x!r}")
        for a in k["var"]:
            sayac["hukum"] += 1
            if o["degerler"][a]["metin"] not in duz:
                hatalar.append(f"düzeltilmiş ölçüm gövdede yok · {slug}: {a} = {o['degerler'][a]['metin']}")
    sayac["hukum"] += 1
    if not re.search(r"31\s+Ağustos,\s+6,\s+10\s+ve\s+17\s+Eylül\s+yazılarımızdaki\s.{0,160}düzeltme\s+notu", govde_yeni, re.S):
        hatalar.append("Bölüm 3, dört yazının düzeltme notunu adıyla anmıyor")


def main() -> int:
    o = arsiv()
    if not MDX.exists():
        print(f"yazı yok: {MDX.relative_to(KOK)}")
        return 1
    m = MDX.read_text(encoding="utf-8")
    alan, govde = bolumler(m)
    # etiket silinmeden önce sorulur: taranan metinde etiketler yoktur
    if re.search(r"<Deger\b", govde):
        hatalar.append("analizde canlı <Deger> etiketi var (analizin sayıları sabittir)")
    duz, formul = taranan_metin(govde)
    izin = Izin(o)
    kaynak = kaynak_metinleri()
    for ad, metin in [("gövde", duz), ("formül", formul)] + [(f"ön bilgi · {k}", _norm(v)) for k, v in alan.items()]:
        envanter(ad, metin, izin)
        bicim(ad, metin)
    for ad, metin in [("gövde", duz)] + [(f"ön bilgi · {k}", _norm(v)) for k, v in alan.items()]:
        alintilar(metin, kaynak)
    blok_alintilar(govde, kaynak)
    hukumler(o, duz)
    duzeltmeler(o, duz)
    for k in ("politika_yeni", "politika_onceki", "anket_ilk", "ima_3a", "anket_yol_3a"):
        if o["degerler"][k]["metin"] not in alan["description"]:
            hatalar.append(f"açıklama manşet sayısını taşımıyor ({k}): {o['degerler'][k]['metin']}")
    ozet = ", ".join(f"{k} {v}" for k, v in sayac.items())
    if hatalar:
        for h in hatalar:
            print("ENGEL ·", h)
        print(f"PPK 22.10 yazısı: {len(hatalar)} engel ({ozet})")
        return 1
    print(f"PPK 22.10 yazısı: temiz ({ozet})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
