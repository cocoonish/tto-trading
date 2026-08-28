#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — beklenti halkasını kapatan katman: ne bekleniyordu, ne geldi.

Takvim bugüne dek yalnız İLERİ bakıyordu: hangi veri ne zaman çıkacak, beklenti
nedir. Veri çıktıktan sonra bülten onu unutuyordu. Oysa bir sabah notunun en
değerli tek tablosu geriye bakan tablodur — dün ne bekleniyordu, ne geldi,
piyasa ne yaptı. Beklenti yayımlayıp gerçekleşmeyi yayımlamamak, söz verip
hesabını vermemektir.

Üç parça ayrı ayrı üretilir ve ASLA birbirinin yerine geçmez:

  gerçekleşme  Bu deponun kendi hattından okunur. Yayım anı ile verinin hatta
               düşmesi arasında saatler geçtiği için hattın KENDİ saati sınanır:
               alanın veri tarihi olay gününden eskiyse "henüz düşmedi" denir.
               Hattın tarihini varsaymak, eski sayıyı yeni yayım diye sunmak olur.
  sürpriz      Yalnız SAYISAL bir beklenti varsa hesaplanır. Takvimdeki serbest
               metin beklenti ("anket: yıl sonu %29,43 · 12 ay sonrası…") sayıya
               çevrilmez; ayrıştırma tahmin üretir, tahmin de sürpriz diye
               yayımlanırsa uydurma olur.
  tepki        Piyasanın olaydan bu yana hareketi. Pencere olayın YAŞINA göre
               seçilir ve etiketiyle birlikte yazılır — "1 günlük" ile "1
               haftalık" tepkiyi aynı hücrede göstermek okuru yanıltır.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import gozlem

BURASI = Path(__file__).resolve().parent

# Olayın yaşı (takvim günü) → piyasa fotoğrafındaki hazır pencere ve etiketi.
TEPKI_PENCERE = ((1, "d1", "1 gün"), (5, "h1", "1 hafta"), (21, "a1", "1 ay"))


@dataclass(frozen=True)
class Takip:
    """Bir takvim olayının gerçekleşmesi hangi hattın hangi alanında okunur."""

    kalip: str                       # takvim olay adında aranan kalıp (regex)
    hat: str
    anahtar: str
    ad: str                          # bültende görünecek büyüklük adı
    birim: str = ""
    ondalik: int = 2
    tarih_alani: str = ""            # alanın kendi saati (boşsa gelenek/ana saat)
    tepki: tuple[str, ...] = ()      # olaydan sonra bakılacak enstrümanlar


# Kalıplar takvimdeki GERÇEK olay adlarından türetildi (bkz. takvim.py çıktısı).
# Bir olayın buraya kaydı yoksa bülten onu yalnız "gerçekleşti" diye anar;
# uydurma bir eşleştirme yanlış sayı yayımlamaktan iyidir değil, kötüsüdür.
TAKIPLER: tuple[Takip, ...] = (
    Takip(r"Haftalık para-banka|Haftalık Para ve Banka", "kredi-parasal", "g_ar_13y",
          "Kur arındırılmış kredi büyümesi (13 hafta yıllıklandırılmış)", "%", 1,
          tepki=("USD/TRY", "BIST 100")),
    Takip(r"IRFCL|Uluslararası Rezervler", "tcmb-net-rezerv", "h_net",
          "Net rezerv (haftalık, resmî)", "mlr USD", 1, "h_tarih",
          tepki=("USD/TRY",)),
    Takip(r"TÜFE|Tüketici Fiyat", "enflasyon", "tufe_aylik",
          "Aylık TÜFE", "%", 2, tepki=("USD/TRY", "BIST 100")),
    Takip(r"Yİ-ÜFE|Yurt İçi Üretici", "enflasyon", "yiufe_aylik",
          "Aylık Yİ-ÜFE", "%", 2),
    Takip(r"Ödemeler dengesi", "odemeler-dengesi", "cari12_mia",
          "Cari denge (12 aylık birikimli)", "mlr USD", 1, tepki=("USD/TRY",)),
    Takip(r"Menkul kıymet ist\.", "yabanci-pozisyon", "toplam_hafta",
          "Yabancı haftalık net akım", "mn USD", 0, tepki=("BIST 100",)),
    Takip(r"Bütçe dengesi|Merkezi Yönetim Bütçe", "butce-borc", "butce_ay",
          "Aylık bütçe dengesi", "mlr TL", 1),
)


# ── takvim arşivi ────────────────────────────────────────────────────────────
# Takvim modülü yalnız İLERİ bakar: bugünden sonraki yayımları listeler. Geçmiş
# olayları sonradan kaynaktan çekmek iki bakımdan yanlış olurdu. Birincisi ağ
# bağımlılığı: kaynak düşerse geriye bakan tablo da düşer. İkincisi ve asıl
# önemlisi, "ne bekleniyordu" sorusunun doğru cevabı O GÜN yayımladığımız
# beklentidir — sonradan güncellenmiş bir anket değil. O yüzden her koşuda
# gördüğümüz takvim kaydı arşive düşer ve geriye bakan tablo arşivden kurulur.
ARSIV = BURASI / "takvim_arsiv.json"


