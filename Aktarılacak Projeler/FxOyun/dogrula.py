#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX GÜN İÇİ OYUN PLANI — beş dersin kapısı (sayfa sınavı 26 kendiliğinden koşturur).

Yalnız standart kütüphane: yayın koşucusunda pandas ve plotly yok. Sorulanlar:

1. ÖZLER — ölçüm dosyası (veri/ders.json) girdilerinin ve kodun özünü taşır; özler yeniden hesaplanır. Sınama dosyası
   (sina.json) planın ve ön kaydın özünü, plan (plan.json) ön kaydın ve aday tablosunun özünü taşır: plan ön kayıttan
   sonra değişmişse ya da sınama başka bir planla koşmuşsa kapı düşer.
2. SEÇİM VE HÜKÜM — ön kaydın seçim kuralı aday tablosuna (gelistir.json) bu kapıda yeniden uygulanır ve plan.json ile
   kıyaslanır; hüküm kuralı her bacağın 2024 → sonucuna yeniden uygulanır ve kayıttaki hükümle kıyaslanır.
3. YENİDEN ÜRETİM — dersler şablondan yeniden üretilir ve yayımlanan MDX ile birebir kıyaslanır.
4. ŞABLON — şablonda elle yazılmış ondalıklı ya da yüzdeli sayı yoktur (sayılar ölçümden gelir).
5. FİGÜRLER — her dersin gömdüğü figürler sırasıyla ders_yaz.SEKIL ve sekil.SEKILLER'dekilerdir; dosya vardır,
   ölçüm dosyasının özünü taşır, başlığı "Şekil NN —" ile başlar ve telefonun gömme çerçevesine sığar.
6. SERİ — sitedeki ders grubu (fx-gunici) bu serinin sırasını taşır; her dersin durumu aktif, ön koşulları seride ve
   kendisinden önce.
7. İDDİALAR — metnin sayıya dayanan nitel hükümleri (devam dönüşten sık, yarı yarıya, iki dönem aynı yönde …) ölçüme
   karşı adıyla sınanır.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
sys.dont_write_bytecode = True

import ders_yaz as dy  # noqa: E402
import sekil_ortak as so  # noqa: E402

KOK = BURASI.parents[1]
VERI = BURASI / "veri"
GRUP_TS = KOK / "site" / "src" / "lib" / "dersGruplari.ts"
D = dy.DERS
ON = tomllib.loads((BURASI / "onkayit_oyun.toml").read_text(encoding="utf-8"))
HATA: list[str] = []
SAY = {"n": 0}


def dogru(kosul: bool, mesaj: str) -> None:
    SAY["n"] += 1
    if not kosul:
        HATA.append(mesaj)


