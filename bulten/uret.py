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
from datetime import date, datetime, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
KOK = BURASI.parent
CIKTI = KOK / "site" / "src" / "data" / "bulten"

import ayar          # noqa: E402
import gozlem        # noqa: E402
import olay as olay_m  # noqa: E402
import takvim as takvim_m  # noqa: E402
import piyasa as piyasa_m  # noqa: E402
import soz as soz_m  # noqa: E402
import grafik_veri as grafik_m  # noqa: E402
import surpriz as surpriz_m  # noqa: E402
import rejim as rejim_m  # noqa: E402


# Sabah bakışı panosu: (hat, anahtar, ad, birim, ondalık, tarih alanı)
# Son alan o göstergenin KENDİ saatidir; boş bırakılırsa `<anahtar>_tarih`
# geleneği, o da yoksa hattın ana saati (`_tarih`) kullanılır. Panodaki tarih
# de, farkın kıyas noktası da bu saatten okunur — yoksa haftalık bir seri,
# hattın günlük saati ilerlediği için her gün "değişmedi" görünür.
GOSTERGELER = [
    ("usdtry-deval", "kur", "USD/TRY", "", 2, ""),
    ("usdtry-deval", "d1a", "1 aylık yıllıklandırılmış deval. hızı", "%", 1, ""),
    ("tcmb-net-rezerv", "h_net", "Net rezerv", "mlr USD", 1, "h_tarih"),
    ("tcmb-net-rezerv", "h_swap_haric", "Swap hariç net rezerv", "mlr USD", 1, "h_tarih"),
    # Haftalık resmî seri ile GÜNLÜK tahmin panoda yan yana durur. İkisi farklı
    # tarihlere aittir ve karıştırılmaları bültende gerçek bir hataya yol açtı:
    # 14.08 tarihli haftalık rakam 24.08 tarihli gibi yazılmıştı. Yan yana
    # görünmeleri karışmalarını zorlaştırıyor.
    ("tcmb-net-rezerv", "g_net", "Net rezerv (günlük tahmin)", "mlr USD", 1, "g_tarih"),
    ("tcmb-net-rezerv", "p_altin_pay", "Brüt rezervde altın payı", "%", 1, "p_tarih"),
    ("fonlama-likidite", "politika", "Politika faizi", "%", 2, ""),
    ("fonlama-likidite", "tlref", "TLREF", "%", 2, ""),
    ("fonlama-likidite", "aofm", "Ağırlıklı ort. fonlama maliyeti", "%", 2, ""),
    ("enflasyon", "tufe_12a", "TÜFE (yıllık)", "%", 2, ""),
    ("enflasyon", "tufe_3a", "TÜFE 3a yıllıklandırılmış (arındırılmış)", "%", 1, ""),
    ("enflasyon", "tufe_3a_ham", "TÜFE 3a yıllıklandırılmış (ham)", "%", 1, ""),
    ("kredi-parasal", "g_ar_13y", "Kredi büyümesi (13h yıl., kur arınd.)", "%", 1, ""),
    ("hazine-ihrac", "maliyet_son", "Son ihale maliyeti", "%", 2, ""),
    ("yabanci-pozisyon", "toplam_4h", "Yabancı 4 haftalık net akım", "mn USD", 0, ""),
    ("try-reer", "redk", "Reel efektif kur", "endeks", 1, ""),
    # FX haber-duyarlılık endeksi — sepet spread'i (güvenli liman tonu eksi
    # risk varlığı tonu). Hattın tek TEMİZ sayısal ölçüsü budur; uçlar
    # (`ust1_deger`, `alt1_deger`) panoya GİRMEZ, çünkü her gün başka bir
    # varlığa aittir ve sürüm kıyası dünkü gümüşle bugünkü altını kıyaslardı.
    # Saati kendi alanından okunur: spread GDELT haftalık arşivinden gelir ve
    # hattın günlük `_tarih`inden birkaç gün geridedir.
    ("fx-haber-endeksi", "spread", "FX haber endeksi — sepet spread'i", "", 3, "spread_tarih"),
]


