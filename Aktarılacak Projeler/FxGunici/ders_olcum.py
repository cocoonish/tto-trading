#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ders ölçümü: koşu çıktılarından dersin ve figürlerin TEK ölçüm dosyası.

Girdi (hepsi depodaki koşu çıktısı ya da arşiv):
  cikti/sonuc/<birim>/<parite>.json     birim × parite koşusu (kosu.py)
  cikti/islem/<birim>/<parite>__*.parquet  varsayılan ve seçilen kombinasyonun işlemleri
  cikti/sonuc/haber/<parite>.json, devam.json   haber analizleri (haber_analiz.py)
  veri/dukascopy/kalite.json, kunye/    veri denetimi ve indirme künyesi
  veri/takvim/olaylar.csv, kunye.json, sinama.json   haber takvimi
  onkayit.toml, ayar.toml               önceden kayıt ve proje ayarı
Çıktı:
  cikti/ders/olcum.json                 figürler (sekil.py), ders metinleri (ders_yaz.py) ve doğrulayıcı
                                        (dogrula.py) yalnız buradan okur

Burada yeni bir ÖLÇÜM yapılmaz, yalnız toplanır; beş istisna adıyla: (1) dört paritenin
HAVUZU — aynı stratejiyi dört paritede birlikte koşmanın işlem başına ortalaması ve günlük
R toplamından Sharpe'ı, kaydedilmiş işlem dosyalarından; (2) stratejiler arası günlük R
korelasyonu; (3) birimlere bölünen ailelerin AİLE sayımı — ön kaydın deneme sayısı aile
başınadır, koşu birim başına seçer (aile_secimi); (4) birden çok yerel saati olan olayların
SAAT REJİMİ — devam satırları ve haber stratejilerinin işlemleri olayın yerel saatine göre
ayrılır (saat_rejimi; ECB basın toplantısının 14:30 saati çoğu hafta ABD'nin 08:30 veri
dakikasına düşer); (5) YEREL TATİLLER — varsayılanların İngiltere ve ABD tatillerindeki işlemleri,
kaydedilmiş işlem dosyalarından (tatil_betimi; ön kayıt dışı, betimleyici). Beşinin tanımı
aşağıda, fonksiyonun kendisinde. Seçilenin komşuları (komsular) ve ay sonu ailesi (ay_sonu_ailesi)
ölçüm değil, koşu çıktısının okunuşudur: ızgaranın satırları ve ay sonu ayrımları olduğu gibi.

Künyenin `kod` alanı ölçümü üreten kodun özüdür (kod_kunyesi): kapı onu yalnız hashlib ile sınar.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import tomllib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import ayar as ay
import metrik as mk
import onkayit_gecmis as og
import saglamlik as sg
import takvim
import zaman as z

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
ONKAYIT_YOL = BURASI / "onkayit.toml"


def _oku(yol: Path):
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else None


def _oz(yol: Path) -> str | None:
    return hashlib.sha256(yol.read_bytes()).hexdigest() if yol.exists() else None


def _icerik_ozu(d: dict) -> str:
    """Ön kaydın AYRIŞTIRILMIŞ içeriğinin özü: yorum ve biçim değişikliği özü değiştirmez."""
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _git(*arg: str) -> str:
    import subprocess
    return subprocess.run(["git", "-C", str(KOK), *arg], capture_output=True, text=True, check=True).stdout


def gecmis_sorunu() -> str | None:
    """Ön kaydın git geçmişi baştan sona okunabiliyor mu; sorun varsa adıyla, yoksa None.

    Sığ klon tek başına engel değildir (bu deponun bulut klonları sığdır): dosyanın görünen İLK commit'i dosyayı
    EKLEYEN commit olmalı ve sığ klonun sınırında olmamalıdır. Sınırdaki commit'in ebeveyni görünmez; dosyanın daha eski
    bir geçmişi varsa kesik kök "ilk kayıt" sanılırdı."""
    import subprocess
    rel = ONKAYIT_YOL.relative_to(KOK).as_posix()
    try:
        gecmis = _git("log", "--format=%H", "--", rel).split()
        sinir_yol = Path(_git("rev-parse", "--git-path", "shallow").strip())
    except (OSError, subprocess.CalledProcessError):
        return "git yok ya da burası bir git deposu değil: ön kaydın geçmişi ölçülemez"
    if not gecmis:
        return "ön kayıt git geçmişinde yok"
    ilk = gecmis[-1]
    sinir_yol = sinir_yol if sinir_yol.is_absolute() else KOK / sinir_yol
    sinir = set(sinir_yol.read_text().split()) if sinir_yol.exists() else set()
    if ilk in sinir:
        return "sığ klon ön kaydın ilk görünen commit'inde kesiliyor (git fetch --deepen ya da --unshallow)"
    try:
        ebeveyn = _git("rev-list", "--parents", "-n", "1", ilk).split()[1:]
    except subprocess.CalledProcessError:
        return "ön kaydın ilk commit'inin ebeveyni okunamadı"
    for p in ebeveyn:
        if subprocess.run(["git", "-C", str(KOK), "cat-file", "-e", f"{p}:{rel}"],
                          capture_output=True).returncode == 0:
            return "ön kaydın ilk görünen commit'i dosyayı eklemiyor: geçmişin başı kesik"
    return None


