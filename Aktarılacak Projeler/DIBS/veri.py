# -*- coding: utf-8 -*-
"""DİBS verim eğrisi & reel faiz — veri katmanı (EVDS3).

Ne yapar
--------
1. TCMB'nin "Devlet İç Borçlanma Senetlerinin Gösterge Niteliğindeki Değerleri"
   veri grubundan (`bie_pydibs`) ve ARŞİV eşinden (`bie_pydibsarsiv`) DİBS
   enstrüman evrenini kurar; her kıymeti türüne göre SINIFLANDIRIR.
2. Sınıflandırmadan geçen SIFIR KUPONLU strip'lerin günlük gösterge FİYAT
   tarihçesini çeker (nominal eğri) — ayrıca TÜFEX anapara strip'lerini (reel
   eğri) ve aktif sabit kuponlu TAHVİLLERİ (YTM çapraz sınaması).
3. Kupon strip'lerinin ÖDEME TUTARINI (`.ORAN` serisi) okur ve tutarın kıymetin
   ömrü boyunca SABİT olduğunu sınar — sabit değilse kıymet değişken faizlidir
   ve nominal eğriden ATILIR.
4. Referans faizleri (TLREF, politika, AOFM, koridor) ve aylık beklenti /
   enflasyon serilerini çeker.
5. Her seriyi TTL'li önbelleğe yazar; ağ düşerse ESKİ önbelleğe düşer ama
   SESSİZ kalmaz — GÖRÜNÜR uyarı basar, `veri_durum.json`'a taşınır.
6. Dönemi (son iş günü / son ay) VERİDEN okur — sabit tarih YASAK.

EVDS3 uç noktası
----------------
`evds2.tcmb.gov.tr` ÖLÜ. Çalışan taban:

    https://evds3.tcmb.gov.tr/igmevdsms-dis/{uç}{param}={değer}&...

Sorgu dizesi `?` ile BAŞLAMAZ; anahtar URL'de DEĞİL `key:` HTTP başlığında
gider. Tek istek ~1000 SATIRLA sınırlı ve aralığın SONUNDAN geriye doldurur,
gerisini uyarı vermeden kırpar → uzun tarihçe PARÇALANARAK çekilir.
Satır sınırı TARİH sayısına bağlıdır, SERİ sayısına değil (ölçüldü: 24 seri ×
963 gün tek istekte 963 satır, 24 dolu kolon, 1,9 sn). Bu yüzden seriler 20'lik
demetler hâlinde ve 900 günlük parçalarla çekilir.

BİRİM DENETİMİ (bu hattın en pahalı tuzakları)
----------------------------------------------
· `TP.<ISIN>` = "Değer" → 100 TL NOMİNAL BAŞINA gösterge fiyat (TL).
  TÜFEX'te bu fiyat ENDEKSLENMİŞ TL'dir, reel fiyat DEĞİL.
· `TP.<ISIN>.ORAN` → adı "Kupon Faiz Oranı" olsa da içerik YILLIK ORAN DEĞİL,
  DÖNEMSEL KUPON TUTARIDIR (100 nominal başına). Ölçüldü: TRT150328A17.ORAN =
  18,40 ve aynı tahvilin kupon strip'i tam 18,40 ödüyor (yıllık %36,8).
  "Yıllık oran" sanılıp 2'ye bölünürse EĞRİ ~15 PUAN KAYAR.
· Hazine BONOLARINDA `.ORAN` faiz değil KALAN GÜN SAYISIDIR (ad alanı "Diğer").
  Ölçüldü: TP.TRB170327T15.ORAN her gün 1 azalıyor. Faiz sanılırsa grafiğe
  "%206" diye bir gözlem girer.
· ISIN'in 10. karakteri "F" olan kıymetler ~48.000 mertebesinde fiyat basar;
  100 nominal ölçeğinde DEĞİLDİR (getiri −%100 çıkar) → dışlanır.
· EVDS3 meta verisinde BİRİM ALANI YOKTUR (serieList yanıtındaki 28 alan
  tarandı). Birim seri ADINDAN okunur; bu yüzden her seriye BÜYÜKLÜK MERTEBESİ
  denetimi konur (aşağıda `MERTEBE`).

Koşum:  python3 veri.py  [--yenile]
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

import pandas as pd

# --------------------------------------------------------------------------- yollar
PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parent.parent                      # …/TTO Trading
VERI = PROJE / "data"
CACHE = VERI / "cache"
for _p in (VERI, CACHE):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- anahtar
# EVDS anahtarı kaynak koda GÖMÜLMEZ. Arama sırası Fonlama/veri.py ile AYNI:
#   TTO_EVDS_KEY ortam değişkeni → <proje>/.evds_key → kök/.evds_key
#   → kardeş TCMBNetRezerv/.evds_key
_ADAYLAR = [
    PROJE / ".evds_key",
    KOK / ".evds_key",
    KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key",
]


def _evds_anahtari() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    for yol in _ADAYLAR:
        if yol.exists():
            try:
                a = yol.read_text(encoding="utf-8").strip()
            except OSError as ex:
                print(f"UYARI: {yol} okunamadı ({type(ex).__name__}).")
                a = ""
            if a:
                return a
    raise RuntimeError(
        "EVDS anahtarı bulunamadı. export TTO_EVDS_KEY=<anahtar> ya da şu "
        "dosyalardan birine yazın (.gitignore'da): "
        + " / ".join(str(y) for y in _ADAYLAR))


BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

DEMET = 20                # tek istekte kaç seri (satır sınırı seri sayısına bağlı DEĞİL)
PARCA_GUN = 900           # tek istekte kaç TAKVİM GÜNÜ (1000 satır sınırının altı)
TTL_CANLI_SAAT = 12       # hâlâ işlem gören kıymet / cari seri
TTL_OLU_SAAT = 24 * 30    # vadesi dolmuş kıymet: değeri artık değişmez, ama TTL'siz DEĞİL
TTL_LISTE_SAAT = 24       # serieList önbelleği

# Boş önbellek dosyasının İMZASI. "EVDS yanıt verdi, bu pencerede gözlem yok"
# ile "çekemedik" birbirinden yalnız bu satırla ayrılır.
BOS_IMZA = "BOS-DOGRULANMIS"
# Planın bu kadarından fazlası veri taşımıyorsa hat DURUR: tek tek uyarı
# basıp devam etmek, evren süzgeci ya da EVDS erişimi bozulduğunda yarım
# bir eğriyi "taze" diye yayımlamak demektir.
BOS_PAY_ESIK = 0.02

# Eğri tarihçesinin başlangıcı. 2013 bilinçli: PKA beklenti serileri
# (TP.PKAUO.*) 2013-01'de başlıyor; reel faiz ayağı öncesi için kurulamıyor.
# Daha geriye gitmek eğri panelini uzatır ama sayfadaki her reel/başabaş
# ölçüsünü boş bırakır.
TARIHCE_BAS = "2013-01-01"

DG_DIBS = "bie_pydibs"              # güncel, GÜNLÜK
DG_DIBS_ARSIV = "bie_pydibsarsiv"   # 1990'a kadar; vadesi dolan kıymet BURAYA düşer

_UYARI: list[str] = []
_ANAHTAR: str | None = None
_ISTEK = {"n": 0}


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı (ondalık virgül, eksi U+2212,
    yüzde önde). Hat kendi klasöründen elle koşturulursa ortak/ PYTHONPATH'te
    olmayabilir; depo kökünden bulunur."""
    try:
        import bicim
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


