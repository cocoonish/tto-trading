#!/usr/bin/env python3
"""USD/TRY serisinde HAFTA SONU barı var mı — ölçüm, hüküm değil.

Neden: 14.09.2026 koşusunda usdtry ve ovp hatları "VERİ GERİLEDİ" ile
durdu (12.09.2026 → 11.09.2026). 12.09 bir CUMARTESİ ve gözlem sayısı
678'den 677'ye indi, yani seriye bir hafta sonu barı girmiş ve sonra
kaynaktan kalkmış. Yayımlanan sayfa hâlâ o cumartesi damgasını taşıyor.

Bu betik ağa çıkar, HÜKÜM KURMAZ, yalnız ölçer:
  (1) seride kaç hafta sonu barı var, hangi yıllarda
  (2) o barlar bir önceki cuma kapanışıyla AYNI mı (bayat tekrar) yoksa
      farklı mı (pazar açılış penceresinden gerçek kotasyon)
  (3) şu anda 12.09.2026 barı duruyor mu
  (4) hafta sonu barının yıllıklandırılmış hıza etkisi ne kadar

Ölçüm olmadan süzgeç koda girmez (CLAUDE.md — sezgi ölçülmeden koda
girmez); bu dosya o ölçümü üretir.
"""
import sys
import datetime as dt

sys.path.insert(0, "ortak")
import pandas as pd  # noqa: E402
import usdtry as U  # noqa: E402

BUGUN = dt.date.today()


# YENİDEN DENEME, ÇÜNKÜ 429 BİR ÖLÇÜM DEĞİL. İlk keşif koşusu tek
# denemede "Too Many Requests" aldı ve ölçüm hiç yapılamadı; bir hız
# sınırı kaynağın ne döndürdüğü hakkında hiçbir şey söylemez. Keşif işi
# yfinance KURMUYOR (yalnız requests·pandas·numpy), o yüzden chart ucu
# burada yedek değil ASIL yoldur ve payı ona göre verilir.
BEKLEME = (10, 30, 60, 120)


def cek(bas: dt.date) -> pd.Series:
    import time
    hatalar = []
    for ad, fn in (("yfinance", U._yfinance_cek), ("chart ucu", U._chart_cek)):
        for deneme, bekle in enumerate((0,) + BEKLEME, start=1):
            if bekle:
                print(f"    {bekle} sn bekleniyor (deneme {deneme})…")
                time.sleep(bekle)
            try:
                s = fn(bas, BUGUN + dt.timedelta(days=1))
                print(f"  kaynak: {ad} · {len(s)} gözlem (deneme {deneme})")
                return s
            except Exception as e:  # noqa: BLE001
                m = f"{type(e).__name__}: {e}"
                print(f"  {ad} düştü (deneme {deneme}): {m[:160]}")
                hatalar.append(f"{ad}/{deneme}: {m[:80]}")
                # Kurulu olmayan bir modül yeniden denemeyle gelmez.
                if isinstance(e, ModuleNotFoundError):
                    break
    raise SystemExit("ENGEL · ölçüm yapılamadı — " + " | ".join(hatalar[-4:]))


def yol(ad: str, fn, bas: dt.date) -> pd.Series | None:
    """Tek bir ucu dener; düşerse None döner — ölçüm öbür yolu kaybetmez."""
    import time
    for deneme, bekle in enumerate((0,) + BEKLEME, start=1):
        if bekle:
            print(f"    {bekle} sn bekleniyor (deneme {deneme})…")
            time.sleep(bekle)
        try:
            s = fn(bas, BUGUN + dt.timedelta(days=1))
            print(f"  {ad}: {len(s)} gözlem · {s.index[0].date()} → "
                  f"{s.index[-1].date()} (deneme {deneme})")
            return s
        except Exception as e:  # noqa: BLE001
            m = f"{type(e).__name__}: {e}"
            print(f"  {ad} düştü (deneme {deneme}): {m[:150]}")
            if isinstance(e, ModuleNotFoundError):
                return None
    return None


def haftasonu(ad: str, s: pd.Series) -> None:
    hs = s[s.index.dayofweek >= 5]
    print(f"  {ad}: hafta sonu barı {len(hs)} / {len(s)} "
          f"({100 * len(hs) / len(s):.2f}%)")
    if not len(hs):
        return
    yil = hs.groupby(hs.index.year).size()
    print("    yıla göre:", ", ".join(f"{y}:{n}" for y, n in yil.items()))
    gunad = {5: "Cmt", 6: "Paz"}
    gun = hs.groupby(hs.index.dayofweek).size()
    print("    güne göre:", ", ".join(f"{gunad[g]}:{n}" for g, n in gun.items()))
    ayni = fark = 0
    farklar = []
    for t in hs.index:
        onceki = s.loc[:t].iloc[:-1]
        if not len(onceki):
            continue
        o, y = float(onceki.iloc[-1]), float(s.loc[t])
        if abs(y - o) < 1e-9:
            ayni += 1
        else:
            fark += 1
            farklar.append((t.date(), o, y, 100 * (y / o - 1)))
    print(f"    önceki barla birebir AYNI: {ayni} · FARKLI: {fark}")
    if farklar:
        fs = pd.Series([f[3] for f in farklar])
        print(f"    fark (%): medyan {fs.median():+.4f} · azami "
              f"|{fs.abs().max():.4f}|")
    print("    son 12:")
    for t, v in hs.tail(12).items():
        print(f"      {t.date()} {gunad[t.dayofweek]}  {v:.4f}")


