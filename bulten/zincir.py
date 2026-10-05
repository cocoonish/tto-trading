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

Kod 4 (pazar teknik analiz halkası) 01.10.2026'da KALDIRILDI: haftalık teknik
analiz bülteni 27.09.2026 sayısıyla sona erdi (kullanıcı kararı) ve pazar işi
yalnız haftaya bakıştır. Numara yeniden kullanılmaz — eski bir talimatın 4'ü
başka bir anlamla karşılamaması için.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTENLER = KOK / "site" / "src" / "data" / "bulten"

# Yazı katmanının elle tetiklemesi gereken iş akışları, ZİNCİR SIRASINDA.
# Adlar iş akışı dosyalarının adıdır; tetikleme GitHub arayüzünden ya da
# depo araçlarından yapılır (yazı katmanının oturumunda ağ kapalı olabilir,
# bu yüzden burada tetikleme YAPILMAZ — yalnız ne tetikleneceği söylenir).
ZINCIR = [("veri.yml", "Veri tazeleme"), ("bulten.yml", "Günlük bülten")]

# VERİ KOŞUSU BÜLTEN GÜNÜNE AİT OLMALI. Eski ölçüt yaştı ("12 saatten yeni
# mi") ve 02.10.2026'da yanlış cevap verdi: önceki akşamın 20:28 UTC koşusu
# sabah 04:18'de 7,8 saatlikti, halka "tamam" dedi, veri tazelenmedi ve kur
# hattı 30.09'da kaldı — o koşu UTC gece yarısından ÖNCEYDİ, yani bülten
# gününün sabahına ait hiçbir yayımı (gece biten seanslar, sabah verileri)
# göremezdi. Soru yaş değil SIRADIR: veri koşusu bülten gününün UTC gece
# yarısından sonra mı koştu, ve ölçüm ondan sonra mı kuruldu.
def _veri_esigi(bugun: dt.date) -> dt.datetime:
    return dt.datetime.combine(bugun, dt.time(0, 0), tzinfo=dt.timezone.utc)


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
            if t.tzinfo is None:
                t = t.replace(tzinfo=dt.timezone.utc)
            yas = (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600
            sonuc = d.get("sonuc", "?")
            esik = _veri_esigi(bugun)
            olcum = None
            if b.get("olusturma"):
                try:
                    olcum = dt.datetime.fromisoformat(str(b["olusturma"]).replace("Z", "+00:00"))
                    # Dilimsiz damga UTC'dir; dilimli ile kıyaslanınca TypeError
                    # verir, istisna yutulur ve zincir sessizce "tam" derdi.
                    if olcum.tzinfo is None:
                        olcum = olcum.replace(tzinfo=dt.timezone.utc)
                except ValueError:
                    olcum = None
            if t < esik or sonuc != "success":
                neden = (f"bülten gününün UTC gece yarısından önce ({yas:.1f} saat önce)"
                         if t < esik else f"sonucu {sonuc}")
                _yaz("✗", f"Veri koşusu bu güne ait değil — {neden}.")
                yapilacak.insert(0, "veri.yml (Veri tazeleme) tetiklenmeli "
                                    "— ölçümden ÖNCE")
                if b:
                    yapilacak.append("bulten.yml (Günlük bülten) YENİDEN tetiklenmeli "
                                     "— mevcut ölçüm tazelenmemiş veriyle kuruldu")
            elif olcum is not None and olcum < t:
                _yaz("✗", f"Ölçüm veri koşusundan ÖNCE kurulmuş (ölçüm {b['olusturma']}, "
                          f"veri {d.get('veri_kosusu')}).")
                yapilacak.append("bulten.yml (Günlük bülten) YENİDEN tetiklenmeli "
                                 "— veri ölçümden sonra tazelendi")
            else:
                _yaz("✓", f"Veri koşusu bu güne ait — {yas:.1f} saat önce ({sonuc}).")
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
                   ("atlanan", _atlanan_blogu), ("fikir", _fikir_blogu)):
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


def _fikir_blogu(bugun: dt.date) -> None:
    """İşlem fikri kararını yazarın İLK gördüğü ekrana koyar.

    05.10.2026'da ilk biçim 3 günlük sayısı fikirsiz yayımlandı: rutin metni
    "yaz.py yalnız yorum/ozet/gundem alanlarına yazmana izin verir" diyordu,
    rehber fikri isteğe bağlı sayıyordu ve denetimin "fikir yok" satırı
    basılmıyordu. Rutin metnini bir aracı değiştiremez (27.08 ilkesi); bu blok
    yazarın sabah koşturduğu ilk araçta eski talimatı adıyla anar ve 05.10
    kararını ("her sayıda en az bir fikir; gerekçesi görünmeyen ya da
    ölçülemeyen fikir açılmaz") yazarın önüne koyar. Yalnız yazılmamış biçim 3
    sayıda basılır; kodu etkilemez.
    """
    dosya = BULTENLER / f"{bugun.isoformat()}.json"
    if not dosya.exists():
        return
    b = json.loads(dosya.read_text(encoding="utf-8"))
    if int(b.get("surum") or 2) < 3 or b.get("gundem_kaynagi") == "yazili":
        return
    kayitlar = [k for k in ((b.get("fikir_karne") or {}).get("kayitlar") or [])
                if isinstance(k, dict) and k.get("durum") in ("acik", "olculemez")]
    print()
    print("  İŞLEM FİKİRLERİ:")
    if kayitlar:
        _yaz("·", f"Açık fikir {len(kayitlar)} (karne): görüşü bozulan için `fikir_kapat`.")
        for k in kayitlar[:12]:
            ek = "ölçülemez" if k.get("durum") == "olculemez" else (
                "giriş bekleniyor" if k.get("giris_bekleniyor") else "açık")
            _yaz(" ", f"  {k.get('kimlik')} · {str(k.get('baslik') or '')[:60]} "
                      f"({ek}, ufuk {k.get('ufuk') or '—'})")
    else:
        _yaz("·", "Açık fikir yok.")
    if b.get("haftalik"):
        _yaz("!", "Haftalık sayı 3–6 fikir taşır: en az iki varlık sınıfında, her biri "
                  "bir senaryoya bağlı.")
    else:
        _yaz("!", "Her sayıda en az bir fikir beklenir (1–3, `fikirler`).")
    _yaz(" ", "  Gerekçesi bugünkü veride görünmeyen fikir açılmaz; ölçülemeyen fikir "
              "açılmaz (`--evren`).")
    _yaz(" ", "  Rutin metnindeki 'yalnız yorum/ozet/gundem' cümlesi eskidir — rehber "
              "esastır (YAZIM.md › İşlem fikirleri).")


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


def main() -> int:
    kod, _ = durum()
    return kod


if __name__ == "__main__":
    sys.exit(main())
