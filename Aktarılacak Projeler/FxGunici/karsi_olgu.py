"""Karşı olgu: ilk sonuçlardan SONRA değişen her uygulama kuralının ölçülmüş etkisi.

Ön kaydın SONRADAN notu (38694c3b) sonuçlardan sonra değişen her kuralın "zamanı, önceki hâli ve ölçülmüş etkisi"ni
metodoloji dersine havale eder. Etki burada ölçülür: her değişiklik kodun GEÇİCİ bir kopyasında tek başına eski
hâline döndürülür (öbür bütün kurallar bugünkü hâliyle), strateji koşusu o kopyada yeniden yapılır ve sonuç bugünkü
koşuyla bileşim bileşim kıyaslanır: hüküm (varsayılanın iki penceresi, seçilen), seçilen kombinasyon, örneklem dışı
işlem başına R, maliyet bayrağı, koşul hükümleri ve değişen işlem sayısı.

Eski hâl bir metin yamasıdır (`DEGISIKLIKLER[*]["yama"]`: dosya, bugünkü metin, eski metin). Her bugünkü metin
dosyada TAM BİR KEZ geçmelidir; geçmiyorsa araç düşer — kod değişip yama eskidiyse sessizce yanlış bir karşı olgu
ölçülmez. Eski metinler git geçmişinden alındı; her değişikliğin commit'i ve işleyen saati `commit` alanındadır
(ders onu oradan basar).

Kıyas, aynı araç içinde yamasız bir kopyada koşan TABAN ile yapılır: iki taraf da aynı koddan çıkar, yalnız tek
kural farklıdır. Sonuç dosyası iki öz taşır:
  kod_ozu    koşunun okuduğu kod (kosu'nun içe aktardığı proje modülleri, takvim, ayar ve ön kayıt dosyaları, bu
             araç) ve veri künyesi (fiyat arşivinin künyesi, olay takvimi). TOML dosyaları AYRIŞTIRILMIŞ içerikleriyle
             girer: yalnız yorumu değişen bir ön kayıt notu koşuyu değiştirmez, karşı olguyu da eskitmez;
  taban_ozu  tabanın sonuç dosyalarının (cikti/sonuc/<birim>/<parite>.json ve devam tablosu) özü.
Ölçüm (ders_olcum) kod özünü yeniden hesaplar ve tabanın özünü BUGÜNKÜ koşu çıktısının (cikti/sonuc) özüyle
kıyaslar: eşitse derslerin bastığı sonuçlar karşı olgunun tabanıyla bayt bayt aynıdır, yani "bugünkü kural" sütunu
dersin kendi sayısıdır. Biri tutmazsa karşı olgu eskidir ve derse giremez.

Koşum:  .venv/bin/python karsi_olgu.py [--paralel N] [--zorla] [--oku <geçici dizin>]
        Kod ve taban özü kayıttakiyle aynıysa yeniden koşmaz (--zorla koşturur). Her (değişiklik, parite) ayrı bir
        süreçtir; kopyalar geçici dizinde kurulur ve iş BAŞARIYLA bitince silinir. Koşulardan sonraki kıyas ya da
        yazım düşerse kopyalar korunur ve yolu basılır; --oku o dizindeki koşulmuş kopyaları yeniden koşmadan
        kıyaslar (yarım saatlik koşu bir kıyas hatasıyla kaybolmasın).

Hesapla değil sayımla bulunan etkiler (yeniden koşu gerekmez) ölçümde: "ölçülemedi" eşiği (ders_olcum.olculemedi_esigi:
önce örneklem dışında 20'den az işlem) ve tatilin kaynağı (ders_olcum.tatil_uyum: önce günün kapsamı).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI / "cikti"
SONUC = CIKTI / "karsi_olgu.json"
PY = sys.executable
CIFTLER = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD")
HABER_BIRIM = ("n1", "n2", "n3", "n4", "n5")

#: Sonuçlardan sonra değişen, işlemleri değiştiren kurallar. `birimler` None ise bütün birimler koşar.
DEGISIKLIKLER: tuple[dict, ...] = (
    {
        "ad": "ham_acilis",
        "commit": "3183b302",
        "birimler": None,
        "yama": [("motor.py",
                  "        # Stop seviyeli emir: giriş tarafının kaymasız açılışı stop'un ötesindeyse işlem yok (kayma işlem"
                  " yaratmaz).\n"
                  "        if stop_tur[e] != 0 and not np.isnan(st):\n"
                  "            ham = ao[i] if y == 1 else bo[i]\n"
                  "            if not ((ham - st) * y > 0.0):\n"
                  "                durum[e] = 2\n"
                  "                continue\n",
                  "")],
    },
    {
        "ad": "bosluk_giris",
        "commit": "3183b302",
        "birimler": None,
        "yama": [("motor.py",
                  "            # Boşluklu sert stop giriş dakikası dahil: emir tarafı stop'un ötesinde açıldıysa dolum o"
                  " açılıştan.\n"
                  "            if sert and (xo - st) * y <= 0.0:\n"
                  "                cf = xo - y * sj; ck = j; nd = 5; mid_c = mo[j]\n"
                  "                kotu = (xo - g) * y\n"
                  "                if kotu < en_kotu:\n"
                  "                    en_kotu = kotu\n"
                  "                break\n"
                  "            if j > i:\n",
                  "            if j > i:\n"
                  "                if sert and (xo - st) * y <= 0.0:\n"
                  "                    cf = xo - y * sj; ck = j; nd = 5; mid_c = mo[j]\n"
                  "                    kotu = (xo - g) * y\n"
                  "                    if kotu < en_kotu:\n"
                  "                        en_kotu = kotu\n"
                  "                    break\n"),
                 ("motor.py",
                  "        if (nd == 3 or nd == 4 or nd == 5 or nd == 6) and ck > i:\n",
                  "        if nd == 3 or nd == 4 or nd == 5 or nd == 6:\n"),
                 ("strat_ortak.py",
                  "        serbest = ci[k] if (nd[k] in (3, 4, 5, 6) and ci[k] > gi[k]) else ci[k] + 1\n",
                  "        serbest = ci[k] if nd[k] in (3, 4, 5, 6) else ci[k] + 1\n")],
    },
    {
        "ad": "onceki_gun",
        "commit": "3183b302",
        "birimler": None,
        "yama": [("gunluk.py",
                  "    onc_h, onc_l, onc_c, onc_o, atr, atr_y, nr4, nr7 = onceki_zincir(h, l, c, o, tatil)\n",
                  "    # ATR: tatil günleri de kotasyon taşıyorsa hesaba girer; değer bugünü içermez (bir kaydırma).\n"
                  "    tr = np.empty(len(gun))\n"
                  "    tr[0] = h[0] - l[0]\n"
                  "    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])\n"
                  "    atr_bugun = _wilder(tr, 14)\n"
                  "    atr = np.concatenate([[np.nan], atr_bugun[:-1]])\n"
                  "    atr_y = _yuzdelik_izleyen(atr)\n"
                  "    onc = lambda x: np.concatenate([[np.nan], x[:-1]])  # noqa: E731\n"
                  "    aralik = h - l\n"
                  "    def nr(n):\n"
                  "        out = np.zeros(len(gun), dtype=bool)\n"
                  "        for i in range(n, len(gun)):\n"
                  "            pen = aralik[i - n:i]\n"
                  "            out[i] = aralik[i - 1] <= pen.min() + 1e-9\n"
                  "        return out\n"
                  "    onc_h, onc_l, onc_c, onc_o, nr4, nr7 = onc(h), onc(l), onc(c), onc(o), nr(4), nr(7)\n")],
    },
    {
        "ad": "secim_esitlik",
        "commit": "3183b302",
        "birimler": None,
        "yama": [("kosu.py",
                  "    en = max(s[\"is\"][\"sharpe\"] for s in adaylar)\n"
                  "    return next(s for s in adaylar if s[\"is\"][\"sharpe\"] >= en - SECIM_TOLERANS)\n",
                  "    return max(adaylar, key=lambda s: s[\"is\"][\"sharpe\"])\n")],
    },
    {
        "ad": "ay_sonu",
        "commit": "2c01d199",
        "birimler": None,
        "yama": [("gunluk.py",
                  "    ay_sonu = np.array([z.londra_ay_sonu(t.date()) for t in tarihler], dtype=bool)\n",
                  "    ay = gun.astype(\"datetime64[M]\")\n"
                  "    ay_sonu = np.zeros(len(gun), dtype=bool)\n"
                  "    ay_sonu[:-1] = ay[1:] != ay[:-1]\n"
                  "    ay_sonu[-1] = False         # pencerenin son günü ayın sonu olup olmadığı bilinmez\n")],
    },
    {
        "ad": "stop_yeri",
        "commit": "09ec1758 · 4d5fa720",
        "birimler": ("fiks_donus", "fiks_momentum", "momentum"),
        "yama": [("strateji.py",
                  "        if s < 0 or e < 0 or e <= s:\n"
                  "            continue\n",
                  "        if s < 0 or e < 0 or e <= s or not np.isfinite(atr[s]):\n"
                  "            continue\n"),
                 ("strateji.py",
                  "        a = atr[e - 1]\n"
                  "        if not np.isfinite(a) or a <= 0:\n"
                  "            continue\n",
                  "        a = atr[s]\n"),
                 ("strateji.py",
                  "        gi = int(m.i0[e])\n"
                  "        satir.append((k, s, yon, np.nan, abs(hareket), m.h[s], m.l[s], a,\n"
                  "                      gi, int(cik[k]), bool(g.ay_sonu[k])))\n",
                  "        satir.append((k, s, yon, m.c[s] - yon * a, abs(hareket), m.h[s], m.l[s], a,\n"
                  "                      int(m.i0[e]), int(cik[k]), bool(g.ay_sonu[k])))\n"),
                 ("strateji.py",
                  "        satir.append((k, s, yon, np.nan, abs(hareket), m.h[s], m.l[s], r,\n"
                  "                      int(gir[k]), int(cik[k]), hareket))\n",
                  "        satir.append((k, s, yon, d.mo[gir[k]] - yon * r, abs(hareket), m.h[s], m.l[s], r,\n"
                  "                      int(gir[k]), int(cik[k]), hareket))\n")],
    },
    {
        "ad": "devam_kirpma",
        "commit": "4d5fa720",
        "birimler": (),
        "haber_analizi": True,      # yalnız haber analizi koşar (kosu.py --yalniz-haber); kıyas devam tablosuyla
        "yama": [("strat_haber.py",
                  "        if ci > gun_sonu:\n"
                  "            kirpilan[c[\"olay\"]] = kirpilan.get(c[\"olay\"], 0) + 1\n"
                  "            continue\n",
                  "        ci = min(ci, int(gun_sonu))\n")],
    },
    {
        # Büyük olay günü koşul değişkeni: önceden duyurulmayan karar günü olay saatinden ÖNCE işaretliyordu. İşlemler
        # değişmez (haber penceresinin maliyeti bu ayrımı yapmaz); değişen koşul kovaları ve onların hükmüdür.
        "ad": "haber_gunu_olaganustu",
        "commit": "dda21888",
        "birimler": None,
        "yama": [("gunluk.py",
                  "        bilinen = _gun_basinda_bilinen(olaylar, t0, j, g.gun_basi)\n"
                  "        haber_gun[j[(j >= 0) & bilinen]] = True\n",
                  "        haber_gun[j[j >= 0]] = True\n")],
    },
    {
        "ad": "haber_tek_pozisyon",
        "commit": "4d5fa720",
        "birimler": HABER_BIRIM,
        "yama": [("strat_haber.py",
                  "                  zaman_mum, tek_pozisyon=False)\n",
                  "                  zaman_mum)\n"),
                 ("strat_haber.py",
                  "    out = tek_pozisyon_uygula(pd.concat(parcalar, ignore_index=True))\n",
                  "    out = pd.concat(parcalar, ignore_index=True)\n")],
    },
)


# ───────────────────────────────────────────── özler
def _oz_dosyalar(yollar) -> str:
    """Dosyaların özü; TOML dosyaları ayrıştırılmış içerikleriyle (yorum satırları koşuyu değiştirmez)."""
    h = hashlib.sha256()
    for p in sorted(yollar, key=lambda x: x.relative_to(BURASI).as_posix()):
        h.update(p.relative_to(BURASI).as_posix().encode())
        h.update(b"\0")
        if p.suffix == ".toml":
            h.update(json.dumps(tomllib.loads(p.read_text(encoding="utf-8")), sort_keys=True, ensure_ascii=False,
                                default=str).encode())
        else:
            h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def kosu_modulleri() -> list[Path]:
    """kosu'nun (ve onun çağırdığı haber analizi ile takvimin) içe aktardığı proje modülleri — ayrı bir süreçte,
    gerçekten içe aktarılarak bulunur; elle tutulan bir liste yarın eklenecek modülü sessizce dışarıda bırakırdı."""
    betik = ("import sys, json; sys.path.insert(0, '.'); import kosu, haber_analiz, takvim, veri, gunluk; "
             "from pathlib import Path; b = Path('.').resolve(); "
             "print(json.dumps(sorted({Path(m.__file__).name for m in list(sys.modules.values()) "
             "if getattr(m, '__file__', None) and Path(m.__file__).resolve().parent == b})))")
    out = subprocess.run([PY, "-c", betik], cwd=BURASI, capture_output=True, text=True, check=True).stdout
    return [BURASI / ad for ad in json.loads(out.strip().splitlines()[-1])]


def kod_ozu() -> str:
    yollar = set(kosu_modulleri())
    yollar |= {BURASI / "karsi_olgu.py", BURASI / "ayar.toml", BURASI / "onkayit.toml"}
    yollar |= {p for p in (BURASI / "veri" / "takvim").glob("*.csv")}
    yollar |= set((BURASI / "veri" / "dukascopy" / "kunye").glob("*.json"))
    return _oz_dosyalar(yollar)


def taban_ozu(kok: Path = CIKTI) -> str:
    """Kıyaslanan koşu çıktılarının özü: birimlerin sonuç dosyaları ve haber analizinin devam tablosu."""
    yollar = [p for p in (kok / "sonuc").glob("*/*.json") if p.parent.name != "haber"]
    yollar.append(kok / "sonuc" / "haber" / "devam.json")
    h = hashlib.sha256()
    for p in sorted(yollar, key=lambda x: x.relative_to(kok).as_posix()):
        h.update(p.relative_to(kok).as_posix().encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


# ───────────────────────────────────────────── kopya ve koşu
def yama_uygula(kopya: Path, yama: list[tuple[str, str, str]]) -> None:
    for dosya, bugun, eski in yama:
        yol = kopya / dosya
        metin = yol.read_text(encoding="utf-8")
        n = metin.count(bugun)
        if n != 1:
            raise SystemExit(f"karşı olgu yaması eskidi: {dosya} içinde bugünkü metin {n} kez geçiyor (1 beklenir):\n"
                             f"{bugun}")
        yol.write_text(metin.replace(bugun, eski), encoding="utf-8")


def yama_sina(yama: list[tuple[str, str, str]]) -> None:
    """Yamaların bugünkü kodda hâlâ tam bir kez geçtiği (kopya kurmadan; --oku yolu)."""
    for dosya, bugun, _ in yama:
        n = (BURASI / dosya).read_text(encoding="utf-8").count(bugun)
        if n != 1:
            raise SystemExit(f"karşı olgu yaması eskidi: {dosya} içinde bugünkü metin {n} kez geçiyor (1 beklenir)")


def kopya_kur(hedef: Path, yama: list) -> None:
    hedef.mkdir(parents=True)
    for p in BURASI.iterdir():
        if p.is_file() and p.suffix in (".py", ".toml", ".txt", ".ini"):
            shutil.copy2(p, hedef / p.name)
    (hedef / "veri").symlink_to(BURASI / "veri")
    yama_uygula(hedef, yama)


def _kos(kopya: Path, birimler, cift: str | None, gunluk: Path) -> float:
    t0 = time.monotonic()
    # cift None: yalnız haber analizi, dört parite tek süreçte (devam tablosu dört paritenin birleşimidir)
    arg = [PY, "kosu.py", "--yalniz-haber"] if cift is None else [PY, "kosu.py", *(birimler or []), cift]
    with gunluk.open("w") as f:
        r = subprocess.run(arg, cwd=kopya, stdout=f, stderr=subprocess.STDOUT,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode != 0:
        raise SystemExit(f"karşı olgu koşusu düştü ({kopya.name} · {cift}); kayıt: {gunluk}")
    return time.monotonic() - t0


# ───────────────────────────────────────────── kıyas
def _yukle(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _sayi(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else x


def _islem_imza(yol: Path) -> set | None:
    if not yol.exists():
        return None
    import pandas as pd
    x = pd.read_parquet(yol, columns=["durum", "giris_t", "cikis_t", "yon", "r"])
    x = x[x["durum"] == 0]
    return set(zip(x["giris_t"].astype("int64"), x["cikis_t"].astype("int64"), x["yon"].astype("int64"),
                   x["r"].round(9)))


def _dosya_adi(cift: str, p: dict) -> str:
    anahtar = "|".join(f"{k}={p[k]}" for k in sorted(p))
    return f"{cift}__" + anahtar.replace("|", "__").replace("=", "-").replace(":", "") + ".parquet"


def _kosul_hukum(a: dict | None) -> dict:
    return {k["degisken"]: k.get("hukum") for k in ((a or {}).get("kosul") or [])}


def bilesim_kiyas(birim: str, cift: str, taban: Path, ko: Path) -> dict | None:
    a, b = _yukle(taban / "sonuc" / birim / f"{cift}.json"), _yukle(ko / "sonuc" / birim / f"{cift}.json")
    if a is None or b is None:
        return None
    out = {"birim": birim, "cift": cift}
    for ad in ("varsayilan", "secilen"):
        x, y = a.get(f"{ad}_analiz") or {}, b.get(f"{ad}_analiz") or {}
        kx, ky = _kosul_hukum(x), _kosul_hukum(y)
        out[ad] = {
            "p_ayni": a.get(ad) == b.get(ad),
            "hukum": [x.get("hukum"), y.get("hukum")],
            "hukum_tum": [x.get("hukum_tum"), y.get("hukum_tum")],
            "maliyet": [x.get("maliyet_yiyor"), y.get("maliyet_yiyor")],
            "maliyet_oos": [x.get("maliyet_yiyor_oos"), y.get("maliyet_yiyor_oos")],
            "oos_r": [_sayi((x.get("oos") or {}).get("beklenti_r")), _sayi((y.get("oos") or {}).get("beklenti_r"))],
            "oos_n": [(x.get("oos") or {}).get("n"), (y.get("oos") or {}).get("n")],
            "tum_r": [_sayi((x.get("tum") or {}).get("beklenti_r")), _sayi((y.get("tum") or {}).get("beklenti_r"))],
            "tum_n": [(x.get("tum") or {}).get("n"), (y.get("tum") or {}).get("n")],
            "kosul_degisen": sorted(d for d in set(kx) | set(ky) if kx.get(d) != ky.get(d)),
            "kosul_tuttu": [sum(1 for v in kx.values() if v == "tuttu"), sum(1 for v in ky.values() if v == "tuttu")],
        }
    # İşlem düzeyi (varsayılan): aynı kombinasyonun alınan işlemleri giriş, çıkış, yön ve R ile.
    p = a.get("varsayilan")
    ix, iy = (_islem_imza(taban / "islem" / birim / _dosya_adi(cift, p)),
              _islem_imza(ko / "islem" / birim / _dosya_adi(cift, p)))
    if ix is not None and iy is not None:
        ortak = len(ix & iy)
        out["islem"] = {"bugun": len(ix), "eski": len(iy), "ortak": ortak,
                        "degisen": (len(ix) - ortak) + (len(iy) - ortak)}
    return out


def devam_kiyas(taban: Path, ko: Path) -> dict:
    """Devam tablosu: hücre hücre (boyut, değer, tf, ufuk) olay sayısı, hüküm ve iki ortalama."""
    a, b = _yukle(taban / "sonuc" / "haber" / "devam.json"), _yukle(ko / "sonuc" / "haber" / "devam.json")
    if a is None or b is None:
        raise SystemExit("karşı olgu: devam tablosu bulunamadı")
    def anahtar(h):
        return (h["boyut"], h["deger"], h["tf"], h["ufuk"])
    ha, hb = {anahtar(h): h for h in a["hucre"]}, {anahtar(h): h for h in b["hucre"]}
    ortak = sorted(set(ha) & set(hb))
    def fark(alan, yan):
        d = [abs(ha[k][yan][alan] - hb[k][yan][alan]) for k in ortak
             if ha[k][yan].get(alan) is not None and hb[k][yan].get(alan) is not None]
        return max(d) if d else None
    n_deg = [k for k in ortak if ha[k]["n_olay"] != hb[k]["n_olay"]]
    h_deg = [{"boyut": k[0], "deger": k[1], "tf": k[2], "ufuk": k[3], "bugun": ha[k]["hukum"], "eski": hb[k]["hukum"]}
             for k in ortak if ha[k]["hukum"] != hb[k]["hukum"]]
    return {"hucre": len(ortak), "yalniz_bugun": len(set(ha) - set(hb)), "yalniz_eski": len(set(hb) - set(ha)),
            "n_degisen": len(n_deg),
            "olay_bugun": sum(ha[k]["n_olay"] for k in n_deg), "olay_eski": sum(hb[k]["n_olay"] for k in n_deg),
            "hukum_degisen": h_deg, "hukum_sayim": {"bugun": a.get("hukum_sayimi"), "eski": b.get("hukum_sayimi")},
            "kir_azami_fark": fark("ort_atr_yuzde", "kir"), "fad_azami_fark": fark("ort_atr_yuzde", "fad"),
            "degisen_hucre": [{"boyut": k[0], "deger": k[1], "tf": k[2], "ufuk": k[3], "n_bugun": ha[k]["n_olay"],
                               "n_eski": hb[k]["n_olay"]} for k in n_deg]}


def ozetle(satirlar: list[dict]) -> dict:
    def fark(k, ad):
        return [s for s in satirlar if s[ad][k][0] != s[ad][k][1]]

    def r_fark(ad, k="oos_r"):
        d = [abs(s[ad][k][0] - s[ad][k][1]) for s in satirlar
             if s[ad][k][0] is not None and s[ad][k][1] is not None]
        oynayan = [x for x in d if x > 5e-7]
        return {"n": len(d), "oynayan": len(oynayan), "azami": max(d) if d else None}

    out = {"bilesim": len(satirlar)}
    for ad in ("varsayilan", "secilen"):
        out[ad] = {
            "p_degisen": [f"{s['birim']}|{s['cift']}" for s in satirlar if not s[ad]["p_ayni"]],
            "hukum_degisen": [{"birim": s["birim"], "cift": s["cift"], "bugun": s[ad]["hukum"][0],
                               "eski": s[ad]["hukum"][1]} for s in fark("hukum", ad)],
            "hukum_tum_degisen": [{"birim": s["birim"], "cift": s["cift"], "bugun": s[ad]["hukum_tum"][0],
                                   "eski": s[ad]["hukum_tum"][1]} for s in fark("hukum_tum", ad)],
            "maliyet_degisen": len(fark("maliyet", ad)), "maliyet_oos_degisen": len(fark("maliyet_oos", ad)),
            "oos_r": r_fark(ad), "tum_r": r_fark(ad, "tum_r"),
            "oos_n_degisen": len(fark("oos_n", ad)),
            "kosul_degisen": sum(len(s[ad]["kosul_degisen"]) for s in satirlar),
            "kosul_tuttu": [sum(s[ad]["kosul_tuttu"][0] for s in satirlar),
                            sum(s[ad]["kosul_tuttu"][1] for s in satirlar)],
        }
        sayim = {}
        for s in satirlar:
            for i, kim in ((0, "bugun"), (1, "eski")):
                h = s[ad]["hukum"][i] or "secim_yok"      # seçilende: ızgaradan seçim yapılamadı
                sayim.setdefault(kim, {})[h] = sayim.setdefault(kim, {}).get(h, 0) + 1
        out[ad]["hukum_sayim"] = sayim
    isl = [s["islem"] for s in satirlar if "islem" in s]
    out["islem"] = {"bilesim": len(isl), "bugun": sum(x["bugun"] for x in isl), "eski": sum(x["eski"] for x in isl),
                    "degisen": sum(x["degisen"] for x in isl),
                    "degisen_bilesim": sum(1 for x in isl if x["degisen"] > 0)}
    return out


# ───────────────────────────────────────────── ana akış
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paralel", type=int, default=max(1, min(4, (os.cpu_count() or 2))))
    ap.add_argument("--zorla", action="store_true")
    ap.add_argument("--yalniz", nargs="*", default=None, help="yalnız bu değişiklikler (ad)")
    ap.add_argument("--oku", default=None, help="koşulmuş kopyaları bu geçici dizinden oku (yeniden koşma)")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(BURASI))
    import kosu  # noqa: E402  (birim listesi ve işlem dosyası adı bugünkü koddan)
    k_oz = kod_ozu()
    eski = _yukle(SONUC)
    if (eski and not a.zorla and a.yalniz is None and a.oku is None and eski.get("kod_ozu") == k_oz
            and eski.get("taban_ozu") == taban_ozu(CIKTI)):
        print(f"karşı olgu güncel (kod {k_oz[:12]} · taban bugünkü koşuyla aynı); koşulmadı")
        return 0
    secilen = [d for d in DEGISIKLIKLER if a.yalniz is None or d["ad"] in a.yalniz]
    stratejiler = [b for b in kosu.BIRIMLER]
    gecici = Path(a.oku) if a.oku else Path(tempfile.mkdtemp(prefix="karsi_olgu_"))
    isler = []
    basarili = False
    try:
        # Taban: yamasız kopya, bütün birimler ve haber analizi — kıyasın öbür tarafı aynı koddan çıkar.
        taban = gecici / "taban" / "FxGunici"
        t0 = time.monotonic()
        if a.oku:
            # Koşulmuş kopyalar yeniden koşulmaz; yamaların bugünkü koda hâlâ uyduğu yine sınanır.
            for d in secilen:
                yama_sina(d["yama"])
            print(f"karşı olgu: koşulmuş kopyalar okunuyor ({gecici})", flush=True)
        else:
            kopya_kur(taban, [])
            tb = {"ad": "taban"}
            isler += [(tb, taban, stratejiler, c) for c in CIFTLER] + [(tb, taban, [], None)]
            for d in secilen:
                kopya = gecici / d["ad"] / "FxGunici"
                kopya_kur(kopya, d["yama"])
                if d.get("haber_analizi"):
                    isler.append((d, kopya, [], None))
                    continue
                birimler = list(d["birimler"]) if d["birimler"] else stratejiler
                for cift in CIFTLER:
                    isler.append((d, kopya, birimler, cift))
            print(f"karşı olgu: {len(secilen)} değişiklik, {len(isler)} koşu, {a.paralel} paralel", flush=True)

            def is_(x):
                d, kopya, birimler, cift = x
                sn = _kos(kopya, birimler, cift, gecici / f"{d['ad']}_{cift or 'haber'}.log")
                print(f"  {d['ad']:20s} {cift or 'haber analizi'} · {sn:.0f} sn", flush=True)
                return sn

            with ThreadPoolExecutor(max_workers=a.paralel) as ex:
                list(ex.map(is_, isler))
        taban_cikti = taban / "cikti"
        t_oz = taban_ozu(taban_cikti)
        sonuc = {"kod_ozu": k_oz, "taban_ozu": t_oz, "degisiklik": {}}
        if eski and a.yalniz is not None and eski.get("kod_ozu") == k_oz and eski.get("taban_ozu") == t_oz:
            sonuc["degisiklik"].update({k: v for k, v in (eski.get("degisiklik") or {}).items()
                                        if k not in {d["ad"] for d in secilen}})
        for d in secilen:
            kopya = gecici / d["ad"] / "FxGunici"
            if d.get("haber_analizi"):
                sonuc["degisiklik"][d["ad"]] = {"commit": d["commit"],
                                                "devam": devam_kiyas(taban_cikti, kopya / "cikti")}
                continue
            birimler = list(d["birimler"]) if d["birimler"] else stratejiler
            satirlar = [s for b in birimler for c in CIFTLER
                        if (s := bilesim_kiyas(b, c, taban_cikti, kopya / "cikti")) is not None]
            if len(satirlar) != len(birimler) * len(CIFTLER):
                raise SystemExit(f"karşı olgu eksik: {d['ad']} {len(satirlar)}/{len(birimler) * len(CIFTLER)} bileşim")
            sonuc["degisiklik"][d["ad"]] = {"commit": d["commit"], "birimler": birimler, **ozetle(satirlar),
                                            "satir": satirlar}
        if kod_ozu() != k_oz:
            raise SystemExit("karşı olgu koşarken kod değişti; yeniden koşturun")
        SONUC.parent.mkdir(parents=True, exist_ok=True)
        SONUC.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        ayni = t_oz == taban_ozu(CIKTI)
        print(f"karşı olgu yazıldı: {SONUC.relative_to(BURASI)} · {time.monotonic() - t0:.0f} sn · bugünkü koşu "
              + ("tabanla aynı" if ayni else "TABANLA AYNI DEĞİL — kosu.py yeniden koşulmalı (ölçüm yazılmaz)"))
        basarili = True
    finally:
        if basarili:
            shutil.rmtree(gecici, ignore_errors=True)
        else:
            print(f"karşı olgu düştü; koşulmuş kopyalar korundu: {gecici} (yeniden okumak için --oku {gecici})",
                  file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