def uyar(mesaj: str) -> None:
    """Görünür uyarı: ekrana basılır ve uyarilar.json'a taşınır."""
    if mesaj not in _UYARI:
        _UYARI.append(mesaj)
    print("  ! " + mesaj, flush=True)


def uyarilar() -> list[str]:
    """Veri katmanının bu koşuda bastığı GÖRÜNÜR uyarılar.

    metrik.py bunu kendi listesine katar; katmadığında tazelik ve
    'ESKİ ÖNBELLEK' uyarıları uyarilar.json'a hiç girmez ve sayfada
    görünmez — düzenin yasakladığı sessiz bayatlamanın tam kendisi.
    """
    return list(_UYARI)


def anahtar() -> str:
    global _ANAHTAR
    if _ANAHTAR is None:
        _ANAHTAR = _evds_anahtari()
    return _ANAHTAR


def _cek(yol: str, deneme: int = 3):
    """EVDS3'ten JSON. Anahtar `key:` BAŞLIĞINDA gider, URL'de değil."""
    son_hata: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                f"{BASE}/{yol}", headers={"key": anahtar(), "User-Agent": UA})
            _ISTEK["n"] += 1
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:            # ağ, zaman aşımı, 5xx…
            son_hata = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü ({yol[:90]}): {son_hata}") from son_hata


def _taze(yol: pathlib.Path, ttl_saat: float) -> bool:
    if not yol.exists():
        return False
    return (dt.datetime.now().timestamp() - yol.stat().st_mtime) / 3600 < ttl_saat


def _yas_gun(yol: pathlib.Path) -> float:
    return (dt.datetime.now().timestamp() - yol.stat().st_mtime) / 86400


# --------------------------------------------------------------------------- ayrıştırıcılar
def _ayristir(items, kolonlar: list[str], bicim: str) -> pd.DataFrame:
    """EVDS `items` → DataFrame.

    İKİ ayrı tarih biçimi dolaşıyor ve karıştırılırsa seri SESSİZCE boşalır:
      GÜNLÜK → "20-08-2026"      AYLIK → "2026-6"
    """
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    if "Tarih" not in df.columns:
        return pd.DataFrame()
    if bicim == "gun":
        t = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    elif bicim == "ay":
        t = pd.to_datetime(df["Tarih"], format="%Y-%m", errors="coerce")
    else:
        raise ValueError(f"bilinmeyen biçim: {bicim}")
    out = {}
    for k in kolonlar:
        if k in df.columns:
            out[k] = pd.to_numeric(df[k].replace("", None), errors="coerce")
    if not out:
        return pd.DataFrame()
    d = pd.DataFrame(out)
    d.index = t
    return d[~d.index.isna()].sort_index()


def _url(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp) -> str:
    return (f"series={'-'.join(kodlar)}"
            f"&startDate={bas:%d-%m-%Y}&endDate={son:%d-%m-%Y}&type=json")


def _demet_cek(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp,
               parca_gun: int, bicim: str) -> tuple[pd.DataFrame, set[str]]:
    """Bir seri demetini tarih parçaları hâlinde çeker.

    Demetin tamamı düşerse (bir kod geçersizse EVDS bütün isteği reddediyor)
    seriler tek tek denenir; böylece bir bozuk kod diğer 19'unu götürmez.

    İKİ DEĞER DÖNER — (veri, DÜŞEN KODLAR). "Veri gelmedi" ile "veri yok"
    ayrı şeylerdir: ağ/HTTP hatasıyla düşen bir kodun BOŞ döndüğünü varsayıp
    dolu önbelleğini ezmek SESSİZ VERİ KAYBIDIR (bu hata bir kez yaşandı).
    Bir kod hangi tarih parçasında olursa olsun istisnayla düştüyse adı
    ikinci değerde döner ve çağıran onun önbelleğine DOKUNMAZ.
    """
    guvenli = [k.replace(".", "_") for k in kodlar]
    parcalar: list[pd.DataFrame] = []
    dusen: set[str] = set()
    imlec = bas
    while imlec <= son:
        sonu = min(imlec + pd.Timedelta(days=parca_gun - 1), son)
        try:
            items = _cek(_url(kodlar, imlec, sonu)).get("items", [])
            p = _ayristir(items, guvenli, bicim)
        except Exception as ex:
            uyar(f"demet düştü ({len(kodlar)} seri · {imlec:%m.%Y}–{sonu:%m.%Y}: "
                 f"{ex}); seriler tek tek deneniyor.")
            tekler = []
            for k, g in zip(kodlar, guvenli):
                try:
                    it = _cek(_url([k], imlec, sonu)).get("items", [])
                    d = _ayristir(it, [g], bicim)
                    if len(d):
                        tekler.append(d)
                except Exception as ex2:
                    dusen.add(k)
                    uyar(f"SERİ ALINAMADI: {k} ({imlec:%m.%Y}–{sonu:%m.%Y}) — {ex2}")
                time.sleep(0.15)
            p = pd.concat(tekler, axis=1) if tekler else pd.DataFrame()
        if len(p):
            parcalar.append(p)
        imlec = sonu + pd.Timedelta(days=1)
        time.sleep(0.12)
    if not parcalar:
        return pd.DataFrame(), dusen
    d = pd.concat(parcalar)
    d = d[~d.index.duplicated(keep="last")].sort_index()
    return d, dusen


def _cache_yolu(kod: str, bicim: str = "gun") -> pathlib.Path:
    return CACHE / f"evds_{bicim}_{kod.replace('.', '_')}.csv"


# ===========================================================================
# 1) DİBS ENSTRÜMAN EVRENİ VE SINIFLANDIRMA
#    (kurallar kesif.py'de GERÇEK API çağrılarıyla doğrulandı; kaynak orada)
# ===========================================================================
# Seri adında ÜÇ biçim dolaşıyor; üçü de karşılanmazsa kıymetler SESSİZCE
# evrenin dışında kalır (ölçüldü: tek biçim varsayımı 2079 kıymetin 288'ini
# düşürüyordu):
#   "TRT150328A17 ( 18.03.2026 15.03.2028 )  Değer (24T2A150328)"
#   "TRT070727A14 (2017-07-19/2027-07-07) Değer (121T2DA070727)"
#   "TRT110226A14 (24-02-2016/11-02-2026) Deger (121T2A110226)"   ← 'Deger' aksansız
_AD = re.compile(
    r"^(?P<isin>TR[A-Z]\w+)\s*\(\s*(?P<ihrac>[\d.\-]+)\s*[/\s]\s*(?P<itfa>[\d.\-]+)\s*\)\s*"
    r"(?P<tur>.+?)\s*\((?P<etiket>[^()]*)\)\s*$")
# TANI AYRIŞTIRICISI — yalnız ÖLÇÜM için. `_AD`'den TEK BİR ŞEYDE ayrılır:
# tarihi yalnız NOKTA AYRAÇLI (gg.aa.yyyy) ve BOŞLUKLA ayrılmış biçimde kabul
# eder, `(Arşiv)` ekini de soymaz. Yani "tek biçim varsayan ayrıştırıcı"nın
# ta kendisidir. Sayfadaki "şu kadarını sessizce düşürürdü" cümlesi HER
# KOŞUDA buradan ölçülür; elle yazılmış eski bir sayı kullanılmaz.
_AD_SAF = re.compile(
    r"^(?P<isin>TR[A-Z]\w+)\s*\(\s*(?P<ihrac>\d{2}\.\d{2}\.\d{4})\s+"
    r"(?P<itfa>\d{2}\.\d{2}\.\d{4})\s*\)\s*"
    r"(?P<tur>.+?)\s*\((?P<etiket>[^()]*)\)\s*$")