def onkayit_gecmisi() -> list[dict] | None:
    """Ön kaydın git geçmişi: her commit'te ayrıştırılmış içeriğin özü ve bir öncekine göre değişen
    bölümler. "Hiçbir kural sonuç görüldükten sonra değişmedi" cümlesi bir beyan değil bu listedir.
    Geçmiş baştan sona okunamıyorsa (gecmis_sorunu) None: ölçülemeyen geçmiş uydurulmaz (şablonun iddiası o zaman
    üretimi düşürür; zincir bu hâli ilk adımında adıyla söyler — hepsi.git_on_kosulu). Zaman İŞLEYEN (committer)
    saatidir: geçmiş yeniden yazılırsa (rebase, amend) saat değişir ve beklenen geçmişle kıyas (ONKAYIT_BEKLENEN)
    bunu yakalar."""
    import subprocess
    rel = ONKAYIT_YOL.relative_to(KOK).as_posix()
    if gecmis_sorunu():
        return None
    try:
        out = _git("log", "--format=%H %cI", "--", rel).split("\n")
    except (OSError, subprocess.CalledProcessError):
        return None
    kayit, onceki = [], None
    for satir in reversed([s for s in out if s.strip()]):
        h, t = satir.split(" ", 1)
        try:
            metin = subprocess.run(["git", "-C", str(KOK), "show", f"{h}:{rel}"],
                                   capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError:
            return None
        d = tomllib.loads(metin)
        degisen = sorted(set(d)) if onceki is None else sorted(k for k in set(d) | set(onceki) if d.get(k) != onceki.get(k))
        # Sonuçlardan önce mi: kayıt, ilk sonuçların görüldüğü commit'in atası (ya da kendisi) mı.
        once = subprocess.run(["git", "-C", str(KOK), "merge-base", "--is-ancestor", h, og.ILK_SONUC[0]],
                              capture_output=True).returncode == 0
        kayit.append({"commit": h[:8], "zaman": t, "icerik_ozu": _icerik_ozu(d), "degisen_bolum": degisen,
                      "sonuctan_once": once, "aciklama": og.ACIKLAMA.get(h[:8])})
        onceki = d
    simdi = tomllib.loads(ONKAYIT_YOL.read_text(encoding="utf-8"))
    if onceki is not None and simdi != onceki:
        kayit.append({"commit": None, "zaman": None, "icerik_ozu": _icerik_ozu(simdi),
                      "degisen_bolum": sorted(k for k in set(simdi) | set(onceki) if simdi.get(k) != onceki.get(k))})
    return kayit


def gecmis_ozet(gecmis: list[dict] | None) -> dict | None:
    """Ön kaydın geçmişinin sayımı (dersin iddiaları): kaç kayıt, kaçı ilk sonuçlardan önce, sonrakilerin kaçı içerik
    değiştiriyor (sıfır olmalı: sonuçtan sonra yalnız açıklama notu yazılabilir)."""
    if not gecmis:
        return None
    sonra = [g for g in gecmis if g.get("sonuctan_once") is False]
    return {"kayit": len(gecmis), "once": sum(1 for g in gecmis if g.get("sonuctan_once") is True),
            "sonra": len(sonra), "sonra_icerik": sum(1 for g in sonra if g.get("degisen_bolum"))}


def _temiz(x):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 6)
    if isinstance(x, (np.floating,)):
        return _temiz(float(x))
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, dict):
        return {str(k): _temiz(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_temiz(v) for v in x]
    return x


# ───────────────────────────────────────────── eğri: günlük birikimli R → haftalık
def haftalik(egri: dict | None) -> dict | None:
    """Günlük birikimli R eğrisinin haftanın son işlem gününe düşen değerleri (figür için).
    Azami düşüş günlük seriden hesaplanır ve ayrıca yazılır: haftalık örnekleme onu küçültürdü."""
    if not egri or not egri.get("gun"):
        return None
    s = pd.Series(egri["r"], index=pd.DatetimeIndex(egri["gun"]))
    h = s.groupby(s.index.to_period("W-FRI")).last()
    gun = s.groupby(s.index.to_period("W-FRI")).apply(lambda x: x.index[-1])
    tepe = np.maximum.accumulate(np.concatenate([[0.0], s.to_numpy()]))[1:]
    dd = tepe - s.to_numpy()
    ddh = pd.Series(dd, index=s.index).groupby(s.index.to_period("W-FRI")).max()
    return {"gun": [g.strftime("%Y-%m-%d") for g in gun], "r": [round(float(v), 3) for v in h],
            "dusus": [round(float(v), 3) for v in ddh], "azami_dusus": round(float(dd.max()), 3)}


def gunluk_seri(egri: dict | None) -> pd.Series:
    """Birikimli eğriden günlük R."""
    if not egri or not egri.get("gun"):
        return pd.Series(dtype=float)
    s = pd.Series(egri["r"], index=pd.DatetimeIndex(egri["gun"]))
    return s.diff().fillna(s.iloc[0])


# ───────────────────────────────────────────── ızgara: ısı haritası ve zaman dilimi kıyası
def _eksen_sirala(degerler) -> list[str]:
    """Izgara ekseninin sırası: değerlerin hepsi sayıysa sayı sırası ("6" "12"den önce; dizge sırası "12"yi öne
    alıyordu), değilse dizge sırası."""
    d = list(degerler)
    try:
        return sorted(d, key=float)
    except ValueError:
        return sorted(d)


#: Izgarada aynı kombinasyonun ikinci adı (ön kayıt: "tf=60'ta ikisi aynıdır, tek sayılır"): NY IB'de ilk denge
#: penceresi mum uzunluğuna eşitse (60 dk mumda 60 dakika) o hücre "tek mum" satırının kendisidir. Isı haritası o
#: hücreyi boş bırakmaz, eşlemesini yazar; boş hücre "işlem yok" demektir.
ESDEGER_HUCRE = {("nyib", "tf", "ib_pencere"): lambda x, y: "tf" if y == x else None}


def isi(s: dict, eksen: tuple[str, str], merkez: dict | None = None) -> dict:
    """İki eksenli ızgara kesiti: öbür parametreler `merkez`de — verilmezse önceden kayıtlı varsayılanda; seçilenin
    çevresi için ızgaradan seçilen kombinasyonda (öbür parametreleri seçilen değerlerinde tutan kesit; seçilen hücre
    ve komşuları ancak bu kesitte görünür). `varsayilan` varsayılanın iki ekseni, `merkez` kesitin merkezidir;
    `varsayilan_kesitte`: varsayılan bu kesitin bir hücresi mi."""
    v = merkez or s["varsayilan"]
    x_ad, y_ad = eksen
    hucre = {}
    for r in s["izgara"]:
        p = r["p"]
        if any(p.get(k) != v.get(k) for k in v if k not in (x_ad, y_ad)):
            continue
        hucre[(str(p[x_ad]), str(p[y_ad]))] = {"is": r["is"], "oos": r["oos"]}
    xs = _eksen_sirala({k[0] for k in hucre})
    ys = _eksen_sirala({k[1] for k in hucre})
    es = ESDEGER_HUCRE.get((s.get("aile"), x_ad, y_ad))
    if es:
        for x in xs:
            for y in ys:
                e = es(x, y)
                if (x, y) not in hucre and e is not None and (x, e) in hucre:
                    hucre[(x, y)] = {"esleme": e}
    sv = s["varsayilan"]
    return {"x_ad": x_ad, "y_ad": y_ad, "x": xs, "y": ys,
            "hucre": [[hucre.get((x, y)) for x in xs] for y in ys],
            "varsayilan": [str(sv.get(x_ad)), str(sv.get(y_ad))], "merkez": [str(v.get(x_ad)), str(v.get(y_ad))],
            "merkez_p": dict(v),
            "varsayilan_kesitte": all(sv.get(k) == v.get(k) for k in set(sv) | set(v) if k not in (x_ad, y_ad))}


def komsular(s: dict) -> dict | None:
    """Seçilen kombinasyonun tek parametre komşuları: her serbest parametre için YALNIZ o parametresi değişen ızgara
    kombinasyonları (öbürleri seçilen değerlerinde), örneklem içi ve dışı. Isı haritası iki boyutluk bir kesittir ve
    seçilen çoğu zaman o kesitte değildir; bu liste seçimin bir düzlükte mi, tek bir tepede mi durduğunu bütün
    boyutlarda okutur. Seçilenin kendi satırı her parametrenin listesinde `secilen` diye durur. Tanımsız bileşim
    (ızgarada olmayan) listede yoktur ve sayısı `tanimsiz` alanında yazar. Seçim yoksa None."""
    p = s.get("secilen")
    if not p:
        return None
    degerler: dict[str, list] = {}
    for r in s["izgara"]:
        for k, v in r["p"].items():
            degerler.setdefault(k, [])
            if v not in degerler[k]:
                degerler[k].append(v)
    out = {"p": dict(p), "parametre": {}}
    for k, vs in degerler.items():
        if len(vs) < 2:
            continue
        satir = []
        for r in s["izgara"]:
            q = r["p"]
            if any(q.get(j) != p.get(j) for j in set(p) | set(q) if j != k):
                continue
            satir.append({"deger": q.get(k), "secilen": q.get(k) == p.get(k), "is": r["is"], "oos": r["oos"],
                          "kopya": r.get("kopya"), "bos": r.get("bos")})
        satir.sort(key=lambda x: vs.index(x["deger"]))
        out["parametre"][k] = {"satir": satir, "tanimsiz": len(vs) - len(satir)}
    return out


def _tf_bos_neden(aile: str, varsayilan: dict, tf: str) -> str | None:
    """Bir zaman diliminde hiçbir paritede işlem açılmamışsa sebebi, kuralın kendi penceresinden ölçülerek. Sebep
    kuraldan okunamıyorsa None: uydurulmaz, ders yalnız "işlem yok" der."""
    from datetime import datetime
    if aile == "vwap_cekilme" and varsayilan.get("capa") == "londra":
        n = int(varsayilan["n"])
        mumlar = []
        for gun in ("2026-01-15", "2026-03-18", "2026-07-15", "2026-10-28"):      # kış · ara (mart) · yaz · ara (ekim)
            y, a, g = map(int, gun.split("-"))
            bas = datetime(y, a, g, 8, 0, tzinfo=z.LONDRA).timestamp() + 3600         # çapa + ilk saat
            son = datetime(y, a, g, 16, 0, tzinfo=z.NEWYORK).timestamp()
            mumlar.append(int((son - bas) // (60 * int(tf))))
        if max(mumlar) < n + 1:
            return (f"sinyal penceresine (Londra 09:00 → New York 16:00) en çok {max(mumlar)} tane {tf} dakikalık mum "
                    f"sığar; kural {n} mumluk trendden sonra bir sinyal mumu ister, yani en az {n + 1} mum")
    return None


def tf_bos(out: dict) -> dict:
    """Zaman dilimi kıyasında hiçbir paritede, iki dönemde de işlem açmayan dilimler ve sebepleri."""
    ciftler = [c for c in out["cift"] if out["cift"][c].get("tf")]
    dilimler = sorted({t for c in ciftler for t in out["cift"][c]["tf"]}, key=int)
    bos = {}
    for t in dilimler:
        if all((((out["cift"][c]["tf"].get(t) or {}).get(d) or {}).get("n") or 0) == 0 for c in ciftler
               for d in ("is", "oos")):
            bos[t] = {"neden": _tf_bos_neden(out["aile"], out["varsayilan"], t)}
    return bos


def ornek_olaylari(ornekler: list[dict], cift: str) -> list[dict]:
    """Örnek günlerin penceresine düşen takvim olayları (paritenin kendi takvimi): figür olayın çizgisini ve adını
    çizer. Haber kuralının kendi olayı da listededir; pencere girişten 8 saat önce ile çıkıştan 1 saat sonra."""
    if not ornekler:
        return ornekler
    df = takvim.olaylar_oku(cift)
    t = df["utc_sn"].to_numpy(np.int64) if len(df) else np.array([], dtype=np.int64)
    out = []
    for x in ornekler:
        i = x.get("islem") or {}
        a, b_ = int(i.get("giris_t", 0)) - 8 * 3600, int(i.get("cikis_t", 0)) + 3600
        m = (t >= a) & (t <= b_)
        out.append({**x, "takvim": [{"olay": str(o), "t": int(u)} for o, u in zip(df["olay"][m], t[m])]})
    return out


def tf_kiyas(s: dict) -> dict:
    """Zaman dilimi kıyası: varsayılan kombinasyonun yalnız `tf`'i değişir.

    New York ilk dengesinde varsayılanın ilk denge penceresi 60 dakikadır; 60 dakikalık mumda o pencere mumun
    kendisidir (ön kayıt: "tf=60'ta ikisi aynıdır, tek sayılır") ve ızgarada `ib_pencere = "tf"` adıyla durur. Kıyas
    60 dakikayı o satırla eşler ve eşlemeyi kayda yazar."""
    v = s["varsayilan"]
    out = {}
    for r in s["izgara"]:
        p = r["p"]
        if all(p.get(k) == v.get(k) for k in v if k != "tf"):
            out[str(p["tf"])] = {"is": r["is"], "oos": r["oos"], "haber_payi": r.get("haber_payi")}
    if s.get("aile") == "nyib" and "60" not in out:
        for r in s["izgara"]:
            p = r["p"]
            if p.get("tf") == 60 and p.get("ib_pencere") == "tf" and \
                    all(p.get(k) == v.get(k) for k in v if k not in ("tf", "ib_pencere")):
                out["60"] = {"is": r["is"], "oos": r["oos"], "haber_payi": r.get("haber_payi"),
                             "esleme": "ib_pencere=tf"}
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def izgara_ozet(s: dict) -> dict:
    """Izgaranın tamamının özeti (bir parite): kaç kombinasyon örneklem içinde, dışında ve ikisinde birden net artı;
    örneklem dışının en iyi ve en kötü kombinasyonu. Isı haritası iki boyutluk bir kesittir; bu sayım bütün ızgarayı
    okur."""
    satir = [r for r in s["izgara"] if (r["is"].get("n") or 0) > 0]
    def arti(r, d):
        x = r[d].get("beklenti_r")
        return x is not None and np.isfinite(x) and x > 0
    dis = [r for r in satir if (r["oos"].get("n") or 0) > 0 and np.isfinite(r["oos"].get("beklenti_r", np.nan))]
    en_iyi = max(dis, key=lambda r: r["oos"]["beklenti_r"]) if dis else None
    en_kotu = min(dis, key=lambda r: r["oos"]["beklenti_r"]) if dis else None
    return {"n": len(s["izgara"]), "islem_acan": len(satir), "is_arti": sum(arti(r, "is") for r in satir),
            # Seçim örneklem içinde asgari işlem ister (ön kayıt [secim]); hiçbir kombinasyon onu sağlamıyorsa ders
            # "seçilemedi" der ve ızgaranın en kalabalık kombinasyonunun işlem sayısını yazar.
            "is_azami_n": max((int(r["is"].get("n") or 0) for r in s["izgara"]), default=0),
            "oos_arti": sum(arti(r, "oos") for r in dis), "ikisi_arti": sum(arti(r, "is") and arti(r, "oos") for r in dis),
            "oos_en_iyi": {"p": en_iyi["p"], "r": en_iyi["oos"]["beklenti_r"], "n": en_iyi["oos"]["n"]} if en_iyi else None,
            "oos_en_kotu": {"p": en_kotu["p"], "r": en_kotu["oos"]["beklenti_r"], "n": en_kotu["oos"]["n"]} if en_kotu else None}


#: Derste tablo olarak verilen varyant kıyasları (şartname §5 N1 "1./2./3. mum", N2 "ilk mum kapanışı ↔ teyit";
#: NY IB'de ilk denge penceresi: §3'ün "aralık penceresi = teyit mumu" kuralı ile ön kaydın 60 dakikası).
VARYANT = {"n1": ["giris_mumu"], "n2": ["giris", "k"], "nyib_0800": ["ib_pencere"], "nyib_0930": ["ib_pencere"]}
#: Her kuralda ayrıca: stop türü, stop yeri ve hedef (şartname §3 iki stop türü ve 1R / 2R / zaman hedefi ister; ızgara
#: onları koşturur, ders her birinin etkisini öbür parametreler varsayılandayken tablo olarak verir). Izgarada tek
#: değeri olan boyut (ör. stopsuz kuralda stop yeri) varyant değildir.
VARYANT_ORTAK = ("stop_turu", "stop_yeri", "hedef")


def varyant_parametreleri(birim: str, izgara_deger: dict) -> list[str]:
    ozel = list(VARYANT.get(birim, []))
    return ozel + [p for p in VARYANT_ORTAK if p not in ozel and len(izgara_deger.get(p) or []) > 1]


def varyant(s: dict, param: str) -> dict:
    """Bir parametrenin değerleri, öbür parametreler önceden kayıtlı varsayılanda (ızgaranın kendi satırları)."""
    v = s["varsayilan"]
    out = {}
    for r in s["izgara"]:
        p = r["p"]
        if all(p.get(k) == v.get(k) for k in v if k != param):
            out[str(p[param])] = {"is": r["is"], "oos": r["oos"], "haber_payi": r.get("haber_payi")}
    return out


# ───────────────────────────────────────────── dört paritenin havuzu
def _islem_dosyasi(kok: Path, birim: str, cift: str, p: dict) -> Path:
    ad = "|".join(f"{k}={p[k]}" for k in sorted(p)).replace("|", "__").replace("=", "-").replace(":", "")
    return kok / "islem" / birim / f"{cift}__{ad}.parquet"


def havuz(kok: Path, birim: str, ciftler: list[str], p: dict, egriler: dict, a: ay.Ayar) -> dict | None:
    """Aynı kombinasyonu dört paritede birlikte koşmak: her işlem 1R risk.

    İşlem başına metrikler (beklenti, isabet, %95 aralık) dört paritenin işlemlerinin birleşiminden;
    Sharpe ve azami düşüş, dört paritenin GÜNLÜK R TOPLAMINDAN (aynı gün dört pozisyon taşınır).
    Örneklem dışı ve içi ayrı; günler pariteler arasında birleşim kümesidir."""
    parca = []
    for c in ciftler:
        yol = _islem_dosyasi(kok, birim, c, p)
        if yol.exists():
            x = pd.read_parquet(yol)
            x["cift"] = c
            parca.append(x)
    if not parca:
        return None
    isl = pd.concat(parca, ignore_index=True)
    gunler = sorted(set().union(*[set(e["gun"]) for e in egriler.values() if e]))
    gun = np.array(gunler, dtype="datetime64[D]")
    out = {}
    for ad, m in (("is", gun <= np.datetime64(a.ic_bitis)), ("oos", gun >= np.datetime64(a.dis_baslangic)),
                  ("tum", np.ones(len(gun), bool))):
        g = gun[m]
        gi = isl["gun"].to_numpy().astype("datetime64[D]")
        x = isl[(gi >= g.min()) & (gi <= g.max())] if len(g) else isl.iloc[:0]
        # %95 aralığı GÜN KÜMELİ: aynı günün dört paritedeki işlemleri doların ortak hareketiyle ilintilidir ve
        # birlikte yeniden örneklenir (işlemleri bağımsız sayan aralık fazla dar çıkar). İşlem başına aralık bilgi
        # olarak yanında durur.
        oz = mk.ozet(x, g, kume_sutun="gun")
        al = mk.alinan(x)
        oz["ga_islem_alt"], oz["ga_islem_ust"] = mk.bootstrap_ort(al["r"].to_numpy()) if len(al) else (None, None)
        # Sıfıra yakın uç (bilgi): havuz cümlesi aralığın sıfıra göre yerini okur (üstünde · kapsıyor · altında).
        if len(al) and ad in ("oos", "tum"):
            sinir = {}
            for uc, hangi in (("ga_alt", "alt"), ("ga_ust", "ust")):
                s_ = mk.sinir_bilgisi(al["r"].to_numpy(np.float64), oz.get(uc), hangi, kume=al["gun"].to_numpy())
                if s_:
                    sinir[uc] = s_
            if sinir:
                oz["sinir"] = sinir
        # günlük R toplamı: dört paritenin günlük R'si toplanır (mk.gunluk_r gün başına toplar)
        oz["pariteler"] = sorted(x["cift"].unique().tolist()) if len(x) else []
        out[ad] = oz
    return out


def _birlesik_islem(kok: Path, birim: str, ciftler: list[str], p: dict) -> pd.DataFrame:
    parca = []
    for c in ciftler:
        yol = _islem_dosyasi(kok, birim, c, p)
        if yol.exists():
            x = pd.read_parquet(yol)
            x["cift"] = c
            parca.append(mk.alinan(x))
    return pd.concat(parca, ignore_index=True) if parca else pd.DataFrame()


def haber_olay(isl: pd.DataFrame, a: ay.Ayar) -> dict:
    """Haber kuralının dört paritelik havuzu, olay ve ilk mum kovası başına. Gözlem birimi OLAYDIR (olay tipi ×
    tarih): işlem sayısı aynı ABD olayının dört paritedeki ölçümünü ayrı sayar, olay sayısı saymaz; %95 aralığı olay
    kümeli bootstrap'tir. N3 ve N4'te haber öncesi aralığın genişliği (pip) olay olay — basın toplantılarında o
    aralık kararın kendi tepkisidir."""
    if not len(isl):
        return {}
    gun = isl["gun"].to_numpy().astype("datetime64[D]")
    kume = isl["olay"].astype(str) + "|" + isl["tarih"].astype(str)
    out: dict = {}
    for boyut in ("olay", "kova"):
        out[boyut] = {}
        for deger, g in isl.groupby(boyut, sort=True):
            m_g = isl.index.isin(g.index)
            satir = {}
            for ad, m in (("tum", np.ones(len(isl), bool)), ("oos", gun >= np.datetime64(a.dis_baslangic))):
                mm = m_g & m
                r = isl["r"].to_numpy()[mm]
                if not len(r):
                    satir[ad] = {"n": 0}
                    continue
                alt, ust = mk.bootstrap_kume_ort(r, kume.to_numpy()[mm])
                satir[ad] = {"n": int(len(r)), "n_olay": int(kume[mm].nunique()), "r": float(r.mean()),
                             "ga_alt": alt, "ga_ust": ust, "isabet": float((isl["pnl_pip"].to_numpy()[mm] > 0).mean())}
            out[boyut][str(deger)] = satir
    if {"ust", "alt"} <= set(isl.columns) and isl["ust"].notna().any():
        pip_nokta = {c: a.nokta_pip(c) for c in isl["cift"].unique()}
        genislik = (isl["ust"] - isl["alt"]) / isl["cift"].map(pip_nokta)
        out["aralik_pip"] = {}
        for olay, g in genislik.groupby(isl["olay"]):
            out["aralik_pip"][str(olay)] = {"medyan": float(g.median()), "n": int(g.notna().sum()),
                                            "cift": {c: float(x.median()) for c, x in g.groupby(isl.loc[g.index, "cift"])}}
    return out


HABER_BIRIM = ("n1", "n2", "n3", "n4", "n5")


def _ham_islem(kok: Path, birim: str, ciftler: list[str], p: dict) -> pd.DataFrame:
    """Kaydedilmiş işlem dosyasının BÜTÜN satırları (alınan ve tek pozisyon kuralının engellediği adaylar)."""
    parca = []
    for c in ciftler:
        yol = _islem_dosyasi(kok, birim, c, p)
        if yol.exists():
            x = pd.read_parquet(yol)
            x["cift"] = c
            parca.append(x)
    return pd.concat(parca, ignore_index=True) if parca else pd.DataFrame()


def durum_sayimi(kok: Path, birim: str, ciftler: list[str], p: dict) -> dict:
    """Varsayılanın emirleri motorun sonuç koduna göre (motor.DURUM), bütün dönem ve bütün paritelerde birlikte: alınan,
    açık pozisyon yüzünden alınmayan, giriş anında stopun ötesinde açılan (risk geçersiz), yürütülen girişi seviye
    hedefini çoktan geçen (hedef geçersiz), giriş dakikası verisi olmayan ve gün sonundan sonraya düşen."""
    import motor as mt
    x = _ham_islem(kok, birim, ciftler, p)
    if not len(x):
        return {}
    out = {ad: 0 for ad in mt.DURUM.values()}
    for k, n in x["durum"].value_counts().items():
        out[mt.DURUM[int(k)]] = int(n)
    out["toplam"] = int(len(x))
    return out


def durum_parite(kok: Path, birim: str, c: str, p: dict) -> dict:
    """Bir kombinasyonun emirleri bir paritede, motorun sonuç koduna göre (bütün dönem); haber biriminde olay türü
    başına da. Olay türünün bütün emirleri gün sonundan sonraya düşüyorsa (alınan sıfır) kombinasyon o olayı
    YAPISAL olarak dışarıda bırakır (ör. 60 dakikalık mumda üçüncü mumdan sonra giren kural, 14:00'teki FOMC kararına
    16:55 gün sonundan önce giremez); ders bunu seçim tablosunda adıyla yazar."""
    import motor as mt
    yol = _islem_dosyasi(kok, birim, c, p)
    if not yol.exists():
        return {}
    x = pd.read_parquet(yol)

    def say(g: pd.DataFrame) -> dict:
        o = {ad: 0 for ad in mt.DURUM.values()}
        for k, n in g["durum"].value_counts().items():
            o[mt.DURUM[int(k)]] = int(n)
        o["toplam"] = int(len(g))
        return o
    out = say(x)
    if "olay" in x.columns:
        out["olay"] = {str(ol): say(g) for ol, g in x.groupby("olay")}
        out["yapisal_disli"] = sorted(ol for ol, d in out["olay"].items()
                                      if d["toplam"] and not d["alindi"] and d["gun_sonu"] == d["toplam"])
    return out


def stop_cikis(kok: Path) -> dict:
    """Stopla çıkan işlemlerin net R dağılımı, çıkış türüne göre (motor.NEDEN: sert stop, kapanış stopu, boşlukla
    stop): kaydedilmiş bütün işlem dosyaları — her kuralın her paritedeki varsayılanı ve seçileni, bütün dönem. Giriş
    dersi "kayıp 1R'yi aşabilir" cümlesini bu sayılarla kurar: kapanış stopu mum kapandıktan sonra sonraki açılışta
    çıktığı için kaybı 1R'nin belirgin ötesine taşıyabilir; ne kadar, buradan."""
    import motor as mt
    dosyalar = sorted((kok / "islem").glob("*/*.parquet"))
    parca = []
    for f in dosyalar:
        x = pd.read_parquet(f, columns=["durum", "neden", "r"])
        parca.append(x[x["durum"] == 0])
    if not parca:
        return {}
    d = pd.concat(parca, ignore_index=True)
    out = {"dosya": len(dosyalar)}
    for kod, ad in mt.NEDEN.items():
        if ad not in ("stop", "kapanis_stop", "bosluk_stop"):
            continue
        r = d.loc[d["neden"] == kod, "r"].to_numpy(float)
        r = r[np.isfinite(r)]
        out[ad] = ({"n": int(len(r)), "medyan": float(np.median(r)), "pay_2r": float((r <= -2).mean()),
                    "pay_15r": float((r <= -1.5).mean()), "en_kotu": float(r.min())} if len(r) else {"n": 0})
    return out


def tek_pozisyon(kok: Path, birim: str, ciftler: list[str], p: dict) -> dict:
    """Haber stratejisinin varsayılanında olay türü başına kaç olayın işleme dönüştüğü (K9: parite başına tek
    pozisyon, bütün olaylara birlikte). Takvimdeki olay sayısı, sinyal veren (aday) olay, en az bir paritede işlem
    açılan olay ve bütün adayları açık bir pozisyon yüzünden alınmayan olay — basın toplantısı satırları yalnız
    kararın pozisyonu kapanmış toplantıları taşır, bu sayım bunu adıyla yazar. Olay = olay türü × tarih; dört
    paritede ölçülen ABD olayı bir kez sayılır."""
    x = _ham_islem(kok, birim, ciftler, p)
    if not len(x) or "olay" not in x.columns:
        return {}
    tk = takvim.tumu()
    tk = tk[tk["ciftler"].str.split().apply(lambda s: bool(set(s) & set(ciftler)))]
    import motor as mt
    alinmis = x[x["durum"] == 0].copy()
    acilista = alinmis["neden"].isin([3, 4, 5, 6]) & (alinmis["cikis_i"] > alinmis["giris_i"])
    alinmis["serbest_i"] = np.where(acilista, alinmis["cikis_i"], alinmis["cikis_i"] + 1)
    out = {}
    for olay, g in x.groupby("olay"):
        aday = set(g["tarih"].astype(str))
        alinan = set(g.loc[g["durum"] == 0, "tarih"].astype(str))
        # Hiçbir paritede işleme dönüşmeyen olayın sebebi: paritelerindeki emirlerin hepsi aynı sebeple alınmadıysa
        # o sebep (motor.DURUM), sebepler paritelerde farklıysa "karma". Tek pozisyon kuralı bunlardan yalnız biridir.
        sebep: dict[str, int] = {}
        # Açık pozisyon yüzünden alınmayan olayda açık duran pozisyonun olayı: adayın giriş dakikası, aynı paritede
        # alınmış bir işlemin girişiyle serbest kaldığı dakika arasına düşer (motorun kuralı: çıkış açılışta olduysa o
        # dakika serbesttir, mum içinde olduysa bir sonraki). Olay düzeyinde, paritelerde tek bir olay türüyse o,
        # farklıysa "karma". Basın toplantısı satırlarının hangi alt küme olduğunu bu sayım söyler (ör. yalnız
        # kararın işleminin toplantıdan önce kapandığı toplantılar).
        acik: dict[str, int] = {}
        kod_acik = next(k for k, v in mt.DURUM.items() if v == "pozisyon_acik")
        for tarih_, gg in g[~g["tarih"].astype(str).isin(alinan)].groupby(g["tarih"].astype(str)):
            kod = set(int(k) for k in gg["durum"].unique())
            ad = mt.DURUM[kod.pop()] if len(kod) == 1 else "karma"
            sebep[ad] = sebep.get(ad, 0) + 1
            if ad == "pozisyon_acik":
                tur: set[str] = set()
                for _, r in gg[gg["durum"] == kod_acik].iterrows():
                    a_ = alinmis[(alinmis["cift"] == r["cift"]) & (alinmis["giris_i"] <= r["giris_i"])
                                 & (alinmis["serbest_i"] > r["giris_i"])]
                    tur |= set(a_["olay"].astype(str))
                k_ = tur.pop() if len(tur) == 1 else ("karma" if tur else "bulunamadı")
                acik[k_] = acik.get(k_, 0) + 1
        out[str(olay)] = {"takvim": int((tk["olay"] == olay).sum()), "aday": len(aday), "alinan": len(alinan),
                          "engellenen": len(aday - alinan), "sebep": sebep, "acik_olay": acik,
                          "aday_satir": int(len(g)), "alinan_satir": int((g["durum"] == 0).sum())}
    return out


def saat_rejimi(kok: Path, a: ay.Ayar, ciftler: list[str], birimler: dict) -> dict:
    """Birden çok yerel saati olan olay türleri, saat saat (bilgi ölçüsü: devam ailesine girmez, hüküm değiştirmez).

    ECB basın toplantısı 21.07.2022'ye kadar 14:30 Frankfurt'ta başlıyordu; o an çoğu hafta 08:30 New York'a, yani
    ABD veri dakikasına düşer (toplantılar perşembe; ABD haftalık işsizlik başvuruları her perşembe 08:30'da, bazı
    günlerde ABD TÜFE'si de aynı dakikada). O rejimde basın toplantısının ilk mumu büyük ölçüde ABD verisinin
    tepkisidir. Rejim başına: olay sayısı ve dönemi, New York karşılığı ve hafta günü, aynı dakikadaki öbür takvim
    olayları, örneklem içi/dışı dağılımı; devam tablosunun ana mumunda kırılım ve fade ortalaması (haber_analiz'in
    kendi hücre tanımıyla, olay düzeyinde); beş haber stratejisinin varsayılanında alınan işlem, olay ve ortalama R;
    haber öncesi aralığın medyan genişliği (N3, N4). Makasın saat saat ölçüsü veri denetiminde
    (kalite.haber_makasi → `saat`)."""
    import haber_analiz as ha
    tk = takvim.tumu()
    if not len(tk):
        return {}
    tk = tk.astype({c: str for c in ("olay", "tarih", "yerel_saat", "bolge")})
    utc = pd.to_datetime(tk["utc_sn"].to_numpy(np.int64), unit="s", utc=True)
    tk["ny"] = [f"{x.hour:02d}:{x.minute:02d}" for x in utc.tz_convert(z.NEWYORK)]
    # Olayın KENDİ bölgesindeki hafta günü (0 = pazartesi).
    tk["hafta_gunu"] = [int(u.tz_convert(b).dayofweek) for u, b in zip(utc, tk["bolge"])]
    ayni = tk.groupby("utc_sn")["olay"].apply(list)
    devam = [kok / "haber" / "devam" / f"{c}.parquet" for c in ciftler]
    dv = pd.concat([pd.read_parquet(d) for d in devam if d.exists()], ignore_index=True) if any(
        d.exists() for d in devam) else pd.DataFrame()
    if len(dv):
        dv = dv[np.isfinite(dv["gun_atr_pip"]) & (dv["gun_atr_pip"] > 0) & (dv["tf"] == ha.ANA_TF)]
        dv = dv.merge(tk[["olay", "tarih", "yerel_saat"]], on=["olay", "tarih"], how="left")
    islem = {b: _birlesik_islem(kok, b, ciftler, birimler[b]["varsayilan"]) for b in HABER_BIRIM if b in birimler}
    out = {}
    for olay, g in tk.groupby("olay"):
        if g["yerel_saat"].nunique() < 2:
            continue
        rej = {}
        for s, gs in g.groupby("yerel_saat"):
            diger = sorted({(o2, r["tarih"]) for _, r in gs.iterrows() for o2 in ayni.get(r["utc_sn"], []) if o2 != olay})
            v = {"n": int(len(gs)), "ilk": gs["tarih"].min(), "son": gs["tarih"].max(),
                 "ic": int((gs["tarih"] <= a.ic_bitis.isoformat()).sum()),
                 "dis": int((gs["tarih"] >= a.dis_baslangic.isoformat()).sum()),
                 "ny": {k: int(n) for k, n in gs["ny"].value_counts().sort_index().items()},
                 "hafta_gunu": {str(k): int(n) for k, n in gs["hafta_gunu"].value_counts().sort_index().items()},
                 "ayni_dakika": [{"olay": o2, "tarih": t} for o2, t in diger],
                 "devam": {}, "strateji": {}, "aralik_pip": {}}
            if len(dv):
                for ufuk, gd in dv[(dv["olay"] == olay) & (dv["yerel_saat"] == s)].groupby("ufuk"):
                    h = ha._hucre(gd, kume=True)
                    v["devam"][str(int(ufuk))] = {"n_olay": h["n_olay"],
                                                  "kir": h["kir"]["ort_atr_yuzde"], "fad": h["fad"]["ort_atr_yuzde"],
                                                  "kir_oos": h["kir"]["oos_ort_atr_yuzde"],
                                                  "fad_oos": h["fad"]["oos_ort_atr_yuzde"],
                                                  "n_oos": h["kir"]["oos_n"]}
            tarihler = set(gs["tarih"])
            for b, isl in islem.items():
                if not len(isl) or "olay" not in isl.columns:
                    continue
                x = isl[(isl["olay"] == olay) & isl["tarih"].astype(str).isin(tarihler)]
                if not len(x):
                    v["strateji"][b] = {"n": 0, "n_olay": 0}
                    continue
                v["strateji"][b] = {"n": int(len(x)), "n_olay": int(x["tarih"].nunique()), "r": float(x["r"].mean()),
                                    "isabet": float((x["pnl_pip"] > 0).mean())}
                if {"ust", "alt"} <= set(x.columns) and x["ust"].notna().any():
                    gen = (x["ust"] - x["alt"]) / x["cift"].map({c: a.nokta_pip(c) for c in x["cift"].unique()})
                    v["aralik_pip"][b] = {"medyan": float(gen.median()), "n": int(gen.notna().sum())}
            rej[str(s)] = v
        out[str(olay)] = {"bolge": g["bolge"].iloc[0], "rejim": rej}
    return out


def olcu_disi(kok: Path, ciftler: list[str], n1_tf: int | None = None) -> dict:
    """Takvimde durup bir haber ölçüsüne girmeyen olaylar, adıyla ve sebebiyle — ölçünün GERÇEK düşürmelerinden:
      cerceve     olay çerçevesinin atladıkları (devam tablosu, beş strateji ve FOMC tablosu bu çerçeveden kurulur;
                  ana mum)
      devam       çerçevede olup devam tablosuna (ana mum) girmeyenler: ilk mumda yön yok, sonraki mum, giriş dakikası
                  ya da çıkış fiyatı yok (strat_haber.devam); sebep ve hangi ufuklarda düştüğü
      devam_atr   günlük ATR'si olmayan günün olayı: devam tablosunun ölçü birimi kurulamaz (haber_analiz.devam_toplu;
                  örneklemin ilk haftası)
      patika      ortalama patikanın dışında kalanlar
    Parite başına; bir olay bütün paritelerinde dışarıdaysa `her_paritede`. İlk mumda yönü olmayan olay ilk mumun
    yönüyle giren N1'in varsayılanına da girmez — N1 varsayılanının mumu ana mumla aynıysa (`n1_ana_mumda`)."""
    import haber_analiz as ha
    cer, pat, dev, atr = {}, {}, {}, {}
    for c in ciftler:
        h = _oku(kok / "sonuc" / "haber" / f"{c}.json") or {}
        for e in ((h.get("atlanan_olay") or {}).get(str(ha.ANA_TF)) or []):
            cer.setdefault((e["olay"], e["tarih"]), {})[c] = e["neden"]
        for o, p in (h.get("patika") or {}).items():
            for e in (p or {}).get("dislanan") or []:
                pat.setdefault((o, e["tarih"]), {})[c] = e["neden"]
        for ufuk, lst in ((((h.get("devam_dusen") or {}).get(str(ha.ANA_TF))) or {}).items()):
            for e in lst or []:
                dev.setdefault((e["olay"], e["tarih"]), {}).setdefault(c, {}).setdefault(e["neden"], set()).add(
                    int(ufuk))
    for e in (_oku(kok / "sonuc" / "haber" / "devam.json") or {}).get("atr_dusen") or []:
        if e["cift"] in ciftler:
            atr.setdefault((e["olay"], e["tarih"]), {})[e["cift"]] = "gunluk_atr_yok"
    tk = takvim.tumu()
    esle = {(r["olay"], r["tarih"]): set(r["ciftler"].split()) & set(ciftler) for _, r in tk.iterrows()}
    ufuklar = sorted(int(u) for u in ha.UFUK)

    def liste(d: dict) -> list[dict]:
        return [{"olay": o, "tarih": t, "parite": dict(sorted(v.items())),
                 "her_paritede": bool(esle.get((o, t))) and set(v) >= esle.get((o, t), set())}
                for (o, t), v in sorted(d.items(), key=lambda kv: (kv[0][1], kv[0][0]))]
    devam = []
    for (o, t), v in sorted(dev.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        devam.append({"olay": o, "tarih": t,
                      "parite": {c: sorted(n) for c, n in sorted(v.items())},
                      # sebep başına düştüğü ufuklar; bütün ufuklarda düştüyse olay o paritede tablonun dışındadır
                      "ufuk": {c: {nd: sorted(u) for nd, u in sorted(n.items())} for c, n in sorted(v.items())},
                      "tum_ufuk": {c: sorted(set().union(*n.values())) == ufuklar for c, n in sorted(v.items())},
                      "her_paritede": bool(esle.get((o, t))) and set(v) >= esle.get((o, t), set())})
    return {"cerceve": liste(cer), "patika": liste(pat), "devam": devam, "devam_atr": liste(atr),
            "ana_tf": int(ha.ANA_TF), "ufuklar": ufuklar,
            "n1_ana_mumda": (n1_tf == int(ha.ANA_TF)) if n1_tf is not None else None}


def hedef_uzaklik(isl: pd.DataFrame) -> dict | None:
    """Hedefin girişten uzaklığı, girişteki risk biriminde ((hedef − giriş)·yön / R): R katı hedefte tanımı gereği
    k, seviye hedefinde (VWAP, pivot, haber öncesi fiyat, aralığın öbür ucu) işlemden işleme değişir."""
    if not len(isl) or "hedef" not in isl:
        return None
    x = isl[np.isfinite(isl["hedef"].to_numpy(float))]
    if not len(x):
        return None
    u = (x["hedef"] - x["giris_f"]) * x["yon"] / x["R"]
    out = {"n": int(len(u)), "medyan": float(u.median()), "c1": float(u.quantile(0.25)), "c3": float(u.quantile(0.75)),
           "pay_2r_ustu": float((u > 2).mean()), "cift": {c: float(g.median()) for c, g in u.groupby(x["cift"])}}
    return out


def gun_ici_yogunluk(kok: Path, birim: str, ciftler: list[str], p: dict, a: ay.Ayar) -> dict:
    """Örneklem dışında işlem açılan günlerin kaçında iki ya da daha çok işlem var ve kaç sinyal açık pozisyon
    yüzünden alınmadı (tek pozisyon kuralı)."""
    out = {}
    for c in ciftler:
        yol = _islem_dosyasi(kok, birim, c, p)
        if not yol.exists():
            continue
        x = pd.read_parquet(yol)
        x = x[x["gun"].to_numpy().astype("datetime64[D]") >= np.datetime64(a.dis_baslangic)]
        al = x[x["durum"] == 0]
        sayi = al.groupby("gun").size()
        out[c] = {"islem_gunu": int(len(sayi)), "iki_ve_ustu": int((sayi >= 2).sum()),
                  "pay": float((sayi >= 2).mean()) if len(sayi) else None,
                  "atlanan_sinyal": int((x["durum"] == 1).sum()), "islem": int(len(al))}
    return out


# ───────────────────────────────────────────── yerel tatiller (betimleyici)
def tatil_betimi(kok: Path, birimler: dict, ciftler: list[str], a: ay.Ayar) -> dict:
    """Yerel tatillerde işlemlerin sonucu — ön kayıt dışı, betimleyici; hükmü değiştirmez. Kurallar yalnız hafta içine
    düşen 25 Aralık ve 1 Ocak'ı işlem günü saymaz (gunluk.TATIL_TAKVIM); İngiltere'nin banka tatillerinde Londra
    kapalıyken, ABD'de Federal Reserve Bankaları kapalıyken (dolar takası yok) de sıradan gün gibi işlem açarlar.
    Listeler resmî kaynaklardan (tatil.py). Her birimin önceden kayıtlı varsayılanı, dört paritenin alınan işlemleri
    birlikte: İngiltere tatili, ABD tatili ve ikisi de olmayan günler; işlem sayısı ve ortalama net R, bütün dönem ve
    örneklem dışı. İşlemin günü FX günüdür (New York 17:00'de başlar); Londra ve New York seansları o günün içindedir.
    İki ülkenin ortak tatili iki satıra da girer. Sınama yapılmaz: on dolayında işlemlik bir kümede ortalama, ancak
    kuralın o günlerde de sıradan gün gibi işlediğini gösterir."""
    import tatil
    from gunluk import TATIL_TAKVIM
    o = tatil.ozet(a.baslangic, a.bitis, set(TATIL_TAKVIM))
    ing, ab = {x["tarih"] for x in o["ingiltere"]}, {x["tarih"] for x in o["abd"]}
    out = {"ingiltere": o["ingiltere"], "abd": o["abd"], "ikisi": o["ikisi"],
           "kunye": {"kaynak": o["kaynak"], "zaman": o["zaman"], "ingiltere": o["ingiltere_sinama"],
                     "abd": o["abd_sinama"], "oz": tatil.ozu()},
           "birim": {}}
    for b, v in birimler.items():
        isl = _birlesik_islem(kok, b, ciftler, v["varsayilan"])
        if not len(isl):
            continue
        gun = pd.to_datetime(isl["gun"]).dt.strftime("%Y-%m-%d").to_numpy()
        dis = isl["gun"].to_numpy().astype("datetime64[D]") >= np.datetime64(a.dis_baslangic)
        m_ing, m_ab = np.isin(gun, list(ing)), np.isin(gun, list(ab))
        satir = {}
        for ad, m in (("ingiltere", m_ing), ("abd", m_ab), ("diger", ~(m_ing | m_ab))):
            satir[ad] = {}
            for d, dm in (("tum", np.ones(len(isl), bool)), ("oos", dis)):
                r = isl["r"].to_numpy(np.float64)[m & dm]
                satir[ad][d] = {"n": int(len(r)), "r": float(r.mean()) if len(r) else None,
                                "gun": int(len(set(gun[m & dm])))}
        out["birim"][b] = satir
    return out


# ───────────────────────────────────────────── birim
def birim_ozet(kok: Path, birim: str, ciftler: list[str], a: ay.Ayar, isi_eksen: tuple[str, str]) -> dict | None:
    import kosu
    sonuc = {c: _oku(kok / "sonuc" / birim / f"{c}.json") for c in ciftler}
    sonuc = {c: s for c, s in sonuc.items() if s}
    if not sonuc:
        return None
    ilk = next(iter(sonuc.values()))
    # Birimin GERÇEK ızgarasının değerleri (koşulan kombinasyonlardan): ders tablosu ailenin ızgarasını değil bunu
    # basar. Birimin sabitlediği boyut tek değerle görünür; tanımsız bileşimler (NY IB'de 60 dk mum + 60 dk ilk denge,
    # pivot kırılımında 'seviye' hedefi) zaten listede yoktur.
    izgara_deger: dict = {}
    for r in ilk["izgara"]:
        for k, v in r["p"].items():
            izgara_deger.setdefault(k, [])
            if v not in izgara_deger[k]:
                izgara_deger[k].append(v)
    out = {"aile": ilk["aile"], "kombinasyon": ilk["kombinasyon"], "varsayilan": ilk["varsayilan"], "cift": {},
           "izgara_deger": izgara_deger,
           # birimin sabitlediği boyutlar ve ön kaydın kendi varsayılanı (birim varsayılanı ondan türetilir: NY IB 08:00)
           "sabit": dict(kosu.BIRIMLER[birim]["sabit"]),
           "onkayit_varsayilan": dict(kosu.ONKAYIT[ilk["aile"]][kosu.BIRIMLER[birim]["varsayilan"]])}
    egri_v, egri_s = {}, {}
    for c, s in sonuc.items():
        va, se, wf = s.get("varsayilan_analiz"), s.get("secilen_analiz"), s.get("walk_forward") or {}
        egri_v[c] = (va or {}).get("egri")
        egri_s[c] = (se or {}).get("egri")
        kirp = lambda d: {k: v for k, v in (d or {}).items() if k not in ("egri", "ornek", "p")} if d else None  # noqa: E731
        out["cift"][c] = {
            "varsayilan": kirp(va), "secilen_p": s.get("secilen"), "secilen": kirp(se),
            "walk_forward": {"secimler": wf.get("secimler"), "ozet": wf.get("ozet"),
                             "sinanan_yillar": wf.get("sinanan_yillar")},
            "isi": isi(s, isi_eksen), "izgara_ozet": izgara_ozet(s),
            # Seçilenin çevresi: öbür parametreleri seçilende tutan kesit ve tek parametre komşuları.
            "isi_secilen": isi(s, isi_eksen, s["secilen"]) if s.get("secilen") else None,
            "komsular": komsular(s),
            # Fiksing kurallarında ay sonu ayrımı üç zaman diliminde (öbür parametreler varsayılanda; kosu.ay_sonu_tf).
            "ay_sonu_tf": s.get("ay_sonu_tf"),
            "tf": tf_kiyas(s), "tf_haber_kaymasiz": s.get("tf_haber_kaymasiz"),
            "varyant": {pa: varyant(s, pa) for pa in varyant_parametreleri(birim, izgara_deger)},
            "egri": {"varsayilan": haftalik(egri_v[c]), "secilen": haftalik(egri_s[c]),
                     "walk_forward": haftalik(wf.get("egri"))},
            "ornek": ornek_olaylari((va or {}).get("ornek") or [], c),
            # Yorum duyarlılığı (kosu.YORUM): ön kaydın harfinin ikinci okumasıyla varsayılan ve ızgaradan seçim.
            "yorum": s.get("yorum"),
        }
    out["tf_bos"] = tf_bos(out)
    out["havuz"] = {"varsayilan": havuz(kok, birim, list(sonuc), ilk["varsayilan"], egri_v, a)}
    tum_islem = _birlesik_islem(kok, birim, list(sonuc), ilk["varsayilan"])
    if "olay" in tum_islem.columns:
        out["haber_olay"] = haber_olay(tum_islem, a)
        out["tek_pozisyon"] = tek_pozisyon(kok, birim, list(sonuc), ilk["varsayilan"])
    out["hedef_uzaklik"] = hedef_uzaklik(tum_islem)
    out["durum"] = durum_sayimi(kok, birim, list(sonuc), ilk["varsayilan"])
    # Parite başına, varsayılan ve seçilen ayrı: düşen emirler sebebiyle (ders seçilenin düşen sinyalini de basar).
    out["durum_parite"] = {c: {"varsayilan": durum_parite(kok, birim, c, ilk["varsayilan"]),
                               "secilen": (durum_parite(kok, birim, c, s["secilen"]) if s.get("secilen") else {})}
                           for c, s in sonuc.items()}
    out["gun_ici"] =gun_ici_yogunluk(kok, birim, list(sonuc), ilk["varsayilan"], a)
    # Hüküm özeti: parite başına önceden kayıtlı varsayılan ve ızgaradan seçilen
    out["hukum"] = {c: {"varsayilan": (v["varsayilan"] or {}).get("hukum"),
                        "varsayilan_tum": (v["varsayilan"] or {}).get("hukum_tum"),
                        "secilen": (v["secilen"] or {}).get("hukum") if v["secilen"] else None,
                        "maliyet_yiyor": (v["varsayilan"] or {}).get("maliyet_yiyor"),
                        "maliyet_yiyor_oos": (v["varsayilan"] or {}).get("maliyet_yiyor_oos")}
                    for c, v in out["cift"].items()}
    out["_gunluk_varsayilan"] = {c: gunluk_seri(e) for c, e in egri_v.items()}
    return out


def korelasyon(birimler: dict, a: ay.Ayar) -> dict:
    """Stratejiler arası günlük R korelasyonu: her birimin önceden kayıtlı varsayılanı, dört paritenin
    günlük R toplamı (havuz). İşlemsiz günler 0 sayılır (Sharpe ile aynı tanım); bütün dönem ve
    örneklem dışı ayrı. Birlikte işlem görmeyen iki stratejinin korelasyonu tanımsız değil SIFIRA
    yakındır — bu bir çeşitlendirme ölçüsüdür, 'aynı şeyi mi alıyorlar' sorusunun cevabı."""
    seriler = {}
    for b, v in birimler.items():
        g = [s for s in v["_gunluk_varsayilan"].values() if len(s)]
        if g:
            seriler[b] = pd.concat(g, axis=1, sort=True).fillna(0.0).sum(axis=1)
    if len(seriler) < 2:
        return {}
    df = pd.concat(seriler, axis=1, sort=True).fillna(0.0)
    out = {"birimler": list(df.columns)}
    for ad, m in (("tum", np.ones(len(df), bool)), ("oos", df.index >= pd.Timestamp(a.dis_baslangic))):
        c = df[m].corr()
        out[ad] = [[None if not np.isfinite(x) else round(float(x), 3) for x in row] for row in c.to_numpy()]
    return out


def aile_secimi(kok: Path, ciftler: list[str]) -> dict:
    """Ön kayıt deflated Sharpe'ın deneme sayısını AİLE başına koyar ([saglamlik] dsr) ve seçimi ailenin tek
    ızgarasından ister; koşu aileleri birimlere böldü ve birim başına seçer (kosu.BIRIMLER). Bölünen her ailenin parite
    başına iki cevabı, koşu yeniden yapılmadan koşu çıktısından:
      secim   ailenin bütün ızgarasından tek seçim (aynı kural: asgari işlem, en yüksek örneklem içi Sharpe, tolerans
              içinde ilk; ailenin ızgara sırası birimlerin BIRIMLER sırasıdır). Ailenin en iyi kombinasyonu bir
              birimin en iyisidir, yani bir birimin seçilenidir; hükmü o seçilenin hükmüdür
      dsr     her birimin seçileninin deflated Sharpe'ı ailenin BÜTÜN denemeleriyle (seçilenin gözlem sayısı, çarpıklık
              ve basıklığı koşu çıktısından: saglamlik.dsr_ozetten)"""
    import kosu
    aileler: dict[str, list[str]] = {}
    for b, t in kosu.BIRIMLER.items():
        aileler.setdefault(t["aile"], []).append(b)
    yil = math.sqrt(mk.YIL_GUN)
    out = {}
    for aile, bs in aileler.items():
        if len(bs) < 2:
            continue
        out[aile] = {"birimler": bs, "cift": {}}
        for c in ciftler:
            sonuc = {b: _oku(kok / "sonuc" / b / f"{c}.json") for b in bs}
            if not all(sonuc.values()):
                continue
            denemeler = [((r["is"] or {}).get("sharpe") if (r["is"] or {}).get("sharpe") is not None
                          else float("nan")) / yil for b in bs for r in sonuc[b]["izgara"]]
            adaylar = []
            dsr = {}
            for b in bs:
                se, p = sonuc[b].get("secilen_analiz"), sonuc[b].get("secilen")
                if not se or not p:
                    continue
                adaylar.append({"birim": b, "p": p, "is": {"sharpe": se["is"].get("sharpe")},
                                "hukum": se.get("hukum")})
                d = se.get("dsr") or {}
                if all(d.get(x) is not None for x in ("sr_yillik", "T", "carpiklik", "basiklik")):
                    a_ = sg.dsr_ozetten(d["sr_yillik"] / yil, np.array(denemeler), int(d["T"]), d["carpiklik"],
                                        d["basiklik"])
                    dsr[b] = {"birim_n": d.get("n_deneme"), "birim_dsr": d.get("dsr"),
                              "birim_dsr_gurultu": d.get("dsr_gurultu"),
                              "aile_n": a_.get("n_deneme"), "aile_dsr": a_.get("dsr"),
                              "aile_dsr_gurultu": a_.get("dsr_gurultu"), "aile_sr0_yillik": a_.get("sr0_yillik"),
                              "aile_sr0_gurultu_yillik": a_.get("sr0_gurultu_yillik")}
            sec = kosu._sec([x for x in adaylar if x["is"]["sharpe"] is not None])
            out[aile]["cift"][c] = {"n_deneme": len(denemeler), "dsr": dsr,
                                    "secim": ({"birim": sec["birim"], "p": sec["p"], "hukum": sec["hukum"],
                                               "is_sharpe": sec["is"]["sharpe"]} if sec else None)}
    return out


#: Ay sonu ailesinin düzeltilmemiş anlamlılık düzeyi (Bonferroni: düzey / sınama sayısı).
AY_SONU_DUZEY = 0.05


def ay_sonu_ailesi(birimler: dict) -> dict:
    """Ay sonu ayrımının çoklu sınama ailesi ve "tutan" ayrımlar — tek tanım (ders özetleri ve "Ne öğrendik" bunu okur).

    Aile, derste ölçülen BÜTÜN ay sonu ayrımlarıdır: fiksing kurallarının her paritesinde önceden kayıtlı varsayılan,
    örneklem içinde seçilen ve varsayılanın zaman dilimi biçimleri (yalnız mum uzunluğu değişir; kosu.ay_sonu_tf).
    Aynı işlem kümesini veren iki ayrım (işlem imzası aynı) tek sınamadır; hiç işlem açmayan biçim sınama değildir.
    Eşik Bonferroni: 0,05 / sınama sayısı.

    Bir ayrım TUTAR: örneklem dışında (2024 →) ay sonu ortalamasının %95 aralığının alt ucu sıfırın üstünde ve ay sonu
    ile öbür günlerin farkı düzeltilmiş eşiğin altında; AYRIK örneklem içinde (2018–2023) de aynı iki şart. Bütün dönem
    tutarlılık ölçütü olamaz: 2024 →'yü içerir, yani örneklem dışı sonuç kendini doğrular. Rastgele yön sınaması alt
    kümeye ön kayıttan SONRA uygulanır; tutma şartına girmez, sonucu yanında durur."""
    uye: list[dict] = []
    for b, v in birimler.items():
        if v.get("aile") != "fiks":
            continue
        for c, x in v["cift"].items():
            gorulen: dict[str, dict] = {}
            adaylar = [("varsayilan", (x.get("varsayilan") or {}).get("p") or v["varsayilan"],
                        (x.get("varsayilan") or {}).get("imza"), (x.get("varsayilan") or {}).get("ay_sonu")),
                       ("secilen", x.get("secilen_p"), (x.get("secilen") or {}).get("imza"),
                        (x.get("secilen") or {}).get("ay_sonu"))]
            adaylar += [(f"tf{t}", y.get("p"), y.get("imza"), y.get("ayrim"))
                        for t, y in sorted((x.get("ay_sonu_tf") or {}).items(), key=lambda kv: int(kv[0]))]
            for kim, p, imza, ayrim in adaylar:
                if not imza or not ayrim:
                    continue
                if imza in gorulen:
                    gorulen[imza]["esdeger"].append(kim)
                    continue
                gorulen[imza] = {"birim": b, "cift": c, "kim": kim, "tf": int((p or {}).get("tf", 0)) or None,
                                 "p": p, "imza": imza, "esdeger": [], "ayrim": ayrim}
            uye += list(gorulen.values())
    n = len(uye)
    esik = AY_SONU_DUZEY / n if n else None
    for u_ in uye:
        a_ = u_["ayrim"]
        sart = {}
        for d in ("oos", "is"):
            x = (a_.get("ay_sonu") or {}).get(d) or {}
            f = (a_.get("fark") or {}).get(d) or {}
            sart[d] = {"alt_arti": bool(x.get("ga_alt") is not None and x["ga_alt"] > 0),
                       "fark_esik": bool(f.get("p") is not None and esik is not None and f["p"] < esik),
                       "isaret_arti": bool(x.get("beklenti_r") is not None and x["beklenti_r"] > 0)}
        u_["sart"] = sart
        u_["tutar"] = sart["oos"]["alt_arti"] and sart["oos"]["fark_esik"] and sart["is"]["alt_arti"] \
            and sart["is"]["fark_esik"]
        u_.pop("ayrim")
    return {"n": n, "duzey": AY_SONU_DUZEY, "esik": esik, "uye": uye,
            "tutan": [{k: u_[k] for k in ("birim", "cift", "kim")} for u_ in uye if u_["tutar"]]}


# ───────────────────────────────────────────── zaman tablosu (TSİ)
def zaman_tablosu(a: ay.Ayar) -> dict:
    yillar = list(range(a.baslangic.year, a.bitis.year + 1))
    ara = {str(y): [{"ilk": b.isoformat(), "son": s.isoformat(), "rejim": r} for b, s, r in z.ara_donemler(y)]
           for y in yillar}
    # Her rejimden bir temsilci gün (2026): olayların TSİ saati rejime göre değişir.
    temsil = [date(2026, 1, 15), date(2026, 3, 18), date(2026, 6, 17), date(2026, 10, 28)]
    return {"ara_donem": ara, "gecis": {str(y): [(g.isoformat(), t) for g, t in z.gecisler(y)] for y in yillar},
            "tablo": z.tsi_tablosu(temsil), "rejim_adi": z.REJIM_ADI,
            # Ölçüm dosyası anahtarları sıralı yazar; tablonun satır sırası ayrıca taşınır (zaman.OLAYLAR).
            "olay_sira": [ad for ad, _, _ in z.OLAYLAR],
            "tsi_sabit": z.tsi_sabit_mi(a.baslangic, a.bitis)}


# ───────────────────────────────────────────── takvim ve veri
#: Takvim satırının notunda saati bir KURALDAN aldığını söyleyen kalıplar (takvim_kur.py'nin yazdığı notlar):
#: Fed'in 13.03.2013 kuralı, ECB'nin 27.06.2022 karar saati duyurusu, BoE'nin yayım kuralı.
SAAT_KURAL_KALIP = r"kuralından|yayım kuralı|karar saati ECB"


HAFTA_GUNU = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def takvim_ozet() -> dict:
    d = BURASI / "veri" / "takvim"
    out = {"kunye": _oku(d / "kunye.json"), "sinama": None, "sayim": {}}
    out["ozler"] = takvim.ozler()
    df = takvim.tumu()
    if len(df):
        df = df.astype({c: str for c in ("olay", "tarih", "yerel_saat", "bolge", "kaynak")})
        if "not" not in df.columns:
            df["not"] = ""
        df["not"] = df["not"].fillna("").astype(str)
        # Kullanıcının ek dosyası (veri/takvim/ek.csv) varsa olaylar ona da bakar: sayım küme küme yazılır.
        out["kume"] = {o: {k: int(n) for k, n in g["kume"].value_counts().items()} for o, g in df.groupby("olay")}
        out["sayim"] = {o: {"toplam": int(len(g)), "yil": {y: int(n) for y, n in g["tarih"].str[:4].value_counts()
                                                           .sort_index().items()},
                            # yerel saat × bölge dağılımı ve kaynağın alan adı (dersin takvim tablosu)
                            "saat": {f"{s} {b}": int(n) for (s, b), n in g.groupby(["yerel_saat", "bolge"]).size().items()},
                            # her yerel saatin ilk ve son tarihi (saat değişikliklerinin günü: ECB 13:45 → 14:15)
                            "saat_aralik": {f"{s} {b}": [x["tarih"].min(), x["tarih"].max()]
                                            for (s, b), x in g.groupby(["yerel_saat", "bolge"])},
                            "olaganustu": [{"tarih": r["tarih"], "saat": r["yerel_saat"], "bolge": r["bolge"]}
                                           for _, r in g.iterrows() if "olağanüstü" in r["not"]],
                            # saatin kaynağı: o tarihin kendi metni (ambargo satırı, karar metninin yayım saati,
                            # duyurunun cümlesi, Fed'in etkinlik takvimi) ya da kurumun yayım KURALI
                            "saat_kaynagi": {"tarih": int((~g["not"].str.contains(SAAT_KURAL_KALIP)).sum()),
                                             "kural": int(g["not"].str.contains(SAAT_KURAL_KALIP).sum())},
                            "kaynak": sorted({u.split("/")[2] for u in g["kaynak"] if u.startswith("http")}),
                            # Olayın yerel tarihinin haftanın günü: haber kurallarında "haftanın günü" koşulunun
                            # kovası çoğu zaman olay türünün vekilidir (cuma ≈ NFP).
                            "hafta_gunu": {HAFTA_GUNU[int(k)]: int(n) for k, n in
                                           pd.to_datetime(g["tarih"]).dt.dayofweek.value_counts().sort_index().items()},
                            "ilk": g["tarih"].min(), "son": g["tarih"].max()}
                        for o, g in df.groupby("olay")}
        # Aynı UTC dakikasına düşen iki takvim olayı (ör. ABD TÜFE'si ile 14:30 Frankfurt'taki ECB basın toplantısı).
        out["ayni_dakika"] = [sorted([{"olay": r["olay"], "tarih": r["tarih"]} for _, r in g.iterrows()],
                                     key=lambda x: x["olay"])
                              for _, g in df.groupby("utc_sn") if len(g) > 1]
        # Fed'in etkinlik takviminin basın toplantısını AYRI SATIRLA listelediği dönem: o dönemin kaç toplantısında satır
        # var ve hangisinde yok (satırsız toplantının saati kuraldan gelir). Metodoloji dersinin "N toplantının M'i"
        # cümlesi buradan; ilk satırlı toplantıdan önceki toplantılar dönemin dışındadır.
        tt = ((((out["kunye"] or {}).get("fomc") or {}).get("basin_saat_tarih")) or {}).get("takvim") or []
        if tt and "FOMC_basin" in set(df["olay"]):
            gb = df[(df["olay"] == "FOMC_basin") & (df["tarih"] >= min(tt))]["tarih"]
            out["fomc_takvim_donemi"] = {"ilk": min(tt), "toplanti": int(len(gb)), "satirli": int(gb.isin(tt).sum()),
                                         "satirsiz": sorted(gb[~gb.isin(tt)].tolist())}
    s = _oku(d / "sinama.json")
    if s:
        # Basın toplantıları fiyattan SINANMAZ (konuşma tek dakikada sıçrama yapmaz); bilgi olarak toplantının ilk
        # 15 dakikasındaki ortalama dakikalık aralığın önceki 15 dakikaya oranı, parite başına.
        bilgi: dict = {}
        for e in s.get("olay") or []:
            if e.get("hukum") != "basin_bilgi":
                continue
            for p, v in (e.get("parite") or {}).items():
                r = (v or {}).get("ilk15_once15_orani")
                if r is not None and np.isfinite(r):
                    bilgi.setdefault(e["olay"], {}).setdefault(p, []).append(float(r))
        out["sinama"] = {"kural": s.get("kural"), "ozet": s.get("ozet"), "celiski": s.get("celiski"),
                         "celiski_olay": [e for e in s.get("olay") or [] if e.get("hukum") == "celiski"],
                         # Sessiz kalan olaylar adıyla (piyasa ne resmî dakikada ne dört aday saatte kımıldamadı)
                         "sessiz_olay": [{k: e.get(k) for k in ("olay", "tarih", "yerel_saat", "bolge")}
                                         for e in s.get("olay") or [] if e.get("hukum") == "sessiz"],
                         # ±6 saatlik uzak tarama (yalnız rapor): resmî saatten açıkça büyük uzak hareket
                         "uzak": s.get("uzak") or [],
                         "basin_bilgi": {o: {p: {"n": len(x), "medyan": float(np.median(x)),
                                                 "birden_buyuk": int(sum(r > 1 for r in x))}
                                             for p, x in sorted(v.items())} for o, v in sorted(bilgi.items())}}
    return out


def veri_ozet(ciftler: list[str]) -> dict:
    """Arşivin künyesi ve kalite raporu, YALNIZ ayardaki paritelerden (ayardan çıkarılan paritenin dosyaları kalsa da)."""
    kunye = {}
    for yol in sorted((ay.DUKA / "kunye").glob("*.json")):
        for k, v in (_oku(yol) or {}).get("birimler", {}).items():
            if k.split("/")[0] not in ciftler:
                continue
            kunye[k] = {x: v.get(x) for x in ("gun", "gun_dolu", "satir", "tam", "istek", "ret", "sha256",
                                               "icerik_ozu", "ilk_gun", "son_gun")}
            kunye[k]["gun_bos"] = len(v.get("gun_bos", []))
            kunye[k]["gun_404"] = len(v.get("gun_404", []))
            # Kaynağın boş ya da "yok" döndürdüğü günler adıyla (az sayıda): dolu gün ile istenen gün arasındaki fark.
            kunye[k]["bos_gunler"] = sorted({str(x)[:10] for x in (v.get("gun_bos") or []) + (v.get("gun_404") or [])})
            kunye[k]["gun_hata"] = len(v.get("gun_hata", []))
    kalite = {c: v for c, v in (_oku(ay.DUKA / "kalite.json") or {}).items() if c in ciftler} or None
    return {"kalite": kalite, "arsiv": kunye, "tatil_uyum": tatil_uyum(kalite)}


def _fx_gunu(utc: str) -> date:
    """UTC damganın FX günü: New York 17:00'de başlayan gün (17:00 ve sonrası ertesi günün etiketi)."""
    t = pd.Timestamp(utc, tz="UTC").tz_convert(z.NEWYORK)
    return (t + pd.Timedelta(days=1)).date() if t.hour >= 17 else t.date()


def tatil_uyum(kalite: dict | None) -> dict | None:
    """Stratejilerin tatil takvimi (gunluk.TATIL_TAKVIM: 25 Aralık ve 1 Ocak, hafta içine düştüğünde) ile arşivde
    kapsamı %50'nin altında kalan işlem günlerinin (kalite.py) parite parite karşılaştırması. Takvim kuraldır,
    kapsam ölçüdür; ikisinin aynı günleri verdiği bir beyan değil bu kayıttır."""
    from gunluk import TATIL_TAKVIM
    if not kalite:
        return None
    out = {}
    for c, e in sorted(kalite.items()):
        if not isinstance(e, dict) or not e.get("ilk") or not e.get("son"):
            continue
        g0, g1 = _fx_gunu(e["ilk"]), _fx_gunu(e["son"])
        takvim = sorted(g.isoformat() for g in pd.bdate_range(g0, g1).date if (g.month, g.day) in TATIL_TAKVIM)
        kapsam = sorted(x[0] for x in (e.get("kapsam") or {}).get("tatil_gunleri") or [])
        out[c] = {"takvim": len(takvim), "kapsam": len(kapsam), "ayni": takvim == kapsam,
                  "yalniz_takvim": sorted(set(takvim) - set(kapsam)), "yalniz_kapsam": sorted(set(kapsam) - set(takvim)),
                  "ilk_fx_gunu": g0.isoformat(), "son_fx_gunu": g1.isoformat()}
    return out


def ay_sonu_kayan(bas: date, bit: date) -> list[str]:
    """Ayın son hafta içi günü ile ayın son Londra iş günü (ön kaydın ay sonu tanımı) ayrışan aylar, örneklemin
    içinde tamamlanan aylarda: o aylarda ay sonu bir önceki iş gününe kayar."""
    out = []
    ay_ = date(bas.year, bas.month, 1)
    while True:
        sonraki = date(ay_.year + (ay_.month == 12), ay_.month % 12 + 1, 1)
        son = sonraki - pd.Timedelta(days=1).to_pytimedelta()
        if son > bit:
            break
        g = son
        while g.weekday() >= 5:
            g -= pd.Timedelta(days=1).to_pytimedelta()
        if not z.londra_ay_sonu(g):
            out.append(f"{ay_.year:04d}-{ay_.month:02d}")
        ay_ = sonraki
    return out


def ileri_bakma_kapsami() -> dict | None:
    """İleriye bakma sınamasının kapsamı, sınamanın KENDİ dosyasından (testler/test_strateji.py, sentetik.py):
    kesim anları, kesim başına koşulan kombinasyon sayısı ve sentetik serinin uzunluğu. Metodoloji dersi sınamayı bu
    kayıtla anlatır; sınama değişirse ders cümlesi de değişir. Okunamazsa None (ders üretimi iddiada düşer)."""
    import ast
    try:
        t = ast.parse((BURASI / "testler" / "test_strateji.py").read_text(encoding="utf-8"))
        st = ast.parse((BURASI / "testler" / "sentetik.py").read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    deger, kesim, sinama = {}, None, []
    for n in t.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            ad = n.targets[0].id
            if ad in ("ORNEK_ILK", "ORNEK_OTEKI", "CIPA_SAYISI") and isinstance(n.value, ast.Constant):
                deger[ad] = int(n.value.value)
            if ad == "CIPA_EK_MUM" and isinstance(n.value, ast.Tuple):
                deger[ad] = [int(x.value) for x in n.value.elts if isinstance(x, ast.Constant)]
            if ad == "KESIMLER":
                kesim = [x.value for x in ast.walk(n.value) if isinstance(x, ast.Constant) and isinstance(x.value, str)
                         and len(x.value) == 16]
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
            sinama.append(n.name)
    gun = bas = None
    for n in st.body:
        if isinstance(n, ast.FunctionDef) and n.name == "dakika_uret":
            ad_ = [a.arg for a in n.args.args]
            dv = dict(zip(ad_[len(ad_) - len(n.args.defaults):], n.args.defaults))
            gun = dv["gun"].value if isinstance(dv.get("gun"), ast.Constant) else None
            bas = dv["bas"].value if isinstance(dv.get("bas"), ast.Constant) else None
    if not kesim or set(deger) != {"ORNEK_ILK", "ORNEK_OTEKI", "CIPA_SAYISI", "CIPA_EK_MUM"} or gun is None:
        return None
    yerel = []
    for x in kesim:
        u = pd.Timestamp(x, tz="UTC")
        lo, ny = u.tz_convert(z.LONDRA).strftime("%H:%M"), u.tz_convert(z.NEWYORK).strftime("%H:%M")
        # Kesim anının seansı (dersin sözcükleri bu sınıftan okunur): UTC gece yarısının ilk saati, Londra
        # açılışından önce, Londra sabahı (açılış → 12:00), New York sabahı (12:00'ye kadar), öbürü.
        an = ("utc_gece_yarisi_sonrasi" if u.hour == 0 else "londra_acilis_oncesi" if lo < "08:00" else
              "londra_sabahi" if lo < "12:00" else "new_york_sabahi" if ny < "12:00" else "diger")
        yerel.append({"utc": x, "londra": lo, "new_york": ny, "an": an,
                      "tsi": u.tz_convert("Europe/Istanbul").strftime("%H:%M")})
    return {"kesim": yerel, "kesim_n": len(kesim), "ornek_ilk": deger["ORNEK_ILK"],
            "ornek_ilk_rastgele": deger["ORNEK_ILK"] - 1, "ornek_oteki": deger["ORNEK_OTEKI"],
            "ornek_oteki_rastgele": deger["ORNEK_OTEKI"] - 1, "sentetik_gun": int(gun), "sentetik_bas": bas,
            # Sinyale çıpalı kesim: birim başına çıpa sayısı ve çıpanın karar anından sonra kaç mum (0: giriş dakikası)
            "cipa_sayisi": deger["CIPA_SAYISI"], "cipa_ek_mum": deger["CIPA_EK_MUM"],
            "sinama": sinama}


# ───────────────────────────────────────────── ana
#: Sonuçlardan sonra verilen ve yeniden koşu gerektirmeyen kararların commit'i (zamanı depodan okunur): sayımla
#: ölçülenler ve hükme girmeyenler. Yeniden koşuyla ölçülenlerin commit'i karsi_olgu.DEGISIKLIKLER'dedir.
SONRADAN_COMMIT = {"hukum_penceresi": "4d5fa720", "olculemedi": "4d5fa720", "tatil": "4d5fa720",
                   "basabas_r": "93df4b61", "onkayitli_iki_olcu": "2c01d199",
                   # zaman çizgisinin bir anı, kural değişikliği değil: dört paritenin ilk tam koşusu
                   "tam_kosu": "09ec1758"}

#: Sonuçtan önceki kodun "ölçülemedi" kuralı (a5268cbe): örneklem dışında 20'den az işlem.
OLCULEMEDI_ESKI_ESIK = 20


def olculemedi_esigi(birimler: dict) -> dict:
    """Sonuçtan önceki "ölçülemedi" kuralı (dönemde 20'den az işlem) bugünkü sonuçlara uygulansaydı: hüküm sayımı ve
    değişen bileşimler, üç pencerede (varsayılan 2024 →, varsayılan bütün dönem, seçilen 2024 →). Kural yalnız etiketi
    değiştirir, yeniden koşu gerekmez."""
    from collections import Counter
    out = {}
    for ad, (taraf, alan, donem) in (("varsayilan", ("varsayilan", "hukum", "oos")),
                                     ("varsayilan_tum", ("varsayilan", "hukum_tum", "tum")),
                                     ("secilen", ("secilen", "hukum", "oos"))):
        bugun, eski, degisen = Counter(), Counter(), []
        for b, v in birimler.items():
            for c, x in v["cift"].items():
                d = x.get(taraf)
                if not d:
                    continue
                h = d.get(alan)
                n = int((d.get(donem) or {}).get("n") or 0)
                e = "olculemedi" if n < OLCULEMEDI_ESKI_ESIK else h
                bugun[h] += 1
                eski[e] += 1
                if e != h:
                    degisen.append({"birim": b, "cift": c, "bugun": h, "n": n})
        out[ad] = {"bugun": dict(bugun), "eski": dict(eski), "degisen": degisen}
    out["esik"] = OLCULEMEDI_ESKI_ESIK
    return out


def karsi_olgu_ozet(kok: Path) -> dict:
    """Sonuçlardan sonra değişen kuralların karşı olgu ölçümü (karsi_olgu.py). Yalnız bugünkü koda ve bugünkü koşu
    çıktısına karşı alınmışsa okunur; değilse ölçüm yazılmaz — eski bir karşı olgu derse "ölçülmüş etki" diye giremez.
    Satır satır kıyas dosyada kalır, ders özetleri okur; her değişikliğin commit'inin işleyen saati depodan."""
    import karsi_olgu as ko
    if not ko.SONUC.exists():
        raise SystemExit("ölçüm yazılmadı: karşı olgu ölçümü yok — .venv/bin/python karsi_olgu.py")
    d = json.loads(ko.SONUC.read_text(encoding="utf-8"))
    hata = []
    if d.get("kod_ozu") != ko.kod_ozu():
        hata.append("koşunun kodu karşı olgu ölçüldükten sonra değişti")
    if d.get("taban_ozu") != ko.taban_ozu(kok):
        hata.append("koşu çıktısı karşı olgunun kıyasladığı çıktı değil")
    eksik = [x["ad"] for x in ko.DEGISIKLIKLER if x["ad"] not in (d.get("degisiklik") or {})]
    if eksik:
        hata.append("karşı olgu eksik: " + ", ".join(eksik))
    if hata:
        raise SystemExit("ölçüm yazılmadı: " + "; ".join(hata) + " — .venv/bin/python karsi_olgu.py")
    out = {}
    for ad, x in d["degisiklik"].items():
        y = {k: v for k, v in x.items() if k != "satir"}
        y["zaman"] = commit_zamani(x.get("commit"))
        # Örneklem dışı net R'si oynayan bileşimler, bugün ve eski kuralla (yön ve büyüklük adıyla yazılsın diye).
        for kim in ("varsayilan", "secilen"):
            oy = []
            for r in x.get("satir") or []:
                v = (r.get(kim) or {}).get("oos_r") or [None, None]
                if v[0] is not None and v[1] is not None and abs(v[0] - v[1]) > 1e-9:
                    oy.append({"birim": r["birim"], "cift": r["cift"], "bugun": v[0], "eski": v[1]})
            if kim in y and oy:
                y[kim] = {**y[kim], "oos_r_oynayan": sorted(oy, key=lambda o: -abs(o["bugun"] - o["eski"]))}
        out[ad] = y
    return out


#: Ölçümün okuduğu ama içe aktarmadığı kod dosyaları (ileri_bakma_kapsami sınamanın kendi dosyasından okur).
KOD_EK = ("testler/test_strateji.py", "testler/sentetik.py")


def kod_kunyesi() -> dict:
    """Ölçümü üreten kod: bu modülün ve içe aktardığı proje modüllerinin (ölçüm sırasında yüklenenler dahil) dosya
    başına SHA-256'sı ve tek özü; KOD_EK'teki dosyalar da. Kapı (dogrula.py) listedeki dosyaları yalnız hashlib ile
    yeniden özetler: biri değiştiyse ve ölçüm yeniden koşulmadıysa ENGEL ("yeniden ölçülmeli"). Liste ölçümün SONUNDA
    alınır, çünkü kapı ağır kütüphaneleri içe aktaramaz ve içe aktarma zincirini kendisi kuramaz."""
    dosya = set(KOD_EK)
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        p = Path(f).resolve()
        try:
            rel = p.relative_to(BURASI)
        except ValueError:
            continue
        if p.suffix != ".py" or rel.parts[0].startswith(".") or "__pycache__" in rel.parts:
            continue
        dosya.add(rel.as_posix())
    ozet = {d: _oz(BURASI / d) for d in sorted(dosya)}
    h = hashlib.sha256()
    for d, o in ozet.items():
        h.update(f"{d}\0{o}\0".encode())
    return {"dosya": ozet, "oz": h.hexdigest()}


def haber_sabitleri() -> dict:
    """Haber ölçülerinin sabitleri (tek tanımları strat_haber, haber_analiz ve gunluk'ta): figür alt yazısı ve dikey
    çizgileri, şablon cümleleri buradan okur — sayı ikinci kez elle yazılmaz."""
    import gunluk
    import haber_analiz as ha
    import strat_haber as sh
    return {"atr_gun": int(gunluk.ATR_GUN), "atr_mum": int(sh.ATR_MUM), "patika_yon_sn": int(sh.PATIKA_YON_SN),
            "fomc_basin_sn": [int(x) for x in sh.FOMC_BASIN_SN], "kova_atr": [float(x) for x in sh.KOVA],
            "kova_adi": list(sh.KOVA_ADI), "ana_tf": int(ha.ANA_TF), "ufuk_dk": [int(x) for x in ha.UFUK]}


def commit_zamani(commit: str | None) -> list[dict]:
    """Bir ya da iki adımlı ("a · b") değişikliğin commit'lerinin işleyen saati (UTC), depodan."""
    zaman = []
    for c in [s.strip() for s in str(commit or "").split("·") if s.strip()]:
        try:
            zaman.append({"commit": c, "zaman": _git("log", "-1", "--format=%cI", c).strip()})
        except Exception:                                 # git yok ya da commit bu klonda değil
            zaman.append({"commit": c, "zaman": None})
    return zaman


def kur(kok: Path | None = None) -> dict:
    import kosu
    a = ay.oku()
    kok = kok or (BURASI / "cikti")
    ciftler = list(a.ciftler)
    birimler = {}
    for b in kosu.BIRIMLER:
        v = birim_ozet(kok, b, ciftler, a, kosu.ISI[b])
        if v:
            birimler[b] = v
    kor = korelasyon(birimler, a)
    for v in birimler.values():
        v.pop("_gunluk_varsayilan", None)
    haber = {c: _oku(kok / "sonuc" / "haber" / f"{c}.json") for c in ciftler}
    onk = tomllib.loads(ONKAYIT_YOL.read_text(encoding="utf-8"))
    olcum = {
        "kunye": {
            "baslangic": a.baslangic.isoformat(), "bitis": a.bitis.isoformat(),
            "ic_bitis": a.ic_bitis.isoformat(), "dis_baslangic": a.dis_baslangic.isoformat(),
            "ciftler": ciftler, "nokta": {c: a.nokta[c] for c in ciftler}, "pip": {c: a.pip[c] for c in ciftler},
            "zaman_dilimleri": list(a.zaman_dilimleri), "kayma_pip": list(a.kayma_pip),
            "temel_kayma_pip": onk["genel"]["temel_kayma_pip"], "haber_kayma_pip": a.haber_kayma_pip,
            "haber_pencere_dk": list(a.haber_pencere_dk), "gun_sonu_et": a.gun_sonu_et,
            "onkayit_ozu": _oz(ONKAYIT_YOL), "ayar_ozu": _oz(BURASI / "ayar.toml"),
            "takvim_ozleri": takvim.ozler(),
            "onkayit_icerik_ozu": _icerik_ozu(onk), "onkayit_gecmisi": (gecmis := onkayit_gecmisi()),
            "onkayit_gecmis_ozet": gecmis_ozet(gecmis),
            # İlk sonuçların görüldüğü commit ve işleyen saati (onkayit_gecmis.ILK_SONUC; saat depodan sınanır).
            "onkayit_ilk_sonuc": {"commit": og.ILK_SONUC[0], "zaman": og.ILK_SONUC[1]},
            "hukum_kurali": onk["hukum"], "secim": onk["secim"], "saglamlik": onk["saglamlik"],
            "kosul": onk["kosul"],
            # Ön kaydın yazmadığı uygulama eşikleri (hüküm kuralının şartları kendi asgarileriyle kurulur): tek
            # tanımları kodda, ders bunları buradan okur.
            "uygulama_esik": {"bootstrap": mk.ASGARI_BOOTSTRAP, "rastgele": sg.ASGARI_RASTGELE,
                              "kosul_oos": sg.ASGARI_KOSUL_OOS, "az_islem": kosu.ASGARI_RASTGELE},
            # Rastgele yön yüzdeliğinin duyarlılığı (bilgi): hangi yüzdelikten sonra ölçüldüğü, çıkarılan en iyi işlem
            # sayıları, sabit tohum listesinin uzunluğu (saglamlik.rastgele_duyarlilik).
            "rastgele_duyarlilik": {"taban": sg.DUYARLILIK_TABAN, "en_iyi": list(sg.DUYARLILIK_EN_IYI),
                                    "tohum": mk.SINIR_TOHUM},
            "ileri_bakma": ileri_bakma_kapsami(),
            "ornek": {"esik": kosu.ORNEK_ESIK, "ek_kayma": kosu.ORNEK_EK_KAYMA},
            # Ön kaydın kural aileleri ve ölçümün birimleri: bir aile birden çok birime bölündüyse adıyla.
            "aile_n": len({v["aile"] for v in kosu.BIRIMLER.values()}),
            "bolunen_aile": sorted({v["aile"] for v in kosu.BIRIMLER.values()
                                    if sum(1 for x in kosu.BIRIMLER.values() if x["aile"] == v["aile"]) > 1}),
            "ay_sonu_kayan": ay_sonu_kayan(a.baslangic, a.bitis),
            # Ön kaydın harfine göre ikinci okuması olan kurallar: birim → [[parametre, harfin okuması], …] (bir
            # kuralın birden çok okuması olabilir; her biri tek başına ölçülür).
            "yorum": {b: [list(x) for x in v] for b, v in kosu.YORUM.items()},
            "haber_sabit": haber_sabitleri(),
        },
        "zaman": zaman_tablosu(a),
        "takvim": takvim_ozet(),
        "veri": veri_ozet(ciftler),
        "birim": birimler,
        "korelasyon": kor,
        "stop_cikis": stop_cikis(kok),
        "aile_secim": aile_secimi(kok, ciftler),
        "haber": {"cift": {c: h for c, h in haber.items() if h}, "devam": _oku(kok / "sonuc" / "haber" / "devam.json"),
                  "saat_rejimi": saat_rejimi(kok, a, ciftler, birimler),
                  # N1'in varsayılan mumu ana mumsa ilk mumda yönü olmayan olay N1'e de girmez (olcu_disi).
                  "olcu_disi": olcu_disi(kok, ciftler, n1_tf=(int(birimler["n1"]["varsayilan"]["tf"])
                                                              if "n1" in birimler else None))},
        # Ay sonu ayrımının çoklu sınama ailesi ve tutan ayrımlar (tek tanım).
        "ay_sonu_aile": ay_sonu_ailesi(birimler),
        # Yerel tatillerde işlemler (ön kayıt dışı, betimleyici).
        "tatil": tatil_betimi(kok, birimler, ciftler, a),
        # Sonuçlardan sonra değişen kuralların ölçülmüş etkisi: yeniden koşuyla (karsi_olgu.py) ve sayımla.
        "karsi_olgu": {"kosu": karsi_olgu_ozet(kok), "olculemedi": olculemedi_esigi(birimler),
                       "zaman": {ad: commit_zamani(c) for ad, c in SONRADAN_COMMIT.items()}},
    }
    tutarlilik(olcum, a)
    # Kod künyesi en sonda: ölçüm sırasında yüklenen her proje modülü listeye girsin.
    olcum["kunye"]["kod"] = kod_kunyesi()
    return _temiz(olcum)


def tutarlilik(olcum: dict, a: ay.Ayar) -> None:
    """Ölçümün girdileri aynı anın girdileri mi: veri denetiminin haber makası bugünkü takvimle kurulmuş mu, takvim
    ayarın penceresiyle mi kurulmuş, ön kaydın geçmişi beklenen geçmiş mi (onkayit_gecmis). Ayrışırsa ölçüm yazılmaz
    (zincirin sırası, elle koşulan bir adım ya da yeniden yazılmış bir geçmiş)."""
    import tatil
    simdi = takvim.ozler()
    tatil_simdi = tatil.ozu()
    hata = []
    for c, v in ((olcum.get("veri") or {}).get("kalite") or {}).items():
        if (v or {}).get("takvim_ozu") != simdi:
            hata.append(f"{c}: veri denetimi (kalite.py) başka bir takvimle koşmuş — takvimden sonra yeniden koşulmalı")
        if ((v or {}).get("yerel_tatil") or {}).get("tatil_ozu") != tatil_simdi:
            hata.append(f"{c}: veri denetimi (kalite.py) başka bir tatil listesiyle koşmuş ya da tatil kapsamını "
                        f"taşımıyor — yeniden koşulmalı")
    k = olcum.get("kunye") or {}
    hata += og.denetle(k.get("onkayit_gecmisi"))
    try:
        t_ilk = _git("log", "-1", "--format=%cI", og.ILK_SONUC[0]).strip()
    except Exception:                                     # git yok ya da commit bu klonda değil
        t_ilk = None
    if t_ilk != og.ILK_SONUC[1]:
        hata.append(f"ilk sonuç commit'inin ({og.ILK_SONUC[0]}) saati depoda {t_ilk}, beklenen {og.ILK_SONUC[1]}")
    pen = ((olcum.get("takvim") or {}).get("kunye") or {}).get("pencere")
    if pen != [a.baslangic.isoformat(), a.bitis.isoformat()]:
        hata.append(f"takvimin penceresi {pen} ayarın penceresiyle aynı değil — takvim_kur.py yeniden koşulmalı")
    if hata:
        raise SystemExit("ölçüm yazılmadı:\n  " + "\n  ".join(hata))


def main(argv: list[str]) -> int:
    kok = Path(argv[0]) if argv else None
    o = kur(kok)
    hedef = (kok or (BURASI / "cikti")) / "ders" / "olcum.json"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
                     encoding="utf-8")
    print(f"✓ {hedef} · {hedef.stat().st_size / 1e6:.1f} MB · {len(o['birim'])} birim")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