def gostergeler(haftalik: bool = False) -> list[dict]:
    """Sabah panosu. Haftalıkta kıyas noktası bir HAFTA öncesidir.

    Haftalık bülten "geçen hafta bu saatte neredeydik" diye sorar; sürüm kıyası
    o soruya yanlış cevap verir, çünkü haftalık bir seri hafta içinde bir kez
    yayımlanır ve sürüm kıyası yalnız o tek yayımı gösterir. Tarihçe yetmezse
    sürüm kıyasına düşülür ve hangisinin kullanıldığı `kiyas` alanında yazar —
    okur neye göre baktığını bilmeden farkı yorumlayamaz.
    """
    out = []
    for hat, anahtar, ad, birim, ond, tarih_alani in GOSTERGELER:
        d = gozlem.anlik(hat)
        if not d:
            continue
        v = d.get(anahtar)
        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        v_tarih = gozlem.anahtar_tarihi(d, anahtar, tarih_alani)
        onc, kiyas = None, "son yayım"
        if haftalik:
            onc = gozlem.anahtar_hafta_once(hat, anahtar, tarih_alani)
            if onc:
                kiyas = "bir hafta önce"
        if onc is None:
            onc = gozlem.onceki_surum_anahtar(hat, anahtar, tarih_alani, v_tarih)
            if haftalik:
                kiyas = "son yayım (bir haftalık tarihçe yok)"
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
                    "veri_tarihi": v_tarih,
                    "kiyas": kiyas,
                    "kiyas_tarihi": (gozlem.anahtar_tarihi(onc.get("d", {}), anahtar,
                                                           tarih_alani) if onc else "")})
    return out


# ─────────────────────────── takvim kayıtlarına BEKLENTİ iliştir
# Kullanıcının istediği: "önemli datalar belirtilecek, beklentiler belirtilecek".
# Beklenti iki yerden gelir ve İKİSİ DE ayrı ayrı yazılır:
#   anket  → TCMB Piyasa Katılımcıları Anketi (enflasyon hattının ozet.json'u)
#   model  → bu deponun kendi tahmini (Hazine ihale modeli, baz etkisi senaryoları)
# Karıştırılmaz: anket piyasanın ne beklediğini, model bizim ne hesapladığımızı söyler.
#
# BEKLENTİ, OLAYIN ÜLKESİNE AİTTİR. Buradaki iki kaynak da Türkiye'yi ölçüyor:
# PKA anketi Türkiye enflasyon ve politika faizi beklentisidir, fonlama hattı
# TCMB'nin faizidir. Eşleme yalnız olay ADINA bakınca "Fed (FOMC) faiz kararı"
# satırı da tutuyordu ve okura Fed toplantısının beklentisi diye TÜRKİYE'nin
# politika faizini (%37,00) ve PKA'nın 12 ay sonrası TL faiz beklentisini
# gösteriyordu — ölçülmemiş bir şeyi ölçülmüş gibi göstermenin en sessiz
# biçimi. Ad eşlemesi yetmez: kaydın ÜLKESİ sorulur. Aynı kusur ABD TÜFE
# satırında bir kez daha vardı ve orada "abd" kelimesi elle dışlanmıştı;
# elle dışlama bir sonraki yabancı veri satırında (euro alanı TÜFE'si) yine
# tutardı. Ülke kapısı ikisini birden kapatır.
def _beklenti_metni(olay: str, ulke: str = "TR") -> str:
    if (ulke or "TR").upper() != "TR":
        return ""              # yabancı takvim satırına Türkiye beklentisi iliştirilmez
    enf = gozlem.anlik("enflasyon") or {}
    fon = gozlem.anlik("fonlama-likidite") or {}
    s = olay.lower()
    p = []
    if "tüfe" in s:
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
        m = _beklenti_metni(k.olay, getattr(k, "ulke", "TR"))
        if m:
            k.beklenti = m


# ═══════════════════════════════════ kural tabanlı YAZI
# Kullanıcının istediği: madde listesi değil, "piyasada ne oldu, ne bekleniyor"
# diye okunan bir metin. Yorum katmanı (LLM) her koşuda çalışmayabilir — bulut
# koşusunda hiç çalışmaz — o yüzden metnin bir TABANI burada, veriden üretilir.
# Bu metin yorum İÇERMEZ: yalnız ölçülen hareketi ve takvimi cümleye çevirir.

