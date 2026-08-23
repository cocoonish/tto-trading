#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — siteyi yayına gönder (public depo → GitHub Pages).

Bu depo PRIVATE'tır ve öyle kalır: veri hatları, Research/ altındaki masa
dokümanları ve git geçmişi burada durur. Yayınlanan tek şey `site/` klasörüdür;
o da ayrı bir PUBLIC depoya kopyalanır (varsayılan: cocoonish.github.io) ve
oradaki GitHub Actions iş akışı derleyip Pages'e koyar.

  python yayinla.py                     # derle → kopyala → commit → push
  python yayinla.py -m "SMC dersi güncellendi"
  python yayinla.py --derleme-yok       # yerel derlemeyi atla (CI yine derler)
  python yayinla.py --kuru              # hiçbir şey yazma/gönderme, ne olacağını göster
  python yayinla.py --denetle           # yalnız denetle: npm, git, kimlik, uzak depo
  python yayinla.py --depo kullanici/repo --klon /yol/klon

Neden kopyalama: iki depo ayrı kalsın diye. Public depoda yalnız sitenin
kaynağı ve tek doğrusal geçmiş bulunur; bu depodaki commit geçmişi (eski
anahtar, özel kontrol görselleri) oraya HİÇ gitmez.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
SITE = KOK / "site"
VARSAYILAN_DEPO = "cocoonish/cocoonish.github.io"
VARSAYILAN_KLON = KOK.parent / "TTO Trading Yayin"
YAYIN_URL = "https://cocoonish.github.io/"

# site/ içinden kopyalanmayacaklar (üretilmiş ya da yerel)
HARIC = {"node_modules", "dist", ".astro", ".DS_Store"}
# Public depoda korunacak, kaynaktan gelmeyecek dosyalar
KORUNAN = {".git", ".github", "README.md", ".gitignore", "CNAME"}

ANAHTAR_KALIBI = re.compile(
    r"^\+.*(KEY|TOKEN|SECRET|PASSWORD|APIKEY)\s*[=:]\s*[\"'][A-Za-z0-9_\-]{8,}",
    re.MULTILINE)

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _renk(m, k):
    return f"\033[{k}m{m}\033[0m" if sys.stdout.isatty() else m


