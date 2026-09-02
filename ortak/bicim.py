"""Sayı ve tarih yazımı — Python tarafının TEK biçim kaynağı.

Sözleşme site/src/lib/bicim.ts ile birebir aynıdır; iki dosya birlikte değişir:
· ondalık ayracı virgül, binlik ayracı nokta (tr-TR);
· eksi işareti U+2212 (−), ASCII tire değil — tabloda hizalama bozulmaz;
· yüzde işareti sayıdan ÖNCE, işaret onun da önünde: "−%1,88", "+%0,4";
· baz puan bir birimdir, sayıdan SONRA yazılır: "−6,5 bp".

Okura giden her Python metni (bülten ölçüm katmanı, tweet, teknik) sayıyı
buradan yazar. `f"{x:+.2f}"` kalıbı okur metnine girmez: hem ondalık noktası
hem ASCII tire taşır ve bülten denetimi (`bicim` ölçütü) bunu uyarı olarak
listeler.
"""
from __future__ import annotations

from datetime import date, datetime

EKSI = "−"

AYLAR_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def sayi(v: float | int | None, ondalik: int = 1, isaret: bool = False) -> str:
    """1234.5 → "1.234,5"; isaret=True ise pozitife "+" konur; eksi U+2212.

    None → "—" (ölçülmemiş değer uydurulmaz)."""
    if v is None:
        return "—"
    v = float(v)
    m = f"{abs(v):,.{ondalik}f}".replace(",", "|").replace(".", ",").replace("|", ".")
    # Yuvarlamadan sonra sıfır kalan değer işaretsiz yazılır ("−0,00" olmaz).
    sifir = float(m.replace(".", "").replace(",", ".")) == 0.0
    if v < 0 and not sifir:
        return EKSI + m
    if isaret and v > 0 and not sifir:
        return "+" + m
    return m


def yuzde(v: float | int | None, ondalik: int = 1, isaret: bool = False) -> str:
    """İşaret önde, % sayının önünde: yuzde(-1.884, 2) → "−%1,88"."""
    if v is None:
        return "—"
    govde = sayi(abs(float(v)), ondalik)
    if float(v) < 0 and govde.strip("0,.") != "":
        return f"{EKSI}%{govde}"
    if isaret and float(v) > 0 and govde.strip("0,.") != "":
        return f"+%{govde}"
    return f"%{govde}"


def degisim(v: float | int | None, birim: str = "%", ondalik: int = 2) -> str:
    """Birimli değişim: birim "%" ise yuzde(), değilse "sayı birim" ("−6,5 bp")."""
    if v is None:
        return "—"
    b = (birim or "").strip()
    if b == "%":
        return yuzde(v, ondalik, isaret=True)
    return f"{sayi(v, ondalik, isaret=True)}{' ' + b if b else ''}"


def tarih_uzun(t: str | date | datetime | None) -> str:
    """'2026-09-01' / '01.09.2026' / date → "1 Eylül 2026"; çözülemezse olduğu gibi."""
    d = tarihe_cevir(t)
    if d is None:
        return t if isinstance(t, str) else ""
    return f"{d.day} {AYLAR_TR[d.month - 1]} {d.year}"


def tarih_kisa(t: str | date | datetime | None) -> str:
    """→ "01.09.2026"; çözülemezse olduğu gibi."""
    d = tarihe_cevir(t)
    if d is None:
        return t if isinstance(t, str) else ""
    return d.strftime("%d.%m.%Y")


def tarihe_cevir(t) -> date | None:
    """GG.AA.YYYY · AA.YYYY (ayın son günü) · ISO (YYYY-MM-DD…) → date; aksi None."""
    if isinstance(t, datetime):
        return t.date()
    if isinstance(t, date):
        return t
    if not isinstance(t, str):
        return None
    s = t.strip()
    try:
        if len(s) == 10 and s[2] == "." and s[5] == ".":
            return datetime.strptime(s, "%d.%m.%Y").date()
        if len(s) == 7 and s[2] == ".":
            ay, yil = int(s[:2]), int(s[3:])
            nxt = date(yil + (ay == 12), 1 if ay == 12 else ay + 1, 1)
            return date.fromordinal(nxt.toordinal() - 1)
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None
    return None