def _cumleler_birlestir(parcalar: list[str]) -> str:
    parcalar = [p for p in parcalar if p]
    if not parcalar:
        return ""
    if len(parcalar) == 1:
        return parcalar[0] + "."
    return "; ".join(parcalar[:-1]) + " ve " + parcalar[-1] + "."


def piyasa_ozeti(b: dict, haftalik: bool = False) -> dict:
    """(ne_oldu, ne_bekleniyor) — veriden türetilmiş iki paragraf."""
    g = {x["anahtar"]: x for x in b["gostergeler"]}
    pencere = "Geçen hafta" if haftalik else "Son veri yayımından bu yana"

    # ── ne oldu
    kur_p = []
    if "kur" in g and g["kur"]["fark"]:
        f = g["kur"]["fark"]
        kur_p.append(f"USD/TRY {g['kur']['metin']} seviyesine {'yükseldi' if f > 0 else 'geriledi'}"
                     f" ({'+' if f > 0 else '−'}{olay_m._s(abs(f), 2)})")
    if "d1a" in g and g["d1a"]["fark"]:
        f = g["d1a"]["fark"]
        kur_p.append(f"kurun bir aylık yıllıklandırılmış artış hızı %{g['d1a']['metin']}"
                     f" ({'+' if f > 0 else '−'}{olay_m._s(abs(f), 1)} puan)")
    if "h_net" in g and g["h_net"]["fark"]:
        f = g["h_net"]["fark"]
        kur_p.append(f"net rezerv {olay_m._s(abs(f), 1)} milyar dolar "
                     f"{'arttı' if f > 0 else 'azaldı'} ve {g['h_net']['metin']} milyar dolara ulaştı")
    if "h_swap_haric" in g and g["h_swap_haric"]["fark"]:
        f = g["h_swap_haric"]["fark"]
        kur_p.append(f"swap hariç net rezerv {g['h_swap_haric']['metin']} milyar dolar "
                     f"({'+' if f > 0 else '−'}{olay_m._s(abs(f), 1)})")

    faiz_p = []
    if "politika" in g:
        faiz_p.append(f"politika faizi %{g['politika']['metin']}")
    if "tlref" in g:
        fark_pol = None
        try:
            fark_pol = float(g["tlref"]["deger"]) - float(g["politika"]["deger"])
        except Exception:
            pass
        m = f"gecelik gerçekleşen faiz (TLREF) %{g['tlref']['metin']}"
        if fark_pol is not None:
            m += (f", politika faizinin {olay_m._s(abs(fark_pol), 2)} puan "
                  f"{'üzerinde' if fark_pol > 0 else 'altında'}")
        faiz_p.append(m)
    if "aofm" in g:
        faiz_p.append(f"ağırlıklı ortalama fonlama maliyeti %{g['aofm']['metin']}")

    enf_p = []
    if "tufe_12a" in g:
        enf_p.append(f"yıllık TÜFE %{g['tufe_12a']['metin']}")
    if "tufe_3a" in g and "tufe_3a_ham" in g:
        enf_p.append(f"son üç ayın yıllıklandırılmış hızı mevsimsellikten arındırılmış "
                     f"%{g['tufe_3a']['metin']}, ham %{g['tufe_3a_ham']['metin']}")

    akim_p = []
    if "toplam_4h" in g:
        v = g["toplam_4h"]["deger"]
        akim_p.append(f"yabancı yatırımcının dört haftalık net {'girişi' if v > 0 else 'çıkışı'} "
                      f"{olay_m._s(abs(v), 0)} milyon dolar")
    if "g_ar_13y" in g:
        akim_p.append(f"kur etkisinden arındırılmış kredi büyümesi (13 haftalık yıllıklandırılmış) "
                      f"%{g['g_ar_13y']['metin']}")

    p1 = []
    if kur_p:
        p1.append(f"{pencere} kur ve rezerv tarafında: " + _cumleler_birlestir(kur_p))
    if faiz_p:
        p1.append("Para politikası tarafında " + _cumleler_birlestir(faiz_p))
    if enf_p:
        p1.append("Enflasyonda son yayımlanan veriye göre " + _cumleler_birlestir(enf_p))
    if akim_p:
        p1.append(_cumleler_birlestir(akim_p).capitalize())

    # Öne çıkanlar listesi hemen altta zaten duruyor; metinde en fazla ikisi anılır,
    # yoksa aynı cümleler iki kez okunur.
    onemli = [o["metin"] for o in b["one_cikanlar"]][:2]
    if onemli:
        p1.append("Değişim sınırını aşanlar arasında: " + " ".join(onemli))

    # ── ne bekleniyor
    kritik = b.get("kritik_takvim") or []
    # Pazar bülteninde "yakın" = yarın başlayan hafta (8 gün); hafta içi günlükte 4 gün.
    yakin = [k for k in kritik if k["kalan_gun"] <= (8 if haftalik else 4)]
    uzak = [k for k in kritik if k["kalan_gun"] > (7 if haftalik else 4)][:5]
    p2 = []
    if yakin:
        satir = []
        for k in yakin:
            m = (f"{k['tr_tarih']} {k['gun']}" + (f" {k['saat']}" if k["saat"] else "")
                 + f" — {k['olay']}")
            if k.get("beklenti"):
                m += f" ({k['beklenti']})"
            satir.append(m)
        p2.append(("Önümüzdeki hafta" if haftalik else "Önümüzdeki günlerde")
                  + " takvimde birinci derece veri var: " + "; ".join(satir) + ".")
    else:
        p2.append("Önümüzdeki hafta birinci derece bir veri ya da karar yok."
                  if haftalik else
                  "Önümüzdeki birkaç gün içinde birinci derece bir veri ya da karar yok.")
    if uzak:
        p2.append("Daha ileride: " + "; ".join(
            f"{k['tr_tarih']} {k['olay']}" + (f" ({k['beklenti']})" if k.get("beklenti") else "")
            for k in uzak) + ".")

    duyuru = b["haberler"]["kurum"]
    if duyuru:
        p2.append("Kurum duyurusu: " + "; ".join(h["baslik"] for h in duyuru[:4]) + ".")

    return {"ne_oldu": " ".join(p1), "ne_bekleniyor": " ".join(p2)}


