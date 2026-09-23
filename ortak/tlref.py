"""TLREF'in aynı gün uzantısı — yöneticisinin (Borsa İstanbul) kendi dosyasından.

NEDEN. Bütün hatlar TLREF'i EVDS'in TP.BISTTLREF.ORAN / .KAPANIS serilerinden
okuyor ve EVDS o serileri BİR İŞ GÜNÜ GERİDEN veriyor. Depodaki koşu tarihçesi
ile 23.09.2026 bulut keşfi (bulten/kesif_tlref_bist*.py) aynı şeyi ölçtü:
T gününün TLREF'i EVDS'e T+1 günü öğlene doğru düşüyor (22.09 17:08 koşusunda
hâlâ 21.09; 23.09 06:56'da hâlâ 21.09). Sabah 04:20 UTC'de yazılan bülten bu
yüzden bir önceki seansın TLREF'ini HİÇBİR GÜN taşıyamıyordu — 23.09 sayısı
"TLREF 21 Eylül itibarıyla" yazdı, oysa 22.09'un değeri Borsa İstanbul'da
22.09 13:00 GMT'den beri yayımlıydı.

KAYNAK SÖZLEŞMESİ ÖLÇÜLDÜ, VARSAYILMADI. Borsa İstanbul TLREF'in yöneticisidir
ve günlük dosyayı "16:00'dan sonra", tarihsel dosyayı "19:30'dan sonra"
yayımlar (sayfanın kendi ilanı; adresler sayfanın indirme düğmelerinden
çözüldü, tahmin edilmedi). Tarihsel dosya EVDS ile örtüşen 1.911 günün
1.911'inde oran olarak BİREBİR aynı (|Δ| = 0), endeks olarak 1.799 günün
1.799'unda 0,00009'dan yakın (EVDS dört ondalığa kırpıyor). Yani EVDS bu
dosyanın bir aynasıdır; aynanın gecikmesi kaynağın gecikmesi değildir.

KURAL. EVDS birincil kalır; bu modül yalnız EVDS'in SON gününden SONRAKİ
günleri ekler. Ve her koşuda sözleşmeyi yeniden sınar: örtüşen günlerden biri
toleransın dışına çıkarsa (kaynak yöntemini değiştirdi, dosya bozuk, ayrıştırma
kaydı) uzantı YAPILMAZ ve sebep adıyla döner — bir kez doğrulanıp bırakılan
eşitlik, kaynak değiştiği gün sessizce yanlışa döner.

AĞ yalnız `indir`dedir; ayrıştırma ve uzatma saf fonksiyonlardır ve duman
sınaması onları gerçek dosyanın biçimiyle kurulan sahte girdiyle koşturur.
"""
from __future__ import annotations

import datetime as _dt
import io
import zipfile

KAYNAK_AD = "Borsa İstanbul TLREF dosyası"
ADRES = {
    "oran": "https://www.borsaistanbul.com/datum/TLREFORANI_D.zip",
    "endeks": "https://www.borsaistanbul.com/datum/BISTTLREFENDEKSI_D.zip",
}
# Sütun ADIYLA sorulur (dosyanın gerçek başlıkları, 23.09.2026 ölçümü):
#   oran:   'TARIH/DATE' · … · 'DEGER/VALUE'
#   endeks: 'Tarih (GG.AA.YYYY) / Date (DD.MM.YYYY)' · … · 'Kapanış Değeri / Closing Value'
SUTUN = {
    "oran": (("tarih",), ("deger", "değer", "value")),
    "endeks": (("tarih",), ("kapanış", "kapanis", "closing")),
}
# Birebirlik toleransı: oran dört ondalıkla yayımlanır; endeksi EVDS dört
# ondalığa kırpıyor (ölçülen en büyük fark 0,00009).
TOLERANS = {"oran": 5e-5, "endeks": 5e-4}
# Sözleşme ancak yeterince örtüşen günde sınanabilir; daha azı "sınanmadı"dır.
ASGARI_ORTUSME = 5
# Makullük: TLREF yüzde olarak yayımlanır.
ARALIK = {"oran": (0.0, 500.0), "endeks": (0.0, 1e9)}


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


