"""TLREF'in aynı gün uzantısı — yöneticisinin (Borsa İstanbul) kendi dosyasından.

NEDEN. Bütün hatlar TLREF'i EVDS'in TP.BISTTLREF.ORAN / .KAPANIS serilerinden
okuyor ve EVDS o serileri BİR İŞ GÜNÜ GERİDEN veriyor. Depodaki koşu tarihçesi
ile 23.09.2026 bulut keşfi (bulten/kesif_tlref_bist*.py) aynı şeyi ölçtü:
T gününün TLREF'i EVDS'e T+1 günü sabaha doğru düşüyor (22.09 17:08 koşusunda
hâlâ 21.09; 23.09 06:56'da hâlâ 21.09, 07:13'te 22.09). Sabah 04:20 UTC'de
yazılan bülten bu yüzden bir önceki seansın TLREF'ini HİÇBİR GÜN taşıyamıyordu
— 23.09 sayısı "TLREF 21 Eylül itibarıyla" yazdı, oysa 22.09'un değeri Borsa
İstanbul'da 22.09 13:00 GMT'den beri yayımlıydı.

KAYNAK SÖZLEŞMESİ ÖLÇÜLDÜ, VARSAYILMADI. Borsa İstanbul TLREF'in yöneticisidir
ve İKİ dosya yayımlar (adresler sayfanın indirme düğmelerinden çözüldü, tahmin
edilmedi; bulten/kesif_tlref_gunluk.py):
  · GÜNLÜK dosya — yalnız o günün değeri, 13:00 GMT'de (Last-Modified
    22.09 13:00:09). Düz ASCII, başlıkları 'TARIH … DEGER' / 'TARIH … KAPANIS'.
  · TARİHSEL zip — 2018'den bugüne, 16:30 GMT civarı (22.09 16:34). UTF-16.
Tarihsel dosya EVDS ile örtüşen 1.911 günün 1.911'inde oran olarak BİREBİR aynı
(|Δ| = 0), endeks olarak 1.799 günün 1.799'unda 0,00009'dan yakın. Yani EVDS bu
dosyanın bir aynasıdır; aynanın gecikmesi kaynağın gecikmesi değildir.

İKİ DOSYA BİRDEN, çünkü ilk yazım yalnız tarihsel zip'i okuyordu ve inceleme
ölçtü: Fonlama'nın günün son koşusu çoğu gün 16:30'dan ÖNCE bitiyor (14.09
15:32 · 17.09 14:21 · 18.09 13:25 · 21.09 15:35); o günlerde zip T'yi henüz
taşımıyor ve uzantı "gerek yok" deyip hiçbir şey eklemiyordu — düzelttiğini
söylediği kusurun ta kendisi. Günlük dosya T'yi 13:00'da verir; tarihsel dosya
EVDS ile birebirliği sınamak için gerekir (günlük dosyanın tek günü örtüşmez).
İkisi de aynı günü taşıdığında değerleri birebir aynı olmalıdır, yoksa uzantı
yapılmaz.

KURAL. EVDS birincil kalır; bu modül yalnız EVDS'in SON gününden SONRAKİ
günleri ekler. Ve her koşuda sözleşmeyi yeniden sınar: örtüşen günlerden biri
toleransın dışına çıkarsa (kaynak yöntemini değiştirdi, dosya bozuk, ayrıştırma
kaydı) uzantı YAPILMAZ ve sebep adıyla döner — bir kez doğrulanıp bırakılan
eşitlik, kaynak değiştiği gün sessizce yanlışa döner. Uzantının TAVANI var
(`AZAMI_UZANTI`): EVDS'in ölçülen gecikmesi bir iş günü; aynanın kendisi
donarsa BIST'le doldurmak birincil kaynağın ölümünü GİZLERDİ.

ÇERÇEVEYE SATIR EKLENMEZ (`cerceveye_ekle`). Yalnız çerçevenin VAR OLAN günleri
doldurulur. İnceleme ölçtü: eklenen bir satırda TLREF dışındaki her sütun boş
kalır, Fonlama'nın marjinal faiz kuralı o günü "TLREF (vekil)" diye yayımlar,
rejim sayaçları ölçülmemiş günü sayar ve pandas birleştirmesi dizin adını
('tarih') düşürüp Carry ile Makroihtiyati'nin okumasını çökertir. Fonlama ve
DİBS çerçeveleri her iş gününü politika faizi serisiyle zaten taşıdığı için
uzantının ihtiyacı olan satır normal koşuda vardır.

SON İYİ KOPYA (`onbellek`). Başarılı her indirme hattın `data/cache`ine yazılır
ve indirme düşerse oradan okunur. Kaynağın yayımladığı bir değer sonradan
değişmez, yani eski kopya örtüşen günlerde sınamayı yine geçer. Kopya olmasaydı
bir koşuda uzanan tarih, BIST'e ulaşılamayan bir sonraki koşuda GERİ çekilir ve
guncelle.py'nin gerileme kapısı hattı durdururdu — isteğe bağlı bir iyileştirme,
yayını durduran bir arızaya dönerdi.

AĞ yalnız `indir`dedir; ayrıştırma ve uzatma saf fonksiyonlardır ve duman
sınaması onları gerçek dosyanın biçimiyle kurulan sahte girdiyle koşturur;
`indir`in kendisi yerel bir sunucuya karşı koşar.
"""
from __future__ import annotations

