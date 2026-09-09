#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reel sektör döviz pozisyonu — hesap katmanı.

data/fdvy.csv yoksa hat İLK KOŞUSUNU BEKLİYOR demektir: ozet.json'a yalnız o
durum yazılır ve grafikler yer tutucu olarak üretilir. Ölçülmemiş sayı
uydurulmaz; sayfa 'taslak' rozetiyle yayımlanır ve ilk başarılı veri
koşusunda kendiliğinden dolar.

AĞA ÇIKMAZ. Bütün ölçüm burada, saf fonksiyonlarda durur (`ozetle`); dosya
okuyan tek yer `hesapla`. Ayrım duman sınamasının sentetik çerçeveyle bütün
sözleşmeyi koşturabilmesi için: ölçüm dosya okumanın içine gömülü kalsaydı
sınanabilen tek şey depodaki o günkü veri olurdu.
"""
from __future__ import annotations

import json
from pathlib import Path

BURASI = Path(__file__).resolve().parent
DATA = BURASI / "data"
KOK = BURASI.parent.parent
REZERV_OZET = KOK / "site" / "public" / "projeler" / "tcmb-net-rezerv" / "ozet.json"

# ÖLÇÜLEMEYEN DEĞERİN YAZIMI. Sayfanın adıyla çağırdığı anahtar HER koşuda
# yazılır: ölçülebiliyorsa sayıyla, ölçülemiyorsa bununla. Atlanırsa sayfada
# MDX'teki statik yedek — yani geçen ayın sayısı — canlı gibi durur ve yayın
# kapısı eksik anahtarı ENGEL sayar (08.09.2026'da bir kez ölçüldü: bir hattın
# atladığı tek anahtar yayını üç kez durdurdu).
OLCULEMEDI = "—"


def bekliyor_ozet() -> dict:
    """Hat ilk veri çekimini beklerken sayfaya basılan durum.

    METİN OKURA GİDER. `ozet.json`un cümle olan her metin alanı sayfaya olduğu
    gibi basılır ve yayın kapısı (sayfa sınavı 17) kod dilini ENGEL sayar.
    Buradaki metin bir zamanlar hattın dosya adını ve yapım ortamını
    anlatıyordu; 09.09.2026'da ölçüldü: `okur_dili.kosu_kaydi_tara` o cümlede
    iki bulgu veriyordu (biri ENGEL). Kusur bugün tetiklenmiyordu — veri vardı —
    yani ilk boş çekimde yayını durduracak bir mayın olarak duruyordu.
    """
    return {"_durum": "ilk koşu bekleniyor",
            "_aciklama": "Bu sayfanın verisi henüz ilk kez derlenmedi; ilk "
                         "başarılı derlemede reel sektörün döviz varlık ve "
                         "yükümlülükleri buraya yazılacak."}


# Yuvarlama payı. TCMB tabloyu milyon dolar tam sayı olarak yayımlıyor; üç
# kalemin ayrı ayrı yuvarlanması 1 milyonluk fark üretebilir. 5 milyon, gerçek
# bir eşleme kaymasının üreteceği farkın (milyarlar) çok altında.
KIMLIK_ESIK_MN = 5.0


def oran_damgasi(ay: str, hafta: str) -> str:
    """Rezerve oranın İKİ PARÇALI saati.

    Oranın payı firmaların AYLIK pozisyonu (~2 ay gecikmeli), paydası TCMB'nin
    HAFTALIK brüt rezervi. İki bacak arasında iki aya varan mesafe var ve tek
    bir gün yazmak iki yönde birden yalan söyler: aylık payı haftalık kadar
    taze, haftalık paydayı aylık kadar bayat gösterir. Sözleşme (CLAUDE.md
    "bir figürün damgası BAĞLAYICI bacaktır") bu hâl için iki parçalı damgayı
    tarif ediyor. Damga bilerek TEK BİR GÜNE ÇÖZÜLMEZ — çözülseydi bileşen onu
    bir ölçüm gününe demirler ve bacaklardan biri hakkında yanıltırdı.
    """
    if not ay or not hafta:
        return OLCULEMEDI
    return f"aylık {ay} · haftalık {hafta}"


def ozetle(d, rez: dict | None) -> dict:
    """Sayfanın okuduğu bütün anahtarlar. `d`: aylık tablo, `rez`: rezerv özeti.

    Saf: dosya okumaz, ağa çıkmaz. `rez` None ise rezerve oran ölçülemez —
    ama anahtarları yine de yazılır (bkz. OLCULEMEDI).
    """
    def son(kolon, ondalik=1):
        if kolon not in d.columns:
            return None, ""
        s = d[kolon].dropna()
        return (None, "") if s.empty else (round(float(s.iloc[-1]) / 1000, ondalik),
                                           f"{s.index[-1]:%m.%Y}")   # mn → mlr USD

    # ÖZDEŞLİK SINAMASI — eşlemenin doğruluğunu VARSAYMAK yerine ÖLÇER.
    # Kolonlar TCMB'nin seri ADINA göre eşleniyor; ad kalıbı bir gün başka bir
    # seriyi yakalarsa hat sessizce yanlış büyüklüğü okur ve bunu hiçbir şey
    # fark etmez. Ama tablonun kendi içinde iki muhasebe kimliği var:
    #     A.Varlıklar − B.Yükümlülükler = C.Net Döviz Pozisyonu
    #     D.Kısa Vadeli Varlıklar − E.Kısa Vadeli Yük. = F.Kısa Vadeli Net
    # Eşleme doğruysa bu iki fark yuvarlama dışında SIFIR olmalı. 283 satırın
    # tamamında maksimum sapma 1 milyon dolar (yuvarlama) ölçüldü. Kalıp kayarsa
    # fark patlar ve hat durur — yanlış sayıyı sayfaya taşımaz.
    kimlik = {}
    for ad, a, b, c in (("net", "varlik_toplam", "yukumluluk_toplam", "net_pozisyon"),
                        ("kisa_vade", "kv_varlik", "kv_yukumluluk", "kv_net")):
        if not all(k in d.columns for k in (a, b, c)):
            continue
        fark = (d[a] - d[b] - d[c]).dropna()
        if not len(fark):
            continue
        maks = float(fark.abs().max())
        kimlik[ad] = {"n": int(len(fark)), "maks_fark_mn": round(maks, 3)}
        if maks > KIMLIK_ESIK_MN:
            # AŞAĞIDAKİ METİN OKURA GİTMEZ: hattın kopya sözleşmesinde
            # uyarilar.json yok, mesaj yalnız koşu günlüğüne düşer — yani
            # okur dili değil OPERATÖR dili doğrusu: onaran kişiye bakacağı
            # dosyayı adıyla söylemeyen bir hata mesajı, her düzeltme için
            # ayrı bir keşif koşusu demektir.
            raise SystemExit(
                f"ÖZDEŞLİK BOZUK ({ad}): {a} − {b} ile {c} arasında "
                f"{maks:,.0f} milyon dolar fark var ({len(fark)} satırda). "
                "Kolon eşlemesi kaymış olmalı — veri_cek.py KALIPLAR ve "
                "data/seriler.json'a bak. Yanlış kolonla sayfa üretilmez.")

    ozet = {}
    for k in ("varlik_toplam", "yukumluluk_toplam", "net_pozisyon",
              "kv_varlik", "kv_yukumluluk", "kv_net"):
        deger, tarih = son(k)
        if deger is not None:
            ozet[k] = deger
            ozet[f"{k}_tarih"] = tarih
    ozet["_tarih"] = ozet.get("net_pozisyon_tarih", "")

    # 12 aylık değişimler (mlr USD)
    for k in ("net_pozisyon", "kv_net"):
        if k in d.columns and d[k].dropna().shape[0] > 12:
            s = d[k].dropna()
            ozet[f"{k}_d12a"] = round(float(s.iloc[-1] - s.iloc[-13]) / 1000, 1)

    # Rezerve oran: net açığın brüt rezerve bölümü — kırılganlığın ölçeği.
    # ANAHTARLAR HER KOŞUDA YAZILIR: rezerv özeti okunamazsa sayı değil
    # OLCULEMEDI basılır. Eskiden anahtar hiç yazılmıyordu ve sayfa o zaman
    # MDX'teki statik yedeği canlı gibi gösteriyordu.
    brut = (rez or {}).get("h_brut")
    hafta = str((rez or {}).get("h_tarih") or "")
    if brut and ozet.get("net_pozisyon") is not None:
        ozet["acik_rezerv_orani"] = round(100 * abs(ozet["net_pozisyon"]) / brut, 1)
        ozet["acik_rezerv_tarih"] = hafta
        ozet["acik_rezerv_orani_tarih"] = oran_damgasi(
            ozet.get("net_pozisyon_tarih", ""), hafta)
    else:
        ozet["acik_rezerv_orani"] = OLCULEMEDI
        ozet["acik_rezerv_orani_tarih"] = OLCULEMEDI
    if kimlik:
        ozet["kimlik"] = kimlik
    return ozet


def rezerv_ozeti() -> dict | None:
    """TCMB net rezerv hattının siteye yazdığı özet (yoksa None). Ağa çıkmaz."""
    try:
        return json.loads(REZERV_OZET.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def hesapla():
    import pandas as pd
    y = DATA / "fdvy.csv"
    if not y.exists():
        return None, bekliyor_ozet()
    d = pd.read_csv(y, parse_dates=["tarih"]).set_index("tarih").sort_index()
    # BOŞ DOSYA "veri var" DEĞİLDİR. 26.08'de veri çekme katmanı tarih biçimini
    # ayrıştıramayıp yalnız BAŞLIK satırından ibaret bir CSV yazdı; burası
    # dosyanın varlığını veri sanıp `_tarih: ""` olan bir özet üretti — yani
    # "ilk koşu bekleniyor" diyen dürüst yer tutucudan DAHA KÖTÜ bir çıktı:
    # sayfa veri varmış gibi görünüyor ama hiçbir sayı yok.
    if d.empty:
        return None, bekliyor_ozet()
    return d, ozetle(d, rezerv_ozeti())


if __name__ == "__main__":
    d, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if d is None:
        print("veri yok — 'ilk koşu bekleniyor' özeti yazıldı")
    else:
        for k, v in ozet.items():
            if not k.startswith("_"):
                print(f"  {k:24s} {v}")
