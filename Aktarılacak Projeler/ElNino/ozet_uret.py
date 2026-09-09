# -*- coding: utf-8 -*-
"""El Niño hattı — ÖZET: site/public/projeler/el-nino/ozet.json + uyarilar.json

ANAHTAR BAŞINA SAAT ölçüm katmanından gelir (metrik.py / kuresel.py, `koy`):
her ölçü beslendiği serilerin EN ESKİ ucuyla damgalanmış olarak `<anahtar>_tarih`
taşır. Burada saat TÜRETİLMEZ; eskiden emtia ucundan önekle damgalanıyordu ve
ABD TÜFE'sine bölünen reel seri emtiadan bir ay geride olduğu hâlde emtianın
saatini alıyordu (09.09.2026'da ölçüldü). Şekil saat defteri de aynı
kaynaktan: metrik.sekil_saatleri — grafik.py figürün alt yazısına, burası
`_sekil_tarih`e yazar.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from metrik import KURESEL_SEKILLER, _bicim, ay_adi, gun_damga, sekil_saatleri

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"
HEDEF = PROJE.parent.parent / "site" / "public" / "projeler" / "el-nino"


def _duz(d: dict) -> dict:
    return {k: v for k, v in d.items()
            if not isinstance(v, (list, dict)) and not k.startswith("_")}


def kuresel_yok_satiri(eski_ozet: dict | None) -> str:
    """Küresel blok düştüğünde okura görünen satır.

    Hattın kendi klasöründe 05–09 numaralı şekiller silinir (grafik.py) ama
    SİTEDEKİ kopyalar kalır: kopya sözleşmesi yalnız var olan dosyayı taşır,
    silmeyi taşımaz. Okur eski şekli taze sanmasın diye durum koşu kaydına
    yazılır; şeklin hangi veriyle çizildiği bir önceki özetten okunur."""
    ay = None
    if eski_ozet:
        g = _bicim.tarihe_cevir(eski_ozet.get("kuresel_tarih"))
        if g is not None:
            ay = ay_adi(g)
    return ("Küresel kanat bu koşuda ölçülemedi (emtia, ABD, Euro Bölgesi ve Fed "
            "kaynakları alınamadı): küresel sayılar üretilmedi ve 05–09 numaralı "
            "şekiller yenilenmedi; sayfadaki o şekiller "
            + (f"{ay} verisiyle çizilmiş " if ay else "")
            + "önceki koşudan kalmadır.")


def main() -> int:
    M = json.loads((DATA / "metrik.json").read_text(encoding="utf-8"))
    duz = _duz(M)
    duz["_tarih"] = M["_tarih"]
    duz["_ay"] = M["_ay"]
    duz.setdefault("epizot_sayisi", len(M.get("epizotlar") or []))
    duz.setdefault("olculen_epizot", len(M.get("epizot_sonrasi") or []))
    uyarilar: list[str] = list(M.get("uyarilar") or [])

    # Bir önceki özet: küresel blok düşerse okura "hangi veriyle çizilmişti"
    # demek için okunur, başka hiçbir alanı taşınmaz.
    eski = None
    try:
        eski = json.loads((HEDEF / "ozet.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    # Küresel blok varsa düzleştirilip aynı özete katılır. YOKSA anahtarları da
    # yoktur — <Deger> statik yedeğe düşer. Eski değeri taşımak, ölçülmemiş bir
    # sayıyı ölçülmüş gibi göstermek olurdu.
    kur_yol = DATA / "kuresel.json"
    G = None
    if kur_yol.exists():
        G = json.loads(kur_yol.read_text(encoding="utf-8"))
        duz.update(_duz(G))
        duz["kuresel_tarih"] = G["_tarih"]
        duz["kuresel_ay"] = G["_ay"]
        duz["kuresel_durum"] = "ölçüldü"
        uyarilar += list(G.get("uyarilar") or [])
        # Ürün kırılımının HER SATIRI ayrı alan olur: yazıdaki tablo böylece
        # canlı kalır. Liste olarak bırakılsaydı MDX'e elle kopyalanacaktı ve
        # bir sonraki koşuda sessizce eskirdi. Saat: listenin ölçüm katmanında
        # yazılmış tek saati (ONI, deflatör ve ürün serilerinin en eskisi).
        kir_saat = G.get("kirilim_tarih")
        for d in (G.get("kirilim") or []):
            for alan, deg in (("fark", d.get("fark")),
                              ("tepe", d.get("son_epizot_tepe")),
                              ("n", d.get("olculen")),
                              ("kosulsuz", d.get("kosulsuz")),
                              ("epizot", d.get("epizot_ortalama"))):
                if deg is not None:
                    duz[f"kir_{d['ad']}_{alan}"] = deg
                    duz[f"kir_{d['ad']}_{alan}_tarih"] = kir_saat
        kir = [d for d in (G.get("kirilim") or [])
               if d.get("fark") is not None and not d.get("toplu")]
        if kir:
            en = max(kir, key=lambda d: d["fark"]); dip = min(kir, key=lambda d: d["fark"])
            for k, v in (("kirilim_tepe_ad", en["baslik"]), ("kirilim_tepe_fark", en["fark"]),
                         ("kirilim_dip_ad", dip["baslik"]), ("kirilim_dip_fark", dip["fark"])):
                duz[k] = v
                duz[f"{k}_tarih"] = kir_saat
        duz.setdefault("fed_olculen", len(G.get("fed_yol") or []))
    else:
        print("  ! kuresel.json yok — özet yalnız Türkiye ölçümünü taşıyor")
        duz["kuresel_durum"] = "ölçülemedi"
        uyarilar.append(kuresel_yok_satiri(eski))

    # ŞEKİL SAAT DEFTERİ: çizen kodun ilanı (metrik.sekil_saatleri), figür
    # başına bağlayıcı bacak; ölçülemeyen uç None — sayfa tarih basmaz.
    duz["_sekil_tarih"] = sekil_saatleri(M, G)

    HEDEF.mkdir(parents=True, exist_ok=True)
    (HEDEF / "ozet.json").write_text(
        json.dumps(duz, ensure_ascii=False, indent=1), encoding="utf-8")
    # KOŞU KAYDI — okura olduğu gibi basılır (ortak/okur_dili.kosu_kaydi_tara
    # sınar). Veri katmanının künye uyarıları (adres, istisna metni) buraya
    # GİRMEZ: onlar operatör içindir ve kunye.json'da durur.
    (HEDEF / "uyarilar.json").write_text(json.dumps({
        "kosum": gun_damga(dt.date.today()),
        "veri": M["_tarih"],
        "kuresel_durum": duz["kuresel_durum"],
        "uyarilar": uyarilar,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── özet yazıldı: {HEDEF/'ozet.json'} ({len(duz)} alan, "
          f"{len(uyarilar)} uyarı)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
