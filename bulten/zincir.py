#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten zincirinin durumu — yazı katmanının sabah attığı ilk adım.

NEDEN VAR. Bülten üç halkalı bir zincir: veri tazeleme → ölçüm → yazı. İlk iki
halka GitHub'ın zamanlanmış tetikleyicisine bağlı ve o tetikleyici bu depoda
ÖLÇÜLEBİLİR biçimde güvenilmez:

  · Kayda geçen zamanlanmış koşuların tamamı 30–60 dakika gecikmeli başladı
    (08:47→09:24 · 13:17→14:06 · 15:37→16:36 UTC, 26.08.2026).
  · Sabah penceresindeki koşular hiç başlamadı: 26.08'de ölçüm, 27.08'de hem
    veri hem ölçüm. İkisinde de yazı katmanı ortada bülten bulamadı.

Zincirin en güvenilir halkası, GitHub'ın zamanlayıcısı değil, yazı katmanını
ateşleyen bulut rutinidir — o her sabah koşuyor. Öyleyse zinciri saat değil
RUTİN sürüklemeli: yazı katmanı önce durumu ölçer, eksik halkayı kendi
tetikler, sonra yazar.

Bu araç o ölçümü yapar. AĞA ÇIKMAZ, saniye sürer, hiçbir şeyi değiştirmez;
yalnız neyin eksik olduğunu ve hangi iş akışının tetikleneceğini söyler.

    python3 bulten/zincir.py

Çıkış kodu — yazı katmanı buna göre davranır:
    0  zincir tam: ölçüm bugünün, yazı bekleniyor → YAZ
    1  ölçüm eksik ya da dünden kalma → İŞ AKIŞLARINI TETİKLE, sonra yeniden bak
    2  bugünün bülteni zaten yazılmış → yapacak bir şey yok
    3  bugün hafta sonu (cumartesi) → bülten üretilmez
    4  YALNIZ PAZAR: haftalık bülten tamam ama TEKNİK ANALİZ bekliyor —
       ölçüm yoksa teknik.yml tetiklenir, varsa yorum yazılır (YAZIM.md,
       "Haftalık teknik analiz"). Pazar işi teknik yayımlanmadan bitmez.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTENLER = KOK / "site" / "src" / "data" / "bulten"
TEKNIKLER = KOK / "site" / "src" / "data" / "teknik"

# Yazı katmanının elle tetiklemesi gereken iş akışları, ZİNCİR SIRASINDA.
# Adlar iş akışı dosyalarının adıdır; tetikleme GitHub arayüzünden ya da
# depo araçlarından yapılır (yazı katmanının oturumunda ağ kapalı olabilir,
# bu yüzden burada tetikleme YAPILMAZ — yalnız ne tetikleneceği söylenir).
ZINCIR = [("veri.yml", "Veri tazeleme"), ("bulten.yml", "Günlük bülten")]

# Veri koşusu nabzı bu yaşı aşarsa ölçüm katmanı bayat sayılır.
NABIZ_SAAT = 12


def _yaz(bayrak: str, metin: str) -> None:
    print(f"  {bayrak} {metin}")


def durum(bugun: dt.date | None = None) -> tuple[int, list[str]]:
    """(çıkış kodu, yapılacaklar) — hiçbir şeyi değiştirmez.

    ÇIKIŞ KODU SÖZLEŞMESİ DEĞİŞMEZ (0/1/2/3/4). Aşağıdaki ek bloklar SALT
    OKUNURDUR: sayı basar, karar vermez, kodu etkilemez. Rutin bu aracı her
    sabah ilk iş koşuyor ve GitHub'a hiç bağlı olmayan tek kanal onun kendi
    bildirimi — 04.09'da araç doğru çalıştı, kod 1 döndürdü, rutin eksik halkayı
    tetikledi, ama elinde SAYI yoktu ve bildirimi de sayısız kaldı.
    """
    bugun = bugun or dt.date.today()
    kod, yapilacak = _zincir_durumu(bugun)
    _ek_bloklar(bugun)
    return kod, yapilacak


