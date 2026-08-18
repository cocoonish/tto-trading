# -*- coding: utf-8 -*-
"""
TCMB EN 24/17 replikasyonu — veri katmanı.

Kaynaklar:
  * TCMB EVDS3 API (evds3.tcmb.gov.tr/igmevdsms-dis) — TÜFE (2025=100, COICOP-2018,
    2005'e geri taşınmış), TÜFE (2003=100, arşiv), Yİ-ÜFE, Yeni Kiracı Kira Endeksi.
  * TÜİK MEDAS — Tüketici Madde Fiyatları (2003=100), 2005/01–2022/04 (yayın Nisan
    2022'de durdu). src/medas_harvest.py ile indirildi.
  * TÜİK Veri Portalı istatistiksel tablolar — temel başlık ağırlıkları, ticaret-hizmet
    ciro endeksleri (2015=100, arşiv).
  * Asgari Ücret Tespit Komisyonu kararları (Resmî Gazete) — brüt asgari ücret.

Her indirme data/cache altına yazılır ve output/log/veri.log'a kaynak+zaman damgası düşülür.
"""
import os
import pathlib
import io, json, time, pathlib, datetime
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
RAW = ROOT / "data" / "raw"
LOGD = ROOT / "output" / "log"
for p in (CACHE, RAW, LOGD):
    p.mkdir(parents=True, exist_ok=True)

EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
# EVDS anahtarı kaynak koda GÖMÜLMEZ. Sırayla: TTO_EVDS_KEY ortam değişkeni →
# proje kökündeki .evds_key dosyası (.gitignore'da). İkisi de yoksa açık hata.
def _evds_anahtari() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    yol = pathlib.Path(__file__).resolve().parent.parent / ".evds_key"
    if yol.exists():
        try:
            a = yol.read_text(encoding="utf-8").strip()
        except OSError:
            a = ""
        if a:
            return a
    raise RuntimeError(
        "EVDS anahtarı bulunamadı: export TTO_EVDS_KEY=<anahtar> ya da "
        f"{yol} dosyasına yazın (.gitignore'da)."
    )

EVDS_KEY = _evds_anahtari()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

_logf = open(LOGD / "veri.log", "a", encoding="utf-8")
def log(msg):
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    _logf.write(line + "\n"); _logf.flush()


# ----------------------------------------------------------------------------- EVDS
# Önbellek tazelik sınırı (saat). Eskiden dosya varsa SÜRESİZ okunuyordu ve hiçbir
# çağıran yenile=True vermiyordu → EVDS verisi ilk indirildiği günde donmuştu; hat her
# ay "koşuyor", grafik üretiyor ama yeni TÜFE'yi hiç görmüyordu (sessiz bayatlama).
CACHE_TTL_SAAT = 24


def _cache_taze(cpath):
    if not cpath.exists():
        return False
    yas_saat = (datetime.datetime.now().timestamp() - cpath.stat().st_mtime) / 3600
    return yas_saat < CACHE_TTL_SAAT