# toplam        : taranan seri adı
# saf_dusen     : saf ayrıştırıcının HİÇ çözemediği ad
# saf_yanlis    : çözdüğü ama etiketi "Arşiv" okuduğu ad (sessiz yanlış sınıf)
# hosgoru_dusen : hoşgörülü ayrıştırıcının da çözemediği ad (gerçek kayıp)
_AYRISTIRMA_TEST = {"toplam": 0, "saf_dusen": 0, "saf_yanlis": 0,
                    "hosgoru_dusen": 0}

_ETI_SABIT = re.compile(r"^\d+T\d+(K\d+|A\d{6})?$")   # 24T2 / 61T2K8 / 121T2A080328
_ETI_ANAPARA = re.compile(r"A\d{6}$")
_ETI_KUPON = re.compile(r"K\d+")
_ETI_GOVDE = re.compile(r"^(\d+T\d+)")                # tahvil serisi kimliği: "24T2"


def _tarih(s: str) -> dt.date | None:
    """gg.aa.yyyy · gg-aa-yyyy · yyyy-aa-gg — üçü de dolaşımda.

    ISO biçimi unutulursa (evren kayıtları ISO saklanıyor) sessizce None döner
    ve eğri BOŞ çıkar; keşifte bir kez yaşandı.
    """
    if not s:
        return None
    for f in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def seri_listesi(dg: str, yenile: bool = False) -> list[dict]:
    yol = VERI / f"serieList_{dg}.json"
    if yenile or not _taze(yol, TTL_LISTE_SAAT):
        d = _cek(f"serieList/type=json&code={dg}")
        yol.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return json.loads(yol.read_text(encoding="utf-8"))


def evren(dg: str, yenile: bool = False) -> dict[str, dict]:
    """Kıymet bazında birleşik kayıt: {taban_kod: {…}}.

    Fiyat serisi (`TP.<ISIN>`) ile oran serisi (`TP.<ISIN>.ORAN`) AYNI kıymete
    aittir; TÜR bilgisi yalnız ORAN serisinin ADINDA olduğu için ikisi burada
    birleştirilir. Oran serisi çekilmezse sukuk/TÜFEX/bono ayrımı İMKÂNSIZDIR.
    """
    ham = seri_listesi(dg, yenile)
    kayit: dict[str, dict] = {}
    ayristirilamayan = 0
    for s in ham:
        ad = (s.get("SERIE_NAME") or "").strip()
        # TANI: saf ayrıştırıcı bu adı ÇÖZEBİLİR MİYDİ? (ham ad üzerinde,
        # `(Arşiv)` soyulmadan — saf ayrıştırıcı onu da bilmez.)
        _AYRISTIRMA_TEST["toplam"] += 1
        _saf = _AD_SAF.match(ad)
        if not _saf:
            _AYRISTIRMA_TEST["saf_dusen"] += 1
        elif _saf.group("etiket").strip() in ("Arşiv", "Archive"):
            _AYRISTIRMA_TEST["saf_yanlis"] += 1
        # Arşiv grubunda ad "… Deger (9B) (Arşiv)" biçiminde biter. Son parantez
        # SOYULMAZSA etiket "Arşiv" olur, sınıflandırma çöker ve tarihçenin KISA
        # UCU sessizce kaybolur (ölçüldü: 2019 eğrisi 3 yılın altında hiç nokta
        # vermiyor, 216 yerine 85 nokta kalıyordu).
        ad = re.sub(r"\s*\((?:Arşiv|Archive)\)\s*$", "", ad)
        m = _AD.match(ad)
        if not m:
            ayristirilamayan += 1
            _AYRISTIRMA_TEST["hosgoru_dusen"] += 1
            continue
        kod = s["SERIE_CODE"]
        taban = kod[:-5] if kod.endswith(".ORAN") else kod
        e = kayit.setdefault(taban, {
            "kod": taban, "isin": m.group("isin"),
            "ihrac": str(_tarih(m.group("ihrac")) or ""),
            "itfa": str(_tarih(m.group("itfa")) or ""),
            "etiket": m.group("etiket"), "grup": dg,
        })
        if kod.endswith(".ORAN"):
            e["oran_kod"] = kod
            e["oran_tur"] = m.group("tur")
        else:
            e["fiyat_bas"] = s.get("START_DATE")
            e["fiyat_son"] = s.get("END_DATE")
    if ayristirilamayan:
        # Okura grup KODU değil adı: 'bie_pydibsarsiv' okurun elinde olmayan bir şeydir.
        grup_adi = "arşiv" if dg == DG_DIBS_ARSIV else "güncel"
        uyar(f"AD BİÇİMİ: {grup_adi} DİBS grubunda {ayristirilamayan} seri adı "
             f"ayrıştırılamadı ({_bicim().yuzde(ayristirilamayan / max(len(ham), 1) * 100, 1)}) "
             "— TCMB ad biçimini değiştirmiş olabilir; bu kıymetler evrene "
             "girmedi.")
    for e in kayit.values():
        et = e["etiket"]
        if e.get("oran_tur") == "Deger":          # aksansız biçim
            e["oran_tur"] = "Değer"
        e["strip"] = ("anapara" if _ETI_ANAPARA.search(et)
                      else "kupon" if _ETI_KUPON.search(et) else "tahvil")
        # Sabit kuponlu nominal DİBS mi? Etiket gövdesinin sonunda "D" varsa
        # (49T4D, 85T2D…) kıymet DEĞİŞKEN FAİZLİ ya da TÜFEX'tir: yayımlanan
        # kupon yalnız CARİ dönemin kuponudur, ileri vadeli kupon strip'ine
        # uygulanınca getiri saçmalar (ölçüldü: %1–%105 arası dağılım).
        e["sabit_nominal"] = bool(
            _ETI_SABIT.match(et)
            and e.get("oran_tur") in ("Kupon Faiz Oranı", None)
            and e["isin"][9:10] != "F")      # 10. karakter "F" → 100 nominal ölçeğinde DEĞİL
        e["tufex"] = e.get("oran_tur") == "Reel Kupon Oranı"
        e["sukuk"] = e.get("oran_tur") == "Kira Getirisi Oranı"
        e["bono"] = e.get("oran_tur") == "Diğer"
        g = _ETI_GOVDE.match(et)
        e["govde"] = g.group(1) if g else ""    # aynı tahvilin strip'lerini bağlar
    return kayit