import datetime as _dt
import io
import zipfile
from pathlib import Path

KAYNAK_AD = "Borsa İstanbul TLREF dosyası"
_KOK = "https://www.borsaistanbul.com/datum/"
# (tür, cins) → adres. Cinsler: "tarihsel" (zip, sözleşme sınaması) ve
# "gunluk" (o günün tek değeri, 13:00 GMT).
ADRES = {
    ("oran", "tarihsel"): _KOK + "TLREFORANI_D.zip",
    ("oran", "gunluk"): _KOK + "tlreforani.csv",
    ("endeks", "tarihsel"): _KOK + "BISTTLREFENDEKSI_D.zip",
    ("endeks", "gunluk"): _KOK + "bisttlrefendeksi.csv",
}
# Sütun ADIYLA sorulur (dosyaların gerçek başlıkları, 23.09.2026 ölçümü):
#   oran   tarihsel: 'TARIH/DATE' · … · 'DEGER/VALUE'      günlük: 'TARIH' · … · 'DEGER'
#   endeks tarihsel: 'Tarih (GG.AA.YYYY) / …' · 'Kapanış Değeri / Closing Value'
#          günlük:   'TARIH' · 'KAPANIS' · 'ACILIS' · 'EN DUSUK' · 'EN YUKSEK'
SUTUN = {
    "oran": (("tarih",), ("deger", "değer", "value")),
    "endeks": (("tarih",), ("kapanış", "kapanis", "closing")),
}
# Birebirlik toleransı: oran dört ondalıkla yayımlanır; endeksi EVDS dört
# ondalığa kırpıyor (ölçülen en büyük fark 0,00009).
TOLERANS = {"oran": 5e-5, "endeks": 5e-4}
# Sözleşme ancak yeterince örtüşen günde sınanabilir; daha azı "sınanmadı"dır.
ASGARI_ORTUSME = 5
# Uzantı en çok bu kadar iş günü ekler. Ölçülen gecikme bir iş günü (EVDS T'yi
# T+1 sabahı verir, BIST 13:00'da); ikinci gün EVDS'in bir günlük ek
# yavaşlığına pay. Fazlası aynanın DONDUĞUNU gösterir ve okura söylenir.
AZAMI_UZANTI = 2
# Makullük: TLREF yüzde olarak yayımlanır.
ARALIK = {"oran": (0.0, 500.0), "endeks": (0.0, 1e9)}
# İstek başlığı. HTTP başlıkları latin-1 ile kodlanır: Türkçe bir harf
# ("hattı") isteği daha AĞA ÇIKMADAN UnicodeEncodeError ile düşürür — 23.09.2026
# uçtan uca koşusu tam bunu ölçtü, duman ise `indir`i sahteyle değiştirdiği için
# görmedi. Değer, keşif koşularında Borsa İstanbul'dan 200 alan başlığın kendisi.
BASLIK = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/148.0.0.0 Safari/537.36")}


