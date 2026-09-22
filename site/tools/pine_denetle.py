#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pine Script statik denetimi — derleyicisi olmayan bir dilin sigortası.

NEDEN VAR. Pine yalnız TradingView'de derlenir; bu depoda derleyici YOK.
Yani bir sözdizimi ya da tip hatası ancak birileri kodu TradingView'e
yapıştırdığında görünür — yani okurun elinde. Aşağıdaki ölçütlerin HER BİRİ
bu depoda gerçekten yapılmış bir hatadan türedi; hiçbiri varsayımsal değil.
Bir hata yapıldığında sorulacak soru "bunu düzelttim mi" değil, "bu hatayı
bir daha yapmamı ne engelleyecek"tir.

KAPSAM DAR VE ADIYLA YAZILI. Bu bir Pine derleyicisi değildir ve öyleymiş
gibi davranmaz: yalnız aşağıdaki ON BİR kusuru arar. Geçmesi "kod derlenir"
demek DEĞİL, "bu on bir kusur yok" demektir. Dokuz ve on derleme kusuru
değil SÖZLEŞME kusurudur: kapanmamış bir bar hakkında konuşan bir betik
derlenir, yeşil koşar ve okura her tick değişen bir hüküm gösterir. On
birincisi Pine'ın en yaygın derleme hatalarından biridir: bir kullanıcı
fonksiyonunun genel değişkeni `:=` ile değiştirmesi.

    python3 site/tools/pine_denetle.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
PINE = BURASI.parent / "public" / "indikatorler"

# ta.* fonksiyonlarının UZUNLUK argümanı "simple int" ister: bara göre
# değişen bir seri int kabul edilmez. Hata mesajı da yanıltıcıdır.
SIMPLE_UZUNLUK = ("ta.highest", "ta.lowest", "ta.sma", "ta.ema", "ta.rma",
                  "ta.wma", "ta.median", "ta.stdev", "ta.atr", "ta.change",
                  "math.sum", "ta.highestbars", "ta.lowestbars")


def _parantezsiz(s: str, giris: int = 0) -> tuple[str, int]:
    """Dengeli parantez gruplarını atar; geriye EN DIŞ düzey kalır.

    `giris`, satıra girerken açık olan parantez derinliğidir ve ZORUNLUDUR:
    Pine'da bir çağrı satırlara yayılır, devam satırının açılış parantezi
    ÖNCEKİ satırdadır. Derinliği satır başında sıfırlayan bir sürüm her
    devam satırını en dış düzey sanar ve on iki yanlış alarm üretir."""
    out, derinlik = [], giris
    for ch in s:
        if ch == "(":
            derinlik += 1
        elif ch == ")":
            derinlik = max(0, derinlik - 1)
        elif derinlik == 0:
            out.append(ch)
    return "".join(out), derinlik


def _kod_satirlari(metin: str) -> list[tuple[int, str]]:
    """Yorum ve dizge içi metni ayıklanmış satırlar."""
    out = []
    for n, ham in enumerate(metin.splitlines(), 1):
        s = re.sub(r'"(?:[^"\\]|\\.)*"', '""', ham)      # dizgeler boşaltılır
        s = re.sub(r"//.*$", "", s)                       # yorum atılır
        out.append((n, s))
    return out


def _ilk_arguman(s: str) -> str:
    """`alertcondition(` çağrısının İLK argümanı — üst düzey virgüle kadar.

    Dizge içi virgül ve parantez sayılmaz; ölçüt operatör önceliğini
    soracaksa argümanın SINIRINI bilmek zorundadır."""
    i = s.find("alertcondition(")
    if i < 0:
        return ""
    derinlik, tirnak, out = 0, False, []
    for c in s[i + len("alertcondition("):]:
        if c == '"':
            tirnak = not tirnak
        if tirnak:
            continue
        if c in "([":
            derinlik += 1
            continue
        if c in ")]":
            if derinlik == 0:
                break
            derinlik -= 1
            continue
        if c == "," and derinlik == 0:
            break
        if derinlik == 0:                 # parantez İÇİ üst düzey değildir
            out.append(c)
    return "".join(out)