def indir(tur: str, zaman_asimi: int = 30) -> bytes:
    """Ağa çıkar. requests; zaman aşımı açık (ortak/sitecustomize de dayatır)."""
    import requests
    r = requests.get(ADRES[tur], timeout=zaman_asimi,
                     headers={"User-Agent": "Mozilla/5.0 (tto-trading veri hattı)"})
    r.raise_for_status()
    return r.content


def uzat(seri, bist: dict[_dt.date, float], tur: str, bugun: _dt.date | None = None):
    """EVDS serisini, son gününden SONRAKİ BIST günleriyle uzatır. SAF.

    `seri`: tarih indeksli pandas Series (NaN olabilir). Döner (seri, bilgi);
    bilgi["durum"] ∈ {"uzatildi", "gerek_yok", "ayrisma", "ortusme_yetersiz",
    "bos"}. Uzatılmayan her hâlde seri DOKUNULMADAN döner.
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
    s = seri.copy()
    for g in yeni:
        s.loc[pd.Timestamp(g)] = bist[g]
    s = s.sort_index()
    return s, {"durum": "uzatildi", "gunler": [g.isoformat() for g in yeni],
               "ortusen": len(ortak), "kaynak": KAYNAK_AD}


def cerceveye_ekle(df, kolonlar: dict[str, str], bugun: _dt.date | None = None):
    """{kolon: tür} için indir → ayrıştır → uzat. Hiç YÜKSELTMEZ.

    Döner (df, uyarilar, bilgi). Uyarı cümleleri okur dilindedir (hattın
    uyarilar.json'u sayfaya olduğu gibi basılır): kod adı, dosya adı yok.
    """
    import pandas as pd
    uyarilar: list[str] = []
    bilgi: dict[str, dict] = {}
    df = df.copy()
    for kolon, tur in kolonlar.items():
        if kolon not in df.columns:
            continue
        try:
            bist = ayristir(indir(tur), tur)
        except Exception as ex:  # ağ, biçim — uzantı bir iyileştirmedir, ölçümü düşürmez
            bilgi[kolon] = {"durum": "indirilemedi", "hata": f"{type(ex).__name__}"}
            uyarilar.append(f"TLREF: Borsa İstanbul dosyasına ulaşılamadı; son gün "
                            f"EVDS'in verdiği gün olarak kaldı.")
            continue
        yeni, b = uzat(df[kolon], bist, tur, bugun)
        bilgi[kolon] = b
        if b["durum"] == "ayrisma":
            # Sayı ve tarih ortak/bicim sözleşmesiyle: bu satır sayfaya basılır.
            try:
                from bicim import sayi as _sayi_yaz, tarih_kisa as _tarih_yaz
            except ImportError:
                _sayi_yaz = lambda v, o=4: f"{v:.{o}f}".replace(".", ",")  # noqa: E731
                _tarih_yaz = lambda t: t  # noqa: E731
            ond = 4 if tur == "oran" else 5
            uyarilar.append(
                f"TLREF: Borsa İstanbul dosyası ile EVDS {_tarih_yaz(b['gun'])} gününde "
                f"ayrışıyor ({_sayi_yaz(b['bist'], ond)} ile {_sayi_yaz(b['evds'], ond)}); "
                f"aynı gün uzantısı yapılmadı.")
        if b["durum"] != "uzatildi":
            continue
        ek = [pd.Timestamp(g) for g in b["gunler"]]
        eksik = [g for g in ek if g not in df.index]
        if eksik:
            df = pd.concat([df, pd.DataFrame(index=pd.DatetimeIndex(eksik))]).sort_index()
        df.loc[ek, kolon] = yeni.loc[ek].values
    return df, uyarilar, bilgi
