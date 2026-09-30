#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BORÇLANMA PROGRAMI YAZISI (30.09.2026) — yayımlanan metni sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
pandas/numpy/plotly YOK: betik yalnız standart kütüphaneyle çalışır, ağa
çıkmaz, duvar saati okumaz (girdisi depodaki arşiv). Dört soru sorar:

1. ARŞİV — `veri/` altındaki her dosyanın sıkıştırılmamış içeriğinin özü
   künyedekiyle aynı mı? Girdi değişmişse yazının bütün sayıları gerekçesiz
   kalır.
2. BELGE — strateji belgelerinin finansman ve ödeme tabloları arşivlenmiş
   metinden BAĞIMSIZ olarak yeniden ayrıştırılıyor (`belge.py`): ölçüm
   dosyasındaki sayılarla ve belgenin kendi özdeşlikleriyle (ihale + doğrudan
   + kamu = iç borçlanma, anapara + faiz = servis, ödeme günleri toplamı =
   servis) tutarlı mı?
3. METİN — yazının tablolarındaki ve cümlelerindeki her ölçülmüş sayı
   `veri/olcum.json` ile aynı mı? Beklenen değerler buraya ELLE yazılmaz;
   ölçüm dosyasından okunur ve yazının tabloları ayrıştırılıp hücre hücre
   karşılaştırılır. İki liste tutulsaydı bir gün sessizce ayrışırdı.
   Cümle aramaları boşluğu tek boşluğa indirir: satır kırılımı metnin
   sözleşmesi değildir, sayı ve sırası sözleşmedir.
4. FİGÜRLER — sekiz figür yayın dizininde var mı, metin her birini gömüyor mu?

Koşum:  python3 dogrula.py
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import re
import statistics as ist
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
SLUG = "borclanma-programi-vade-2026-09-30"
MDX = KOK / "site/src/content/analiz" / f"{SLUG}.mdx"
ONCEKI_MDX = KOK / "site/src/content/analiz/borclanma-programi-vade-2026-08-31.mdx"
SEKIL = KOK / "site/public/analiz" / SLUG
sys.path.insert(0, str(BURASI))
import belge  # noqa: E402

hatalar: list[str] = []
sayac = {"hucre": 0, "metin": 0, "belge": 0}
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
      "Eylül", "Ekim", "Kasım", "Aralık"]
# Metinde sözcükle yazılan küçük sayımlar ("dokuzunda", "sekizinci ardışık ay")
SOZ = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on"]
SIRA = ["", "birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yedinci",
        "sekizinci", "dokuzuncu", "onuncu"]


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 1, arti: bool = False) -> str:
    """Ondalık virgül, binlik nokta, eksi U+2212."""
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if round(x, b) < 0:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0) else s


def yz(x: float, b: int = 1, arti: bool = False) -> str:
    s = "%" + sayi(abs(x), b)
    if round(x, b) < 0:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0) else s


def gun(iso: str) -> str:
    """'2026-10-05' → '05.10'."""
    return f"{iso[8:10]}.{iso[5:7]}"


