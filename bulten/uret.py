#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — üretici: olay + takvim + haber → tek JSON.

Çıktı: site/src/data/bulten/YYYY-MM-DD.json
Astro bu dosyayı derleme sırasında okuyup sayfaya çevirir (istemci tarafında
veri çekme yok; bülten statik ve arşivlenebilir).

Bölümler:
  gostergeler   sabah bakışı: temel seviyeler tek satırda
  one_cikanlar  eşiği aşan ÖNEMLİ olaylar
  notlar        dikkat seviyesindeki olaylar (gruplanmış)
  veri_gunlugu  hangi hat tazelendi / hangisi gecikti
  takvim        bu hafta / gelecek hafta / sonraki iki hafta
  haberler      kurum duyuruları + kümelenmiş haber başlıkları
  yorum         LLM katmanının yazdığı kısa metin (boş olabilir)

Yorum alanı BOŞ bırakılabilir: bülten yorumsuz da tamdır. Yorum katmanı sonradan
aynı dosyayı açıp 'yorum' alanını doldurur (bkz. --yorum-yaz).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
KOK = BURASI.parent
CIKTI = KOK / "site" / "src" / "data" / "bulten"

import ayar          # noqa: E402
import gozlem        # noqa: E402
import olay as olay_m  # noqa: E402
import takvim as takvim_m  # noqa: E402


# Sabah bakışı panosu: (hat, anahtar, ad, birim, ondalık)
GOSTERGELER = [
    ("usdtry-deval", "kur", "USD/TRY", "", 2),
    ("usdtry-deval", "d1a", "1 aylık yıllıklandırılmış deval. hızı", "%", 1),
    ("tcmb-net-rezerv", "h_net", "Net rezerv", "mlr USD", 1),
    ("tcmb-net-rezerv", "h_swap_haric", "Swap hariç net rezerv", "mlr USD", 1),
    ("fonlama-likidite", "politika", "Politika faizi", "%", 2),
    ("fonlama-likidite", "tlref", "TLREF", "%", 2),
    ("fonlama-likidite", "aofm", "Ağırlıklı ort. fonlama maliyeti", "%", 2),
    ("enflasyon", "tufe_12a", "TÜFE (yıllık)", "%", 2),
    ("enflasyon", "tufe_3a", "TÜFE 3a yıllıklandırılmış (arındırılmış)", "%", 1),
    ("enflasyon", "tufe_3a_ham", "TÜFE 3a yıllıklandırılmış (ham)", "%", 1),
    ("kredi-parasal", "g_ar_13y", "Kredi büyümesi (13h yıl., kur arınd.)", "%", 1),
    ("hazine-ihrac", "maliyet_son", "Son ihale maliyeti", "%", 2),
    ("yabanci-pozisyon", "toplam_4h", "Yabancı 4 haftalık net akım", "mn USD", 0),
    ("try-reer", "redk", "Reel efektif kur", "endeks", 1),
]


def gostergeler() -> list[dict]:
    out = []
    for hat, anahtar, ad, birim, ond in GOSTERGELER:
        d = gozlem.anlik(hat)
        if not d:
            continue
        v = d.get(anahtar)
        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        onc = gozlem.onceki_surum(hat, gozlem._tarih_of(d))
        eski = (onc or {}).get("d", {}).get(anahtar) if onc else None
        fark = (v - eski) if isinstance(eski, (int, float)) else None
        out.append({"ad": ad, "hat": hat, "anahtar": anahtar,
                    "deger": round(float(v), ond), "birim": birim, "ondalik": ond,
                    "metin": olay_m._s(float(v), ond),
                    # Yuvarlamadan sonra sıfır kalan fark "−0,00" diye görünüyordu;
                    # değişmemiş bir seriyi değişmiş gibi göstermek bültenin işi değil.
                    "fark": round(float(fark), ond) if fark is not None else None,
                    "fark_metin": (("+" if fark > 0 else "−") + olay_m._s(abs(fark), ond))
                                  if (fark is not None and round(abs(float(fark)), ond) > 0) else "",
                    "veri_tarihi": gozlem._tarih_of(d)})
    return out


