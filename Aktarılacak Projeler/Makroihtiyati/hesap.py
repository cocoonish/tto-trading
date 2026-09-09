#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Makroihtiyati çerçevenin ölçülen izi — hesap katmanı.

Bu sayfa düzenleme METİNLERİNİ değil, düzenlemelerin VERİDEKİ ayak izini
ölçer. Kredi hattının kendi sayfasında gerekçelendirilmiş bir yasak var:
tebliğle değişen tarih ve oranlar koda gömülmez, çünkü bir sonraki duyuruda
sessizce yanlışa dönerler. Bu hat o yasağa uyar — sınırın kendisini çizmez,
sınırın bıraktığı üç izi çizer:

  ayrışma    Aynı ekonomide tüketici kredisi %43, ticari %19 büyüyorsa bu
             piyasa sonucu değil, kanal bazlı tavanların doğrudan ürünüdür.
  kaçak      Tavanın kapsamadığı kanala akış: bireysel kredi kartı büyümesinin
             tüketici kredisinden, kurumsal kartın ticariden farkı.
  fiyat      Miktar kısıtı fiyata yansır: ihtiyaç kredisi faizinin politika
             faizinden makası, kısıtın gölge fiyatıdır.

Düzenleme defteri (duzenlemeler.json) elle bakılan ayrı bir DOSYADIR, kod
değil: her kaydın kaynağı ve doğrulama durumu vardır ve sayfa yalnız
"dogrulandi" işaretli kayıtları basar. Doğrulanmamış tarih yayımlamak, bu
sitenin uydurma yasağının ihlalidir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent.parent
KREDI_HAT = KOK / "Aktarılacak Projeler" / "Kredi"
KREDI = KREDI_HAT / "data"
FONLAMA = KOK / "Aktarılacak Projeler" / "Fonlama" / "data"

# ŞEKİL SAAT DEFTERİ — figür → o figürü ÇİZEN bacağın saat anahtarı. Tek liste:
# grafik.py yazmadan önce buraya bakar (defterde olmayan figür yazılamaz),
# hesapla() damgayı buradan kurar. İki ayrı liste bir gün sessizce ayrışır.
SEKILLER = {
    "ayrisma.html": "g_tuketici_13y_tarih",        # haftalık kredi hacmi
    "kacak.html": "kacak_bkk_tarih",               # haftalık kredi hacmi
    "makas.html": "makas_ihtiyac_tarih",           # haftalık akım faiz
    "bkea.html": "bkea_std_isletme_tarih",         # üç aylık eğilim anketi
}


def yukle():
    h = pd.read_csv(KREDI / "metrik_haftalik.csv", parse_dates=["tarih"]).set_index("tarih")
    f = pd.read_csv(KREDI / "faiz.csv", parse_dates=["tarih"]).set_index("tarih")
    b = pd.read_csv(KREDI / "ceyreklik.csv", parse_dates=["tarih"]).set_index("tarih")
    g = pd.read_csv(FONLAMA / "gunluk.csv", parse_dates=["tarih"],
                    usecols=["tarih", "politika"]).set_index("tarih")
    g["politika"] = g["politika"].ffill()          # adım fonksiyonu (bkz. Carry hattı)
    # Faiz serisi haftalık (cuma); politika o güne eşlenir.
    # faiz.csv kendi 'politika' kolonunu taşıyor; kaynak tek olsun diye o
    # atılır, Fonlama'nın günlük ve ffill'li serisi kullanılır.
    f = f.drop(columns=["politika"], errors="ignore").join(g, how="left")
    f["politika"] = f["politika"].ffill()
    for kanal in ("ihtiyac", "ticari_tl", "konut"):
        f[f"makas_{kanal}"] = f[f"f_{kanal}"] - f["politika"]
    f["makas_mevduat"] = f["mev_tl"] - f["politika"]
    # Kaçak: kapsam dışı kanalın kapsanan kanaldan büyüme farkı
    h["kacak_bkk"] = h["g_bkk_13y"] - h["g_tuketici_13y"]
    h["kacak_kurumsal_kart"] = h["g_kurumsal_kart_13y"] - h["g_ticari_13y"]
    h["ayrisma"] = h["g_tuketici_13y"] - h["g_ticari_13y"]
    return h, f, b


