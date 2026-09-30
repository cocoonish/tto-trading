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
 8. VADE — TEK CETVEL (30.09.2026). Gerçekleşen vade gün/365,25'e bölünüp iki
    ondalığa yuvarlanıyordu, planın vadesi ise takvimin gün sayısından gün/365
    okunuyordu: plan ile gerçekleşen iki ayrı cetvelle ölçülüyordu ve panonun
    Eylül ortalaması (4,48) aynı veriden gün/365 ile kurulan ölçüden (4,49)
    ayrışıyordu. Tek tanım `vade_yil` · `plan_vade_yil`; birikimin eski satırları
    `vade_normalize` ile tarihlerden yeniden kurulur; üç aylık ortalama
    yuvarlanmış aylık ortalamalardan değil toplamlardan ve TAKVİM ayından.
    Canlı tahminin "benzer vade" hedefi de gün sayısından okunur — backtest'in
    sınadığı kural budur (etiket "5 Yıl" ile ayrışıyordu).
 9. AYRIŞTIRICI — bütün sonuç duyuruları yeniden okundu (kesif_valor.py, 286
    PDF · 471 ihale) ve üç yazım sapması ölçüldü: "İhraç (Valör ) Tarihi"
    (boşluk; valör okunamadı, vade boş kaldı, ortalamadan SESSİZCE düştü),
    "06/04/2020" (tarih okunamadı, iki ihale veri setine HİÇ girmedi) ve
    İngilizce sayı biçimi ("7,602" → 7,602 milyon TL; fiyat "87.561" → 87561).
    Maddeler duyuruların GERÇEK metin parçalarıyla koşar; Türkçe yolun
    değişmediği de aynı gerçek blokla sınanır.
10. İŞLENDİ DEFTERİ — duyuru PDF'i okunmadan ÖNCE işlendi sayılıyordu; o an
    düşen bir indirme ihaleyi kalıcı olarak kaybettiriyordu (23.03.2021 ×2,
    13.12.2021: defterde var, satırı yok). Defter artık tarihli satır veren
    PDF'in duyurusunu yazar; indirilemeyen ve tarihsiz PDF 0 sayılır. Defter
    CSV yazıldıktan SONRA kalıcılaşır ve main()'deki istisna sıfırla çıkmaz.
11. BİRİKİM KAYNAĞI — birikim önce git'e girmeyen Excel'den okunuyordu; CSV'ye
    yapılan bir düzeltme yerel bir tam koşuda sessizce geri alınırdı. Önce
    İZLENEN CSV.
12. İTFA ↔ ISIN — 24.08.2020 duyurusu değişken faizli TRT050527T17'nin itfasını
    öbür tahvilin tarihiyle yazıyor. ISIN kodu ve aynı tahvilin öbür ihaleleri
    BİRLİKTE tutuyorsa düzeltilir, tek başına ISIN yetmez.

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