def _metin(ham: bytes) -> str:
    """Tarihsel dosyalar UTF-16 (BOM ÿþ), günlükler tek baytlı — ikisi de okunur."""
    if ham[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return ham.decode("utf-16")
    for kod in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            return ham.decode(kod)
        except UnicodeDecodeError:
            continue
    return ham.decode("latin-1", "ignore")


def _tarih(s: str) -> _dt.date | None:
    s = s.strip().strip('"')
    for f in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(s[:10], f).date()
        except ValueError:
            continue
    return None


def _sayi(s: str) -> float | None:
    s = s.strip().strip('"')
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(",", "")          # binlik virgül: '15,145,000,000'
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def ayristir(ham: bytes, tur: str) -> dict[_dt.date, float]:
    """Zip'li ya da düz CSV → {gün: değer}. Tarih/değer sütunu ADIYLA bulunur.

    Bulunamazsa ValueError, dosyanın GERÇEK başlıklarıyla — "bulunamadı" deyip
    neyin bulunabileceğini söylememek her düzeltme için ayrı bir keşif demekti.
    """
    if ham[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(ham))
        ham = z.read(z.namelist()[0])
    satirlar = [s for s in _metin(ham).splitlines() if s.strip()]
    if not satirlar:
        raise ValueError("boş dosya")
    bas = satirlar[0]
    ayrac = max((";", ",", "\t"), key=bas.count)
    baslik = [h.strip().lower() for h in bas.split(ayrac)]
    t_ad, d_ad = SUTUN[tur]
    ti = next((i for i, h in enumerate(baslik) if any(a in h for a in t_ad)), None)
    di = next((i for i, h in enumerate(baslik) if any(a in h for a in d_ad)), None)
    if ti is None or di is None:
        raise ValueError(f"{tur}: tarih/değer sütunu bulunamadı; başlıklar: {baslik}")
    alt, ust = ARALIK[tur]
    out: dict[_dt.date, float] = {}
    for s in satirlar[1:]:
        p = s.split(ayrac)
        if len(p) <= max(ti, di):
            continue
        g, v = _tarih(p[ti]), _sayi(p[di])
        # İkinci başlık satırı (İngilizce) ve dipnot satırları tarih taşımaz.
        if g is None or v is None or not (alt < v < ust):
            continue
        out[g] = v
    return out


def indir(tur: str, cins: str = "tarihsel", zaman_asimi: int = 30) -> bytes:
    """Ağa çıkar. Standart kütüphane (urllib): hatların kendi .venv'leri
    `requests` taşımayabilir (DİBS taşımıyor) ve eksik paket yerelde her koşuda
    okura sahte bir "ulaşılamadı" satırı basardı."""
    import urllib.request
    istek = urllib.request.Request(ADRES[(tur, cins)], headers=BASLIK)
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
        return r.read()


def _kopya_yolu(onbellek: Path | None, tur: str, cins: str) -> Path | None:
    return Path(onbellek) / f"tlref_bist_{tur}_{cins}.bin" if onbellek else None


def bist_serisi(tur: str, onbellek: Path | None = None) -> tuple[dict[_dt.date, float], dict]:
    """Tarihsel + günlük dosya → {gün: değer} ve nereden geldiği. Hiç YÜKSELTMEZ
    ağ için; tarihsel dosya ne indirilebildi ne kopyası var ise boş döner.

    Başarılı indirme `onbellek`e yazılır; düşen indirme oradan okunur.
    İki dosya aynı günü taşıyıp değerleri ayrışırsa ValueError — hangi dosyanın
    doğru olduğu bilinemez, uzantı yapılmamalı.
    """
    parca: dict[str, dict[_dt.date, float]] = {}
    nereden: dict[str, str] = {}
    bicim: list[str] = []        # ayrıştırılamayan dosyalar, GERÇEK başlıklarıyla
    for cins in ("tarihsel", "gunluk"):
        yol = _kopya_yolu(onbellek, tur, cins)
        try:
            ham = indir(tur, cins)
        except Exception as ex:  # ağ
            ham, hata = None, type(ex).__name__
        if ham is not None:
            try:
                parca[cins] = ayristir(ham, tur)      # ayrışmayan dosya kopyalanmaz
                nereden[cins] = "canlı"
                if yol:
                    try:
                        yol.parent.mkdir(parents=True, exist_ok=True)
                        yol.write_bytes(ham)
                    except OSError:
                        pass
                continue
            except Exception as ex:  # ValueError (başlık), BadZipFile, kodlama
                # Biçim değişti: "ulaşılamadı" demek yanlış sebep olurdu ve
                # dosyanın gerçek başlıkları (ayristir'ın mesajı) kaybolurdu.
                hata = "biçim"
                bicim.append(f"{cins}: {type(ex).__name__}: {ex}")
        if yol and yol.exists():
            try:
                parca[cins] = ayristir(yol.read_bytes(), tur)
                nereden[cins] = f"son iyi kopya ({hata})"
                continue
            except Exception:
                pass
        nereden[cins] = f"yok ({hata})"
    seri = dict(parca.get("tarihsel") or {})
    if not seri:
        return {}, {"nereden": nereden, "bicim": bicim}
    tol = TOLERANS[tur]
    for g, v in (parca.get("gunluk") or {}).items():
        if g in seri and abs(seri[g] - v) >= tol:
            raise ValueError(f"{tur}: günlük dosya ile tarihsel dosya {g.isoformat()} "
                             f"gününde ayrışıyor ({v} ile {seri[g]})")
        seri.setdefault(g, v)
    return seri, {"nereden": nereden, "bicim": bicim}


def uzat(seri, bist: dict[_dt.date, float], tur: str, bugun: _dt.date | None = None):
    """EVDS serisini, son gününden SONRAKİ BIST günleriyle uzatır. SAF.

    `seri`: tarih indeksli pandas Series (NaN olabilir). Döner (seri, bilgi);
    bilgi["durum"] ∈ {"uzatildi", "gerek_yok", "ayrisma", "ortusme_yetersiz",
    "evds_geride", "bos"}. Uzatılmayan her hâlde seri DOKUNULMADAN döner.
    """
    import pandas as pd
    bugun = bugun or _dt.date.today()
    if not bist:
        return seri, {"durum": "bos"}
    dolu = seri.dropna()
    evds = {pd.Timestamp(i).date(): float(v) for i, v in dolu.items()}
    ortak = sorted(set(evds) & set(bist))
    if len(ortak) < ASGARI_ORTUSME:
        return seri, {"durum": "ortusme_yetersiz", "ortusen": len(ortak)}
    tol = TOLERANS[tur]
    for g in ortak:
        if abs(evds[g] - bist[g]) >= tol:
            return seri, {"durum": "ayrisma", "gun": g.isoformat(),
                          "evds": evds[g], "bist": bist[g], "ortusen": len(ortak)}
    son = max(evds) if evds else None
    yeni = sorted(g for g in bist if (son is None or g > son)
                  and g <= bugun and g.weekday() < 5)
    if not yeni:
        return seri, {"durum": "gerek_yok", "ortusen": len(ortak),
                      "son": son.isoformat() if son else None}
    if len(yeni) > AZAMI_UZANTI:
        return seri, {"durum": "evds_geride", "gunler": [g.isoformat() for g in yeni],
                      "evds_son": son.isoformat() if son else None, "ortusen": len(ortak)}
    s = seri.copy()
    for g in yeni:
        s.loc[pd.Timestamp(g)] = bist[g]
    s = s.sort_index()
    return s, {"durum": "uzatildi", "gunler": [g.isoformat() for g in yeni],
               "ortusen": len(ortak), "kaynak": KAYNAK_AD}


def _bicimle():
    """Okur satırı sayıyı ve tarihi ortak/bicim sözleşmesiyle yazar."""
    try:
        from bicim import sayi, tarih_kisa
        return sayi, tarih_kisa
    except ImportError:
        return (lambda v, o=4: f"{v:.{o}f}".replace(".", ",")), (lambda t: t)


def cerceveye_ekle(df, kolonlar: dict[str, str], bugun: _dt.date | None = None,
                   onbellek: Path | None = None):
    """{kolon: tür} için BIST serisi → uzat → çerçevenin VAR OLAN günlerine yaz.
    Hiç YÜKSELTMEZ ve SATIR EKLEMEZ (modül başlığı: neden).

    Döner (df, uyarilar, bilgi). Uyarı cümleleri okur dilindedir (hattın
    uyarilar.json'u sayfaya olduğu gibi basılır): kod adı, dosya adı yok.
    """
    uyarilar: list[str] = []
    bilgi: dict[str, dict] = {}
    df = df.copy()
    sayi_yaz, tarih_yaz = _bicimle()

    def uyar(u: str) -> None:
        if u not in uyarilar:        # oran ve endeks aynı yayımcının iki dosyası
            uyarilar.append(u)

    for kolon, tur in kolonlar.items():
        if kolon not in df.columns:
            continue
        try:
            bist, kay = bist_serisi(tur, onbellek)
        except ValueError as ex:
            bilgi[kolon] = {"durum": "ayrisma", "hata": str(ex)}
            uyar("TLREF: Borsa İstanbul'un günlük ve tarihsel dosyaları aynı günde "
                 "ayrışıyor; aynı gün uzantısı yapılmadı.")
            continue
        for b_ in kay.get("bicim") or []:
            print(f"  ! TLREF · Borsa İstanbul dosyası ayrıştırılamadı — {b_}")
        if not bist:
            bilgi[kolon] = {"durum": "indirilemedi", **kay}
            if kay.get("bicim"):
                uyar("TLREF: Borsa İstanbul dosyasının biçimi tanınmadı; son gün "
                     "EVDS'in verdiği gün olarak kaldı.")
            else:
                uyar("TLREF: Borsa İstanbul dosyasına ulaşılamadı; son gün "
                     "EVDS'in verdiği gün olarak kaldı.")
            continue
        yeni, b = uzat(df[kolon], bist, tur, bugun)
        b.update(kay)
        bilgi[kolon] = b
        if b["durum"] == "ayrisma":
            ond = 4 if tur == "oran" else 5
            uyar(f"TLREF: Borsa İstanbul dosyası ile EVDS {tarih_yaz(b['gun'])} gününde "
                 f"ayrışıyor ({sayi_yaz(b['bist'], ond)} ile {sayi_yaz(b['evds'], ond)}); "
                 f"aynı gün uzantısı yapılmadı.")
        elif b["durum"] == "ortusme_yetersiz":
            uyar("TLREF: Borsa İstanbul dosyası ile EVDS'in örtüşen günleri kaynak "
                 "sözleşmesini sınamaya yetmiyor; aynı gün uzantısı yapılmadı.")
        elif b["durum"] == "evds_geride":
            uyar(f"TLREF: EVDS serisi {tarih_yaz(b['evds_son'])} gününde duruyor, "
                 f"Borsa İstanbul {len(b['gunler'])} iş günü ileride; birincil kaynak "
                 f"donmuş olabilir, aynı gün uzantısı yapılmadı.")
        if b["durum"] != "uzatildi":
            continue
        import pandas as pd
        ek = [pd.Timestamp(g) for g in b["gunler"]]
        icerde = [g for g in ek if g in df.index]
        disarida = [g.date().isoformat() for g in ek if g not in df.index]
        if icerde:
            df.loc[icerde, kolon] = yeni.loc[icerde].values
        b["gunler"] = [g.date().isoformat() for g in icerde]
        if disarida:
            # Çerçevenin o gün satırı yok (öbür seriler henüz yayımlanmadı):
            # normal bir erken koşu hâli, okura değil kayda.
            b["satirsiz"] = disarida
        if not icerde:
            b["durum"] = "satir_yok"
    return df, uyarilar, bilgi