def _zincir_durumu(bugun: dt.date) -> tuple[int, list[str]]:
    yapilacak: list[str] = []

    print("═" * 66)
    print(f"  BÜLTEN ZİNCİRİ · {bugun.isoformat()} "
          f"({['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'][bugun.weekday()]})")
    print("═" * 66)

    if bugun.weekday() == 5:
        _yaz("·", "Cumartesi — bülten üretilmez.")
        return 3, []

    # ── halka 3: bugünün bülteni ne durumda
    dosya = BULTENLER / f"{bugun.isoformat()}.json"
    b: dict = {}
    if dosya.exists():
        try:
            b = json.loads(dosya.read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            b = {}

    if not dosya.exists() or not b:
        _yaz("✗", f"ÖLÇÜM YOK — {dosya.name} bulunamadı.")
        yapilacak.append("bulten.yml (Günlük bülten) tetiklenmeli")
    else:
        if b.get("gundem_kaynagi") == "yazili":
            _yaz("✓", f"Bülten YAZILMIŞ (ölçüm damgası {b.get('olusturma') or '—'}).")
            piyasa = len((b.get("piyasa") or {}).get("gruplar") or [])
            _yaz("·", f"piyasa fotoğrafı {piyasa} grup · "
                      f"gündem {len(b.get('gundem') or {})} bölüm")
            # PAZAR: bülten bitti diye iş bitmedi — teknik analiz de pazar işi.
            if bugun.weekday() == 6:
                t_kod, t_yapilacak = _teknik_durum(bugun)
                if t_kod:
                    print()
                    print("  HAFTALIK BÜLTEN TAMAM — TEKNİK ANALİZ BEKLİYOR:")
                    for i, adim in enumerate(t_yapilacak, 1):
                        print(f"    {i}. {adim}")
                    return 4, t_yapilacak
            print()
            print("  Yapacak bir şey yok.")
            return 2, []
        _yaz("✓", f"Ölçüm hazır — damga {b.get('olusturma') or '—'}.")

    # ── ölçümün kendisi sağlam mı: boş fotoğrafla üretilmiş olabilir
    if b:
        p = b.get("piyasa") or {}
        n_grup = len(p.get("gruplar") or [])
        n_haber = len((b.get("haberler") or {}).get("haber") or [])
        if n_grup == 0 or n_haber == 0:
            _yaz("✗", f"ÖLÇÜM SAKAT — piyasa {n_grup} grup, haber {n_haber} madde. "
                      "Ağsız bir ortamda üretilmiş olabilir.")
            yapilacak.append("bulten.yml (Günlük bülten) YENİDEN tetiklenmeli "
                             "— mevcut dosya boş ölçüyle üretilmiş")
        else:
            _yaz("✓", f"Ölçüm dolu — piyasa {n_grup} grup, haber {n_haber} madde.")

    # ── halka 1: veri iş akışı nabzı
    nabiz = BURASI / "kosu_nabzi.json"
    if not nabiz.exists():
        _yaz("!", "Veri koşusu nabzı yok — veri hattının koşup koşmadığı bilinmiyor.")
    else:
        try:
            d = json.loads(nabiz.read_text(encoding="utf-8"))
            t = dt.datetime.fromisoformat(
                str(d.get("veri_kosusu", "")).replace("Z", "+00:00"))
            yas = (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600
            sonuc = d.get("sonuc", "?")
            if yas > NABIZ_SAAT or sonuc != "success":
                _yaz("✗", f"Veri koşusu {yas:.1f} saat önce ({sonuc}).")
                yapilacak.insert(0, "veri.yml (Veri tazeleme) tetiklenmeli "
                                    "— ölçümden ÖNCE")
            else:
                _yaz("✓", f"Veri koşusu {yas:.1f} saat önce ({sonuc}).")
        except Exception:                                      # noqa: BLE001
            _yaz("!", "Veri koşusu nabzı okunamadı.")

    print()
    if not yapilacak:
        print("  Zincir tam. Bülteni oku, damgasını al ve YAZ.")
        return 0, []

    print("  EKSİK HALKA VAR — yazmadan önce tetikle:")
    for i, adim in enumerate(yapilacak, 1):
        print(f"    {i}. {adim}")
    print()
    print("  Tetikleme yazı katmanının oturumunda ELLE yapılır: iş akışını")
    print("  workflow_dispatch ile başlat, koşunun commit'ini bekle, `git pull`")
    print("  ile al, sonra bu aracı yeniden koştur. Bülteni YEREL üretmeye")
    print("  çalışma — yazı katmanının oturumunda piyasa ve haber uçları")
    print("  kapalıdır ve boş ölçüyle bir bülten üretilir (bkz. YAZIM.md).")
    return 1, yapilacak


# ── ek bloklar: SALT OKUNUR ──────────────────────────────────────────────────
#
# Üçü de yalnız SAYI basar. Hiçbiri çıkış kodunu değiştirmez, hiçbiri bir kapı
# değildir ve üçü de try/except içindedir: bu bloklardaki bir kusur zincirin
# okunmasını düşürmemeli. Bu halka KOLAYLIK, sigorta değil — rutin bu satırlara
# hiç bakmasa da gecikme ölçüsü deftere yazılır ve alarm iş akışı e-postayı
# gönderir.

def _ek_bloklar(bugun: dt.date) -> None:
    for ad, fn in (("gecikme", _gecikme_blogu), ("tema", _tema_blogu),
                   ("atlanan", _atlanan_blogu)):
        try:
            fn(bugun)
        except Exception as e:                                 # noqa: BLE001
            _yaz("!", f"{ad} bloğu okunamadı ({e.__class__.__name__}) — "
                      "zincir durumu bundan etkilenmez.")


def _gecikme_blogu(bugun: dt.date) -> None:
    """Okura verilen SÖZ ile gerçekleşen yan yana.

    04.09.2026'ya kadar bu karşılaştırma hiçbir yerde yapılmıyordu: sitenin
    ilanı (`yayin_takvimi.json`) ve gerçekleşen anlar (bültenin kendi
    damgaları) aynı depoda duruyordu ve ikisini yan yana koyan tek satır kod
    yoktu. Ölçünün tanımı burada DEĞİL, `bulten/gecikme.py`de.
    """
    sys.path.insert(0, str(BURASI))
    import gecikme

    satirlar = gecikme.olc(KOK, bugun)
    if not satirlar:
        return
    print()
    print("  YAYIN SÖZÜ:")
    simdi = dt.datetime.now(dt.timezone.utc)
    for s in satirlar:
        soz = dt.datetime.fromisoformat(s["soz"])
        soz_ist = (soz + dt.timedelta(hours=gecikme.TR_SAAT)).strftime("%H:%M")
        simdi_ist = (simdi + dt.timedelta(hours=gecikme.TR_SAAT)).strftime("%H:%M")
        dk = gecikme._sayi(abs(s["gecikme_dk"]))
        if s["sinif"] == "zamaninda":
            durum_metni = (f"söz {soz_ist}'e {dk} dakika var"
                           if s["henuz_yazilmadi"] else f"söz {dk} dakika ile tutuldu")
            _yaz("✓", f"{s['yayin']}: {durum_metni}.")
            continue
        nasil = "söz geçeli" if s["henuz_yazilmadi"] else "gecikme"
        _yaz("✗" if s["sinif"] == "alarm" else "!",
             f"SÖZ RİSK ALTINDA — {s['yayin']}: hedef {soz_ist}, şu an "
             f"{simdi_ist}, {nasil} {dk} dakika (pay {s['pay_dk']} dk)"
             + (f", darboğaz {s['darbogaz']}" if s["darbogaz"] else "") + ".")
        _yaz(" ", "  Bildirimde 'gecikti' değil DAKİKA ve darboğaz halka yaz.")


def _tema_blogu(bugun: dt.date) -> None:
    """Tema defteri ölçümden YENİ mi — 0. adımda sorulur, yazı sırasında değil.

    Tema bölümü bültene ÖLÇÜM anında işlenir; defteri sonradan güncellemek
    sayfayı düzeltmez, ölçümün yeniden kurulması gerekir. 04.09'da bu yazı
    sırasında fark edildi ve ölçüm İKİ KEZ yeniden kuruldu (05:34 ve 05:39,
    ~11 dakika). Aynı soru burada sorulursa tek kurulum yeter.
    """
    dosya = BULTENLER / f"{bugun.isoformat()}.json"
    defter_yolu = BURASI / "temalar.json"
    if not dosya.exists() or not defter_yolu.exists():
        return
    b = json.loads(dosya.read_text(encoding="utf-8"))
    defter = json.loads(defter_yolu.read_text(encoding="utf-8"))
    gomulu = {x.get("ad"): x for x in ((b.get("temalar") or {}).get("temalar") or [])}
    ayrisan = []
    for x in (defter.get("temalar") or []):
        g = gomulu.get(x.get("ad"))
        if g is None:
            ayrisan.append(f"{x.get('ad')} (ölçümde hiç yok)")
            continue
        for alan in ("gelisme", "son_gozlem", "durum", "izlenecek_gosterge"):
            if str(x.get(alan, "")) != str(g.get(alan, "")):
                ayrisan.append(f"{x.get('ad')} ({alan})")
                break
    print()
    if not ayrisan:
        _yaz("✓", "Tema görüntüsü defterle aynı.")
        return
    _yaz("✗", "TEMA DEFTERİ ÖLÇÜMDEN YENİ: " + ", ".join(ayrisan[:4]) + ".")
    _yaz(" ", "  Defteri düzeltmek sayfayı düzeltmez. Defteri ŞİMDİ tamamla, "
              "sonra bulten.yml'i --yeniden-olc ile tetikle, sonra yaz —")
    _yaz(" ", "  yazarken fark edilirse ölçüm ikinci kez kurulur ve bülten "
              "o kadar geç çıkar.")


def _atlanan_blogu(bugun: dt.date) -> None:
    """Son veri koşusunda bir hat atlandıysa yazarın önüne konur.

    Alan bugün BOŞ: koşacak hatları bütçeyle kesen adım henüz yok. Blok yine
    de duruyor çünkü okuması bedava ve alan dolduğu gün kendiliğinden görünür
    olması, o gün birinin hatırlamasına bel bağlamaktan güvenli.
    """
    sys.path.insert(0, str(BURASI))
    import nabiz

    d = nabiz.oku(nabiz.yol(BURASI))
    kosular = [k for k in (d.get("kosular") or []) if isinstance(k, dict)]
    if not kosular:
        return
    son = kosular[-1]
    atlanan = son.get("atlanan_butce") or []
    if not atlanan:
        return
    print()
    _yaz("!", "Son veri koşusunda atlanan hatlar: " + ", ".join(map(str, atlanan)))
    _yaz(" ", "  Bu hatların sayısı dünkü sürümde; günün haberini onların "
              "üstüne kurma, kullanacaksan kendi tarihiyle kullan.")


def _teknik_durum(bugun: dt.date) -> tuple[int, list[str]]:
    """Pazar teknik analiz halkası: (0 tamam, 1 iş var), yapılacaklar.

    Rutin metnine güvenilmez (bkz. CLAUDE.md, sigorta araca konur): pazar
    rutini teknik bülteni unutamasın diye durum BURADA, rutinin her pazar
    zaten koşturduğu araçta raporlanır. Nöbetçinin pazar koşusu aynı soruyu
    yayının son kapısında bağımsız sorar.
    """
    dosya = TEKNIKLER / f"{bugun.isoformat()}.json"
    if not dosya.exists():
        _yaz("✗", f"TEKNİK ÖLÇÜM YOK — {dosya.name} bulunamadı.")
        return 1, ["teknik.yml (Haftalık teknik analiz) tetiklenmeli, commit'i "
                   "beklenip `git pull` ile alınmalı",
                   "sonra yorum yazılmalı: YAZIM.md → 'Haftalık teknik analiz'"]
    try:
        t = json.loads(dosya.read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        _yaz("✗", "TEKNİK ÖLÇÜM OKUNAMADI — dosya bozuk.")
        return 1, ["teknik.yml yeniden tetiklenmeli (yeniden_olc=true)"]
    if t.get("yazili"):
        _yaz("✓", f"Teknik analiz YAZILMIŞ (damga {t.get('olcum_zamani') or '—'}).")
        return 0, []
    _yaz("✗", f"Teknik ölçüm hazır (damga {t.get('olcum_zamani') or '—'}) "
              "ama YORUM YAZILMAMIŞ.")
    return 1, ["yorum yazılmalı: YAZIM.md → 'Haftalık teknik analiz' "
               "(teknik/yaz.py, --damga ile)"]


def main() -> int:
    kod, _ = durum()
    return kod


if __name__ == "__main__":
    sys.exit(main())
