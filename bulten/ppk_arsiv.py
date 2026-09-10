#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPK DUYURU ARŞİVİ — yayımlanmış karar metinlerini depoya indirir.

NEDEN AYRI BİR HAT. Bir merkez bankası metninin TONU tek metinden okunamaz;
ancak bir öncekiyle, giderek yılın tamamıyla yan yana konunca ölçülebilir
(10.09.2026 analizinde ölçüldü: yedi paragrafın altısı önceki metinle birebir
aynı, değişen tek paragraf teşhis). Bir ton endeksi kurulacaksa girdisi bu
arşivdir ve arşiv DEPODA durmalıdır — her ölçümde yeniden indirilirse ölçüm
tekrarlanabilir olmaz.

CANLI DEĞİL. Yayımlanmış bir duyuru bir daha değişmez (bkz. CLAUDE.md, "Orta
Vadeli Program" ilkesi: yayımlanmış bir belge de bir veri kaynağıdır, ama canlı
değildir). Bu yüzden hat İDEMPOTENT: dosyası olan belge yeniden indirilmez,
`--yenile` denmedikçe. Yeni bir toplantıdan sonra koşturulur ve yalnız yeni
belgeyi getirir.

KAPSAM ÖLÇÜLDÜ (10.09.2026, yoklama koşusu): 2016–2026 arasında on bir yılın
ONBİRİNDE de üç liste sayfasının üçü de açık ve toplam ~131 TEKİL faiz kararı
var (yılda 16 → 6; TCMB 2016'da aylık toplanıyordu, bugün sekiz toplantılı
takvimde). Toplantı özeti sayısı ~110.

NE YAPMAZ. Yorum yapmaz, ton ölçmez, hüküm kurmaz — yalnız metni ayrıştırıp
saklar. Ölçüm `bulten/ppk_endeks.py`nin işi; arşiv onun GİRDİSİDİR ve ikisi
bilerek ayrı: girdiyi üreten kod hükmü de kurarsa, hükmün yanlışı girdiye
sessizce sızar.

Koşum:  python3 -u bulten/ppk_arsiv.py --yillar 2016 2026
        python3 -u bulten/ppk_arsiv.py --yillar 2026 2026 --yenile
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ARSIV = BURASI / "veri" / "ppk"

sys.path.insert(0, str(BURASI))
from kesif_ppk import _cek, _duyuru_baglari, _metin, adaylar  # noqa: E402

INDIRME_SN = 30
NAZIK_SN = 0.25          # ardışık istekler arası bekleme — kaynağa yüklenmeyelim

# Künye çıpası İKİ DİLDE: EN "No: 2026-38", TR "Sayı: 2026-38".
BAS = re.compile(r"^(No|Say[ıi])\s*:\s*(DUY|ANO)?(\d{4})-(\d+)")
# Gövdenin bittiği yer: adres bloğu ya da belgenin kendi başlığının tekrarı.
SON = re.compile(r"(?i)^(Central Bank of the Republic|"
                 r"T[üu]rkiye Cumhuriyet Merkez Bankas[ıi]|"
                 r"Faiz Oranlar[ıi]na [İIi]li[şs]kin Bas[ıi]n Duyurusu \(|"
                 r"Para Politikas[ıi] Kurulu Toplant[ıi] [ÖOo]zeti \(|"
                 r"Press Release on Interest Rates \(|"
                 r"Summary of the Monetary Policy Committee Meeting \()")

AY_TR = {"ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5,
         "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8,
         "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11, "kasim": 11,
         "aralık": 12, "aralik": 12}
AY_EN = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
         "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
         "november": 11, "december": 12}

TARIH_TR = re.compile(r"^(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})$")
TARIH_EN = re.compile(r"^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$")

# Karar cümlesindeki oranlar. TR ve EN ayrı yazılıyor; ikisi de yakalanır.
ORAN_TR = re.compile(r"yüzde\s+(\d+(?:,\d+)?)")
ORAN_EN = re.compile(r"(\d+(?:\.\d+)?)\s+percent")


def _tarihe(satir: str) -> str | None:
    """Belgenin kapak tarihi → ISO. Ayrıştıramazsa None (uydurma yok)."""
    s = satir.strip()
    m = TARIH_TR.match(s)
    if m:
        ay = AY_TR.get(m.group(2).lower())
        if ay:
            return f"{int(m.group(3)):04d}-{ay:02d}-{int(m.group(1)):02d}"
    m = TARIH_EN.match(s)
    if m:
        ay = AY_EN.get(m.group(1).lower())
        if ay:
            return f"{int(m.group(3)):04d}-{ay:02d}-{int(m.group(2)):02d}"
    return None


def _tur(baslik: str) -> str:
    b = baslik.lower()
    if "faiz oran" in b or "interest rate" in b:
        return "karar"
    if "toplantı özeti" in b or "summary of the monetary" in b:
        return "ozet"
    return "diger"


def _dil(adres: str) -> str:
    return "EN" if "/EN/" in adres or "ANO" in adres.upper() else "TR"