def ceyrek_saati(t, bugun=None) -> tuple[str, str]:
    """Üç aylık gözlemin SAATİ ve okur ETİKETİ.

    Kaynak çeyreği çeyreğin İLK gününe damgalıyor (Kredi hattının veri katmanı
    bunu adıyla yazıyor: 2026-Ç2 → 2026-04-01). O damga sayfaya olduğu gibi
    basıldığında okura bir GÜN gibi görünüyordu: 09.09.2026'da ölçüldü, şekil
    04'ün altında ve tablonun son satırında "01.04.2026" yazıyordu ve okur
    aradaki 161 günü anketin yaşı sanıyordu — oysa anket 30.06'da biten çeyreği
    ölçer, yaşı 71 gündür.

    Biçim sözleşmesi (ortak/bicim, iki tarafta aynı): üç aylık saat çeyreğin
    SON AYIDIR, `AA.YYYY`; çözüldüğünde ayın son gününe demirlenir. Çeyreğin
    kendi adı bir ÖLÇÜ değil ETİKETTİR, ayrı anahtara yazılır ("2026-Ç2") ve
    hiçbir yaş ya da bayatlık hükmüne girmez.

    Çeyrek daha KAPANMADIYSA saat yazılmaz: kapanmamış bir ayın son günü
    yarına düşer ve yayın kapısı onu (haklı olarak) ENGEL sayar. Anket kapanan
    çeyreği ölçtüğü için bu hâl pratikte doğmaz; ölçülmemiş bir günü ilan
    etmektense boş bırakmak sözleşmenin kendisidir.
    """
    t = pd.Timestamp(t)
    bugun = pd.Timestamp(bugun) if bugun is not None else pd.Timestamp.today().normalize()
    donem_sonu = t + pd.offsets.MonthEnd(3)          # 2026-04-01 → 2026-06-30
    etiket = f"{t.year}-Ç{(t.month - 1) // 3 + 1}"
    return ("" if donem_sonu > bugun else f"{donem_sonu:%m.%Y}"), etiket


def tolerans() -> dict[str, int] | None:
    """Tazelik eşikleri KREDİ hattının kendi tablosundan okunur — TEK KAYNAK.

    Bu hattın serileri kredi hattının dosyalarıdır; ikinci bir eşik yazılsaydı
    biri güncellenip öteki unutulurdu. Eşik okunamazsa sayı UYDURULMAZ: hüküm
    hiç yazılmaz ve sayfa "bayatlık ölçülmüyor" der (üç hâlli sözleşme).
    """
    try:
        if str(KREDI_HAT) not in sys.path:
            sys.path.append(str(KREDI_HAT))          # sona: kendi modüllerimiz önde kalsın
        import veri as kredi_veri
        return {"haftalik": int(kredi_veri.tazelik_tolerans("haftalik")),
                "ceyrek": int(kredi_veri.tazelik_tolerans("ceyrek"))}
    except Exception:                                # noqa: BLE001
        return None


