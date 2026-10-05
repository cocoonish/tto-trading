#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DÜZELTME YANITI — yayımlanmış bir gönderideki hatalı sayı ya da iddia için
orijinalin altına "Düzeltme" yanıtı (karar 05.10.2026).

Sitede her yayımlanmış sayının tarihli bir düzeltme kaydı var (bülten JSON'unun
`duzeltmeler` alanı, analiz ön bilgisinin `duzeltmeler` listesi); X'te yoktu.
Hatalı bir sayı X'te düzeltilmeden duruyordu.

TETİK AÇIKTIR. Hangi düzeltmenin X'e gideceğine YAZAR karar verir: düzeltme
kaydına iki isteğe bağlı alan yazar —

    gonderi        hedef gönderinin defter anahtarı ("bulten:2026-10-04",
                   "analiz:<slug>"); tweet/defter.json'da KİMLİKLİ olmalı
    gonderi_metni  yazarın kısa düzeltme metni (düz metin, sayfa yapısı anmaz)

Otomatik alt dize tetiği bilerek YOK. Ölçüldü (05.10.2026): kayıtların `eski`
değerini arşivde aramak 85 kaydın yalnız 9'unda eşleşiyor ve bunların 3'ü
YANLIŞ gönderiye düşüyor ("%2,56" → "Brent −%2,56"); gerçek vakaları da
kaçırıyor (bileşik `eski` metni gönderide birebir geçmiyor). İlgisiz bir
gönderinin altına atılan herkese açık bir "Düzeltme", korumak istediği güveni
doğrudan zedeler.

Metin alanlardan mekanik KURULMAZ: kayıtların beşte biri sayfa yapısını anıyor
("gösterge şeridi", "Türkiye bölümü") ve X okurunun elinde o sayfa yok. Gönderi
yazarın `gonderi_metni`dir; araç yalnız başlığı ("Düzeltme — <hedefin başlığı>")
ve sorumluluk notunu ekler.

DEFTER ANAHTARI içeriğe bağlıdır: duzeltme:<hedef>:<sha1(eski|yeni)[:8]>.
Aynı kayıt birkaç bülten dosyasında çoğalsa da (yazı katmanı listeyi bütünüyle
yeniden yazar) tek gönderi çıkar; düzeltmenin düzeltmesi başka bir eski→yeni
çifti olduğu için ayrı anahtarla, AYNI ana gönderinin altına gider.

METİN TEKİLLİĞİ (`metin_ozu`): anahtar eski→yeni çiftine bağlı, X ise METNE
bakar — aynı hedefe aynı metni ikinci kez kabul etmez (403, kopya içerik). İki
kayıt aynı hedefe aynı `gonderi_metni`ni taşırsa (bir yanıt iki düzeltmeyi
birden anlatıyor) ikincisi aday OLMAZ: koşu içinde adıyla uyarılır, defterde
o metin o hedefe zaten gitmişse sessizce geçilir. Önce bu ikiz her sabah 403
alıp koşuyu düşürüyor, arkadaki geçerli düzeltmeleri ve etkileşim okumasını
21 gün boyunca götürüyordu. Öz defter kaydına yazılır (`metin_oz`); anahtar
tanımı değişmez. Ters hâl — aynı eski→yeni çiftine iki AYRI metin — tek
yanıt üretir ve ikinci metin koşu içinde adıyla uyarılır.

PENCERE: kaydın KENDİ tarihinden (`tarih`) sonraki PENCERE_GUN gün — kayıt
hangi sayının dosyasında durursa dursun; bülten ve analiz için tek kural
(`_pencerede`). Bülten dosyasının günü yalnız gelecekteki dosyayı eler. Pencere
dışında kalan ya da tarihi çözülemeyen, `gonderi` taşıyan ve defterde henüz
olmayan kayıt SESSİZCE düşmez: adıyla uyarılır ("X'e gitmedi"). Geçmiş
gönderiler için kendiliğinden düzeltme ATILMAZ.

Sınama girişi (yazma kapısı bunu alt süreçte çağırır, bkz. bulten/yaz.py):

    echo "<gonderi_metni>" | python3 tweet/duzeltme.py --sina bulten:2026-10-04

gönderimdeki metnin birebir aynısını kurar ve tweet kapısından geçirir;
ENGEL'de çıkış 1.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
import uret  # noqa: E402
import analiz as analiz_m  # noqa: E402