def arsiv_oku() -> dict:
    if not ARSIV.exists():
        return {}
    try:
        return json.loads(ARSIV.read_text(encoding="utf-8")).get("kayitlar", {})
    except (ValueError, OSError):
        return {}


def _alan(k, ad, varsayilan=""):
    return getattr(k, ad, None) if not isinstance(k, dict) else k.get(ad, varsayilan)


def arsivle(kayitlar: list) -> int:
    """Bu koşuda görülen takvim kayıtlarını arşive ekle. Dönüş: yeni kayıt sayısı.

    Var olan kayıt EZİLMEZ: ilk görüldüğü hâli, yani o günkü beklenti korunur.
    """
    d = arsiv_oku()
    yeni = 0
    for k in kayitlar:
        tarih = str(_alan(k, "tarih") or "")[:10]
        olay = str(_alan(k, "olay") or "").strip()
        if not tarih or not olay:
            continue
        anahtar = f"{tarih}|{olay}"
        if anahtar in d:
            continue
        d[anahtar] = {"tarih": tarih, "olay": olay,
                      "saat": _alan(k, "saat", "") or "",
                      "ulke": _alan(k, "ulke", "") or "",
                      "onem": _alan(k, "onem", 2),
                      "beklenti": _alan(k, "beklenti", "") or "",
                      "beklenti_sayi": _alan(k, "beklenti_sayi", None),
                      "gorulme": datetime.now().date().isoformat()}
        yeni += 1
    if yeni:
        ARSIV.write_text(json.dumps(
            {"_aciklama": "Takvimde GÖRÜLMÜŞ her olayın ilk hâli. 'Ne bekleniyordu' "
                          "sorusunun cevabı o gün yayımladığımız beklentidir; sonradan "
                          "güncellenen bir anket değil. Kayıtlar ezilmez.",
             "_son_guncelleme": datetime.now().date().isoformat(),
             "kayitlar": dict(sorted(d.items()))},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return yeni


def _gun(m) -> date | None:
    try:
        return datetime.fromisoformat(str(m)[:10]).date()
    except (ValueError, TypeError):
        return None


def _tr_gun(m) -> date | None:
    """`24.08.2026` biçimli veri tarihini çöz (hatların yazdığı biçim)."""
    for kalip in ("%d.%m.%Y", "%Y-%m-%d", "%m.%Y", "%Y-%m"):
        try:
            return datetime.strptime(str(m)[:10], kalip).date()
        except (ValueError, TypeError):
            continue
    return None


def _takip(olay: str) -> Takip | None:
    for t in TAKIPLER:
        if re.search(t.kalip, olay or "", re.I):
            return t
    return None


def _tepki(piyasa: dict, adlar: tuple[str, ...], yas: int) -> dict:
    """Belirlenen enstrümanların olaydan bu yana hareketi — penceresi etiketli."""
    alan, etiket = "a1", "1 ay"
    for sinir, a, e in TEPKI_PENCERE:
        if yas <= sinir:
            alan, etiket = a, e
            break
    satirlar = {s["ad"]: s for g in (piyasa or {}).get("gruplar", [])
                for s in g.get("satirlar", [])}
    kalemler = []
    for ad in adlar:
        s = satirlar.get(ad)
        if not s or s.get(alan) is None:
            continue
        kalemler.append({"ad": ad, "deger": s[alan], "birim": s.get("degisim_birim", "%"),
                         "sigma": s.get("d1_sigma") if alan == "d1" else None})
    return {"pencere": etiket, "kalemler": kalemler} if kalemler else {}


def gecmis_olaylar(kayitlar: list, piyasa: dict, bugun: date | None = None,
                   geri_gun: int = 7) -> list[dict]:
    """Son `geri_gun` içinde vakti geçmiş olaylar için sonuç satırı.

    Girdi olarak bu koşunun takvimi verilir; önce arşive eklenir, sonra geriye
    bakan liste ARŞİVDEN kurulur — bu koşunun takvimi zaten yalnız geleceği
    içerir, geçmiş yalnız arşivde durur.
    """
    bugun = bugun or date.today()
    arsivle(kayitlar)
    out = []
    for k in arsiv_oku().values():
        g = _gun(getattr(k, "tarih", None) or (k.get("tarih") if isinstance(k, dict) else None))
        if g is None or not (0 <= (bugun - g).days <= geri_gun):
            continue
        olay = getattr(k, "olay", None) or (k.get("olay") if isinstance(k, dict) else "")
        beklenti = getattr(k, "beklenti", "") or (k.get("beklenti", "") if isinstance(k, dict) else "")
        beklenti_sayi = (getattr(k, "beklenti_sayi", None)
                         if not isinstance(k, dict) else k.get("beklenti_sayi"))
        yas = (bugun - g).days
        t = _takip(olay)

        satir = {"olay": olay, "tarih": g.isoformat(), "yas_gun": yas,
                 "beklenti": beklenti, "ad": t.ad if t else "", "birim": t.birim if t else "",
                 "gerceklesme": None, "onceki": None, "surpriz": None,
                 "durum": "takip dışı", "veri_tarihi": ""}
        if t:
            d = gozlem.anlik(t.hat) or {}
            v = d.get(t.anahtar)
            v_tarih = gozlem.anahtar_tarihi(d, t.anahtar, t.tarih_alani) if d else ""
            veri_gun = _tr_gun(v_tarih)
            # "Geldi mi?" sorusunun İKİ meşru cevabı var ve eski kod yalnız
            # birincisine bakıyordu:
            #   (a) verinin REFERANS tarihi yayım gününe ulaştı (günlük seriler);
            #   (b) anahtarın SÜRÜMÜ yayım gününde/sonrasında ilerledi.
            # Haftalık TCMB serilerinde (a) YAPISAL olarak imkânsız: 27.08
            # Perşembe yayımı 21.08 dönemini taşır, yani referans tarihi yayım
            # tarihini hiçbir zaman yakalayamaz ve "geldi" durumu ölü koddu —
            # 28.08 bülteni, gösterge panosu 14.08→21.08 İLERLEMİŞKEN aynı
            # yayım için "veri henüz hatta düşmedi" yazdı. (b) bunu kapatır:
            # gozlem'in sürüm saati, şimdiki referans tarihine NE ZAMAN
            # geçildiğini tutar; geçiş yayım günü ya da sonrasıysa yayım
            # hattımıza düşmüş demektir. Günlük anahtarlarda (b) yeni bir
            # davranış eklemez — orada (a) zaten aynı gün doğrulanır.
            surum_gunu = None
            alan = gozlem.tarih_alani(d, t.anahtar, t.tarih_alani)
            # Alan adı boşsa anahtarın saati hattın ANA saatidir (kurucu ilke —
            # saat: açık alan → <anahtar>_tarih → _tarih). O hâlde sürüm sorusu
            # da hat düzeyinde sorulur: son_gorulme, ana saatin şimdiki değerine
            # ne zaman geçildiğini verir. Gözlem deposu ölçüm anlarında yazdığı
            # için bu an gerçek gelişten SONRA olabilir — sakınca yok: geç ilan
            # edilen bir geliş yanlış değildir, erken ilan edilen olurdu.
            sg = (gozlem.alan_son_gorulme(t.hat, alan) if alan
                  else gozlem.son_gorulme(t.hat))
            if sg and sg[1]:
                surum_gunu = _gun(str(sg[1])[:10])
            geldi = veri_gun is not None and (
                veri_gun >= g or (surum_gunu is not None and surum_gunu >= g))
            if v is None or not isinstance(v, (int, float)) or isinstance(v, bool):
                satir["durum"] = "hat bu büyüklüğü üretmiyor"
            elif not geldi:
                # Yayım oldu ama bizim hattımıza henüz düşmedi. Hattın elindeki
                # eski sayıyı "gerçekleşme" diye yazmak yanlış olurdu.
                satir["durum"] = "veri henüz hatta düşmedi"
                satir["veri_tarihi"] = v_tarih
            else:
                onc = gozlem.onceki_surum_anahtar(t.hat, t.anahtar, t.tarih_alani, v_tarih)
                onceki = (onc or {}).get("d", {}).get(t.anahtar) if onc else None
                satir.update(
                    gerceklesme=round(float(v), t.ondalik),
                    onceki=round(float(onceki), t.ondalik)
                    if isinstance(onceki, (int, float)) and not isinstance(onceki, bool) else None,
                    durum="geldi", veri_tarihi=v_tarih)
                if isinstance(beklenti_sayi, (int, float)) and not isinstance(beklenti_sayi, bool):
                    satir["surpriz"] = round(float(v) - float(beklenti_sayi), t.ondalik)
                    satir["beklenti_sayi"] = float(beklenti_sayi)
            if t.tepki:
                tp = _tepki(piyasa, t.tepki, yas)
                if tp:
                    satir["tepki"] = tp
        # Takip edilmeyen ve beklentisi de olmayan olay bültende yer kaplamaz:
        # "şu veri çıktı, hakkında söyleyecek bir şeyimiz yok" satırı okura bir
        # şey vermez. Takip edilen ya da beklenti yayımlanmış olanlar kalır.
        if satir["durum"] != "takip dışı" or beklenti:
            out.append(satir)
    out.sort(key=lambda s: s["tarih"], reverse=True)
    return out
