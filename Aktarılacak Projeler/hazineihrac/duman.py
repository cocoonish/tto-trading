# -*- coding: utf-8 -*-
"""Hazine ihraç hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer, çıkış 0/1.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur ve düşerse hat hiç
koşmaz. Sınama yalnız `--denetle` yazan birinin eline bırakılsaydı zamanlanmış
koşu onu hiç sormaz, bozuk bir ölçüm katmanının çıktısı siteye kopyalanırdı.

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR (09.09.2026'da ölçülenler)
--------------------------------------------------------------------------
 1. ERKEN DURMA ÇIPASI — artımlı taramanın çıpası yalnız `hazine_ihale_verileri
    .xlsx`ten okunuyordu ve o dosya .gitignore'da: BULUTTA hiç yok. Çıpa None
    kalınca her duyuru "yeni" sayılıyor, ardışık-eski sayacı hiç artmıyor ve
    kazıyıcı her tam kipte MAX_PAGES (200) sayfayı baştan geziyordu. Çıpa artık
    depoda İZLENEN CSV'ye düşer. Aynı kusur birikmiş veriyi okuyan yolda bir
    kez düzeltilmişti; erken durma yolu genelleştirilmemişti.
 2. YENİLİK KARARI — kararın üç hâli var ve ikisi eskiden koşulsuz "yeni"
    diyordu. Çıpa yoksa daha önce İŞLENMİŞ bir duyuru yeni değildir; başlıktan
    tarih okunamadıysa işlenmemiş duyuru yeni sayılır (erken durma yüzünden hiç
    okunmamış bir duyuruyu atlamak, birkaç fazla sayfadan pahalıdır).
 3. HEDEFSİZ TAKVİM YAZILMAZ — 06.09.2026'da duyurusuz bir koşu boş bir hedef
    tablosuyla döndü, planlı takvim hedefsiz ve ölçeksiz kuruldu ve dosyanın
    üzerine yazıldı; sayfanın adıyla çağırdığı on anahtar bir sonraki özet
    koşusunda düşecek, yayın kapısı ENGEL verecekti. İki kapı birden sınanıyor:
    duyurusuz koşu hedef tablosunu DİSKTEN döndürür, hedefsiz takvim dosyaya
    yazılmaz. Depodaki takvimin kendisi de sınanır (hedef sütunu dolu, ölçekleme
    uygulanmış): bozuk bir sürüm siteye ancak bir kez kopyalanır.
 4. SAYFA SÖZLEŞMESİ — sayfanın <Deger> ile adıyla çağırdığı her anahtar
    özette olmalı; eksik anahtar yayın kapısında ENGEL üretir.
 5. SAAT YAZIMI — günlük saatler GG.AA.YYYY; hiçbir saat anahtarında ISO ya da
    ay adı yok. Şekil 02'nin birleşik damgasındaki İKİ tarih de çözülmeli ve
    yarına düşmemeli (sayfa sınavı 18b her tarihi ayrı ayrı sınar).
 6. TAKVİMİN UÇLARI — plan_bas takvimin ilk İHRACIDIR ve DOĞRUDAN SATIŞ
    olabilir: Ağustos–Ekim takviminde plan_bas 20.08.2026 (doğrudan satış), ilk
    ihale 07.09.2026 idi — 18 gün. Hattın ana saatini yalnız ihale sonucu
    ilerlettiği için "sıradaki ihale" ayrı bir anahtardır (plan_ihale_bas).
    Uçlar satır sırasından değil tarihten okunur.
 7. OKUR DİLİ — özetin cümle olan alanları sayfaya olduğu gibi basılır.

Koşum:  python3 duman.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import tempfile

import pandas as pd

BURASI = pathlib.Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))

import main as hat                                                 # noqa: E402

GECTI, DUSTU = 0, 0
_KUSUR: list[str] = []

GUN_RX = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
TARIH_RX = re.compile(r"\d{2}\.\d{2}\.\d{4}")
ISO_RX = re.compile(r"\d{4}-\d{2}")
AY_ADLARI = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
MDX = KOK / "site" / "src" / "content" / "projeler" / "hazine-ihrac.mdx"


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    global GECTI, DUSTU
    if kosul:
        GECTI += 1
        print(f"  ✓ {ad}")
    else:
        DUSTU += 1
        _KUSUR.append(ad)
        print(f"  ✗ {ad}" + (f"\n      {ayrinti}" if ayrinti else ""))


def _ozet() -> dict:
    yol = BURASI / "ozet.json"
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else {}


def _mdx() -> str:
    return MDX.read_text(encoding="utf-8") if MDX.exists() else ""


def _planli() -> pd.DataFrame:
    return pd.read_csv(BURASI / hat.PLANNED_CSV, encoding="utf-8-sig")


def _kaynak(fn) -> str:
    import inspect
    return inspect.getsource(fn)


# ── 1. erken durma çıpası ────────────────────────────────────────────────────
def bolum_cipa() -> None:
    print("\n▶ Erken durma çıpası")
    o = _ozet()
    with tempfile.TemporaryDirectory() as td:
        sina("çıpa dosyası yoksa None", hat.birikmis_son_ihale(td) is None)
        pd.DataFrame({"İhale Tarihi": ["01.03.2026", "15.07.2026", "09.02.2026"],
                      "ISIN": ["a", "b", "c"]}).to_csv(
            os.path.join(td, hat.CSV_OUTPUT), index=False, encoding="utf-8-sig")
        c = hat.birikmis_son_ihale(td)
        sina("Excel yokken çıpa İZLENEN CSV'den okunur",
             c is not None and c.strftime("%d.%m.%Y") == "15.07.2026", repr(c))
    d = hat.birikmis_son_ihale(str(BURASI))
    sina("depodaki çıpa hattın kendi saatiyle aynı",
         d is not None and o.get("_tarih") and d.strftime("%d.%m.%Y") == o["_tarih"],
         f"çıpa={d} · _tarih={o.get('_tarih')}")
    src = _kaynak(hat.TreasuryAuctionScraper.get_auction_announcement_urls)
    sina("tarama çıpayı ortak fonksiyondan alır", "birikmis_son_ihale(" in src)
    sina("tarama çıpayı Excel'den DOĞRUDAN okumaz", "EXCEL_OUTPUT" not in src,
         "xlsx .gitignore'da; doğrudan okuma bulutta çıpayı None yapar")
    sina("ardışık-eski sayacı çıpa yokken de işler",
         bool(re.search(r"if not FORCE_ALL_FETCH:\s*\n\s*if page_has_any_auction"
                        r" and not page_has_new_auction", src)),
         "sayaç bir çıpa koşuluna bağlanırsa bulutta hiç artmaz")


# ── 2. yenilik kararının doğruluk tablosu ────────────────────────────────────
def bolum_yenilik() -> None:
    print("\n▶ Yenilik kararı (duyuru_yeni)")
    cipa = pd.Timestamp("2026-08-18")
    y = hat.duyuru_yeni
    sina("çıpa var · ihale çıpa günü → yeni", y("u", pd.Timestamp("2026-08-18"), cipa, set()))
    sina("çıpa var · ihale çıpadan yeni → yeni", y("u", pd.Timestamp("2026-09-14"), cipa, set()))
    sina("çıpa var · ihale çıpadan eski → eski", not y("u", pd.Timestamp("2026-07-01"), cipa, set()))
    sina("çıpa yok · işlenmiş duyuru → ESKİ", not y("u", None, None, {"u"}),
         "eski kod burada koşulsuz 'yeni' diyordu; sayaç hiç artmıyordu")
    sina("çıpa yok · işlenmemiş duyuru → yeni", y("v", None, None, {"u"}))
    sina("tarih okunamadı · işlenmemiş → yeni", y("v", pd.NaT, cipa, {"u"}))
    sina("tarih okunamadı · işlenmiş → eski", not y("u", pd.NaT, cipa, {"u"}))
    sina("zorla çekimde her duyuru yeni",
         y("u", pd.Timestamp("2020-01-01"), cipa, {"u"}, zorla=True))


# ── 3. hedefsiz takvim yazılmaz ──────────────────────────────────────────────
def bolum_takvim_kapisi() -> None:
    print("\n▶ Planlı takvimin yazma kapısı")
    kol = "Aylık Strateji Hedefi (Milyar TL)"
    sina("hedefsiz takvim 'hedef var' saymaz",
         not hat._hedef_var(pd.DataFrame({kol: [None, None]})))
    sina("tek dolu hücre yeter", hat._hedef_var(pd.DataFrame({kol: [None, 261.9]})))
    sina("hedef sütunu hiç yoksa 'hedef var' değil",
         not hat._hedef_var(pd.DataFrame({"İhale Tarihi": ["14.09.2026"]})))
    src = _kaynak(hat.TreasuryAuctionScraper.scrape_all_auctions)
    sina("duyurusuz koşu hedef tablosunu diskten döndürür",
         "self._mevcut_karsilastirma()" in src,
         "boş çerçeve döndürmek hedefsiz bir takvim yazdırır")
    ana = _kaynak(hat.main)
    sina("takvim yalnız hedef varken yazılır ve arşivlenir",
         bool(re.search(r"if not planned_df\.empty and _hedef_var\(planned_df\)", ana)))
    pl = _planli()
    sina("depodaki takvimin hedef sütunu dolu", hat._hedef_var(pl),
         "hedefsiz sürüm siteye kopyalanırsa on anahtar birden düşer")
    ih = pl[pl["Yöntem"].astype(str).str.contains("hale", na=False)]
    t = pd.to_numeric(ih["Tahmini Gerçekleşme (Milyon TL)"], errors="coerce")
    g = pd.to_numeric(ih["Geçmiş Ort. Gerçekleşme (Milyon TL)"], errors="coerce")
    sina("tahminlere strateji ölçeklemesi uygulanmış",
         bool(len(ih)) and bool((t.round(0) != g.round(0)).any()),
         "her satırda tahmin = geçmiş ortalama ise ölçekleme hiç koşmamıştır")


# ── 4. sayfa sözleşmesi ──────────────────────────────────────────────────────
def bolum_sozlesme() -> None:
    print("\n▶ Sayfa sözleşmesi")
    o, mdx = _ozet(), _mdx()
    sina("proje sayfası bulundu", bool(mdx), str(MDX))
    cagrilan = set(re.findall(r'proje="hazine-ihrac"\s+anahtar="([^"]+)"', mdx))
    eksik = sorted(k for k in cagrilan if k not in o)
    sina("sayfanın çağırdığı her anahtar özette var", bool(cagrilan) and not eksik,
         f"eksik: {eksik}")
    acik = set(re.findall(r'tarihAnahtari="([^"]+)"', mdx))
    sina("sayfadaki her açık damga anahtarı özette çözülüyor",
         all(isinstance(o.get(a), str) and o[a] for a in acik), f"{sorted(acik)}")


# ── 5. saat yazımı ───────────────────────────────────────────────────────────
def bolum_saat() -> None:
    print("\n▶ Saat yazımı")
    o = _ozet()
    yarin = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    saatler = {k: v for k, v in o.items() if k.endswith("_tarih")}
    sina("ana saat GG.AA.YYYY", bool(GUN_RX.match(str(o.get("_tarih")))), repr(o.get("_tarih")))
    sina("takvim saati GG.AA.YYYY", bool(GUN_RX.match(str(o.get("plan_tarih")))),
         repr(o.get("plan_tarih")))
    sina("saat anahtarlarında ISO ya da ay adı yok",
         not [k for k, v in saatler.items()
              if ISO_RX.search(str(v)) or any(a in str(v) for a in AY_ADLARI)],
         str({k: v for k, v in saatler.items() if ISO_RX.search(str(v))}))
    sina("hiçbir saat yarına düşmüyor",
         all(pd.to_datetime(v, format="%d.%m.%Y", errors="coerce") < yarin
             for v in saatler.values() if GUN_RX.match(str(v))),
         str(saatler))
    kisa = str(o.get("plan_gerc_kisa", ""))
    tarihler = TARIH_RX.findall(kisa)
    sina("birleşik damga iki tarih taşır ve ikisi de çözülüyor",
         len(tarihler) == 2 and all(
             pd.notna(pd.to_datetime(t, format="%d.%m.%Y", errors="coerce")) for t in tarihler),
         repr(kisa))
    sina("birleşik damganın bacakları hattın kendi saatleri",
         set(tarihler) == {str(o.get("plan_tarih")), str(o.get("_tarih"))}, repr(kisa))


# ── 6. takvimin uçları ve sıradaki ihale ─────────────────────────────────────
def bolum_uclar() -> None:
    print("\n▶ Takvimin uçları")
    o, pl = _ozet(), _planli()
    t = pd.to_datetime(pl["İhale Tarihi"], dayfirst=True, errors="coerce").dropna()
    ih = pl[pl["Yöntem"].astype(str).str.contains("hale", na=False)]
    ti = pd.to_datetime(ih["İhale Tarihi"], dayfirst=True, errors="coerce").dropna()
    sina("plan_bas takvimin EN ERKEN günü (satır sırası değil)",
         o.get("plan_bas") == t.min().strftime("%d.%m.%Y"),
         f"{o.get('plan_bas')} vs {t.min():%d.%m.%Y}")
    sina("plan_son takvimin EN GEÇ günü",
         o.get("plan_son") == t.max().strftime("%d.%m.%Y"),
         f"{o.get('plan_son')} vs {t.max():%d.%m.%Y}")
    src = pathlib.Path(BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    sina("özet üreticisi sıradaki İHALE gününü ayrı yazar",
         "plan_ihale_bas" in src,
         "plan_bas doğrudan satış olabilir; 'veri gecikti' kararı ihale gününe bakar")
    pi = o.get("plan_ihale_bas")
    sina("sıradaki ihale günü yazıldıysa gerçekten bir İHALE satırı",
         pi is None or pi == ti.min().strftime("%d.%m.%Y"),
         f"{pi} vs {ti.min():%d.%m.%Y}")
    if pi is None:
        # Sessizce atlanan bir ölçüt geçen ölçütle aynı görünür; anahtarın
        # henüz yazılmamış olması ADIYLA basılır.
        print("      · not: anahtar depodaki özette henüz yok — hattın bir "
              "sonraki koşusunda yazılır, ölçüt o gün bağlayıcı olur")
    sina("takvim hattın ana saatinden ileri başlıyor",
         t.min() > pd.to_datetime(o.get("_tarih"), format="%d.%m.%Y"),
         "takvim gerçekleşmiş bir ihaleyi 'planlı' gösteriyorsa tazelenmemiştir")


# ── 7. okur dili ─────────────────────────────────────────────────────────────
def bolum_okur_dili() -> None:
    print("\n▶ Okur dili")
    try:
        sys.path.insert(0, str(KOK / "ortak"))
        import okur_dili
    except ImportError as e:                                           # noqa: BLE001
        sina("okur_dili modülü bulundu", False, str(e))
        return
    o = _ozet()
    cumle = [v for v in o.values() if isinstance(v, str) and " " in v and len(v) > 20]
    bulgu = [b for b in okur_dili.kosu_kaydi_tara(cumle)
             if b[1] in ("kod dili", "yapım dili")]
    sina("özetin cümle alanlarında kod/yapım dili yok", not bulgu, str(bulgu[:5]))


def main() -> int:
    print("Hazine ihraç hattı — duman sınaması (ağa çıkmaz)")
    bolum_cipa()
    bolum_yenilik()
    bolum_takvim_kapisi()
    bolum_sozlesme()
    bolum_saat()
    bolum_uclar()
    bolum_okur_dili()
    print(f"\n{GECTI} geçti · {DUSTU} düştü")
    if _KUSUR:
        print("Düşenler: " + " | ".join(_KUSUR))
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