def temalar() -> dict:
    """Tema defteri — bültenin hafızası.

    Günlük bülten olayları görür ama TEMAYI göremez: dört varlığın aynı sebeple
    hareket ettiğini fark etmek, her birini ayrı ayrı açıklamaktan farklı bir iştir.
    Defter bu farkı kapatır ve günler arasında süreklilik sağlar.
    """
    y = BURASI / "temalar.json"
    if not y.exists():
        return {}
    try:
        d = json.loads(y.read_text(encoding="utf-8"))
    except Exception:
        return {}
    # Her temanın izlediği varlıkların GÜNCEL hareketini iliştir: okur temayı
    # okurken sayıyı da görsün, yazar da tezle veriyi yan yana koyabilsin.
    piyasa_satir = {}
    try:
        import piyasa as piyasa_m
        ham = piyasa_m._ham_veri()
        for v in piyasa_m.VARLIKLAR:
            r = piyasa_m.satir(v, ham["seri"])
            if r:
                piyasa_satir[r["ad"]] = r
        for t in piyasa_m.tr_faizleri():
            piyasa_satir.setdefault(t["ad"], {"ad": t["ad"], "son": t["deger"],
                                              "birim": t["birim"], "d1": None, "h1": None,
                                              "ybb": None, "degisim_birim": ""})
        # Türev büyüklükler (eğri eğimleri, crack spread'ler) de temalara bağlanır:
        # enerji teması rafineri marjı olmadan, arz teması eğri eğimi olmadan eksiktir.
        for t in piyasa_m.turetilmis(ham["seri"]):
            piyasa_satir.setdefault(t["ad"], {"ad": t["ad"], "son": t["deger"],
                                              "birim": t["birim"], "d1": t.get("d1"),
                                              "h1": None, "ybb": None, "degisim_birim": ""})
    except Exception:
        pass
    for t in d.get("temalar", []):
        t["olculer"] = [piyasa_satir[a] for a in t.get("varliklar", []) if a in piyasa_satir]
    # Defterin yazara yönelik iç notları (`_aciklama`, `_yazar_notu`) bültenin
    # JSON'uyla public depoya gidiyordu. Okura gitmeyen not siteye de gitmez.
    for k in [k for k in d if k.startswith("_") and k != "_son_guncelleme"]:
        d.pop(k, None)
    return d


