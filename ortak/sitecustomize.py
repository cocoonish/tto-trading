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

5. KOŞU BOYU PAYLAŞIM ve URLLIB (21.10.2026). Kesicinin durumu süreç
   başına yaşıyordu ve "bir hattın kararı öbürüne taşınmasın" diye bilerek
   öyleydi. 21.10 sabahı bunun bedeli ölçüldü: EVDS TLS el sıkışmasında
   asılıyordu, TÜİK takvim ucu yanıt vermiyordu ve her hat aynı kaynağın
   öldüğünü kendi zaman aşımlarını baştan ödeyerek yeniden öğrendi — TCMB
   rezerv 105 sn, USD/TRY 210, REDK 196, yabancı pozisyonu 195 sn; Kredi 20
   dakikalık tavanına çarptı, 40 dakikalık tazeleme adımı kesildi, bülten
   52 dakika geç başladı. İkinci kusur kapsamdaydı: emniyet yalnız `requests`'i
   sarıyordu, oysa EVDS'i okuyan on hat (Kredi, YP mevduatı, Fonlama, DİBS,
   Bütçe, Enflasyon, Ödemeler, OVP, Büyüme, Reel kesim) `urllib` kullanıyor —
   kesici onlara HİÇ ulaşmıyordu ve Kredi seri başına 3 × 90 sn bekledi.
   Şimdi: (a) `TTO_HTTP_KESICI_DOSYA` verilmişse durum o dosyada tutulur ve
   koşunun bütün süreçleri (veri.yml'in bütün adımları, guncelle.py'nin bütün
   hatları) aynı kesiciyi görür; bir hat açtıysa sonraki hat beklemeden
   önbelleğe düşer. "Hiç denemeden vazgeçer" itirazı kesicinin kendi
   kuralıyla karşılanır: süre dolunca TEK yoklama yapılır, başarı herkesi
   açar. (b) Yoklama da düşerse süre ikiye katlanır (azami
   TTO_HTTP_KESICI_AZAMI_SN): uzun bir kesintide her üç dakikada bir 90
   saniyelik yoklama ödemek, kesicinin kurtardığı zamanı geri yer. (c)
   `urllib.request.OpenerDirector.open` da sarılır: (verilmemişse) varsayılan
   zaman aşımı her yerde, kesici YALNIZ paylaşım dosyası verildiğinde (veri
   hattı); yeniden deneme EKLENMEZ, hatların kendi döngüsü var. Araştırma
   arşivlerinin uyuyan döngüleri bu yüzden etkilenmez. HTTP hatası (4xx/5xx) sunucunun yanıt verdiğidir,
   kesiciyi besler değil sıfırlar. (d) Kesicinin attığı istisna `tto_kesici`
   özniteliği taşır; hatların yeniden deneme döngüsü onu görünce bekleme
   yapmadan çıkar (bulten/duman.py bunu kapsamdaki her döngüde sorar).
   Yerel ana bilgisayar (127.0.0.1, localhost) paylaşılmaz: sınamaların
   sahte sunucuları birbirini kesmez.

AYAR (ortam değişkeni)
----------------------
  TTO_HTTP_BAGLANTI   bağlantı zaman aşımı, sn   (öntanımlı 15)
  TTO_HTTP_OKUMA      okuma zaman aşımı, sn      (öntanımlı 60)
  TTO_HTTP_DENEME     toplam deneme sayısı       (öntanımlı 3)
  TTO_HTTP_KESICI_ESIK aynı ana bilgisayarda kesiciyi açan ardışık tam başarısızlık (öntanımlı 2)
  TTO_HTTP_KESICI_SN   kesici açık kalma süresi, sn (öntanımlı 180); 0 = kesici yok
  TTO_HTTP_KESICI_AZAMI_SN yoklama düştükçe ikiye katlanan sürenin tavanı, sn (öntanımlı 900)
  TTO_HTTP_KESICI_DOSYA koşu boyu paylaşılan kesici durumu (JSON); boşsa süreç başına
  TTO_HTTP_KAPALI     "1" ise emniyet hiç kurulmaz