def evds_cek(kod, start="01-01-2005", end=None, yenile=False):
    """Tek EVDS serisini aylık frekansta çeker; cache'e yazar. Dönen: DatetimeIndex'li Series.

    Önbellek 24 saatten tazeyse okunur; değilse EVDS'e gidilir. Ağ hatasında eski
    önbelleğe düşülür (UYARI ile) — çevrimdışı koşu çalışır ama sessiz kalmaz.
    end verilmezse bugün+1 ay (eskiden '01-12-2026' sabitti: Aralık 2026'dan sonra
    hiçbir yeni gözlem gelmezdi)."""
    guvenli = kod.replace(".", "_")
    cpath = CACHE / f"evds_{guvenli}.csv"
    if cpath.exists() and (_cache_taze(cpath) and not yenile):
        s = pd.read_csv(cpath, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = kod
        return s
    if end is None:
        end = (pd.Timestamp.today() + pd.DateOffset(months=1)).strftime("01-%m-%Y")
    url = f"{EVDS_BASE}series={kod}&startDate={start}&endDate={end}&type=json"
    try:
        r = requests.get(url, headers={"key": EVDS_KEY, "User-Agent": UA}, timeout=60)
        r.raise_for_status()
        items = r.json().get("items", [])
    except Exception as e:
        if cpath.exists():
            log(f"UYARI: EVDS erişilemedi ({kod}: {e}); ESKİ önbellek kullanılıyor "
                f"(dosya {cpath.name}, {(datetime.datetime.now().timestamp() - cpath.stat().st_mtime) / 86400:.0f} gün)")
            s = pd.read_csv(cpath, index_col=0, parse_dates=True).iloc[:, 0]
            s.name = kod
            return s
        raise
    if not items:
        raise RuntimeError(f"EVDS boş döndü: {kod}")
    df = pd.DataFrame(items)
    kolon = kod.replace(".", "_")
    df["tarih"] = pd.to_datetime(df["Tarih"], format="%Y-%m")
    s = pd.to_numeric(df.set_index("tarih")[kolon], errors="coerce").dropna()
    s.name = kod
    s.to_csv(cpath)
    log(f"EVDS indirildi: {kod} ({s.index.min():%Y-%m} → {s.index.max():%Y-%m}, {len(s)} gözlem)")
    time.sleep(0.4)
    return s


# Çekilecek EVDS serileri
EVDS_SERILER = {
    # --- Yeni baz: TÜFE (2025=100), COICOP-2018, 2005'e backcast ---
    "tufe_genel":      "TP.TUKFIY2025.GENEL",
    "gida_alkolsuz":   "TP.TUKFIY2025.01",
    "kira_0411":       "TP.TUKFIY2025.04110",   # kiracılar tarafından ödenen gerçek kira
    "enerji_045":      "TP.TUKFIY2025.045",     # elektrik, gaz ve diğer yakıtlar
    "lokanta_11":      "TP.TUKFIY2025.11",
    "yemek_111":       "TP.TUKFIY2025.111",     # yiyecek ve içecek sunum hizmetleri
    "yemek_1111":      "TP.TUKFIY2025.1111",
    "tam_sunum_11111": "TP.TUKFIY2025.11111",   # lokanta vb. tam sunum
    "sinirli_11112":   "TP.TUKFIY2025.11112",   # sınırlı sunum (fast-food tipi)
    "konaklama_1120":  "TP.TUKFIY2025.1120",
    # Gıda 5'li gruplar (2022/04 sonrası madde uzatması için)
    "g_tahillar_01111":   "TP.TUKFIY2025.01111",
    "g_unlar_01112":      "TP.TUKFIY2025.01112",
    "g_ekmek_01113":      "TP.TUKFIY2025.01113",
    "g_et_01122":         "TP.TUKFIY2025.01122",
    "g_etkuru_01123":     "TP.TUKFIY2025.01123",
    "g_sut_01141":        "TP.TUKFIY2025.01141",
    "g_peynir_01145":     "TP.TUKFIY2025.01145",
    "g_yogurt_01146":     "TP.TUKFIY2025.01146",
    "g_yumurta_01148":    "TP.TUKFIY2025.01148",
    "g_bitkiselyag_01151":"TP.TUKFIY2025.01151",
    "g_tereyagi_01152":   "TP.TUKFIY2025.01152",
    "g_yaprakli_01171":   "TP.TUKFIY2025.01171",
    "g_meyvesebze_01172": "TP.TUKFIY2025.01172",
    "g_digersebze_01174": "TP.TUKFIY2025.01174",
    "g_yumrulu_01175":    "TP.TUKFIY2025.01175",
    "g_baklagil_01176":   "TP.TUKFIY2025.01176",
    "g_salca_01179":      "TP.TUKFIY2025.01179",
    "g_tuzsos_01193":     "TP.TUKFIY2025.01193",
    "g_baharat_01194":    "TP.TUKFIY2025.01194",
    "g_meyve_01162":      "TP.TUKFIY2025.01162",   # turunçgiller (limon)
    # --- Eski baz: TÜFE (2003=100), arşiv ---
    "eski_genel":   "TP.FG.J0",
    "eski_gida":    "TP.FG.J01",
    "eski_kira41":  "TP.FG.J041",
    "eski_enerji45":"TP.FG.J045",
    "eski_lokanta": "TP.FG.J11",
    "eski_yemek111":"TP.FG.J111",
    "eski_konaklama":"TP.FG.J112",
    # --- Yİ-ÜFE ---
    "yi_ufe": "TP.TUFE1YI.T1",
    # --- TCMB Yeni Kiracı Kira Endeksi (2018+) ---
    "ykke": "TP.YKKE.TR",
}

def tum_evds(yenile=False):
    """Tüm EVDS serilerini indirir; DataFrame (aylık) döner."""
    seriler = {}
    for ad, kod in EVDS_SERILER.items():
        try:
            seriler[ad] = evds_cek(kod, yenile=yenile)
        except Exception as e:
            log(f"HATA {ad} ({kod}): {e}")
    df = pd.DataFrame(seriler)
    df.index.name = "tarih"
    return df


# ----------------------------------------------------------------------------- MEDAS madde fiyatları
MADDE_ADLARI = {
    "1110101": "Çorbalar", "1110102": "Hazır Yemekler", "1110103": "Kebaplar",
    "1110104": "Pideler", "1110105": "Çiğ köfte (Köfteler)", "1110106": "Ekmekarası (Döner)",
    "1110108": "Burgerler", "1110110": "Pizza",
    "0111101": "Pirinç", "0111209": "Bulgur", "0111201": "Buğday Unu", "0111301": "Ekmek",
    "0112201": "Dana Eti", "0112501": "Tavuk Eti", "0112701": "Sucuk", "0112703": "Salam",
    "0114101": "Süt", "0114301": "Yoğurt", "0114401": "Beyaz Peynir", "0114402": "Kaşar Peyniri",
    "0114501": "Yumurta", "0115101": "Tereyağı", "0115302": "Ayçiçek Yağı", "0115301": "Zeytinyağı",
    "0117122": "Domates", "0117117": "Sivri Biber", "0117146": "Kuru Soğan", "0117130": "Havuç",
    "0117152": "Marul", "0117201": "Patates", "0117153": "Maydanoz", "0116130": "Limon",
    "0117401": "Kuru Fasulye", "0117403": "Mercimek", "0117505": "Salça", "0117504": "Turşu",
    "0119001": "Baharat", "0119002": "Tuz", "0119008": "Ketçap", "0119009": "Mayonez",
}

AY_KOLONLARI = ["01-Ocak","02-Şubat","03-Mart","04-Nisan","05-Mayıs","06-Haziran",
                "07-Temmuz","08-Ağustos","09-Eylül","10-Ekim","11-Kasım","12-Aralık"]

def medas_madde_fiyatlari():
    """MEDAS pivot xls dosyasını düzenli panele çevirir: DataFrame[tarih x madde_kodu] (TL)."""
    cpath = CACHE / "medas_madde_fiyatlari_panel.csv"
    xls = RAW / "medas_madde_fiyatlari.xls"
    # Panel önbelleği yalnız ham xls'ten YENİYSE geçerli (yeni hasat → panel yeniden kurulur)
    if cpath.exists() and (not xls.exists() or cpath.stat().st_mtime >= xls.stat().st_mtime):
        df = pd.read_csv(cpath, index_col=0, parse_dates=True)
        return df
    ham = pd.read_excel(xls, header=None)
    # Başlık satırlarını bul: ay adları 2. satırda (index 1?) — dinamik ara
    ay_satiri = None
    for i in range(6):
        vals = ham.iloc[i].astype(str).tolist()
        if any("Ocak" in v for v in vals):
            ay_satiri = i; break
    aylar = ham.iloc[ay_satiri].tolist()
    ay_idx = {j: int(str(a).split("-")[0]) for j, a in enumerate(aylar)
              if isinstance(a, str) and "-" in a and str(a).split("-")[0].isdigit()}
    kayitlar = []
    madde = None
    import re
    for _, row in ham.iloc[ay_satiri+1:].iterrows():
        h1 = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
        m = re.match(r"^(\d{7})\.\s*\((.+)\)\s*$", h1.strip())
        if m:
            madde = m.group(1)
        yil = row.iloc[2]
        if madde and pd.notna(yil) and str(yil).replace(".0","").isdigit():
            yil = int(float(yil))
            for j, ay in ay_idx.items():
                v = row.iloc[j]
                if pd.notna(v) and str(v).strip() not in ("", "-"):
                    try:
                        fiyat = float(str(v).replace(",", "."))
                    except ValueError:
                        continue
                    if fiyat > 0:
                        kayitlar.append((datetime.date(yil, ay, 1), madde, fiyat))
    uzun = pd.DataFrame(kayitlar, columns=["tarih", "kod", "fiyat"])
    uzun["tarih"] = pd.to_datetime(uzun["tarih"])
    df = uzun.pivot_table(index="tarih", columns="kod", values="fiyat")
    df.to_csv(cpath)
    log(f"MEDAS panel: {df.shape[0]} ay x {df.shape[1]} madde "
        f"({df.index.min():%Y-%m} → {df.index.max():%Y-%m}) — kaynak: TÜİK MEDAS, Tüketici Madde Fiyatları (2003=100)")
    return df


# ----------------------------------------------------------------------------- MEDAS Tarım ÜFE (tür bazlı)
def medas_tarim_ufe():
    """Tarım ÜFE (2020=100) tür bazlı endeks paneli: DataFrame[tarih x kod].
    Kodlar: '01.42' besi sığırı, '01.47' kümes hayvanları+yumurta, '01.45' koyun-keçi, ..."""
    cpath = CACHE / "medas_tarim_ufe_panel.csv"
    xls = RAW / "medas_tarim_ufe.xls"
    if cpath.exists() and (not xls.exists() or cpath.stat().st_mtime >= xls.stat().st_mtime):
        return pd.read_csv(cpath, index_col=0, parse_dates=True)
    import re
    ham = pd.read_excel(xls, header=None)
    ay_satiri = None
    for i in range(6):
        if any("Ocak" in str(v) for v in ham.iloc[i].tolist()):
            ay_satiri = i; break
    aylar = ham.iloc[ay_satiri].tolist()
    ay_idx = {j: int(str(a).split("-")[0]) for j, a in enumerate(aylar)
              if isinstance(a, str) and "-" in a and str(a).split("-")[0].isdigit()}
    kayitlar, kod = [], None
    for _, row in ham.iloc[ay_satiri+1:].iterrows():
        h1 = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
        m = re.match(r"^([\d.]+)\.\s*\((.+)\)\s*$", h1.strip())
        if m:
            kod = m.group(1).rstrip(".")
        yil = row.iloc[2]
        if kod and pd.notna(yil) and str(yil).replace(".0", "").isdigit():
            yil = int(float(yil))
            for j, ay in ay_idx.items():
                v = row.iloc[j]
                if pd.notna(v) and str(v).strip() not in ("", "-"):
                    try:
                        val = float(str(v).replace(",", "."))
                    except ValueError:
                        continue
                    if val > 0:
                        kayitlar.append((datetime.date(yil, ay, 1), kod, val))
    uzun = pd.DataFrame(kayitlar, columns=["tarih", "kod", "endeks"])
    uzun["tarih"] = pd.to_datetime(uzun["tarih"])
    df = uzun.pivot_table(index="tarih", columns="kod", values="endeks")
    df.to_csv(cpath)
    log(f"Tarım ÜFE panel: {df.shape[0]} ay x {df.shape[1]} kod ({df.index.min():%Y-%m} → {df.index.max():%Y-%m}) — kaynak: TÜİK MEDAS Tarım ÜFE (2020=100)")
    return df


# ----------------------------------------------------------------------------- Ağırlıklar
def temel_baslik_agirliklari():
    """TÜFE temel başlık (4'lü COICOP) ağırlıkları, yıl x kod (2003=100 sepeti)."""
    cpath = CACHE / "tuik_temel_baslik_agirliklar.csv"
    if cpath.exists():
        return pd.read_csv(cpath, index_col=0)
    f = RAW / "tuik_2003_temel_baslik_agirliklar.xlsx"
    ham = pd.read_excel(f, header=None)
    # Yapıyı keşfet: ilk sütun kod, ikinci ad, sonraki sütunlar yıllar
    log(f"temel başlık ham boyut: {ham.shape}")
    return ham  # keşif amaçlı; parse endeks.py'de tamamlanacak


# ----------------------------------------------------------------------------- Asgari ücret
# Kaynak: Asgari Ücret Tespit Komisyonu kararları (Resmî Gazete). Brüt, aylık, TL.
# 2024'te ara zam YOKTUR (tüm yıl 20.002,50 TL) — PwC/EY bordro parametreleri ile teyit.
ASGARI_UCRET_BRUT = [
    ("2013-01", 978.60), ("2013-07", 1021.50),
    ("2014-01", 1071.00), ("2014-07", 1134.00),
    ("2015-01", 1201.50), ("2015-07", 1273.50),
    ("2016-01", 1647.00),
    ("2017-01", 1777.50),
    ("2018-01", 2029.50),
    ("2019-01", 2558.40),
    ("2020-01", 2943.00),
    ("2021-01", 3577.50),
    ("2022-01", 5004.00), ("2022-07", 6471.00),
    ("2023-01", 10008.00), ("2023-07", 13414.50),
    ("2024-01", 20002.50),
    ("2025-01", 26005.50),
    ("2026-01", 33030.00),
]

# ----------------------------------------------------------------------------- Analiz dönemi (TEK KAYNAK)
# "Güncel ay" ve "iki yıl önce" HİÇBİR modülde sabit yazılmaz; buradan okunur.
# Eskiden '2026-07-01' ~40 yerde gömülüydü: Ağustos TÜFE geldiğinde hat koşar,
# grafikleri yeniden üretir ama Temmuz'da kalır ve sayfa bayat veriyi taze gibi
# gösterirdi (TCMB hattında yaşanan "sessiz bayatlama"nın aynısı).
AYLAR_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
            7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
AYLAR_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
              7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}