def uret(tarih: date | None = None, haber_tara: bool = True,
         takvim_ufku: int | None = None, tur: str = "gunluk") -> dict:
    """tur: "gunluk" (hafta içi sabah) | "haftalik" (pazar akşamı, haftaya bakış)."""
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
        # OKURA GÖRÜNEN AD KAYDA YAZILIR. Site bu adı eskiden proje sayfasının
        # başlığından çözüyordu ve bu, HER HATTIN BİR PANOSU OLDUĞUNU varsayar;
        # ölçümünü bir yazıya besleyen hat (panosu yok) sayfada slug'a düşerdi.
        # Ad tek yerde tanımlı (ayar.HAT_ADI), kayıt onu taşır.
        return {**asdict(o), "hat_ad": ayar.HAT_ADI.get(o.hat, "") if o.hat else ""}

    one_cikan = [dk(o) for o in olaylar if o.seviye == "onemli"]
    notlar = [dk(o) for o in olaylar if o.seviye == "dikkat" and o.grup != "diger"]
    gunluk = [dk(o) for o in olaylar if o.seviye == "bilgi" or
              (o.seviye == "dikkat" and o.grup == "diger")]

    gruplar = []
    for gid, gbaslik in ayar.GRUPLAR:
        icerik = [dk(o) for o in olaylar if o.grup == gid and o.seviye in ("onemli", "dikkat")]
        if icerik:
            gruplar.append({"id": gid, "baslik": gbaslik, "olaylar": icerik})

    # 3) takvim — haftalık bültende kapsam genişler
    haftalik = tur == "haftalik"
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

    # 4) cross-asset piyasa fotoğrafı (TL faizleri + global varlıklar + türevler)
    try:
        piyasa = piyasa_m.topla(haftalik=haftalik)
    except Exception as e:                                      # noqa: BLE001
        piyasa = {"hata": f"{type(e).__name__}: {e}", "gruplar": [], "turetilmis": [],
                  "tr_faizleri": [], "en_cok_hareket": {}, "eksik": [], "kaynak_yok": []}

    # 5) haberler — bölge × alan bölümlerine ayrılmış hâlde
    haberler, okunamayan, bolumler, kilit = ([], [], [], [])
    if haber_tara:
        try:
            import haber as haber_m
            # Haftalık bülten haftanın TAMAMINI tarar (168 saat): 19 Ağustos'taki ABD
            # Hazinesi geri alım duyurusu 72 saatlik pencerenin dışında kalmış ve
            # haftanın ana sürücüsü bültene hiç girmemişti.
            # Günlük pencere de 36'dan 72 saate çıkarıldı: 36 saat, cuma akşamı çıkan
            # bir gelişmeyi pazartesi sabahı göremiyordu. Kilit gelişme puanlaması
            # zaten eskiyi geri plana atıyor, yani geniş pencere gürültü üretmiyor.
            h, okunamayan = haber_m.tara(pencere_saat=168 if haftalik else 72)
            # SIRA BAĞLAYICI: bolumle() haberleri hem PUANLAR (onem) hem de
            # kaynağından okuyup ZENGİNLEŞTİRİR (ozet), yani h'yi yerinde
            # değiştirir. Dondurma işlemi önce yapılırsa kaydedilen listede her
            # maddenin önemi 0.0 kalır ve özetler eksik olur — 2026-08-26'da
            # 112 haberin hepsi 0.0 puanla kaydedilmişti, aralarında 12 kaynağın
            # yazdığı "Treasury buyback" haberi de vardı.
            # bolumle() haberleri puanlar, kaynağından zenginleştirir ve kilit
            # listesini de döndürür. Dondurma ONDAN SONRA ve TEK yerde yapılır:
            # kilit_gelismeler()'i ikinci kez çağırmak zenginleştirilmiş metinle
            # yeniden puanlıyor, üst düzey listede eski puan kalıyor ve aynı
            # haber aynı dosyada iki ayrı önem puanıyla yazılıyordu.
            bolumler, kilit = haber_m.bolumle(h)
            haberler = [asdict(x) for x in h]
        except Exception as e:                                  # noqa: BLE001
            okunamayan = [f"haber taraması düştü: {type(e).__name__}"]

    b = {
        "tarih": tarih.isoformat(),
        "gun": takvim_m.GUNLER_TR[tarih.weekday()],
        "tr_tarih": f"{tarih.day} {takvim_m.AYLAR_TR[tarih.month - 1]} {tarih.year}",
        # DİLİMLİ damga. Koşucu UTC'de çalışıyor ve eski dilimsiz damga sayfada
        # İstanbul saati gibi basılıyordu ("04:30" — 07:30'un UTC hâli).
        "olusturma": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gostergeler": gostergeler(haftalik),
        # Rejim panosu: gösterge şeridi seviyeyi verir, bu pano seviyelerin
        # BİRLİKTE ne anlama geldiğini. Her satır iki ölçülen büyüklüğün farkı
        # ve o farkın işareti rejimi tarif ediyor.
        "rejim": rejim_m.panosu(),
        "piyasa": piyasa,
        "temalar": temalar(),
        "one_cikanlar": one_cikan,
        "notlar": notlar,
        "gruplar": gruplar,
        "veri_gunlugu": gunluk,
        # Söz defteri: bültenin verdiği sözlerin okura görünen hâli. Defter
        # zaten tutuluyordu ama yalnız yazı katmanı ve denetim görüyordu;
        # hesap vermenin okura ulaşmayan hâli hesap vermek sayılmaz.
        "izleme": soz_m.ozet(tarih.isoformat()),
        # Sayfadaki satır içi SVG'lerin verisi. Plotly bültene girmez: gömülü
        # kütüphane tek grafikte 4,6 MB ve sabah notu o ağırlığı kaldırmaz.
        "grafikler": grafik_m.hazirla(),
        # Beklenti halkasının kapanan ucu: vakti geçmiş olaylar için ne geldi,
        # sürpriz ne kadar, piyasa ne yaptı. Takvim tek başına yalnız ileri
        # bakıyordu; beklenti yayımlayıp gerçekleşmeyi yayımlamamak eksik kalıyordu.
        "sonuclar": surpriz_m.gecmis_olaylar(kayitlar, piyasa, tarih),
        "takvim": takvim_bloklari,
        "kritik_takvim": kritik,
        "haftalik": haftalik,
        "haberler": {
            "bolumler": bolumler,
            "kilit": kilit,
            "kurum": [h for h in haberler if h.get("kurum")],
            "haber": [h for h in haberler if not h.get("kurum")],
            "okunamayan": okunamayan,
        },
        # Gündem yazısı: bölüm bölüm ayrıntılı metin. Kural tabanlı koşu buraya
        # başlıkları cümleye çevirerek bir TABAN koyar; yorum katmanı kaynakları
        # açıp okuyarak bu metni ZENGİNLEŞTİRİR ve yerine geçer.
        "gundem": {},
        # Yazı-özel bölümlerin sırası ve başlıkları (haber listesi olmayanlar)
        "gundem_yazi_bolumleri": [{"id": i, "baslik": t} for i, t in ayar.GUNDEM_YAZI_BOLUMLERI],
        "yorum": None,
        "yorum_zamani": None,
        "tur": tur,
        "surum": 2,
    }
    b["ozet"] = piyasa_ozeti(b, haftalik=haftalik)
    b["gundem"] = gundem_tabani(b)
    b["gundem_kaynagi"] = "otomatik"        # yorum katmanı yazınca "yazili" olur
    return b