def kos(komut, cwd=None, sessiz=False):
    r = subprocess.run(komut, cwd=cwd, capture_output=sessiz, text=True,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r


def npm_yolu():
    for ad in ("npm.cmd", "npm") if os.name == "nt" else ("npm",):
        y = shutil.which(ad)
        if y:
            return y
    return None


def git_var() -> bool:
    return shutil.which("git") is not None


def git_kimlik() -> str | None:
    """Ad/e-posta ayarlı değilse commit sessizce düşer; sorunu ÖNCE söyle."""
    ad = kos(["git", "config", "user.name"], sessiz=True).stdout.strip()
    posta = kos(["git", "config", "user.email"], sessiz=True).stdout.strip()
    if ad and posta:
        return None
    return ('git kimliği ayarlı değil — commit yapılamaz. Çözüm:\n'
            '      git config --global user.name "Adınız"\n'
            '      git config --global user.email "eposta@ornek.com"')


def uzak_erisim(depo: str) -> str | None:
    """Public depoya erişilebiliyor mu? (klonlama/push saatler sonra patlamasın.)"""
    r = subprocess.run(["git", "ls-remote", "--exit-code", "-h",
                        f"https://github.com/{depo}.git"],
                       capture_output=True, text=True, timeout=60,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if r.returncode == 0:
        return None
    return (f"{depo} deposuna erişilemedi (ağ ya da yetki). "
            f"git çıktısı: {(r.stderr or '').strip().splitlines()[-1] if r.stderr.strip() else '?'}")


def denetle(depo: str, klon: Path) -> int:
    """Hiçbir şey göndermeden 'yayın patlar mı?' der."""
    print("\n▶ Ön denetim")
    engel = []
    npm = npm_yolu()
    print(f"  npm        {'✓ ' + npm if npm else 'yok — yerel derleme atlanır (CI derler)'}")
    print(f"  node_modules {'✓' if (SITE / 'node_modules').exists() else 'yok — npm install koşacak'}")
    if not git_var():
        print(_renk("  git        YOK", 31)); engel.append("git kurulu değil")
    else:
        print("  git        ✓")
        k = git_kimlik()
        print("  kimlik     " + ("✓" if not k else _renk("YOK", 31)))
        if k:
            engel.append(k)
        try:
            u = uzak_erisim(depo)
        except Exception as ex:
            u = f"{depo} denetlenemedi ({type(ex).__name__})"
        print(f"  uzak depo  {'✓ ' + depo if not u else _renk(u, 31)}")
        if u:
            engel.append(u)
    print(f"  klon       {'✓ ' + str(klon) if (klon / '.git').exists() else 'yok — klonlanacak'}")
    for e in engel:
        print(_renk(f"  ✗ {e}", 31))
    return 1 if engel else 0


def derle() -> bool:
    """Yerelde derle — CI'da patlamasın diye ÖNCE burada görelim."""
    npm = npm_yolu()
    if not npm:
        print(_renk("  [uyarı] npm yok, yerel derleme atlandı (CI yine derleyecek)", 33))
        return True
    if not (SITE / "node_modules").exists():
        print("  npm install…")
        if kos([npm, "install"], cwd=SITE).returncode != 0:
            return False
    print("  npm run build…")
    return kos([npm, "run", "build"], cwd=SITE).returncode == 0


def klonu_hazirla(depo: str, klon: Path, kuru: bool) -> bool:
    if (klon / ".git").exists():
        print(f"  klon mevcut: {klon}")
        if not kuru:
            # Çıkış kodu ESKİDEN yok sayılıyordu: pull çakışırsa hata ancak push
            # aşamasında, anlaşılmaz biçimde ortaya çıkıyordu.
            r = kos(["git", "pull", "--rebase", "--autostash"], cwd=klon, sessiz=True)
            if r.returncode != 0:
                print(_renk("  ✗ klon güncellenemedi (git pull --rebase düştü).", 31))
                print((r.stderr or r.stdout or "").strip()[-500:])
                print(f"  Çözüm: klonu silip yeniden oluşturun →  rm -rf \"{klon}\"")
                return False
        return True
    if kuru:
        print(f"  (kuru) klonlanacaktı: {depo} → {klon}")
        return True
    print(f"  klonlanıyor: {depo} → {klon}")
    klon.parent.mkdir(parents=True, exist_ok=True)
    r = kos(["git", "clone", f"https://github.com/{depo}.git", str(klon)])
    if r.returncode != 0:
        print(_renk(f"  ✗ klonlanamadı. Public depo var mı? "
                    f"(gh repo create {depo.split('/')[-1]} --public …)", 31))
        return False
    return True


def kopyala(klon: Path, kuru: bool) -> int:
    """site/ → klon. KORUNAN dosyalara dokunulmaz; artık dosyalar silinir."""
    n = 0
    kaynaklar = [p for p in SITE.iterdir() if p.name not in HARIC]
    for p in kaynaklar:
        hedef = klon / p.name
        if kuru:
            n += 1
            continue
        if p.is_dir():
            if hedef.exists():
                shutil.rmtree(hedef)
            shutil.copytree(p, hedef, ignore=shutil.ignore_patterns(*HARIC))
        else:
            shutil.copy2(p, hedef)
        n += 1
    # kaynakta olmayan ama klonda duran fazlalıklar (KORUNAN hariç)
    adlar = {p.name for p in kaynaklar} | KORUNAN
    if not klon.exists():          # kuru koşuda klon henüz yok
        return n
    for p in klon.iterdir():
        if p.name not in adlar:
            print(f"    - fazlalık siliniyor: {p.name}")
            if not kuru:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    return n


def site_url_yaz(klon: Path, url: str, kuru: bool):
    """astro.config'teki site: alanını yayın adresine sabitle (sitemap için)."""
    p = klon / "astro.config.mjs"
    if not p.exists():
        return
    s = p.read_text(encoding="utf-8")
    yeni = re.sub(r"site:\s*'[^']*'", f"site: '{url.rstrip('/')}'", s, count=1)
    if yeni != s and not kuru:
        p.write_text(yeni, encoding="utf-8")
        print(f"    astro.config site: {url.rstrip('/')}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-m", "--mesaj", default="site: içerik ve grafik güncellemesi")
    ap.add_argument("--depo", default=VARSAYILAN_DEPO)
    ap.add_argument("--klon", type=Path, default=VARSAYILAN_KLON)
    ap.add_argument("--derleme-yok", action="store_true")
    ap.add_argument("--kuru", action="store_true", help="hiçbir şey yazma/gönderme")
    ap.add_argument("--denetle", action="store_true",
                    help="yalnız ortamı denetle (npm, git, kimlik, uzak depo) ve çık")
    a = ap.parse_args()

    print(f"{'═' * 66}\n  Siteyi yayına gönder → {a.depo}\n{'═' * 66}")
    if a.kuru:
        print(_renk("  KURU KOŞU — dosya yazılmaz, push yapılmaz\n", 36))

    if a.denetle:
        return denetle(a.depo, a.klon)
    # Gönderime başlamadan önce sessiz denetim: derleme dakikalar sürüyor,
    # kimlik/erişim sorununu ondan SONRA öğrenmek zaman kaybı.
    if not a.kuru and git_var():
        k = git_kimlik()
        if k:
            print(_renk(f"  ✗ {k}", 31))
            return 1

    if not a.derleme_yok:
        print("\n▶ Yerel derleme (CI'dakiyle aynı)")
        if not derle():
            print(_renk("  ✗ derleme düştü — yayın durduruldu", 31))
            return 1
        print(_renk("  ✓ derleme tamam", 32))

    print("\n▶ Public depo klonu")
    if not klonu_hazirla(a.depo, a.klon, a.kuru):
        return 1

    print("\n▶ site/ kopyalanıyor")
    n = kopyala(a.klon, a.kuru)
    site_url_yaz(a.klon, YAYIN_URL, a.kuru)
    print(f"  {n} öğe")

    if a.kuru:
        print("\n  (kuru koşu bitti)")
        return 0

    print("\n▶ Commit + push")
    kos(["git", "add", "-A"], cwd=a.klon)
    diff = subprocess.run(["git", "diff", "--cached"], cwd=a.klon,
                          capture_output=True, text=True).stdout
    if ANAHTAR_KALIBI.search(diff):
        print(_renk("  ✗ DURDU: eklenen satırlarda gömülü kimlik bilgisi kalıbı var.", 31))
        for satir in ANAHTAR_KALIBI.findall(diff)[:3]:
            print(f"      {satir}")
        kos(["git", "reset", "-q"], cwd=a.klon)
        return 1
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=a.klon).returncode == 0:
        print("  değişiklik yok — yayın gerekmiyor")
        return 0
    r = kos(["git", "commit", "-q", "-m", a.mesaj], cwd=a.klon, sessiz=True)
    if r.returncode != 0:
        print(_renk("  ✗ commit düştü", 31))
        print((r.stderr or r.stdout or "").strip()[-500:])
        k = git_kimlik()
        if k:
            print(_renk(f"  {k}", 33))
        return 1
    if kos(["git", "push"], cwd=a.klon).returncode != 0:
        # En sık sebep: depo başka bir yerden ilerlemiş. Bir kez rebase'leyip dene.
        print(_renk("  push reddedildi — rebase ile bir kez daha deneniyor", 33))
        if kos(["git", "pull", "--rebase", "--autostash"], cwd=a.klon).returncode != 0 \
                or kos(["git", "push"], cwd=a.klon).returncode != 0:
            print(_renk("  ✗ push başarısız", 31))
            print(f"  Elle: cd \"{a.klon}\" && git pull --rebase && git push")
            return 1

    print(_renk("\n  ✓ Gönderildi. GitHub Actions derleyip yayınlıyor (~2 dk).", 32))
    print(f"    site   : {YAYIN_URL}")
    print(f"    akışlar: https://github.com/{a.depo}/actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