def main() -> int:
    print("=" * 64)
    print(f"USD/TRY hafta sonu barı keşfi · {BUGUN}")
    print("=" * 64)
    print("\nSORU: yayımlanan sayfa 12.09.2026 (CUMARTESİ) damgası ve 48,55")
    print("taşıyor; bugünkü koşu 11.09 · 48,59 verdi ve gerileme kapısı düştü.")
    print("Cumartesi barı hangi UÇTAN geliyor — ve gerçek bir kotasyon mu?\n")

    bas = dt.date(2015, 1, 1)
    print("[0] İKİ UÇ AYRI AYRI (üretim chart ucunu kullanıyor, keşif yfinance'i):")
    a = yol("yfinance ", U._yfinance_cek, bas)
    b = yol("chart ucu", U._chart_cek, bas)
    if a is None and b is None:
        raise SystemExit("ENGEL · iki uç da düştü — ölçüm yapılamadı")

    print("\n[1] Hafta sonu barı, UÇ BAŞINA:")
    for ad, s in (("yfinance ", a), ("chart ucu", b)):
        if s is None:
            print(f"  {ad}: ÖLÇÜLEMEDİ (uç düştü)")
        else:
            haftasonu(ad, s)

    print("\n[2] 12.09.2026 (Cumartesi) barı:")
    hedef = pd.Timestamp("2026-09-12")
    for ad, s in (("yfinance ", a), ("chart ucu", b)):
        if s is None:
            print(f"  {ad}: ÖLÇÜLEMEDİ")
        elif hedef in s.index:
            print(f"  {ad}: VAR · {float(s.loc[hedef]):.4f}")
        else:
            print(f"  {ad}: YOK")

    print("\n[3] İki uç birbirinden ayrışıyor mu:")
    if a is not None and b is not None:
        sadece_a = a.index.difference(b.index)
        sadece_b = b.index.difference(a.index)
        print(f"  yalnız yfinance'te: {len(sadece_a)} gün"
              + (f" → {[str(x.date()) for x in sadece_a[-8:]]}" if len(sadece_a) else ""))
        print(f"  yalnız chart ucunda: {len(sadece_b)} gün"
              + (f" → {[str(x.date()) for x in sadece_b[-8:]]}" if len(sadece_b) else ""))
        ortak = a.index.intersection(b.index)
        d = (a.loc[ortak] - b.loc[ortak]).abs()
        buyuk = d[d > 1e-6]
        print(f"  ortak {len(ortak)} günün {len(buyuk)}'inde değer farklı")
        for t in buyuk.index[-8:]:
            print(f"    {t.date()}  yf {float(a.loc[t]):.4f} · chart "
                  f"{float(b.loc[t]):.4f}")
    else:
        print("  iki uç birden ölçülemedi — kıyas YOK")

    print("\n[4] Son 12 gün (uç uca):")
    for ad, s in (("yfinance ", a), ("chart ucu", b)):
        if s is None:
            continue
        print(f"  {ad}:")
        for t, v in s.tail(12).items():
            print(f"    {t.date()} {t.strftime('%a')}  {v:.4f}")

    print("\n[5] Hafta içi kapsam (bir hafta içi süzgeci ne kaybettirir):")
    for ad, s in (("yfinance ", a), ("chart ucu", b)):
        if s is None:
            continue
        temiz = s[s.index.dayofweek < 5]
        ilk, son = temiz.index[0].date(), temiz.index[-1].date()
        bekl = len(pd.bdate_range(ilk, son))
        print(f"  {ad}: hafta içi {len(temiz)} · düşen {len(s) - len(temiz)} · "
              f"iş günü {bekl} ({100 * len(temiz) / bekl:.1f}%)")

    print("\n[6] Yıllıklandırılmış hıza etkisi (varsa):")

    def hiz(seri: pd.Series, gun: int) -> float:
        son = seri.index[-1]
        onceki = seri.loc[:son - pd.Timedelta(days=gun)]
        if not len(onceki):
            return float("nan")
        bas_t, bas_v = onceki.index[-1], float(onceki.iloc[-1])
        n = (son - bas_t).days
        return float("nan") if n <= 0 else \
            100 * ((float(seri.iloc[-1]) / bas_v) ** (365 / n) - 1)

    for ad, s in (("yfinance ", a), ("chart ucu", b)):
        if s is None:
            continue
        temiz = s[s.index.dayofweek < 5]
        for gun, etiket in ((30, "1 aylık"), (90, "3 aylık")):
            x, y = hiz(s, gun), hiz(temiz, gun)
            print(f"  {ad} {etiket}: ham {x:.2f}% · hafta içi {y:.2f}% "
                  f"· fark {x - y:+.2f} puan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