Bu dosya HİÇBİR koşuluda koşuyu düşürmez: kurulum tümüyle try/except içinde.
Emniyetin kendisi bir hattı öldürürse emniyet olmaktan çıkar.
"""
from __future__ import annotations

import json
import os
import sys
import time


def _sayi(ad: str, ontanimli: float) -> float:
    try:
        return float(os.environ.get(ad, "") or ontanimli)
    except (TypeError, ValueError):
        return ontanimli


def _host(url) -> str:
    try:
        from urllib.parse import urlsplit
        return urlsplit(str(url)).netloc.lower() or str(url)[:60]
    except Exception:  # noqa: BLE001
        return str(url)[:60]


_YEREL = {"localhost", "127.0.0.1", "::1", "[::1]"}


def _yerel_mi(host: str) -> bool:
    h = host.rsplit("@", 1)[-1]
    if h.startswith("["):
        h = h.split("]", 1)[0] + "]"
    elif h.count(":") == 1:
        h = h.split(":", 1)[0]
    return h in _YEREL


class _Kesici:
    """Ana bilgisayar başına devre kesici; durum süreç içinde ya da koşu boyu
    paylaşılan dosyada. Kayıt: {"sayac", "acilis" (epoch sn | None), "sure"}.

    Kararın üç hâli: "kapali" (istek denenir), "acik" (denenmeden düşer),
    "yoklama" (süre doldu: tek deneme; düşerse süre ikiye katlanır)."""

    def __init__(self) -> None:
        self.esik = max(1, int(_sayi("TTO_HTTP_KESICI_ESIK", 2)))
        self.sn = max(0.0, _sayi("TTO_HTTP_KESICI_SN", 180.0))
        self.azami = max(self.sn, _sayi("TTO_HTTP_KESICI_AZAMI_SN", 900.0))
        self.yerel: dict = {}
        self.duyurulan: set = set()

    @staticmethod
    def _dosya() -> str:
        # Her çağrıda okunur: guncelle.py ortamı süreç açıldıktan SONRA kurabilir.
        return (os.environ.get("TTO_HTTP_KESICI_DOSYA") or "").strip()

    def _ortak(self, host: str) -> str:
        return "" if _yerel_mi(host) else self._dosya()

    def _tumu(self, yol: str) -> dict:
        try:
            with open(yol, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:  # noqa: BLE001 — dosya yok, yarım ya da bozuk: boş say
            return {}

    def oku(self, host: str):
        yol = self._ortak(host)
        if yol:
            k = self._tumu(yol).get(host)
            return k if isinstance(k, dict) else None
        return self.yerel.get(host)

    def yaz(self, host: str, kayit) -> None:
        if kayit is None:
            self.yerel.pop(host, None)
        else:
            self.yerel[host] = kayit
        yol = self._ortak(host)
        if not yol:
            return
        try:
            with open(yol + ".kilit", "a+") as kilit:
                try:
                    import fcntl
                    fcntl.flock(kilit.fileno(), fcntl.LOCK_EX)
                except Exception:  # noqa: BLE001 — kilit yoksa en kötü ihtimal kayıp bir güncelleme
                    pass
                d = self._tumu(yol)
                if kayit is None:
                    if host not in d:
                        return
                    d.pop(host, None)
                else:
                    d[host] = kayit
                gecici = f"{yol}.{os.getpid()}.tmp"
                with open(gecici, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False)
                os.replace(gecici, yol)
        except Exception:  # noqa: BLE001 — paylaşım yazılamazsa süreç içi durum yeter
            pass

    def karar(self, host: str):
        """(hâl, kalan sn, kayıt)."""
        if self.sn <= 0:
            return "kapali", 0.0, None
        k = self.oku(host)
        if not k or k.get("acilis") is None:
            return "kapali", 0.0, k
        try:
            gecen = time.time() - float(k["acilis"])
            sure = float(k.get("sure") or self.sn)
        except (TypeError, ValueError):
            return "kapali", 0.0, None
        if gecen < -5:                 # saat geri gitti: süre dolmuş say, yokla
            return "yoklama", 0.0, k
        if gecen < sure:
            if host not in self.duyurulan and self._ortak(host):
                self.duyurulan.add(host)
                print(f"   ⚡ devre kesici açık: {host} bu koşuda yanıt vermedi; "
                      f"{sure - gecen:.0f} sn daha denenmeyecek (önbellek dalları çalışır)",
                      file=sys.stderr, flush=True)
            return "acik", sure - gecen, k
        return "yoklama", 0.0, k

    def basari(self, host: str) -> None:
        if self.oku(host) is not None:
            self.yaz(host, None)

    def basarisiz(self, host: str, yoklama: bool) -> None:
        if self.sn <= 0:
            return
        k = self.oku(host) or {}
        sayac = int(k.get("sayac") or 0) + 1
        if yoklama:
            sure = min(float(k.get("sure") or self.sn) * 2, self.azami)
            self.yaz(host, {"sayac": sayac, "acilis": time.time(), "sure": sure})
            print(f"   ⚡ devre kesici yeniden AÇILDI: {host} yoklamada da yanıt vermedi; "
                  f"{sure:.0f} sn boyunca denenmeyecek", file=sys.stderr, flush=True)
        elif sayac >= self.esik:
            self.yaz(host, {"sayac": sayac, "acilis": time.time(), "sure": self.sn})
            print(f"   ⚡ devre kesici AÇILDI: {host} ardışık {sayac} istekte "
                  f"yanıt vermedi; {self.sn:.0f} sn boyunca bu ana bilgisayara "
                  f"istek denenmeyecek (önbellek dalları çalışır)",
                  file=sys.stderr, flush=True)
        else:
            self.yaz(host, {"sayac": sayac, "acilis": None, "sure": self.sn})

    @staticmethod
    def mesaj(host: str, kayit, kalan: float, url) -> str:
        sayac = int((kayit or {}).get("sayac") or 0)
        return (f"devre kesici açık: {host} son {sayac} istekte hiç yanıt vermedi, "
                f"{kalan:.0f} sn daha denenmeyecek — {str(url)[:90]}")


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
    kesici = _Kesici()

    # Yeniden denenebilir sayılanlar: yanıt hiç başlamadı ya da yarıda kesildi.
    # HTTP 4xx/5xx BURAYA GİRMEZ — onu çağıran kod yorumlamalı (EVDS boş yanıtı
    # KeyError'a çeviriyor; onu hata sanıp tekrarlamak seriyi yok yere yavaşlatır).
    _TEKRARLANIR = (_hata.ConnectTimeout, _hata.ReadTimeout,
                    _hata.ConnectionError, _hata.ChunkedEncodingError)

    _asil = requests.sessions.Session.request

    def request(self, method, url, **kw):
        if kw.get("timeout") is None:
            kw["timeout"] = (baglanti, okuma)
        host = _host(url)
        hal, kalan, kayit = kesici.karar(host)
        # Kesici AÇIK: süre dolmadıysa hiç denemeden düş; dolduysa tek yoklama.
        if hal == "acik":
            e = _hata.ConnectionError(kesici.mesaj(host, kayit, kalan, url))
            e.tto_kesici = True
            raise e
        yoklama = hal == "yoklama"
        # Yalnız yan etkisiz yöntemler tekrarlanır; yoklama tek atıştır.
        tekrar = 1 if yoklama else (deneme if str(method).upper() in ("GET", "HEAD") else 1)
        for sira in range(1, tekrar + 1):
            try:
                yanit = _asil(self, method, url, **kw)
                kesici.basari(host)            # başarı: sayaç ve kesici sıfır
                return yanit
            except _TEKRARLANIR as e:
                if sira == tekrar:
                    kesici.basarisiz(host, yoklama)
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


def _kur_urllib() -> None:
    """urllib.request için kesici + varsayılan zaman aşımı (yeniden deneme yok)."""
    if os.environ.get("TTO_HTTP_KAPALI") == "1":
        return
    import socket
    import urllib.error
    import urllib.request
    from urllib.parse import urlsplit

    od = urllib.request.OpenerDirector
    if getattr(od, "_tto_emniyet", False):
        return
    okuma = _sayi("TTO_HTTP_OKUMA", 60.0)
    kesici = _Kesici()
    _asil = od.open
    _ONTANIMLI = socket._GLOBAL_DEFAULT_TIMEOUT

    def open(self, fullurl, data=None, timeout=_ONTANIMLI):  # noqa: A001 — imza urllib'inki
        url = fullurl if isinstance(fullurl, str) else getattr(fullurl, "full_url", "")
        try:
            sema = urlsplit(str(url)).scheme.lower()
        except Exception:  # noqa: BLE001
            sema = ""
        if timeout is _ONTANIMLI and socket.getdefaulttimeout() is None and sema in ("http", "https"):
            timeout = okuma
        # urllib KESİCİSİ yalnız koşu boyu paylaşım verildiğinde (veri hattı:
        # veri.yml iş ortamı ya da guncelle.py) devrede. Araştırma arşivleri
        # (arastirma-veri.yml) kendi uyuyan yeniden deneme döngülerini taşıyor;
        # orada iki geçici düşüşten sonra açılan bir kesici, sonraki denemeleri
        # boşa harcatırdı. requests yolunun kesicisi her yerde (eski davranış).
        if sema not in ("http", "https") or not kesici._dosya():
            return _asil(self, fullurl, data, timeout)
        host = _host(url)
        hal, kalan, kayit = kesici.karar(host)
        if hal == "acik":
            e = urllib.error.URLError(kesici.mesaj(host, kayit, kalan, url))
            e.tto_kesici = True
            raise e
        try:
            yanit = _asil(self, fullurl, data, timeout)
        except urllib.error.HTTPError:
            kesici.basari(host)                # sunucu yanıt verdi: ölü değil
            raise
        except OSError:                        # URLError, zaman aşımı, TLS, bağlantı
            kesici.basarisiz(host, hal == "yoklama")
            raise
        kesici.basari(host)
        return yanit

    open.__doc__ = _asil.__doc__
    od.open = open
    od._tto_emniyet = True


try:
    _kur()
except Exception as _e:  # noqa: BLE001 — emniyet, koşuyu asla düşürmez
    print(f"::warning::HTTP emniyeti kurulamadı ({_e!r}) — istekler zaman aşımısız",
          file=sys.stderr, flush=True)
# urllib AYRI kurulur: requests'i taşımayan bir .venv'de (DİBS) ilk kurulum
# düşüyordu ve urllib emniyeti onunla birlikte gidiyordu.
try:
    _kur_urllib()
except Exception as _e:  # noqa: BLE001
    print(f"::warning::urllib emniyeti kurulamadı ({_e!r})", file=sys.stderr, flush=True)


# ── ZAMAN YOLCULUĞU — yalnız TTO_SAHTE_GUN verilince ────────────────────────
# Kapıları ileri bir günde koşturmak için (bkz. ortak/zaman_yolculugu.py).
# Değişken yoksa TEK SATIR çalışmaz; üretim yolu değişmez. Kurulamazsa
# SESSİZCE GEÇİLMEZ: ölçülmemiş bir koşu, ölçülüp temiz çıkmışla aynı görünür
# ve tam bu yüzden bu depoda dört kez sahte temiz üretildi.
#
# İÇE AKTARMA İLE KURULUM AYRI DENENİR (01.10.2026). İkisi tek `try`daydı ve
# `except ImportError: pass` modülün YOKLUĞU için yazılmıştı; ama `baslat()`
# freezegun'u kendi içinde içe aktarıyor ve kütüphane kurulu değilse onun
# ImportError'ı da aynı dala düşüyordu: TTO_SAHTE_GUN verilmiş, koşu çıkış 0,
# saat BUGÜNDE — bu oturumda haftalık kipin yıl başı bombasını ilk denemede
# "temiz" gösteren tam buydu. Modül yoksa sessiz; kurulum düşerse değişken
# verilmişken GÜRÜLTÜLÜ.
try:
    import zaman_yolculugu as _zy
except ImportError:
    _zy = None
try:
    if _zy is not None and _zy.etkin() and not _zy.baslat():
        raise RuntimeError("saat kaydırılamadı")
except Exception as _ze:  # noqa: BLE001
    import os as _os
    import sys as _sys
    if (_os.environ.get("TTO_SAHTE_GUN") or "").strip():
        print(f"::error::zaman yolculuğu kurulamadı ({_ze!r}) — ölçüm GEÇERSİZ",
              file=_sys.stderr, flush=True)
        raise SystemExit(3)