# ── 8. vade — tek cetvel ────────────────────────────────────────────────────
def _dene(fn):
    """Maddenin hesabı sınamanın DIŞINDA koşar: istisna ölçütü değil duman.py'yi
    düşürürdü (bkz. CLAUDE.md, TUFEX/Büyüme). Döner: (değer, hata metni)."""
    try:
        return fn(), ""
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def bolum_vade() -> None:
    print("\n▶ Vade — tek cetvel (gün/365)")
    v, h = _dene(lambda: hat.vade_yil("12.04.2023", "01.03.2028"))
    sina("vade_yil: 12.04.2023 → 01.03.2028 = 1785 gün = 4,8904 yıl (strateji takvimi 1785 gün)",
         v == round(1785 / 365, 4), h or repr(v))
    v, h = _dene(lambda: (hat.vade_yil("", "01.03.2028"), hat.vade_yil("12.04.2023", "12.04.2023"),
                          hat.vade_yil("12.04.2023", "01.03.2020")))
    sina("okunamayan ya da geri giden vade BOŞ (uydurulmaz)", v == (None, None, None), h or repr(v))
    v, h = _dene(lambda: (hat.plan_vade_yil("2Yıl /707 Gün"), hat.plan_vade_yil("16Ay /483 Gün"),
                          hat.plan_vade_yil("5 Yıl"), hat.plan_vade_yil("6Ay")))
    sina("plan vadesi gün sayısından (gün varsa), yoksa etiketten",
         v == (round(707 / 365, 4), round(483 / 365, 4), 5.0, 0.5), h or repr(v))
    v, h = _dene(lambda: hat.plan_vade_yil("2Yıl /707 Gün") == hat.vade_yil("07.10.2026", "13.09.2028"))
    sina("plan ve gerçekleşen AYNI cetvel: takvimin 707 günü = valörden itfaya gün", v is True, h)

    for dosya in ("main.py", "vade_proj.py", "web_cikti_tahmin.py", "grafik_yenile.py", "ozet_uret.py"):
        kod = [sat.split("#")[0] for sat in (BURASI / dosya).read_text(encoding="utf-8").splitlines()]
        sina(f"{dosya}: vade 365.25'e bölünmüyor", not any("365.25" in sat for sat in kod))

    # vade_normalize: eski cetvel yeniden kurulur, satır düşmez, boş kalan boş kalır
    cer = pd.DataFrame({
        "ISIN": ["A", "B", "C"], "İhale Tarihi": ["10.04.2023", "11.04.2023", "12.04.2023"],
        "Valör Tarihi": ["12.04.2023", "12.04.2023", None],
        "İtfa Tarihi": ["01.03.2028", "12.04.2024", "01.03.2028"],
        "Vade (Yıl)": [None, 1.0, None], "Toplam(Gerçekleşme)": [100.0, 300.0, 50.0]})
    n, h = _dene(lambda: hat.vade_normalize(cer))
    sina("vade_normalize satır düşürmez", n is not None and len(n) == 3, h)
    if n is not None:
        sina("boş vade tarihlerden kurulur, eski cetvel (365,25) yeniden yazılır",
             list(n["Vade (Yıl)"][:2]) == [round(1785 / 365, 4), round(366 / 365, 4)], repr(list(n["Vade (Yıl)"])))
        sina("valörü olmayan satırın vadesi boş kalır", pd.isna(n["Vade (Yıl)"].iloc[2]))
        n2, h2 = _dene(lambda: hat.vade_normalize(n))
        sina("vade_normalize eşgüçlü (ikinci kez aynı)", n2 is not None and n2.equals(n), h2)

    # ağırlıklı ortalama: toplamlardan, takvim ayı penceresi
    w = pd.DataFrame({
        "ISIN": ["A", "B", "C", "D"],
        "İhale Tarihi": ["05.01.2026", "06.01.2026", "10.03.2026", "10.04.2026"],
        "Valör Tarihi": ["07.01.2026", "07.01.2026", "11.03.2026", "13.04.2026"],
        "İtfa Tarihi": ["07.01.2027", "07.01.2031", "11.03.2029", "13.04.2027"],
        "Vade (Yıl)": [None] * 4, "Toplam(Gerçekleşme)": [100.0, 100.0, 50.0, 50.0]})
    wa, h = _dene(lambda: hat.TreasuryAuctionScraper.calculate_weighted_average_maturity(None, w))
    sina("vade tablosu ağa çıkmadan kuruluyor", wa is not None and len(wa) == 3, h or repr(wa))
    if wa is not None and len(wa) == 3:
        yil = lambda a, b: (pd.Timestamp(b) - pd.Timestamp(a)).days / 365  # noqa: E731
        ocak = (yil("2026-01-07", "2027-01-07") + yil("2026-01-07", "2031-01-07")) / 2
        mart = yil("2026-03-11", "2029-03-11")
        nisan = yil("2026-04-13", "2027-04-13")
        # Nisan penceresi = Şubat–Nisan (TAKVİM): Ocak girmez; satır sırasıyla girerdi
        beklenen = round((mart * 50 + nisan * 50) / 100, 2)
        sina("üç aylık pencere TAKVİM ayıdır (ihalesiz Şubat pencereyi dörde yaymaz)",
             wa["3 Aylık Ağırlıklı Ortalama Vade"].iloc[-1] == beklenen,
             f'{wa["3 Aylık Ağırlıklı Ortalama Vade"].iloc[-1]} ≠ {beklenen}')
        sina("aylık ortalama gün/365 ile", wa["Ağırlıklı Ortalama Vade (Yıl)"].iloc[0] == round(ocak, 2),
             f'{wa["Ağırlıklı Ortalama Vade (Yıl)"].iloc[0]} ≠ {round(ocak, 2)}')

    # yapı: tek tanım, çağrı yerlerinde kullanılıyor
    sina("ayrıştırıcı vadeyi vade_yil'den yazar", "vade_yil(" in _kaynak(hat.TreasuryAuctionScraper._extract_auction_details))
    sina("birikim yazılmadan önce vade_normalize'dan geçer",
         _kaynak(hat.TreasuryAuctionScraper.scrape_all_auctions).count("vade_normalize(") >= 3)
    sina("canlı tahminin hedefi takvimin gün sayısından (backtest'le aynı kural)",
         "plan_vade_yil(" in _kaynak(hat.TreasuryAuctionScraper._forecast_one_issuance))
    gy = (BURASI / "grafik_yenile.py").read_text(encoding="utf-8")
    sina("hafif kip vade tablosunu ihale verisinden KURAR (okumaz)",
         "calculate_weighted_average_maturity" in gy and "WADE_CSV, index=False" in gy.replace("KOK / WADE_CSV", "WADE_CSV"))
    vp = (BURASI / "vade_proj.py").read_text(encoding="utf-8")
    sina("karşı olgunun hedefi de gün sayısından", 'ty = _vade_yil(r["Vade Terimi"])' in vp)