ARSIV = BURASI / "arsiv"
PENCERE_GUN = 21
ON_EK = "duzeltme"
HEDEF_RE = re.compile(r"^(bulten|analiz|teknik|ozel):\S+$")

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def anahtar(hedef: str, eski: str, yeni: str) -> str:
    """İçeriğe bağlı defter anahtarı — sıraya değil (sıra her yamada kayar)."""
    oz = hashlib.sha1(f"{eski}|{yeni}".encode("utf-8")).hexdigest()[:8]
    return f"{ON_EK}:{hedef}:{oz}"


def metin_ozu(govde: str) -> str:
    """Yanıt metninin özü: gönderimdeki normalleştirmeden (boşluk tekleştirme +
    tipografi, `metin` ile aynı yol) sonra sha256[:12]. Aynı hedefte başlık ve
    sorumluluk notu sabit olduğu için X'in kopya içerik kararını bu belirler."""
    return hashlib.sha256(uret._tipografi(re.sub(r"\s+", " ", str(govde)).strip())
                          .encode("utf-8")).hexdigest()[:12]


def _anahtar_hedefi(k: str) -> str | None:
    """duzeltme:<hedef>:<oz> → <hedef> (hedef anahtarı ':' taşır, öz taşımaz)."""
    if not k.startswith(ON_EK + ":"):
        return None
    govde = k[len(ON_EK) + 1:]
    return govde.rsplit(":", 1)[0] if ":" in govde else None


def kimlikli(defter: dict, hedef: str) -> str | None:
    """Hedefin zincirindeki İLK kimlik; kimliksizse None (yanıt atılamaz)."""
    idler = (defter.get(hedef) or {}).get("idler") or []
    return str(idler[0]) if idler else None


# ── kaynaklar ────────────────────────────────────────────────────────────────

def _pencerede(d: dict, bugun: dt.date) -> bool | None:
    """Kaydın tarihi penceredeyse True, değilse False (geçmiş ya da ileri),
    tarih çözülemezse None. Bülten ve analiz için TEK tanım."""
    try:
        gun = dt.date.fromisoformat(str(d.get("tarih") or "")[:10])
    except ValueError:
        return None
    return bugun - dt.timedelta(days=PENCERE_GUN) <= gun <= bugun


def _bulten_kayitlari(bugun: dt.date, dizin: Path) -> list[dict]:
    """Bülten dosyalarındaki gonderi'li kayıtlar. Pencere burada SORULMAZ
    (kaydın tarihinden sorulur, `adaylar`): düzeltme düzelttiği sayının eski
    dosyasına da yazılabilir. Yalnız gelecekteki dosya elenir."""
    out = []
    if not dizin.exists():
        return out
    for p in sorted(dizin.glob("*.json")):
        try:
            gun = dt.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if gun > bugun:
            continue
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            continue
        for d in b.get("duzeltmeler") or []:
            if isinstance(d, dict) and (d.get("gonderi") or d.get("gonderi_metni")):
                out.append({**d, "kaynak": f"bulten:{p.stem}"})
    return out


_FM = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
_OGE = re.compile(r"^(\s*)-\s+([A-Za-z_]\w*):\s*(.*)$")
_ALAN = re.compile(r"^(\s+)([A-Za-z_]\w*):\s*(.*)$")


def on_bilgi_duzeltmeleri(metin: str) -> list[dict]:
    """Analiz ön bilgisindeki `duzeltmeler:` listesi (ortak/on_bilgi yalnız tek
    satırlık skaler okur). Biçim, depodaki yazıların kullandığı kadardır:
    `  - alan: '…'` ile açılan öğe, `    alan: '…'` ile süren alanlar; değerler
    on_bilgi.deger ile çözülür (tek tanım: tırnak ve '' kaçışı)."""
    m = _FM.match(metin)
    if not m:
        return []
    out: list[dict] = []
    icinde = False
    for satir in m.group(1).splitlines():
        if not icinde:
            if re.match(r"^duzeltmeler:\s*$", satir):
                icinde = True
            continue
        if satir and not satir[0].isspace():
            break                                              # liste bitti
        o = _OGE.match(satir)
        if o:
            out.append({o.group(2): analiz_m._on_bilgi.deger(o.group(3))})
            continue
        a = _ALAN.match(satir)
        if a and out:
            out[-1][a.group(2)] = analiz_m._on_bilgi.deger(a.group(3))
    return out


def _duzeltme_blogu(metin: str) -> str:
    """Ön bilginin ham `duzeltmeler:` bloğu (uyarı kararı için)."""
    m = _FM.match(metin)
    if not m:
        return ""
    blok = re.search(r"^duzeltmeler:\s*\n((?:[ \t].*\n?|\s*\n)*)", m.group(1) + "\n", re.M)
    return blok.group(1) if blok else ""


