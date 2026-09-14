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


def cek(bas: dt.date) -> pd.Series:
    for ad, fn in (("yfinance", U._yfinance_cek), ("chart ucu", U._chart_cek)):
        try:
            s = fn(bas, BUGUN + dt.timedelta(days=1))
            print(f"  kaynak: {ad} · {len(s)} gözlem")
            return s
        except Exception as e:  # noqa: BLE001
            print(f"  {ad} düştü: {type(e).__name__}: {e}")
    raise SystemExit("ENGEL · iki uç da düştü — ölçüm yapılamadı")


def main() -> int:
    print("=" * 64)
    print(f"USD/TRY hafta sonu barı keşfi · {BUGUN}")
    print("=" * 64)

    # (0) HAM seri — yükleyicinin süzgeçlerinden GEÇMEDEN.
    print("\n[0] Ham seri (2015 →):")
    s = cek(dt.date(2015, 1, 1))
    print(f"  kapsam {s.index[0].date()} → {s.index[-1].date()}")

    # (1) Hafta sonu barlarının sayımı ve yıl dağılımı.
    hs = s[s.index.dayofweek >= 5]
    print(f"\n[1] Hafta sonu barı: {len(hs)} / {len(s)} "
          f"({100 * len(hs) / len(s):.2f}%)")
    if len(hs):
        yil = hs.groupby(hs.index.year).size()
        print("  yıla göre:", ", ".join(f"{y}:{n}" for y, n in yil.items()))
        gun = hs.groupby(hs.index.dayofweek).size()
        ad = {5: "Cmt", 6: "Paz"}
        print("  güne göre:", ", ".join(f"{ad[g]}:{n}" for g, n in gun.items()))
        print("  son 15:")
        for t, v in hs.tail(15).items():
            print(f"    {t.date()} {ad[t.dayofweek]}  {v:.4f}")

    # (2) Hafta sonu barı önceki iş gününün kapanışıyla AYNI mı?
    #     Aynıysa bayat tekrar; farklıysa gerçek bir kotasyon penceresi.
    print("\n[2] Hafta sonu barı önceki barla aynı mı:")
    if len(hs):
        ayni = fark = 0
        farklar = []
        for t in hs.index:
            onceki = s.loc[:t].iloc[:-1]
            if not len(onceki):
                continue
            o = float(onceki.iloc[-1])
            y = float(s.loc[t])
            if abs(y - o) < 1e-9:
                ayni += 1
            else:
                fark += 1
                farklar.append((t.date(), o, y, 100 * (y / o - 1)))
        print(f"  birebir aynı: {ayni} · farklı: {fark}")
        if farklar:
            fs = pd.Series([f[3] for f in farklar])
            print(f"  fark (%): medyan {fs.median():+.4f} · "
                  f"ortalama {fs.mean():+.4f} · azami |{fs.abs().max():.4f}|")
            print("  son 10 farklı:")
            for d, o, y, p in farklar[-10:]:
                print(f"    {d}  {o:.4f} → {y:.4f}  ({p:+.4f}%)")
    else:
        print("  hafta sonu barı yok")

    # (3) Tartışmanın kaynağı: 12.09.2026 barı ŞU AN duruyor mu?
    print("\n[3] 12.09.2026 (Cumartesi) barı:")
    hedef = pd.Timestamp("2026-09-12")
    print(f"  şu anki seride: {'VAR ' + format(float(s.loc[hedef]), '.4f') if hedef in s.index else 'YOK'}")
    print("  son 10 gün:")
    for t, v in s.tail(10).items():
        print(f"    {t.date()} {t.strftime('%a')}  {v:.4f}")

    # (4) ETKİ: hafta sonu barı yıllıklandırılmış hızı ne kadar oynatır?
    #     Sayfa 1 aylık ve 3 aylık devalüasyon hızını basıyor.
    print("\n[4] Hafta sonu barının yıllıklandırılmış hıza etkisi:")

    def hiz(seri: pd.Series, gun: int) -> float:
        if len(seri) < 2:
            return float("nan")
        son = seri.index[-1]
        hedef_gun = son - pd.Timedelta(days=gun)
        onceki = seri.loc[:hedef_gun]
        if not len(onceki):
            return float("nan")
        bas_t, bas_v = onceki.index[-1], float(onceki.iloc[-1])
        n = (son - bas_t).days
        if n <= 0:
            return float("nan")
        return 100 * ((float(seri.iloc[-1]) / bas_v) ** (365 / n) - 1)

    temiz = s[s.index.dayofweek < 5]
    for gun, ad2 in ((30, "1 aylık"), (90, "3 aylık")):
        a, b = hiz(s, gun), hiz(temiz, gun)
        print(f"  {ad2}: hafta sonu dahil {a:.2f}% · yalnız hafta içi {b:.2f}% "
              f"· fark {a - b:+.2f} puan")

    # (5) Süzgecin bedeli: hafta içi barı YANLIŞLIKLA düşürür mü?
    print("\n[5] Hafta içi kapsam (süzgeç konursa ne kaybedilir):")
    print(f"  hafta içi gözlem: {len(temiz)} · düşen: {len(s) - len(temiz)}")
    ilk, son = temiz.index[0].date(), temiz.index[-1].date()
    bekl = len(pd.bdate_range(ilk, son))
    print(f"  {ilk} → {son} arası iş günü {bekl}, elde {len(temiz)} "
          f"({100 * len(temiz) / bekl:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
