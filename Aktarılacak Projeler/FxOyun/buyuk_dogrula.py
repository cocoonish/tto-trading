#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BÜYÜK MUM — dört dersin kapısı (dogrula.py çağırır; sayfa sınavı 26 kendiliğinden koşturur).

Yalnız standart kütüphane. Sorulanlar:

1. ÖZLER — ölçüm dosyası (veri/buyuk_ders.json) girdilerinin, ön kaydın ve kodun özünü taşır; sınama dosyası planın,
   ön kaydın ve kodun, plan ön kaydın ve aday tablosunun özünü taşır.
2. SEÇİM VE HÜKÜM — ön kaydın seçim kuralı aday tablosuna (buyuk_gelistir.json) burada yeniden uygulanır ve planla
   kıyaslanır; hüküm kuralı her girişin 2024 → sonucuna yeniden uygulanır; 2018–2023 satırları aday tablosuyla aynıdır.
3. YENİDEN ÜRETİM VE ŞABLON — dersler şablondan yeniden üretilip yayımlanan MDX ile birebir kıyaslanır; şablonda elle
   yazılmış ondalıklı ya da yüzdeli sayı yoktur.
4. FİGÜRLER — gömülen figürler buyuk_ders_yaz.SEKIL ve buyuk_sekil.SEKILLER'dekilerdir; dosya vardır, ölçüm dosyasının
   özünü taşır, başlığı "Şekil NN —" ile başlar ve telefonun gömme çerçevesine sığar.
5. İDDİALAR — metnin sayıya dayanan nitel hükümleri ölçüme karşı adıyla sınanır.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"


