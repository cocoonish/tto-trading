"""Seri önbelleğinin tazelik sözleşmesi — TEK tanım.

Her EVDS hattı ham yanıtı `data/cache/*.csv`e yazar ve dosyayı belli bir süre
(bugün sekiz hatta 12 saat, marj hattında 24) taze sayar. Önbellek gerekli:
önbelleksiz koşucuda kredi hattı 869 saniye sürüyor.

Ama bir TTL, YAYIM GÜNÜNDE yanlış konuşur ve bunu `veri.yml`in kendi yorumu
adıyla yazıyordu: "Sabah koşmuş bir tazeleme, yayımdan SONRA koşana eski
dosyayı verir ve hat 'veri değişmedi' diyerek yeşil biter." Önlem olarak elle
tetiklenen koşuya `TTO_YENILE=1` kondu.

O önlem ÖLÇÜLDÜ (07.09.2026) ve dokuz hattın SEKİZİNDE karşılığı yoktu:
değişkeni yalnız Enflasyon okuyordu, yani "takvimi dinleme, koşulsuz tazele"
düğmesi kalan sekiz hat için önbelleği hiç atlamıyordu. Kusurun görüntüsü ile
sağlığın görüntüsü aynı: koşu yeşil biter, hat "veri değişmedi" der, sayfa
dünkü sayıda durur.

Kural bu yüzden hatların dosyasında değil burada durur; hatların `_taze`si
buraya devreder ve `bulten/duman.py` devretmeyeni ENGEL sayar. Kapsam bir
listeden değil sözleşmeden türetilir: dosyada TTL'li bir önbellek varsa
tazelik kararı buradan geçmelidir.

DIŞARIDA KALAN, adıyla: `Aktarılacak Projeler/indices` (FX haber endeksi)
canlı haber akışını saniye cinsinden bir saatlik önbellekte tutuyor. O hat
`veri.yml`de değil `fx.yml`de koşuyor, tetiği bir yayım takvimi değil haber
akışının kendisi ve TTO_YENILE oraya hiç geçmiyor — sözleşme onu bağlamaz.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

# Ortam değişkeninin adı TEK yerde. `veri.yml` "zorla" girdisinde bunu export
# ediyor; iki tarafın ayrı dizge tutması, bir gün sessizce ayrışmaları demek.
YENILE_DEGISKENI = "TTO_YENILE"
DOGRU = ("1", "true", "True", "TRUE", "evet")
# KOŞUNUN BAŞLANGIÇ ANI (epoch saniye; guncelle.py hat başlarken yazar).
# "Koşulsuz tazele" bir KOŞU için söylenir, her ADIM için değil: marj hattı
# beş adımdan oluşur ve beşi de aynı 39 EVDS serisini okur. TTO_YENILE tek
# başına her adımda önbelleği atlatıyor, yani zorlanmış bir koşu aynı seriyi
# beş kez indiriyordu (09.09.2026'da ölçüldü: yerelde her adım "EVDS
# erişilemedi" satırlarını baştan yazdı). Bu anın ARDINDAN yazılmış dosya bu
# koşunun kendi indirmesidir ve tazedir.
KOSU_BASLANGIC_DEGISKENI = "TTO_KOSU_BASLANGIC"


def yenile_istendi() -> bool:
    """Bu koşuda önbellek atlanacak mı (elle tetiklenmiş tazeleme)."""
    return (os.environ.get(YENILE_DEGISKENI) or "").strip() in DOGRU


def taze(yol: str | os.PathLike[str] | Path, ttl_saat: float) -> bool:
    """Önbellek dosyası hâlâ kullanılabilir mi.

    Yoksa taze değildir; TTO_YENILE verilmişse yalnız BU KOŞUDA yazılmış dosya
    tazedir (bkz. KOSU_BASLANGIC_DEGISKENI) — önceki koşulardan kalan hiçbiri."""
    y = Path(yol)
    if not y.exists():
        return False
    if yenile_istendi():
        return _bu_kosuda_yazildi(y)
    return (dt.datetime.now().timestamp() - y.stat().st_mtime) / 3600 < ttl_saat


def kosu_baslangici() -> float | None:
    """Bu koşunun başlangıç anı (epoch sn); guncelle.py dışından koşulunca yok."""
    ham = (os.environ.get(KOSU_BASLANGIC_DEGISKENI) or "").strip()
    try:
        return float(ham) if ham else None
    except ValueError:
        return None


def _bu_kosuda_yazildi(y: Path) -> bool:
    """Dosya bu koşunun başlangıcından SONRA yazıldıysa, bu koşunun indirmesidir."""
    bas = kosu_baslangici()
    return bas is not None and y.stat().st_mtime >= bas


def yas_gun(yol: str | os.PathLike[str] | Path) -> float:
    """Dosyanın gün cinsinden yaşı (uyarı metinleri buradan yazar)."""
    return (dt.datetime.now().timestamp() - Path(yol).stat().st_mtime) / 86400