def kredi_durumu() -> dict | None:
    """Kredi hattının koşu kaydı — tazelik uyarıları ORADA ölçülür."""
    y = KREDI / "veri_durum.json"
    try:
        return json.loads(y.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def bayatlik(ozet: dict, durum: dict | None, tol: dict | None,
             bugun=None) -> tuple[bool | None, str]:
    """Hattın bayatlık hükmü: (bayat, okura yazılan tek cümle).

    Sayfanın veri durumu şeridi üç hâllidir ve bu hat hiçbirini yazmıyordu:
    09.09.2026'da ölçüldü, şerit "bayatlık ölçülmüyor" basıyordu — oysa aynı
    serilerin tazeliği kredi hattında zaten ölçülüyordu. Hüküm iki bacağı
    ayrı ayrı sorar (haftalık kredi/faiz, üç aylık anket) ve üst hattın kendi
    tazelik uyarılarını SAYAR; uyarı metinleri okura kopyalanmaz, çünkü
    operatör için yazılmışlardır.

    Ölçülemiyorsa None döner: "veri taze" demek, ölçmemişken ölçmüş gibi
    davranmaktır.
    """
    if tol is None and durum is None:
        return None, ""
    bugun = pd.Timestamp(bugun) if bugun is not None else pd.Timestamp.today().normalize()
    sebep: list[str] = []
    if tol is not None:
        hafta = _tarihe(ozet.get("_tarih"))
        if hafta is not None:
            gun = (bugun - hafta).days
            if gun > tol["haftalik"]:
                sebep.append(f"haftalık kredi ve faiz serileri {gun} gündür ilerlemedi "
                             f"(tolerans {tol['haftalik']} gün)")
        anket = _tarihe(ozet.get("bkea_std_isletme_tarih"))
        if anket is not None:
            gun = (bugun - anket).days
            if gun > tol["ceyrek"]:
                sebep.append(f"üç aylık eğilim anketi {gun} gündür yenilenmedi "
                             f"(tolerans {tol['ceyrek']} gün)")
    kaynak_uyari = [u for u in ((durum or {}).get("uyarilar") or [])
                    if str(u).startswith(("TAZELİK", "BAYAT", "SERİ"))]
    if kaynak_uyari:
        sebep.append(f"kaynak seriler için {len(kaynak_uyari)} tazelik uyarısı düştü")
    if sebep:
        return True, ("Bayat veri: " + "; ".join(sebep)
                      + ". Sayfadaki sayılar bu koşuda ilerlememiş olabilir.")
    return False, ("Veri taze: haftalık kredi ve faiz serileri ile üç aylık "
                   "eğilim anketi toleransın içinde.")


def _tarihe(m):
    """`GG.AA.YYYY` ya da `AA.YYYY` → gün; çözülemezse None (ortak sözleşme)."""
    if not isinstance(m, str) or not m:
        return None
    for kalip in ("%d.%m.%Y", "%m.%Y"):
        try:
            t = pd.Timestamp(pd.to_datetime(m, format=kalip))
        except (ValueError, TypeError):
            continue
        return t + pd.offsets.MonthEnd(0) if kalip == "%m.%Y" else t
    return None


def defter() -> dict:
    y = BURASI / "duzenlemeler.json"
    if not y.exists():
        return {"kayitlar": []}
    try:
        return json.loads(y.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"kayitlar": []}


def hesapla(bugun=None):
    h, f, b = yukle()

    def son(df, kolon, ondalik=1):
        """(değer, son gözlemin GÜNÜ) — yazım çağrı yerinde, bacağın ritmine göre."""
        s = df[kolon].dropna()
        return (None, None) if s.empty else (round(float(s.iloc[-1]), ondalik),
                                             s.index[-1])

    ozet = {}
    for kolon in ("g_ar_13y", "g_tuketici_13y", "g_ticari_13y", "g_kobi_13y",
                  "g_bkk_13y", "g_kurumsal_kart_13y", "ayrisma", "kacak_bkk",
                  "kacak_kurumsal_kart", "npl", "kredi_mevduat"):
        d, t = son(h, kolon)
        if d is not None:
            ozet[kolon], ozet[f"{kolon}_tarih"] = d, f"{t:%d.%m.%Y}"
    for kolon in ("makas_ihtiyac", "makas_ticari_tl", "makas_konut",
                  "makas_mevduat", "f_ihtiyac", "f_ticari_tl", "mev_tl", "politika"):
        d, t = son(f, kolon, 2)
        if d is not None:
            ozet[kolon], ozet[f"{kolon}_tarih"] = d, f"{t:%d.%m.%Y}"
    # ÜÇ AYLIK BACAK — saat çeyreğin son ayı (AA.YYYY), çeyreğin adı ayrı anahtarda.
    etiket = ""
    for kolon in ("bkea_std_isletme", "bkea_std_kobi", "bkea_std_konut",
                  "bkea_std_diger", "bkea_talep"):
        d, t = son(b, kolon)
        if d is not None:
            saat, etiket = ceyrek_saati(t, bugun)
            ozet[kolon], ozet[f"{kolon}_tarih"] = d, saat
    # Sayfa çeyreğin adını ADIYLA çağırıyor: her koşuda yazılır, ölçülemezse "—".
    ozet["bkea_ceyrek"] = etiket or "—"
    ozet["bkea_ceyrek_tarih"] = ozet.get("bkea_std_isletme_tarih", "")

    dfr = defter()
    kayitlar = dfr.get("kayitlar", [])
    ozet["_tarih"] = ozet.get("g_ar_13y_tarih", "")

    # ── ŞEKİL SAAT DEFTERİ — her figür KENDİ bacağının günüyle damgalanır ────
    # GrafikEmbed, MDX'te `tarihAnahtari` verilmemişse şeklin altına hattın ANA
    # saatini (`_tarih`) basar; o saat de haftalık kredi bacağıdır. Ama bu hat
    # TEK saatli değil: haftalık kredi/faiz serilerinin (Cuma) yanında ÇEYREKLİK
    # Banka Kredileri Eğilim Anketi duruyor. Ölçüldü (03.09.2026): ceyreklik.csv
    # 2026-04-01'de (2026-Ç2 anketi) bitiyor, şekil 04'ün altında ise 21.08.2026
    # yazıyordu — 142 gün. Okur dört buçuk ay eski bir anketi bugünün verisi
    # sanıyordu; üstelik sayfanın kendi metni doğru söylüyor ("son çeyrekte"),
    # damga onu yalanlıyordu.
    #
    # Makas figürü (03) bugün TESADÜFEN doğru damgalıydı: faiz.csv ile
    # metrik_haftalik.csv'nin indeksleri şu an birebir aynı (1129 satır, ölçüldü)
    # — ama bunlar EVDS'te ayrı ürünler (hacimler bie_hpbitablo, faizler
    # bie_kt100h) ve faiz tablosunun bir hafta geç yayımlandığı gün damga
    # sessizce yanlışa döner. Bu yüzden her figür ana saate değil, ÇİZDİĞİ
    # çerçevenin ucuna bağlanır. Değerler yukarıda seriden OKUNDU, burada
    # türetilmiyor; bir bacak hiç ölçülemediyse anahtar None kalır ve sayfa o
    # şeklin altına tarih basmaz (yanlış tarih, tarihsizlikten kötüdür).
    ozet["_sekil_tarih"] = {ad: (ozet.get(anahtar) or None)
                            for ad, anahtar in SEKILLER.items()}
    ozet["defter_toplam"] = len(kayitlar)
    ozet["defter_dogrulanmis"] = sum(1 for k in kayitlar
                                     if k.get("dogrulama") == "dogrulandi")

    # ── BAYATLIK HÜKMÜ — sayfanın veri durumu şeridi üç hâlli okur ───────────
    bayat, cumle = bayatlik(ozet, kredi_durumu(), tolerans(), bugun)
    if bayat is not None:
        ozet["bayat"], ozet["bayat_cumlesi"] = bayat, cumle
    return h, f, b, ozet


if __name__ == "__main__":
    h, f, b, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("veri tarihi:", ozet["_tarih"])
    print(f"  ayrışma (tüketici − ticari)  {ozet['ayrisma']:+.1f} puan "
          f"({ozet['g_tuketici_13y']} vs {ozet['g_ticari_13y']})")
    print(f"  kaçak: BKK − tüketici        {ozet['kacak_bkk']:+.1f} puan (BKK {ozet['g_bkk_13y']})")
    print(f"  kaçak: kur. kart − ticari    {ozet['kacak_kurumsal_kart']:+.1f} puan")
    print(f"  makas: ihtiyaç − politika    {ozet['makas_ihtiyac']:+.2f} puan")
    print(f"  makas: ticari − politika     {ozet['makas_ticari_tl']:+.2f} puan")
    print(f"  makas: mevduat − politika    {ozet['makas_mevduat']:+.2f} puan")
    print(f"  BKEA işletme std ({ozet['bkea_ceyrek']}, saat {ozet['bkea_std_isletme_tarih'] or '—'})"
          f" {ozet['bkea_std_isletme']:+.1f}")
    print("  bayatlık:", ozet.get("bayat_cumlesi", "ölçülmedi"))
    print(f"  defter: {ozet['defter_toplam']} kayıt, {ozet['defter_dogrulanmis']} doğrulanmış")