def gundem_tabani(b: dict) -> dict:
    """Bölüm bölüm taban metni: başlıklar ve varsa özetleri cümleye dizilir.

    Bu, yorum katmanının yerine geçmez — o katman kaynakları açıp okuyarak
    ayrıntılı yazıyı üretir. Ama katman çalışmadığında (bulut koşusu) bülten
    yine de "gündemde ne var" sorusunu cevaplar; boş bölüm bırakmaz.
    """
    out = {}
    for bol in b.get("haberler", {}).get("bolumler", []):
        if bol["id"] == "kurum":
            continue
        cumleler = []
        for m in bol["maddeler"]:
            c = m["baslik"].split(" - ")[0].strip().rstrip(".")
            if m.get("ozet"):
                c += f" — {m['ozet'].rstrip('.…')}"
            kaynak = m.get("kaynak", "")
            if kaynak and not kaynak.startswith("Arama"):
                c += f" ({kaynak})"
            cumleler.append(c + ".")
        if cumleler:
            out[bol["id"]] = " ".join(cumleler)
    return out


def ozet_ekle(b: dict) -> dict:
    b["ozet"] = piyasa_ozeti(b, haftalik=b.get("haftalik", False))
    return b


def yaz(b: dict) -> Path:
    CIKTI.mkdir(parents=True, exist_ok=True)
    y = CIKTI / f"{b['tarih']}.json"
    # Yorum katmanı daha önce yazdıysa KORUNUR: deterministik koşu yorumu silmemeli.
    if y.exists():
        try:
            eski = json.loads(y.read_text(encoding="utf-8"))
            if eski.get("yorum"):
                b["yorum"], b["yorum_zamani"] = eski["yorum"], eski.get("yorum_zamani")
            # Yorum katmanının yazdığı ayrıntılı gündem metni, sonraki
            # deterministik koşularda TABAN metinle ezilmemeli.
            if eski.get("gundem_kaynagi") == "yazili" and eski.get("gundem"):
                b["gundem"], b["gundem_kaynagi"] = eski["gundem"], "yazili"
                # ÖZET DE YAZI KATMANININDIR. ozet_ekle() her koşuda
                # b["ozet"]'i makine özetiyle EZİYORDU ve burada hiçbir
                # koruma yoktu: yazı katmanının "ne oldu / ne bekleniyor"
                # paragrafları sessizce kayboluyor, sayfa yine "yazılı"
                # göründüğü için de kimse fark etmiyordu. Yorum ve gündem
                # korunuyorsa özet de korunmalı — üçü aynı elden çıkar.
                if eski.get("ozet"):
                    b["ozet"] = eski["ozet"]
            # --habersiz koşusu, daha önce toplanmış haberleri SİLMEMELİ: gün içinde
            # hızlı bir yeniden üretim bülteni fakirleştirmesin.
            eski_h = (eski.get("haberler") or {})
            yeni_h = b.get("haberler") or {}
            if not (yeni_h.get("kurum") or yeni_h.get("haber")) and \
                    (eski_h.get("kurum") or eski_h.get("haber")):
                b["haberler"] = eski_h
            # Piyasa fotoğrafı BOŞ dönmüşse eskisi korunur. 2026-08-25 bulut
            # koşusunda yfinance kurulu olmadığı için piyasa katmanı sessizce
            # boş döndü ve o günün bülteninde 11 varlık grubu, 24 TL faiz satırı
            # SİLİNDİ — bülten yazılı görünmeye devam ettiği için de sayfa
            # piyasasız yayında kaldı. Eski fotoğraf, hiç fotoğraf yoktan iyidir;
            # ne zamana ait olduğu zaten kaydın kendi damgasında yazar.
            eski_p = (eski.get("piyasa") or {})
            yeni_p = b.get("piyasa") or {}
            if not (yeni_p.get("gruplar") or yeni_p.get("tr_faizleri")) and \
                    (eski_p.get("gruplar") or eski_p.get("tr_faizleri")):
                b["piyasa"] = eski_p
                # Tema ölçüleri de piyasa katmanından besleniyor; yalnız
                # fotoğrafı geri yükleyip ölçüleri boş bırakmak, sayfada dolu
                # bir piyasa tablosunun hemen altında sayısız bir tema bölümü
                # bırakıyordu. İkisi aynı kaynaktan gelir, birlikte gelmeli.
                eski_t = {x.get("ad"): x for x in
                          ((eski.get("temalar") or {}).get("temalar") or [])}
                for tema in ((b.get("temalar") or {}).get("temalar") or []):
                    if not tema.get("olculer") and eski_t.get(tema.get("ad"), {}).get("olculer"):
                        tema["olculer"] = eski_t[tema["ad"]]["olculer"]
                        tema["olcu_bayat"] = True
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
