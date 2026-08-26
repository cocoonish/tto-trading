#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — ekonomik takvim.

Dört kaynak, dört güvenilirlik seviyesi. Her satır KENDİ kaynağını ve
kesinliğini taşır; bülten bunu okura gösterir (tahmini tarihi kesin gibi
sunmak, bültenin en kolay yalanı olurdu):

  hazine   → kendi hattımızın ayrıştırdığı Hazine ihale programı   [kesin]
             + o ihale için KENDİ modelimizin beklentisi
  fed      → federalreserve.gov FOMC takvimi (kazıma)              [kesin]
  ecb      → ecb.europa.eu Yönetim Konseyi para politikası takvimi [kesin]
  elle     → takvim_elle.json: TR (TÜİK/TCMB) ve ABD/EA veri günleri.
             Her kayıt "kesin" (resmî takvimden doğrulanmış) ya da "kural"
             (ör. 'ayın 3'ü' kuralıyla türetilmiş) olarak işaretlidir.

Ağ erişimi olmayan ortamda (cron kısıtlı olabilir) kazıyıcılar sessizce boş
döner ve önbellekteki son başarılı sonuç kullanılır — takvim hiç yoktan iyidir,
ama bayat olduğu da SÖYLENİR.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ONBELLEK = BURASI / "onbellek"
ONBELLEK.mkdir(exist_ok=True)
ELLE = BURASI / "takvim_elle.json"

AYLAR_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
            "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


@dataclass
class Kayit:
    tarih: str            # YYYY-MM-DD
    saat: str = ""        # "10:00" (TSİ) — bilinmiyorsa boş
    ulke: str = "TR"
    olay: str = ""
    onem: int = 2         # 1 = kritik, 2 = önemli, 3 = takip
    kaynak: str = ""
    kesinlik: str = "kesin"   # kesin | kural | tahmini
    beklenti: str = ""        # varsa: anket/model beklentisi (serbest metin)
    # Sayısal beklenti AYRI durur ve serbest metinden TÜRETİLMEZ. Metni
    # ayrıştırmak tahmin üretir; tahminden hesaplanan bir "sürpriz" uydurma
    # olur. Yalnız elle girilen ya da kendi modelimizden gelen sayı buraya yazılır
    # ve sürpriz ancak bu alan doluysa hesaplanır (bkz. surpriz.py).
    beklenti_sayi: float | None = None
    onceki: str = ""          # varsa: bir önceki gerçekleşme
    not_: str = ""

    def gun_adi(self) -> str:
        return GUNLER_TR[datetime.strptime(self.tarih, "%Y-%m-%d").weekday()]

    def tr_tarih(self) -> str:
        d = datetime.strptime(self.tarih, "%Y-%m-%d")
        return f"{d.day} {AYLAR_TR[d.month - 1]} {d.year}"


def _onbellege_yaz(ad: str, veri):
    (ONBELLEK / f"{ad}.json").write_text(
        json.dumps({"zaman": datetime.now().isoformat(timespec="seconds"), "veri": veri},
                   ensure_ascii=False, indent=1), encoding="utf-8")


def _onbellekten(ad: str):
    y = ONBELLEK / f"{ad}.json"
    if not y.exists():
        return None, None
    try:
        d = json.loads(y.read_text(encoding="utf-8"))
        return d.get("veri"), d.get("zaman")
    except Exception:
        return None, None


def _getir(url: str, zaman_asimi=25) -> str | None:
    try:
        import requests
        r = requests.get(url, timeout=zaman_asimi, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8"})
        return r.text if r.ok else None
    except Exception:
        return None


# ────────────────────────────────────────────────────────── Hazine (kendi hattımız)
def hazine(ufuk_gun: int = 21) -> list[Kayit]:
    y = KOK / "Aktarılacak Projeler" / "hazineihrac" / "tablolar.json"
    if not y.exists():
        return []
    try:
        t = json.loads(y.read_text(encoding="utf-8"))["tablolar"]["planli"]
    except Exception:
        return []
    sut = {ad: i for i, ad in enumerate(t["sutunlar"])}
    bugun = date.today()
    out = []
    for r in t["satirlar"]:
        try:
            g = datetime.strptime(r[sut["İhale Tarihi"]], "%d.%m.%Y").date()
        except Exception:
            continue
        if not (bugun <= g <= bugun + timedelta(days=ufuk_gun)):
            continue
        senet = r[sut["Senet Tanımı"]]
        vade = r[sut["Vade Terimi"]]
        yontem = str(r[sut["Yöntem"]])
        tahmin = r[sut.get("Tahmini Gerçekleşme (Milyon TL)", -1)] if "Tahmini Gerçekleşme (Milyon TL)" in sut else None
        b2c = r[sut["Tahmini Bid-to-Cover"]] if "Tahmini Bid-to-Cover" in sut else None
        bek = ""
        if tahmin:
            bek = f"model: {tahmin/1000:.1f} mlr TL gerçekleşme"
            if b2c:
                bek += f", teklif/karşılama {b2c:.2f}"
        elif "Doğrudan" in yontem:
            bek = "doğrudan satış — ihale tahmini yok"
        out.append(Kayit(g.isoformat(), "", "TR",
                         f"Hazine: {senet} ({vade}) — {yontem}",
                         onem=1 if "İhale" in yontem else 2,
                         kaynak="Hazine ihale programı (kendi hattımız)",
                         kesinlik="kesin", beklenti=bek))
    return out


# ────────────────────────────────────────────── TÜİK Ulusal Veri Yayımlama Takvimi
# Türkiye'nin RESMÎ veri takvimi: TÜİK, TCMB, Hazine (HMB), BDDK, SPK hepsi burada,
# tarih + SAAT + dönem bilgisiyle. Uç nokta sayfanın kendi kullandığı JSON servisidir.
# Günde onlarca kayıt geliyor; ayar.TAKVIM_KURALLARI ile önem filtresinden geçirilir.
TUIK_UC = "https://www.tuik.gov.tr/Kurumsal/GetYillikHaberBulteniListesi?yil={yil}"


def _tuik_onem(ad: str):
    from ayar import TAKVIM_KURALLARI
    for kalip, onem, kisa in TAKVIM_KURALLARI:
        if re.search(kalip, ad, re.I):
            return onem, kisa
    return None, None


def tuik(ufuk_gun: int = 21, asgari_onem: int = 2) -> list[Kayit]:
    bugun, son = date.today(), date.today() + timedelta(days=ufuk_gun)
    yillar = sorted({bugun.year, son.year})
    ham = []
    for y in yillar:
        try:
            import requests
            r = requests.get(TUIK_UC.format(yil=y), timeout=40, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.tuik.gov.tr/Kurumsal/Veri_Takvimi"})
            if r.ok:
                d = r.json()
                ham += d.get("yayindaOlmayanlarList", []) + d.get("yayindaOlanlarList", [])
        except Exception:
            continue
    if not ham:
        veri, zaman = _onbellekten("tuik")
        if not veri:
            return []
        kayitlar = [Kayit(**k) for k in veri]
        for k in kayitlar:
            k.not_ = (k.not_ + " (önbellekten; takvim servisi okunamadı)").strip()
        return [k for k in kayitlar if bugun.isoformat() <= k.tarih <= son.isoformat()]

    out: list[Kayit] = []
    gorulen = set()
    for x in ham:
        g = str(x.get("gTarih", ""))[:10]
        if not (bugun.isoformat() <= g <= son.isoformat()):
            continue
        ad = x.get("adi") or ""
        onem, kisa = _tuik_onem(ad)
        if onem is None or onem > asgari_onem:
            continue
        anahtar = (g, ad)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        saat = str(x.get("gTarih", ""))[11:16]
        kurum = x.get("sorumluKisaAd") or ""
        donem = x.get("donemi") or ""
        out.append(Kayit(g, saat, "TR", f"{kurum}: {kisa or ad}" + (f" ({donem})" if donem else ""),
                         onem=onem, kaynak="TÜİK Ulusal Veri Yayımlama Takvimi",
                         kesinlik="kesin", not_=ad if kisa and kisa != ad else ""))
    if out:
        _onbellege_yaz("tuik", [asdict(k) for k in out])
    return out


# ────────────────────────────────────────────────────────── Fed
def fed(yil: int | None = None) -> list[Kayit]:
    """FOMC toplantıları. Sayfa yıl panelleri hâlinde: '2026 FOMC Meetings' başlığı
    altında 'January 27-28', 'March 17-18*' biçiminde ay + gün aralığı.
    Karar toplantının İKİNCİ günü açıklanır; takvime o gün yazılır.
    'Minutes: ... (Released February 18, 2026)' satırları da ay+gün kalıbına uyar;
    ardından virgül+yıl geldiği için ELENİR (yoksa tutanak günü toplantı sanılırdı).
    """
    yil = yil or date.today().year
    ham = _getir("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    if not ham:
        veri, _ = _onbellekten("fed")
        return [Kayit(**k) for k in (veri or [])]
    duz = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", ham))
    AYLAR = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
    kayitlar: list[Kayit] = []
    bloklar = re.split(r"(?=\d{4} FOMC Meetings)", duz)
    for blok in bloklar:
        m = re.match(r"(\d{4}) FOMC Meetings", blok)
        if not m:
            continue
        blok_yil = int(m.group(1))
        if blok_yil < yil:
            continue
        for mm in re.finditer(r"\b(" + "|".join(AYLAR) + r")\s+(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?(\*?)", blok):
            kuyruk = blok[mm.end():mm.end() + 8]
            if re.match(r"\s*,\s*\d{4}", kuyruk):          # "February 18, 2026" → tutanak
                continue
            ay = AYLAR.index(mm.group(1)) + 1
            gun = int(mm.group(3) or mm.group(2))
            try:
                g = date(blok_yil, ay, gun)
            except ValueError:
                continue
            kayitlar.append(Kayit(g.isoformat(), "21:00", "ABD", "Fed (FOMC) faiz kararı",
                                  onem=1, kaynak="federalreserve.gov", kesinlik="kesin",
                                  not_="Karar TSİ 21:00 civarı, toplantının ikinci günü."))
    gorulen, tekil = set(), []
    for k in sorted(kayitlar, key=lambda x: x.tarih):
        if k.tarih not in gorulen:
            gorulen.add(k.tarih)
            tekil.append(k)
    if tekil:
        _onbellege_yaz("fed", [asdict(k) for k in tekil])
    return tekil


# ────────────────────────────────────────────────────────── ECB
def ecb() -> list[Kayit]:
    """ECB Yönetim Konseyi PARA POLİTİKASI toplantıları.

    Sayfa 'GG/AA/YYYY' + açıklama satırlarından oluşuyor. Karar ikinci gün
    ('Day 2, followed by press conference') açıklanır; takvime o gün yazılır.
    'non-monetary policy meeting' satırları elenir — onlar faiz kararı değildir.
    """
    ham = _getir("https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html")
    if not ham:
        veri, _ = _onbellekten("ecb")
        return [Kayit(**k) for k in (veri or [])]
    duz = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", ham))
    kayitlar: list[Kayit] = []
    for m in re.finditer(r"(\d{2})/(\d{2})/(\d{4})((?:(?!\d{2}/\d{2}/\d{4}).){0,220})", duz):
        aciklama = m.group(4).lower()
        if "non-monetary" in aciklama or "monetary policy meeting" not in aciklama:
            continue
        if "press conference" not in aciklama:            # birinci gün: karar yok
            continue
        try:
            g = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        kayitlar.append(Kayit(g.isoformat(), "16:15", "EA", "ECB para politikası kararı",
                              onem=1, kaynak="ecb.europa.eu", kesinlik="kesin",
                              not_="Karar TSİ 16:15, basın toplantısı 16:45."))
    gorulen, tekil = set(), []
    for k in sorted(kayitlar, key=lambda x: x.tarih):
        if k.tarih not in gorulen:
            gorulen.add(k.tarih)
            tekil.append(k)
    if tekil:
        _onbellege_yaz("ecb", [asdict(k) for k in tekil])
    return tekil


# ────────────────────────────────────────────────────────── elle küratörlü
def _is_gunu(g: date) -> date:
    while g.weekday() >= 5:
        g += timedelta(days=1)
    return g


def elle(ufuk_gun: int = 21) -> list[Kayit]:
    """takvim_elle.json: kesin tarihler + 'ayın N'i' kuralıyla türetilenler."""
    if not ELLE.exists():
        return []
    d = json.loads(ELLE.read_text(encoding="utf-8"))
    bugun, son = date.today(), date.today() + timedelta(days=ufuk_gun)
    out: list[Kayit] = []

    for k in d.get("kesin", []):
        try:
            g = date.fromisoformat(k["tarih"])
        except Exception:
            continue
        if bugun <= g <= son:
            out.append(Kayit(k["tarih"], k.get("saat", ""), k.get("ulke", "TR"), k["olay"],
                             k.get("onem", 2), k.get("kaynak", ""), "kesin",
                             k.get("beklenti", ""), k.get("onceki", ""), k.get("not", "")))

    # kural: her ay ayın N'inde (hafta sonuna denk gelirse ilk iş günü)
    for k in d.get("kural", []):
        for ay_ofset in range(0, 3):
            y, m = bugun.year, bugun.month + ay_ofset
            y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
            try:
                g = date(y, m, int(k["gun"]))
            except ValueError:
                continue
            if k.get("is_gunune_kaydir", True):
                g = _is_gunu(g)
            if bugun <= g <= son:
                out.append(Kayit(g.isoformat(), k.get("saat", ""), k.get("ulke", "TR"),
                                 k["olay"], k.get("onem", 2), k.get("kaynak", ""), "kural",
                                 k.get("beklenti", ""), k.get("onceki", ""),
                                 k.get("not", "Tarih kuralla türetildi; resmî takvimle doğrulanmalı.")))
    return out


# ────────────────────────────────────────────────────────── birleştir
def topla(ufuk_gun: int = 21, asgari_onem: int = 2) -> list[Kayit]:
    hepsi = hazine(ufuk_gun) + elle(ufuk_gun) + tuik(ufuk_gun, asgari_onem)
    bugun, son = date.today(), date.today() + timedelta(days=ufuk_gun)
    for k in fed() + ecb():
        try:
            g = date.fromisoformat(k.tarih)
        except Exception:
            continue
        if bugun <= g <= son:
            hepsi.append(k)
    hepsi.sort(key=lambda k: (k.tarih, k.onem, k.saat))
    return hepsi


def hafta_gruplari(kayitlar: list[Kayit]) -> list[tuple[str, list[Kayit]]]:
    """Takvimi 'bu hafta / gelecek hafta / sonraki' diye üçe ayır.

    PAZAR İSTİSNASI: pazar günü içinde bulunulan hafta fiilen bitmiştir ve o günün
    raporu zaten YARIN başlayan hafta için yazılır. Takvimi takvimsel haftaya göre
    bölmek, pazar bülteninde "Bu hafta (0)" gibi anlamsız bir boş blok üretiyordu.
    Bu yüzden pazar günü "bu hafta" = yarından itibaren gelecek pazara kadar.
    """
    bugun = date.today()
    pazar_mi = bugun.weekday() == 6
    if pazar_mi:
        bas = bugun + timedelta(days=1)                  # yarın: pazartesi
        hafta_sonu = bas + timedelta(days=6)             # gelecek pazar
        basliklar = ("Önümüzdeki hafta", "Sonraki hafta", "İki hafta sonrası")
    else:
        hafta_sonu = bugun + timedelta(days=(6 - bugun.weekday()))
        basliklar = ("Bu hafta", "Gelecek hafta", "Sonraki iki hafta")
    gelecek_sonu = hafta_sonu + timedelta(days=7)
    kova = {"bu": [], "gelecek": [], "sonra": []}
    for k in kayitlar:
        g = date.fromisoformat(k.tarih)
        kova["bu" if g <= hafta_sonu else "gelecek" if g <= gelecek_sonu else "sonra"].append(k)
    return [(basliklar[0], kova["bu"]), (basliklar[1], kova["gelecek"]),
            (basliklar[2], kova["sonra"])]


if __name__ == "__main__":
    for baslik, grup in hafta_gruplari(topla(21)):
        print(f"\n=== {baslik} ({len(grup)})")
        for k in grup:
            kes = "" if k.kesinlik == "kesin" else f"  [{k.kesinlik}]"
            print(f"  {k.tr_tarih():18s} {k.gun_adi():10s} {k.ulke:3s} {k.olay[:62]:64s}"
                  f"{('· ' + k.beklenti) if k.beklenti else ''}{kes}")