def oz(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kos(dogru, HATA: list[str], SAY: dict) -> None:
    import buyuk_ders_yaz as by
    import sekil_ortak as so
    D = by.D
    ON = tomllib.loads((BURASI / "onkayit_buyuk.toml").read_text(encoding="utf-8"))
    S = json.loads((VERI / "buyuk_sina.json").read_text(encoding="utf-8"))
    P = json.loads((VERI / "buyuk_plan.json").read_text(encoding="utf-8"))
    G = json.loads((VERI / "buyuk_gelistir.json").read_text(encoding="utf-8"))

    # ── 1 · özler
    ku = D["kunye"]
    for ad, h in ku["girdi"].items():
        dogru(h == oz(VERI / ad), f"büyük mum: ölçüm dosyası {ad} özünü taşımıyor (buyuk_ders_olcum.py yeniden koşulmalı)")
    dogru(ku["onkayit"] == oz(BURASI / "onkayit_buyuk.toml"), "büyük mum: ölçüm dosyası ön kaydın özünü taşımıyor")
    for dosya, h in ku["kod"].items():
        dogru(h == oz(BURASI / dosya), f"büyük mum: ölçüm dosyası {dosya} kodunun güncel özünü taşımıyor")
    dogru(S["plan_ozu"] == oz(VERI / "buyuk_plan.json"), "büyük mum: sınama başka bir planla koşmuş")
    dogru(S["onkayit_ozu"] == oz(BURASI / "onkayit_buyuk.toml"), "büyük mum: sınama başka bir ön kayıtla koşmuş")
    dogru(P["onkayit_ozu"] == oz(BURASI / "onkayit_buyuk.toml"), "büyük mum: plan ön kayıttan sonra değişmiş")
    dogru(P["gelistir_ozu"] == oz(VERI / "buyuk_gelistir.json"), "büyük mum: plan başka bir aday tablosundan seçilmiş")
    for dosya, h in S["kod_ozu"].items():
        dogru(h == oz(BURASI / dosya), f"büyük mum: sınama {dosya} kodunun güncel hâliyle koşmamış")
    dogru(D["bacak"] == S["bacak"] and D["plan"] == P, "büyük mum: ölçüm dosyasının plan ve girişleri kaynaklarıyla aynı değil")

    # ── 2 · seçim ve hüküm
    k = ON["secim"]
    adaylar = [{**r, "suzgec": None, "deger": None} for r in G["hucre"]] + G["suzgec"]
    beklenen = {}
    for tf in ON["tanim"]["dilimler"]:
        for yon in ("devam", "ters"):
            rs = [r for r in adaylar if r["tf"] == tf and r["giris"].startswith(yon + ":")]
            uygun = [r for r in rs if r["n"] >= k["en_az_islem"] and r["ort_R"] > 0
                     and (r.get("y1_R") or 0) > 0 and (r.get("y2_R") or 0) > 0]
            if uygun:
                en = max(uygun, key=lambda r: r["ort_R"])
                beklenen[(tf, yon)] = (en["giris"], en["suzgec"], en["deger"])
    plan = {(x["tf"], x["yon"]): (x["giris"], x["suzgec"], x["deger"]) for x in P["islem"]}
    dogru(plan == beklenen, f"büyük mum: plan seçim kuralıyla yeniden kurulamıyor: {plan} ↔ {beklenen}")
    dogru(P["aday_toplam"] == sum(1 for r in adaylar), "büyük mum: aday sayısı aday tablosuyla tutmuyor")
    dogru([(x["tf"], x["giris"]) for x in P["referans"]] ==
          [(tf, r["giris"]) for tf in ON["tanim"]["dilimler"] for r in ON["referans"]], "büyük mum: referans girişler ön kayıttakiler değil")
    h = ON["hukum"]
    for b in S["bacak"]:
        o = b["dis"]
        bek = ("olculemedi" if o["n"] < h["en_az_islem"] else "calisiyor" if (o.get("alt") or -1) > 0
               else "zayif" if o["ort_R"] > 0 else "calismiyor")
        dogru(b["hukum"] == bek, f"büyük mum: {b['bacak']}: hüküm {b['hukum']}, kuralın verdiği {bek}")
        if b["rol"] == "islem":
            src = next((r for r in adaylar if r["tf"] == b["tf"] and r["giris"] == b["giris"]
                        and r["suzgec"] == b["suzgec"] and r["deger"] == b["deger"]), None)
            dogru(src is not None and src["n"] == b["ic"]["n"] and abs(src["ort_R"] - b["ic"]["ort_R"]) < 1e-9,
                  f"büyük mum: {b['bacak']}: sınamanın 2018–2023 satırı aday tablosuyla aynı değil")
        else:
            src = next(r for r in G["hucre"] if r["tf"] == b["tf"] and r["giris"] == b["giris"])
            dogru(src["n"] == b["ic"]["n"] and abs(src["ort_R"] - b["ic"]["ort_R"]) < 1e-9,
                  f"büyük mum: {b['bacak']}: referansın 2018–2023 satırı aday tablosuyla aynı değil")

    # ── 3 · yeniden üretim ve şablon
    cikti = by.hepsi()
    for slug in by.SIRA:
        yol = by.CIKTI / f"{slug}.mdx"
        dogru(yol.exists() and yol.read_text(encoding="utf-8") == cikti[slug],
              f"{slug}.mdx şablondan yeniden üretilen metinle aynı değil (buyuk_ders_yaz.py koşulmalı)")
        ham = re.sub(r"\{\{.*?\}\}", "", (by.METIN / f"{slug}.md").read_text(encoding="utf-8"), flags=re.S)
        for m in re.finditer(r"\d+,\d+|%", ham):
            HATA.append(f"{slug}.md: elle yazılmış sayı: …{ham[max(0, m.start() - 30):m.end() + 10]}…")
        SAY["n"] += 2

    # ── 4 · figürler
    agac = ast.parse((BURASI / "buyuk_sekil.py").read_text(encoding="utf-8"))
    sekiller = next(ast.literal_eval(n.value) for n in agac.body
                    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SEKILLER")
    dogru(sekiller == by.SEKIL, "büyük mum: buyuk_sekil.SEKILLER ile buyuk_ders_yaz.SEKIL ayrışıyor")
    olcum = oz(VERI / "buyuk_ders.json")
    gomme = re.compile(r'<GrafikEmbed src="/arastirma/([^/"]+)/([^"]+)\.html" baslik="[^"]*" no="(\d\d)"')
    baslik_re = re.compile(r'"text":"((?:\\u015e|Ş)ekil (?:[^"\\]|\\.)*)"')
    for slug in by.SIRA:
        mdx = (by.CIKTI / f"{slug}.mdx").read_text(encoding="utf-8")
        gom = gomme.findall(mdx)
        dogru([a for _, a, _ in gom] == by.SEKIL[slug], f"{slug}: gömülen figürler {[a for _, a, _ in gom]} ↔ {by.SEKIL[slug]}")
        for s, ad, no in gom:
            dogru(s == slug and ad[:2] == no, f"{slug}: gömme {s}/{ad} numarası {no} ile uyuşmuyor")
            yol = so.CIKTI_KOK / slug / f"{ad}.html"
            if not yol.exists():
                HATA.append(f"{slug}: figür yok: {ad}.html")
                continue
            html = yol.read_text(encoding="utf-8")
            dogru(f'name="tto-olcum-ozu" content="{olcum}"' in html,
                  f"{slug}/{ad}: figür güncel ölçüm dosyasından çizilmemiş (buyuk_sekil.py koşulmalı)")
            m = baslik_re.search(html)
            baslik = json.loads(f'"{m.group(1)}"') if m else ""
            dogru(baslik.startswith(f"Şekil {no} —"), f"{slug}/{ad}: başlık 'Şekil {no} —' ile başlamıyor")
            dogru(not so.tasan_satirlar(baslik), f"{slug}/{ad}: başlık telefonda taşıyor")

    # ── 5 · iddialar
    iddialar(D, dogru)


def iddialar(D: dict, dogru) -> None:
    V = D["davranis"]
    S = D["suzgec"]
    iki = ("ic", "dis")
    fark = lambda v: v["geri_0.5"] - v["ayna_geri_0.5"]
    # ders 6
    for dn in iki:
        v5, v15, v60 = V["5"][dn], V["15"][dn], V["60"][dn]
        dogru(v5["sim_1.0"] < 0.5 and fark(v5) > 0 and v5["net_24"]["ort"] < 0, f"{dn}: 5 dk geri verme okuması tutmuyor")
        dogru(v60["sim_1.0"] > 0.5 and v60["net_24"]["ort"] > 0, f"{dn}: 1 sa devam okuması tutmuyor")
        dogru(abs(v15["sim_1.0"] - 0.5) < 0.02, f"{dn}: 15 dk ±1 ATR payı yazı turaya yakın değil")
        dogru(abs(fark(v60)) < 0.02, f"{dn}: 1 sa yarısına dönüş aynadan belirgin ayrışıyor (metin 'ne sık ne seyrek' diyor)")
        for tf in ("5", "15", "60"):
            v = V[tf][dn]
            dogru(v["makas_mum_kat_ort"] < 1.15 and v["makas_mum_iki_kat"] < 0.06, f"{dn} {tf}: makas büyük mumda açılmıyor değil")
            dogru(v["geri_0.5_dk_med"] <= 2 * int(tf), f"{dn} {tf}: yarısına dönüş 'bir iki mum içinde' değil")
    dogru(V["60"]["ic"]["net_24"]["alt"] > 0, "1 sa 2018–2023 net_24 aralığı sıfırı kapsıyor")
    dogru(V["60"]["dis"]["net_24"]["alt"] < 0 < V["60"]["dis"]["net_24"]["ust"], "1 sa 2024 → net_24 aralığı metindeki gibi sıfırı kapsamıyor")
    dogru(V["5"]["ic"]["net_24"]["ust"] < 0 and V["5"]["dis"]["net_24"]["alt"] < 0 < V["5"]["dis"]["net_24"]["ust"],
          "5 dk net_24 aralıkları metindeki gibi değil (2018–23 sıfırın altında, 2024 → sıfırı kapsıyor)")
    for dn in iki:
        dogru(V["5"][dn]["sim_1.0_ci"]["ust"] < 0.5 and V["5"][dn]["geri_0.5_fark"]["alt"] > 0,
              f"{dn}: 5 dk ±1 ATR payı / yarısına dönüş aralığıyla tutmuyor")
        dogru(V["15"][dn]["geri_0.5_fark"]["alt"] > 0, f"{dn}: 15 dk geri verme aralığı sıfırın üstünde değil")
        dogru(V["15"][dn]["net_24"]["alt"] < 0 < V["15"][dn]["net_24"]["ust"], f"{dn}: 15 dk 24 mum yolu sıfırdan ayrışıyor")
        dogru(V["60"][dn]["sim_1.0_ci"]["alt"] < 0.5 < V["60"][dn]["sim_1.0_ci"]["ust"], f"{dn}: 1 sa ±1 ATR payı yazı turadan ayrışıyor")
        dogru(V["5"][dn]["net24_pip_ort"] < 0 and abs(V["5"][dn]["net24_pip_ort"]) < V["5"][dn]["makas_once_pip_med"]
              < V["60"][dn]["net24_pip_ort"], f"{dn}: pip karşılaştırması (5 dk makastan küçük, 1 sa büyük) tutmuyor")
    dogru(V["15"]["ic"]["sim_1.0_ci"]["alt"] < 0.5 < V["15"]["ic"]["sim_1.0_ci"]["ust"]
          and abs(V["15"]["dis"]["sim_1.0_ci"]["ust"] - 0.5) < 0.005, "15 dk ±1 ATR aralıkları metindeki gibi değil")
    T = D["tek"]
    for dn in iki:
        dogru(T["5"][dn]["pay"] > 0.9 and T["5"][dn]["tum"]["geri_0.5_fark"]["alt"] > 0 and T["5"][dn]["tum"]["net_24"]["ort"] < 0,
              f"{dn}: tek taraflı aralıkla 5 dk geri verme sürmüyor")
    S0 = D["sayim_tum"]
    dogru(S0["60"]["eksik_cuma"] > 0.8 * S0["60"]["eksik"], "1 sa eksik veri dışlamasının çoğu cuma değil")
    dogru(abs(V["5"]["ic"]["net_24"]["ort"] * V["5"]["ic"]["A_pip_med"]) < V["5"]["ic"]["makas_once_pip_med"],
          "5 dk ortalama geri verme pip cinsinden makastan küçük değil")
    for tf in ("5", "60"):
        v = V[tf]["ic"]
        dogru(abs(v["geri_50_uc"] - v["ayna_geri_50_uc"]) < 0.03, f"{tf}: geri çekilip uca dönüş şansla beklenen kadar değil")
        dogru(abs(v["geri_50_uc"] / v["geri_0.5"] - v["ayna_geri_50_uc"] / v["ayna_geri_0.5"]) < 0.03,
              f"{tf}: yarısına dönenler içinde uca dönüş şansla beklenen kadar değil")
    # ders 7
    s5 = S["5"]
    for dn in iki:
        dogru(fark(s5["kapanis"]["uc"][dn]) > 0.02 and abs(fark(s5["kapanis"]["geri"][dn])) < 0.01,
              f"{dn}: 5 dk kapanış ucunda geri verme / geri verilmişte fark yok değil")
        dogru(s5["seans"]["asya"][dn]["sim_1.0"] < s5["seans"]["londra"][dn]["sim_1.0"] and fark(s5["seans"]["asya"][dn]) > 0.04,
              f"{dn}: 5 dk Asya geri verme okuması tutmuyor")
        dogru(0 < fark(s5["seans"]["londra"][dn]) < 0.6 * fark(s5["seans"]["asya"][dn]), f"{dn}: 5 dk Londra 'yarı yarıya küçük' değil")
        dogru(s5["kapanis"]["geri"][dn]["net_24"]["ort"] < 0, f"{dn}: 5 dk geri verilmiş mumun 24 mum yolu eksi değil")
        a15 = S["15"]["seans"]["asya"][dn]
        dogru(a15["sim_1.0_ci"]["ust"] < 0.5 and a15["geri_0.5_fark"]["alt"] > 0, f"{dn}: 15 dk Asya okuması tutmuyor")
        l60 = S["60"]["seans"]["londra"][dn]
        dogru(l60["net_24"]["ort"] > 0, f"{dn}: 1 sa Londra seansı artı değil")
        dogru(s5["ardisik"]["evet"][dn]["net_24"]["ust"] < 0 and abs(s5["ardisik"]["hayir"][dn]["net_24"]["ort"]) < 0.03,
              f"{dn}: 5 dk ardışık büyük mum okuması tutmuyor")
        s60 = S["60"]
        dogru(s60["trend"]["trendle"][dn]["net_24"]["ort"] > 0, f"{dn}: 1 sa trend yönündeki mum artı değil")
        dogru(s60["kapanis"]["geri"][dn]["net_24"]["ort"] < 0 < min(s60["kapanis"]["uc"][dn]["net_24"]["ort"],
                                                                       s60["kapanis"]["orta"][dn]["net_24"]["ort"]),
              f"{dn}: 1 sa fitili uzun mum eksi / öbürleri artı değil")
    dogru(s5["kova"]["4-5"]["ic"]["net_24"]["ust"] < 0 < s5["kova"]["4-5"]["dis"]["net_24"]["ort"], "5 dk 4–5 ATR kovası metindeki gibi değil")
    k15 = S["15"]["kova"]["3-4"]
    dogru(k15["ic"]["net_24"]["ort"] < -0.2 and k15["dis"]["net_24"]["alt"] < 0 < k15["dis"]["net_24"]["ust"], "15 dk 3–4 ATR kovası metindeki gibi değil")
    t60 = S["60"]["trend"]
    dogru(t60["trendle"]["ic"]["net_24"]["alt"] > 0 and t60["yatay"]["ic"]["net_24"]["ort"] < 0 < t60["karsi"]["dis"]["net_24"]["ort"],
          "1 sa trend okuması metindeki gibi değil")
    dogru(abs(t60["trendle"]["dis"]["net_24"]["ort"] - t60["karsi"]["dis"]["net_24"]["ort"]) < 0.1
          and t60["yatay"]["dis"]["net_24"]["ort"] < 0, "1 sa 2024 → trend ayrımı 'iki taraf aynı yerde' değil")
    l = S["60"]["seans"]["londra"]
    dogru(l["ic"]["net_24"]["alt"] < 0 < l["dis"]["net_24"]["alt"], "1 sa Londra aralıkları metindeki gibi değil")
    for v in ("sakin",):
        dogru(all(S["5"]["kosu"][v][dn]["net_24"]["ust"] < 0 for dn in iki), "5 dk sakin geçmiş hücresi metindeki gibi değil")
    dogru(s5["haber"]["haber"]["ic"]["n"] < 1000, "5 dk haber mumu 'çok az' değil")
    dogru(sum(len(v) for v in S["5"].values()) * 3 == 78, "süzgeç hücre sayısı metindeki yetmiş sekiz değil")
    # ders 8
    I = {tf: {dn: {x["giris"]: x for x in D["izgara"][tf][dn]} for dn in iki} for tf in ("5", "15", "60")}
    for tf in ("5", "15", "60"):
        for dn in iki:
            hs = [x for g, x in I[tf][dn].items() if g.endswith(":s2:h1")]
            dogru(all(x["ort_R"] < 0 for x in hs), f"{tf} {dn}: maliyetten sonra artıda bir biçim var (s2·h1)")
    g5 = I["5"]["ic"]
    dogru(all(abs(x["brut_R"]) < 0.1 for g, x in g5.items() if g.endswith(":s2:h1")), "5 dk maliyetsiz sonuçlar sıfır çevresinde değil")
    dogru(g5["ters:piyasa:s2:h1"]["brut_R"] > 0, "5 dk tersine piyasa maliyetsiz artı değil")
    dogru(g5["devam:piyasa:s2:h1"]["maliyet_R"] > 2 * max(abs(x["brut_R"]) for g, x in g5.items() if g.endswith(":s2:h1")),
          "5 dk maliyet maliyetsiz sonuçlardan kat kat büyük değil")
    for g, x in g5.items():
        if g.endswith(":s2:h1") and ":limit_" in g:
            dogru(1.4 < x["maliyet_R"] / abs(x["brut_R"]) < 2.6, f"5 dk {g}: limit maliyeti 'iki katı civarında' değil")
    # maliyetten sonra artı hücreler: yalnız 1 saatte, hedefi 2 R olan geri çekilme limitleri
    for tf in ("5", "15", "60"):
        for dn in iki:
            art = {g for g, x in I[tf][dn].items() if x["n"] and x["ort_R"] > 0}
            dogru(art <= ({"devam:limit_0.25:s2:h2", "devam:limit_0.5:s2:h2"} if tf == "60" else set()),
                  f"{tf} {dn}: maliyetten sonra artı hücreler metindeki gibi değil: {sorted(art)}")
        if tf in ("5", "15"):
            for dn in iki:
                hs = {g: x for g, x in I[tf][dn].items() if g.endswith(":s2:h1") and x["n"]}
                dogru(":limit_" in max(hs, key=lambda g: hs[g]["ort_R"]), f"{tf} {dn}: en az kaybeden biçim limit değil")
    h60 = {g: x for g, x in I["60"]["ic"].items() if g.endswith(":s2:h1") and x["n"]}
    dogru(max(h60, key=lambda g: h60[g]["ort_R"]) == "devam:onayli:s2:h1", "1 sa 2018–23 en az kaybeden onay mumu değil")
    for dn in iki:
        x = I["5"][dn]
        dogru(x["devam:limit_0.5:s2:h1"]["ort_R"] > x["devam:piyasa:s2:h1"]["ort_R"]
              and x["devam:limit_0.5:s2:h1"]["brut_R"] < x["devam:piyasa:s2:h1"]["brut_R"], f"{dn}: 5 dk limit net iyi / maliyetsiz kötü değil")
        dogru(x["ters:limit_uc:s2:h1"]["brut_R"] < x["ters:piyasa:s2:h1"]["brut_R"], f"{dn}: 5 dk tersine limit maliyetsiz kenarı yok etmiyor")
        for r in D["ters_secim"][dn]:
            if r["giris"].endswith(":s2:h1"):
                dogru(r["piyasa_kazanma_dolan"] < 0.5 < r["piyasa_kazanma_kacan"], f"{dn}: ters seçim {r['tf']} {r['giris']} tutmuyor")
    dogru(g5["devam:piyasa:s1:h1"]["maliyet_R"] > g5["devam:piyasa:s2:h1"]["maliyet_R"] > I["60"]["ic"]["devam:piyasa:s2:h1"]["maliyet_R"],
          "stop uzaklığı ve dilimle maliyet sırası metindeki gibi değil")
    g60 = {g: x for g, x in I["60"]["ic"].items() if g.endswith(":s2:h1")}
    dv = [x["brut_R"] for g, x in g60.items() if g.startswith("devam")]
    dogru(sum(b > 0 for b in dv) > len(dv) / 2 and all(x["brut_R"] < 0 for g, x in g60.items() if g.startswith("ters")),
          "1 sa mumun yönündekilerin çoğu artı / tersine hepsi eksi değil")
    ilk2 = sorted(g60, key=lambda g: -g60[g]["ort_R"])[:2]
    dogru(set(ilk2) == {"devam:onayli:s2:h1", "devam:limit_0.25:s2:h1"}, f"1 sa sıfıra en yakın iki biçim metindeki değil: {ilk2}")
    dogru(abs(g5["devam:onayli:s2:h1"]["brut_R"] - g5["devam:piyasa:s2:h1"]["brut_R"]) < 0.02, "5 dk onay ile piyasa maliyetsiz farklı")
    # ders 9 · "Masada": örnek mumların sonucu metindeki hükümlerle (5 dk: yarıya döndü, sonra artı bitti;
    # 1 sa: yarıya dönmedi, bir gün sonra makastan küçük artı)
    def ornek(tf):
        o = D["ornek"][tf]
        m = o["mumlar"]
        i = next(k for k, x in enumerate(m) if x[0] == o["bt"])
        s = m[i + 1:i + 25]
        orta = (o["h"] + o["l"]) / 2
        y = o["yon"]
        return (min(x[3] for x in s) <= orta if y > 0 else max(x[2] for x in s) >= orta), y * (s[-1][4] - o["c"]) / o["A"]
    t15 = datetime.fromtimestamp(D["ornek"]["15"]["bt"], ZoneInfo("Europe/London"))
    dogru(t15.hour >= 7, "örnek 15 dk mum Asya seansında (metin 'Asya seansında değil' diyor)")
    g5, n5 = ornek("5")
    g60, n60 = ornek("60")
    dogru(g5 and n5 > 0, "örnek 5 dk mum: 'yarıya döndü, uyarı yanıldı' hükmü tutmuyor")
    dogru((not g60) and 0 < n60 * D["ornek"]["60"]["A"] / 10 < V["60"]["ic"]["makas_once_pip_med"] + 1,
          "örnek 1 sa mum: 'yarıya dönmedi, maliyetini çıkaramazdı' hükmü tutmuyor")
    B = D["bacak"]
    dogru(all(b["hukum"] == "calismiyor" for b in B), "büyük mum: bütün girişler 'çalışmıyor' değil")
    dogru(all(b["dis"]["ort_R"] <= 0 for b in B), "büyük mum: 2024 → artı bir giriş var")
    dogru(all(b["suzgec"] for b in B if b["rol"] == "islem") and len([b for b in B if b["rol"] == "islem"]) == 3,
          "büyük mum: seçilen girişler metindeki gibi üç ve süzgeçli değil")
    l60 = next(b for b in B if b["rol"] == "islem" and b["tf"] == 60 and b["giris"].startswith("devam"))
    dogru(l60["dis"]["ust"] < 0 and l60["dis"]["brut_R"] < 0, "1 sa seçilen giriş: aralık ve maliyetsiz sonuç metindeki gibi değil")
    ref = {(b["tf"], b["giris"]): b for b in B if b["rol"] == "referans"}
    dogru(ref[(5, "ters:piyasa:s2:h1")]["dis"]["brut_R"] > 0 and ref[(60, "devam:piyasa:s2:h1")]["dis"]["brut_R"] > 0
          and ref[(60, "devam:limit_0.5:s2:h1")]["dis"]["brut_R"] > 0, "referans maliyetsiz okumaları metindeki gibi değil")
