#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mumdan sonra giriş biçimleri — bid/ask simülatörü (geliştirmede ve sınamada AYNI kod).

Bir GİRİŞ dört şeyle tanımlanır: yön (mumun yönünde "devam" ya da tersine "ters"), emir biçimi, stop ve hedef.
Emir biçimleri (E = mumun kendi ucu, X = öbür ucu, R = aralığı, A = olayın ATR'si, y = mumun yönü):

  devam · piyasa   mum kapanınca, sonraki dakikanın açılışında piyasa emri
  devam · limit_f  mumun ucundan f·R geri çekilme seviyesine limit (f = 0,25 · 0,50 · 0,62); seviye kapanışın
                   geri çekilme tarafında değilse (mum zaten o kadar geri vermişse) emir yok
  devam · stop     ucun bir nokta ötesine stop emri (ucun kırılması)
  devam · onayli   sonraki mum mumun yönünde kapanırsa (kapanışı mumun kapanışının ötesinde), onun kapanışında piyasa
  ters  · piyasa   mum kapanınca, sonraki dakikanın açılışında, mumun tersine piyasa emri
  ters  · limit_uc mumun ucuna limit (uca dönüşü sat/al)
  ters  · limit_ote ucun 0,5·A ötesine limit (uzamayı sat/al)
  ters  · stop     mumun orta noktasına stop emri (mumun yarısının kırılması); kapanış ortanın geri tarafındaysa yok
  ters  · onayli   sonraki mum mumun tersine kapanırsa, onun kapanışında piyasa

Limit ve stop emirleri mum kapandıktan sonra BEKLE mum boyunca geçerlidir. Stop, planlanan girişten k·A (k = 1 · 2);
hedef riskin katı (1 · 2). Ne stop ne hedef görülürse pozisyon izleme penceresinin (24 mum) sonunda kapanır.

Dolum (kötümser, oyun_sim ile aynı kurallar):
- Alış ask'tan, satış bid'den. Limit kendi fiyatına (dakika o fiyatın ötesinde açıldıysa açılışa) kaymasız dolar;
  piyasa ve stop emri 0,5 pip kötü dolar, takvimdeki bir olayın 2 dk öncesi – 15 dk sonrası penceresinde +1 pip.
- Dolum dakikasında hedef sayılmaz, stop sayılır; aynı dakikada ikisi görülürse stop.
- R planlanan riskle ölçülür; planlanan risk 3 pipten küçükse işlem yok.
Maliyetsiz sonuç: AYNI kurallar orta fiyatla, kaymasız (`orta` görünümüyle `simule`).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

KAYMA_PIP = 0.5
HABER_KAYMA_PIP = 1.0
HABER_PENCERE = (-2 * 60, 15 * 60)
EN_AZ_RISK_PIP = 3.0
BEKLE = 6                          # mum
LIMIT_OTE_A = 0.5
TICK = 1.0                          # nokta

DEVAM = ["piyasa", "limit_0.25", "limit_0.5", "limit_0.62", "stop", "onayli"]
TERS = ["piyasa", "limit_uc", "limit_ote", "stop", "onayli"]
STOPLAR = [1.0, 2.0]
HEDEFLER = [1.0, 2.0]


@dataclass(frozen=True)
class Giris:
    yon: str            # devam · ters
    emir: str
    stop: float         # A
    hedef: float        # riskin katı

    @property
    def ad(self) -> str:
        return f"{self.yon}:{self.emir}:s{self.stop:g}:h{self.hedef:g}"


def hepsi() -> list[Giris]:
    return [Giris(y, e, s, h) for y, emirler in (("devam", DEVAM), ("ters", TERS))
            for e in emirler for s in STOPLAR for h in HEDEFLER]


def coz(ad: str) -> Giris:
    y, e, s, h = ad.split(":")
    return Giris(y, e, float(s[1:]), float(h[1:]))


def _ilk(m: np.ndarray) -> int:
    return int(np.argmax(m)) if m.any() else -1


class Orta:
    """Dakika verisinin orta fiyat görünümü (maliyetsiz sonuç için)."""

    def __init__(self, d):
        self.t, self.pip = d.t, d.pip
        for x in "ohlc":
            m = getattr(d, f"m{x}")
            setattr(self, f"b{x}", m), setattr(self, f"a{x}", m), setattr(self, f"m{x}", m)


def _haber(t: int, haber_sn: np.ndarray) -> bool:
    if not len(haber_sn):
        return False
    k = np.searchsorted(haber_sn, t - HABER_PENCERE[1])
    return k < len(haber_sn) and haber_sn[k] <= t - HABER_PENCERE[0]


def emir(d, e: dict, g: Giris) -> dict | None:
    """Olay + giriş → emir: işlem yönü s, tür (piyasa · limit · stop), planlanan fiyat, ilk geçerli dakika j_bas,
    son geçerli dakika j_son. Uygun değilse None."""
    y, c, h, l, A, tf = e["yon"], e["c"], e["h"], e["l"], e["A"], e["tf"]
    if y == 0:
        return None
    R = h - l
    E, orta = (h if y > 0 else l), (h + l) / 2
    s = y if g.yon == "devam" else -y
    j0 = e["j0"]
    j_son = int(np.searchsorted(d.t, e["bt"] + (1 + BEKLE) * tf * 60))
    if g.emir == "piyasa":
        return {"s": s, "tur": "piyasa", "j_bas": j0}
    if g.emir == "onayli":
        sonraki = int(np.searchsorted(d.t, e["bt"] + 2 * tf * 60)) - 1          # sonraki mumun son dakikası
        if sonraki < j0:
            return None
        if s * (d.mc[sonraki] - c) <= 0:
            return None
        return {"s": s, "tur": "piyasa", "j_bas": sonraki + 1}
    if g.emir.startswith("limit_") and g.yon == "devam":
        f = float(g.emir.split("_")[1])
        p = E - y * f * R
        if y * (c - p) <= 0:
            return None
        return {"s": s, "tur": "limit", "fiyat": p, "j_bas": j0, "j_son": j_son}
    if g.emir == "limit_uc":
        if y * (E - c) <= 0:
            return None
        return {"s": s, "tur": "limit", "fiyat": E, "j_bas": j0, "j_son": j_son}
    if g.emir == "limit_ote":
        return {"s": s, "tur": "limit", "fiyat": E + y * LIMIT_OTE_A * A, "j_bas": j0, "j_son": j_son}
    if g.emir == "stop" and g.yon == "devam":
        return {"s": s, "tur": "stop", "fiyat": E + y * TICK, "j_bas": j0, "j_son": j_son}
    if g.emir == "stop" and g.yon == "ters":
        if y * (c - orta) <= 0:
            return None
        return {"s": s, "tur": "stop", "fiyat": orta, "j_bas": j0, "j_son": j_son}
    raise ValueError(g.emir)


def simule(d, e: dict, g: Giris, haber_sn: np.ndarray, kayma_pip: float = KAYMA_PIP,
           haber_kayma_pip: float = HABER_KAYMA_PIP) -> dict | None:
    """Tek olayın tek girişi. Dönüş: None (emir yok / dolmadı) ya da işlem kaydı."""
    em = emir(d, e, g)
    if em is None:
        return None
    pip, t = e["pip"], d.t
    kay, hk = kayma_pip * pip, haber_kayma_pip * pip
    s, j_bas, j1 = em["s"], em["j_bas"], e["j1"]
    if j_bas >= j1:
        return None
    if em["tur"] == "piyasa":
        i = j_bas
        plan = d.ao[i] if s > 0 else d.bo[i]
        ek = kay + (hk if _haber(int(t[i]), haber_sn) else 0.0)
        giris = plan + ek if s > 0 else plan - ek
    else:
        j_son = min(em["j_son"], j1)
        p = em["fiyat"]
        if em["tur"] == "limit":
            k = _ilk(d.al[j_bas:j_son] <= p) if s > 0 else _ilk(d.bh[j_bas:j_son] >= p)
            if k < 0:
                return None
            i = j_bas + k
            giris = min(p, d.ao[i]) if s > 0 else max(p, d.bo[i])
        else:
            k = _ilk(d.ah[j_bas:j_son] >= p) if s > 0 else _ilk(d.bl[j_bas:j_son] <= p)
            if k < 0:
                return None
            i = j_bas + k
            ek = kay + (hk if _haber(int(t[i]), haber_sn) else 0.0)
            giris = (max(p, d.ao[i]) + ek) if s > 0 else (min(p, d.bo[i]) - ek)
        plan = p
    risk = g.stop * e["A"]
    if risk < EN_AZ_RISK_PIP * pip:
        return None
    stop = plan - s * risk
    hedef = plan + s * g.hedef * risk
    if s > 0:
        lo, hi, op, cl = d.bl[i:j1], d.bh[i:j1], d.bo[i:j1], d.bc[i:j1]
        stop_m, hedef_m = lo <= stop, hi >= hedef
    else:
        lo, hi, op, cl = d.al[i:j1], d.ah[i:j1], d.ao[i:j1], d.ac[i:j1]
        stop_m, hedef_m = hi >= stop, lo <= hedef
    hedef_m = hedef_m.copy()
    if len(hedef_m):
        hedef_m[0] = False
    stop_emri = em["tur"] == "stop"
    if stop_emri and len(stop_m):
        # Stop emriyle girişte dolum dakikasının dolumdan ÖNCEKİ kısmı koruyucu stopun tarafında olabilir (fiyat önce
        # stopa iner, sonra girişi tetikler). O dakikada koruyucu stop yalnız dakika stopun ötesinde KAPANDIYSA sayılır
        # (dolumdan sonra stopa dönülmüş demektir) ve çıkış stop seviyesinden yazılır, dakikanın açılışından değil.
        stop_m = stop_m.copy()
        stop_m[0] = bool(cl[0] <= stop) if s > 0 else bool(cl[0] >= stop)
    ks, kh = _ilk(stop_m), _ilk(hedef_m)
    if ks >= 0 and (kh < 0 or ks <= kh):
        k = ks
        ek = kay + (hk if _haber(int(t[i + k]), haber_sn) else 0.0)
        if stop_emri and k == 0:
            cikis = (stop - ek) if s > 0 else (stop + ek)
        else:
            cikis = (min(stop, op[k]) - ek) if s > 0 else (max(stop, op[k]) + ek)
        neden = "stop"
    elif kh >= 0:
        k = kh
        cikis = max(hedef, op[k]) if s > 0 else min(hedef, op[k])
        neden = "hedef"
    else:
        k = len(cl) - 1
        ek = kay + (hk if _haber(int(t[i + k]), haber_sn) else 0.0)
        cikis = (cl[k] - ek) if s > 0 else (cl[k] + ek)
        neden = "zaman"
    r = (cikis - giris) * s / risk
    return {"giris_dk": int(t[i]), "cikis_dk": int(t[i + k]), "neden": neden, "R": float(r),
            "risk_pip": float(risk / pip), "bekleme_dk": int((t[i] - t[e["j0"]]) // 60)}