def denetle(yol: Path) -> list[str]:
    metin = yol.read_text(encoding="utf-8")
    satir = _kod_satirlari(metin)
    ad = yol.name
    bulgu: list[str] = []

    # ① Sürüm ve giriş noktası ilan edilmiş mi.
    if "//@version=" not in metin:
        bulgu.append(f"{ad}: //@version ilanı yok")
    if not re.search(r"^\s*(indicator|strategy|library)\s*\(", metin, re.M):
        bulgu.append(f"{ad}: indicator()/strategy() çağrısı yok")

    # ② VİRGÜLLE ÇOKLU ATAMA. Pine `a = x, b = y` kabul etmez; demet ataması
    #    yalnız `[a, b] = f()` biçimindedir. Bu hata bu dosyada yapıldı.
    #
    #    HASSASİYET: ölçüt YALNIZ en dış düzeye bakmalı. İlk yazımda parantez
    #    içi de taranıyordu ve `input.float(0.5, "…", minval = 0.1, step = …)`
    #    satırlarının hepsi ihlal sayıldı — 78 yanlış alarm. Yanlış alarm
    #    üreten bir denetime kimse bakmaz.
    derinlik = 0
    for n, s in satir:
        acikti = derinlik > 0
        dis, derinlik = _parantezsiz(s, derinlik)
        if acikti:
            continue
        if re.match(r"^\s*\w+\s*=\s*[^=]", dis) and re.search(r",\s*\w+\s*=\s*[^=]", dis):
            bulgu.append(f"{ad}:{n}: virgülle çoklu atama — Pine kabul etmez, satırlara böl")

    # ③ SERİ UZUNLUK. ta.* uzunluğu simple int olmalı; yerel/seri bir
    #    değişken geçirmek derlemeyi düşürür. Bu hata bu dosyada yapıldı.
    sabitler = set(re.findall(r"^\s*(\w+)\s*=\s*input\.\w+\(", metin, re.M))
    sabitler |= set(re.findall(r"^\s*(\w+)\s*=\s*(\d+)\s*$", metin, re.M) and [])
    for n, s in satir:
        for fn in SIMPLE_UZUNLUK:
            for m in re.finditer(re.escape(fn) + r"\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", s):
                arg = [a.strip() for a in m.group(1).split(",")]
                if len(arg) < 2:
                    continue
                uz = arg[-1]
                if re.fullmatch(r"\d+", uz) or uz in sabitler:
                    continue
                if re.fullmatch(r"[\w.]+", uz):
                    bulgu.append(
                        f"{ad}:{n}: {fn} uzunluğu '{uz}' — simple int olmalı; "
                        f"input ya da sabit değilse her değer için ayrı hesaplayıp seç")

    # ④ FONKSİYON PARAMETRESİNİN GEÇMİŞİ. Pine, yerel bir değişkenin
    #    geçmişine bakmaya izin vermez. Bu hata bu dosyada yapıldı.
    icinde = None
    params: set[str] = set()
    for n, s in satir:
        bas = re.match(r"^(\w+)\s*\(([^)]*)\)\s*=>", s)
        if bas:
            icinde = bas.group(1)
            params = {re.sub(r"^\s*(?:simple |series |const )?\w+\s+", "", a).strip()
                      for a in bas.group(2).split(",") if a.strip()}
            params = {a for a in params if re.fullmatch(r"\w+", a)}
            continue
        if icinde and s.strip() and not s.startswith((" ", "\t")):
            icinde, params = None, set()
            continue
        if icinde:
            for a in params:
                if re.search(r"\b" + re.escape(a) + r"\s*\[", s):
                    bulgu.append(
                        f"{ad}:{n}: '{a}' bir fonksiyon parametresi ve geçmişine bakılıyor — "
                        f"Pine buna izin vermez; globali oku ya da seçici bir int al")

    # ⑤ DENGESİZ PARANTEZ — ama SATIR başına değil, DEYİM başına.
    #
    #    Pine'da bir çağrı birden çok satıra yayılabilir ve ara satırların
    #    tek başına dengeli olması BEKLENMEZ. İlk yazım satır satır bakıyordu
    #    ve çok satırlı her çağrıyı ihlal saydı. Doğru ölçü: bir deyim (girintisiz
    #    bir satırla başlayan blok) kapandığında denge SIFIR olmalı.
    denge, bas = 0, 0
    for n, s in satir:
        if denge == 0 and s.strip():
            bas = n
        denge += s.count("(") - s.count(")")
        if denge < 0:
            bulgu.append(f"{ad}:{n}: fazladan kapanan parantez")
            denge = 0
    if denge != 0:
        bulgu.append(f"{ad}: dosya sonunda {denge} parantez açık kaldı (deyim {bas}. satırda başlıyor)")

    # ⑥ İLAN ile İÇERİK ÇELİŞKİSİ. Dosyanın başlığı "hiçbir eşik
    #    uydurulmamıştır" diyorsa, dosyada dersin vermediği bir TANIM SEÇİMİ
    #    grubu bulunamaz. Bu çelişki gerçekten oluştu: tanım seçimleri
    #    eklendi, başlık eski iddiayı taşımaya devam etti. Bir dosyanın
    #    KENDİ HAKKINDAKİ İDDİASI da içeriğinin parçasıdır.
    bas = metin.split("//@version", 1)[0]
    tanim_var = 'input' in metin and re.search(r'group\s*=\s*gT\b', metin) is not None
    mutlak = re.search(r"[Hh]içbiri (kalibre edilmemiş, )?uydurulmam", bas) is not None
    if tanim_var and mutlak and "TANIM SEÇİMİ" not in bas.upper().replace("İ", "I").replace("TANIM SECIMI", "TANIM SEÇİMİ") and "TANIM SEÇİM" not in bas:
        bulgu.append(f"{ad}: başlık 'hiçbiri uydurulmamıştır' diyor ama dosyada "
                     f"tanım seçimi grubu (gT) var — ilan içerikle çelişiyor")

    # ⑦ KULLANIMDAN SONRA TANIMLANAN FONKSİYON. Pine betiği yukarıdan aşağı
    #    derlenir: bir kullanıcı fonksiyonu ÇAĞRILDIĞI satırdan önce
    #    tanımlanmış olmalıdır. Ölçüt durum kutuları fonksiyonlara
    #    bölündüğünde kondu — o güne kadar dosyada tek bir kullanıcı
    #    fonksiyonu yoktu, yani risk YENİ. Statik, saniyeler sürüyor ve
    #    TradingView'e yapıştırmadan soruyor.
    tanim: dict[str, int] = {}
    for n, s in satir:
        m = re.match(r"\s*(?:export\s+)?([A-Za-z_]\w*)\s*\([^)]*\)\s*=>", s)
        if m and m.group(1) not in tanim:
            tanim[m.group(1)] = n
    for fn, tn in tanim.items():
        for n, s in satir:
            if n >= tn:
                break
            # Kendi tanım satırı ve yorum dışı her çağrı sayılır.
            if re.search(r"(?<![\w.])" + re.escape(fn) + r"\s*\(", s):
                bulgu.append(f"{ad}:{n}: '{fn}()' burada çağrılıyor ama "
                             f"{tn}. satırda tanımlanıyor — Pine yukarıdan aşağı derler")
                break

    # ⑧ YEREL KAPSAMDA TANIMLANAN FONKSİYON. Pine bir kullanıcı fonksiyonunu
    #    yalnız GENEL kapsamda kabul eder; `if` bloğunun ya da başka bir
    #    fonksiyonun içinde `f(x) =>` yazılırsa derlenmez. Bu hata 15.09'da
    #    rejim panosunda yapıldı (durum kutusunun `if barstate.islast`
    #    bloğuna bir yardımcı yazıldı) ve yedinci ölçüt onu görmedi: tanım
    #    çağrıdan öncedeydi. Girintili bir tanım satırı ENGEL.
    for n, s in satir:
        if re.match(r"[ \t]+(?:export\s+)?[A-Za-z_]\w*\s*\([^)]*\)\s*=>", s):
            bulgu.append(f"{ad}:{n}: fonksiyon yerel kapsamda tanımlanıyor (girintili `=>`) — "
                         f"Pine fonksiyonu yalnız genel kapsamda kabul eder")

    # ⑨ ALARMIN KAPANIŞ KAPISI. Gönderilmiş bir alarm geri alınamaz. Canlı
    #    barda doğup kapanışta yok olan bir koşul — kırılım modu kalıbı barın
    #    ilk tick'inde yapısal olarak DOĞRUDUR, gap eşiği bir EŞİTLİK
    #    sınamasıdır — okura grafikte karşılığı olmayan bir emir tarif eder.
    #    16.09.2026'da ölçüldü: iki dosyadaki on üç `alertcondition`ın on üçü
    #    de kapısızdı ve fiyat panelinde tam üstlerinde "hepsi KAPANMIŞ bar
    #    üzerinden" yazan bir YORUM duruyordu. Bir kural yalnız yoruma
    #    yazıldığında dayatılmaz; ölçüt o yorumu koda çevirir.
    for n, s in satir:
        if "alertcondition(" not in s:
            continue
        if "barstate.isconfirmed" not in s:
            bulgu.append(f"{ad}:{n}: alertcondition kapanış kapısı taşımıyor — "
                         f"koşul `barstate.isconfirmed and …` ile kurulmalı")
        elif " or " in _ilk_arguman(s):
            # `and` `or`'dan SIKI bağlar: "isconfirmed and A or B" aslında
            # "(isconfirmed and A) or B"dir ve B tarafı kapının DIŞINDA kalır.
            # 16.09.2026'da kapıyı KOYAN yama tam bunu yaptı: üç alarmın ayı
            # tarafı kapısız kaldı ve ölçüt onları GEÇİRDİ, çünkü satırda
            # `barstate.isconfirmed` GEÇİYORDU. Kapının kendi yanlış geçişi de
            # bir arızadır; ölçüt artık üst düzey `or` arar.
            bulgu.append(f"{ad}:{n}: alertcondition koşulunda parantezsiz üst düzey `or` — "
                         f"`and` sıkı bağlar, kapanış kapısı `or`un sağ tarafını KAPSAMAZ")

    # ⑩ KAPANMAMIŞ BARA ÇİZİM. Bar başına çizen her çağrı (`label.new`,
    #    `plotshape`, `barcolor`, `bgcolor`) kapanmamış barda da çalışır ve
    #    bar içinde defalarca doğup kaybolur. Betik `kapanmis` diye bir bar
    #    disiplini ilan ediyorsa, bu çağrıların HEPSİ ondan geçmelidir —
    #    ilan edip bir çağrı yerine uygulamamak, kapsamı sessizce daraltır.
    #    Kapı yalnız disiplini İLAN EDEN dosyada sorulur: ilanı olmayan bir
    #    dosyaya "eksik" demek, ölçütü yanlış dosyaya koşturmak olurdu.
    if re.search(r"^kapanmis\s*=", metin, re.M):
        # Kapı adları SÖZLEŞMEDEN türetilir, elle listelenmez: `kapanmis`in
        # kendisi ve ondan TÜRETİLEN her ad (ör. `cizimBari = bar_index >=
        # last_bar_index - 1 and kapanmis`) kapı sayılır. Elle tutulan bir ad
        # listesi, bir gün yeni bir sarmalayıcı eklendiğinde sessizce
        # yanlış alarm üretirdi.
        kapilar = {"kapanmis"}
        for _, s in satir:
            m = re.match(r"([A-Za-z_]\w*)\s*=[^=]", s)
            if m and any(k in s.split("=", 1)[1] for k in kapilar):
                kapilar.add(m.group(1))
        gecer = lambda s: any(k in s for k in kapilar)          # noqa: E731

        for n, s in satir:
            if re.search(r"\b(plotshape|barcolor|bgcolor)\(", s) and not gecer(s):
                bulgu.append(f"{ad}:{n}: bar başına çizen çağrı `kapanmis` kapısından geçmiyor")
        # `label.new` bir blok içindedir; kapı onu saran EN YAKIN `if`tedir.
        acik: list[tuple[int, str]] = []          # (girinti, satır)
        for n, s in satir:
            girinti = len(s) - len(s.lstrip())
            while acik and acik[-1][0] >= girinti:
                acik.pop()
            if re.match(r"[ \t]*if\b", s):
                acik.append((girinti, s))
            elif "label.new(" in s and not any(gecer(a) for _, a in acik):
                bulgu.append(f"{ad}:{n}: `label.new` kapanmamış barda da basılıyor — "
                             f"saran `if` `kapanmis` taşımalı")

    # ⑪ FONKSİYON İÇİNDEN GENEL DEĞİŞKENE ATAMA. Pine, bir kullanıcı
    #    fonksiyonunun GENEL kapsamdaki değişkeni `:=` ile değiştirmesine izin
    #    vermez ("Cannot modify global variable 'x' in function"); fonksiyondan
    #    yalnız dizi/harita/nesne İÇERİĞİ (array.set, box.set_*) değiştirilir.
    #    21.09.2026'da yapıldı: fiyat panelinin olay fonksiyonu sekiz genel
    #    değişkene yazıyordu, on ölçüt geçiyordu, dosya derlenmiyordu. Genel
    #    adlar GİRİNTİSİZ bildirimlerden türer (`x = …`, `var T x = …`,
    #    `[a, b] = …`); fonksiyon gövdesinde `x :=` görülür, `x` genelse ve
    #    gövdede daha önce `x = …` ile YEREL bildirilmemişse ENGEL. Parametre
    #    adı da yereldir.
    genel: set[str] = set()
    for _, s in satir:
        m = re.match(r"^(?:var\s+|varip\s+)?(?:(?:simple|series|const)\s+)?(?:[A-Za-z_][\w.<>]*\s+)?([A-Za-z_]\w*)\s*=(?!=|>)", s)
        if m:
            genel.add(m.group(1))
        m = re.match(r"^\[([^\]]+)\]\s*=(?!=)", s)
        if m:
            genel |= {a.strip() for a in m.group(1).split(",") if a.strip()}
    icinde, yerel = None, set()
    for n, s in satir:
        bas = re.match(r"^(\w+)\s*\(([^)]*)\)\s*=>", s)
        if bas:
            icinde = bas.group(1)
            yerel = {re.sub(r"^\s*(?:simple |series |const )?\w+\s+", "", a).strip()
                     for a in bas.group(2).split(",") if a.strip()}
            continue
        if icinde and s.strip() and not s.startswith((" ", "\t")):
            icinde, yerel = None, set()
            continue
        if not icinde:
            continue
        m = re.match(r"\s+(?:\[([^\]]+)\]|([A-Za-z_]\w*))\s*=(?!=|>)", s)
        if m:
            yerel |= {a.strip() for a in m.group(1).split(",")} if m.group(1) else {m.group(2)}
        for m in re.finditer(r"(?<![\w.])([A-Za-z_]\w*)\s*:=", s):
            isim = m.group(1)
            if isim in genel and isim not in yerel:
                bulgu.append(f"{ad}:{n}: '{isim}' genel kapsamda bildirilmiş ve `{icinde}()` içinden "
                             f"`:=` ile değiştiriliyor — Pine izin vermez; hükmü döndür, çağrı yerinde yaz")

    return bulgu


def main() -> int:
    yollar = sorted(PINE.glob("*.pine"))
    if not yollar:
        print(f"ENGEL · {PINE} altında .pine yok", file=sys.stderr)
        return 1
    hepsi: list[str] = []
    for y in yollar:
        hepsi += denetle(y)
    if hepsi:
        print("PINE DENETİMİ DÜŞTÜ:", file=sys.stderr)
        for h in hepsi:
            print("  ✗", h, file=sys.stderr)
        return 1
    print(f"pine denetimi · {len(yollar)} dosya · on bir ölçüt GEÇTİ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
