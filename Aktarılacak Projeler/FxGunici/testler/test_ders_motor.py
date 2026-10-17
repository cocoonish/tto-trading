# -*- coding: utf-8 -*-
"""Ders motoru: biçim sözleşmesi, yol, koşul, iddia, sabit ve blok davranışı."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ders_motor as dm  # noqa: E402

# Künye pariteleri tanımlar (ders_motor.parite_kur): motor elle tutulan bir parite listesi taşımaz.
O = {"kunye": {"bitis": "2026-10-15", "ciftler": ["EURUSD"], "nokta": {"EURUSD": 1e-5}, "pip": {"EURUSD": 1e-4}},
     "birim": {"orb": {"aile": "orb", "varsayilan": {"tf": 15},
                       "cift": {"EURUSD": {"varsayilan": {"oos": {"beklenti_r": -0.0412, "n": 1431, "isabet": 0.2798,
                                                                  "ga_alt": -0.091, "bos": None},
                                                          "maliyet": {"0.5": {"oos": {"beklenti_r": -0.04}}},
                                                          "hukum": "calismiyor"},
                                           "ornek": [{"gun": "2026-10-14", "islem": {"giris_f": 111986.0}}]}},
                       "havuz": {"varsayilan": {}}}}}


def _u():
    return dm.Uretim(O, {"orb": {"izgara": {"tf": [5, 15]}}})


def test_bicim_sozlesmesi():
    assert dm.bicimle(-0.0412, "r") == "−0,04"
    assert dm.bicimle(0.0412, "r") == "+0,04"
    assert dm.bicimle(-0.001, "r") == "0,00"            # sıfıra yuvarlanan işaretsiz
    assert dm.bicimle(0.2798, "yz1") == "%28,0"
    assert dm.bicimle(-0.031, "yz1") == "−%3,1"           # işaret yüzdeden önce
    assert dm.bicimle(1431, "n") == "1.431"
    assert dm.bicimle("2026-10-14", "tarih_uzun") == "14 Ekim 2026"
    with pytest.raises(dm.SablonHatasi):
        dm.bicimle(None, "r")                            # ölçülemeyen değer sessizce basılmaz
    assert dm.bicimle(None, "r?") == "—"


def test_yol_ve_tirnakli_anahtar():
    u = _u()
    ctx = u.birim_ctx("orb")
    assert dm.yol_coz('E.varsayilan.maliyet."0.5".oos.beklenti_r', ctx) == -0.04
    assert dm.yol_coz("E.ornek.[0].gun", ctx) == "2026-10-14"
    assert dm.yol_coz("E.yok.boyle", ctx) is None
    with pytest.raises(dm.SablonHatasi):
        dm.yol_coz("Z.x", ctx)


def test_kosul_ve_iddia():
    u = _u()
    ctx = u.birim_ctx("orb")
    assert dm.kosul('E.varsayilan.hukum == "calismiyor" and E.varsayilan.oos.n > 1000', ctx)
    assert dm.kosul('E.varsayilan.oos.beklenti_r > 0 or E.varsayilan.oos.n >= 1431', ctx)
    assert not dm.kosul("not E.varsayilan.oos.n", ctx)
    assert u.isle("A{{? E.varsayilan.oos.ga_alt < 0 }}B", ctx) == "AB"
    with pytest.raises(dm.SablonHatasi, match="İDDİA"):
        u.isle("{{? E.varsayilan.oos.beklenti_r > 0 }}", ctx)
    with pytest.raises(dm.SablonHatasi):            # ölçülemeyenle büyüklük kıyası tanımsız
        dm.kosul("E.varsayilan.oos.bos > 0", ctx)


def test_if_elif_else_ic_ice():
    u = _u()
    ctx = u.birim_ctx("orb")
    s = ('{% if E.varsayilan.hukum == "calisiyor" %}X{% elif E.varsayilan.oos.n > 1000 %}'
         '{% if E.varsayilan.oos.isabet > 0.5 %}Y{% else %}Z{% endif %}{% else %}W{% endif %}')
    assert u.isle(s, ctx) == "Z"
    with pytest.raises(dm.SablonHatasi):
        u.isle("{% if E.varsayilan.oos.n %}açık kaldı", ctx)


def test_sabit_bildirilir_ve_fiyat():
    u = _u()
    ctx = u.birim_ctx("orb")
    assert u.isle('BB({{= "20" }}, {{= "2" }})', ctx) == "BB(20, 2)"
    assert u.sabitler == ["20", "2"]
    assert u.isle("{{ E.ornek.[0].islem.giris_f | fiyat }}", ctx) == "1,11986"
    with pytest.raises(dm.SablonHatasi):
        u.isle("{{ E.varsayilan.oos.n }}", ctx)          # biçimsiz yer tutucu yok


def test_sekil_numarasi_ve_import():
    sablon = "---\ntitle: 'x'\n---\n\n{{! sekil karsilastirma-ozet Özet }}\n{{! sekil veri-makas Makas }}\n"
    m, u = dm.ders_uret(sablon, O, {})
    assert "import GrafikEmbed" in m and m.index("import") > m.index("---\n", 4)
    assert 'no="01"' in m and 'no="02"' in m and u.sekiller == ["karsilastirma-ozet", "veri-makas"]


def _pratik_u(ek_neden: int, ek_cikis_t: int) -> tuple:
    """Hedefte kapanan bir örnek işlem ve onun ek kaymalı yeniden koşusu (çıkış nedeni ve anı parametre)."""
    kunye = {"bitis": "2026-10-15", "ciftler": ["EURUSD"], "nokta": {"EURUSD": 1e-5}, "pip": {"EURUSD": 1e-4},
             "gun_sonu_et": "16:55", "temel_kayma_pip": 0.5, "haber_kayma_pip": 1.0, "haber_pencere_dk": [-2, 15]}
    islem = {"yon": 1, "giris_t": 1760436000, "cikis_t": 1760439600, "giris_f": 111986.0, "stop": 111836.0,
             "cikis_f": 112286.0, "hedef": 112286.0, "neden": 2, "hedef_tur": 1, "hedef_k": 2.0, "r": 2.0,
             "pnl_pip": 30.0, "R_pip": 15.0, "stopsuz": False}
    hedefte = ek_neden in (2, 6)
    ek_cikis = 112316.0 if hedefte else 112100.0
    ek = {"kayma_pip": 1.5, "durum": 0, "giris_f": 111996.0, "stop": 111836.0, "hedef": 112316.0,
          "cikis_f": ek_cikis, "cikis_t": ek_cikis_t, "neden": ek_neden,
          "pnl_pip": (ek_cikis - 111996.0 - 10) / 10 if not hedefte else 32.0, "R_pip": 16.0}
    ek["r"] = ek["pnl_pip"] / ek["R_pip"]
    o = {"kunye": kunye, "birim": {"orb": {"aile": "orb", "varsayilan": {}, "havuz": {"varsayilan": {}},
                                           "cift": {"EURUSD": {"ornek": [{"etiket": "kazanan", "gun": "2025-10-14",
                                                                          "islem": islem, "ek_kayma": ek,
                                                                          "takvim": []}]}}}}}
    u = dm.Uretim(o, {"orb": {"izgara": {}}})
    return u, u.birim_ctx("orb")


def test_pratik_ek_kayma_hedefe_yine_ulasinca_ulasilamadi_yazilmaz():
    # Ek kaymalı koşu da hedefte (30 dakika sonra) kapanırsa: "yine ulaşıldı", "ulaşılamadı" değil.
    u, ctx = _pratik_u(2, 1760441400)
    m = dm.blok_pratik_islem(u, ctx, "orb", "Alıştırma", "kazanan")
    assert "yine ulaşıldı" in m and "ulaşılamadı" not in m
    # Ek kaymalı koşu hedefe değmeden başka bir çıkışla kapanırsa: "ulaşılamadı".
    u, ctx = _pratik_u(3, 1760443200)
    m = dm.blok_pratik_islem(u, ctx, "orb", "Alıştırma", "kazanan")
    assert "ulaşılamadı" in m


def test_pratik_r_gosterilen_sayilardan():
    # "a / b = c" satırında c gösterilen a ve b'den: 30 / 15 = +2,00.
    u, ctx = _pratik_u(2, 1760441400)
    m = dm.blok_pratik_islem(u, ctx, "orb", "Alıştırma", "kazanan")
    assert "30,0 / 15,0 = **+2,00 R**" in m
    assert dm._oran_yaz("22,8", "29,05") == "+0,78"      # kayıttaki 0,785'in ikinci yuvarlaması 0,79 yazardı


def test_mevsim_kovalari_tek_tanim():
    """Tek bir yerel saatte giren kuralın iki kovası (yaz, kış); metin ve figür aynı tanımı okur."""
    import adlar
    k = lambda d: {str(h): {"n": n} for h, n in d.items()}
    assert adlar.mevsim_kovalari(k({17: 1358, 18: 913})) == (17, 18)
    assert adlar.mevsim_kovalari(k({23: 900, 0: 500})) == (23, 0)          # gece yarısını aşan ardışık saatler
    assert adlar.mevsim_kovalari(k({17: 500, 18: 900})) is None             # geç kova kalabalıksa mevsim değil
    assert adlar.mevsim_kovalari(k({17: 900, 19: 500})) is None             # ardışık değil
    assert adlar.mevsim_kovalari(k({17: 393, 18: 847, 19: 361})) is None    # üç kova
    assert adlar.mevsim_kovalari(k({17: 900, 18: 500, 19: 0})) == (17, 18)  # boş kova sayılmaz
    st = {"17": {"n": 1358, "beklenti_r": -0.20}, "18": {"n": 913, "beklenti_r": -0.19}}
    u = _u()
    ctx = {"B": {"cift": {"EURUSD": {"varsayilan": {"saat_tsi": st}}}}}
    u.ON = {"kosul": {"asgari_kova_islem": 30}}
    metin = dm.blok_saat_okuma(u, ctx, "EURUSD")
    assert "yaz saatinde 17:00–17:59 TSİ" in metin and "kış saatinde 18:00–18:59 TSİ" in metin


# ─────────────────────────────────────────────────────────────── ikinci tur: saat, eşik, karşılık, FOMC, yoğunluk
K2 = {"bitis": "2026-10-15", "baslangic": "2018-01-01", "ciftler": ["EURUSD", "GBPUSD"],
      "nokta": {"EURUSD": 1e-5, "GBPUSD": 1e-5}, "pip": {"EURUSD": 1e-4, "GBPUSD": 1e-4}}


def _u2(**ek) -> "dm.Uretim":
    return dm.Uretim({"kunye": K2, "birim": {}, **ek}, {})


def test_tsi_tek_gun_ve_gun_degisimi():
    # New York 17:00, 15 Mart 2020 (ABD yaz saatinde, UTC−4) → 21:00 UTC → ertesi gün 00:00 TSİ.
    assert dm._tsi_tek("2020-03-15", "17:00", "America/New_York") == "TSİ 16.03.2020 00:00"
    # Aynı gün: TSİ'de gün değişmiyorsa tarih yazılmaz.
    assert dm._tsi_tek("2026-10-14", "08:30", "America/New_York") == "TSİ 15:30"
    assert dm._tsi_tek("2020-03-11", "07:00", "Europe/London") == "TSİ 10:00"
    assert dm._tsi_tek("2026-07-15", "12:00", "Europe/London") == "TSİ 14:00"


def test_kalite_esigi_raporun_kendisinden():
    esik = {"tatil": 0.5, "normal": 0.9}
    u = _u2(veri={"kalite": {"EURUSD": {"esik": esik}, "GBPUSD": {"esik": dict(esik)}}})
    assert dm.blok_kalite_esik(u, {}, "normal", "in") == "%90'ın"
    assert dm.blok_kalite_esik(u, {}, "tatil", "in") == "%50'nin"
    # Paritelerde ayrışan, eksik ya da hiç olmayan eşik elle tamamlanmaz: üretim düşer.
    for kalite in ({"EURUSD": {"esik": esik}, "GBPUSD": {"esik": {"tatil": 0.5, "normal": 0.8}}},
                   {"EURUSD": {"esik": esik}, "GBPUSD": {}},
                   {}):
        with pytest.raises(dm.SablonHatasi, match="kalite_esik"):
            dm.blok_kalite_esik(_u2(veri={"kalite": kalite}), {}, "normal")


def _havuz(brut, b_alt, net):
    return {"havuz": {"varsayilan": {"tum": {"brut_r": brut, "ga_brut_alt": b_alt, "ga_brut_ust": brut + 0.03,
                                             "beklenti_r": net, "ga_alt": net - 0.03, "ga_ust": net + 0.03}}}}


def test_karsilik_okumasi_ve_korelasyon():
    kor = {"birimler": ["fiks_momentum", "fiks_donus"], "tum": [[1.0, -0.05], [-0.05, 1.0]]}
    u = _u2(korelasyon=kor, birim={"fiks_momentum": _havuz(0.02, -0.01, -0.10),
                                   "fiks_donus": _havuz(-0.01, -0.04, -0.12)})
    m = dm.blok_karsilik(u, {}, "fiks_momentum:fiks_donus")
    assert "Fiksing momentumu ile Fiksing dönüşü: yalnız birinin brütü artı, ikisi de maliyetten sonra eksi" in m
    assert "günlük R korelasyonu −0,05" in m and "iki paritenin havuzu" in m
    # İkisinin de brütü artı ve aralığı sıfırın üstünde, ikisi de net eksi: maliyet eksiye çeviriyor.
    u = _u2(korelasyon=kor, birim={"fiks_momentum": _havuz(0.06, 0.01, -0.02),
                                   "fiks_donus": _havuz(0.05, 0.02, -0.03)})
    m = dm.blok_karsilik(u, {}, "fiks_momentum:fiks_donus")
    assert "ikisinin de brütü artı ve aralığı sıfırın üstünde, ikisini de maliyet eksiye çeviriyor" in m
    with pytest.raises(dm.SablonHatasi, match="karsilik"):
        dm.blok_karsilik(u, {}, "fiks_momentum:vwap_donus")


def _fomc(satir, n60, n90):
    return {"haber": {"cift": {"EURUSD": {"fomc": {"satir": satir, "ozet": {"basin_60": {"donus": {"n": n60}},
                                                                             "basin_90": {"donus": {"n": n90}}}}}}}}


def test_fomc_paydasi_dusenleri_adiyla_ve_sayimla():
    satir = [{"tarih": "2024-01-31", "karar": 0.3, "basin_60": 0.2, "basin_90": 0.1},
             {"tarih": "2024-03-20", "karar": 0.0, "basin_60": 0.4, "basin_90": 0.5},
             {"tarih": "2024-05-01", "karar": 0.1, "basin_60": -0.2, "basin_90": 0.0}]
    m = dm.blok_fomc_payda(_u2(**_fomc(satir, 2, 1)), {})
    # 20.03 karar penceresinde sıfır (iki pencerede de), 01.05 yalnız uzatılan pencerede sıfır.
    assert "20.03.2024 kararının ilk yarım saatinde hareket sıfır olduğu için 2 (ilk saatte)" in m
    assert ("20.03.2024 kararının ilk yarım saatinde hareket sıfır; 01.05.2024 basın toplantısının ilk doksan "
            "dakikasında hareket sıfır olduğu için 1 (16:00'ya uzatılan pencerede)") in m
    assert "korelasyon her paritede 3 toplantının hepsinden" in m
    # Ölçünün paydası düşen sayısıyla tutmazsa cümle kurulmaz.
    with pytest.raises(dm.SablonHatasi, match="fomc_payda"):
        dm.blok_fomc_payda(_u2(**_fomc(satir, 3, 1)), {})
    with pytest.raises(dm.SablonHatasi, match="FOMC ölçümü yok"):
        dm.blok_fomc_payda(_u2(haber={"cift": {}}), {})
    sifirsiz = [dict(r, karar=0.2, basin_90=0.3) for r in satir]
    assert "hiçbir toplantıda iki hareketten biri sıfır değil" in dm.blok_fomc_payda(_u2(**_fomc(sifirsiz, 3, 3)), {})


def _yogunluk(tekil: bool, **ek) -> dict:
    y = {"n": 40, "n_olay": 8, "toplam_r": 4.0, "olay_r": 3.0, "pay": 0.75, "islem_payi": 0.2, "olay_ort": 0.375,
         "olay_disi_ort": 0.03125, "en_iyi_gun": "2024-05-03", "en_iyi_r": 2.0, "en_iyi_olay_gunu": True,
         "en_iyi_tekil": tekil, "pay_en_iyi_haric": 0.5, **ek}
    return {"haber_yogunluk": y,
            "varsayilan": {"kosul": [{"degisken": "haber_gunu",
                                      "kovalar": [{"kova": "haber günü", "is_n": 30, "is_r": -0.1, "oos_n": 8}]}]}}


def test_olay_gunu_yogunlugu_ve_en_iyi_tek_islem():
    u = _u2()
    s = dm._olay_yogunluk_cumle(u, "EURUSD", _yogunluk(True))
    assert s.startswith("EUR/USD'de örneklem dışı net sonucun ≈%75'i 8 büyük olay günü işleminden geliyor")
    assert "Aynı kova örneklem içinde 30 işlemde −0,10 R'ydi." in s
    assert ("En iyi tek işlem (03.05.2024) de bir büyük olay günündeydi; o çıkarıldığında da kalan sonucun ≈%50'si "
            "olay günlerinden geliyor.") in s
    # En iyi değeri birden çok işlem paylaşıyorsa (2R hedefleri) "en iyi tek işlem" yoktur.
    assert "En iyi tek işlem" not in dm._olay_yogunluk_cumle(u, "EURUSD", _yogunluk(False))
    # Eşiklerin altında cümle kurulmaz; kova kaydı yoksa üretim düşer.
    assert dm._olay_yogunluk_cumle(u, "EURUSD", _yogunluk(True, pay=0.4)) == ""
    assert dm._olay_yogunluk_cumle(u, "EURUSD", _yogunluk(True, islem_payi=0.3)) == ""
    assert dm._olay_yogunluk_cumle(u, "EURUSD", _yogunluk(True, islem_payi=1.0)) == ""
    cv = _yogunluk(True)
    cv["varsayilan"]["kosul"] = []
    with pytest.raises(dm.SablonHatasi, match="olay_yogunluk"):
        dm._olay_yogunluk_cumle(u, "EURUSD", cv)