def tam_gun(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


def ay_uzun(a: str) -> str:
    """'2026-01' → 'Ocak 2026'."""
    return f"{AY[int(a[5:7])]} {a[:4]}"


def terim_gun(terim: str) -> int:
    return int(re.search(r"/\s*(\d+)", terim).group(1))


# ─────────────────────────────────────────────── tablo ayrıştırma
def tablolar(metin: str) -> list[list[list[str]]]:
    out, blok = [], []
    for satir in metin.splitlines():
        s = satir.strip()
        if s.startswith("|") and s.endswith("|"):
            hucre = [h.strip().replace("**", "") for h in s[1:-1].split("|")]
            if not all(set(h) <= set("-: ") for h in hucre):
                blok.append(hucre)
        elif blok:
            out.append(blok)
            blok = []
    if blok:
        out.append(blok)
    return out


def tablo(tl: list, baslik: str, kacinci: int = 0) -> list[list[str]]:
    """Başlık satırının ilk hücresi `baslik` olan tabloların `kacinci`sı."""
    bulunan = [t for t in tl if t and t[0][0] == baslik]
    if len(bulunan) <= kacinci:
        hatalar.append(f"tablo bulunamadı: {baslik!r} #{kacinci}")
        return []
    return bulunan[kacinci]


def hucre(t: list, ilk: str, sutun: int, beklenen: str, ad: str, bas: bool = False) -> None:
    """`ilk` satırının `sutun`. hücresi (0 = etiket) beklenen metne eşit mi
    (`bas`: onunla mı başlıyor)."""
    sayac["hucre"] += 1
    for r in t:
        if r[0] == ilk:
            g = r[sutun] if sutun < len(r) else "(yok)"
            if (g.startswith(beklenen) if bas else g == beklenen):
                return
            hatalar.append(f"{ad} · '{ilk}' sütun {sutun + 1}: metin {g!r}, ölçüm {beklenen!r}")
            return
    hatalar.append(f"{ad}: satır yok: {ilk!r}")


def _ek_sil(s: str) -> str:
    """Kesme işaretinden sonraki eki siler: "59,8'den" → "59,8'". Türkçede ek
    sayının OKUNUŞUNA göre değişir (59,8'den · 90,4'e · 38,27'ye); kapı ekin
    doğruluğunu değil sayının kendisini sorar — yoksa her doğru cümle için
    ayrı bir ek kuralı yazmak gerekirdi."""
    return re.sub(r"'[a-zçğıöşüâîû]+", "'", s)


def _duz(s: str) -> str:
    """Boşluk ve satır sonu tek boşluğa iner; YAML'ın kaçışlı kesmesi ('') teke."""
    return re.sub(r"\s+", " ", s.replace("''", "'"))


def metinde(m: str, parca: str, ad: str) -> None:
    sayac["metin"] += 1
    mm, pp = _ek_sil(_duz(m)), _ek_sil(_duz(parca))
    if pp not in mm and pp.replace(",", "{,}") not in mm:
        hatalar.append(f"metinde yok ({ad}): {parca!r}")


def dogru(kosul: bool, mesaj: str) -> None:
    """Ölçümün kendisi hakkında, metnin sözcükle kurduğu bir iddia."""
    sayac["metin"] += 1
    if not kosul:
        hatalar.append(mesaj)


# ─────────────────────────────────────────────── 1 · arşiv
def arsiv() -> dict:
    kunye = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
    for ad, k in kunye["dosyalar"].items():
        ham = gzip.decompress((VERI / ad).read_bytes())
        if hashlib.sha256(ham).hexdigest() != k["sha256"]:
            hatalar.append(f"arşiv özü tutmuyor: {ad}")
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    if o.get("cipa") != kunye["cipa"]:
        hatalar.append(f"ölçümün çıpası ({o.get('cipa')}) künyeninkiyle ({kunye['cipa']}) aynı değil")
    return o


# ─────────────────────────────────────────────── 2 · belge, bağımsız ayrıştırma
KALEM = ("ihale", "dogrudan", "kamu", "ic_borclanma", "ic_servis", "ic_anapara", "ic_faiz",
         "dis_servis", "dis_anapara", "dis_faiz", "borclanma_disi", "odemeler")


def belgeden(o: dict) -> dict:
    arsiv_ = json.loads(gzip.decompress((VERI / "strateji_arsivi.json.gz").read_bytes()))
    B = [belge.oku(k) for k in arsiv_ if "metin" in k]
    yeni = next(b for b in B if tuple(b["donem"]) == ("2026-10", "2026-12"))
    eski = next(b for b in B if tuple(b["donem"]) == ("2026-09", "2026-11"))
    for ad, b in (("yeni", yeni), ("eski", eski)):
        if b["sha256"] != o["belge"][ad]["sha256"]:
            hatalar.append(f"{ad} belgenin özü ölçüm dosyasındakiyle aynı değil")
        for ay, f in b["finansman"].items():
            for k in KALEM:
                sayac["belge"] += 1
                if f.get(k) != o["program"][ad][ay].get(k):
                    hatalar.append(f"{ad} belge {ay} {k}: belge {f.get(k)} · ölçüm {o['program'][ad][ay].get(k)}")
            for sol, sag, ad2 in ((f["ihale"] + f["dogrudan"] + f["kamu"], f["ic_borclanma"], "borçlanma"),
                                  (f["ic_anapara"] + f["ic_faiz"], f["ic_servis"], "iç servis"),
                                  (f["dis_anapara"] + f["dis_faiz"], f["dis_servis"], "dış servis"),
                                  (f["ic_servis"] + f["dis_servis"], f["odemeler"], "ödemeler"),
                                  (f["borclanma_disi"] + f["ic_borclanma"] + f.get("dis_borclanma", 0),
                                   f["finansman"], "finansman")):
                sayac["belge"] += 1
                if abs(sol - sag) > 0.15:
                    hatalar.append(f"{ad} belge {ay} özdeşlik ({ad2}): {sol:.1f} ≠ {sag:.1f}")
            od = b["odemeler"]["aylar"].get(ay)
            sayac["belge"] += 1
            if not od or abs(od["toplam"] / 1000 - f["ic_servis"]) > 0.15:
                hatalar.append(f"{ad} belge {ay}: ödeme günleri toplamı iç borç servisini tutmuyor")
    # Doğrudan satış satırının adı: "Doğrudan Satışlar" başlığını taşımayan belgeler
    # (satır o yıllarda "Kira Sertifikası" diye geçiyor) hangi aralıkta yayımlanmış?
    adsiz = sorted(k["duyuru"][:7] for k in arsiv_ if k.get("metin")
                   and not re.search(r"Doğrudan\s+Satışlar", k["metin"] if isinstance(k["metin"], str)
                                     else "\n".join(k["metin"])))
    return {"yeni": yeni, "eski": eski, "etiket_aralik": (adsiz[0], adsiz[-1]) if adsiz else None}


# ─────────────────────────────────────────────── 3 · metin
ETIKET = {"Sabit kuponlu": "Sabit Kuponlu Devlet Tahvili", "TLREF'e endeksli": "TLREF'e Endeksli Devlet Tahvili",
          "Altın tahvili": "Altın Tahvili", "Altına dayalı kira sertifikası": "Altına Dayalı Kira Sertifikası",
          "TLREFK'ye endeksli kira sertifikası": "TLREFK'ye Endeksli Kira Sertifikası",
          "ABD doları cinsi devlet tahvili": "ABD Doları Cinsi Devlet Tahvili",
          "Kira sertifikası": "Kira Sertifikası", "Kuponsuz": "Kuponsuz Devlet Tahvili"}


def _senet(etiket: str) -> str:
    for k in sorted(ETIKET, key=len, reverse=True):
        if etiket.startswith(k):
            return ETIKET[k]
    return "?"


def takvim_tablolari(tl: list, o: dict) -> None:
    S = o["takvim"]["satirlar"]
    for i, ay in enumerate(("2026-10", "2026-11")):
        t = tablo(tl, "Kâğıt", i)
        beklenen = [r for r in S if r["ay"] == ay]
        sayac["hucre"] += 1
        if len(t) - 1 != len(beklenen):
            hatalar.append(f"{ay} takvim tablosu: {len(t) - 1} satır, ölçüm {len(beklenen)}")
        for r in t[1:]:
            itfa = "-".join(reversed(r[1].split(".")))
            eslesen = [b for b in beklenen if b["itfa"] == itfa and b["senet"] == _senet(r[0])]
            if len(eslesen) != 1:
                hatalar.append(f"{ay} takvim satırı ölçümde yok: {r[0]!r} {r[1]}")
                continue
            b = eslesen[0]
            sayac["hucre"] += 2
            eski = gun(b["eski_gun"]) if b["eski_gun"] else "—"
            yeni = gun(b["yeni_gun"]) if b["yeni_gun"] else "— (çıktı)"
            if r[2] != eski:
                hatalar.append(f"{ay} {r[0]}: eski gün metin {r[2]!r}, ölçüm {eski!r}")
            if not r[3].startswith(yeni):
                hatalar.append(f"{ay} {r[0]}: yeni gün metin {r[3]!r}, ölçüm {yeni!r}")
            if b["durum"] == "eklendi" and "eklendi" not in r[3]:
                hatalar.append(f"{ay} {r[0]}: eklenen satır işaretsiz")
            if ("ilk ihraç" in r[0]) != ("İlk" in b["yontem"]):
                hatalar.append(f"{ay} {r[0]}: yöntem etiketi ölçümle çelişiyor")


def plan_tablosu(tl: list, o: dict) -> None:
    t = tablo(tl, "Tarih")
    S = o["vade"]["satirlar"]
    sayac["hucre"] += 1
    if len(t) - 1 != len(S):
        hatalar.append(f"plan tablosu {len(t) - 1} satır, ölçüm {len(S)}")
    for r, b in zip(t[1:], S):
        sayac["hucre"] += 5
        if r[0] != b["gun"][:5]:
            hatalar.append(f"plan tablosu gün {r[0]} ≠ {b['gun'][:5]}")
        if _senet(r[1]) != b["senet"]:
            hatalar.append(f"plan tablosu kâğıt {r[1]!r} ≠ {b['senet']!r}")
        if f"/ {sayi(terim_gun(b['terim']), 0)} gün" not in r[2]:
            hatalar.append(f"plan tablosu vade {r[2]!r} ≠ {b['terim']!r}")
        if r[3] != b["itfa"]:
            hatalar.append(f"plan tablosu itfa {r[3]} ≠ {b['itfa']}")
        if r[5] != sayi(b["g_mlr"]):
            hatalar.append(f"plan tablosu {r[0]} {r[1]} beklenen {r[5]} ≠ {sayi(b['g_mlr'])}")
        if f"{int(b['n'])} ihale" not in r[6]:
            hatalar.append(f"plan tablosu {r[0]} {r[1]} kıyas havuzu {r[6]!r} ≠ n {b['n']}")


def finansman_tablosu(tl: list, o: dict) -> None:
    t = tablo(tl, "Kalem (milyar TL)")
    Y, E = o["program"]["yeni"], o["program"]["eski"]
    sutun = [E["2026-10"], Y["2026-10"], E["2026-11"], Y["2026-11"], Y["2026-12"]]
    satir = {"Piyasadan ihale": "ihale", "Doğrudan satış": "dogrudan", "Kamuya satış": "kamu",
             "İç borçlanma": "ic_borclanma", "İç borç servisi": "ic_servis", "· anapara": "ic_anapara",
             "· faiz": "ic_faiz", "Dış borç servisi": "dis_servis", "Borçlanma dışı kaynaklar": "borclanma_disi",
             "Hedef (ihale + kamuya satış)": "hedef"}
    for ad, k in satir.items():
        for i, f in enumerate(sutun, start=1):
            hucre(t, ad, i, sayi(f[k]), "finansman tablosu")
    for ad, k in (("Çevirme oranı", "cevirme"), ("Doğrudan satış payı", "dogrudan_pay")):
        for i, f in enumerate(sutun, start=1):
            hucre(t, ad, i, yz(f[k]), "finansman tablosu")


def metin(o: dict, bg: dict) -> None:
    m = MDX.read_text(encoding="utf-8")
    tl = tablolar(m)
    PR, Y, E = o["program"], o["program"]["yeni"], o["program"]["eski"]
    FK, OD, TT, FT = PR["fark"], o["odeme"], o["takvim_tarihce"], o["finansman_tarihce"]
    V, EY, M, H, A, K, P = o["vade"], o["eylul"], o["maliyet"], o["hedef"], o["arz"], o["kisa_uc"], o["piyasa"]
    Q = PR["ceyrek"]
    ek, ek_e = Y["2026-10"], E["2026-10"]
    GA = V["gercek_aylik"]
    d = P["guncel"]["dibs-verim-egrisi"]
    once, fark = P["onceki"], P["fark_bp"]
    O31 = EY["onceki"]
    sat = {r["itfa"]: r for r in EY["satirlar"]}
    tl_e, y2_e, y5_e, y8_e = sat["11.09.2030"], sat["13.09.2028"], sat["16.04.2031"], sat["27.09.2034"]

    def _f(x: str) -> float:
        return float(x.replace(",", "."))

    # ── 2 · takvim
    takvim_tablolari(tl, o)
    dogru(o["takvim"]["ekim_valor"] == ["2026-10-07"] and o["takvim"]["ekim_ihale_gunleri"] == ["2026-10-05", "2026-10-06"],
          "Ekim'in tek valörü ve iki ihale günü ölçümle çelişiyor")
    dogru(o["takvim"]["valor_aylik"] == {"2026-10": ["2026-10-07"], "2026-11": ["2026-11-11"], "2026-12": ["2026-12-09"]},
          f"ayların tek valör günü değişmiş: {o['takvim']['valor_aylik']}")
    metinde(m, "(7 Ekim, 11 Kasım, 9 Aralık)", "valör günleri")
    # 2.1 — valörü yedi gün öne alınan üç kâğıdın gün sayısı
    kay = [r for r in o["takvim"]["satirlar"] if r["ay"] == "2026-10" and not r["dogrudan"]
           and r["eski_terim"] and terim_gun(r["yeni_terim"]) != terim_gun(r["eski_terim"])]
    dogru(len(kay) == 3 and all(terim_gun(r["yeni_terim"]) - terim_gun(r["eski_terim"]) == 7 for r in kay),
          "valörü öne alınan Ekim kâğıtları üç tane ve yedi gün değil")
    kay_i = {r["itfa"]: r for r in kay}
    metinde(m, f"5 yıllık {sayi(terim_gun(kay_i['2031-04-16']['eski_terim']), 0)}'ten "
               f"{sayi(terim_gun(kay_i['2031-04-16']['yeni_terim']), 0)} güne, TLREF'in 4 yıllığı "
               f"{sayi(terim_gun(kay_i['2030-09-11']['eski_terim']), 0)}'den {sayi(terim_gun(kay_i['2030-09-11']['yeni_terim']), 0)} "
               f"güne, 8 yıllık {sayi(terim_gun(kay_i['2034-09-27']['eski_terim']), 0)}'ten "
               f"{sayi(terim_gun(kay_i['2034-09-27']['yeni_terim']), 0)} güne", "yedi gün")
    # Ekim'in +0,01 yılı yalnız bu yedi günden: ihale kâğıtları iki takvimde aynı
    ek_ihale = [r for r in o["takvim"]["satirlar"] if r["ay"] == "2026-10" and not r["dogrudan"]]
    dogru(all(r["durum"] in ("aynı", "kaydı") for r in ek_ihale) and len(ek_ihale) == 4,
          "Ekim'in ihale kâğıtları iki takvimde aynı değil")
    metinde(m, f"**{sayi(OD['en_buyuk_mlr'])} milyar TL**, Ekim'in iç borç servisinin {yz(OD['en_buyuk_pay_ekim'])}", "7 Ekim")
    metinde(m, f"toplam {sayi(OD['ekim_diger_gunler_mlr'])} milyar TL", "14 ve 21 Ekim")
    dogru(abs(OD["ekim_7_program_mlr"] - (ek["ihale"] + ek["dogrudan"])) < 0.05, "7 Ekim programı ihale + doğrudan değil")
    metinde(m, f"**{sayi(OD['ekim_7_program_mlr'])} milyar TL** ({sayi(ek['ihale'])} + {sayi(ek['dogrudan'])}), 7 Ekim "
               f"valörlü: o günün ödemesinin {sayi(OD['ekim_7_fazla_mlr'])} milyar TL üstünde", "7 Ekim fazlası")
    metinde(m, f"Kamuya satışın {sayi(ek['kamu'])} milyar TL'si", "kamuya satış valörsüz")
    itfa7 = [r for r in TT["ekim_itfa_dogrudan"] if r["itfa"] == "2026-10-07"]
    dogru(sorted(r["senet"] for r in itfa7) == ["Altın Tahvili", "Altına Dayalı Kira Sertifikası"]
          and {r["ihale"] for r in itfa7} == {"2024-10-07"} and {r["valor"] for r in itfa7} == {"2024-10-09"},
          "7 Ekim'de itfa olan altın senetleri ölçümle çelişiyor")
    metinde(m, f"satış {tam_gun(itfa7[0]['ihale'])}, valör {tam_gun(itfa7[0]['valor'])}", "altın itfası")
    dogru(TT["ilk_haftada_biten"] == ["2022-07", "2026-10"], f"ilk haftada biten aylar değişmiş: {TT['ilk_haftada_biten']}")
    dogru(TT["son_gun_10_ve_once"] == ["2020-12", "2022-07", "2023-05", "2026-10"],
          f"ilk on günde biten aylar değişmiş: {TT['son_gun_10_ve_once']}")
    metinde(m, "ilk on gününde bittiği iki ay daha var (Aralık 2020, Mayıs 2023)", "ilk on gün")
    metinde(m, f"{TT['kesin_ay_sayisi']} kesin aylık takvimde", "kesin ay sayısı")
    metinde(m, f"| Son ihaleden bir sonraki ayın ilk ihalesine kadar boşluk | {TT['ekim_bosluk']} gün | Medyan "
               f"{sayi(TT['bosluk_medyan'], 0)} gün; en uzun {TT['bosluk_maks']} gün, üç kez "
               f"({', '.join(ay_uzun(a) for a in TT['bosluk_maks_aylar'])}) |", "boşluk")
    dogru(TT["bosluk_ekim_ve_ustu"] == 3 and len(TT["bosluk_maks_aylar"]) == 3,
          f"en uzun boşluk ayları değişmiş: {TT['bosluk_maks_aylar']}")
    metinde(m, f"| Ayın son ihalesinin günü | {TT['ekim_son']} |", "son ihale günü")
    g = TT["ilk_gun_gecis"]
    dogru(g["diger"] == 0 and g["ayni"] + g["bir_gun"] + g["bir_hafta"] == g["n"], f"ilk gün geçişleri tutmuyor: {g}")
    metinde(m, f"{g['n']} geçişin {g['ayni']}'inde aynı gün, {g['bir_gun']}'unda bir gün, {g['bir_hafta']}'inde bir "
               f"hafta kaydı; bir hafta öne çekildiği yalnız {g['one_cekilen']} ay var", "ilk gün geçişi")
    t = tablo(tl, "Gün")
    hucre(t, "05.10", 2, sayi(A["gun_toplam"]["05.10.2026"]), "gün arzı")
    hucre(t, "06.10", 2, sayi(A["gun_toplam"]["06.10.2026"]), "gün arzı")
    metinde(m, f"hedefinin %{sayi(V['gerceklesme_varsayimi'], 0)}'sine ölçeklenmiş", "gerçekleşme varsayımı")

    # ── 3 · finansman
    finansman_tablosu(tl, o)
    metinde(m, f"bir ayda {sayi(FK['2026-10']['ic_servis'])} milyar TL arttı (anapara {sayi(FK['2026-10']['ic_anapara'], 1, True)}, "
               f"faiz {sayi(FK['2026-10']['ic_faiz'], 1, True)})", "servis artışı")
    ekim = {g_["gun"]: g_ for g_ in OD["ekim"]}
    g7, g21 = ekim["2026-10-07"], ekim["2026-10-21"]
    metinde(m, f"7 Ekim ödemesi {sayi(g7['eski'])}'ten {sayi(g7['yeni'])}'e ({sayi(g7['fark'], 1, True)})", "7 Ekim farkı")
    metinde(m, f"21 Ekim ödemesi {sayi(g21['eski'])}'dan {sayi(g21['yeni'])}'a ({sayi(g21['fark'], 1, True)})", "21 Ekim farkı")
    dogru(ekim["2026-10-14"]["fark"] == 0.0, "14 Ekim ödemesi değişmiş, metin 'aynı' diyor")
    metinde(m, f"{sayi(ek_e['ic_borclanma'])}'den {sayi(ek['ic_borclanma'])}'e ({sayi(FK['2026-10']['ic_borclanma'], 1, True)})", "borçlanma farkı")
    metinde(m, f"**borçlanma dışı kaynaklarla** ({sayi(FK['2026-10']['borclanma_disi'], 1, True)})", "bdk farkı")
    metinde(m, f"İhale {sayi(-FK['2026-10']['ihale'])}, kamuya satış {sayi(-FK['2026-10']['kamu'])} milyar TL azalırken doğrudan "
               f"satış {sayi(FK['2026-10']['dogrudan'])} milyar TL arttı", "Ekim bileşim farkı")
    metinde(m, f"hedef bu yüzden {yz(FK['2026-10']['hedef_yuzde'])} gösteriyor; iç borçlanmanın toplamı ise "
               f"{yz((ek['ic_borclanma'] / ek_e['ic_borclanma'] - 1) * 100, 1, True)}", "yüzdeler")
    metinde(m, f"ihale {sayi(-FK['2026-11']['ihale'])} milyar TL azaldı, doğrudan satış {sayi(E['2026-11']['dogrudan'])}'dan "
               f"{sayi(Y['2026-11']['dogrudan'])}'a indi, kamuya satış {sayi(FK['2026-11']['kamu'])} milyar TL arttı", "Kasım bileşimi")
    dogru(abs(FK["2026-11"]["ihale"] + FK["2026-11"]["kamu"] + FK["2026-11"]["dogrudan"]) < 0.05, "Kasım'ın bileşim farkları toplamı sıfır değil")
    metinde(m, f"{sayi(E['2026-11']['hedef'])}'ten {sayi(Y['2026-11']['hedef'])}'a", "Kasım hedefi")
    metinde(m, f"ihale {sayi(E['2026-11']['ihale'])}'ten {sayi(Y['2026-11']['ihale'])}'e iniyor", "Kasım ihalesi")
    metinde(m, f"{yz(FK['2026-10']['hedef_yuzde'])})", "Ekim hedef yüzdesi (özet)")
    t = tablo(tl, "Ölçü (Ekim–Aralık 2026)")
    hucre(t, "İç borç servisi", 1, f"{sayi(Q['ic_servis'])} milyar TL (anapara {sayi(Q['ic_anapara'])} · faiz {sayi(Q['ic_faiz'])})", "çeyrek")
    hucre(t, "Faizin iç borç servisindeki payı", 1, yz(Q["faiz_pay"]), "çeyrek")
    hucre(t, "İç borçlanma", 1, f"{sayi(Q['ic_borclanma'])} milyar TL", "çeyrek")
    hucre(t, "Çevirme oranı", 1, yz(Q["cevirme"]), "çeyrek")
    hucre(t, "İhale · doğrudan satış · kamuya satış", 1,
          f"{yz(Q['ihale_pay'])} · {yz(Q['dogrudan_pay'])} · {yz(Q['kamu_pay'])}", "çeyrek")
    hucre(t, "Dış borç servisi · planlanan dış borçlanma", 1, f"{sayi(Q['dis_servis'])} · 0,0 milyar TL", "çeyrek")
    hucre(t, "Borçlanma dışı kaynakların ödemelerdeki payı", 1,
          f"{yz(Q['bdk_pay'])} ({sayi(Q['borclanma_disi'])} / {sayi(Q['odemeler'])} milyar TL)", "çeyrek")
    metinde(m, f"net **{sayi(Q['ic_servis'] - Q['ic_borclanma'])} milyar TL**", "net ödeme")
    seri = FT["seri"]
    bdk = sorted(((seri[a]["borclanma_disi"], a) for a in seri), reverse=True)
    dogru(bdk[2][1] == "2026-10" and [a for _, a in bdk[:2]] == ["2026-01", "2026-02"],
          f"borçlanma dışı kaynakların ilk üçü değişmiş: {bdk[:3]}")
    metinde(m, f"önündeki iki ay Ocak ve Şubat 2026 ({sayi(bdk[0][0])} ve {sayi(bdk[1][0])})", "bdk sırası")

    # ── 4 · doğrudan satışlar
    dogru(bg["etiket_aralik"] == ("2019-11", "2020-11"), f"'Kira Sertifikası' etiketli belge aralığı değişmiş: {bg['etiket_aralik']}")
    metinde(m, f"({ay_uzun(bg['etiket_aralik'][0])} – {ay_uzun(bg['etiket_aralik'][1])} belgelerinde aynı satır", "etiket aralığı")
    t = tablo(tl, "Ölçü", 1)
    S_ = FT["ekim_sira"]
    esit = sorted(a for a in seri if a != "2026-10" and seri[a]["dogrudan"] == S_["dogrudan"]["deger"])
    hucre(t, "Doğrudan satış", 1, f"{sayi(S_['dogrudan']['deger'])} milyar TL", "sıra")
    hucre(t, "Doğrudan satış", 2, f"{S_['dogrudan']['buyukten_sira']}. büyük, {' ve '.join(ay_uzun(a) for a in esit)} ile eşit "
                                  f"(yüzdelik %{sayi(S_['dogrudan']['yuzdelik'], 0)})", "sıra")
    hucre(t, "İç borçlanmadaki payı", 1, yz(S_["dogrudan_pay"]["deger"]), "sıra")
    hucre(t, "İç borçlanmadaki payı", 2, f"{S_['dogrudan_pay']['buyukten_sira']}. büyük (yüzdelik %{sayi(S_['dogrudan_pay']['yuzdelik'], 0)})", "sıra")
    hucre(t, "Borçlanma dışı kaynaklar", 1, f"{sayi(S_['borclanma_disi']['deger'])} milyar TL", "sıra")
    hucre(t, "Borçlanma dışı kaynaklar", 2, f"{S_['borclanma_disi']['buyukten_sira']}. büyük (yüzdelik %{sayi(S_['borclanma_disi']['yuzdelik'], 0)})", "sıra")
    cv = [seri[a]["cevirme"] for a in seri if a != "2026-10"]
    c0 = S_["cevirme"]["deger"]
    hucre(t, "Çevirme oranı", 1, yz(c0), "sıra")
    hucre(t, "Çevirme oranı", 2, f"{sum(x > c0 for x in cv)} ayda daha yüksek, {sum(x < c0 for x in cv)} ayda daha düşük, "
                                 f"{sum(x == c0 for x in cv) + 1} ayda eşit (yüzdelik %{sayi(S_['cevirme']['yuzdelik'], 0)})", "sıra")
    dogru(FT["n"] == 83 and FT["ilk"] == "2019-12" and FT["son"] == "2026-10",
          f"tarihsel seri kapsamı değişmiş: {FT['ilk']}–{FT['son']} ({FT['n']})")
    metinde(m, f"Temmuz ve Ağustos 2025'te {sayi(seri['2025-07']['dogrudan'])} ve {sayi(seri['2025-08']['dogrudan'])} milyar TL'ye çıktı "
               f"(2024'ün aylık ortalaması {sayi(FT['yil24_dogrudan_ort'])}, 2025'inki {sayi(FT['yil25_dogrudan_ort'])}) ve "
               f"**2026'nın ilk dokuz ayında ortalama {sayi(FT['yil26']['dogrudan'])} milyar TL** oldu (payı ortalama "
               f"{yz(FT['yil26']['dogrudan_pay'])})", "rejim")
    y25 = [seri[a]["dogrudan"] for a in seri if a.startswith("2025")]
    dogru(sorted(y25)[-2:] == sorted([seri["2025-07"]["dogrudan"], seri["2025-08"]["dogrudan"]]),
          "2025'in en büyük iki doğrudan satış ayı Temmuz–Ağustos değil")
    mn, mx = FT["yil26_dogrudan_min"], FT["yil26_dogrudan_maks"]
    dogru(mn[1] == "2026-09" and mx[1] == "2026-07", f"2026'nın en düşük/en yüksek ayı değişmiş: {mn} {mx}")
    metinde(m, f"en düşük ay {sayi(mn[0])} milyar TL ile **Eylül**, en yüksek {sayi(mx[0])} ile Temmuz", "2026 uçları")
    dogru(TT["doviz_altin_2026_ay"] == 8 and TT["doviz_altin_2026_bos"] == ["2026-09"],
          "2026'da altın/döviz doğrudan satışı olan ay sayısı değişmiş")
    usd = TT["usd_tahvil_aylari"]
    metinde(m, f"{ay_uzun(usd[0])}'den bu yana {len(usd)} kesin takvimde yer aldı; Ekim 2026 yılın "
               f"{SIRA[sum(1 for a in usd if a.startswith('2026'))]}", "USD tahvili")
    R = FT["dogrudan_revizyon"]
    metinde(m, f"{R['n']} ayda, bir ayın ilk yayımlanan doğrudan satış hedefi ile kesin hedefi karşılaştırıldığında "
               f"{R['yukari']}'sında kesin olan daha yüksek, {R['asagi']}'ünde düşük, {R['ayni']}'sinde aynı; medyan fark "
               f"{sayi(R['medyan_fark'], 1, True)} milyar TL", "revizyon yönü")
    z = R["zincir"]
    metinde(m, f"{sayi(z['2026-10'][0])} → {sayi(z['2026-10'][1])} → {sayi(z['2026-10'][2])}", "Ekim doğrudan zinciri")
    dogru(len(z["2026-11"]) == 2 and z["2026-11"][1] < z["2026-11"][0] and z["2026-12"] == [0.0],
          f"Kasım/Aralık doğrudan zinciri değişmiş: {z['2026-11']} {z['2026-12']}")
    metinde(m, f"**Kasım'ın {sayi(z['2026-11'][1])}'ı ikinci sürüm** ve ilk revizyonu aşağıydı "
               f"({sayi(z['2026-11'][0])} → {sayi(z['2026-11'][1])})", "Kasım zinciri")
    metinde(m, f"İlk revizyonu aşağı olan {R['asagi_sonra']['n']} ayın {R['asagi_sonra']['yukari']}'sinde kesin hedef ikinci "
               f"sürümün üstünde çıktı", "aşağıdan sonra")
    metinde(m, f"İlk değeri sıfır olan {R['sifirdan']['n']} ayın {R['sifirdan']['yukari']}'unda kesin hedef sıfırın üstündeydi, "
               f"ama o ayların medyan kesin değeri yalnız {sayi(R['sifirdan']['yukari_medyan'])} milyar TL", "sıfırdan")
    dogru(R["dusuk_ilk_2026_yukari"] == len(R["dusuk_ilk_2026"]) == 3, "2026'nın düşük ilk sürümlü ayları değişmiş")
    for a, i, k_ in R["dusuk_ilk_2026"]:
        metinde(m, f"{AY[int(a[5:])]} {sayi(i, 0)} → {sayi(k_, 0)}", "düşük ilk sürüm")

    # ── 5 · servis
    t = tablo(tl, "Dördüncü çeyrek")
    for yil in ("2022", "2023", "2024", "2025"):
        q = FT["q4"][f"{yil}-Ç4"]
        hucre(t, yil, 1, sayi(q["ic_servis"]), "Q4")
        hucre(t, yil, 2, sayi(q["ic_faiz"]), "Q4")
        hucre(t, yil, 3, yz(q["faiz_pay"]), "Q4")
    q = FT["q4"]["2026-Ç4"]
    hucre(t, "2026 (plan)", 1, sayi(q["ic_servis"]), "Q4")
    hucre(t, "2026 (plan)", 2, sayi(q["ic_faiz"]), "Q4")
    hucre(t, "2026 (plan)", 3, yz(q["faiz_pay"]), "Q4")
    q25 = FT["q4"]["2025-Ç4"]
    dogru(min((FT["q4"][f"{y}-Ç4"]["faiz_pay"], y) for y in ("2022", "2023", "2024", "2025", "2026"))[1] == "2026",
          "2026 dördüncü çeyreğinin faiz payı 2022'den bu yana en düşük değil")
    metinde(m, f"anapara ({sayi(q['ic_anapara'])} milyar TL) geçen yılın aynı çeyreğinin ({sayi(q25['ic_anapara'])}) "
               f"{sayi(q['ic_anapara'] / q25['ic_anapara'])} katı", "anapara oranı")
    metinde(m, f"**{yz(FT['q4_faiz_artis_yuzde'])}**, iç borç servisi **{yz(FT['q4_servis_artis_yuzde'])}**", "Q4 artış")
    metinde(m, f"Yıllık TÜFE'yle ({yz(FT['q4_faiz_reel_tufe'], 2)}, Ağustos) arındırıldığında faiz ödemesindeki reel artış "
               f"yalnız {yz(FT['q4_faiz_reel_yuzde'])}", "reel faiz artışı")
    metinde(m, f"çeyreğin faiz ödemesi ({sayi(Q['ic_faiz'])}) iç borçlanmanın ({sayi(Q['ic_borclanma'])}) "
               f"{yz(Q['ic_faiz'] / Q['ic_borclanma'] * 100)}'üne eşit", "faiz/borçlanma")
    c = FT["ceyrek"]
    ilk3 = [c[f"2026-Ç{i}"]["ic_servis"] for i in (1, 2, 3)]
    dogru(1400 <= min(ilk3) and max(ilk3) <= 1700, f"2026'nın ilk üç çeyreği 1,4–1,7 trilyon bandının dışında: {ilk3}")
    dec = Y["2026-12"]
    metinde(m, f"Aralık'ta anapara yalnız {sayi(dec['ic_anapara'])} milyar TL, faiz {sayi(dec['ic_faiz'])} milyar TL "
               f"(payı {yz(dec['faiz_pay'])})", "Aralık faiz")

    # ── 6 · vade
    t = tablo(tl, "Ay")
    for ad, a in (("Ekim 2026", "2026-10"), ("Kasım 2026", "2026-11")):
        v = V["aylik"][a]
        hucre(t, ad, 1, sayi(v["aov_karsi"], 2), "vade tablosu")
        hucre(t, ad, 2, sayi(v["aov"], 2), "vade tablosu")
        hucre(t, ad, 3, sayi(v["aov_fark"], 2, True), "vade tablosu")
        hucre(t, ad, 4, f"{yz(v['tlref_pay_karsi'])} → {yz(v['tlref_pay'])}", "vade tablosu")
        hucre(t, ad, 5, f"{sayi(v['reprice_karsi'], 2)} → {sayi(v['reprice'], 2)}", "vade tablosu")
    va = V["aylik"]["2026-12"]
    hucre(t, "Aralık 2026", 2, sayi(va["aov"], 2), "vade tablosu")
    hucre(t, "Aralık 2026", 4, f"— → {yz(va['tlref_pay'])}", "vade tablosu")
    hucre(t, "Aralık 2026", 5, f"— → {sayi(va['reprice'], 2)}", "vade tablosu")
    s5 = next(r for r in V["satirlar"] if r["itfa"] == "16.04.2031" and r["gun"].endswith(".10.2026"))
    metinde(m, f"\"5 yıl / {sayi(terim_gun(s5['terim']), 0)} gün\" {sayi(s5['v'], 2)} yıldır", "kalan vade örneği")
    plan_tablosu(tl, o)
    metinde(m, f"üç ayda {sayi(sum(r['g_mlr'] for r in V['satirlar']))} milyar TL", "plan toplamı")
    metinde(m, f"üç ayın beklenen satışının {yz(A['tek_kiyas_pay'])}'ünü taşıyor", "tek kıyas payı")
    dogru(A["tek_kiyas_satir"] == 4, f"tek ihaleye dayanan satır sayısı {A['tek_kiyas_satir']}, metin 'dört satır'")
    kas = {r["itfa"]: r for r in o["takvim"]["satirlar"] if r["ay"] == "2026-11" and not r["dogrudan"]}
    metinde(m, f"yeni 5 yıllık kâğıt ({sayi(terim_gun(kas['2031-11-05']['eski_terim']) / 365, 2)} yıl) yerine 16.04.2031 "
               f"itfalı kâğıt ({sayi(terim_gun(kas['2031-04-16']['yeni_terim']) / 365, 2)} yıl)", "Kasım kâğıt vadeleri")
    metinde(m, f"Planın üç aylık ortalaması {sayi(V['plan_aov'], 2)} yıl", "plan AOV")
    t = tablo(tl, "3 aylık yuvarlanan vade (yıl)")
    YU = V["yuvarlanan"]
    for i, a in enumerate(("2026-09", "2026-10", "2026-11", "2026-12"), start=1):
        hucre(t, "Bugün", i, sayi(YU[a], 2), "yuvarlanan")
    for i, k_ in enumerate(("vp_plan_ay1_yuv", "vp_plan_ay2_yuv", "vp_plan_ay3_yuv"), start=1):
        hucre(t, "31 Ağustos projeksiyonu", i, O31[k_], "yuvarlanan")
    metinde(m, f"projeksiyondan {sayi(YU['2026-09'] - _f(O31['vp_plan_ay1_yuv']), 2)} yıl uzun", "Eylül farkı")
    metinde(m, f"{sayi(YU['2026-10'] - _f(O31['vp_plan_ay2_yuv']), 2)} ve {sayi(YU['2026-11'] - _f(O31['vp_plan_ay3_yuv']), 2)} yıllık fark", "Ekim-Kasım farkı")
    metinde(m, f"Ekim'de {sayi(V['yuvarlanan_karsi']['2026-10'], 2)}, Kasım'da {sayi(V['yuvarlanan_karsi']['2026-11'], 2)} yıl", "karşı olgu yuvarlanan")
    metinde(m, f"değişimi {sayi(V['uzama_3a'], 2, True)} yıl", "uzama")
    metinde(m, f"{V['uzama_n']} üç aylık değişimin", "uzama n")
    metinde(m, f"{yz(V['uzama_yuzdelik'], 0)}'lük yüzdelikte", "uzama yüzdelik")
    metinde(m, f"Temmuz'un {sayi(YU['2026-07'], 2)} yılından Eylül'ün {sayi(YU['2026-09'], 2)} yılına iki ayda "
               f"{sayi(YU['2026-09'] - YU['2026-07'], 2)} yıl", "iki aylık sıçrama")
    dogru(abs(YU["2026-12"] - V["plan_aov"]) < 0.005, "Aralık'ın yuvarlanan vadesi planın üç aylık ortalaması değil")

    # ── 7 · TLREF payı ve faiz riski
    t = tablo(tl, "Ölçü", 2)
    hucre(t, "TLREF'e endeksli ve değişken faizli pay", 1, f"%{O31['vp_plan_tlref_pay']}", "başlık")
    hucre(t, "TLREF'e endeksli ve değişken faizli pay", 2, yz(V["plan_tlref_pay"]), "başlık")
    hucre(t, "Sabit (bono, kuponsuz, sabit kuponlu) pay", 1, f"%{O31['vp_plan_sabit_pay']}", "başlık")
    hucre(t, "Sabit (bono, kuponsuz, sabit kuponlu) pay", 2, yz(V["plan_sabit_pay"]), "başlık")
    hucre(t, "Yeniden fiyatlama vadesi", 1, f"{O31['vp_reprice_plan']} yıl", "başlık")
    hucre(t, "Yeniden fiyatlama vadesi", 2, f"{sayi(V['plan_reprice'], 2)} yıl", "başlık")
    metinde(m, f"**{yz(EY['ekim_tlref_pay_0831'])}** TLREF payı", "31.08 kıyas verisiyle Ekim")
    t3 = EY["tahmin_0831"]["tlref_son3"]
    metinde(m, f"({' · '.join(sayi(r['mlr']) for r in t3)} milyar TL); bugün kıyas o kâğıdın 14 Eylül'deki ilk satışı "
               f"({sayi(tl_e['gerc_mlr'])} milyar TL)", "TLREF kıyası")
    RD = V["reprice_duyarlilik_05"]
    metinde(m, f"0,5 yıl alınsa planın ortalaması {sayi(V['plan_reprice'], 2)} yerine {sayi(RD['plan'], 2)}, son on üç ayın "
               f"gerçekleşeni {sayi(V['gecmis_12a_reprice'], 2)} yerine {sayi(RD['gecmis_13a'], 2)}, Ekim'in aynı ay kıyası "
               f"{sayi(V['aylik']['2026-10']['reprice_karsi'], 2)} → {sayi(V['aylik']['2026-10']['reprice'], 2)} yerine "
               f"{sayi(RD['ekim_karsi'], 2)} → {sayi(RD['ekim'], 2)} yıl", "0,5 duyarlılığı")
    metinde(m, f"gerçekleşen {sayi(V['gecmis_12a_reprice'], 2)} yılından (aynı pencerede vade {sayi(V['gecmis_12a_aov'], 2)} yıl)", "13 ay fiyatlama")
    t = tablo(tl, "Gerçekleşen")
    aylar3 = ("2026-07", "2026-08", "2026-09")
    for ad, k_, b, yuzde in (("Ağırlıklı ortalama vade (yıl)", "aov", 2, False), ("Bono hariç vade (yıl)", "aov_bonosuz", 2, False),
                             ("TLREF'e endeksli ve değişken faizli pay", "tlref_pay", 1, True),
                             ("Sabit faizli pay (bono dahil)", "sabit_pay", 1, True), ("Bono payı", "bono_pay", 1, True),
                             ("Yeniden fiyatlama vadesi (yıl)", "reprice", 2, False)):
        for i, a in enumerate(aylar3, start=1):
            hucre(t, ad, i, yz(GA[a][k_], b) if yuzde else sayi(GA[a][k_], b), "gerçekleşen tablosu")
    for ad, x in (("Ağırlıklı ortalama vade (yıl)", sayi(EY["aov_plan_yazi"], 2)), ("Bono hariç vade (yıl)", sayi(EY["aov_plan_yazi"], 2)),
                  ("TLREF'e endeksli ve değişken faizli pay", yz(EY["tlref_pay_plan"])),
                  ("Sabit faizli pay (bono dahil)", yz(100 - EY["tlref_pay_plan"])), ("Bono payı", yz(0)),
                  ("Yeniden fiyatlama vadesi (yıl)", sayi(EY["reprice_plan"], 2))):
        hucre(t, ad, 4, x, "gerçekleşen tablosu")
    dogru(abs(GA["2026-09"]["aov"] - EY["aov_gerc"]) < 0.005, "Eylül'ün iki AOV ölçüsü ayrışıyor")
    nt = ("2026-04", "2026-05", "2026-06", "2026-07")
    dogru(all(GA[a]["tlref_pay"] > 50 for a in nt), "Nisan–Temmuz TLREF payı dört ayın dördünde %50'nin üstünde değil")
    metinde(m, f"({' · '.join(yz(GA[a]['tlref_pay']) for a in nt)}) ve yeniden fiyatlama vadesi {sayi(GA['2026-04']['reprice'], 2)}'tan "
               f"{sayi(GA['2026-07']['reprice'], 2)} yıla kısalıyordu", "Nisan–Temmuz")
    metinde(m, f"faiz riskinin vadesi {sayi(GA['2026-08']['reprice'], 2)} yıla sıçradı", "Ağustos sıçraması")
    metinde(m, f"Bono hariç ölçülünce Ağustos {sayi(GA['2026-08']['aov_bonosuz'], 2)}, Eylül {sayi(GA['2026-09']['aov_bonosuz'], 2)} yıl", "bono hariç")

    # ── 8 · Eylül
    t = tablo(tl, "İhale")
    ad = {"13.09.2028": "2 yıl sabit · 14.09", "11.09.2030": "4 yıl TLREF · 14.09",
          "16.04.2031": "5 yıl sabit · 15.09", "27.09.2034": "8 yıl sabit · 15.09"}
    for r in EY["satirlar"]:
        s_ = ad[r["itfa"]]
        for i, (k_, b) in enumerate((("plan_mlr", 1), ("gerc_mlr", 1), ("kat", 2), ("rekabetci_teklif_mlr", 1),
                                     ("rekabetci_mlr", 1)), start=1):
            hucre(t, s_, i, sayi(r[k_], b), "Eylül tablosu")
        hucre(t, s_, 6, yz(r["rekabetci_kabul"]), "Eylül tablosu")
        hucre(t, s_, 7, sayi(r["rot_mlr"]), "Eylül tablosu")
        hucre(t, s_, 8, sayi(r["btc"], 2), "Eylül tablosu")
        hucre(t, s_, 9, yz(r["bilesik"], 2), "Eylül tablosu")
    HD = EY["hedef_doldurma"]
    metinde(m, f"tahmin {sayi(EY['plan_mlr'])}, gerçekleşen {sayi(EY['gerc_mlr'])} — hedefin {yz(HD['oran_ham'], 2)}'i", "Eylül toplam")
    metinde(m, f"TLREF'e gelen rekabetçi teklif ({sayi(tl_e['rekabetci_teklif_mlr'])} milyar TL) dört ihalenin en büyüğü, "
               f"teklif/satış oranı ({sayi(tl_e['btc'], 2)}) en yükseği; Hazine bu teklifin {yz(tl_e['rekabetci_kabul'])}'sini", "TLREF talebi")
    dogru(max(EY["satirlar"], key=lambda r: r["rekabetci_teklif_mlr"])["itfa"] == "11.09.2030"
          and max(EY["satirlar"], key=lambda r: r["btc"])["itfa"] == "11.09.2030", "TLREF en büyük teklif ve en yüksek oran değil")
    metinde(m, f"**{sayi(EY['uzun_sabit_gerc_mlr'])} milyar TL** sattı — tahminimizin ({sayi(EY['uzun_sabit_plan_mlr'])} milyar TL) "
               f"{sayi(EY['uzun_sabit_gerc_mlr'] / EY['uzun_sabit_plan_mlr'], 1)} katı", "uzun sabit")
    metinde(m, f"ay genelinde bu pay {yz(EY['rot_pay_gerc'])}; 5 yıllığın {sayi(y5_e['gerc_mlr'])} milyar TL'sinin "
               f"{sayi(y5_e['rot_mlr'])}'si, 8 yıllığın {sayi(y8_e['gerc_mlr'])}'unun {sayi(y8_e['rot_mlr'])}'ı", "ROT payı")
    metinde(m, f"TLREF'te {yz(tl_e['rot_py_kabul'])}'si ({sayi(tl_e['rot_py_teklif_mlr'])} milyar TL'nin "
               f"{sayi(tl_e['rot_py_mlr'])}'ı), 5 ve 8 yıllıkta {yz(y5_e['rot_py_kabul'])} ve "
               f"{yz(y8_e['rot_py_kabul'])}'si kabul edildi", "piyasa yapıcı ROT kabulü")
    TK = EY["tlref_kabul"]
    metinde(m, f"TLREF'teki oran 2025–2026'nın {TK['py_n']} TLREF ihalesinin en düşük {SIRA[TK['py_sira_kucukten']]}si", "PY sırası")
    metinde(m, f"Eylül'ün vadesi {sayi(EY['aov_gerc'], 2)} yıl (tahminimiz {sayi(EY['aov_plan_yazi'], 2)}), TLREF payı "
               f"{yz(EY['tlref_pay_gerc'])} (tahminimiz {yz(EY['tlref_pay_plan'])}), yeniden fiyatlama vadesi "
               f"{sayi(EY['reprice_gerc'], 2)} yıl (tahminimiz {sayi(EY['reprice_plan'], 2)}); harmanlanmış bileşik faiz "
               f"{yz(EY['maliyet_gerc'], 2)}", "Eylül sonucu")
    # kutu: karar mı, mekanik mi
    metinde(m, f"öbür {TK['diger_n']} TLREF ihalesinde rekabetçi kabulün medyanı {yz(TK['diger_medyan'])} ve "
               f"{SOZ[TK['diger_50_alti']]}unda %50'nin altında; Eylül'ün {yz(TK['eylul'])}'si", "TLREF taban oranı")
    dogru(TK["eylul"] == tl_e["rekabetci_kabul"], "TLREF kabulünün iki ölçüsü ayrışıyor")
    metinde(m, f"({TK['onceki_gun']}, {yz(TK['onceki_kabul'])})", "önceki TLREF ihalesi")
    metinde(m, f"önceki üç TLREF ihalesinin ortalamasıydı ({sayi(EY['tahmin_0831']['tlref_kiyas_mlr'])} milyar TL)", "TLREF kıyas ortalaması")
    dogru(abs(ist.mean(r["mlr"] for r in t3) - EY["tahmin_0831"]["tlref_kiyas_mlr"]) < 0.06, "TLREF kıyası son üç ihalenin ortalaması değil")
    SB = EY["sabit4_kabul"]
    dogru(SB["eylul_5y"] == y5_e["rekabetci_kabul"] and SB["eylul_8y"] == y8_e["rekabetci_kabul"]
          and min(SB["eylul_5y"], SB["eylul_8y"]) > SB["diger_maks"], "uzun sabit kuponun kabulü taban oranın en yükseğini aşmıyor")
    metinde(m, f"{yz(SB['eylul_5y'])} ve {yz(SB['eylul_8y'])}, 2025–2026'da 4 yıl ve üstü öbür {SB['diger_n']} sabit kuponlu "
               f"ihalenin en yükseğinin ({yz(SB['diger_maks'])}) üstünde; o ihalelerin medyanı {yz(SB['diger_medyan'])}", "sabit taban oranı")
    KY = EY["fiyat"]["kuyruk"]
    metinde(m, f"5 yıllıkta {sayi(KY['16.04.2031']['fark_bp'], 0)}, 8 yıllıkta {sayi(KY['27.09.2034']['fark_bp'], 0)} baz puan; "
               f"TLREF'te {sayi(KY['11.09.2030']['fark_bp'], 0)}, 2 yıllıkta {sayi(KY['13.09.2028']['fark_bp'], 0)} baz puan", "kuyruk")
    FY = EY["fiyat"]
    dogru(abs(FY["tlref_red_mlr"] - (tl_e["rekabetci_teklif_mlr"] - tl_e["rekabetci_mlr"])) < 0.06, "reddedilen TLREF teklifi tutmuyor")
    metinde(m, f"reddedilen {sayi(FY['tlref_red_mlr'])} milyar TL'lik teklifin ortalama bileşik faizi {yz(FY['tlref_red_ort'])}, "
               f"kesmenin ({yz(KY['11.09.2030']['kesme'], 2)}) {sayi((FY['tlref_red_ort'] - KY['11.09.2030']['kesme']) * 100, 0)} "
               f"baz puan üstü", "reddedilen TLREF")
    dogru(abs(HD["gun15_mlr"] - HD["kalan_mlr"]) < 0.06 and HD["yarim_puan_ici"] == 1,
          f"hedefin son gün doldurulması ölçümle çelişiyor: {HD}")
    metinde(m, f"Eylül'ün hedefi {sayi(HD['hedef'])} milyar TL'ydi; 14 Eylül'de {sayi(HD['gun14_mlr'])} satıldı, 15 Eylül'de "
               f"kalan {sayi(HD['kalan_mlr'])}'un tamamı. Ay {yz(HD['oran_ham'], 2)}'le kapandı: hedef–gerçekleşme kaydının "
               f"{HD['ay_n']} ayında hedefin yarım puan yakınında biten tek ay", "hedef doldurma")
    metinde(m, f"hedefin %{sayi(EY['tahmin_0831']['varsayim'], 0)}'sine ölçekliydi, Eylül {yz(HD['oran_ham'], 2)} gerçekleşti", "%87 varsayımı")
    metinde(m, f"hedefin %{sayi(EY['tahmin_0831']['varsayim'], 0)}'sine ölçekli. Gerçekleşen", "%87 figür notu")
    y8s = next(r for r in EY["y8_son3"] if r["gun"] == EY["tahmin_0831"]["y8_son_ihale"])
    metinde(m, f"kâğıt en son {y8s['gun']}'te, {sayi(y8s['mlr'])} milyar TL satılmıştı", "8 yıllık eski kıyas")
    pka24 = d["pka_faiz_24a"]
    metinde(m, f"24 ay sonrası politika faizi beklentisi ({yz(pka24, 2)}) ise bir haftalık repo faizidir ve bileşik karşılığı "
               f"{yz(EY['anket_24a_bilesik'], 2)}. Aradaki fark **{sayi(EY['y8_anket_fark'])} puan**", "8 yıl vs anket")
    dogru(abs(EY["anket_24a_bilesik"] - ((1 + pka24 / 100 * 7 / 365) ** (365 / 7) - 1) * 100) < 0.006, "anketin bileşik karşılığı tutmuyor")
    metinde(m, f"8 yıllık kâğıdın {yz(y8_e['bilesik'], 2)}'u yıllık bileşik", "8 yıllık faiz")
    ua, ue, BR = EY["uzun_agu"], EY["uzun_eyl"], EY["btc_rekabetci"]
    metinde(m, f"Ağustos'un {sayi(ua['btc'], 2)}'ünün altına düşerse", "1,63 eşiği")
    metinde(m, f"15 Eylül'de oran {sayi(ue['btc'], 2)} oldu; yalnız rekabetçi tekliflerle {sayi(BR['y8'], 2)} (Ağustos'taki 9 yıllıkta "
               f"{sayi(BR['agu9'], 2)})", "Eylül 8 yıl oranı")
    metinde(m, f"{sayi(ua['teklif_mlr'])} milyar TL teklifin {sayi(ua['gerc_mlr'])}'ünü almıştı", "Ağustos 9 yıl")
    metinde(m, f"{sayi(ue['teklif_mlr'])}'in {sayi(ue['gerc_mlr'])}'unu ({yz(ue['kabul_teklif_orani'])})", "Eylül 8 yıl")
    metinde(m, f"Teklifin kendisi {yz(abs(ue['teklif_mlr'] / ua['teklif_mlr'] - 1) * 100, 0)} azaldı", "teklif düşüşü")

    # ── 9 · kısa uç
    metinde(m, f"Son bono ihalesi {K['son_bono']['gun'][:2].lstrip('0')} Ağustos 2026 ({sayi(K['son_bono']['mlr'])} milyar TL)", "son bono")
    metinde(m, f"son on iki ayın bono satışı {sayi(K['bono_12a_mlr'])} milyar TL", "12 ay bono")
    dogru(TT["bonosuz_kosu"]["2026-12"] == 4 and TT["bonosuz_kosu"]["2026-09"] == 1
          and TT["bonosuz_en_uzun"] == {"bitis": "2021-06", "ay": 12}, "bonosuz ardışık ay ölçüleri değişmiş")
    metinde(m, f"arasında **{TT['bonosuz_en_uzun']['ay']} ay**", "en uzun bonosuz")
    kup = TT["kuponsuz"]
    son_k = kup[-1]
    dogru(son_k["ay"] == "2026-12" and son_k["gun"] == 483, "Aralık kuponsuzu ölçümde 483 gün değil")
    onc = kup[:-1]
    metinde(m, f"{TT['kuponsuz_n_onceki']} kuponsuz ihraç satırı", "kuponsuz sayısı")
    metinde(m, f"({min(k_['gun'] for k_ in onc)}–{TT['kuponsuz_maks_gun_onceki']} gün) ve **{TT['kuponsuz_bonosuz_ay']}'u bononun "
               f"planda olmadığı aylarda**", "kuponsuz örüntü")
    BP = TT["bonosuz_ay_pay"]
    dogru(TT["kuponsuz_bonosuz_ay"] + TT["kuponsuz_bonolu_ay"] == TT["kuponsuz_n_onceki"], "kuponsuz satırları bonolu + bonosuz değil")
    metinde(m, f"({ay_uzun(BP['bas'])} – {ay_uzun(BP['son'])}) {BP['n']} ayın {BP['bonosuz']}'inde zaten bono yoktu. Bonosuz aylar "
               f"dönemin {yz(BP['bonosuz'] / BP['n'] * 100, 0)}'sı, kuponsuz satırlarının "
               f"{yz(TT['kuponsuz_bonosuz_ay'] / TT['kuponsuz_n_onceki'] * 100, 0)}'ü", "bonosuz taban")
    metinde(m, f"bononun yanında da {TT['kuponsuz_bonolu_ay']} kez geldi", "bonolu kuponsuz")
    sk = K["son_kuponsuz"]
    metinde(m, f"Son kuponsuz ihale {int(sk['gun'][:2])} {AY[int(sk['gun'][3:5])]} {sk['gun'][6:]}'da, "
               f"{round(sk['v'] * 12)} aylık, {sayi(sk['mlr'])} milyar TL, {yz(sk['bilesik'], 2)}'ten", "son kuponsuz")
    metinde(m, f"Beklenen satış {sayi(A['kuponsuz_mlr'])} milyar TL: Aralık ihale planının {yz(A['kuponsuz_aralik_pay'])}'si, "
               f"üç ayın {yz(A['kuponsuz_pay'])}'ü", "kuponsuz payı")
    kv_ = next(r for r in V["satirlar"] if r["senet"] == "Kuponsuz Devlet Tahvili")
    metinde(m, f"ihale sonuçlarındaki {int(kv_['n'])} kuponsuz tahvil ihalesinden", "kuponsuz havuzu")
    dogru(int(kv_["n"]) == K["kuponsuz_n"], "kuponsuz havuzu ihale sonuçlarındaki kuponsuz sayısı değil")
    metinde(m, f"1 yıl ({yz(d['spot_1y'], 2)}) ile 2 yıl ({yz(d['spot_2y'], 2)})", "16 ay komşuları")

    # ── 10 · Kasım
    ay31 = EY["t160431_aylar_2026"]
    dogru(ay31 == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"], f"16.04.2031'in 2026 ayları değişmiş: {ay31}")
    metinde(m, f"Nisan'dan Eylül'e {SOZ[len(ay31)]} ayın {SOZ[len(ay31)]}sında satıldı, yani Kasım satışı kâğıdın "
               f"{SIRA[len(ay31) + 2]} ardışık ayı", "sekizinci ardışık ay")

    # ── 11 · maliyet
    t = tablo(tl, "Kova")
    kv = M["kova"]
    for ad_, k_ in (("≤ 1 yıl, sabit (bono)", "sabit|≤1 yıl"), ("1–3 yıl, sabit", "sabit|1–3 yıl"), ("3–6 yıl, sabit", "sabit|3–6 yıl"),
                    ("6 yıl üstü, sabit", "sabit|6 yıl+"), ("3–6 yıl, TLREF'e endeksli ve değişken faizli", "degisken|3–6 yıl")):
        hucre(t, ad_, 1, yz(kv[k_]["maliyet"], 2), "maliyet")
        hucre(t, ad_, 2, sayi(kv[k_]["mlr"]), "maliyet")
    metinde(m, f"**{sayi(M['makas_1a_6p'], 2)} puan**", "makas")
    metinde(m, f"**{yz(M['plan'], 2)}**; 31 Ağustos planınınki %{O31['vp_plan_maliyet']}", "plan maliyeti")
    metinde(m, f"(planın {yz(M['plan_eylul_ihale_pay'])}'sı için mümkün, kalanı kovasıyla) sepet **{yz(M['plan_eylul_fiyat'], 2)}**", "Eylül fiyatıyla sepet")
    metinde(m, f"**{yz(EY['maliyet_gerc'], 2)}**", "Eylül maliyet")
    metinde(m, f"({yz(kv['reel|3–6 yıl']['maliyet'], 2)})", "reel")
    dogru(M["pencere_bas"] == "2026-05-15" and M["veri_sonu"] == "2026-09-15", "maliyet penceresi değişmiş")

    # ── 12 · hedefler
    t = tablo(tl, "Ay", 1)
    for ad_ in ("Eylül 2026", "Ekim 2026", "Kasım 2026", "Aralık 2026"):
        a = {"Eylül 2026": "2026-09", "Ekim 2026": "2026-10", "Kasım 2026": "2026-11", "Aralık 2026": "2026-12"}[ad_]
        hucre(t, ad_, 1, " → ".join(sayi(x) for x in H["zincir"][a]), "hedef zinciri")
    metinde(m, f"**{yz(H['ekim_ilk_fark_yuzde'])}**", "Ekim ilk fark")
    metinde(m, f"kesin ayı bilinen {H['rev_n']} ayında", "revizyon n")
    metinde(m, f"medyan revizyon **{yz(H['rev_medyan'])}**, ortalama mutlak revizyon {yz(H['rev_mutlak_ort'])} ve revizyonların "
               f"yalnız {yz(H['rev_yukari_pay'], 0)}'i yukarı; ay başına ortalama {sayi(H['rev_surum_ort'])} sürüm", "revizyon")
    metinde(m, f"Kasım'ın {yz(H['kasim_fark_yuzde'], 1, True)}'u", "Kasım revizyonu")
    ar = H["aralik"]
    dogru(len(ar) == 6 and H["aralik_yukari"] == sum(v > 0 for v in ar.values()) == 3 and H["aralik_asagi"] == 3,
          f"Aralık revizyonları değişmiş: {ar}")
    metinde(m, f"{min(ar)[:4]}–{max(ar)[:4]} arasındaki {SOZ[len(ar)]} Aralık'ın {SOZ[H['aralik_yukari']]}ünde hedef yukarı, "
               f"{SOZ[H['aralik_asagi']]}ünde aşağı", "Aralık revizyonları")
    g_ = H["gerc_24a"]
    metinde(m, f"ortalama {yz(g_['ort'])}, medyan {yz(g_['medyan'])}, en düşük {yz(g_['min'])}, en yüksek {yz(g_['maks'])}, "
               f"standart sapma {sayi(g_['std'])} puan; {g_['n']} ayın {g_['alti_n']}'sinde ({yz(g_['alti_pay'], 0)}) hedefin altında", "gerçekleşme")
    metinde(m, f"Eylül {yz(HD['oran_ham'], 2)} ile hedefi tam tutturdu", "Eylül hedef")

    # ── 13 · eğri
    t = tablo(tl, "Vade")
    dug = ["spot_3a", "spot_6a", "spot_1y", "spot_2y", "spot_3y", "spot_5y", "spot_7y"]
    for i, k_ in enumerate(dug, start=1):
        hucre(t, "28.08.2026", i, sayi(once[k_], 2), "eğri")
        hucre(t, d["_tarih"], i, sayi(d[k_], 2), "eğri")
        hucre(t, "Değişim (bp)", i, sayi(fark[k_], 0, True), "eğri")
    dogru(all(150 <= fark[k_] <= 190 for k_ in ("spot_3y", "spot_5y", "spot_7y")), "3–7 yıl bölgesi 150–190 baz puan satılmamış")
    dogru(fark["forward_2y1y"] > fark["forward_1y1y"], "ileri oranlarda en büyük artış iki yıl sonrası değil")
    metinde(m, f"{yz(once['forward_1y1y'], 2)}'den {yz(d['forward_1y1y'], 2)}'e ({sayi(fark['forward_1y1y'], 0, True)} bp)", "1y1y")
    metinde(m, f"{yz(once['forward_2y1y'], 2)}'ten {yz(d['forward_2y1y'], 2)}'e ({sayi(fark['forward_2y1y'], 0, True)} bp)", "2y1y")
    metinde(m, f"{yz(once['pka_faiz_12a'], 2)}'dan {yz(d['pka_faiz_12a'], 2)}'ye", "anket 12 ay")
    metinde(m, f"{sayi(abs(P['egim_2y5y_once']), 2)} puandan {sayi(abs(P['egim_2y5y']), 2)} puana", "terslik")
    ul = A["uzun_satirlar"]
    metinde(m, f"{sayi(A['uzun_mlr'])} milyar TL, üç ihalede ({' · '.join(sayi(r['g_mlr']) for r in ul)})", "uzun arz")
    metinde(m, f"{TT['ekim_bosluk'] - 1} gün ihale yok (bir ihaleden ötekine {TT['ekim_bosluk']} gün)", "ihalesiz gün")
    dogru((dt.date(2026, 11, 9) - dt.date(2026, 10, 6)).days == TT["ekim_bosluk"], "boşluk 6 Ekim → 9 Kasım değil")
    metinde(m, f"Eylül'ün tahmini de {sayi(y8_e['plan_mlr'])} milyar TL'ydi ve {sayi(y8_e['gerc_mlr'])} satıldı", "8 yıllık tahmin")

    # ── 14 · karne
    t = tablo(tl, "#")
    KR = {k_["no"]: k_ for k_ in o["karne"]}
    KT = o["karne_tez"]
    kt = KT["olculen"]
    metinde(m, f"| Tez | Vade uzuyor, faiz riski uzamıyor (yeniden fiyatlama vadesi {sayi(kt['reprice_gecmis'], 2)} → "
               f"{sayi(kt['reprice_plan'], 2)} yıl) |", "tez beklentisi")
    hucre(t, "Tez", 2, f"Eylül'ün vadesi {sayi(kt['eylul_aov'], 2)} yıl (karşı olgu {sayi(kt['eylul_karsi'], 2)}, tahmin "
                       f"{sayi(kt['eylul_plan'], 2)}); yeniden fiyatlama vadesi {sayi(kt['eylul_reprice'], 2)} yıl", "karne tez")
    hucre(t, "Tez", 3, KT["hukum"], "karne tez hüküm")
    dogru(kt["eylul_aov"] > kt["eylul_karsi"] and kt["eylul_reprice"] > kt["reprice_gecmis"],
          "tezin hükmü ölçümle çelişiyor (vade uzamadı ya da faiz riski uzamadı)")
    ol = KR[1]["olculen"]
    hucre(t, "1", 2, f"Eylül gerçekleşeni {sayi(ol['eylul_yuv'], 2)} (projeksiyon {sayi(ol['yazi_eylul_yuv'], 2)}); yeni planla Ekim "
                     f"{sayi(ol['ekim_yuv'], 2)}, Kasım {sayi(ol['kasim_yuv'], 2)}, Aralık {sayi(ol['aralik_yuv'], 2)}", "karne")
    ol = KR[3]["olculen"]
    hucre(t, "3", 2, f"Ekim {sayi(ol['ekim'][1])} → {sayi(ol['ekim'][2])}; Kasım {sayi(ol['kasim'][0])} → {sayi(ol['kasim'][1])}", "karne")
    hucre(t, "4", 2, f"İhale 13 Ekim'den 6 Ekim'e alındı, henüz yapılmadı; 15 Eylül'de {sayi(KR[4]['olculen']['eylul_8y_btc'], 2)}", "karne", bas=True)
    hucre(t, "5", 2, f"Politika faizi 10 Eylül'de sabit kaldı ({yz(KR[5]['olculen']['politika'])})", "karne")
    ol = KR[6]["olculen"]
    hucre(t, "6", 2, f"2 yıl–5 yıl tersliği {sayi(abs(ol['egim_2y5y_once']), 2)} → {sayi(abs(ol['egim_2y5y']), 2)} puan, kapanmadı; "
                     f"plan vadesi {sayi(ol['plan_aov'], 2)} yıl, kısa uçta yalnız 16 aylık kuponsuz ({yz(A['kuponsuz_pay'])})", "karne")
    # hüküm ölçüm dosyasından okunur; ikinci bir liste tutulmaz
    for no, k_ in KR.items():
        hucre(t, str(no), 3, k_["hukum"], "karne hüküm")
    metinde(m, f"Eylül zaten projeksiyonun {sayi(YU['2026-09'] - _f(O31['vp_plan_ay1_yuv']), 2)} yıl üstünde bitti ve yeni plan "
               f"Ekim'i {sayi(YU['2026-10'], 2)}'e taşıyor", "karne 1 gidişat")
    # 31 Ağustos yazısının kendi sayıları (sabit basılır): 2y–9y tersliği ve momentum girdisi
    om = ONCEKI_MDX.read_text(encoding="utf-8")
    t9 = re.search(r'anahtar="egim_2y9y_mutlak" ondalik=\{1\}>([\d,]+)</Deger>', om).group(1)
    metinde(m, f"2 yıl–9 yıl tersliğiydi ({t9} puan)", "eski 2y–9y")
    mo = re.search(r'anahtar="baz_momentum_aylik" ondalik=\{2\}>([\d,]+)</Deger>', om).group(1)
    KS = o["karne_senaryo"]
    enf = P["guncel"]["enflasyon"]
    dogru(KS["kol"] == "kırılmaz" and min(KS["cekirdek"], KS["manset"]) >= KS["esik"], "momentum kolu ölçümle çelişiyor")
    metinde(m, f"Eşik aylık %{sayi(KS['esik'])}'luk çekirdek momentumdu. Ağustos'ta çekirdek C'nin mevsimsellikten "
               f"arındırılmış üç aylık yıllıklandırılmış hızı {yz(enf['c_3a'], 2)}, aylık karşılığı {yz(KS['cekirdek'], 2)}; "
               f"31 Ağustos yazısının andığı %{mo}'lik seri ise manşet TÜFE'nin arındırılmış son üç ay ortalamasıdır "
               f"(o sayfadaki düzeltme notu) ve Ağustos'ta {yz(KS['manset'], 2)}", "momentum")
    dogru("duzeltmeler:" in om and f"%{mo}" in om.split("duzeltmeler:")[1].split("\n---")[0],
          "31 Ağustos yazısında momentum girdisinin düzeltme notu yok")
    t = tablo(tl, "Momentum kırılmaz kolunun beklentisi")
    sira_ = ["DİBS 2 yıl yatay ya da yukarı", "DİBS 9 yıl yatay", "2 yıl–9 yıl tersliği artar", "Enflasyon risk primi genişler",
             "Hazine'nin bir sonraki belgesinde sabit kupon payı artar",
             "Yıl sonu OIS 100–125 baz puana geriler; 2027 OIS %33,50 civarında kalır"]
    sayac["hucre"] += 1
    if [r[0] for r in t[1:]] != sira_:
        hatalar.append(f"senaryo tablosunun satırları değişmiş: {[r[0] for r in t[1:]]}")
    for ad_, s_ in zip(sira_, KS["satirlar"]):
        hucre(t, ad_, 2, s_["hukum"], "senaryo hüküm")
    hucre(t, sira_[0], 1, f"{sayi(fark['spot_2y'], 0, True)} bp", "senaryo")
    hucre(t, sira_[2], 1, f"2 yıl–5 yıl tersliği {sayi(abs(P['egim_2y5y_once']), 2)} → {sayi(abs(P['egim_2y5y']), 2)} puan, azaldı", "senaryo")
    hucre(t, sira_[3], 1, f"5 yıllık risk primi {sayi(once['risk_primi_5y'], 2)} → {sayi(d['risk_primi_5y'], 2)} puan", "senaryo")
    hucre(t, sira_[4], 1, f"Başlık sayısında %{O31['vp_plan_sabit_pay']} → {yz(V['plan_sabit_pay'])}, aynı ay kıyasında değişim yok; "
                          f"ihalelerde TLREF payı Temmuz'un {yz(GA['2026-07']['tlref_pay'])}'inden Ağustos ve Eylül'de "
                          f"{yz(GA['2026-08']['tlref_pay'])} ve {yz(GA['2026-09']['tlref_pay'])}'ye indi", "senaryo")

    # ── 15 · beklentiler
    metinde(m, f"planın {sayi(V['aylik']['2026-10']['aov'], 2)} yılının üstünde, TLREF payı planın {yz(V['aylik']['2026-10']['tlref_pay'])}'inin", "beklenti 1")
    metinde(m, f"iki ayda TLREF payı {yz(GA['2026-08']['tlref_pay'])} ve {yz(GA['2026-09']['tlref_pay'])}, vade "
               f"{sayi(GA['2026-08']['aov'], 2)} ve {sayi(GA['2026-09']['aov'], 2)} yıl", "beklenti 1 dayanak")
    metinde(m, f"medyanı {yz(TK['diger_medyan'])} ve %50'nin altında kalması olağan", "beklenti 1 taban")
    metinde(m, f"o ihalelerin medyanının ({yz(SB['diger_medyan'])})", "beklenti 1 sabit taban")
    metinde(m, f"{sayi(z['2026-11'][0])} → {sayi(z['2026-11'][1])}) için {R['asagi_sonra']['n']} ayın {R['asagi_sonra']['yukari']}'si; "
               f"Aralık'ınki (ilk değer sıfır) için {R['sifirdan']['n']} ayın {R['sifirdan']['yukari']}'u, ama medyan kesin değer "
               f"{sayi(R['sifirdan']['yukari_medyan'])} milyar TL", "beklenti 2")
    metinde(m, f"Aralık'ın {sayi(Y['2026-12']['hedef'])} milyar TL'lik hedefi", "beklenti 3")
    metinde(m, f"revizyonların {yz(H['rev_yukari_pay'], 0)}'si yukarı ve medyan {yz(H['rev_medyan'])}; ama "
               f"{min(ar)[:4]}–{max(ar)[:4]}'in {SOZ[len(ar)]} Aralık'ında {SOZ[H['aralik_yukari']]} yukarı, "
               f"{SOZ[H['aralik_asagi']]} aşağı", "beklenti 3 dayanak")
    metinde(m, f"({TT['kuponsuz_n_onceki']} satırın {TT['kuponsuz_bonosuz_ay']}'u; bonosuz ayların payı "
               f"{yz(BP['bonosuz'] / BP['n'] * 100, 0)})", "beklenti 4")

    # ── Ne ölçmedik · izleme
    metinde(m, f"ödemesinden {sayi(OD['ekim_7_fazla_mlr'])} milyar TL fazla borçlanıyor", "ön finansman")
    metinde(m, f"bir ayda {sayi(FK['2026-10']['ic_servis'])} milyar TL artmasının", "servis artışı (sınır)")
    katlar = [r["kat"] for r in EY["satirlar"]]
    metinde(m, f"tahminin {sayi(min(katlar), 2)} ile {sayi(max(katlar), 2)} katı", "kat aralığı")
    import csv
    import io
    ham = gzip.decompress((VERI / "ihale.csv.gz").read_bytes()).decode("utf-8-sig")
    ih = list(csv.DictReader(io.StringIO(ham)))
    aylar_ih = sorted(f"{r['İhale Tarihi'][6:10]}-{r['İhale Tarihi'][3:5]}" for r in ih)
    dogru(aylar_ih[0] == "2020-01" and aylar_ih[-1] == "2026-09",
          f"ihale veri seti {aylar_ih[0]} – {aylar_ih[-1]}, metin Ocak 2020 – Eylül 2026 diyor")
    metinde(m, "ihale veri setimiz Ocak 2020'de başlıyor", "veri seti başlangıcı")
    metinde(m, f"HMB ihale sonuç duyuruları, Ocak 2020 – Eylül 2026, {len(ih)} ihale", "kaynakça ihale")
    metinde(m, f"HMB ihale sonuç duyuruları (Ocak 2020 – Eylül 2026, {len(ih)} ihale)", "künye ihale")
    metinde(m, f"5 yıllıkta rekabetçi olmayan satış payı (Eylül'de {yz(y5_e['rot_mlr'] / y5_e['gerc_mlr'] * 100, 0)})", "izleme 5 yıl ROT")
    metinde(m, f"(plan {yz(V['aylik']['2026-10']['tlref_pay'])}) · 5 ve 8 yıllıkta kabul (Eylül {yz(y5_e['rekabetci_kabul'])} · "
               f"{yz(y8_e['rekabetci_kabul'])}) · 8 yıllık satış (tahmin {sayi(sat_plan('27.09.2034', V))}) · teklif/satış "
               f"(Eylül {sayi(y8_e['btc'], 2)})", "izleme 6 Ekim")
    metinde(m, f"Çeyreğin en büyük ödemesi ({sayi(OD['en_buyuk_mlr'])} milyar TL)", "izleme 7 Ekim")
    metinde(m, f"doğrudan satışı ({sayi(Y['2026-11']['dogrudan'])}) · Aralık hedefi ({sayi(Y['2026-12']['hedef'])})", "izleme 30 Ekim")
    metinde(m, f"Aralık'ın kesin takvimi ve doğrudan satışı ({sayi(Y['2026-12']['dogrudan'])})", "izleme 30 Kasım")
    metinde(m, f"Satış (tahmin {sayi(A['kuponsuz_mlr'])} milyar TL)", "izleme 7 Aralık")

    # ── özet, açıklama ve rakam şeridi: gövdeyle aynı sayılar
    metinde(m, f"iç borçlanmasının {yz(ek['dogrudan_pay'])}'ı", "tez doğrudan payı")
    va10 = V["aylik"]["2026-10"]
    metinde(m, f"planlı vade {sayi(va10['aov_karsi'], 2)}'den {sayi(va10['aov'], 2)} yıla gidiyor", "tez planlı vade")
    metinde(m, f"gerçekleşen vade Temmuz'da {sayi(GA['2026-07']['aov'], 2)}, Eylül'de {sayi(GA['2026-09']['aov'], 2)} yıl; TLREF payı "
               f"{yz(GA['2026-07']['tlref_pay'])}'den {yz(GA['2026-09']['tlref_pay'])}'ye indi, faiz riskinin vadesi "
               f"{sayi(GA['2026-07']['reprice'], 2)}'den {sayi(GA['2026-09']['reprice'], 2)} yıla çıktı", "tez gerçekleşen")
    metinde(m, f"Temmuz''da {sayi(GA['2026-07']['aov'], 2)}, Ağustos''ta {sayi(GA['2026-08']['aov'], 2)}, Eylül''de "
               f"{sayi(GA['2026-09']['aov'], 2)} yıl", "açıklama gerçekleşen")
    metinde(m, f"hedefi {sayi(ek_e['hedef'])}'den {sayi(ek['hedef'])} milyar TL'ye ({yz(FK['2026-10']['hedef_yuzde'])}), doğrudan "
               f"satış {sayi(ek_e['dogrudan'])}'dan {sayi(ek['dogrudan'])}'a", "özet ne değişti")
    metinde(m, f"ihale ve doğrudan satış programı ({sayi(OD['ekim_7_program_mlr'])} milyar TL) o gün valörlü", "özet 7 Ekim")
    metinde(m, f"ortalaması {sayi(FT['yil26']['dogrudan'])} milyar TL; <b>istisna {sayi(mn[0])} ile Eylül'dü</b>", "özet doğrudan")
    metinde(m, f"Ekim {sayi(va10['aov_fark'], 2, True)} yıl (valörün yedi gün öne alınması), Kasım "
               f"{sayi(V['aylik']['2026-11']['aov_fark'], 2, True)}", "özet plan vadesi")
    metinde(m, f"<b>Temmuz {sayi(GA['2026-07']['aov'], 2)}, Ağustos {sayi(GA['2026-08']['aov'], 2)}, Eylül "
               f"{sayi(GA['2026-09']['aov'], 2)} yıl</b>; Eylül için 31 Ağustos tahminimiz {sayi(EY['aov_plan_yazi'], 2)}", "özet vade")
    metinde(m, f"TLREF payı Temmuz'da {yz(GA['2026-07']['tlref_pay'])}, Ağustos'ta {yz(GA['2026-08']['tlref_pay'])}, Eylül'de "
               f"{yz(GA['2026-09']['tlref_pay'])}; yeniden fiyatlama vadesi {sayi(GA['2026-07']['reprice'], 2)}'den "
               f"{sayi(GA['2026-08']['reprice'], 2)} ve {sayi(GA['2026-09']['reprice'], 2)} yıla", "özet faiz riski")
    metinde(m, f"(Ekim {sayi(va10['reprice_karsi'], 2)} → {sayi(va10['reprice'], 2)} yıl)", "özet aynı ay")
    metinde(m, f"hedefin kalanını, {sayi(HD['kalan_mlr'])} milyar TL'yi tam sattı (ay {yz(HD['oran_ham'], 2)})", "özet Eylül")
    metinde(m, f"rekabetçi teklifin {yz(y5_e['rekabetci_kabul'])} ve {yz(y8_e['rekabetci_kabul'])}'i kabul edildi, 2025–2026'nın en "
               f"yükseği; TLREF'teki {yz(tl_e['rekabetci_kabul'])} olağandı (medyan {yz(TK['diger_medyan'])})", "özet kabul")
    metinde(m, f"(483 gün) arşivin en uzun kuponsuzu; beklenen satış {sayi(A['kuponsuz_mlr'])} milyar TL, planın {yz(A['kuponsuz_pay'])}'ü",
            "özet kısa uç")
    metinde(m, f"Sonra {TT['ekim_bosluk'] - 1} gün ihale yok", "özet ihalesiz gün")
    metinde(m, f"<li><b>{yz(ek['dogrudan_pay'])}</b>", "şerit doğrudan")
    metinde(m, f"<li><b>{TT['ekim_bosluk']} gün</b>", "şerit boşluk")
    metinde(m, f"<li><b>{sayi(va10['aov'], 2)} yıl</b><span>Ekim'in planlı vadesi (önceki takvim {sayi(va10['aov_karsi'], 2)})", "şerit plan vadesi")
    metinde(m, f"<li><b>{sayi(GA['2026-09']['aov'], 2)} yıl</b><span>Eylül'ün gerçekleşen vadesi (Temmuz {sayi(GA['2026-07']['aov'], 2)})", "şerit Eylül")
    metinde(m, f"<li><b>{yz(GA['2026-09']['tlref_pay'])}</b><span>Eylül'ün TLREF payı (Temmuz {yz(GA['2026-07']['tlref_pay'])})", "şerit TLREF")
    metinde(m, f"<li><b>{sayi(EY['uzun_sabit_gerc_mlr'])} milyar TL</b><span>15 Eylül'de 5 ve 8 yıllıktan satılan", "şerit uzun sabit")
    dogru(abs(EY["uzun_sabit_gerc_mlr"] - HD["gun15_mlr"]) < 0.06, "15 Eylül satışı 5 ve 8 yıllığın toplamı değil")
    metinde(m, f"<li><b>{son_k['gun']} gün</b>", "şerit kuponsuz")


def sat_plan(itfa: str, V: dict) -> float:
    """Ekim'deki plan satırının beklenen tutarı (izleme listesi)."""
    return next(r["g_mlr"] for r in V["satirlar"] if r["itfa"] == itfa and r["gun"].endswith(".10.2026"))


# ─────────────────────────────────────────────── 4 · figürler
def figurler() -> None:
    m = MDX.read_text(encoding="utf-8")
    kaynak = (BURASI / "sekil.py").read_text(encoding="utf-8")
    liste = re.findall(r'"(\d\d_[a-z_]+)"', kaynak[kaynak.index("SEKILLER"):kaynak.index("]", kaynak.index("SEKILLER"))])
    if len(liste) != 8:
        hatalar.append(f"figür listesi {len(liste)} öğe, beklenen 8")
    for ad in liste:
        if not (SEKIL / f"{ad}.html").exists():
            hatalar.append(f"figür yok: {ad}.html")
        if f"/analiz/{SLUG}/{ad}.html" not in m:
            hatalar.append(f"figür metinde gömülü değil: {ad}")
    gomulu = re.findall(r'<GrafikEmbed src="/analiz/' + SLUG + r'/(\d\d_[a-z_]+)\.html"[^>]*no="(\d\d)"', m)
    if [n for _, n in gomulu] != [f"{i:02d}" for i in range(1, len(gomulu) + 1)]:
        hatalar.append(f"şekil numaraları sıralı değil: {[n for _, n in gomulu]}")
    # Figürün İÇİNDEKİ başlık numarası, sayfanın ona verdiği numarayla aynı olmalı:
    # okur "Şekil 03" başlıklı kutunun içinde "Şekil 02" okursa yazıyla figür
    # birbirini gösteremez. Dosya öneki de aynı numarayı taşır.
    for ad, no in gomulu:
        yol = SEKIL / f"{ad}.html"
        if not ad.startswith(no + "_"):
            hatalar.append(f"figür dosyasının öneki gömme numarasıyla aynı değil: {ad} · no {no}")
        # Plotly başlığı JSON içinde \u kaçışıyla yazar ("Şekil 01 —"):
        # iki yazım da aranır, yoksa kapı her figürde yanlış alarm verir.
        if yol.exists():
            html = yol.read_text(encoding="utf-8")
            if f"Şekil {no} —" not in html and f"\\u015eekil {no} \\u2014" not in html:
                hatalar.append(f"figürün içindeki başlık 'Şekil {no}' değil: {ad}")


def main() -> int:
    o = arsiv()
    bg = belgeden(o)
    metin(o, bg)
    figurler()
    if hatalar:
        print(f"✗ Borçlanma programı yazısı · {len(hatalar)} hata")
        for h in hatalar[:80]:
            print("  ·", h)
        return 1
    print(f"✓ Borçlanma programı yazısı · {sayac['belge']} belge ölçütü, {sayac['hucre']} tablo hücresi, "
          f"{sayac['metin']} metin parçası, 8 figür")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
