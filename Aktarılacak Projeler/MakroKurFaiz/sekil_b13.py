#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 13 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden).

Şekil 24 matrisin ısı haritasıdır. Hücreler çubuk izi olarak çizilir, çünkü ısı haritası
desen (tarama) taşımaz: ölçülen hücre renkli (eş hareket korelasyonu), vaka hücresi açık
renk ve noktalı, kaynaklı hücre çapraz taralı, kurulmayan hücre boş. Matris iki alt panele
bölünür (DM tarafının ve EM tarafının rejimleri): iki tarafta korelasyonun ölçtüğü seriler
farklıdır ve dar ekranda altı sütun yan yana okunmaz.

Ölçülen hücrede ikinci bir soru daha görünür: olay günü korelasyonu aynı rejimin sıradan
günlerinden ayrışıyor mu (Fisher z, |z| ≥ 2 → kalın çerçeve). Başlığın bulgusu bu ayrımdan
kurulur, çünkü işaretin kendisi çoğu hücrede sıradan günlerde de aynıdır: "olay günü şu
yönde" demek, olay gününe özgü bir eş hareket iddiası değildir.
"""
from __future__ import annotations

import re

from sekil_ortak import (ALT_EM, BASLIK_EM, sar, ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)

# Satır (şok) ve sütun (rejim) etiketleri — tam adlar ölçümden gelir, burada yalnız dar
# ekranda sığan kısa yazım durur. Tanınmayan kimlik ölçümdeki tam adıyla basılır.
_SOK_KISA = {
    "butce": "Bütçe / borçlanma", "gsyh": "GSYH, PMI/ISM", "istihdam": "İstihdam", "tufe": "TÜFE",
    "para": "Para politikası", "cari": "Cari denge", "rezerv": "Haftalık rezerv", "not": "Not kararı",
    "emtia": "Emtia / enerji", "kuresel": "Küresel risk (VIX)",
}
_REJIM_KISA = {
    "R1": "normal", "R2": "mali kaygı", "R3": "güvenilir MB", "R4": "mali baskı",   # dar sütun: tam ad ipucunda
    "R5_DM": "riskten kaçış", "R5_EM": "riskten kaçış",
}
_TARAF = {
    "dm": ("DM tarafı", "2 yıllık × dolar",
           "DM tarafı: ABD 2 yıllık getiri × doların değeri (G10 sepeti); bütçe ve not satırlarında "
           "ABD vakaları, bütçede ayrıca İngiltere (gilt × sterlin)"),
    "em": ("EM tarafı", "2 yıllık × TL",
           "EM tarafı: DİBS 2 yıllık getiri × TL'nin değeri (USD/TRY'nin tersi); bütçe satırında "
           "euro çevresi vakaları (ülke 2 yıllığı × euro)"),
}
_SERI = (("kur", "kur"), ("2y", "2 yıllık"), ("uzun", "uzun uç"), ("egim", "eğim"))
_KADRAN = {"politika": "politika (faiz ↑, para ↑)", "prim": "prim (faiz ↑, para ↓)",
           "gevseme": "gevşeme (faiz ↓, para ↓)", "guvenli_liman": "güvenli liman (faiz ↓, para ↑)",
           "prim_dusus": "prim düşüşü (faiz ↓, para ↑)"}
_PARA = {"dm": "dolar", "em": "TL"}
# Ölçülen hücrenin olay türü, başlık cümlesinde okurun tanıdığı adıyla (para satırının DM yüzü
# FOMC kararları, EM yüzü PPK kararlarıdır; pencere notu "karar günü (14:00 New York / TSİ)").
_OLAY_AD = {("para", "dm"): "FOMC", ("para", "em"): "PPK",
            ("kuresel", "dm"): "VIX sıçraması", ("kuresel", "em"): "VIX sıçraması"}
_AYRISMA_Z = 2.0                     # Fisher z: |z| ≥ 2 ayrışma sayılır (ölçümün kendi ölçütü)

# Durum → çizim. Renk ölçülen büyüklüğü yalnız ölçülen hücrede taşır; öbür durumlar desendir.
_KENAR = "#cfc9bd"
_VAKA_ZEMIN = "rgba(184,134,11,0.13)"
_SOLUK = "#6f6a62"                   # kurulmadı yazısı: soluk ama beyaz zeminde okunur (≥ 4,5:1)
_DURUM = {
    "olculdu": "ölçüldü",
    "olculdu+": "ölçüldü, artı: faiz ↑ para ↑",
    "olculdu-": "ölçüldü, eksi: faiz ↑ para ↓",
    "ayrisan": "kalın çerçeve: korelasyon sıradan günden farklı (|z| ≥ 2)",
    "olculdu_es_hareket_yok": "ölçüldü, eş hareket kurulmadı",
    "vaka": "vaka (1–9 olay; korelasyon yazılmaz)",
    "kaynak": "kaynak (bölüm kaynakla anlatır; sebebi notta)",
    "kurulmadi": "kurulmadı (sebebi hücrenin notunda)",
}
_LEJANT_SIRA = {"olculdu+": 1, "olculdu-": 2, "ayrisan": 3, "olculdu_es_hareket_yok": 4, "vaka": 5,
                "kaynak": 6, "kurulmadi": 7}
_OLCEK = [[0.0, CLARET], [0.5, "#f1eee8"], [1.0, MAVI]]


def _parlaklik(renk: str) -> float:
    """WCAG göreli parlaklığı (#rrggbb)."""
    def kanal(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * kanal(r) + 0.7152 * kanal(g) + 0.0722 * kanal(b)


def _yazi_rengi(zemin: str) -> str:
    """Hücre zeminine göre karşıtlığı yüksek olan yazı rengi (beyaz ya da mürekkep)."""
    lz = _parlaklik(zemin)
    beyaz = 1.05 / (lz + 0.05)
    koyu = (max(lz, _parlaklik(MUREKKEP)) + 0.05) / (min(lz, _parlaklik(MUREKKEP)) + 0.05)
    return "white" if beyaz > koyu else MUREKKEP


def _olcek_rengi(r: float) -> str:
    """Ölçekteki rengin r ∈ [−1, 1] noktası (lejant örneği için)."""
    def hx(c):
        return [int(c[i:i + 2], 16) for i in (1, 3, 5)]
    u = (max(-1.0, min(1.0, r)) + 1) / 2
    (u0, c0), (u1, c1) = (_OLCEK[0], _OLCEK[1]) if u <= 0.5 else (_OLCEK[1], _OLCEK[2])
    w = (u - u0) / (u1 - u0)
    a, b = hx(c0), hx(c1)
    return "#" + "".join(f"{round(a[i] + (b[i] - a[i]) * w):02x}" for i in range(3))


def _okur(s: str | None) -> str:
    """Ölçüm notunu okur diline çevirir (iç terimler ve iç atıflar çıkar)."""
    if not s:
        return ""
    s = s.replace("plasebo sınaması: ", "").replace("kurulmadı (plasebo)", "kurulmadı (plasebo sınaması)")
    s = s.replace("dört serinin hiçbiri plasebo sınamasını geçmedi",
                  "dört serinin (kur, 2 yıllık, uzun uç, eğim) hiçbirinde olay penceresindeki hareket "
                  "plasebo sınamasını geçmedi")
    s = s.replace("plasebo sınamasını", "plasebo sınamasını").replace("arşivde yok", "elde yok")
    s = re.sub(r"\s*\(tuzak \d+\)", "", s)
    s = re.sub(r"\s*\(BLS yayım arşivi elde yok\)", "", s)
    return s


_ADLAR = ("İngiltere", "Fitch", "Moody's", "İtalya", "İspanya")


def _vaka_notu(h: dict) -> str:
    """Hücre notunu o hücrenin vakalarına indirger: notun, hücrede bulunmayan bir vakayı anan
    yan cümlesi düşer (not aynı tarafın bütün hücrelerinde ortaktır). Dışlama cümlesi kalır."""
    ham = _okur(h.get("not"))
    if not ham:
        return ""
    vakalar = " ".join(f"{v.get('ad', '')} {v.get('ulke', '')}" for v in h.get("vakalar") or [] if isinstance(v, dict))
    kalan = []
    for cumle in re.split(r"(?<=\.)\s+", ham):
        parca = []
        for yan in cumle.rstrip(".").split("; "):
            yok = [a for a in _ADLAR if a in yan and a not in vakalar]
            if yok and "girmedi" not in yan:
                continue
            yan = yan.replace("satırları", "pencereleri").replace("satırı", "penceresi")
            parca.append(yan + " sütuna yazıldı" if yan.endswith("etiketiyle") else yan)
        if parca:
            kalan.append("; ".join(parca) + ".")
    return " ".join(kalan)


def _baslik_yeri(baslik: str) -> dict:
    """Başlık bloğu üstten çapalanır (kendiliğinden yerleşince alt başlık sütun başlıklarına binebiliyordu)
    ve ev stilinin üst payı içinde ORTALANIR: pay satır başına 26 piksel büyür (92 + 26·satır + 26),
    blok satır başına ~19,7 piksel tutar; fark üstte bırakılırsa alt başlıkla ızgara arasında boşluk
    büyür. 33 piksel: pad 48'de bloğun ölçülen üst kenarı; 30 piksel: sütun başlıkları."""
    satir = baslik.count("<br>") + 1
    pay = 92 + 26 * baslik.count("<br>") + 26
    kaydir = max(0.0, (pay - 30 - 2 * 33 - 19.7 * satir) / 2)
    return dict(text=baslik, y=1, yref="container", yanchor="top", pad=dict(t=int(48 + kaydir)))


def _sar(metin: str, en: int = 60) -> str:
    """Hover satırlarını sözcük sınırında böler (dar ekranda kutu taşmasın)."""
    cikti = []
    for satir in metin.split("<br>"):
        parca, uz = [], 0
        for k in satir.split(" "):
            if parca and uz + 1 + len(k) > en:
                cikti.append(" ".join(parca))
                parca, uz = [k], len(k)
            else:
                parca.append(k)
                uz += (1 if len(parca) > 1 else 0) + len(k)
        cikti.append(" ".join(parca))
    return "<br>".join(cikti)


def _imzali(x: float, b: int = 2) -> str:
    return ("+" if x > 0 else "") + vir(x, b)


def _aralik(h: dict) -> str:
    """Olayların tarih aralığı; aylık pencerede ay olarak, tek olayda tek tarih olarak."""
    if not (h.get("ilk") and h.get("son")):
        return ""
    yaz = ay if re.search(r"\bayı\b", h.get("pencere") or "") else tarih
    a, b = yaz(h["ilk"]), yaz(h["son"])
    return a if a == b else f"{a}–{b}"


def _oranlar(h: dict) -> str:
    o = h.get("oranlar") or {}
    if not o:
        return ""
    parca, kurulmayan = [], []
    for k, ad in _SERI:
        v = o.get(k)
        if isinstance(v, (int, float)):
            parca.append(f"{ad} {vir(v, 2)}")
        elif v is not None:
            kurulmayan.append(ad)
    s = "olay / sıradan dönem ortalama |değişim| oranı: " + " · ".join(parca) if parca else ""
    if kurulmayan:
        s += ("<br>" if s else "") + ", ".join(kurulmayan) + ": plasebo sınamasını geçmedi"
    return s


def _kadran(k: str | None, taraf: str, y2: float | None = None) -> str:
    if not k:
        return "2 yıllık serisi yok"
    if k == "sifir":                                 # işaret çarpımı sıfır: kadran tanımsız
        return "kadran yok (2 yıllık kımıldamadı)" if y2 == 0 else "kadran yok (para kımıldamadı)"
    if taraf == "em" and k == "guvenli_liman":
        k = "prim_dusus"
    return _KADRAN.get(k, k)


def _vakalar(h: dict, taraf: str) -> list[str]:
    para = _PARA[taraf]
    satir = []
    for v in h.get("vakalar") or []:
        if isinstance(v, list):                      # tek günlük olay: [gün, 2y bp, para %, kadran]
            gun, y2, p, kd = v
            satir.append(f"• {tarih(gun)}: 2 yıllık {_imzali(y2, 1)} bp, {para} "
                         f"{yuzde(p, 2, arti=True)} → {_kadran(kd, taraf, y2)}")
        else:                                        # çok günlük vaka penceresi
            satir.append(f"• {v['ad']} ({tarih(v['ilk'])}–{tarih(v['son'])}): {_kadran(v.get('kadran_2y'), taraf)}")
    return satir


def _euro_cevresi(h: dict) -> bool:
    """EM tarafının bütçe pencereleri Türkiye değil euro çevresidir (kur bacağı euro)."""
    return "euro" in ((h.get("birim") or {}).get("kur") or "")


_YONETILEN = ""                      # yönetilen kur döneminin ay aralığı; s21_matris ölçümden doldurur


def _yonetilen_donemi(o: dict) -> str:
    """Bölüm 1'in yönetilen kur notundaki ay aralığı ("2021-12…2023-06" → "12.2021–06.2023")."""
    m = re.search(r"(\d{4})-(\d{2})\s*…\s*(\d{4})-(\d{2})", o["b01"]["p1b"].get("yonetilen_kur_notu") or "")
    return f"{m[2]}.{m[1]}–{m[4]}.{m[3]}" if m else ""


def _yonetilen(h: dict) -> str:
    """EM olay hücresinde yönetilen kur döneminin olayları kur bacağına girmez (adıyla)."""
    n, ne, ny = h.get("n") or 0, h.get("n_es"), h.get("n_yonetilen")
    if ny and ne is not None and ne != n:
        donem = f" ({_YONETILEN})" if _YONETILEN else ""
        return (f"{ny} olay yönetilen kur döneminde{donem}: kur bacağına ve eş harekete girmedi; "
                f"eş hareket {ne} olayda")
    return ""


def _hover(sok: str, sok_ad: str, rejim_ad: str, h: dict, desen: str, taraf: str, imza: float | None) -> str:
    bas = f"<b>{sok_ad}</b><br><b>{rejim_ad}</b>"
    n = h.get("n") or 0
    pencere = h.get("pencere") or ""
    sat = [bas]
    if desen == "olculdu":
        sat.append(f"ölçüldü · {n} olay, {_aralik(h)} · {pencere}")
        sat.append(f"eş hareket ({'ABD 2 yıllık × dolar' if taraf == 'dm' else 'DİBS 2 yıllık × TL'}, korelasyon): "
                   f"{_imzali(h['es_hareket'])}")
        if _yonetilen(h):
            sat.append(_yonetilen(h))
        if h.get("es_hareket_spearman") is not None:
            sat.append(f"sıra korelasyonu {_imzali(h['es_hareket_spearman'])}")
        if h.get("es_hareket_sakin") is not None:
            z = h.get("es_fark_z")
            hukum = ("" if z is None else
                     (" → olay günü sıradan günlerden ayrışıyor" if abs(z) >= _AYRISMA_Z
                      else " → olay günü sıradan günlerden ayrışmıyor"))
            sat.append(f"sıradan günlerde {_imzali(h['es_hareket_sakin'])} ({vir(h['n_sakin'], 0)} gün) · "
                       f"fark (Fisher z) {'—' if z is None else _imzali(z, 1)}; |z| ≥ 2 ayrışma sayılır{hukum}")
        oh = h.get("onceki_hafta") or {}
        if oh.get("es_hareket") is not None:
            sat.append(f"rejim bir önceki haftanın etiketinden alınırsa: {_imzali(oh['es_hareket'])} "
                       f"({oh.get('n_es', oh.get('n'))} olay)")
        if h.get("b_payi") is not None:
            sat.append(f"faiz ile paranın aynı yöne gittiği olay payı {yuzde(h['b_payi'] * 100, 0)}"
                       f" · sıradan günlerde {yuzde(h['b_payi_sakin'] * 100, 0)}")
        o = _oranlar(h)
        if o:
            sat.append(o)
        if sok == "para" and taraf == "em":
            sat.append("not: faiz piyasanın 2 yıllık getirisidir, politika sürprizi değil; güvenilir bir "
                       "artırım risk primini düşürünce 2 yıllık düşüp TL değer kazanabilir. İşaret, kararın kura "
                       "etkisi diye okunmaz.")
        if sok == "kuresel":
            sat.append("not: VIX sıçraması günleri, dolar ve ABD getirisinin büyük oynadığı günlerle aynı anda "
                       "doğar; oranların yüksekliği kısmen bu seçimden gelir.")
    elif desen == "olculdu_es_hareket_yok":
        sat.append(f"ölçüldü · {n} olay, {_aralik(h)} · {pencere}")
        sat.append("eş hareket kurulmadı: " + _okur(str(h.get("es_hareket"))))
        o = _oranlar(h)
        if o:
            sat.append(o)
    elif desen == "vaka":
        sat.append(f"vaka · {n} olay" + (f", {_aralik(h)}" if _aralik(h) else "") + " · on olaydan az: korelasyon yazılmaz")
        if taraf == "em" and _euro_cevresi(h):
            sat.append("seriler: Türkiye değil, euro çevresi (ülkenin 2 ve 10 yıllığı × euro)")
        if _yonetilen(h):
            sat.append(_yonetilen(h).replace("eş harekete girmedi; eş hareket", "kadran listesine girmedi; liste"))
        if imza is not None:
            sat.append(f"2 yıllık × para kadran dengesi (aynı yön − ters yön) / kadranı belli olay: "
                       f"{_imzali(imza)}; test değil")
        sat += _vakalar(h, taraf)
        o = _oranlar(h)
        if o:
            sat.append(o)
        vn = _vaka_notu(h)
        if vn:
            sat.append("not: " + vn)
    elif desen == "kaynak":
        bol = h.get("kaynak_bolum")
        sat.append("kaynak · bu veriyle kurulamadı; dersin kaynak listesi kapsıyor" + (f" ({bol})" if bol else ""))
        sat.append("sebep: " + _okur(h.get("olcum_denemesi") or h.get("not")))
        if n:
            sat.append(f"denenen ölçüm: {n} olay, {_aralik(h)} · {pencere}")
    else:
        sat.append("kurulmadı · " + _okur(h.get("not")))
        if n:
            sat.append(f"denenen ölçüm: {n} olay, {_aralik(h)} · {pencere}")
    return _sar("<br>".join(sat))


def _hucre_yazisi(desen: str, h: dict) -> str:
    if desen == "olculdu":
        return f"<b>{_imzali(h['es_hareket'])}</b> ölçüldü"
    if desen == "olculdu_es_hareket_yok":
        return "ölçüldü"
    if desen == "vaka":
        return f"vaka · {h['n']}"
    if desen == "kaynak":
        return "kaynak"
    return "kurulmadı"


def _olay_araligi(m: dict) -> tuple[str, str]:
    """Matrisin çizdiği olayların ilk ve son günü: hücrelerin kendi aralıkları ve vaka pencereleri."""
    gunler = []
    for satir in m.values():
        for h in satir.values():
            for k in ("ilk", "son"):
                if h.get(k):
                    gunler.append(h[k][:10])
            for v in h.get("vakalar") or []:
                if isinstance(v, list):
                    gunler.append(v[0][:10])
                else:
                    gunler += [v["ilk"][:10], v["son"][:10]]
    return min(gunler), max(gunler)


def _baslik_bulgusu(olcu: list[dict]) -> list[str]:
    """Başlığın bulgu yarısı (satır parçaları), ölçülen hücrelerden: olay günü eş hareketi sıradan
    günlerden hangi hücrelerde ayrışıyor (Fisher z, |z| ≥ 2) ve orada işaret ne."""
    ayr = [x for x in olcu if x["z"] is not None and abs(x["z"]) >= _AYRISMA_Z]
    if not olcu:
        return ["hiçbir hücrede eş hareket ölçülemedi"]
    if not ayr:
        return ["hiçbir hücrede olay günü eş hareketi", "sıradan günlerden ayrışmıyor"]
    if len({(x["sok"], x["taraf"]) for x in ayr}) == 1 and len({x["r"] > 0 for x in ayr}) == 1:
        x = ayr[0]
        ad = _OLAY_AD.get((x["sok"], x["taraf"]), _SOK_KISA.get(x["sok"], x["sok"]))
        yon = "aynı yönde" if x["r"] > 0 else "ters yönde"
        return [f"yalnız {ad} günlerinin eş hareketi sıradan günlerden",
                f"ayrışıyor: 2 yıllık faiz ile {_PARA[x['taraf']]} {yon}"]
    return [f"olay günü eş hareketi {len(ayr)} hücrede", "sıradan günlerden ayrışıyor"]


def s21_matris(o: dict) -> None:
    global _YONETILEN
    _YONETILEN = _yonetilen_donemi(o)
    b = o["b13"]
    s = b["sekil_21"]
    m = b["matris"]
    ozet = b["matris_ozeti"]
    tanim = {c["kimlik"]: c for c in b["matris_tanim"]["sutunlar"]}
    satirlar, sutunlar = s["satirlar"], s["sutunlar"]
    sok_ad = dict(zip(satirlar, s["satir_ad"]))
    rejim_ad = dict(zip(sutunlar, s["sutun_ad"]))
    taraflar = [t for t in ("dm", "em") if any(tanim[c]["taraf"] == t for c in sutunlar)]
    kolonlar = {t: [c for c in sutunlar if tanim[c]["taraf"] == t] for t in taraflar}
    ns = len(satirlar)

    fig = make_subplots(rows=len(taraflar), cols=1, vertical_spacing=0.085)
    gorulen_durum = set()
    ann = []
    olcu = []                                    # ölçülen hücreler: başlığın bulgusu buradan kurulur
    for p, t in enumerate(taraflar, start=1):
        kol = kolonlar[t]
        kume = {}
        for i, sk in enumerate(satirlar):
            for j, c in enumerate(kol):
                jj = sutunlar.index(c)
                desen = s["desen"][i][jj]
                h = m[sk][c]
                rad = f"{c.replace('_DM', '').replace('_EM', '')} · {rejim_ad[c]}"
                k = kume.setdefault(desen, {"x": [], "base": [], "renk": [], "yazi": [], "yrenk": [],
                                            "hover": [], "kalin": []})
                k["x"].append(j)
                k["base"].append(i - 0.46)
                k["yazi"].append(_hucre_yazisi(desen, h))
                # Para satırının iki yüzü ayrı olay listesidir: DM'de FOMC, EM'de PPK kararları.
                had = f"Para politikası ({_OLAY_AD[(sk, t)]} kararları)" if sk == "para" else sok_ad[sk]
                k["hover"].append(_hover(sk, had, rad, h, desen, t, s["vaka_imza"][i][jj]))
                if desen == "olculdu":
                    r = s["es_hareket"][i][jj]
                    z = h.get("es_fark_z")
                    ayrisiyor = z is not None and abs(z) >= _AYRISMA_Z
                    olcu.append({"sok": sk, "kol": c, "taraf": t, "r": r, "z": z})
                    k["renk"].append(r)
                    k["yrenk"].append(_yazi_rengi(_olcek_rengi(r)))
                    k["kalin"].append(3.2 if ayrisiyor else 1.0)
                else:
                    k["yrenk"].append({"kurulmadi": _SOLUK, "kaynak": "#5f594f"}.get(desen, MUREKKEP))
        for desen in ("olculdu", "olculdu_es_hareket_yok", "vaka", "kaynak", "kurulmadi"):
            if desen not in kume:
                continue
            k = kume[desen]
            if desen == "olculdu":
                marker = dict(color=k["renk"], colorscale=_OLCEK, cmin=-1, cmax=1,
                              line=dict(color=MUREKKEP, width=k["kalin"]), showscale=False)
                # Renk dizisi lejantta boş görünür; her hücre değerini yazdığı için sürekli ölçek
                # yerine yön lejantta iki örnekle verilir (yalnız ölçülen işaretler); kalın çerçeve
                # (olay günü sıradan günlerden ayrışıyor) kendi öğesiyle.
                for isaret, r0 in (("olculdu+", 0.6), ("olculdu-", -0.6)):
                    if isaret in gorulen_durum or not any((r > 0) == (r0 > 0) for r in k["renk"] if r):
                        continue
                    fig.add_trace(go.Bar(x=[None], y=[None], name=_DURUM[isaret], legendgroup=isaret,
                                         legendrank=_LEJANT_SIRA[isaret],
                                         marker=dict(color=_olcek_rengi(r0), line=dict(color=MUREKKEP, width=1)),
                                         hoverinfo="skip"), p, 1)
                    gorulen_durum.add(isaret)
                if "ayrisan" not in gorulen_durum and any(w > 1 for w in k["kalin"]):
                    fig.add_trace(go.Bar(x=[None], y=[None], name=_DURUM["ayrisan"], legendgroup="ayrisan",
                                         legendrank=_LEJANT_SIRA["ayrisan"],
                                         marker=dict(color="white", line=dict(color=MUREKKEP, width=3.2)),
                                         hoverinfo="skip"), p, 1)
                    gorulen_durum.add("ayrisan")
            elif desen == "olculdu_es_hareket_yok":
                marker = dict(color="white", line=dict(color=MUREKKEP, width=1.2))
            elif desen == "vaka":
                marker = dict(color=_VAKA_ZEMIN, line=dict(color="#d9c79a", width=1),
                              pattern=dict(shape=".", fgcolor="rgba(184,134,11,0.55)", size=6, solidity=0.12))
            elif desen == "kaynak":
                marker = dict(color="white", line=dict(color="#a39b8c", width=1),
                              pattern=dict(shape="x", fgcolor="#a39b8c", bgcolor="white", size=7, solidity=0.16))
            else:
                marker = dict(color="white", line=dict(color=_KENAR, width=1))
            fig.add_trace(go.Bar(
                x=k["x"], y=[0.92] * len(k["x"]), base=k["base"], width=0.94, marker=marker,
                name=_DURUM[desen], legendgroup=desen, legendrank=_LEJANT_SIRA.get(desen, 9),
                showlegend=desen not in gorulen_durum and desen != "olculdu",
                text=k["yazi"], textposition="inside", insidetextanchor="middle", textangle=0,
                textfont=dict(color=k["yrenk"], size=11), customdata=k["hover"], constraintext="inside",
                hovertemplate="%{customdata}<extra></extra>"), p, 1)
            gorulen_durum.add(desen)
        # Sütun başlıkları (panelin üstünde) ve köşe hücresi (tarafın adı ve korelasyonun serileri)
        ust = fig.layout["yaxis" if p == 1 else f"yaxis{p}"].domain[1]
        xr = "x" if p == 1 else f"x{p}"
        for j, c in enumerate(kol):
            kod = c.replace("_DM", "").replace("_EM", "")
            ann.append(dict(x=j, xref=xr, y=ust, yref="paper", yanchor="bottom", showarrow=False,
                            text=f"<b>{kod}</b><br><span style='font-size:9.5px'>{_REJIM_KISA.get(c, rejim_ad[c])}</span>",
                            font=dict(size=11),
                            hovertext=f"{kod} · {rejim_ad[c]}"))
        ad, alt, uzun = _TARAF[t]
        ann.append(dict(x=0, xref="paper", xanchor="right", xshift=-8, y=ust, yref="paper", yanchor="bottom",
                        showarrow=False, align="right", text=f"<b>{ad}</b><br>{alt}", font=dict(size=11),
                        hovertext=uzun))
        fig.update_xaxes(visible=False, range=[-0.5, len(kol) - 0.5], row=p, col=1)
        fig.update_yaxes(range=[ns - 0.5, -0.5], tickvals=list(range(ns)),
                         ticktext=[_SOK_KISA.get(sk, sok_ad[sk]) for sk in satirlar],
                         showgrid=False, ticks="", showline=False, ticklabelstandoff=6, row=p, col=1)

    say = ozet["durum_sayisi"]
    ilk, son = _olay_araligi(m)
    # Başlık ve alt başlık dar ekrana göre sarılır (Plotly başlığı sarmaz): ortak ölçü (sekil_ortak.sar,
    # telefonun gömme çerçevesine göre em cinsinden). Ev stili üst boşluğu satır sayısından kurar.
    parca = [f"Şekil 24 — {ozet['hucre']} hücreden {say.get('olculdu', 0)} hücre ölçülebildi;"] + _baslik_bulgusu(olcu)
    baslik = "<br>".join(s for x in parca for s in sar(x, BASLIK_EM))
    alt = [
        "ABD Hazinesi, CNBC, Yahoo Finance, TCMB, TÜİK, Fed, Dünya Bankası",
        f"olay günü, haftası ya da ayı, {tarih(ilk)}–{tarih(son)}; rejim o haftanın etiketi",
        "ölçüldü: en az on olay ve plasebo sınamasını geçen en az bir seri",
        "renk: olay günlerinde 2 yıllık faiz ve para değeri değişimlerinin korelasyonu",
        "para: DM'de dolar (G10 sepetine karşı), EM'de TL (USD/TRY'nin tersi)",
    ]
    alt = [s for x in alt for s in sar(x, ALT_EM)]
    fig.update_layout(
        barmode="overlay", bargap=0, annotations=list(fig.layout.annotations) + ann,
        # Başlık bloğu çerçevenin üst kenarına üstten çapalanır: ev stili üst boşluğu satır başına
        # sabit payla kurar ve blok kendiliğinden yerleşince son alt başlık satırları sütun
        # başlıklarının üstüne biniyordu. Üstten çapada blok aşağı doğru akar ve pay ona yeter.
        title=_baslik_yeri(baslik + "<br><sub>" + "<br>".join(alt) + "</sub>"),
        hoverlabel=dict(align="left"),
    )
    _yaz(fig, "24_matris.html", 900)
