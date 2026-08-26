# -*- coding: utf-8 -*-
"""Ağa çıkan her hattın altına serilen ortak emniyet: HTTP zaman aşımı + yeniden deneme.

NEDEN VAR
---------
2026-08-27 koşusunda TCMB Net Rezerv hattı EVDS'te **21 dakika** asılı kaldı ve
ReadTimeout ile düştü. Sebep tek bir eksik argümandı: `tcmb` istemcisi isteği
`requests.get(url, headers=..., proxies=...)` ile atıyor — `timeout` yok, yani
`read timeout=None`. Sunucu yanıtı hiç kapatmazsa istemci sonsuza kadar bekler.

Argümanı çağrı yerinden geçirmek MÜMKÜN DEĞİL: `tcmb.Client.read(**kwargs)`
kwargs'ı `requests.get`'e değil **sorgu dizesine** (`params`) koyuyor
(bkz. tcmb 0.5.0, core.py:152). `client.read(..., timeout=60)` isteği düzeltmez,
URL'ye `timeout=60` yazar. Bu yüzden emniyet kütüphanenin ALTINA seriliyor.

NASIL DEVREYE GİRİYOR
---------------------
Python yorumlayıcısı açılışta `sitecustomize` modülünü BULABİLİYORSA kendiliğinden
import eder. Bu klasör `PYTHONPATH`e eklenince (guncelle.py'de `_COCUK_ENV`,
bulutta `.github/workflows/veri.yml` iş env'i) her hat alt süreci — kendi .venv'i
olsa bile — bu emniyetle açılır. Hatların dosyalarına tek satır eklemek gerekmez;
yarın eklenecek hat da korumalı doğar.

NE YAPAR
--------
1. `timeout` verilmeden atılan her isteğe varsayılan bir zaman aşımı koyar.
   Açıkça timeout veren çağrılara DOKUNMAZ (net_rezerv.py'nin PDF indirmeleri
   kendi 30/60 sn'sini kullanmaya devam eder).
2. Yalnız GET/HEAD için, zaman aşımı/bağlantı hatasında üstel bekleyişle yeniden
   dener. Diğer yöntemler (POST…) tekrarlanmaz: yan etkileri olabilir.
3. Her yeniden denemeyi stderr'e tek satır yazar — koşu kaydında "neden uzun
   sürdü" sorusu cevapsız kalmasın.

AYAR (ortam değişkeni)
----------------------
  TTO_HTTP_BAGLANTI   bağlantı zaman aşımı, sn   (öntanımlı 15)
  TTO_HTTP_OKUMA      okuma zaman aşımı, sn      (öntanımlı 60)
  TTO_HTTP_DENEME     toplam deneme sayısı       (öntanımlı 3)
  TTO_HTTP_KAPALI     "1" ise emniyet hiç kurulmaz

Bu dosya HİÇBİR koşuluda koşuyu düşürmez: kurulum tümüyle try/except içinde.
Emniyetin kendisi bir hattı öldürürse emniyet olmaktan çıkar.
"""
from __future__ import annotations

import os
import sys
import time


def _sayi(ad: str, ontanimli: float) -> float:
    try:
        return float(os.environ.get(ad, "") or ontanimli)
    except (TypeError, ValueError):
        return ontanimli


def _kur() -> None:
    if os.environ.get("TTO_HTTP_KAPALI") == "1":
        return

    import requests
    from requests import exceptions as _hata

    if getattr(requests.sessions.Session, "_tto_emniyet", False):
        return  # iç içe import: iki kez sarma

    baglanti = _sayi("TTO_HTTP_BAGLANTI", 15.0)
    okuma = _sayi("TTO_HTTP_OKUMA", 60.0)
    deneme = max(1, int(_sayi("TTO_HTTP_DENEME", 3)))

    # Yeniden denenebilir sayılanlar: yanıt hiç başlamadı ya da yarıda kesildi.
    # HTTP 4xx/5xx BURAYA GİRMEZ — onu çağıran kod yorumlamalı (EVDS boş yanıtı
    # KeyError'a çeviriyor; onu hata sanıp tekrarlamak seriyi yok yere yavaşlatır).
    _TEKRARLANIR = (_hata.ConnectTimeout, _hata.ReadTimeout,
                    _hata.ConnectionError, _hata.ChunkedEncodingError)

    _asil = requests.sessions.Session.request

    def request(self, method, url, **kw):
        if kw.get("timeout") is None:
            kw["timeout"] = (baglanti, okuma)
        # Yalnız yan etkisiz yöntemler tekrarlanır.
        tekrar = deneme if str(method).upper() in ("GET", "HEAD") else 1
        for sira in range(1, tekrar + 1):
            try:
                return _asil(self, method, url, **kw)
            except _TEKRARLANIR as e:
                if sira == tekrar:
                    raise
                bekle = 3.0 * (3 ** (sira - 1))  # 3 sn, 9 sn
                print(f"   ↻ HTTP {sira}/{tekrar} düştü ({type(e).__name__}), "
                      f"{bekle:.0f} sn sonra tekrar — {str(url)[:90]}",
                      file=sys.stderr, flush=True)
                time.sleep(bekle)
        raise AssertionError("ulaşılamaz")  # pragma: no cover

    request.__doc__ = _asil.__doc__
    requests.sessions.Session.request = request
    requests.sessions.Session._tto_emniyet = True


try:
    _kur()
except Exception as _e:  # noqa: BLE001 — emniyet, koşuyu asla düşürmez
    print(f"::warning::HTTP emniyeti kurulamadı ({_e!r}) — istekler zaman aşımısız",
          file=sys.stderr, flush=True)