def birlesik_evren(yenile: bool = False) -> dict[str, dict]:
    """Güncel + ARŞİV grubun birleşimi.

    Vadesi dolan kıymet güncel gruptan DÜŞÜYOR: yalnız `bie_pydibs` ile 2013
    yılı için 5 nokta kalıyor (ölçüldü). Tarihsel eğri arşiv birleştirilmeden
    KURULAMAZ. Çakışmada güncel kayıt kazanır (aynı kıymet iki grupta da
    olabilir; güncel grubun START/END tarihleri daha yenidir).
    """
    ars = evren(DG_DIBS_ARSIV, yenile)
    cur = evren(DG_DIBS, yenile)
    havuz = dict(ars)
    for k, v in cur.items():
        eski = havuz.get(k)
        if eski and eski.get("fiyat_bas") and v.get("fiyat_bas"):
            # Fiyat penceresini iki grubun BİRLEŞİMİ yap: arşiv erken ucu,
            # güncel grup geç ucu taşıyor.
            b1, b2 = _tarih(eski["fiyat_bas"]), _tarih(v["fiyat_bas"])
            s1, s2 = _tarih(eski.get("fiyat_son") or ""), _tarih(v.get("fiyat_son") or "")
            if b1 and b2 and b1 < b2:
                v["fiyat_bas"] = eski["fiyat_bas"]
            if s1 and s2 and s1 > s2:
                v["fiyat_son"] = eski["fiyat_son"]
        havuz[k] = v
    return havuz


def _canli(v: dict, a: dt.date, b: dt.date) -> bool:
    """Kıymetin fiyat serisi [a, b] penceresiyle KESİŞİYOR mu?"""
    s = _tarih(v.get("fiyat_bas") or "")
    e = _tarih(v.get("fiyat_son") or "")
    return bool(s and e and s <= b and e >= a)


# ===========================================================================
# 2) FİYAT TARİHÇESİ ÇEKİMİ (demet + parça + TTL'li seri bazlı önbellek)
# ===========================================================================
def _ttl(son: dt.date, bugun: dt.date) -> float:
    """Vadesi dolmuş kıymetin gösterge değeri artık DEĞİŞMEZ; onu her koşuda
    yeniden çekmek 800 isteği boşa harcar. Yine de TTL'sizlik YASAK: 30 günlük
    TTL revizyonu yakalar, `--yenile` her şeyi tazeler."""
    return TTL_OLU_SAAT if (bugun - son).days > 30 else TTL_CANLI_SAAT