def _analiz_kayitlari(bugun: dt.date, dizin: Path) -> tuple[list[dict], list[str]]:
    """(kayıtlar, uyarılar). Bir dosyanın okunamayan ön bilgisi (katlanmış YAML)
    YALNIZ o dosyayı düşürür; öbür dosyalar ve bülten kayıtları işlenir.
    Uyarı yalnız o dosyanın düzeltme bloğu X'e bir şey götürmek istiyorsa
    (gonderi/gonderi_metni) basılır — X'e hiçbir şey göndermeyen bir dosya her
    koşuda uyarı üretmez. Katlanmış değer düz metin olarak OKUNMAZ: tek tanım
    ortak/on_bilgi'dir."""
    out: list[dict] = []
    uyari: list[str] = []
    if not dizin.exists():
        return out, uyari
    for y in sorted(dizin.glob("*.mdx")):
        ham = y.read_text(encoding="utf-8")
        try:
            kayitlar = on_bilgi_duzeltmeleri(ham)
        except analiz_m._on_bilgi.OnBilgiHatasi as e:
            if re.search(r"^\s*(?:-\s+)?gonderi(?:_metni)?\s*:", _duzeltme_blogu(ham), re.M):
                uyari.append(f"analiz:{y.stem}: düzeltme kaydı okunamadı ({str(e)[:80]}) — X'e gitmedi")
            continue
        for d in kayitlar:
            if d.get("gonderi") or d.get("gonderi_metni"):
                out.append({**d, "kaynak": f"analiz:{y.stem}"})
    return out, uyari


def _kayit_adi(aday: dict) -> str:
    """Uyarıda kaydın adı: alan + kaynak (iki kayıt aynı dosyada durabilir)."""
    return f"{str(aday.get('alan') or '—')!r} ({aday['kaynak']})"


