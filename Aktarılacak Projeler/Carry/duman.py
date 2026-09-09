# -*- coding: utf-8 -*-
"""TL taşıma (carry) hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur; düşerse hat
koşmaz. Sınamada duran her madde bir gün gerçekten yanlış yayımlanmış bir
sayı ya da yanlış bir tarihtir. Çerçeve SENTETİKTİR: depodaki CSV'lere ve
hattın o günkü ozet.json'una bakılmaz — gerçek seriyle sınamak ölçütü
verinin bugünkü hâline bağlar ve yarın veri değiştiğinde sınama sebepsiz
düşer; duman adımlardan ÖNCE koştuğu için dosyaya bağlı bir ölçüt hattı
kendi ilk koşusundan bile alıkoyardı.

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR (09.09.2026'da ölçüldü)
--------------------------------------------------------------------------
 1. ANAHTAR BAŞINA SAAT — carry_2y_tlref, n2y, f_1y1y, tlref_b, getiri_1y ve
    zirveden 07.09 satırından okunuyor, kendi saatleri yazılmadığı için sayfa
    ipucu hattın saatini (08.09, kurun günü) gösteriyordu. Kural: her sayısal
    anahtar `<ad>_tarih` taşır; istisna yalnız tarihsel ölçüler (zirve, dip,
    en derin çöküş…), onlar "ne zaman yaşandı" der, tazelik saati taşımaz.
 2. SAYFANIN ÇAĞIRDIĞI ANAHTAR — MDX'in `<Deger>` ile adıyla çağırdığı her
    anahtar özette var ve (sayısalsa) kendi saatiyle. Sayfa yeni bir anahtar
    çağırırsa burası onu adıyla söyler.
 3. OKUR TARİHİ — çöküş dönemleri ve en kötü aylar ISO (yıl-ay-gün)
    yazılıyordu; okura giden dosyada biçim sözleşmesi GG.AA.YYYY'dir
    (ortak/bicim = lib/bicim). Sıralama TARİHLE yapılır, metinle değil: ISO
    metni sözlük sırasında tesadüfen kronolojikti, GG.AA.YYYY değildir.
 4. POLİTİKA FAİZİ: GÖZLEM ≠ İLAN — ileri taşınmış (ffill) değer kur gününe
    etiketleniyordu; EVDS satırı bir gün geride ve Fonlama sayfası aynı seriyi
    o günle yazıyor. `politika` gözlemin günü, `politika_ilan` kur gününe
    taşınmış yürürlükteki faiz. PPK GÜNÜ RİSKİ: karar günü EVDS satırı henüz
    yazılmadıysa ilan ESKİ oranı taşır ve makas karar büyüklüğü kadar yanlış
    çıkar; hat bunu düzeltemez (karar takvimi okumuyor). Tek sigorta iki
    saatin AYRIŞMASI ve bunun görünür olması — burada o sınanıyor.
 5. ÇİZİM EKSENİ — özet okura yazılınca dikey çizgi tarihi Plotly'ye ISO
    çevrilerek verilmeli; okur yazımı doğrudan verilirse çizgi kategori
    eksenine düşer ve şekil sessizce bozulur.
 6. ŞEKİL DAMGASI BAĞLAYICI BACAK — iki bacaklı figürde damga EN ESKİ bacak;
    min() yapısal, hangi bacağın geride olduğuna bakmaz.
 7. ÖLÇÜLEMEYEN BOŞ — bütünüyle boş bir kolonun anahtarı "—" yazılır,
    atlanmaz (sayfa anahtarı adıyla çağırıyor; eksik anahtar yayın kapısında
    ENGEL, JSON null ise donmuş statik yedek).
 8. KONVANSİYON — basit gecelik faiz bileşiğe (1+r/365)^365−1 ile çevrilir;
    sayfanın ana dersi bu dönüşüm (26.08.2026: 2y taşıma bileşikle −8,47,
    basitle +0,61).
 9. YAPISAL KİLİT — `yukle` gözlemi ilan'dan ayıran `ilan_tasi`den geçer;
    `hesapla` çerçeveyi argüman alır (bu sınamanın kapısı); kaynakta ISO
    biçim kalıbı yok; kapıdan sonra tanım yok.

Koşum:  python3 duman.py
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))

import hesap                                                        # noqa: E402

SONUC: list[tuple[str, str]] = []
GUN = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def sina(ad, fn):
    try:
        fn()
        SONUC.append(("✓", ad))
    except Exception as e:                                     # noqa: BLE001
        SONUC.append(("✗", f"{ad} — {type(e).__name__}: {e}"))


# ===========================================================================
#  SENTETİK ÇERÇEVE
# ===========================================================================
KUR_SON = "2026-09-08"


def _cerceve(kur_son=KUR_SON, tlref_son="2026-09-07", dibs_son="2026-09-07",
             politika_son="2026-09-07", bas="2022-01-03",
             politika=37.0, karar=None, soklar=((("2023-06-01", 1.010)),
                                                (("2024-11-01", 1.018)))):
    """Kur gününe hizalı iş günü çerçevesi. Bacakların bittiği günler ayrı
    ayrı seçilir: hat tam bu ayrışmayı ölçüyor.

    Kur düzgün aşınır (+%0,07/gün ≈ %19/yıl); iki KUR ŞOKU (21 iş günü, günde
    %1,0 ve %1,8) endekste ölçülebilir çöküş ve en kötü ay üretir. Şok günleri
    bilerek seçildi: okur yazımında "..06.2023" ile "..11.2024" sözlük sırası
    kronolojik sıranın TERSİDİR — metinle sıralayan bir kod burada yakalanır.
    `karar=(gün, oran)` verilirse politika faizi o günden itibaren yeni orandır
    (EVDS satırı yazılmışsa); politika_son'dan sonrası boştur.
    """
    idx = pd.bdate_range(bas, kur_son)
    idx.name = "tarih"
    n = len(idx)
    buyume = np.full(n, 1.0007)
    for gun_, g in soklar:
        i = idx.searchsorted(pd.Timestamp(gun_))
        buyume[i:i + 21] = g
    d = pd.DataFrame(index=idx)
    d["usdtry"] = 13.0 * np.cumprod(buyume)
    d["tlref"] = 36.9
    d["aofm"] = 37.0
    d["politika"] = politika
    if karar is not None:
        d.loc[d.index >= pd.Timestamp(karar[0]), "politika"] = karar[1]
    d["koridor_alt"], d["koridor_ust"] = 35.5, 40.0
    d["n2y"], d["f_1y1y"] = 40.0, 41.0
    d["carry_2y_tlref"], d["carry_2y_tlref_basit"] = -4.6, 3.1
    d["carry_2y_politika"], d["carry_3a_tlref"] = -4.6, -7.5
    d.loc[d.index > pd.Timestamp(tlref_son), ["tlref", "aofm"]] = np.nan
    d.loc[d.index > pd.Timestamp(politika_son),
          ["politika", "koridor_alt", "koridor_ust"]] = np.nan
    d.loc[d.index > pd.Timestamp(dibs_son),
          ["carry_2y_tlref", "carry_2y_tlref_basit", "carry_2y_politika",
           "carry_3a_tlref"]] = np.nan
    return hesap.ilan_tasi(d)


def _ozet(**k) -> dict:
    return hesap.hesapla(_cerceve(**k))[2]


def _sayisal(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ===========================================================================
#  1 · ANAHTAR BAŞINA SAAT
# ===========================================================================
def _anahtar_basina_saat():
    o = _ozet()
    assert o["_tarih"] == "08.09.2026", o["_tarih"]
    # DİBS taşıma kolonu kur gününden bir gün geride: saat o satırın günü.
    for k in ("carry_2y_tlref", "carry_2y_tlref_basit", "carry_2y_politika",
              "carry_3a_tlref"):
        assert o[f"{k}_tarih"] == "07.09.2026", (k, o.get(f"{k}_tarih"))
    # TLREF'e bağlı her anahtar TLREF'in günü; kur gününe gelen bacak kur günü.
    for k in ("tlref", "tlref_b", "endeks", "getiri_1y", "zirveden", "sharpe_3y",
              "makas_tlref_b_d3a"):
        assert o[f"{k}_tarih"] == "07.09.2026", (k, o.get(f"{k}_tarih"))
    for k in ("kur", "d1a", "d3a", "n2y", "f_1y1y", "makas_politika_d1a"):
        assert o[f"{k}_tarih"] == "08.09.2026", (k, o.get(f"{k}_tarih"))
    # GENEL KURAL, listeden değil sözleşmeden: her sayısal anahtar kendi
    # saatini taşır; tarihsel ölçüler hariç.
    saatsiz = [k for k, v in o.items()
               if _sayisal(v) and not k.endswith("_tarih") and not hesap.tarihsel_mi(k)
               and not GUN.match(str(o.get(f"{k}_tarih", "")))]
    assert not saatsiz, f"saati yazılmamış sayısal anahtar: {saatsiz}"
    # Tarihsel ölçü saat TAŞIMAZ: "en derin çöküş ne zaman" bir tazelik saati
    # değildir; Deger.astro TARIHSEL kalıbıyla aynı ayrım.
    assert hesap.tarihsel_mi("en_derin_cokus") and hesap.tarihsel_mi("cokus_sayisi")
    assert not hesap.tarihsel_mi("carry_2y_tlref_basit") and not hesap.tarihsel_mi("n2y")


# ===========================================================================
#  2 · SAYFANIN ÇAĞIRDIĞI ANAHTAR
# ===========================================================================
def _sayfa_anahtarlari():
    mdx = KOK / "site" / "src" / "content" / "projeler" / "tl-tasima.mdx"
    if not mdx.exists():
        print("  (sayfa dosyası yok — sayfa anahtarı ölçütü atlandı)")
        return
    kul = set(re.findall(r'<Deger\s+proje="tl-tasima"\s+anahtar="([^"]+)"',
                         mdx.read_text(encoding="utf-8")))
    assert kul, "sayfa hiçbir anahtar çağırmıyor — sınamanın hedefi değişmiş"
    o = _ozet()
    eksik = sorted(k for k in kul if k not in o)
    assert not eksik, f"sayfanın çağırdığı ama özette olmayan anahtar: {eksik}"
    saatsiz = sorted(k for k in kul if _sayisal(o[k]) and not k.endswith("_tarih")
                     and not hesap.tarihsel_mi(k) and f"{k}_tarih" not in o)
    assert not saatsiz, f"sayfada basılan ama saati olmayan anahtar: {saatsiz}"
    # Şekillerin açık damgaları da özette ve çözülüyor.
    for k in re.findall(r'tarihAnahtari="([^"]+)"', mdx.read_text(encoding="utf-8")):
        assert GUN.match(str(o.get(k, ""))), (k, o.get(k))


# ===========================================================================
#  3 · OKUR TARİHİ
# ===========================================================================
def _okur_tarihi():
    o = _ozet()
    metin = json.dumps(o, ensure_ascii=False)
    assert not ISO.search(metin), f"özette ISO tarih: {ISO.search(metin).group(0)}"
    for k, v in o.items():
        if k.endswith("_tarih") or k == "endeks_bas":
            assert GUN.match(v), (k, v)
    assert o["cokusler"], "sentetik şok çöküş üretmedi — çerçeve ölçütü sınayamıyor"
    for c in o["cokusler"]:
        for k in ("bas", "dip_tarih"):
            assert GUN.match(c[k]), (k, c[k])
        assert c["bitis"] == "" or GUN.match(c["bitis"]), c["bitis"]
    assert GUN.match(o["en_derin_cokus_tarih"])
    # Kronolojik sıra, TARİHLE. Çerçeve ayırt edici olmalı: metin sırası ile
    # tarih sırası farklı düşmezse bu ölçüt hiçbir şeyi ölçmez.
    kotu = [x["tarih"] for x in o["kotu_aylar"]]
    assert len(kotu) >= 2, kotu
    zaman = [hesap.tarihe_cevir(t) for t in kotu]
    assert zaman == sorted(zaman), f"en kötü aylar kronolojik değil: {kotu}"
    assert sorted(kotu) != kotu, f"çerçeve ayırt edici değil (metin sırası da kronolojik): {kotu}"


# ===========================================================================
#  4 · POLİTİKA FAİZİ: GÖZLEM ≠ İLAN
# ===========================================================================
def _politika_gozlem_ilan():
    # (a) kur günü politika satırı boş: gözlem bir gün geride, ilan kur günü.
    o = _ozet()
    assert o["politika_tarih"] == "07.09.2026", o["politika_tarih"]
    assert o["politika_ilan_tarih"] == "08.09.2026", o["politika_ilan_tarih"]
    assert o["politika"] == o["politika_ilan"] == 37.0
    assert o["makas_politika_d1a_tarih"] == "08.09.2026"
    # (b) ham gözlem kolonu TAŞINMAZ: ilan_tasi yalnız politika_ilan'ı doldurur.
    d = _cerceve()
    assert d["politika"].isna().iloc[-1] and not d["politika_ilan"].isna().iloc[-1]
    assert d["politika_ilan"].isna().sum() == 0
    # (c) karar günü EVDS'te yazılmışsa ilan yeni oranı taşır ve makas onunla kurulur.
    o2 = _ozet(karar=("2026-09-04", 35.0))
    assert o2["politika"] == 35.0 and o2["politika_ilan"] == 35.0
    d2 = _cerceve(karar=("2026-09-04", 35.0))
    _, e2, oz2 = hesap.hesapla(d2)
    assert abs(oz2["makas_politika_d1a"] - (35.0 - oz2["d1a"])) < 0.051
    # (d) PPK GÜNÜ RİSKİ: karar 04.09'da ama EVDS satırı 03.09'da bitiyor →
    # ilan ESKİ oranı taşır; hat bunu bilemez. Sigorta: iki saat ayrışır ve
    # ayrışma görünür (gözlem 03.09, ilan 08.09).
    o3 = _ozet(politika_son="2026-09-03", karar=("2026-09-04", 35.0))
    assert o3["politika"] == 37.0 and o3["politika_ilan"] == 37.0, "gözlem gelmeden yeni oran uydurulmuş"
    assert o3["politika_tarih"] == "03.09.2026" and o3["politika_ilan_tarih"] == "08.09.2026"
    g, i = hesap.tarihe_cevir(o3["politika_tarih"]), hesap.tarihe_cevir(o3["politika_ilan_tarih"])
    assert (i - g).days == 5, "taşıma iki saatin farkında görünmüyor"


# ===========================================================================
#  5 · ÇİZİM EKSENİ
# ===========================================================================
def _cizim_ekseni():
    import grafik
    assert grafik.eksen_tarihi("07.04.2020") == "2020-04-07"
    assert grafik.eksen_tarihi("21.12.2021") == "2021-12-21"
    try:
        grafik.eksen_tarihi("Aralık 2021")
    except ValueError:
        pass
    else:
        raise AssertionError("çözülemeyen tarih sessizce geçti")
    src = (BURASI / "grafik.py").read_text(encoding="utf-8")
    assert 'add_vline(x=eksen_tarihi(x["tarih"])' in src, \
        "dikey çizgi okur yazımıyla veriliyor — kategori eksenine düşer"


# ===========================================================================
#  6 · ŞEKİL DAMGASI BAĞLAYICI BACAK
# ===========================================================================
def _sekil_damgasi():
    # TLREF geride, DİBS taze: Şekil 01 ve 03 TLREF'e, Şekil 04 DİBS'e düşer.
    o = _ozet(tlref_son="2026-09-04", dibs_son="2026-09-07")
    assert o["makas_tarih"] == "04.09.2026", o["makas_tarih"]
    assert o["nakit_tahvil_tarih"] == "04.09.2026", o["nakit_tahvil_tarih"]
    assert o["carry_tarih"] == "07.09.2026", o["carry_tarih"]
    # DİBS geride, TLREF taze: Şekil 03 ve 04 DİBS'e düşer, Şekil 01 TLREF'te.
    o = _ozet(tlref_son="2026-09-07", dibs_son="2026-09-03")
    assert o["nakit_tahvil_tarih"] == "03.09.2026", o["nakit_tahvil_tarih"]
    assert o["carry_tarih"] == "03.09.2026", o["carry_tarih"]
    assert o["makas_tarih"] == "07.09.2026", o["makas_tarih"]
    assert o["carry_2y_tlref_tarih"] == "03.09.2026" and o["endeks_tarih"] == "07.09.2026"


# ===========================================================================
#  7 · ÖLÇÜLEMEYEN BOŞ
# ===========================================================================
def _olculemeyen_bos():
    d = _cerceve()
    d["carry_3a_tlref"] = np.nan
    o = hesap.hesapla(d)[2]
    assert o["carry_3a_tlref"] == hesap.OLCULEMEDI, o["carry_3a_tlref"]
    assert "carry_3a_tlref_tarih" not in o, "ölçülmemiş değere saat yazılmış"
    assert "carry_2y_tlref_tarih" in o


# ===========================================================================
#  8 · KONVANSİYON
# ===========================================================================
def _konvansiyon():
    b = hesap.gecelik_bilesik(pd.Series([36.9, 39.86]))
    assert abs(b.iloc[0] - 44.61) < 0.01 and abs(b.iloc[1] - 48.94) < 0.01, b.tolist()
    o = _ozet()
    assert abs(o["tlref_b"] - 44.61) < 0.01


# ===========================================================================
#  9 · YAPISAL KİLİT
# ===========================================================================
def _yapisal():
    src = (BURASI / "hesap.py").read_text(encoding="utf-8")
    agac = ast.parse(src)
    yukle = next(f for f in agac.body if isinstance(f, ast.FunctionDef) and f.name == "yukle")
    assert "ilan_tasi(" in ast.unparse(yukle), "yukle gözlemi ilandan ayıran ilan_tasi'den geçmiyor"
    assert "ffill" not in ast.unparse(yukle), "yukle içinde ffill: ham gözlem kolonu kaybolur"
    hesapla = next(f for f in agac.body if isinstance(f, ast.FunctionDef) and f.name == "hesapla")
    assert hesapla.args.args and hesapla.args.args[0].arg == "d", \
        "hesapla çerçeveyi argüman almıyor — duman sınaması kapısız kalır"
    assert "%Y-%m-%d" not in src, "kaynakta ISO biçim kalıbı: okura giden dosyaya sızar"
    kapi = None
    for g in agac.body:
        if isinstance(g, ast.If) and "__main__" in ast.dump(g.test):
            kapi = g.lineno
    assert kapi is not None
    sonra = [g.name for g in agac.body
             if isinstance(g, (ast.FunctionDef, ast.ClassDef)) and g.lineno > kapi]
    assert not sonra, f"kapıdan sonra tanım: {sonra}"


sina("anahtar başına saat: her sayısal anahtar kendi gözlem gününü taşır", _anahtar_basina_saat)
sina("sayfanın çağırdığı her anahtar özette ve saatiyle", _sayfa_anahtarlari)
sina("okur tarihi GG.AA.YYYY; ISO yok; en kötü aylar tarihle sıralı", _okur_tarihi)
sina("politika faizi: gözlem günü ayrı, ilan kur günü; PPK riski görünür", _politika_gozlem_ilan)
sina("dikey çizgi tarihi Plotly'ye ISO çevrilerek verilir", _cizim_ekseni)
sina("şekil damgası bağlayıcı (en eski) bacak, min() yapısal", _sekil_damgasi)
sina("bütünüyle boş kolon '—' yazılır, atlanmaz, saatsiz", _olculemeyen_bos)
sina("basit gecelik → bileşik konvansiyon", _konvansiyon)
sina("yapısal kilit: ilan_tasi, hesapla(d), ISO kalıbı yok, kapı sonrası tanım yok", _yapisal)

if __name__ == "__main__":
    for im, ad in SONUC:
        print(f"  {im} {ad}")
    dusen = [a for im, a in SONUC if im == "✗"]
    print(f"\n{len(SONUC) - len(dusen)}/{len(SONUC)} geçti")
    raise SystemExit(1 if dusen else 0)