# ── 9. ayrıştırıcı — gerçek duyuru metinleriyle ─────────────────────────────
_BLOK_TR = """TRT010328T12 Ortalama Yıllık Basit : 13,93 13,62
Senet Tanımı :TLREF'e Endeksli Devlet Tahvili Ortalama Yıllık Bileşik : 14,67 14,33
İhraç Tipi :Yeniden İhraç (2. ihraç ) En Düşük Yıllık Bileşik : 13,37 13,37
İhale Tarihi :10.04.2023 En Yüksek Yıllık Bileşik : 17,47 14,93
İhraç (Valör ) Tarihi :12.04.2023
Vade Tarihi :01.03.2028 Fiyat (TL) Teklif Gerçekleşme
Ortalama Fiyat : 90,773 91,782
ROT 1İhale En Yüksek Fiyat : 94,739 94,739
Toplam Katılımcı Sayısı : 10 14 En Düşük Fiyat : 83,000 90,000
Miktar (Net, Milyon TL) Teklif (a) Gerçekleşme (b) b/a (%)
ROT :                   8.925                          5.400                 60,5
   Kamu Kurumları :                           -                                  -                    -
   Piyasa Yapıcılar :                  8.925                         5.400                60,5    Katılımcı
İhale :                 14.754                          9.416                 63,8    1. 32,5%
   Piyasa Yapıcılar :                13.984                         8.914                63,7    2. 18,7%
Toplam :                 23.679                        14.816                 62,6    4. 8,6%
İhraç Sonrası Stok :                 31.809"""

_BLOK_EN = """TRT090621T18 Ortalama Yıllık Basit : 12.22 12.11
Senet Tanımı :Kuponsuz Devlet Tahvili Ortalama Yıllık Bileşik : 12.10 11.99
İhraç Tipi :Yeniden İhraç (2. ihraç) En Düşük Yıllık Bileşik : 11.85 11.85
İhale Tarihi :06/04/2020 En Yüksek Yıllık Bileşik : 12.91 12.06
İhraç (Valör) Tarihi :08/04/2020
Vade Tarihi :09/06/2021 Fiyat (TL) Teklif Gerçekleşme
Ortalama Fiyat : 87.460 87.561
ROT 1İhale En Yüksek Fiyat : 87.690 87.690
Toplam Katılımcı Sayısı : 9 12 En Düşük Fiyat : 86.720 87.492
Miktar (Net, Milyon TL) Teklif (a) Gerçekleşme (b) b/a (%)
ROT :             5,801                   4,500            77.6
   Kamu Kurumları :                         500                               500               100.0
   Piyasa Yapıcılar :                     5,301                            4,000                  75.5    Katılımcı
İhale :             5,598                   3,102            55.4    1. 21.0%
Toplam :           11,399                   7,602            66.7    4. 13.8%
İhraç Sonrası Stok :           12,493"""