# ─────────────────────────── takvim kayıtlarına BEKLENTİ iliştir
# Kullanıcının istediği: "önemli datalar belirtilecek, beklentiler belirtilecek".
# Beklenti iki yerden gelir ve İKİSİ DE ayrı ayrı yazılır:
#   anket  → TCMB Piyasa Katılımcıları Anketi (enflasyon hattının ozet.json'u)
#   model  → bu deponun kendi tahmini (Hazine ihale modeli, baz etkisi senaryoları)
# Karıştırılmaz: anket piyasanın ne beklediğini, model bizim ne hesapladığımızı söyler.
def _beklenti_metni(olay: str) -> str:
    enf = gozlem.anlik("enflasyon") or {}
    fon = gozlem.anlik("fonlama-likidite") or {}
    s = olay.lower()
    p = []
    if "tüfe" in s and "abd" not in s:
        if enf.get("bek_yilsonu") is not None:
            p.append(f"anket (PKA, {enf.get('bek_n', '?')} katılımcı): yıl sonu "
                     f"%{olay_m._s(enf['bek_yilsonu'], 2)}")
        if enf.get("bek_12a") is not None:
            p.append(f"12 ay sonrası %{olay_m._s(enf['bek_12a'], 2)}")
        if enf.get("baz_momentum_yilsonu") is not None and enf.get("baz_tekrar_yilsonu") is not None:
            p.append(f"kendi baz etkisi modelimiz: momentum senaryosu "
                     f"%{olay_m._s(enf['baz_momentum_yilsonu'], 2)}, tekrar senaryosu "
                     f"%{olay_m._s(enf['baz_tekrar_yilsonu'], 2)}")
    if "ppk" in s or "faiz kararı" in s:
        if fon.get("politika") is not None:
            p.append(f"mevcut politika faizi %{olay_m._s(fon['politika'], 2)}")
        if enf.get("bek_faiz_12a") is not None:
            p.append(f"anket: 12 ay sonrası politika faizi %{olay_m._s(enf['bek_faiz_12a'], 2)}")
    if "ödemeler dengesi" in s:
        pass  # ödemeler dengesi hattı kurulunca buraya beklenti bağlanacak
    return " · ".join(p)


def beklenti_iliştir(kayitlar: list) -> None:
    for k in kayitlar:
        if getattr(k, "beklenti", ""):
            continue           # Hazine ihalesi gibi kendi beklentisi olanlara dokunma
        m = _beklenti_metni(k.olay)
        if m:
            k.beklenti = m


def uret(tarih: date | None = None, haber_tara: bool = True,
         takvim_ufku: int | None = None) -> dict:
    tarih = tarih or date.today()
    ufuk = takvim_ufku or ayar.TAKVIM_UFKU

    # 1) anlık görüntüleri kaydet (kıyas noktası ilerlesin)
    yazilan = []
    for hat in ayar.RITIM:
        d = gozlem.anlik(hat)
        if d and gozlem.kaydet(hat, d):
            yazilan.append(hat)

    # 2) olaylar
    olaylar = olay_m.topla()
    grup_adi = dict(ayar.GRUPLAR)

    def dk(o):
        return asdict(o)

    one_cikan = [dk(o) for o in olaylar if o.seviye == "onemli"]
    notlar = [dk(o) for o in olaylar if o.seviye == "dikkat" and o.grup != "diger"]
    gunluk = [dk(o) for o in olaylar if o.seviye == "bilgi" or
              (o.seviye == "dikkat" and o.grup == "diger")]

    gruplar = []
    for gid, gbaslik in ayar.GRUPLAR:
        icerik = [dk(o) for o in olaylar if o.grup == gid and o.seviye in ("onemli", "dikkat")]
        if icerik:
            gruplar.append({"id": gid, "baslik": gbaslik, "olaylar": icerik})

    # 3) takvim — Pazartesi (ya da --haftalik) günü kapsam genişler
    haftalik = tarih.weekday() == 0
    asgari = ayar.TAKVIM_HAFTALIK_ASGARI_ONEM if haftalik else ayar.TAKVIM_ASGARI_ONEM
    kayitlar = takvim_m.topla(ufuk, asgari)
    beklenti_iliştir(kayitlar)
    takvim_bloklari = []
    for baslik, grup in takvim_m.hafta_gruplari(kayitlar):
        takvim_bloklari.append({
            "baslik": baslik,
            "kayitlar": [{**asdict(k), "gun": k.gun_adi(), "tr_tarih": k.tr_tarih()} for k in grup],
        })
    # Kritik takvim: ufkun TAMAMINDA onem=1 olanlar. "Daha da önemli veriler 2-3
    # hafta içinde ne zaman?" sorusunun tek bakışta cevabı; haftalık bloklardan
    # ayrı durur, çünkü okur onları hafta hafta değil ÖNEM sırasıyla arıyor.
    kritik = [{**asdict(k), "gun": k.gun_adi(), "tr_tarih": k.tr_tarih(),
               "kalan_gun": (date.fromisoformat(k.tarih) - tarih).days}
              for k in kayitlar if k.onem == 1]

    # 4) haberler
    haberler, okunamayan = ([], [])
    if haber_tara:
        try:
            import haber as haber_m
            h, okunamayan = haber_m.tara()
            haberler = [asdict(x) for x in h]
        except Exception as e:                                  # noqa: BLE001
            okunamayan = [f"haber taraması düştü: {type(e).__name__}"]

    return {
        "tarih": tarih.isoformat(),
        "gun": takvim_m.GUNLER_TR[tarih.weekday()],
        "tr_tarih": f"{tarih.day} {takvim_m.AYLAR_TR[tarih.month - 1]} {tarih.year}",
        "olusturma": datetime.now().isoformat(timespec="seconds"),
        "gostergeler": gostergeler(),
        "one_cikanlar": one_cikan,
        "notlar": notlar,
        "gruplar": gruplar,
        "veri_gunlugu": gunluk,
        "takvim": takvim_bloklari,
        "kritik_takvim": kritik,
        "haftalik": haftalik,
        "haberler": {
            "kurum": [h for h in haberler if h.get("kurum")],
            "haber": [h for h in haberler if not h.get("kurum")],
            "okunamayan": okunamayan,
        },
        "yorum": None,
        "yorum_zamani": None,
        "surum": 1,
    }