# TÜFE ile birlikte yayımlanmayan (gecikmeli) seriler: son ay tespitinde sayılmaz.
_GECIKMELI = {"ykke"}
_SON_AY_ONBELLEK = {}


def son_ay(evds=None):
    """Analizin 'güncel' ayı: TÜFE tabanlı serilerin TAMAMININ bulunduğu son ay
    ('YYYY-MM-01'). Arşiv (2003=100) ve YKKE gibi bilinçli gecikmeli seriler
    sayılmaz. Bir kez hesaplanıp önbelleğe alınır (aynı koşuda tüm modüller aynı
    dönemi görsün)."""
    if "son" in _SON_AY_ONBELLEK:
        return _SON_AY_ONBELLEK["son"]
    df = evds if evds is not None else tum_evds()
    kolonlar = [c for c in df.columns if c not in _GECIKMELI and not c.startswith("eski_")]
    tam = df[kolonlar].dropna(how="any")
    if tam.empty:
        raise RuntimeError("son_ay: TÜFE serileri boş — EVDS çekimi başarısız olmuş olabilir")
    _SON_AY_ONBELLEK["son"] = tam.index[-1].strftime("%Y-%m-01")
    return _SON_AY_ONBELLEK["son"]


def once_ay(son=None, ay=24):
    """Kıyas ayı: güncel aydan `ay` ay önce (varsayılan iki yıl) — 'YYYY-MM-01'."""
    son = son or son_ay()
    return (pd.Timestamp(son) - pd.DateOffset(months=ay)).strftime("%Y-%m-01")


