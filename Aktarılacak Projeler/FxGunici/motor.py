#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İşlem motoru: emir listesini 1 dakikalık bid/ask verisinde dolumlara çevirir.

Bütün stratejiler aynı motordan geçer; strateji yalnız EMİR üretir (hangi
dakikada, hangi yönde, stop ve hedef nerede, en geç ne zaman çıkılır), dolumu
motor yapar. Kurallar (önceden kayıt, `onkayit.toml`):

  GİRİŞ   sinyal mumunun kapanışından sonraki ilk dakikanın AÇILIŞINDA:
          alış ask'tan, satış bid'den, artı kayma.
  R       gerçek giriş fiyatından stop seviyesine planlanan risk. Stopsuz
          (yalnız zamanla çıkan) stratejide R birimi emirle gelir (ATR).
          Emir stop SEVİYESİ değil yalnız risk uzaklığı taşıyorsa (fiksing ve
          gün içi momentumun stop'lu varyantları: "stop 1·ATR"), stop YÜRÜTÜLEN
          girişten o kadar uzağa konur; R tam olarak o uzaklıktır ve stop'lu ile
          stop'suz varyant aynı R birimiyle kıyaslanır.
          R ≤ 0 ise (giriş stop'un ötesinde açıldıysa) işlem YOK, sayılır.
          Stop SEVİYESİ taşıyan emirde giriş tarafının KAYMASIZ açılışı da
          sorulur: uzunda ask ≤ stop, kısada bid ≥ stop ise işlem YOK. Kayma
          emirden sonra gelen bir maliyettir; dolumu stop'un berisine itip
          olmayacak bir işlemi (R ≤ kayma) doğuramaz. (Sonradan, 16.10.2026:
          ilk koşu bunu yalnız kaymalı dolumla soruyordu; ön kayıttaki not.)
  MAE/MFE işlem boyunca emir tarafındaki en kötü / en iyi gezinme (giriş
          fiyatına göre). Hedefin dolduğu dakikanın ters ucu MAE'ye, boşluklu
          stop ve hedefin açılış fiyatı uçlara girer; gerçekleşen sonuç her
          zaman ikisinin arasındadır (MAE ≤ sonuç ≤ MFE).
  SERT    stop emir tarafında dakika dakika sorulur: uzunda bid ≤ stop,
  STOP    kısada ask ≥ stop. Dakika stop'un ötesinde AÇILIRSA dolum açılış
          fiyatıdır (boşluk); değilse stop seviyesi. Her ikisinde de kayma.
          Boşluk kuralı GİRİŞ dakikasında da geçerlidir: giriş tarafı stop'un
          berisinde açılıp emir tarafı ötesinde açıldıysa (makas stop'u
          kapsıyor) çıkış o dakikanın emir tarafı açılışıdır. Bu çıkıştan sonra
          aynı dakikada yeni giriş yoktur.
  KAPANIŞ mumun mid kapanışı stop'un ötesindeyse bir sonraki dakikanın (yani
  STOP'U  sonraki mumun) açılışında piyasa emriyle çıkılır.
  HEDEF   limit emir: uzunda bid ≥ hedef, kısada ask ≤ hedef. Kayma yok. Dakika
          hedefin ötesinde açılırsa dolum açılış (lehte). SEVİYE hedefi (VWAP,
          pivot, aralık ucu, itkinin ucu) yürütülen girişin gerisinde ya da
          tam üstünde kalırsa işlem YOK ("hedef geçersiz", sayılır). Bu kural
          yürütülen girişe, yani kaymaya bağlıdır: maliyet merdiveninin her
          basamağında atılan sinyal sayısı değişebilir.
  AYNI    bir dakikada hem stop hem hedef değdiyse: açılış birinin ötesindeyse
  DAKİKA  o; değilse STOP önce sayılır (sıra 1 dakikadan çözülemez) ve işlem
          `belirsiz` diye işaretlenir. 5/15/60 dakikalık mumun içindeki sıra
          zaten dakika dakika yürüyerek çözülür.
  ZAMAN   `cikis_i` dakikasının açılışında piyasa emriyle (gün sonu, N mum).
  GÜN     giriş dakikası gün sonu çıkışında ya da sonrasındaysa (16:55 ET)
  SONU    işlem YOK ("gun_sonu", sayılır; strat_ortak giriş dizinini −2 yazar).
  TEK     bir pozisyon açıkken gelen emir alınmaz (sayılır).
  POZİSYON
  HABER   dolum dakikası haber penceresindeyse kaymaya haber kayması eklenir;
          makas zaten o dakikanın gerçek bid/ask'ıdır.

Brüt sonuç mid'den mid'e ölçülür (makas ve kayma yok); net sonuç dolumlardan.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from veri import Dakika

# Emir alanları
EMIR = np.dtype([
    ("giris_i", np.int64), ("yon", np.int8), ("stop", np.float64), ("risk", np.float64),
    ("hedef_tur", np.int8), ("hedef_k", np.float64), ("hedef_seviye", np.float64),
    ("cikis_i", np.int64), ("stop_tur", np.int8), ("kimlik", np.int64),
])
HEDEF_YOK, HEDEF_R, HEDEF_SEVIYE = 0, 1, 2
STOP_YOK, STOP_SERT, STOP_KAPANIS = 0, 1, 2

# Sonuç kodları
DURUM = {0: "alindi", 1: "pozisyon_acik", 2: "risk_gecersiz", 3: "hedef_gecersiz", 4: "veri_yok", 5: "gun_sonu"}
#: strat_ortak'ın gün sonundan sonraki girişe yazdığı dizin (−1: sonraki mum yok, veri yok).
GIRIS_GUN_SONU = -2
NEDEN = {1: "stop", 2: "hedef", 3: "zaman", 4: "kapanis_stop", 5: "bosluk_stop", 6: "bosluk_hedef"}


@njit(cache=True)
def _simule(bo, bh, bl, ao, ah, al, mo, mc, bar_son, haber,
            giris_i, yon, stop, risk, hedef_tur, hedef_k, hedef_seviye, cikis_i, stop_tur,
            kayma, haber_kayma, tek_pozisyon):
    n_emir = len(giris_i)
    n = len(bo)
    durum = np.zeros(n_emir, np.int8)
    giris_f = np.full(n_emir, np.nan)
    cikis_f = np.full(n_emir, np.nan)
    cikis_dk = np.full(n_emir, -1, np.int64)
    neden = np.zeros(n_emir, np.int8)
    R = np.full(n_emir, np.nan)
    pnl = np.full(n_emir, np.nan)
    brut = np.full(n_emir, np.nan)
    mae = np.full(n_emir, np.nan)
    mfe = np.full(n_emir, np.nan)
    belirsiz = np.zeros(n_emir, np.bool_)
    hedef_f = np.full(n_emir, np.nan)
    stop_f = np.full(n_emir, np.nan)
    serbest = 0
    for e in range(n_emir):
        i = giris_i[e]
        son = cikis_i[e]
        if i == -2:
            durum[e] = 5
            continue
        if i < 0 or i >= n or son <= i:
            durum[e] = 4
            continue
        if tek_pozisyon and i < serbest:
            durum[e] = 1
            continue
        y = yon[e]
        s0 = kayma + (haber_kayma if haber[i] else 0.0)
        if y == 1:
            g = ao[i] + s0
        else:
            g = bo[i] - s0
        st = stop[e]
        sert = stop_tur[e] == 1
        kap = stop_tur[e] == 2
        # Stop seviyeli emir: giriş tarafının kaymasız açılışı stop'un ötesindeyse işlem yok (kayma işlem yaratmaz).
        if stop_tur[e] != 0 and not np.isnan(st):
            ham = ao[i] if y == 1 else bo[i]
            if not ((ham - st) * y > 0.0):
                durum[e] = 2
                continue
        if stop_tur[e] != 0 and np.isnan(st) and risk[e] > 0.0:
            st = g - y * risk[e]            # stop yürütülen girişten risk kadar uzakta
        if stop_tur[e] != 0 and not np.isnan(st):
            r = (g - st) * y
        else:
            r = risk[e]
            sert = False
            kap = False
        if not (r > 0.0):
            durum[e] = 2
            continue
        ht = hedef_tur[e]
        T = np.nan
        if ht == 1:
            T = g + y * hedef_k[e] * r
        elif ht == 2:
            T = hedef_seviye[e]
        if ht != 0 and (T - g) * y <= 0.0:
            durum[e] = 3
            continue
        mid_g = mo[i]
        en_iyi = 0.0
        en_kotu = 0.0
        cf = np.nan
        ck = -1
        nd = 0
        mid_c = np.nan
        j = i
        while j < son and j < n:
            if y == 1:
                xo = bo[j]; xh = bh[j]; xl = bl[j]
            else:
                xo = ao[j]; xh = ah[j]; xl = al[j]
            sj = kayma + (haber_kayma if haber[j] else 0.0)
            yari = 0.5 * (ao[j] - bo[j])
            # Boşluklu sert stop giriş dakikası dahil: emir tarafı stop'un ötesinde açıldıysa dolum o açılıştan.
            if sert and (xo - st) * y <= 0.0:
                cf = xo - y * sj; ck = j; nd = 5; mid_c = mo[j]
                kotu = (xo - g) * y
                if kotu < en_kotu:
                    en_kotu = kotu
                break
            if j > i:
                if ht != 0 and (xo - T) * y >= 0.0:
                    cf = xo; ck = j; nd = 6; mid_c = mo[j]
                    iyi = (xo - g) * y
                    if iyi > en_iyi:
                        en_iyi = iyi
                    break
            if y == 1:
                stop_deg = sert and xl <= st
                hedef_deg = ht != 0 and xh >= T
            else:
                stop_deg = sert and xh >= st
                hedef_deg = ht != 0 and xl <= T
            if stop_deg:
                cf = st - y * sj; ck = j; nd = 1; mid_c = st + y * yari
                if hedef_deg:
                    belirsiz[e] = True
                kotu = (st - g) * y
                if kotu < en_kotu:
                    en_kotu = kotu
                break
            if hedef_deg:
                cf = T; ck = j; nd = 2; mid_c = T + y * yari
                iyi = (T - g) * y
                if iyi > en_iyi:
                    en_iyi = iyi
                # Dakikanın içindeki sıra bilinmez: hedefin dolduğu dakikanın ters ucu MAE'ye girer.
                kotu = ((xl - g) if y == 1 else (g - xh))
                if kotu < en_kotu:
                    en_kotu = kotu
                break
            iyi = ((xh - g) if y == 1 else (g - xl))
            kotu = ((xl - g) if y == 1 else (g - xh))
            if iyi > en_iyi:
                en_iyi = iyi
            if kotu < en_kotu:
                en_kotu = kotu
            if kap and bar_son[j] and (mc[j] - st) * y < 0.0:
                k = j + 1
                if k >= son:
                    k = son
                if k < n:
                    sk = kayma + (haber_kayma if haber[k] else 0.0)
                    if y == 1:
                        cf = bo[k] - sk
                    else:
                        cf = ao[k] + sk
                    ck = k; nd = 4; mid_c = mo[k]
                break
            j += 1
        if ck < 0:
            k = son if son < n else n - 1
            sk = kayma + (haber_kayma if haber[k] else 0.0)
            if y == 1:
                cf = bo[k] - sk
            else:
                cf = ao[k] + sk
            ck = k; nd = 3; mid_c = mo[k]
        giris_f[e] = g
        cikis_f[e] = cf
        cikis_dk[e] = ck
        neden[e] = nd
        R[e] = r
        pnl[e] = (cf - g) * y
        brut[e] = (mid_c - mid_g) * y
        # Gerçekleşen sonuç gezinmenin dışında kalamaz (çıkış dakikasının açılışı ve çıkış kayması dahil).
        if pnl[e] < en_kotu:
            en_kotu = pnl[e]
        if pnl[e] > en_iyi:
            en_iyi = pnl[e]
        mae[e] = en_kotu
        mfe[e] = en_iyi
        hedef_f[e] = T
        stop_f[e] = st if (stop_tur[e] != 0) else np.nan
        # Çıkış açılışta olduysa (zaman, kapanış stop'u, boşluk) aynı dakikada yeni giriş olabilir; giriş dakikasının
        # kendisindeki boşluklu stop bunun dışındadır (o dakikanın açılışı zaten bu işlemin girişidir).
        if (nd == 3 or nd == 4 or nd == 5 or nd == 6) and ck > i:
            serbest = ck
        else:
            serbest = ck + 1
    return durum, giris_f, cikis_f, cikis_dk, neden, R, pnl, brut, mae, mfe, belirsiz, hedef_f, stop_f


def bos_emir(n: int) -> np.ndarray:
    e = np.zeros(n, dtype=EMIR)
    e["stop"] = np.nan
    e["risk"] = np.nan
    e["hedef_seviye"] = np.nan
    return e


def simule(d: Dakika, emir: np.ndarray, bar_son: np.ndarray, haber: np.ndarray | None = None,
           kayma_pip: float = 0.0, haber_kayma_pip: float = 0.0, tek_pozisyon: bool = True) -> pd.DataFrame:
    """Emirleri giriş dakikasına göre sıralar, simüle eder; alınan ve alınmayan her emir için bir satır."""
    if haber is None:
        haber = np.zeros(len(d), dtype=np.bool_)
    sira = np.argsort(emir["giris_i"], kind="stable")
    e = emir[sira]
    k = kayma_pip * d.pip
    hk = haber_kayma_pip * d.pip
    (durum, gf, cf, cdk, nd, R, pnl, brut, mae, mfe, bel, hf, sf) = _simule(
        d.bo, d.bh, d.bl, d.ao, d.ah, d.al, d.mo, d.mc, bar_son, haber,
        e["giris_i"], e["yon"], e["stop"], e["risk"], e["hedef_tur"], e["hedef_k"], e["hedef_seviye"],
        e["cikis_i"], e["stop_tur"], float(k), float(hk), bool(tek_pozisyon))
    gi = e["giris_i"]
    ok = (gi >= 0) & (gi < len(d))
    t_g = np.where(ok, d.t[np.clip(gi, 0, len(d) - 1)], -1)
    t_c = np.where(cdk >= 0, d.t[np.clip(cdk, 0, len(d) - 1)], -1)
    df = pd.DataFrame({
        "kimlik": e["kimlik"], "durum": durum, "yon": e["yon"].astype(np.int8),
        "giris_i": gi, "cikis_i": cdk, "giris_t": t_g, "cikis_t": t_c,
        # Stop: emrin seviyesi; seviye yoksa motorun yürütülen girişten kurduğu stop (alınan işlemde);
        # stop'suz işlemde stop yoktur (R birimi `R` sütunundadır).
        "giris_f": gf, "cikis_f": cf,
        "stop": np.where(e["stop_tur"] == STOP_YOK, np.nan, np.where(np.isnan(e["stop"]), sf, e["stop"])),
        "hedef": hf,
        # Emrin kendi stop alanı (seviye ya da NaN: yürütülen girişten konacak stop); işlemi aynı kuralla yeniden
        # koşturmak için (ör. örnek işlemin ek kaymalı hâli).
        "stop_emir": e["stop"], "risk_emir": e["risk"], "hedef_seviye_emir": e["hedef_seviye"],
        "R": R, "pnl": pnl, "brut": brut, "mae": mae, "mfe": mfe,
        "neden": nd, "belirsiz": bel, "plan_cikis_i": e["cikis_i"], "stop_tur": e["stop_tur"],
        "hedef_tur": e["hedef_tur"], "hedef_k": e["hedef_k"],
    })
    pip = float(d.pip)
    df["pnl_pip"] = df["pnl"] / pip
    df["brut_pip"] = df["brut"] / pip
    df["R_pip"] = df["R"] / pip
    df["r"] = df["pnl"] / df["R"]
    df["r_brut"] = df["brut"] / df["R"]
    df["mae_r"] = df["mae"] / df["R"]
    df["mfe_r"] = df["mfe"] / df["R"]
    df["sure_dk"] = (df["cikis_t"] - df["giris_t"]) / 60.0
    return df