def yaz(b: dict) -> Path:
    CIKTI.mkdir(parents=True, exist_ok=True)
    y = CIKTI / f"{b['tarih']}.json"
    # Yorum katmanı daha önce yazdıysa KORUNUR: deterministik koşu yorumu silmemeli.
    if y.exists():
        try:
            eski = json.loads(y.read_text(encoding="utf-8"))
            if eski.get("yorum"):
                b["yorum"], b["yorum_zamani"] = eski["yorum"], eski.get("yorum_zamani")
            # --habersiz koşusu, daha önce toplanmış haberleri SİLMEMELİ: gün içinde
            # hızlı bir yeniden üretim bülteni fakirleştirmesin.
            eski_h = (eski.get("haberler") or {})
            yeni_h = b.get("haberler") or {}
            if not (yeni_h.get("kurum") or yeni_h.get("haber")) and \
                    (eski_h.get("kurum") or eski_h.get("haber")):
                b["haberler"] = eski_h
        except Exception:
            pass
    y.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    return y


def ozet_yaz(b: dict) -> str:
    """Terminal özeti."""
    satir = [f"{b['tr_tarih']} {b['gun']} — TTO günlük bülten"]
    satir.append(f"  gösterge: " + " · ".join(
        f"{g['ad'].split('(')[0].strip()} {g['metin']}{g['birim']}" for g in b["gostergeler"][:5]))
    satir.append(f"  öne çıkan: {len(b['one_cikanlar'])} · not: {len(b['notlar'])} · "
                 f"takvim: {sum(len(t['kayitlar']) for t in b['takvim'])} · "
                 f"duyuru: {len(b['haberler']['kurum'])} · haber: {len(b['haberler']['haber'])}")
    for o in b["one_cikanlar"]:
        satir.append(f"   !! {o['metin']}")
    for o in b["notlar"][:6]:
        satir.append(f"    · {o['metin']}")
    return "\n".join(satir)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--habersiz", action="store_true", help="RSS taramasını atla (hızlı)")
    ap.add_argument("--ufuk", type=int, default=None, help="takvim ufku (gün)")
    ap.add_argument("--yazma", action="store_true", help="dosyaya yazma, yalnız göster")
    a = ap.parse_args()

    b = uret(haber_tara=not a.habersiz, takvim_ufku=a.ufuk)
    print(ozet_yaz(b))
    if not a.yazma:
        y = yaz(b)
        print(f"\n  yazıldı: {y.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
