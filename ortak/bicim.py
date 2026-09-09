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

from datetime import date, datetime, timedelta

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


def sonraki_is_gunu(gun: date) -> date:
    """`gun`den SONRAKİ ilk iş günü (Pzt–Cum).

    Yayımlanmış bir tarihin ne kadar ileri olabileceğinin sınırı budur, "yarın"
    değil. Sebep kaynağın kendi yayım sözleşmesi: TCMB ERTESİ İŞ GÜNÜNÜN
    gösterge kurunu bugün yayımlıyor (USDTRYDeval hattı bunu bilerek istiyor —
    `EVDS_ILERI_GUN`), yani cuma günü çekilen seri PAZARTESİ ile biter.
    "Yarından ileri olamaz" kuralı bu yüzden her cuma öğleden sonra yanlış
    alarm veriyordu: 04.09.2026 (cuma) tazelemesinden sonra sayfa sınavı
    `usdtry-deval/ozet.json: _tarih 07.09.2026 yarından ileri` diye DÜŞTÜ ve
    yayın iş akışı arka arkaya dört kez kırmızı bitti — site yirmi bir saat
    dondu, dördü de kullanıcıya e-posta olarak gitti. Veri doğruydu, ölçüt
    yanlıştı; ve yayının önünde duran bir denetimin yanlış alarmı arızanın
    kendisidir.

    Sınır GEVŞEK DEĞİL: hafta içi hâlâ +1 gün, hafta sonunu atlarken en çok
    +3 gün. Haftalar ileri bir tarih yine ENGEL üretir.
    """
    ertesi = gun + timedelta(days=1)
    while ertesi.weekday() >= 5 or tatil_mi(ertesi):   # 5=Cmt, 6=Paz
        ertesi += timedelta(days=1)
    return ertesi

# RESMÎ TATİL — sınırın hafta sonundan sonraki yarısı.
#
# Yukarıdaki sınır yalnız hafta sonunu atlıyordu ve bu ölçülebilir bir gün
# için yetmiyor: 31.12.2026 PERŞEMBE tam iş günü, TCMB o gün ertesi iş
# gününün kurunu ilan eder ve ertesi iş günü 1 Ocak TATİL olduğu için
# 04.01.2027'dir. Hafta sonu bilen ama tatil bilmeyen sınır o gün 01.01.2027
# der ve yayımlanan DOĞRU tarihi "ileri" sayıp yayını durdurur — 04.09.2026'da
# aynı sınıftan bir yanlış alarm siteyi yirmi bir saat dondurmuştu. Aynı hesap
# 28.10.2026 için de tutuyor (29 Ekim tatil → sınır 30.10).
#
# SABİT tarihli tatiller kanunla bellidir ve burada tam listelenir. HAREKETLİ
# olanlar (Ramazan ve Kurban bayramları) hicri takvimden gelir ve resmî
# takvimden OKUNMADAN buraya YAZILMAZ — uydurma bir tarih, olmayan bir tatilde
# sınırı gevşetir ve gerçek bir ileri tarihi kaçırır. Girilmemiş bir yıl için
# davranış bugünküyle AYNI (yalnız hafta sonu atlanır), yani bu tablo hiçbir
# koşulda yeni bir yanlış alarm üretemez: eklenen her gün sınırı yalnız İLERİ
# taşır. Bayram günleri girildiğinde `HAREKETLI_TATIL`e yılıyla eklenir.
TATIL_SABIT = (
    (1, 1),      # Yılbaşı
    (4, 23),     # Ulusal Egemenlik ve Çocuk Bayramı
    (5, 1),      # Emek ve Dayanışma Günü
    (5, 19),     # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    (7, 15),     # Demokrasi ve Millî Birlik Günü
    (8, 30),     # Zafer Bayramı
    (10, 29),    # Cumhuriyet Bayramı
)
# {yıl: (ISO gün, …)} — resmî takvimden girilir; boş yıl = yalnız hafta sonu.
HAREKETLI_TATIL: dict[int, tuple[str, ...]] = {}


def tatil_mi(gun: date) -> bool:
    """`gun` resmî tatil mi (sabit tarihliler + girilmiş hareketli günler)."""
    if (gun.month, gun.day) in TATIL_SABIT:
        return True
    return gun.isoformat() in HAREKETLI_TATIL.get(gun.year, ())
