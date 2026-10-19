#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oyun planı bacaklarının bid/ask simülatörü — gözlemde ve sınamada AYNI kod.

Bir BACAK, bir anın bir ilk mum sınıfına verilen tepkidir: nereden girilir (limit, kırılım emri ya da piyasa),
stop nereye, hedef nereye, emir ne kadar bekler, pozisyon en geç ne zaman kapanır. Bacak türleri:

- katil     : ilk mumun yönünde, mumun ORTA noktasına limit (geri çekilmede katıl). Stop mumun öbür ucunun
              ötesinde (tampon kadar). Reddedilen mumda yön reddin yönüdür.
- kirilim   : küçük ilk mumun iki ucuna kırılım emri; önce tetiklenen geçerli, öbürü iptal. Stop öbür uç.
- fiks_ver  : fiksing anında, fiksinge kadar süren koşunun TERSİNE piyasa emri; stop koşunun ucunun ötesinde.
- devam     : ilk mumun kapanışında, mumun yönünde piyasa emri; stop mumun öbür ucunun ötesinde.

Hedef üç biçimde yazılır: "uc" (ilk mumun kendi ucu), "orta" (ilk mumun orta noktası) ya da planlanan riskin
katı (ör. 1.0 = 1R). Emir dolmazsa işlem yoktur. Pozisyon pencerenin sonunda piyasa emriyle kapanır.

Dolum kuralları (kötümser):
- Alış emri ask'tan, satış emri bid'den dolar. Limit emir fiyatına (dakika o fiyatın ötesinde açıldıysa açılış
  fiyatına) dolar, kayma yoktur. Piyasa, stop ve kırılım emirleri `kayma` kadar kötü dolar; haber penceresinde
  (olaydan 2 dk önce – 15 dk sonra) `haber_kayma` eklenir.
- Dolum dakikasında hedef sayılmaz, stop sayılır. Bir dakikada hem stop hem hedef görülürse stop sayılır.
- R, PLANLANAN riskle ölçülür (planlanan giriş ile stop arası); boşlukla dolan bir emir R'yi şişirmez.