def oz(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ─────────────────────────────────────────────────────────────── 1 · özler
def ozler() -> None:
    ku = D["kunye"]
    for ad, yol in (("gozlem", VERI / "gozlem.json"), ("sina", VERI / "sina.json"), ("plan", VERI / "plan.json"),
                    ("onkayit", BURASI / "onkayit_oyun.toml")):
        dogru(ku[ad] == oz(yol), f"ölçüm dosyası {yol.name} özünü taşımıyor (ders_olcum.py yeniden koşulmalı)")
    for dosya, h in ku["kod"].items():
        dogru(h == oz(BURASI / dosya), f"ölçüm dosyası {dosya} kodunun güncel özünü taşımıyor")
    S = json.loads((VERI / "sina.json").read_text(encoding="utf-8"))
    P = json.loads((VERI / "plan.json").read_text(encoding="utf-8"))
    dogru(S["plan_ozu"] == oz(VERI / "plan.json"), "sınama başka bir planla koşmuş (sina.json plan özü)")
    dogru(S["onkayit_ozu"] == oz(BURASI / "onkayit_oyun.toml"), "sınama başka bir ön kayıtla koşmuş")
    dogru(P["onkayit_ozu"] == oz(BURASI / "onkayit_oyun.toml"), "plan ön kayıttan sonra değişmiş (plan.json ön kayıt özü)")
    dogru(P["gelistir_ozu"] == oz(VERI / "gelistir.json"), "plan başka bir aday tablosundan seçilmiş")
    for dosya, h in S["kod_ozu"].items():
        dogru(h == oz(BURASI / dosya), f"sınama {dosya} kodunun güncel hâliyle koşmamış")
    dogru(D["bacak"] == S["bacak"], "ölçüm dosyasının bacakları sınama dosyasıyla aynı değil")
    dogru(D["plan"] == P, "ölçüm dosyasının planı plan.json ile aynı değil")


# ─────────────────────────────────────────────────────────────── 2 · seçim ve hüküm
def secim_ve_hukum() -> None:
    import secim
    g = json.loads((VERI / "gelistir.json").read_text(encoding="utf-8"))
    kural = ON["secim"]
    hucre: dict = {}
    for r in g["satir"]:
        if r["anahtar"] == "+".join(kural["duzey"] + ["bacak"]):
            hucre.setdefault((r["aile"], r["sinif"]), []).append(r)
    beklenen = {}
    for k, rs in hucre.items():
        uygun = [r for r in rs if r["n"] >= kural["en_az_islem"] and r["ort_R"] > 0]
        if uygun:
            beklenen[k] = secim.bacak_coz(max(uygun, key=lambda r: r["ort_R"])["bacak"])
    plan = {(x["aile"], x["sinif"]): x["bacak"] for x in D["plan"]["islem"]}
    dogru(plan == beklenen, f"plan, ön kaydın seçim kuralıyla yeniden kurulamıyor: {plan} ↔ {beklenen}")
    izle = {(x["aile"], x["sinif"]) for x in D["plan"]["izle"]}
    dogru(izle == set(hucre) - set(beklenen), "'izle' hücreleri seçim kuralının bıraktığı hücreler değil")
    h = ON["hukum"]
    for b in D["bacak"]:
        o = b["dis"]
        if o["n"] < h["en_az_islem"]:
            bek = "olculemedi"
        elif o.get("alt", -1) > 0:
            bek = "calisiyor"
        else:
            bek = "zayif" if o["ort_R"] > 0 else "calismiyor"
        dogru(b["hukum"] == bek, f"{b['bacak']}: hüküm {b['hukum']}, kuralın verdiği {bek}")


# ─────────────────────────────────────────────────────────────── 3–4 · yeniden üretim ve şablon
_YER = re.compile(r"\{\{.*?\}\}", re.S)
_ONDALIK = re.compile(r"\d+,\d+")


def uretim() -> None:
    cikti = dy.hepsi()
    for slug in dy.SIRA:
        yol = dy.CIKTI / f"{slug}.mdx"
        dogru(yol.exists() and yol.read_text(encoding="utf-8") == cikti[slug],
              f"{slug}.mdx şablondan yeniden üretilen metinle aynı değil (ders_yaz.py koşulmalı)")
        ham = _YER.sub("", (dy.METIN / f"{slug}.md").read_text(encoding="utf-8"))
        for m in _ONDALIK.finditer(ham):
            HATA.append(f"{slug}.md: elle yazılmış ondalıklı sayı: …{ham[max(0, m.start() - 30):m.end() + 10]}…")
        for m in re.finditer("%", ham):
            HATA.append(f"{slug}.md: elle yazılmış yüzde: …{ham[max(0, m.start() - 30):m.end() + 10]}…")
        SAY["n"] += 2


# ─────────────────────────────────────────────────────────────── 5 · figürler
_GOMME = re.compile(r'<GrafikEmbed src="/arastirma/([^/"]+)/([^"]+)\.html" baslik="[^"]*" no="(\d\d)"')
_BASLIK = re.compile(r'"text":"((?:\\u015e|Ş)ekil (?:[^"\\]|\\.)*)"')   # figür başlığı (alt yazılar ayrı alanda)


def figurler() -> None:
    import ast
    agac = ast.parse((BURASI / "sekil.py").read_text(encoding="utf-8"))
    sekiller = next(ast.literal_eval(n.value) for n in agac.body
                    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SEKILLER")
    dogru(sekiller == dy.SEKIL, "sekil.SEKILLER ile ders_yaz.SEKIL ayrışıyor")
    olcum = oz(so.OLCUM)
    for slug in dy.SIRA:
        mdx = (dy.CIKTI / f"{slug}.mdx").read_text(encoding="utf-8")
        gom = _GOMME.findall(mdx)
        dogru([a for _, a, _ in gom] == dy.SEKIL[slug], f"{slug}: gömülen figürler {[a for _, a, _ in gom]} ↔ {dy.SEKIL[slug]}")
        for s, ad, no in gom:
            dogru(s == slug and ad[:2] == no, f"{slug}: gömme {s}/{ad} numarası {no} ile uyuşmuyor")
            yol = so.CIKTI_KOK / slug / f"{ad}.html"
            if not yol.exists():
                HATA.append(f"{slug}: figür yok: {yol.relative_to(KOK)}")
                continue
            html = yol.read_text(encoding="utf-8")
            dogru(f'name="tto-olcum-ozu" content="{olcum}"' in html,
                  f"{slug}/{ad}: figür güncel ölçüm dosyasından çizilmemiş (sekil.py koşulmalı)")
            m = _BASLIK.search(html)
            baslik = json.loads(f'"{m.group(1)}"') if m else ""
            dogru(baslik.startswith(f"Şekil {no} —"), f"{slug}/{ad}: başlık 'Şekil {no} —' ile başlamıyor")
            tasan = so.tasan_satirlar(baslik)
            dogru(not tasan, f"{slug}/{ad}: başlık telefonda taşıyor: {tasan}")


# ─────────────────────────────────────────────────────────────── 6 · seri
def seri() -> None:
    ts = GRUP_TS.read_text(encoding="utf-8")
    m = re.search(r"id:\s*'fx-gunici'.*?slugSirasi:\s*\[(.*?)\]", ts, flags=re.S)
    dogru(bool(m) and re.findall(r"'([^']+)'", m.group(1)) == dy.SIRA,
          "sitedeki 'fx-gunici' ders grubu bu serinin sırasını taşımıyor")
    for slug in dy.SIRA:
        sab = (dy.METIN / f"{slug}.md").read_text(encoding="utf-8")
        d = re.search(r"^durum:\s*'(\w+)'", sab, flags=re.M)
        dogru(bool(d) and d.group(1) == "aktif", f"{slug}: durum aktif değil")
        on = re.search(r"^onkosul:\s*\[(.*?)\]", sab, flags=re.M)
        for o in (re.findall(r"'([^']+)'", on.group(1)) if on else []):
            dogru(o in dy.SIRA and dy.SIRA.index(o) < dy.SIRA.index(slug), f"{slug}: ön koşul {o} seride önce değil")


# ─────────────────────────────────────────────────────────────── 7 · iddialar
def iddialar() -> None:
    A, Dv, K, F, T = D["aile_davranis"], D["davranis"], D["kucuk"], D["fiksing_ay_sonu"], D["trend"]
    B = {(b["rol"], b["aile"], b["sinif"]): b for b in D["bacak"]}
    iki = ("ic", "dis")
    # okuma ve açılışlar
    for dn in iki:
        dogru(A[dn]["acilis"]["normal"]["orta"] > 0.85, f"{dn}: normal açılış mumunun yarısına dönüşü 'neredeyse her zaman' değil")
        dogru(A[dn]["acilis"]["guclu"]["devam"] > A[dn]["acilis"]["guclu"]["donus"], f"{dn}: güçlü açılış mumu dönüşten sık devam etmiyor")
        for s in ("normal", "reddedilen"):
            dogru(abs(A[dn]["acilis"][s]["devam"] - A[dn]["acilis"][s]["donus"]) < 0.05, f"{dn}: açılış {s} mumunda devam ile dönüş yarı yarıya değil")
        for s in ("guclu", "normal", "reddedilen"):
            uo = A[dn]["acilis"][s]["orta_uc"] / A[dn]["acilis"][s]["orta"]
            dogru(0.4 < uo < 0.55, f"{dn}: açılış {s}: yarısına dönen mumun kendi ucuna gitmesi yarı yarıya değil ({uo:.2f})")
        for a in ("tokyo_acilis", "londra_acilis", "ny_acilis"):
            dogru(0.4 < K[dn][a]["kirilim_1R"] < 0.6, f"{dn}: {a} küçük mum kırılımı yarı yarıya değil")
    for s in ("guclu", "normal", "reddedilen"):
        dogru(abs(T["acilis"][s]["trendle"]["devam"] - T["acilis"][s]["karsi"]["devam"]) < 0.05, f"açılış {s}: trend devamı değiştiriyor")
        dogru(abs(T["fiksing"][s]["trendle"]["devam"] - T["fiksing"][s]["karsi"]["devam"]) < 0.05, f"fiksing {s}: trend devamı değiştiriyor")
    # fiksingler
    for dn in iki:
        g = A[dn]["fiksing"]["guclu"]
        dogru(g["orta"] > 0.5 and g["donus"] < g["devam"] < g["orta"], f"{dn}: güçlü fiksing koşusu 'geri verilir ama dönmez' değil")
        dogru(K[dn]["wmr"]["kirilim_1R"] < 0.35 and K[dn]["tokyo_fiks"]["kirilim_1R"] > K[dn]["wmr"]["kirilim_1R"],
              f"{dn}: sessiz Londra fiksinginden sonraki kırılım 'çoğu zaman bir yere gitmiyor' değil ya da Tokyo'dan yüksek")
        dogru(F["wmr"][dn]["ay_sonu"]["guclu"]["devam"] < F["wmr"][dn]["diger"]["guclu"]["devam"],
              f"{dn}: ay sonunda Londra fiksingine güçlü koşu öbür günlerden az devam etmiyor")
    o_ic = F["wmr"]["ic"]["ay_sonu"]["guclu"]["orta"] - F["wmr"]["ic"]["diger"]["guclu"]["orta"]
    o_dis = F["wmr"]["dis"]["ay_sonu"]["guclu"]["orta"] - F["wmr"]["dis"]["diger"]["guclu"]["orta"]
    dogru(o_ic * o_dis < 0, "metin ay sonu geri verme farkını 'iki dönemde farklı' diyor; iki dönemde aynı yöne bakıyor")
    t_ic = F["tokyo_fiks"]["ic"]["ay_sonu"]["normal"]["donus"] - F["tokyo_fiks"]["ic"]["diger"]["normal"]["donus"]
    t_dis = F["tokyo_fiks"]["dis"]["ay_sonu"]["normal"]["donus"] - F["tokyo_fiks"]["dis"]["diger"]["normal"]["donus"]
    dogru(abs(t_ic) < 0.05 < t_dis, "Tokyo ay sonu farkı 'iki dönemde aynı yöne bakmıyor' değil")
    # haberler
    for m in ("devam",):
        for s in ("guclu", "normal"):
            dogru(A["dis"]["veri"][s][m] < A["ic"]["veri"][s][m] - 0.1, f"ABD verisi {s}: devam payı 2024 sonrasında belirgin düşmedi")
    dogru(A["dis"]["veri"]["guclu"]["donus"] < A["ic"]["veri"]["guclu"]["donus"], "ABD verisi güçlü: dönüş payı düşmedi")
    dogru(A["ic"]["veri"]["guclu"]["devam"] > A["ic"]["veri"]["guclu"]["donus"], "ABD verisi güçlü 2018–2023: devam dönüşten sık değil")
    dogru(A["dis"]["mb"]["guclu"]["donus"] == 0, "güçlü karar mumunda 2024 sonrasında tersine dönen var")
    for dn in iki:
        dogru(A[dn]["mb"]["reddedilen"]["devam"] > A[dn]["mb"]["reddedilen"]["donus"], f"{dn}: reddedilen karar mumu devamı dönüşten sık değil")
        dogru(K[dn]["fomc"]["kirilim_1R"] > 0.5, f"{dn}: Fed küçük mum kırılımı 'çoğu zaman yol aldı' değil")
    dogru(K["dis"]["cpi"]["kirilim_1R"] < K["ic"]["cpi"]["kirilim_1R"], "TÜFE küçük mum kırılımı 2024 sonrasında düşmedi")
    # bacaklar
    sik = [b for b in D["bacak"] if b["rol"] == "referans" and b["aile"] in ("acilis", "fiksing")]
    dogru(all(b["hukum"] == "calismiyor" and b["dis"]["ust"] < 0 for b in sik), "sık anların referans tepkilerinden biri çalışmıyor değil ya da aralığı sıfırı kapsıyor")
    dogru(sum(b["dis"]["kazanma"] > 0.5 for b in sik) > len(sik) / 2, "sık anların tepkilerinin çoğunda kazanma oranı yarının üstünde değil")
    for s in ("guclu", "normal", "reddedilen"):
        dogru(B[("referans", "acilis", s)]["dis"]["brut_R"] < 0, f"açılış {s}: maliyetsiz sonuç eksi değil")
    for a in ("acilis", "fiksing"):
        b = B[("referans", a, "kucuk")]["dis"]
        dogru(b["brut_R"] > 0 > b["ort_R"] and b["brut_R"] - b["ort_R"] > b["brut_R"], f"{a} küçük: maliyet maliyetsiz kenardan büyük değil")
    dogru(abs(B[("referans", "fiksing", "guclu")]["dis"]["brut_R"]) < 0.1, "güçlü fiksing tepkisinin maliyetsiz sonucu sıfıra yakın değil")
    izle = {(x["aile"], x["sinif"]) for x in D["plan"]["izle"]}
    dogru({(a, s) for a in ("acilis", "fiksing") for s in ("guclu", "normal", "reddedilen", "kucuk")} <= izle,
          "açılış ve fiksinglerin bütün hücreleri 'izle' değil")
    mg = B[("islem", "mb", "guclu")]
    dogru(D["dagilim"][mg["bacak"]]["dis"]["neden"].get("stop", 0) == 0, "güçlü karar mumu tepkisinde stopta biten işlem var")
    dogru(abs(mg["ic"]["ort_R"]) < 0.05, "güçlü karar mumu tepkisinin 2018–2023 sonucu sıfıra yakın değil")
    dogru(mg["ic"]["ort_R"] > 0 and mg["dis"]["ort_R"] > 0 and B[("islem", "mb", "normal")]["ic"]["ort_R"] > 0
          and B[("islem", "mb", "normal")]["dis"]["ort_R"] > 0, "merkez bankası tepkileri iki dönemde de artı değil")
    vg = B[("islem", "veri", "guclu")]
    dogru(vg["ic"]["ort_R"] > 0 > vg["dis"]["ort_R"], "güçlü veri mumu: 2018–2023 artı, 2024 → eksi değil")
    mk = B[("referans", "mb", "kucuk")]
    dogru(mk["ic"]["ort_R"] < 0 < mk["dis"]["ort_R"], "küçük karar mumu kırılımı iki dönemde ayrı işaret vermiyor")
    for k in (("referans", "mb", "normal"), ("referans", "mb", "kucuk")):
        o = B[k]["dis"]
        dogru(o["ort_R"] > 0 and o["alt"] <= 0 < o["ust"], f"{k}: 2024 → artı ve aralığı sıfırı kapsıyor değil")
    dogru(not any(b["hukum"] == "calisiyor" for b in D["bacak"]), "bir tepki 'çalışıyor' hükmü almış; metin hiçbirinin almadığını söylüyor")


def main() -> int:
    for f in (ozler, secim_ve_hukum, uretim, figurler, seri, iddialar):
        try:
            f()
        except Exception as e:                       # kapının kendisi düşerse de adıyla düşer
            HATA.append(f"{f.__name__} koşamadı: {type(e).__name__}: {e}")
    if HATA:
        print("✗ FX oyun planı: " + "\n  ".join(HATA))
        return 1
    print(f"✓ FX oyun planı: {SAY['n']} ölçüt geçti (özler, seçim ve hüküm, yeniden üretim, şablon, figürler, seri, iddialar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
