# -*- coding: utf-8 -*-
"""Yazı katmanının ihale iddiaları ile ÖLÇÜLEN takvimin kıyası — tek tanım.

NEDEN AYRI BİR MODÜL. Hüküm iki şeyden kuruluyor ve ikisi de sınanabilir
olmalı: (1) düzyazıdan tarih bağlı bir ihale iddiasını çıkarmak, (2) o günün
yürürlükteki stratejide karşılığı olup olmadığına bakmak. `denetim.py`nin
içine gömülseydi kalıbın hassasiyeti ancak tam bir bülten kurarak ölçülebilirdi.

KAYNAK CANLI PLAN DEĞİL, YÜRÜRLÜKTEKİ STRATEJİ. `hazine_planlanan_ihaleler.csv`
yalnız bugünden İLERİYİ tutar; oysa iddia dünle de ilgili olabilir ("dün yapılan
ihalenin sonuçları henüz düşmedi"). Strateji üç ayı kapsar ve arşivde
sürümleriyle durur (`takvim_arsiv/<tarih>_<ad>.csv`); PENCERE oradan gelir.
Pencerenin DIŞINDA depo bir şey bilmez ve ölçüt susar.

AMA PENCERENİN İÇİNDE HAKEM PLAN DEĞİL GERÇEKLEŞMEDİR. "Kayıt yoksa o gün ihale
YOKTUR" hükmü bir PLANA dayandırılamaz, çünkü plan iki yönde birden kayar ve
ikisi de ölçüldü (16.09.2026). İleri yönde: arşivlenen dosya canlı planın
kopyasıdır ve yapılmış ihaleyi düşürür — aynı Eylül–Kasım stratejisi 13.09'da
iki eylül günü, 14.09'da bir gün, 15.09'da hiçbiri ile arşivlendi, yani bugünün
planına sorulunca gerçekleşmiş her ihale "olmayan ihale" çıkar. Geri yönde: 17
ve 18 Ağustos ihaleleri gerçekten yapıldı ama en eski arşiv sürümünde (05.08) o
günler hiç YOK — Hazine plandan sapabilir. İkinci kusur, "iddia gününden önceki
sürüme sor" düzeltmesini de çürüttü: tarihçede 23–30 Ağustos'un altı sayısı
birden yanlış pozitif verdi.

Bu yüzden kural ÜÇ HÂLLİ ve gerçekleşme tablosunu hakem alır: gerçekleşmiş bir
gün TEMİZDİR (plan ne derse desin), gerçekleşmemiş ve GEÇMİŞ bir gün ÇELİŞKİDİR,
gerçekleşmemiş ve İLERİDEKİ bir gün plana sorulur — henüz olmamış bir ihalenin
tek kaynağı odur. Tablo okunamazsa hüküm plana kalır.

HASSASİYET ÖLÇÜLEREK KURULDU. İlk yazımda çıpa "aynı cümledeki her tarih"ti ve
13 sayıda 49 bulgu verdi; çoğu aynı cümlede geçen alakasız bir yayımdı
("4 Eylül'de ABD tarım dışı istihdamı, 7 Eylül'de … bono ihalesi" → 4 Eylül
yanlış yakalanıyordu). İki daraltma kondu: çıpa ile ihale iddiası arasında
EN ÇOK ~70 karakter olabilir, ve aralarında BAŞKA BİR TARİH bulunamaz — çıpa,
iddianın EN YAKIN tarihi olmak zorunda. Bulgu 49 → 23'e indi ve 23'ün 23'ü de
tek bir gerçek kusura (kaldırılan 07.09 bono ihalesi) çıktı.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ARSIV = KOK / "Aktarılacak Projeler" / "hazineihrac" / "takvim_arsiv"
SUTUN = "İhale Tarihi"

# PENCERE ARŞİV DOSYASININ ADINDAN TÜRETİLMEZ. İlk yazımda dosya adındaki
# tarihten (+1 ay) kuruldu ve YANLIŞ çıktı: o tarih belgenin yayım günü değil,
# hattın onu TARADIĞI gündür — aynı Eylül–Kasım stratejisi 31.08, 01.09 ve
# 06.09'da üç kez arşivlendi ve en yenisinden kurulan pencere 01.10'da
# başlıyordu, yani asıl sorulacak gün (07.09) pencerenin dışında kalıyordu.
# Ölçüt hüküm veremeden susardı.
#
# Doğru kaynak hattın KENDİ İLANI: `ozet.json`daki `plan_strateji` — belgenin
# BAŞLIĞI ("Eylül – Kasım 2026 İç Borçlanma Stratejisi"), kapsadığı dönemi
# yılıyla birlikte yazar ve ayrıştırma belirsizlik taşımaz (yıl atlayan bir
# strateji de doğru okunur).
#
# İLAN KAYMAYAN NİTELİKTEN OKUNUR. İlk yazımda çapraz sınama `plan_ay1_ad` …
# `plan_ay3_ad`dan kuruluyordu ve o alanlar belgenin kapsadığı ayları DEĞİL,
# canlı planda İLERİDE KALAN ayları sayar — `ozet_uret.py` bunu adıyla yazıyor
# ("takvimdeki ay sayısı DEĞİŞKEN"). 15.09.2026'da Eylül'ün son ihalesi geçince
# canlı plan Ekim–Kasım'a düştü, ilan 01.10'da başladı, dosya adı 01.09'da
# başlamaya devam etti ve duman sınaması DÜŞTÜ — kapı adımlardan önce koştuğu
# için 16.09 sabahı veri hiç tazelenmedi. Aynı sınıfın bir eşi 14.09'da
# ölçülmüştü: canlı bir dosyada yalnız KAYMAYAN nitelik sorulur.
OZET = KOK / "site" / "public" / "projeler" / "hazine-ihrac" / "ozet.json"
TABLOLAR = KOK / "site" / "public" / "projeler" / "hazine-ihrac" / "tablolar.json"

AY = {"ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
      "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12}
_AYK = "|".join(AY)

# Çıpa ile iddia arasında BAŞKA TARİH OLAMAZ (bkz. modül başlığı).
_ARA = (r"(?:(?!\d{1,2}\s+(?:" + _AYK + r")|\bBugün\b|\bDün\b|\bYarın\b)[^.!?]){0,70}?")
_KIYMET = r"(?:Hazine|bono|tahvil|kira sertifika|altın tahvil)"
KALIP = re.compile(
    r"(?:(Bugün|Dün|Yarın)|(\d{1,2})\s+(" + _AYK + r"))"
    + _ARA + _KIYMET + _ARA + r"(?:ihale|ihra[cç])", re.I)
# Olumsuz ya da ölçülemezlik bildiren cümle iddia değildir.
OLUMSUZ = re.compile(r"\b(yok|bulunmuyor|boş|yapılmıyor|planlanmıyor|iptal|"
                     r"ölçülemez|kaldırıl|çıkarıl)\b", re.I)
KAYMA = {"bugün": 0, "dün": -1, "yarın": 1}


def _tarihe(m: str) -> dt.date | None:
    for kalip in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(m[:10], kalip).date()
        except ValueError:
            continue
    return None


def _ay_ekle(g: dt.date, n: int) -> dt.date:
    ay = g.month + n
    return dt.date(g.year + (ay - 1) // 12, (ay - 1) % 12 + 1, 1)


def yururlukteki(simdi: dt.date | None = None) -> tuple[set[dt.date], dt.date, dt.date] | None:
    """(ihale günleri, pencere başı, pencere sonu) — en yeni strateji sürümü.

    Döner `None`: arşiv okunamadı. Ölçüt o zaman hüküm vermez, susmaz da."""
    if not ARSIV.exists():
        return None
    simdi = simdi or dt.date.today()
    adaylar = []
    for y in ARSIV.glob("*.csv"):
        g = _tarihe(y.name[:10])
        if g and g <= simdi:
            adaylar.append((g, y))
    if not adaylar:
        return None
    damga, yol = max(adaylar)
    gunler: set[dt.date] = set()
    try:
        with yol.open(encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            kol = next((k for k in (r.fieldnames or []) if k and SUTUN in k), None)
            if not kol:
                # Sütun adı değişmiş: "bulunamadı" demek ama neyin
                # bulunabileceğini söylememek, ayrı bir keşif koşusu demektir.
                print(f"  [uyarı] {yol.name}: '{SUTUN}' sütunu yok; "
                      f"dosyadaki sütunlar: {[k for k in (r.fieldnames or []) if k]}")
                return None
            for satir in r:
                g = _tarihe(str(satir.get(kol) or ""))
                if g:
                    gunler.add(g)
    except OSError:
        return None
    if not gunler:
        return None
    # PENCERE, GÜNLERİ VEREN BELGENİN KENDİSİNDEN. Aynı yerden türetmek zorunlu:
    # günleri bir stratejiden, pencereyi başkasından almak tarihçeye karşı
    # koşulduğunda tutarsız bir hüküm üretir (eski bir sayıyı bugünün
    # penceresiyle ölçmek gibi).
    pencere = pencere_adi(yol.name)
    if pencere is None:
        return None
    return gunler, pencere[0], pencere[1]


def pencere_adi(ad: str) -> tuple[dt.date, dt.date] | None:
    """Arşiv dosyasının adından stratejinin kapsadığı dönem.

    Ad hattın kendi ürettiği belge başlığından geliyor:
    `2026-08-31_Eylül--Kasım-2026-İç-Borçlanma-Stratejisi.csv`. Dosyanın
    BAŞINDAKİ tarih belgenin yayım günü DEĞİL, hattın onu taradığı gündür —
    aynı strateji üç kez arşivlenmiş olabilir — bu yüzden pencere oradan
    türetilemez; ay adlarından türetilir. Yıl atlayan bir strateji
    (Aralık–Şubat) de doğru okunur: bitiş ayı başlangıçtan küçükse yıl artar."""
    aylar = re.findall(r"(" + _AYK + r")", ad, re.I)
    yil = re.search(r"(20\d{2})", ad)
    if len(aylar) < 2 or not yil:
        return None
    a1, a2 = AY[aylar[0].lower()], AY[aylar[-1].lower()]
    y1 = int(yil.group(1))
    y2 = y1 + (1 if a2 < a1 else 0)
    bas = dt.date(y1, a1, 1)
    son = _ay_ekle(dt.date(y2, a2, 1), 1) - dt.timedelta(days=1)
    return bas, son


def pencere_ilani() -> tuple[dt.date, dt.date] | None:
    """Hattın `ozet.json`daki ilanı (`plan_strateji`) — ÇAPRAZ SINAMA için.

    Belge başlığı ile arşiv dosyasının adı hattın İKİ ayrı yerinden gelir ve
    aynı dönemi söylemek zorundadır; tutmuyorsa biri yanlış ayrıştırıyor
    demektir ve bunu duman sınaması sorar. Ay listesi (`plan_ay*_ad`) bu
    soruya CEVAP VEREMEZ: o alanlar ileride kalan ayları sayar ve takvim
    ilerledikçe daralır (bkz. modül başlığı)."""
    import json
    try:
        d = json.loads(OZET.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return pencere_adi(str(d.get("plan_strateji") or ""))


def gerceklesen() -> set[dt.date] | None:
    """Gerçekleşmiş ihale günleri — hattın ihale tablosundan.

    Plan kayar, gerçekleşme kaymaz: bir gün bu kümedeyse o gün ihale YAPILMIŞTIR
    ve hiçbir plan sürümü bunun aksini söyleyemez. Döner `None`: tablo okunamadı
    (hüküm plana kalır)."""
    import json
    try:
        d = json.loads(TABLOLAR.read_text(encoding="utf-8"))
        t = (d.get("tablolar") or {}).get("ihaleler") or {}
        kol = t["sutunlar"].index(SUTUN)
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        return None
    gunler = {g for g in (_tarihe(str(s[kol])) for s in t.get("satirlar") or []
                          if len(s) > kol) if g}
    return gunler or None


def iddialar(b: dict) -> list[dict]:
    """Bültenin düzyazısındaki tarih bağlı ihale iddiaları."""
    try:
        bugun = dt.date.fromisoformat(str(b.get("tarih")))
    except (TypeError, ValueError):
        return []
    sys.path.insert(0, str(BURASI))
    import tekrar                                              # noqa: E402
    out: list[dict] = []
    for alan, metin in tekrar.bolumler(b).items():
        for m in KALIP.finditer(metin):
            parca = m.group(0)
            # OLUMSUZLUK CÜMLENİN TAMAMINDA ARANIR, eşleşen parçada değil:
            # kalıp "…ihale" ile biter ve "Bugün Hazine'nin ihale takviminde
            # kayıt YOK" cümlesinde olumsuzluk eşleşmenin ARDINDA kalıyordu —
            # yani bir yokluk bildirimi iddia sayılıyordu.
            bas = max(metin.rfind(".", 0, m.start()), metin.rfind("!", 0, m.start()),
                      metin.rfind("?", 0, m.start())) + 1
            son = min([x for x in (metin.find(".", m.end()), metin.find("!", m.end()),
                                   metin.find("?", m.end())) if x != -1] or [len(metin)])
            cumle = metin[bas:son + 1]
            if OLUMSUZ.search(cumle):
                continue
            if m.group(1):
                etiket = m.group(1)
                gun = bugun + dt.timedelta(days=KAYMA[etiket.lower()])
            else:
                try:
                    gun = dt.date(bugun.year, AY[m.group(3).lower()], int(m.group(2)))
                except (ValueError, KeyError):
                    continue
                etiket = f"{m.group(2)} {m.group(3)}"
            out.append({"alan": alan, "etiket": etiket, "gun": gun,
                        "parca": parca[:120]})
    return out


def celiskiler(b: dict, simdi: dt.date | None = None) -> list[dict] | None:
    """Yürürlükteki stratejinin KAPSADIĞI dönemde karşılığı olmayan iddialar.

    Döner `None`: strateji okunamadı (hüküm verilemez)."""
    try:
        bugun = dt.date.fromisoformat(str(b.get("tarih")))
    except (TypeError, ValueError):
        return []
    takvim = yururlukteki(simdi or bugun)
    if takvim is None:
        return None
    gunler, bas, son = takvim
    # YAYIMLANMIŞ DÜZELTME ÇELİŞKİYİ KAPATIR. Sayfanın "Düzeltmeler" bölümü
    # okura o iddianın düzeltildiğini aynı sayfada söylüyor; eski iddiayı
    # metinden silmek tarihçeyi yeniden yazmak olurdu (okur eski sayıya göre
    # karar vermiş olabilir). Kapsam, düzeltme kaydının `alan`ında iddianın
    # tarih etiketinin ("7 Eylül") geçmesiyle kurulur — başka bir tarihi
    # düzelten kayıt bu iddiayı kapatmaz.
    duzeltilen = [str(d.get("alan") or "") for d in (b.get("duzeltmeler") or [])
                  if isinstance(d, dict)]

    # GEÇMİŞİN HAKEMİ PLAN DEĞİL GERÇEKLEŞMEDİR.
    #
    # Strateji belgesi bir PLANDIR ve iki yönde birden kayar. (1) Arşivlenen
    # dosya canlı planın kopyasıdır ve YAPILMIŞ ihaleyi düşürür: aynı
    # Eylül–Kasım stratejisi 13.09'da iki eylül günü (14 · 15), 14.09'da bir gün
    # (15), 15.09'da HİÇBİRİ ile arşivlendi. Bugünün planına sorulunca
    # gerçekleşmiş her ihale "olmayan ihale" çıkar — 16.09.2026'da tam bu oldu
    # ve 15 Eylül'ün iki yeniden ihracını anlatan MEŞRU bir paragraf yayını
    # durdurdu. (2) Plan geriye doğru da eksiktir: 17 ve 18 Ağustos ihaleleri
    # gerçekten yapıldı ama en eski arşiv sürümünde (05.08) o günler YOK, yani
    # "iddia gününden önceki sürüme sor" kuralı da yanlış alarm üretiyor —
    # ölçüldü, tarihçede 23–30 Ağustos'un altı sayısı birden kusurlu çıktı.
    # Hazine plandan sapabilir; plan, olmuş bir ihalenin kanıtı değildir.
    #
    # Gerçekleşme tablosu ise kesin bilgidir ve hattın kendi çıktısında duruyor.
    # Kural üç hâlli: gerçekleşmiş bir gün TEMİZDİR (plan ne derse desin);
    # gerçekleşmemiş ve GEÇMİŞ bir gün ÇELİŞKİDİR; gerçekleşmemiş ve İLERİDEKİ
    # bir gün plana sorulur, çünkü henüz olmamış bir ihalenin tek kaynağı odur.
    # Tablo okunamazsa hüküm plana kalır — bilinen davranış, sessiz körlük değil.
    olan = gerceklesen()
    bul = []
    for x in iddialar(b):
        if not (bas <= x["gun"] <= son):
            continue
        if any(x["etiket"] in a for a in duzeltilen):
            continue
        if olan is not None and x["gun"] in olan:
            continue                      # gerçekten yapılmış: hüküm yok
        if olan is not None and x["gun"] <= bugun:
            bul.append(x)                 # geçmiş gün, gerçekleşme yok
        elif x["gun"] not in gunler:
            bul.append(x)                 # ileriki gün, planda da yok
    return bul
