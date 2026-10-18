# -*- coding: utf-8 -*-
"""Atıf kapısı (atif.py): atıfın biçimi, künyenin ayrıştırılması ve dondurulmuş kaynağa karşı denetim. Girdiler
sentetik; dondurulmuş dizin geçici dizinde kurulur ve özleri ozler.yaz ile yazılır."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atif  # noqa: E402
import ozler  # noqa: E402


def test_atiflar_anlati_parantez_ve_cok_parcali():
    m = ("Evans (2018) 21 paritede bunu buldu. Getiriler rastgele yürüyüşse (Kaminski ve Lo, 2014) değer katmaz; "
         "evren büyükse en iyisi şansla iyi görünür (White, 2000; Sullivan, Timmermann ve White, 1999). Ayrıca "
         "(kazananın laneti; Ioannidis, 2008) ve (Bailey ve López de Prado, 2014). Gao, Han, Li ve Zhou (2018) "
         "ilk yarım saati sınadı; (O'Brien ve Fleming,\n1979). Tarih aralığı (2018–2023) ve (Mart 2024) atıf değil.")
    assert atif.atiflar(m) == [("Evans", 2018), ("Kaminski ve Lo", 2014), ("White", 2000),
                               ("Sullivan, Timmermann ve White", 1999), ("Ioannidis", 2008),
                               ("Bailey ve López de Prado", 2014), ("Gao, Han, Li ve Zhou", 2018),
                               ("O'Brien ve Fleming", 1979)]
    # Türkçe ek adın dışında kalır; yıldan sonra süren parantezdeki atıf da okunur
    m = ("Melvin ve Prins'e (2015) dayanarak, White'ın (2000) evreni; (Melvin ve Prins, 2015; akış dersi) ve "
         "(EUR/USD, 2024 →).")
    assert atif.atiflar(m) == [("Melvin ve Prins", 2015), ("White", 2000), ("Melvin ve Prins", 2015)]


def test_virgulu_eksik_atif_bicim_hatasidir_tarih_degildir():
    m = "Belgelenmiş olan budur (Melvin ve Prins 2015; akış dersi), ama (Mart 2024) ve (Şubat 2015) birer tarihtir."
    assert atif.bozuk_atiflar(m) == ["Melvin ve Prins 2015"]
    assert atif.atiflar(m) == []          # kayda karşılık aranamaz: kapı onu ayrıca adıyla düşürür


def test_kunye_ayristir_dergi_ve_kurum_belgesi():
    k = atif.kunye_ayristir("White, H. (2000). A Reality Check for Data Snooping. _Econometrica_, 68(5), 1097–1126.")
    assert k == {"yazar": "White, H.", "yil": 2000, "soyadlar": ["White"], "baslik": "A Reality Check for Data Snooping",
                 "dergi": "Econometrica", "cilt": "68", "sayi": "5", "ilk": "1097", "son": "1126"}
    k = atif.kunye_ayristir("Bailey, D. H., Borwein, J. M., López de Prado, M. ve Zhu, Q. J. (2014). P. _N_, 61(5), "
                            "458–471.")
    assert k["soyadlar"] == ["Bailey", "Borwein", "López de Prado", "Zhu"]
    assert atif.kunye_ayristir("Barber, B. M., Lee, Y.-T. ve Odean, T. (2014). X. _J_, 18, 1–24.")["soyadlar"] == \
        ["Barber", "Lee", "Odean"]
    k = atif.kunye_ayristir("Barber, B. M. ve Odean, T. (2014). The Cross-Section. _Journal of Financial Markets_, "
                            "18, 1–24.")
    assert k["cilt"] == "18" and k["sayi"] is None and (k["ilk"], k["son"]) == ("1", "24")
    k = atif.kunye_ayristir("ESMA (2018). ESMA agrees to prohibit binary options. Basın duyurusu, 27 Mart 2018.")
    assert k["yil"] == 2018 and k["baslik"] == "ESMA agrees to prohibit binary options" and "cilt" not in k


def _donmus(tmp_path, d):
    dizin = tmp_path / "kaynak"
    dizin.mkdir()
    (dizin / "white2000.json").write_text(json.dumps(d), encoding="utf-8")
    ozler.yaz(dizin)
    return dizin


def _kayit(tmp_path, **ek):
    k = {"id": "white2000", "atif": "White", "yil": 2000, "ders": ["d"], "durum": "dogrulandi",
         "kunye": "White, H. (2000). A Reality Check for Data Snooping. _Econometrica_, 68(5), 1097–1126.",
         "alinti": ["used more than once for purposes of inference"]}
    k.update(ek)
    yol = tmp_path / "kaynaklar.json"
    yol.write_text(json.dumps({"kaynak": [k]}), encoding="utf-8")
    return yol


DONMUS = {"crossref": {"baslik": "A Reality Check for Data Snooping", "yil": 2000, "cilt": "68", "sayi": "5",
                       "yazarlar": [{"soyad": "White", "ad": "Halbert"}],
                       "sayfa": "1097-1126", "ozet": "Data snooping occurs when a given set of data is used more "
                                                     "than once for purposes of inference or model selection."}}


def test_denetim_gecer_ve_her_kusur_adiyla_duser(tmp_path):
    dizin = _donmus(tmp_path, DONMUS)
    metin = {"d": "Bunu gösterir (White, 2000).\n\n## Kaynaklar\n\n- White (2000)"}
    assert atif.denetim(metin, _kayit(tmp_path), dizin) == []
    # bellekten yazılmış künye: cilt ve sayfa kayar
    h = atif.denetim(metin, _kayit(tmp_path, kunye="White, H. (2000). A Reality Check for Data Snooping. "
                                                   "_Econometrica_, 67(5), 1097–1127."), dizin)
    assert any("cildi 67" in x for x in h) and any("son sayfası 1127" in x for x in h)
    h = atif.denetim(metin, _kayit(tmp_path, kunye="Whyte, H. (2000). A Reality Check for Data Snooping. "
                                                   "_Econometrica_, 68(5), 1097–1126."), dizin)
    assert any("künyenin yazarları ['whyte']" in x for x in h)
    # alıntı kaynakta yok
    h = atif.denetim(metin, _kayit(tmp_path, alinti=["data snooping is entirely harmless in practice"]), dizin)
    assert any("alıntı dondurulmuş kaynakta yok" in x for x in h)
    # PDF'in böldüğü sözcük alıntıyı düşürmez; çok kısa bir alıntı hiçbir şeyi kanıtlamaz
    assert atif.denetim(metin, _kayit(tmp_path, alinti=["used more than once for pur poses of inference"]), dizin) == []
    h = atif.denetim(metin, _kayit(tmp_path, alinti=["data snooping"]), dizin)
    assert any("alıntı çok kısa" in x for x in h)
    # katalog yalnız ilk sayfayı veriyorsa son sayfa kayıtta adıyla açık yazılır
    tek = {**DONMUS, "crossref": {**DONMUS["crossref"], "sayfa": "1097"}}
    (tmp_path / "x").mkdir()
    dizin2 = _donmus(tmp_path / "x", tek)
    h = atif.denetim(metin, _kayit(tmp_path), dizin2)
    assert any("son sayfa katalogda yok" in x for x in h)
    assert atif.denetim(metin, _kayit(tmp_path, acik=["son sayfa"]), dizin2) == []
    # doğrulanmamış kayıt metinde anılamaz
    h = atif.denetim(metin, _kayit(tmp_path, durum="dogrulanamadi"), dizin)
    assert any("doğrulanmamış" in x for x in h)
    # virgülü eksik atıf adıyla düşer
    h = atif.denetim({"d": "Bunu gösterir (White 2000; ek)."}, _kayit(tmp_path), dizin)
    assert any("atıf biçimi bozuk" in x and "(White 2000)" in x for x in h)
    # metinde kaydı olmayan atıf ve kaydın andığı ama metnin anmadığı ders
    h = atif.denetim({"d": "Başka bir şey (Holm, 1979)."}, _kayit(tmp_path), dizin)
    assert any("atıf kayıtta yok: Holm (1979)" in x for x in h) and any("metinde atfı yok" in x for x in h)
    # dondurulmuş dosya sonradan değişirse
    (dizin / "white2000.json").write_text(json.dumps({**DONMUS, "x": 1}), encoding="utf-8")
    assert any("dondurulmuş kaynak" in x for x in atif.denetim(metin, _kayit(tmp_path), dizin))


def test_kaynakca_listesi_atfi_saymaz_ve_dersin_kayitlari_sirali(tmp_path):
    # kaynakça listesindeki "(2000)" metnin atfı sayılmaz: atıf yalnız gövdeden okunur
    dizin = _donmus(tmp_path, DONMUS)
    yol = _kayit(tmp_path)
    metin = {"d": "Atıf yok.\n\n## Kaynaklar\n\n- White, H. (2000). A Reality Check."}
    assert any("metinde atfı yok" in x for x in atif.denetim(metin, yol, dizin))
    kayit = json.loads(yol.read_text(encoding="utf-8"))
    kayit["kaynak"].append({**kayit["kaynak"][0], "id": "a", "atif": "Armitage", "kunye": "Armitage, P. (1969). X."})
    kayit["kaynak"].append({**kayit["kaynak"][0], "id": "b", "atif": "Bailey", "durum": "dogrulanamadi",
                            "kunye": "Bailey, D. (2014). Y."})
    yol.write_text(json.dumps(kayit), encoding="utf-8")
    assert [k["id"] for k in atif.ders_kaynaklari("d", yol)] == ["a", "white2000"]   # doğrulanmamış listeye girmez