def cek_fiyatlar(plan: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
                 etiket: str, yenile: bool = False) -> pd.DataFrame:
    """{kod: (başlangıç, bitiş)} planını çeker; geniş DataFrame döndürür.

    Önbellek SERİ BAZINDADIR (demet bileşimi değişince önbellek geçersizleşmesin).
    EVDS BAŞARIYLA yanıt verip o kıymet için hiç satır döndürmediyse BOŞ
    önbellek dosyası yazılır — aksi hâlde o kıymet her koşuda yeniden denenir
    ve koşum süresi sessizce şişer.

    BOŞ ÖNBELLEK İMZALIDIR (`# BOS-DOGRULANMIS <iso>` başlığı). İmza olmadan
    "gerçekten boş" ile "çekilemedi" ayırt edilemez; çekim İSTİSNAYLA düştüyse
    var olan önbelleğe DOKUNULMAZ (aksi hâlde 13 yıllık tarihçe 22 baytlık bir
    başlık satırıyla ezilir — bu hata bir kez yaşandı ve ikinci koşuda tek
    uyarı bile düşmüyordu).
    """
    bugun = dt.date.today()
    dusen_kalici: set[str] = set()
    bos_yazilan = 0
    eksik = [k for k in plan
             if yenile or not _taze(_cache_yolu(k), _ttl(plan[k][1].date(), bugun))]
    if eksik:
        # Aynı tarih penceresini paylaşanları bir arada tut: demet aralığı
        # bileşenlerin BİRLEŞİMİ olduğu için karışık sıralama parça sayısını
        # (ve istek sayısını) katlar.
        eksik.sort(key=lambda k: (plan[k][0], plan[k][1]))
        n_demet = -(-len(eksik) // DEMET)
        print(f"  {etiket}: {len(eksik)}/{len(plan)} seri EVDS'ten çekiliyor "
              f"({n_demet} demet)", flush=True)
        for i in range(0, len(eksik), DEMET):
            grup = eksik[i:i + DEMET]
            bas = min(plan[k][0] for k in grup)
            son = max(plan[k][1] for k in grup)
            d, dusen = _demet_cek(grup, bas, son, PARCA_GUN, "gun")
            for k in grup:
                g = k.replace(".", "_")
                yol = _cache_yolu(k)
                if g in d.columns and d[g].notna().any():
                    s = d[g].dropna()
                    s.name = k
                    s.to_csv(yol)
                elif k in dusen:
                    # Çekim İSTİSNAYLA düştü: bu "veri yok" DEĞİL, "veri
                    # gelmedi"dir. Var olan önbelleğe dokunulmaz.
                    dusen_kalici.add(k)
                else:
                    yol.write_text(f"# {BOS_IMZA} {dt.date.today().isoformat()}\n"
                                   f"tarih,{k}\n", encoding="utf-8")
                    bos_yazilan += 1
            if (i // DEMET) % 10 == 9:
                print(f"    … {i + len(grup)}/{len(eksik)} "
                      f"({_ISTEK['n']} istek)", flush=True)
    out: dict[str, pd.Series] = {}
    bos_dogrulanmis = 0          # EVDS "bu pencerede gözlem yok" dedi
    bos_imzasiz = 0              # dosya boş ama imzası yok → şüpheli
    for k in plan:
        yol = _cache_yolu(k)
        if not yol.exists():
            uyar(f"SERİ YOK: {k} — ne EVDS'ten geldi ne önbellekte var.")
            continue
        try:
            s = pd.read_csv(yol, index_col=0, parse_dates=True,
                            comment="#").iloc[:, 0]
        except (ValueError, IndexError, pd.errors.EmptyDataError):
            s = pd.Series(dtype=float)
        if s.empty:
            ilk = yol.read_text(encoding="utf-8")[:80]
            if ilk.startswith(f"# {BOS_IMZA}"):
                bos_dogrulanmis += 1
            else:
                bos_imzasiz += 1
            continue
        out[k] = s
    if bos_dogrulanmis:
        print(f"    ({bos_dogrulanmis} kıymet penceresinde hiç gözlem yok — "
              "EVDS doğruladı, atlandı)")
    # BURADA `print` YETMEZ: bu satırlar uyarilar.json'a ve ozet.json'a
    # girmezse ikinci koşuda kayıp SESSİZ kalır (dosya artık "taze" sayılır
    # ve hiç çekim denenmez).
    if dusen_kalici:
        uyar(f"ÇEKİM DÜŞTÜ: {len(dusen_kalici)} kıymet EVDS'ten alınamadı; "
             "önbelleklerine DOKUNULMADI (eski değerler kullanılıyor olabilir).")
    if bos_imzasiz:
        uyar(f"BOŞ ÖNBELLEK (imzasız): {bos_imzasiz} kıymetin önbellek dosyası "
             "boş ama 'EVDS doğruladı' imzası taşımıyor — eski bir koşuda "
             "ezilmiş olabilir; önbellek yenilenmeli.")
    toplam_bos = bos_dogrulanmis + bos_imzasiz + len(dusen_kalici)
    if plan and toplam_bos / len(plan) > BOS_PAY_ESIK:
        raise SystemExit(
            f"DUR: {etiket} planındaki {len(plan)} kıymetin {toplam_bos}'i "
            f"({toplam_bos / len(plan) * 100:.1f}%) veri taşımıyor — eşik "
            f"%{BOS_PAY_ESIK * 100:.0f}. EVDS erişimi ya da evren süzgeci "
            "bozulmuş olabilir; siteye kopyalama YAPILMAZ.")
    if not out:
        return pd.DataFrame()
    df = pd.DataFrame(out).sort_index()
    df.index.name = "tarih"
    return df


def cek_kume(kodlar: dict[str, tuple[str, str]], bicim: str, parca_gun: int,
             yenile: bool = False, etiket: str = "") -> pd.DataFrame:
    """Referans/beklenti serileri: {ad: (kod, başlangıç)} → tek DataFrame.

    Fonlama hattıyla AYNI kalıp: önbellek seri bazında, ağ düşerse GÖRÜNÜR
    uyarıyla eski önbelleğe düşülür.
    """
    ad_kod = {ad: k for ad, (k, _) in kodlar.items()}
    eksik = [ad for ad in kodlar
             if yenile or not _taze(_cache_yolu(ad_kod[ad], bicim), TTL_CANLI_SAAT)]
    if eksik:
        print(f"  {etiket}: {len(eksik)}/{len(kodlar)} seri EVDS'ten çekiliyor")
        eksik = sorted(eksik, key=lambda a: kodlar[a][1])
        bugun = pd.Timestamp.today().normalize()
        for i in range(0, len(eksik), DEMET):
            grup = eksik[i:i + DEMET]
            bas = min(pd.Timestamp(kodlar[a][1]) for a in grup)
            d, _dusen = _demet_cek([ad_kod[a] for a in grup], bas, bugun,
                                   parca_gun, bicim)
            for a in grup:
                g = ad_kod[a].replace(".", "_")
                if g in d.columns and d[g].notna().any():
                    s = d[g].dropna()
                    s.name = ad_kod[a]
                    s.to_csv(_cache_yolu(ad_kod[a], bicim))
    out: dict[str, pd.Series] = {}
    for ad, (kod, _) in kodlar.items():
        yol = _cache_yolu(kod, bicim)
        if not yol.exists():
            uyar(f"SERİ YOK: {ad} ({kod}) — ne EVDS'ten geldi ne önbellekte var.")
            continue
        if not _taze(yol, TTL_CANLI_SAAT):
            uyar(f"ESKİ ÖNBELLEK: {ad} ({kod}) {_yas_gun(yol):.0f} gün eski — "
                 "EVDS'ten tazelenemedi, bu seri BAYAT olabilir.")
        try:
            s = pd.read_csv(yol, index_col=0, parse_dates=True).iloc[:, 0]
        except (ValueError, IndexError, pd.errors.EmptyDataError):
            uyar(f"SERİ BOŞ: {ad} ({kod}) — önbellek dosyası veri taşımıyor.")
            continue
        out[ad] = s
    df = pd.DataFrame(out).sort_index()
    df.index.name = "tarih"
    return df


# ===========================================================================
# 3) REFERANS / BEKLENTİ / ENFLASYON SERİLERİ
#    (kodlar kesif.py'de tek tek doğrulandı; birim seri ADINDAN okunur)
# ===========================================================================
# --- İŞ GÜNÜ --- (hepsi YÜZDE)
GUNLUK: dict[str, tuple[str, str]] = {
    "tlref":         ("TP.BISTTLREF.ORAN", "2018-12-28"),  # BIST TLREF gecelik
    "politika":      ("TP.PY.P02.1H",      "2013-01-01"),  # 1 hafta repo SATIŞ kotasyonu
    "politika_ger":  ("TP.PY.P06.1H",      "2013-01-01"),  # gerçekleşen 1 haftalık repo
    "aofm":          ("TP.APIFON4",        "2013-01-01"),  # ağırlıklı ort. fonlama maliyeti
    # AOFM'nin TABANI: APİ fonlama toplamı — MİLYON TL (yüzde DEĞİL).
    # AOFM bir ORTALAMADIR; ağırlığı sıfıra yaklaşınca yayımlanan sayı
    # dejenere olur (son değer donar). Fonlama hattı bu yüzden 5 milyar TL
    # tabanı arıyor; aynı kapı burada da uygulanır, yoksa aynı gün üç sayfada
    # üç farklı AOFM durumu görünür.
    "fon_top":       ("TP.APIFON1.TOP",    "2013-01-01"),  # APİ fonlaması, MİLYON TL
    "koridor_alt":   ("TP.PY.P01.ON",      "2013-01-01"),  # O/N borçlanma
    "koridor_ust":   ("TP.PY.P02.ON",      "2013-01-01"),  # O/N borç verme
    "bist_on":       ("TP.AOFOBAP",        "2018-12-27"),  # BİST gecelik repo AOF
}

# --- AYLIK ---
AYLIK: dict[str, tuple[str, str]] = {
    # PKA beklentileri — YÜZDE (katılımcı sayısı ADET)
    "pka_12a":         ("TP.PKAUO.S01.E.U", "2013-01-01"),
    "pka_12a_medyan":  ("TP.BEK.S01.E.M",   "2013-01-01"),
    "pka_12a_std":     ("TP.BEK.S01.E.S",   "2013-01-01"),
    "pka_12a_n":       ("TP.BEK.S01.E.X",   "2013-01-01"),
    "pka_24a":         ("TP.PKAUO.S01.F.U", "2013-01-01"),
    "pka_5y":          ("TP.PKAUO.S01.G.U", "2017-11-01"),
    "pka_yilsonu":     ("TP.PKAUO.S01.D.U", "2013-01-01"),
    "pka_faiz_12a":    ("TP.PKAUO.S04.D.U", "2013-01-01"),
    "pka_faiz_24a":    ("TP.PKAUO.S04.E.U", "2013-01-01"),
    "reel_kesim_12a":  ("TP.ENFBEK.IYA12ENF", "2015-01-01"),
    "hanehalki_12a":   ("TP.ENFBEK.HBA12ENF", "2015-01-01"),
    # TÜFE — ENDEKS. İki baz zincirlenir (aşağıda `tufe_zinciri`).
    "tufe_2025":       ("TP.TUKFIY2025.GENEL", "2005-01-01"),   # 2025=100, cari
    "tufe_2003":       ("TP.FG.J0",            "2003-01-01"),   # 2003=100, 2026-01'de DONDU
    # İç borç stoku — BİN TL (bağlam; eğriye girmez)
    "ic_borc_tahvil":  ("TP.KB.A01", "2005-01-01"),
    "ic_borc_bono":    ("TP.KB.A05", "2005-01-01"),
    "ic_borc_toplam":  ("TP.KB.A09", "2005-01-01"),
}

# Büyüklük mertebesi denetimi — EVDS3'te BİRİM ALANI YOK, birim seri adından
# okunuyor. 1000× hata bu eşikte yakalanır.
MERTEBE = {
    "tlref": ("yüzde", -10, 500), "politika": ("yüzde", -10, 500),
    "aofm": ("yüzde", -10, 500), "koridor_alt": ("yüzde", -10, 500),
    "koridor_ust": ("yüzde", -10, 500), "bist_on": ("yüzde", -10, 500),
    # MİLYON TL: 2026'da APİ fonlaması 10^5–10^7 mertebesinde (yüz milyar–
    # birkaç trilyon TL). Bin TL sanılsaydı 1000× büyük, milyar TL sanılsaydı
    # 1000× küçük çıkardı; eşik ikisini de yakalar.
    "fon_top": ("milyon TL", 0, 5e7),
    "pka_12a": ("yüzde", -10, 500), "pka_24a": ("yüzde", -10, 500),
    "pka_5y": ("yüzde", -10, 500), "pka_faiz_12a": ("yüzde", -10, 500),
    "pka_12a_n": ("adet", 1, 500),
    "tufe_2025": ("endeks", 50, 100_000), "tufe_2003": ("endeks", 50, 100_000),
    "ic_borc_toplam": ("bin TL", 1e6, 1e12),
}

# --------------------------------------------------------------------------- tazelik
# (etiket, tolerans TAKVİM GÜNÜ). Referans DUVAR SAATİDİR: verinin kendi son
# gününü referans almak denetimi kendi kendine referanslı hâle getirir
# ("son gözlem bugün, demek ki taze").
TAZELIK_GUNLUK = {
    "tlref":       ("TLREF (TP.BISTTLREF.ORAN)", 5),
    "politika":    ("Politika faizi (TP.PY.P02.1H)", 5),
    "aofm":        ("AOFM (TP.APIFON4)", 5),
    "koridor_ust": ("Faiz koridoru (TP.PY.P02.ON)", 5),
}
TAZELIK_EGRI = ("DİBS gösterge değerleri", 5)
# PKA ayın ikinci yarısında yayımlanır; TÜFE ayın ilk haftasında. 45 gün
# toleransı iki yayımın da kaçmasını yakalar, normal ritmi alarm saymaz.
TAZELIK_AYLIK = {
    "pka_12a":   ("PKA 12 ay beklentisi (TP.PKAUO.S01.E.U)", 45),
    "tufe_2025": ("TÜFE (TP.TUKFIY2025.GENEL)", 45),
}
# PKA katılımcı sayısı bu eşiğin altına inerse beklenti serisi gürültülenir ve
# Fisher reel faizi oynar → GÖRÜNÜR uyarı.
PKA_N_ESIK = 40


def tazelik_tolerans(aile: str = "gunluk") -> int:
    """Bu ailedeki EN SIKI tolerans (takvim günü).

    ozet_uret.py bayat bayrağını buradan okur; eşik iki yerde ayrı ayrı
    yazılırsa biri güncellenip öteki unutulur ve bayatlık sessizce kaçar.
    """
    if aile == "gunluk":
        return min(min(t for _, t in TAZELIK_GUNLUK.values()), TAZELIK_EGRI[1])
    return min(t for _, t in TAZELIK_AYLIK.values())


AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım",
         12: "Aralık"}
AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
           7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def gun_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {AY_TR[t.month]} {t.year}"


def ay_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_TR[t.month]} {t.year}"