def bolum_ayristirici() -> None:
    print("\n▶ Ayrıştırıcı — gerçek duyuru metinleriyle")
    S = hat.TreasuryAuctionScraper.__new__(hat.TreasuryAuctionScraper)
    S.fields = ['ISIN', 'Senet Tanımı', 'İhale Tarihi', 'Valör Tarihi', 'İtfa Tarihi', 'Vade (Yıl)']
    tr, h = _dene(lambda: S._parse_auction_data(_BLOK_TR)[0])
    sina("Türkçe blok ayrıştırılıyor", tr is not None, h)
    if tr is not None:
        sina("'İhraç (Valör ) Tarihi' — boşluklu etiket okunur", tr.get("Valör Tarihi") == "12.04.2023",
             repr(tr.get("Valör Tarihi")))
        sina("vadesi dolu: 1785 gün", tr.get("Vade (Yıl)") == round(1785 / 365, 4), repr(tr.get("Vade (Yıl)")))
        sina("Türkçe yol DEĞİŞMEDİ: tutar 23679/14816, fiyat 91.782, ROT 5400",
             (tr.get("Toplam(Teklif)"), tr.get("Toplam(Gerçekleşme)"), tr.get("Ortalama Fiyat(Gerçekleşme)"),
              tr.get("ROT Toplam(Gerçekleşme)")) == ("23679", "14816", "91.782", "5400"), repr(tr))
    en, h = _dene(lambda: S._parse_auction_data(_BLOK_EN)[0])
    sina("İngilizce blok ayrıştırılıyor", en is not None, h)
    if en is not None:
        sina("'06/04/2020' tarihleri okunur ve GG.AA.YYYY'ye çevrilir",
             (en.get("İhale Tarihi"), en.get("Valör Tarihi"), en.get("İtfa Tarihi"))
             == ("06.04.2020", "08.04.2020", "09.06.2021"), repr(en))
        sina("İngilizce sayı: tutar 7602 (7,602 değil), fiyat 87.561 (87561 değil)",
             (en.get("Toplam(Gerçekleşme)"), en.get("Ortalama Fiyat(Gerçekleşme)"), en.get("ROT Kamu(Teklif)"))
             == ("7602", "87.561", "500"), repr(en))
        sina("İngilizce faiz: 11.99", en.get("Ortalama Yıllık Bileşik(Gerçekleşme)") == "11.99")
    eksi_en = "TRT280628T18 Ortalama Yıllık Basit : -0.25 -0.30\nSenet Tanımı :TÜFE'ye Endeksli"
    tire_tr = "TRT1 Ortalama Yıllık Basit : - 13,62\nOrtalama Fiyat : 90,773 91,782"
    sina("eksi reel faizli İngilizce blok '.' · Teklif '-' olan Türkçe blok ','",
         (hat.TreasuryAuctionScraper._sayi_bicimi(eksi_en), hat.TreasuryAuctionScraper._sayi_bicimi(tire_tr))
         == (".", ","))
    v, h5 = _dene(lambda: (hat.plan_vade_yil("2Yıl /707 gün"), hat.plan_vade_yil("5 yıl / 1.785 Gün")))
    sina("plan vadesi büyük/küçük harfe duyarsız ve binlik noktalı gün", v == (round(707 / 365, 4), round(1785 / 365, 4)), h5 or repr(v))
    sina("biçim faiz satırından: Türkçe ',' · İngilizce '.' · faizsiz blok Türkçe",
         (hat.TreasuryAuctionScraper._sayi_bicimi(_BLOK_TR), hat.TreasuryAuctionScraper._sayi_bicimi(_BLOK_EN),
          hat.TreasuryAuctionScraper._sayi_bicimi("Toplam : 1.234 1.000")) == (",", ".", ","))