def ad_uzun(t):
    """'2026-07-01' → 'Temmuz 2026'"""
    t = pd.Timestamp(t); return f"{AYLAR_TR[t.month]} {t.year}"


def ad_kisa(t):
    """'2026-07-01' → 'Tem-2026'"""
    t = pd.Timestamp(t); return f"{AYLAR_KISA[t.month]}-{t.year}"


def ad_kisa2(t):
    """'2026-07-01' → 'Tem-26'"""
    t = pd.Timestamp(t); return f"{AYLAR_KISA[t.month]}-{str(t.year)[2:]}"


def asgari_ucret_serisi(bitis=None):
    """Brüt asgari ücreti aylık seriye açar (basamak fonksiyonu). bitis: 'YYYY-MM';
    verilmezse analizin güncel ayı. Tablodaki son yıldan sonraki aylar için son
    tutar taşınır ve UYARI basılır — yeni yıl zammı ASGARI_UCRET_BRUT'a eklenmeli."""
    bitis = bitis or son_ay()[:7]
    son_yil = max(int(d[:4]) for d, _ in ASGARI_UCRET_BRUT)
    if int(bitis[:4]) > son_yil:
        log(f"UYARI: asgari ücret tablosu {son_yil} ile bitiyor; {bitis} için son tutar taşınıyor")
    idx = pd.date_range("2013-01-01", pd.Timestamp(bitis + "-01"), freq="MS")
    s = pd.Series(index=idx, dtype=float, name="asgari_ucret_brut")
    for donem, tutar in ASGARI_UCRET_BRUT:
        s.loc[s.index >= pd.Timestamp(donem + "-01")] = tutar
    return s


if __name__ == "__main__":
    df = tum_evds()
    print(df.tail(3).iloc[:, :6])
    mp = medas_madde_fiyatlari()
    print(mp.tail(3).iloc[:, :6])
    print(asgari_ucret_serisi().tail(3))