def kisa_ad(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_KISA[t.month]}-{str(t.year)[2:]}"


# ===========================================================================
# 4) ANA AKIŞ
# ===========================================================================
def _plan(havuz: dict[str, dict], kodlar: list[str], bas: pd.Timestamp,
          bugun: pd.Timestamp) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    """Her kıymet için çekim penceresi: kendi yayın aralığı ∩ tarihçe penceresi."""
    plan = {}
    for k in kodlar:
        v = havuz[k]
        b = pd.Timestamp(_tarih(v.get("fiyat_bas") or "") or bas.date())
        s = pd.Timestamp(_tarih(v.get("fiyat_son") or "") or bugun.date())
        plan[k] = (max(b, bas), min(s + pd.Timedelta(days=3), bugun))
    return plan


def oran_degerleri(havuz: dict[str, dict], kodlar: list[str],
                   yenile: bool = False) -> tuple[dict[str, float], dict[str, dict]]:
    """Kupon strip'lerinin ÖDEME TUTARI + sabitlik sınaması.

    `.ORAN` = DÖNEMSEL kupon TUTARI (100 nominal başına), yıllık oran DEĞİL.
    SABİT kuponlu bir kıymette bu tutar ömür boyu değişmez; değişiyorsa kıymet
    değişken faizlidir ve nominal eğriye GİREMEZ. Pencere olarak kıymetin son
    ~900 günü alınır (tek istekte gelir) ve o pencerede min == maks sınanır.
    """
    bugun = pd.Timestamp.today().normalize()
    plan = {}
    for k in kodlar:
        v = havuz[k]
        s = pd.Timestamp(_tarih(v.get("fiyat_son") or "") or bugun.date())
        b = pd.Timestamp(_tarih(v.get("fiyat_bas") or "") or (s - pd.Timedelta(days=PARCA_GUN)).date())
        s = min(s + pd.Timedelta(days=3), bugun)
        plan[v["oran_kod"]] = (max(b, s - pd.Timedelta(days=PARCA_GUN - 1)), s)
    df = cek_fiyatlar(plan, "kupon ödeme tutarı (.ORAN)", yenile)
    odeme: dict[str, float] = {}
    tani: dict[str, dict] = {}
    for k in kodlar:
        ok = havuz[k]["oran_kod"]
        if ok not in df.columns:
            continue
        s = df[ok].dropna()
        if s.empty:
            continue
        sabit = bool(s.max() - s.min() <= 1e-9)
        odeme[k] = float(s.iloc[-1])
        tani[k] = {"sabit": sabit, "min": float(s.min()), "maks": float(s.max()),
                   "n": int(len(s))}
    return odeme, tani


def tufe_zinciri(a: pd.DataFrame) -> pd.Series:
    """2003=100 tabanlı TÜFE zinciri (TÜFEX referans endeksinin tabanı).

    TP.FG.J0 (2003=100) TÜİK'in 2025 baz değişikliğiyle 2026-01'de DONDU;
    sonrası TP.TUKFIY2025.GENEL ile zincirlenir. Zincir katsayısı ÖRTÜŞME
    AYINDAN her koşuda yeniden okunur — SABİT YAZILMAZ (ölçülen: 31,8312;
    TÜİK yeni bir baz açıklarsa bu sayı değişir ve sabit yazılmış olsaydı
    bütün reel eğri sessizce kayardı).
    """
    eski = a["tufe_2003"].dropna() if "tufe_2003" in a.columns else pd.Series(dtype=float)
    yeni = a["tufe_2025"].dropna() if "tufe_2025" in a.columns else pd.Series(dtype=float)
    if eski.empty or yeni.empty:
        uyar("TÜFE zinciri kurulamadı — TÜFEX reel eğrisi hesaplanamaz.")
        return pd.Series(dtype=float)
    ortak = eski.index.intersection(yeni.index)
    if ortak.empty:
        uyar("TÜFE zinciri: iki baz hiç örtüşmüyor — katsayı okunamadı.")
        return eski
    son_ortak = ortak.max()
    kat = float(eski.loc[son_ortak] / yeni.loc[son_ortak])
    zincir = eski.copy()
    ek = yeni[yeni.index > son_ortak] * kat
    zincir = pd.concat([zincir, ek]).sort_index()
    zincir = zincir[~zincir.index.duplicated(keep="first")]
    zincir.attrs["zincir_kat"] = kat
    zincir.attrs["zincir_ay"] = str(son_ortak.date())
    return zincir


