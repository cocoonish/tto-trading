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


def yenile_istendi() -> bool:
    """Bu koşuda önbellek atlanacak mı (elle tetiklenmiş tazeleme)."""
    return (os.environ.get(YENILE_DEGISKENI) or "").strip() in DOGRU


def taze(yol: str | os.PathLike[str] | Path, ttl_saat: float) -> bool:
    """Önbellek dosyası hâlâ kullanılabilir mi.

    Yoksa taze değildir; TTO_YENILE verilmişse hiçbir dosya taze değildir."""
    if yenile_istendi():
        return False
    y = Path(yol)
    if not y.exists():
        return False
    return (dt.datetime.now().timestamp() - y.stat().st_mtime) / 3600 < ttl_saat


def yas_gun(yol: str | os.PathLike[str] | Path) -> float:
    """Dosyanın gün cinsinden yaşı (uyarı metinleri buradan yazar)."""
    return (dt.datetime.now().timestamp() - Path(yol).stat().st_mtime) / 86400
