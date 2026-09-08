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
4. DEVRE KESİCİ (08.09.2026). Kaynak BÜTÜNÜYLE yanıt vermiyorsa her isteğe
   ayrı ayrı tam yeniden deneme bütçesi ödemek hattı öldürür: marj hattı 39
   EVDS serisi çekiyor, seri başına 3 × 60 sn okuma + 3 + 9 sn bekleme ≈ 3,2 dk
   — EVDS'in yanıt vermediği bir akşamda beş seri 15 dakikalık adım tavanını
   doldurdu ve hat, 34 serinin ÖNBELLEĞİ dururken, hiçbir şey üretmeden kesildi.
   Tavanı büyütmek çare değil (39 seri × 3,2 dk = 2 saat); kusur isteklerin
   birbirinden ders almamasında. Aynı ana bilgisayarda ardışık TTO_HTTP_KESICI_ESIK
   tam başarısızlıktan sonra kesici AÇILIR: o ana bilgisayara sonraki istekler
   TTO_HTTP_KESICI_SN saniye boyunca hiç denenmeden ConnectionError ile döner
   (hatların "kaynak düştü → önbellek" dalları aynı istisnayı yakalar), süre
   dolunca TEK deneme ile yoklanır, başarı sayacı sıfırlar. Marj için hesap:
   2 seri × 3,2 dk + 37 anlık düşme ≈ 6,5 dk — tavanın altında, önbellekle
   tamamlanır ve koşu kaydına "ESKİ önbellek" uyarıları düşer.

AYAR (ortam değişkeni)
----------------------
  TTO_HTTP_BAGLANTI   bağlantı zaman aşımı, sn   (öntanımlı 15)
  TTO_HTTP_OKUMA      okuma zaman aşımı, sn      (öntanımlı 60)
  TTO_HTTP_DENEME     toplam deneme sayısı       (öntanımlı 3)
  TTO_HTTP_KESICI_ESIK aynı ana bilgisayarda kesiciyi açan ardışık tam başarısızlık (öntanımlı 2)
  TTO_HTTP_KESICI_SN   kesici açık kalma süresi, sn (öntanımlı 180); 0 = kesici yok
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
    kesici_esik = max(1, int(_sayi("TTO_HTTP_KESICI_ESIK", 2)))
    kesici_sn = max(0.0, _sayi("TTO_HTTP_KESICI_SN", 180.0))
    # Ana bilgisayar → (ardışık tam başarısızlık sayısı, kesicinin açıldığı an).
    # Süreç başına yaşar: her hat kendi alt sürecinde koşar, bir hattın kesici
    # kararı öbürüne taşınmaz — taşınsaydı EVDS'in düştüğü an bütün hatlar
    # denemeden vazgeçerdi ve bir yeniden deneme penceresi boşa giderdi.
    kesik: dict = {}

    # Yeniden denenebilir sayılanlar: yanıt hiç başlamadı ya da yarıda kesildi.
    # HTTP 4xx/5xx BURAYA GİRMEZ — onu çağıran kod yorumlamalı (EVDS boş yanıtı
    # KeyError'a çeviriyor; onu hata sanıp tekrarlamak seriyi yok yere yavaşlatır).
    _TEKRARLANIR = (_hata.ConnectTimeout, _hata.ReadTimeout,
                    _hata.ConnectionError, _hata.ChunkedEncodingError)

    _asil = requests.sessions.Session.request

    def _host(url) -> str:
        try:
            from urllib.parse import urlsplit
            return urlsplit(str(url)).netloc.lower() or str(url)[:60]
        except Exception:  # noqa: BLE001
            return str(url)[:60]

    def request(self, method, url, **kw):
        if kw.get("timeout") is None:
            kw["timeout"] = (baglanti, okuma)
        host = _host(url)
        sayac, acilis = kesik.get(host, (0, None))
        # Kesici AÇIK: süre dolmadıysa hiç denemeden düş; dolduysa tek yoklama.
        yoklama = False
        if kesici_sn > 0 and acilis is not None:
            gecen = time.monotonic() - acilis
            if gecen < kesici_sn:
                raise _hata.ConnectionError(
                    f"devre kesici açık: {host} son {sayac} istekte hiç yanıt vermedi, "
                    f"{kesici_sn - gecen:.0f} sn daha denenmeyecek — {str(url)[:90]}")
            yoklama = True
        # Yalnız yan etkisiz yöntemler tekrarlanır; yoklama tek atıştır.
        tekrar = 1 if yoklama else (deneme if str(method).upper() in ("GET", "HEAD") else 1)
        for sira in range(1, tekrar + 1):
            try:
                yanit = _asil(self, method, url, **kw)
                kesik.pop(host, None)          # başarı: sayaç ve kesici sıfır
                return yanit
            except _TEKRARLANIR as e:
                if sira == tekrar:
                    if kesici_sn > 0:
                        sayac += 1
                        if sayac >= kesici_esik:
                            kesik[host] = (sayac, time.monotonic())
                            print(f"   ⚡ devre kesici AÇILDI: {host} ardışık {sayac} istekte "
                                  f"yanıt vermedi; {kesici_sn:.0f} sn boyunca bu ana bilgisayara "
                                  f"istek denenmeyecek (önbellek dalları çalışır)",
                                  file=sys.stderr, flush=True)
                        else:
                            kesik[host] = (sayac, None)
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
