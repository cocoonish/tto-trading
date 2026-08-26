#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reel sektör döviz pozisyonu — EVDS'ten veri çekme.

Kaynak: TCMB "Finansal Kesim Dışındaki Firmaların Döviz Varlık ve
Yükümlülükleri" (veri grubu `bie_fdvy`, aylık, Aralık 2002'den beri).

Seri kodları KODA GÖMÜLMEZ: ilk koşuda grubun seri listesi EVDS'ten çekilir,
adlarıyla birlikte data/seriler.json'a yazılır ve hangi kolonun ne olduğu
ADDAN eşlenir. TCMB bir serinin adını/kodunu değiştirirse eşleme düşer ve hat
sessizce yanlış kolon okumak yerine açık hata verir — tazeleme hattındaki
"ölü kalıp" ilkesinin buradaki karşılığı.

Anahtar sırası bütün hatlarla aynı: TTO_EVDS_KEY → .evds_key (proje, kök,
TCMBNetRezerv). Anahtar üstbilgide gider, URL'de değil.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

BURASI = Path(__file__).resolve().parent
DATA = BURASI / "data"
BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
GRUP = "bie_fdvy"
# HTTP başlıkları latin-1 ile kodlanır: Türkçe harf koymak isteği daha
# gönderilmeden UnicodeEncodeError ile düşürür (26.08 koşusunda oldu).
UA = "Mozilla/5.0 (TTO Trading veri hatti)"


def anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    kok = BURASI.parent.parent
    for yol in (BURASI / ".evds_key", kok / ".evds_key",
                kok / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key"):
        if yol.exists():
            a = yol.read_text(encoding="utf-8").strip()
            if a:
                return a
    raise SystemExit("EVDS anahtarı yok: TTO_EVDS_KEY ya da .evds_key gerekli.")


def _cek(url: str, deneme: int = 3):
    son = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:                                   # noqa: BLE001
            son = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü: {son}") from son


# Kolon → seri ADI kalıbı. Kod değil AD eşlenir; adlar metaveriyle birlikte
# data/seriler.json'a yazılır ki eşleme her koşuda denetlenebilir olsun.
# TCMB bu tabloyu HİYERARŞİK KODLA adlandırıyor: "A.Varlıklar",
# "B.a.1.Yurt İçinden Sağlanan Krediler", "C.Net Döviz Pozisyonu"… Kalıplar
# bu koda demirleniyor; serbest kalıp iki nedenle yanlıştı:
#
#   Toplamları HİÇ bulamıyordu. "^Varlıklar$" adı "A.Varlıklar" olan seriyle
#   eşleşmez; ön ekteki "A." yüzünden hat 27.08'de "zorunlu kolonlar
#   eşlenemedi" deyip düştü.
#
#   Bulduklarını da tesadüfen doğru buluyordu. "Net Döviz Pozisyon" hem
#   "C.Net Döviz Pozisyonu" hem "F.Kısa Vadeli Net Döviz Pozisyonu" ile
#   eşleşiyor; doğru olanı seçmesinin tek sebebi C'nin listede önce gelmesiydi.
#   TCMB sıralamayı değiştirse hat SESSİZCE yanlış kolonu okurdu.
#
# Tam eşleşme, kaymayı sessizlikten çıkarıp açık hataya çeviriyor: TCMB adı
# değiştirirse hat durur ve sebebini yazar (dökümü de loga basar).
KALIPLAR = {
    "varlik_toplam":     r"^A\.\s*Varlıklar$",
    "yukumluluk_toplam": r"^B\.\s*Yükümlülükler$",
    "net_pozisyon":      r"^C\.\s*Net Döviz Pozisyonu$",
    "kv_varlik":         r"^D\.\s*Kısa Vadeli Varlıklar$",
    "kv_yukumluluk":     r"^E\.\s*Kısa Vadeli Yükümlülükler$",
    "kv_net":            r"^F\.\s*Kısa Vadeli Net Döviz Pozisyonu$",
    "mevduat":           r"^A\.a\.\s*Mevduat$",
    "ihracat_alacak":    r"^A\.c\.\s*İhracat Alacakları$",
    "yi_kredi":          r"^B\.a\.1\.\s*Yurt İçinden Sağlanan Krediler$",
    "yd_kredi":          r"^B\.a\.2\.\s*Yurt Dışından Sağlanan Krediler$",
    "ithalat_borc":      r"^B\.b\.\s*İthalat Borçları$",
}


def kesfet() -> dict:
    """Grubun seri listesini çek, kalıplara eşle, data/seriler.json'a yaz."""
    ham = _cek(f"{BASE}/serieList/type=json&code={GRUP}")
    seriler = ham if isinstance(ham, list) else ham.get("items", [])
    dokum = [{"kod": s.get("SERIE_CODE"), "ad": (s.get("SERIE_NAME") or "").strip()}
             for s in seriler if s.get("SERIE_CODE")]
    esleme, kullanilmis = {}, set()
    for kolon, kalip in KALIPLAR.items():
        for s in dokum:
            if s["kod"] in kullanilmis:
                continue
            if re.search(kalip, s["ad"], re.I):
                esleme[kolon] = s
                kullanilmis.add(s["kod"])
                break
    DATA.mkdir(exist_ok=True)
    (DATA / "seriler.json").write_text(json.dumps(
        {"_aciklama": "bie_fdvy grubunun seri dökümü ve kolon eşlemesi. Eşleme "
                      "AD kalıbıyla yapılır; TCMB adı değiştirirse eşleme düşer ve "
                      "hat açık hata verir — sessiz yanlış kolon okunmaz.",
         "grup": GRUP, "esleme": esleme, "tum_seriler": dokum},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    eksik = [k for k in ("varlik_toplam", "yukumluluk_toplam", "net_pozisyon")
             if k not in esleme]
    if eksik:
        # Adları LOGA da bas. seriler.json diske yazıldı ama koşu düşerse o
        # dosya depoya girmeyebilir; o zaman kalıbı düzeltecek olan elinde
        # hiçbir şey olmadan kalır. 27.08 koşusunda tam bu oldu: hat
        # "zorunlu kolonlar eşlenemedi" deyip sustu, hangi adlarla
        # karşılaştığını kimse öğrenemedi. Log her hâlükârda kalıyor.
        print(f"\nKEŞİF EKSİK — eşlenemeyen zorunlu kolonlar: {eksik}", flush=True)
        print(f"Grupta {len(dokum)} seri var. Eşleşenler:", flush=True)
        for k, v in esleme.items():
            print(f"   ✓ {k:18s} ← {v['ad']}", flush=True)
        print("Eşleşmeyen adlar (ilk 60):", flush=True)
        esles = {v["kod"] for v in esleme.values()}
        for x in [d for d in dokum if d["kod"] not in esles][:60]:
            print(f"   · {x['ad']}", flush=True)
        raise SystemExit(f"KEŞİF EKSİK — zorunlu kolonlar eşlenemedi: {eksik}. "
                         f"Yukarıdaki adlara bakıp KALIPLAR güncellenmeli "
                         f"(döküm ayrıca data/seriler.json'da).")
    return esleme


def indir(esleme: dict):
    import pandas as pd
    kodlar = [v["kod"] for v in esleme.values()]
    url = (f"{BASE}/series={('-'.join(kodlar))}&startDate=01-12-2002"
           f"&endDate=01-12-2099&type=json&formulas=0")
    ham = _cek(url)
    kayitlar = ham.get("items", ham) if isinstance(ham, dict) else ham
    df = pd.DataFrame(kayitlar)
    ters = {v["kod"].replace(".", "_"): k for k, v in esleme.items()}
    df = df.rename(columns=ters)
    df["tarih"] = pd.to_datetime(df["Tarih"], format="%m-%Y", errors="coerce")
    kolonlar = ["tarih"] + [k for k in esleme if k in df.columns]
    df = df[kolonlar].dropna(subset=["tarih"]).sort_values("tarih")
    for k in esleme:
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce")
    df.to_csv(DATA / "fdvy.csv", index=False)
    print(f"fdvy.csv: {len(df)} satır, {df['tarih'].min():%Y-%m} → {df['tarih'].max():%Y-%m}")


if __name__ == "__main__":
    esleme = kesfet()
    print("eşlenen kolonlar:", ", ".join(esleme))
    indir(esleme)