def adaylar(bugun: dt.date, defter: dict, bulten_dizin: Path | None = None,
            analiz_dizin: Path | None = None) -> tuple[list[dict], list[str]]:
    """(gönderilecek düzeltmeler, uyarılar). Dizinler çağrı anında okunur
    (uret.BULTENLER, analiz.ANALIZ_DIZIN) — duman fikstürü onları yamar.

    Her aday: {anahtar, hedef, ust, metin_ham, eski, yeni, kaynak, alan, metin_oz}.
    Defterde olan anahtar ve hedefe zaten gitmiş metin atlanır; hedefi kimliksiz
    kayıt GÖNDERİLMEZ ve adıyla uyarılır (yazma kapısı bunu zaten reddeder;
    analiz ön bilgisi o kapıdan geçmez)."""
    bd = bulten_dizin or uret.BULTENLER
    ad = analiz_dizin or analiz_m.ANALIZ_DIZIN
    an_kayit, an_uyari = _analiz_kayitlari(bugun, ad)
    kayitlar = _bulten_kayitlari(bugun, bd) + an_kayit
    secilen: dict[str, dict] = {}
    uyari: list[str] = list(an_uyari)
    # Defterde bir hedefe ZATEN giden (ya da gönderimi kesilmiş, hedefi silinmiş)
    # metinler: (hedef, metin özü). X aynı metni ikinci kez almaz.
    giden_metin = {(h, v.get("metin_oz")) for kk, v in defter.items()
                   if (h := _anahtar_hedefi(kk)) and isinstance(v, dict) and v.get("metin_oz")}
    secilen_metin: dict[tuple[str, str], str] = {}
    for d in kayitlar:
        hedef = str(d.get("gonderi") or "").strip()
        govde = str(d.get("gonderi_metni") or "").strip()
        pencere = _pencerede(d, bugun)
        if not pencere:
            # Pencere dışı ya da tarihsiz: gönderilmez. Uyarı yalnız defterde
            # olmayan (gönderilmiş eski kayıt sonsuza kadar uyarı üretmesin) ve
            # tarihi GEÇMİŞTE ya da çözülemeyen kayda — ileri tarihli kayıt
            # vakti gelince gider.
            k0 = anahtar(hedef, str(d.get("eski") or ""), str(d.get("yeni") or ""))
            if pencere is False and str(d.get("tarih") or "")[:10] > bugun.isoformat():
                continue
            if k0 not in defter:
                neden = ("tarihi çözülemedi" if pencere is None
                         else f"{PENCERE_GUN} günlük pencerenin dışında")
                uyari.append(f"{d['kaynak']}: düzeltme kaydı ({str(d.get('tarih') or '—')[:10]}) "
                             f"{neden} — X'e gitmedi")
            continue
        if not hedef or not govde:
            uyari.append(f"{d['kaynak']}: düzeltme kaydında gonderi ve gonderi_metni birlikte "
                         "yazılır — biri eksik, X'e gitmedi")
            continue
        if not HEDEF_RE.match(hedef):
            uyari.append(f"{d['kaynak']}: düzeltme hedefi bir defter anahtarı değil ({hedef!r})")
            continue
        ust = kimlikli(defter, hedef)
        if not ust:
            uyari.append(f"{d['kaynak']}: düzeltme hedefi {hedef} defterde kimliksiz — yanıt atılamaz")
            continue
        k = anahtar(hedef, str(d.get("eski") or ""), str(d.get("yeni") or ""))
        oz = metin_ozu(govde)
        if k in defter:
            continue
        if k in secilen:
            # Aynı eski→yeni çifti, AYRI metin: yalnız ilk kaydın metni gider.
            # Uyarı yalnız koşu içi çakışmada — gönderildikten sonra yapılan biçim
            # düzeltmesi (`k in defter`) pencere boyunca her koşuda uyarı basmaz.
            if oz != secilen[k]["metin_oz"]:
                uyari.append(f"{d['kaynak']}: {hedef} için aynı eski→yeni çiftiyle ikinci bir "
                             f"gonderi_metni var (alan {str(d.get('alan') or '—')!r}) — yalnız "
                             f"{_kayit_adi(secilen[k])} kaydının metni gider; iki metni tek kayıtta birleştir")
            continue
        if (hedef, oz) in giden_metin:
            continue                                   # bu metin bu hedefe zaten gitti
        if (hedef, oz) in secilen_metin:
            ilk = secilen[secilen_metin[(hedef, oz)]]
            uyari.append(f"{d['kaynak']}: {hedef} için aynı metinle ikinci bir düzeltme kaydı "
                         f"(alan {str(d.get('alan') or '—')!r}) — tek yanıt gider ({_kayit_adi(ilk)} kaydı); "
                         "X aynı metni ikinci kez kabul etmez")
            continue
        secilen[k] = {"anahtar": k, "hedef": hedef, "ust": ust, "metin_ham": govde,
                      "eski": d.get("eski"), "yeni": d.get("yeni"), "kaynak": d["kaynak"],
                      "alan": d.get("alan"), "metin_oz": oz}
        secilen_metin[(hedef, oz)] = k
    return list(secilen.values()), uyari


# ── metin ────────────────────────────────────────────────────────────────────

def hedef_basligi(hedef: str, arsiv: Path | None = None) -> str:
    """Hedef gönderinin başlığı ve tarihi: arşivdeki gönderilmiş metnin ilk
    satırından ("Haftaya Bakış — 4 Ekim 2026" → "Haftaya Bakış, 4 Ekim 2026";
    analizde başlık satırı da eklenir). Arşiv yoksa anahtardan kurulur."""
    yol = (arsiv or ARSIV) / (hedef.replace(":", "-") + ".txt")
    try:
        ham = yol.read_text(encoding="utf-8") if yol.exists() else None
    except (OSError, UnicodeDecodeError):
        ham = None                                             # bozuk arşiv: anahtardan kur
    if ham is not None:
        govde = ham.split("\n", 2)
        satirlar = [s.strip() for s in (govde[2] if len(govde) > 2 else "").split("\n") if s.strip()]
        if satirlar:
            bas = satirlar[0].replace(" — ", ", ", 1)
            if hedef.startswith("analiz:") and len(satirlar) > 1:
                bas += ": " + satirlar[1].split(" — ")[0].strip()
            return bas
    tur, ad = hedef.split(":", 1)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", ad)
    tarih = (f"{int(m.group(3))} {AYLAR[int(m.group(2))]} {m.group(1)}" if m else "")
    if tur == "bulten" and m:
        gun = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return f"{'Haftaya Bakış' if gun.weekday() == 6 else 'Sabah Notu'}, {tarih}"
    return f"{'Analiz' if tur == 'analiz' else tur.capitalize()}{', ' + tarih if tarih else ''}"