def _no(adres: str) -> tuple[int, int] | None:
    m = re.search(r"(?i)(?:DUY|ANO)(\d{4})-(\d+)", adres)
    return (int(m.group(1)), int(m.group(2))) if m else None


def ayristir(ham: str) -> dict | None:
    """Sayfa HTML'i → {tarih, paragraflar}. Çıpa tutmazsa None."""
    satirlar = _metin(ham).split("\n")
    icinde = False
    govde: list[str] = []
    tarih = None
    for satir in satirlar:
        if not icinde:
            if BAS.match(satir):
                icinde = True
            continue
        if SON.match(satir):
            break
        # Künyeden hemen sonraki tarih satırı belgenin kapak tarihidir.
        if tarih is None:
            tarih = _tarihe(satir)
            if tarih:
                continue
        if len(satir) > 2:
            govde.append(satir)
    if not govde:
        return None
    return {"tarih": tarih, "paragraflar": govde}


def oranlari_coz(paragraflar: list[str], dil: str) -> list[float]:
    """Karar paragrafındaki faiz oranları — METİNDEN, başka seriden değil.

    Endeksin doğrulanacağı şey kararın KENDİSİ; oranı ayrı bir seriden almak
    ikinci bir hizalama sorunu (hangi gün, hangi kaynak) getirirdi. Metin zaten
    söylüyor: "politika faizi … yüzde 37'de sabit tutulmasına". Ayrıştırılamazsa
    BOŞ döner — ölçülemeyen boş bırakılır.
    """
    kalip = ORAN_EN if dil == "EN" else ORAN_TR
    for p in paragraflar:
        dusuk = p.lower()
        if ("politika faizi" in dusuk or "policy rate" in dusuk):
            ham = kalip.findall(p)
            return [float(x.replace(",", ".")) for x in ham]
    return []


def yol(yil: int, no: int, dil: str) -> Path:
    return ARSIV / f"{yil}" / f"{yil}-{no:02d}-{dil}.json"


def indir(yillar: range, yenile: bool = False) -> int:
    ARSIV.mkdir(parents=True, exist_ok=True)
    yeni = atlanan = tutmayan = kapali = 0
    for yil in yillar:
        baglar: dict[str, str] = {}
        for _ad, url in adaylar(yil):
            kod, govde = _cek(url, INDIRME_SN)
            if kod != 200:
                kapali += 1
                continue
            for metin, adres in _duyuru_baglari(govde, url):
                baglar.setdefault(adres, metin)
            time.sleep(NAZIK_SN)

        hedef = [(a, m) for a, m in baglar.items() if _tur(m) in ("karar", "ozet")]
        print(f"\n▶ {yil}: {len(hedef)} belge (karar + özet, iki dil)")
        for adres, baslik in sorted(hedef, key=lambda kv: (_no(kv[0]) or (0, 0))):
            nn = _no(adres)
            if not nn:
                continue
            byil, bno = nn
            dil = _dil(adres)
            p = yol(byil, bno, dil)
            if p.exists() and not yenile:
                atlanan += 1
                continue
            kod, ham = _cek(adres, INDIRME_SN)
            time.sleep(NAZIK_SN)
            if kod != 200:
                print(f"    ! {byil}-{bno:02d} {dil} indirilemedi ({kod})")
                continue
            coz = ayristir(ham)
            if not coz:
                tutmayan += 1
                print(f"    ! {byil}-{bno:02d} {dil} künye çıpası tutmadı")
                continue
            kayit = {
                "yil": byil, "no": bno, "dil": dil, "tur": _tur(baslik),
                "baslik": baslik, "tarih": coz["tarih"], "adres": adres,
                "paragraflar": coz["paragraflar"],
                "oranlar": oranlari_coz(coz["paragraflar"], dil),
            }
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(kayit, ensure_ascii=False, indent=1),
                         encoding="utf-8")
            yeni += 1
            print(f"    ✓ {byil}-{bno:02d} {dil} {coz['tarih']} "
                  f"{kayit['tur']:6} {len(coz['paragraflar'])} paragraf "
                  f"oran={kayit['oranlar']}")

    print(f"\nARŞİV: yeni {yeni} · zaten vardı {atlanan} · "
          f"çıpa tutmadı {tutmayan} · kapalı liste sayfası {kapali}")
    # ÇIPA TUTMAYAN BELGE SESSİZ GEÇMEZ. Bir ayrıştırıcı kusuru burada
    # "birkaç belge eksik" diye görünür ve endeks onu ölçemez; sayı yazılıyor
    # ki bir sonraki koşu neyin eksik olduğunu bilsin.
    return 0 if tutmayan == 0 else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yillar", nargs=2, type=int, default=[2016, 2026],
                    metavar=("BAS", "SON"))
    ap.add_argument("--yenile", action="store_true",
                    help="dosyası olan belgeyi de yeniden indir")
    a = ap.parse_args()
    return indir(range(a.yillar[0], a.yillar[1] + 1), a.yenile)


if __name__ == "__main__":
    raise SystemExit(main())