Maliyetsiz sonuç (`brut`) aynı kuralların orta fiyatla, makas ve kayma olmadan yeniden simülasyonudur. (İlk yazımda
maliyetsiz sonuç gerçek işlemin seviyelerinden kuruluyordu ve kırılım emrinin girişini tetik dakikasının açılışından
alıyordu; bu, kırılımda ~0,2 R'lik sahte bir maliyetsiz kenar üretti. Net sonuç o değişiklikten etkilenmez.)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import sinif as sf

KAYMA_PIP = 0.5
HABER_KAYMA_PIP = 1.0
HABER_PENCERE = (-2, 15)        # dk
EN_AZ_RISK_PIP = 3.0            # planlanan risk bundan küçükse işlem yok (makas R'yi yutar)


@dataclass(frozen=True)
class Bacak:
    tur: str                    # katil · kirilim · fiks_ver · devam
    hedef: str | float          # "uc" · "orta" · riskin katı
    tampon: float = 0.1         # stopun ilk mum ucunun ötesindeki payı, ilk mum aralığı R cinsinden
    bekle: int = 60             # emrin geçerlilik süresi (dk), izleme başlangıcından


def _ilk(m: np.ndarray) -> int:
    return int(np.argmax(m)) if m.any() else -1


def _haber_mi(e: dict, t: int) -> bool:
    an = sf.AN[e["an"]]
    if an.aile not in ("veri", "mb"):
        return False
    return HABER_PENCERE[0] * 60 <= t - e["t0"] <= HABER_PENCERE[1] * 60


def emir(e: dict, b: Bacak) -> dict | None:
    """Olay + bacak → emir (yön, giriş türü ve fiyatı, stop, hedef). Uygun değilse None."""
    o, h, l, c, R, s = e["o"], e["h"], e["l"], e["c"], e["h"] - e["l"], e["yon"]
    orta = (h + l) / 2
    if b.tur in ("katil", "devam"):
        if s == 0:
            return None
        y = s
        giris = orta if b.tur == "katil" else None
        stop = (l - b.tampon * R) if y > 0 else (h + b.tampon * R)
        ref = giris if giris is not None else c
        kendi_uc = h if y > 0 else l
    elif b.tur == "fiks_ver":
        if s == 0:
            return None
        y, giris = -s, None
        stop = (h + b.tampon * R) if s > 0 else (l - b.tampon * R)
        ref, kendi_uc = c, None
    elif b.tur == "kirilim":
        return {"tur": "kirilim", "ust": h, "alt": l, "R": R, "hedef": b.hedef, "tampon": b.tampon}
    else:
        raise ValueError(b.tur)
    risk = abs(ref - stop)
    if b.hedef == "uc":
        hedef = kendi_uc
    elif b.hedef == "orta":
        hedef = orta
    else:
        hedef = ref + y * float(b.hedef) * risk
    if hedef is None or (hedef - ref) * y <= 0:
        return None
    return {"tur": "limit" if giris is not None else "piyasa", "y": y, "giris": giris, "stop": stop,
            "hedef": hedef, "risk": risk}


def simule(d, e: dict, b: Bacak, kayma_pip: float = KAYMA_PIP,
           haber_kayma_pip: float = HABER_KAYMA_PIP) -> dict | None:
    """Tek olayın tek bacağı. Dönüş: None (emir yok / dolmadı) ya da işlem kaydı."""
    em = emir(e, b)
    if em is None:
        return None
    pip = e["pip"]
    kayma = kayma_pip * pip
    hk = haber_kayma_pip * pip
    j0, j1 = e["j0"], e["j1"]
    son_giris = min(j1, int(np.searchsorted(d.t, d.t[j0] + b.bekle * 60)))
    t = d.t
    # ── giriş
    if em["tur"] == "kirilim":
        R = em["R"]
        if R < EN_AZ_RISK_PIP * pip:
            return None
        ust = _ilk(d.ah[j0:son_giris] >= em["ust"])
        alt = _ilk(d.bl[j0:son_giris] <= em["alt"])
        if ust < 0 and alt < 0:
            return None
        if ust >= 0 and (alt < 0 or ust < alt):
            y, i, plan = 1, j0 + ust, em["ust"]
        elif alt >= 0 and (ust < 0 or alt < ust):
            y, i, plan = -1, j0 + alt, em["alt"]
        else:
            return None                                    # aynı dakikada iki uç: sıra bilinmez
        ek = kayma + (hk if _haber_mi(e, t[i]) else 0.0)
        giris = (max(plan, d.ao[i]) + ek) if y > 0 else (min(plan, d.bo[i]) - ek)
        stop = (em["alt"] - em["tampon"] * R) if y > 0 else (em["ust"] + em["tampon"] * R)
        risk = abs(plan - stop)
        hedef = plan + y * float(em["hedef"]) * risk
    else:
        y, risk, stop, hedef = em["y"], em["risk"], em["stop"], em["hedef"]
        if risk < EN_AZ_RISK_PIP * pip:
            return None
        if em["tur"] == "limit":
            p = em["giris"]
            k = _ilk(d.al[j0:son_giris] <= p) if y > 0 else _ilk(d.bh[j0:son_giris] >= p)
            if k < 0:
                return None
            i = j0 + k
            giris = min(p, d.ao[i]) if y > 0 else max(p, d.bo[i])
            plan = p
        else:
            i = j0
            ek = kayma + (hk if _haber_mi(e, t[i]) else 0.0)
            giris = (d.ao[i] + ek) if y > 0 else (d.bo[i] - ek)
            plan = d.ao[i] if y > 0 else d.bo[i]
            risk = abs(plan - stop)
            if risk < EN_AZ_RISK_PIP * pip or (hedef - plan) * y <= 0:
                return None
    # ── çıkış (çıkış tarafı: alışta bid, satışta ask)
    if y > 0:
        lo, hi, op, cl = d.bl[i:j1], d.bh[i:j1], d.bo[i:j1], d.bc[i:j1]
        stop_m, hedef_m = lo <= stop, hi >= hedef
    else:
        lo, hi, op, cl = d.al[i:j1], d.ah[i:j1], d.ao[i:j1], d.ac[i:j1]
        stop_m, hedef_m = hi >= stop, lo <= hedef
    hedef_m = hedef_m.copy()
    if len(hedef_m):
        hedef_m[0] = False                                 # dolum dakikasında hedef sayılmaz
    ks, kh = _ilk(stop_m), _ilk(hedef_m)
    if ks >= 0 and (kh < 0 or ks <= kh):
        k = ks
        ek = kayma + (hk if _haber_mi(e, t[i + k]) else 0.0)
        cikis = (min(stop, op[k]) - ek) if y > 0 else (max(stop, op[k]) + ek)
        neden = "stop"
    elif kh >= 0:
        k = kh
        cikis = max(hedef, op[k]) if y > 0 else min(hedef, op[k])
        neden = "hedef"
    else:
        k = len(cl) - 1
        ek = kayma + (hk if _haber_mi(e, t[i + k]) else 0.0)
        cikis = (cl[k] - ek) if y > 0 else (cl[k] + ek)
        neden = "zaman"
    r = (cikis - giris) * y / risk                          # net: makas ve kayma dahil
    return {"cift": e["cift"], "an": e["an"], "t0": e["t0"], "gun": e["gun"], "sinif": e["sinif"],
            "uyum": e["uyum"], "y": int(y), "giris_dk": int(t[i]), "cikis_dk": int(t[i + k]), "neden": neden,
            "R": float(r), "risk_pip": float(risk / pip), "kazandi": bool(r > 0)}


class _Orta:
    """Dakika verisinin orta fiyat görünümü: alış ve satış dizilerinin yerine orta fiyat (kopya yok)."""

    def __init__(self, d):
        self.t, self.pip = d.t, d.pip
        for x in "ohlc":
            m = getattr(d, f"m{x}")
            setattr(self, f"b{x}", m), setattr(self, f"a{x}", m), setattr(self, f"m{x}", m)


def orta(d) -> _Orta:
    return _Orta(d)


def brut(d_orta, e: dict, b: Bacak) -> float | None:
    """Maliyetsiz sonuç: AYNI kurallar orta fiyatla, makas ve kayma olmadan (dolum, stop ve hedef de orta fiyattan
    sorulur). Dönüş: R ya da None (orta fiyatta emir dolmadıysa)."""
    x = simule(d_orta, e, b, kayma_pip=0.0, haber_kayma_pip=0.0)
    return None if x is None else x["R"]