# ── 10. işlendi defteri ─────────────────────────────────────────────────────
def bolum_defter() -> None:
    print("\n▶ İşlendi defteri — iş bitmeden yazılmaz")
    S = hat.TreasuryAuctionScraper.__new__(hat.TreasuryAuctionScraper)
    S.fields = ['ISIN', 'Senet Tanımı', 'İhale Tarihi', 'Valör Tarihi', 'İtfa Tarihi', 'Vade (Yıl)']
    cevap = {"u_iyi": [{"ISIN": "TRT1", "İhale Tarihi": "10.04.2023"}],
             "u_bos": [],                                              # indirilemedi
             "u_tarihsiz": [{"ISIN": "TRT2", "İhale Tarihi": ""}]}      # '06/04/2020' vakası
    S.extract_data_from_pdf_sync = lambda url: cevap[url]
    eski = hat.USE_ASYNC
    try:
        hat.USE_ASYNC = False
        _, h = _dene(lambda: S._process_pdf_batch_parallel(list(cevap)))
    finally:
        hat.USE_ASYNC = eski
    g = getattr(S, "pdf_gecerli", {})
    sina("PDF başına geçerli satır sayılır: iyi 1 · indirilemeyen 0 · tarihsiz 0",
         g == {"u_iyi": 1, "u_bos": 0, "u_tarihsiz": 0}, h or repr(g))
    src = _kaynak(hat.TreasuryAuctionScraper.scrape_all_auctions)
    i_isle = src.find("self._process_pdf_batch_parallel(")
    i_ekle = src.find("self.processed_urls.add(announcement_url)")
    sina("duyuru defteri PDF işlendikten SONRA yazılır",
         0 <= i_isle < i_ekle, f"işleme {i_isle} · defter {i_ekle}")
    sina("defter geçerli satır şartına bağlı",
         "self.pdf_gecerli.get(pdf_url, 0) > 0" in src[i_isle:i_ekle])
    # async yol — üretimin kullandığı yol (USE_ASYNC=True)
    S2 = hat.TreasuryAuctionScraper.__new__(hat.TreasuryAuctionScraper)
    S2.fields = S.fields
    eski_ind, eski_parse = hat.download_multiple_pdfs_async, S2._parse_pdf_content

    async def _sahte_indir(urls, concurrency=8):
        return {u: u.encode() for u in urls if u != "u_bos"}     # indirilemeyen sözlükte YOK
    S2._parse_pdf_content = lambda icerik: cevap[icerik.decode()]
    try:
        hat.download_multiple_pdfs_async = _sahte_indir
        hat.USE_ASYNC = True
        _, h2 = _dene(lambda: S2._process_pdf_batch_parallel(list(cevap)))
    finally:
        hat.download_multiple_pdfs_async = eski_ind
        hat.USE_ASYNC = eski
    g2 = getattr(S2, "pdf_gecerli", {})
    sina("async yol da sayar: iyi 1 · indirilemeyen 0 · tarihsiz 0",
         g2 == {"u_iyi": 1, "u_bos": 0, "u_tarihsiz": 0}, h2 or repr(g2))
    ana = _kaynak(hat.main)
    i_csv = ana.find("df.to_csv(CSV_OUTPUT")
    i_def = ana.find("scraper._save_url_cache()")
    sina("defter CSV yazıldıktan SONRA kalıcılaşır", 0 <= i_csv < i_def, f"csv {i_csv} · defter {i_def}")
    sina("scrape_all_auctions defteri kendisi yazmaz", "self._save_url_cache()" not in src)
    sina("main() istisnada sıfırla çıkmaz", "raise SystemExit(1)" in ana)

    # birikim kaynağı: önce izlenen CSV
    with tempfile.TemporaryDirectory() as td:
        pd.DataFrame({"ISIN": ["A", "B"], "İhale Tarihi": ["14.09.2026", "15.09.2026"]}).to_csv(
            os.path.join(td, hat.CSV_OUTPUT), index=False, encoding="utf-8-sig")
        try:
            pd.DataFrame({"ISIN": ["A"], "İhale Tarihi": ["18.08.2026"]}).to_excel(
                os.path.join(td, hat.EXCEL_OUTPUT), sheet_name="İhale Verileri", index=False)
            excel_var = True
        except Exception:  # noqa: BLE001 — openpyxl yoksa kaynak sırası metinden sorulur
            excel_var = False
        if excel_var:
            c, h3 = _dene(lambda: hat.birikmis_son_ihale(td))
            sina("çıpa, eski Excel dururken İZLENEN CSV'den", c == pd.Timestamp("2026-09-15"), h3 or repr(c))
    sc = _kaynak(hat.TreasuryAuctionScraper.scrape_all_auctions)
    sina("birikim önce CSV'den okunur (Excel yalnız yedek)",
         0 <= sc.find("(CSV_OUTPUT, lambda") < sc.find("(EXCEL_OUTPUT, lambda"))

    # iki vade tüketicisi tek toplam fonksiyonundan okur
    sina("vade tablosu aylik_vade_toplamlari'dan kurulur",
         "aylik_vade_toplamlari(" in _kaynak(hat.TreasuryAuctionScraper.calculate_weighted_average_maturity))
    vp = (BURASI / "vade_proj.py").read_text(encoding="utf-8")
    sina("vade projeksiyonu da aynı fonksiyondan okur (ikinci tanım yok)",
         "aylik_vade_toplamlari(hist)" in vp and "hazine_vade_analizi.csv" not in vp)
    sina("gerçekleşen ile planın çakıştığı ay TOPLANIR (plan gerçekleşeni ezmez)",
         "gecmis_hacim.get(a, 0.0) + plan_hacim.get(a, 0.0)" in vp and "yuv_gercek[gecmis_aylar[-1]]" in vp)
    import tablo_uret
    tt, h6 = _dene(lambda: tablo_uret._tarih(pd.Series(["2023-04-01", "10.04.2023", "7.07.2026"]))
                   .dt.strftime("%d.%m.%Y").tolist())
    sina("tablo tarihleri biçimiyle okunur: ISO 2023-04-01 Nisan'dır, Ocak değil",
         tt == ["01.04.2023", "10.04.2023", "07.07.2026"], h6 or repr(tt))
    tu = (BURASI / "tablo_uret.py").read_text(encoding="utf-8")
    sina("tablo vadeyi iki ondalıkla gösterir (saklama dört)", '"Vade (Yıl)"].round(2)' in tu.replace(
        'pd.to_numeric(d["Vade (Yıl)"], errors="coerce").round(2)', '"Vade (Yıl)"].round(2)'))

    # itfa ↔ ISIN
    it = pd.DataFrame({
        "ISIN": ["TRT050527T17"] * 3 + ["TRT240724T15", "TRT010199T99"],
        "İhale Tarihi": ["24.08.2020", "11.05.2020", "14.09.2020", "24.08.2020", "01.01.2020"],
        "Valör Tarihi": ["26.08.2020", "13.05.2020", "16.09.2020", "26.08.2020", "03.01.2020"],
        "İtfa Tarihi": ["24.07.2024", "05.05.2027", "05.05.2027", "24.07.2024", "05.05.2030"],
        "Toplam(Gerçekleşme)": [2357.0, 1.0, 1.0, 3672.0, 1.0]})
    n, h4 = _dene(lambda: hat.vade_normalize(it))
    sina("itfa ISIN'le çelişir ve aynı tahvilin ihaleleri ISIN'le tutarsa düzeltilir",
         n is not None and n.at[0, "İtfa Tarihi"] == "05.05.2027", h4 or (repr(list(n["İtfa Tarihi"])) if n is not None else ""))
    sina("kaynak teyidi yoksa (tek ihale) dokunulmaz",
         n is not None and n.at[4, "İtfa Tarihi"] == "05.05.2030")
    sina("tutan satırlara dokunulmaz", n is not None and n.at[3, "İtfa Tarihi"] == "24.07.2024")


def main() -> int:
    print("Hazine ihraç hattı — duman sınaması (ağa çıkmaz)")
    bolum_cipa()
    bolum_yenilik()
    bolum_takvim_kapisi()
    bolum_sozlesme()
    bolum_saat()
    bolum_uclar()
    bolum_okur_dili()
    bolum_vade()
    bolum_ayristirici()
    bolum_defter()
    print(f"\n{GECTI} geçti · {DUSTU} düştü")
    if _KUSUR:
        print("Düşenler: " + " | ".join(_KUSUR))
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