def metin(aday: dict, arsiv: Path | None = None) -> str:
    """'Düzeltme — <hedef başlığı>' + yazarın metni + sorumluluk notu."""
    govde = uret._tipografi(re.sub(r"\s+", " ", aday["metin_ham"]).strip())
    not_ = uret.SORUMLULUK_TEKNIK if aday["hedef"].startswith("analiz:") else uret.SORUMLULUK_BULTEN
    return f"Düzeltme — {hedef_basligi(aday['hedef'], arsiv)}\n\n{govde}\n\n{not_}"


def sina(hedef: str, govde: str) -> tuple[list[str], list[str]]:
    """Yazma anı sınaması: gönderimdeki metnin BİREBİR aynısı (başlık + metin +
    sorumluluk notu) kurulur ve tweet kapısından (tur='duzeltme') geçirilir."""
    import denetim as denetim_m
    return denetim_m.denetle(metin({"hedef": hedef, "metin_ham": govde}), "duzeltme")


def sina_analiz(yol: Path, defter: dict) -> list[str]:
    """Bir analiz dosyasının X'e gidecek düzeltme kayıtlarını YAZILDIĞI GÜN sınar
    (site/tools/analiz_sinavi.py çağırır; UYARI olur, siteyi durdurmaz). Bülten
    kaydı yazma anında `bulten/yaz.py`den geçer; analiz ön bilgisi elle yazıldığı
    için kusurlu bir metin ancak gönderim sabahı görünürdü ve tweet koşusu
    pencere boyunca (21 gün) her gün kırmızı biterdi. Ayrıştırıcı ve gönderilen
    metin gönderimdekinin aynısıdır (`on_bilgi_duzeltmeleri` · `sina`).
    Dönüş: okura değil yazara giden satırlar ("ENGEL …" · "UYARI …")."""
    ham = yol.read_text(encoding="utf-8")
    if not re.search(r"^\s*(?:-\s+)?gonderi(?:_metni)?\s*:", _duzeltme_blogu(ham), re.M):
        return []
    try:
        kayitlar = on_bilgi_duzeltmeleri(ham)
    except analiz_m._on_bilgi.OnBilgiHatasi as e:
        return [f"UYARI düzeltme kaydı okunamadı ({str(e)[:80]}) — X'e gitmez"]
    out: list[str] = []
    for i, d in enumerate(kayitlar, 1):
        hedef, govde = d.get("gonderi"), d.get("gonderi_metni")
        if not (hedef or govde):
            continue
        ad = f"düzeltme {i} ({str(d.get('alan') or '—')!r})"
        if not (hedef and govde):
            out.append(f"UYARI {ad}: gonderi ve gonderi_metni birlikte yazılır — X'e gitmez")
            continue
        if not HEDEF_RE.match(str(hedef)):
            out.append(f"UYARI {ad}: hedef {hedef!r} bir gönderim defteri anahtarı değil — X'e gitmez")
            continue
        if not (defter.get(hedef) or {}).get("idler"):
            out.append(f"UYARI {ad}: hedef {hedef!r} gönderim defterinde kimliksiz — yanıt atılamaz")
        engel, uyari = sina(str(hedef), str(govde))
        out += [f"ENGEL {ad}: {x}" for x in engel] + [f"UYARI {ad}: {x}" for x in uyari]
    return out


if __name__ == "__main__" and len(sys.argv) >= 3 and sys.argv[1] == "--sina-analiz":
    # Alt süreçte çağrılır (site/tools/analiz_sinavi.py) — `--sina` ile aynı sebep.
    try:
        _defter = json.loads((BURASI / "defter.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _defter = {}
    for _x in sina_analiz(Path(sys.argv[2]), _defter):
        print(_x)
    raise SystemExit(0)


if __name__ == "__main__" and len(sys.argv) >= 3 and sys.argv[1] == "--sina":
    # Alt süreçte çağrılır (bulten/yaz.py): bu modül sys.path'i ve sys.modules
    # ['uret']'i değiştirir; yazma kapısının kendi sürecine yüklenmemeli.
    _e, _u = sina(sys.argv[2], sys.stdin.read())
    for _x in _e:
        print(f"ENGEL {_x}")
    for _x in _u:
        print(f"UYARI {_x}")
    raise SystemExit(1 if _e else 0)


if __name__ == "__main__":                                     # kuru döküm
    import gonder
    bugun = dt.datetime.now(dt.timezone.utc).date()
    a, u = adaylar(bugun, gonder._defter_oku(gonder.DEFTER))
    for x in u:
        print("!", x)
    for x in a:
        print(f"── {x['anahtar']} → yanıt {x['ust']}\n{metin(x)}\n")
    if not a:
        print("gönderilecek düzeltme yok")