def kos(yenile: bool = False) -> dict:
    print("EVDS3 → DİBS verim eğrisi & reel faiz · veri katmanı")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")
    t0 = time.time()
    bugun = pd.Timestamp.today().normalize()
    bas = pd.Timestamp(TARIHCE_BAS)

    # --- (1) evren ---------------------------------------------------------
    havuz = birlesik_evren(yenile)
    a_d, b_d = bas.date(), bugun.date()
    # NOMİNAL SPOT EĞRİNİN EVRENİ. Dışarıda kalanlar ve nedenleri:
    #   · sukuk (kira sertifikası) — DİBS değil, TL nominal tahvil eğrisine ait değil
    #   · TÜFEX — reel kıymet, ayrı eğri (aşağıda `tufex`)
    #   · hazine BONOSU — `.ORAN` faiz değil KALAN GÜN SAYISI; kısa uç zaten
    #     kupon strip'leriyle dolu olduğu için bono hiç alınmıyor (yanlış birim
    #     riskini almaya değmez)
    #   · değişken faizli (etiket gövdesi "D" ile biten) ve ölçek dışı ("F")
    #   · kuponlu tahvilin KENDİSİ — sıfır kuponlu değil
    nominal = [k for k, v in havuz.items()
               if v["sabit_nominal"] and v["strip"] in ("anapara", "kupon")
               and _tarih(v["itfa"]) and _canli(v, a_d, b_d)]
    tufex = [k for k, v in havuz.items()
             if v["tufex"] and v["strip"] == "anapara"
             and _tarih(v["itfa"]) and _tarih(v["ihrac"]) and _canli(v, a_d, b_d)]
    # Kuponlu tahvillerin KENDİSİ: sıfır kuponlu DEĞİL, spot eğriye girmez.
    # Yalnız YTM çapraz sınaması için ve yalnız AKTİF olanlar çekilir.
    tahvil = [k for k, v in havuz.items()
              if v["sabit_nominal"] and v["strip"] == "tahvil"
              and _tarih(v["itfa"]) and _canli(v, (bugun - pd.Timedelta(days=10)).date(), b_d)]
    print(f"  evren: {len(havuz)} kıymet (güncel + arşiv) · "
          f"nominal sıfır kuponlu {len(nominal)} · TÜFEX anapara {len(tufex)} · "
          f"aktif kuponlu tahvil {len(tahvil)}")

    # --- (2) kupon ödeme tutarları ve sabitlik sınaması --------------------
    kuponlu = [k for k in nominal
               if havuz[k]["strip"] == "kupon" and havuz[k].get("oran_kod")]
    kupon_oransiz = [k for k in nominal
                     if havuz[k]["strip"] == "kupon" and not havuz[k].get("oran_kod")]
    odeme, oran_tani = oran_degerleri(havuz, kuponlu, yenile)
    degisken = [k for k, t in oran_tani.items() if not t["sabit"]]
    if degisken:
        uyar(f"DEĞİŞKEN KUPON: {len(degisken)} kupon strip'inin ödeme tutarı "
             "kendi penceresinde SABİT DEĞİL — değişken faizli kıymet nominal "
             "eğriye sızmış olabilir; bu strip'ler eğriden çıkarıldı.")
    if kupon_oransiz:
        print(f"    ({len(kupon_oransiz)} kupon strip'inin .ORAN kardeşi yok — "
              "arşivde 1546 kıymette bu eksik var; o strip'ler kullanılamaz)")
    # Ödemesi olmayan / değişken kupon strip'i eğriye giremez.
    nominal = [k for k in nominal
               if havuz[k]["strip"] == "anapara"
               or (k in odeme and oran_tani.get(k, {}).get("sabit"))]
    print(f"  nominal sıfır kuponlu evren (ödeme doğrulanmış): {len(nominal)}")

    # --- (3) fiyat tarihçeleri --------------------------------------------
    F = cek_fiyatlar(_plan(havuz, nominal, bas, bugun), "nominal strip fiyatı", yenile)
    T = cek_fiyatlar(_plan(havuz, tufex, bas, bugun), "TÜFEX anapara fiyatı", yenile)
    # Kuponlu tahvil fiyatı: yalnız son ~900 gün (çapraz sınama kesiti için).
    tahvil_plan = {k: (max(bugun - pd.Timedelta(days=PARCA_GUN - 1), bas), bugun)
                   for k in tahvil}
    B = cek_fiyatlar(tahvil_plan, "kuponlu tahvil fiyatı (YTM sınaması)", yenile)

    if F.empty:
        raise SystemExit("DUR: nominal strip fiyatı hiç gelmedi — eğri kurulamaz.")

    # --- (4) referans / beklenti serileri ---------------------------------
    G = cek_kume(GUNLUK, "gun", PARCA_GUN, yenile, etiket="referans faizler")
    A = cek_kume(AYLIK, "ay", 20000, yenile, etiket="beklenti / enflasyon")

    # BÜYÜKLÜK MERTEBESİ DENETİMİ — EVDS3'te birim alanı yok.
    for kaynak in (G, A):
        for ad in kaynak.columns:
            if ad not in MERTEBE:
                continue
            birim, alt, ust = MERTEBE[ad]
            s = kaynak[ad].dropna()
            if s.empty:
                continue
            v = float(s.iloc[-1])
            if not (alt <= v <= ust):
                uyar(f"MERTEBE: {ad} son değer {v:,.4f} — '{birim}' için beklenen "
                     f"[{alt:,.0f}, {ust:,.0f}] aralığının DIŞINDA. Birim tanımı "
                     "değişmiş olabilir (1000× hatası bu eşikte yakalanır).")

    # --- (5) künye tabloları ----------------------------------------------
    # Ödeme sütunu eğrinin ÇEKİRDEĞİDİR: anapara strip'i 100, kupon strip'i
    # kendi dönemsel kupon TUTARI (yıllık oran DEĞİL).
    with (VERI / "kunye_nominal.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "isin", "govde", "etiket", "strip", "ihrac", "itfa",
                    "odeme", "grup", "fiyat_bas", "fiyat_son"])
        for k in sorted(nominal, key=lambda x: havuz[x]["itfa"]):
            if k not in F.columns:
                continue
            v = havuz[k]
            w.writerow([k, v["isin"], v["govde"], v["etiket"], v["strip"],
                        v["ihrac"], v["itfa"],
                        100.0 if v["strip"] == "anapara" else odeme[k],
                        v["grup"], v.get("fiyat_bas", ""), v.get("fiyat_son", "")])
    with (VERI / "kunye_tufex.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "isin", "etiket", "ihrac", "itfa", "grup"])
        for k in sorted(tufex, key=lambda x: havuz[x]["itfa"]):
            if k not in T.columns:
                continue
            v = havuz[k]
            w.writerow([k, v["isin"], v["etiket"], v["ihrac"], v["itfa"], v["grup"]])
    with (VERI / "kunye_tahvil.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "isin", "govde", "etiket", "ihrac", "itfa"])
        for k in sorted(tahvil, key=lambda x: havuz[x]["itfa"]):
            if k not in B.columns:
                continue
            v = havuz[k]
            w.writerow([k, v["isin"], v["govde"], v["etiket"], v["ihrac"], v["itfa"]])

    # --- (6) TÜFE zinciri --------------------------------------------------
    cpi = tufe_zinciri(A)
    if not cpi.empty:
        cpi.to_csv(VERI / "tufe_zincir.csv", header=["tufe_2003_bazli"])

    # --- (7) dönem: VERİDEN okunur ----------------------------------------
    s_gun = son_gun(F)
    s_ay = A["pka_12a"].dropna().index[-1] if "pka_12a" in A.columns and A["pka_12a"].notna().any() else None
    print(f"  SON EĞRİ GÜNÜ : {gun_ad(s_gun)}  "
          f"({int(F.loc[s_gun].notna().sum())} kıymette gözlem)")
    if s_ay is not None:
        print(f"  SON ANKET AYI : {ay_ad(s_ay)}")

    # --- (8) denetimler ----------------------------------------------------
    for u in tazelik_denetimi(F, G, A, bugun):
        uyar(u)
    if "pka_12a_n" in A.columns and A["pka_12a_n"].notna().any():
        n_kat = float(A["pka_12a_n"].dropna().iloc[-1])
        if n_kat < PKA_N_ESIK:
            uyar(f"ANKET ZAYIF: PKA katılımcı sayısı {n_kat:.0f} "
                 f"(eşik {PKA_N_ESIK}). Beklenti serisi gürültülenir, Fisher "
                 "reel faizi oynar.")

    # --- (9) yazım ---------------------------------------------------------
    # Geniş fiyat matrisi GZİP'li CSV: 860 kıymet × 3.400 iş günü ham hâlde
    # ~10 MB, sıkıştırılmış ~2 MB. pandas .gz'yi hem yazar hem okur.
    F.to_csv(VERI / "fiyat_nominal.csv.gz", float_format="%.6f")
    if not T.empty:
        T.to_csv(VERI / "fiyat_tufex.csv.gz", float_format="%.6f")
    if not B.empty:
        B.to_csv(VERI / "fiyat_tahvil.csv.gz", float_format="%.6f")
    G.to_csv(VERI / "gunluk.csv")
    A.to_csv(VERI / "aylik.csv")

    durum = {
        "kosum": dt.datetime.now().isoformat(timespec="seconds"),
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        "son_ay": s_ay.strftime("%Y-%m-%d") if s_ay is not None else None,
        "tarihce_bas": TARIHCE_BAS,
        "istek_sayisi": _ISTEK["n"],
        "sure_sn": round(time.time() - t0, 1),
        "evren": {
            "toplam_kiymet": len(havuz),
            "nominal_sifir_kuponlu": len(nominal),
            "nominal_fiyati_gelen": int(F.shape[1]),
            "tufex_anapara": len(tufex),
            "tufex_fiyati_gelen": int(T.shape[1]) if not T.empty else 0,
            "aktif_kuponlu_tahvil": len(tahvil),
            "kupon_oran_kardesi_yok": len(kupon_oransiz),
            "degisken_kupon_atilan": len(degisken),
        },
        "tufe_zinciri": {
            "kat": cpi.attrs.get("zincir_kat") if not cpi.empty else None,
            "ortusme_ay": cpi.attrs.get("zincir_ay") if not cpi.empty else None,
        },
        # AYRIŞTIRMA TANISI — sayfadaki "tek biçim varsayan bir ayrıştırıcı şu
        # kadarını düşürürdü" cümlesi buradan okunur; elle yazılmış sayı YOK.
        "ayristirma_test": dict(_AYRISTIRMA_TEST),
        "gunluk_seri": int(G.shape[1]), "aylik_seri": int(A.shape[1]),
        "uyarilar": list(_UYARI),
    }
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazıldı: data/fiyat_nominal.csv.gz ({F.shape[0]}x{F.shape[1]}), "
          f"fiyat_tufex.csv.gz ({T.shape[0] if not T.empty else 0}x"
          f"{T.shape[1] if not T.empty else 0}), gunluk.csv, aylik.csv")
    print(f"  {_ISTEK['n']} EVDS isteği · {time.time() - t0:.0f} sn")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return durum


# --------------------------------------------------------------------------- dönem
_SON: dict[str, str] = {}
# Eğrinin "dolu" sayılması için gereken en az sıfır kuponlu nokta sayısı.
# Son gün kısmi dolu olabilir (TCMB bazı kıymetleri gün içinde geç basıyor);
# eşik altındaki günü çıpa yapmak eğriyi bir avuç noktadan kurar.
EGRI_MIN_NOKTA = 30


def son_gun(F: pd.DataFrame | None = None) -> pd.Timestamp:
    """Analizin çıpa günü: eğrinin DOLU olduğu son İŞ GÜNÜ. Sabit tarih YASAK.

    HAFTA SONU ELENİR. TCMB gösterge değeri takvim günü işliyor (Cumartesi ve
    Pazar fiyatı Cuma'nın tekrarı DEĞİL — ölçüldü), yani eğri hafta sonu da
    "dolu" görünür. Ama TLREF, politika faizi ve AOFM iş günü serileridir:
    çıpa hafta sonuna düşerse taşıma ve reel faiz ölçüleri boş çıkar ve sayfa
    "veri var ama sayı yok" durumuna düşer. Çıpa bu yüzden iş gününe çekilir.
    """
    if "gun" in _SON:
        return pd.Timestamp(_SON["gun"])
    if F is None:
        F = pd.read_csv(VERI / "fiyat_nominal.csv.gz", index_col=0, parse_dates=True)
    n = F.notna().sum(axis=1)
    dolu = n[(n >= EGRI_MIN_NOKTA) & (n.index.dayofweek < 5)]
    if dolu.empty:
        raise RuntimeError(
            f"son_gun: hiçbir iş gününde {EGRI_MIN_NOKTA} sıfır kuponlu nokta "
            "yok — EVDS çekimi düşmüş ya da sınıflandırma bozulmuş olabilir.")
    _SON["gun"] = dolu.index[-1].strftime("%Y-%m-%d")
    return dolu.index[-1]


def tazelik_denetimi(F: pd.DataFrame, G: pd.DataFrame, A: pd.DataFrame,
                     bugun: pd.Timestamp) -> list[str]:
    uy: list[str] = []
    n = F.notna().sum(axis=1)
    dolu = n[(n >= EGRI_MIN_NOKTA) & (n.index.dayofweek < 5)]
    if dolu.empty:
        uy.append("TAZELİK: eğri hiçbir iş gününde dolu değil.")
    else:
        gecikme = (bugun - dolu.index[-1]).days
        etiket, tol = TAZELIK_EGRI
        if gecikme > tol:
            uy.append(f"TAZELİK: {etiket} son dolu günü "
                      f"{dolu.index[-1]:%d.%m.%Y} ({gecikme} gün önce, tolerans "
                      f"{tol} gün). Yayın durmuş olabilir.")
    for ad, (etiket, tol) in TAZELIK_GUNLUK.items():
        if ad not in G.columns or G[ad].dropna().empty:
            uy.append(f"TAZELİK: '{etiket}' hiç yüklenemedi.")
            continue
        son = G[ad].dropna().index[-1]
        gecikme = (bugun - son).days
        if gecikme > tol:
            uy.append(f"TAZELİK: {etiket} son gözlemi {son:%d.%m.%Y} "
                      f"({gecikme} gün önce, tolerans {tol} gün).")
    for ad, (etiket, tol) in TAZELIK_AYLIK.items():
        if ad not in A.columns or A[ad].dropna().empty:
            uy.append(f"TAZELİK: '{etiket}' hiç yüklenemedi.")
            continue
        son = A[ad].dropna().index[-1]
        # Aylık seride tarih ayın 1'idir; gecikme AY SONUNDAN ölçülür.
        ay_sonu = son + pd.offsets.MonthEnd(0)
        gecikme = (bugun - ay_sonu).days
        if gecikme > tol:
            uy.append(f"TAZELİK: {etiket} son gözlemi {ay_ad(son)} "
                      f"({gecikme} gün önce, tolerans {tol} gün).")
    return uy


if __name__ == "__main__":
    kos(yenile="--yenile" in sys.argv)
