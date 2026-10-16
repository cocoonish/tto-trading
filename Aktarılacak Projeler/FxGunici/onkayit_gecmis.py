# -*- coding: utf-8 -*-
"""Ön kaydın BEKLENEN git geçmişi ve ilk sonuçların görüldüğü commit — tek tanım. Ölçüm (ders_olcum) depodan okuduğu
geçmişi bununla kıyaslar ve ayrışırsa yazılmaz; kapı (dogrula.py) ölçüm dosyasının taşıdığı geçmişi bununla kıyaslar.

Geçmiş yeniden yazılırsa (rebase, amend, zorla push) commit ya da işleyen saati değişir; ön kayda yeni bir commit
eklenirse liste uzar. İkisinde de metodoloji dersinin "ön kayıt bu kayıtlardan ibarettir" cümlesi bir beyan olmaktan
çıkardı. Ön kayda bilerek yeni bir kayıt eklenirse (ayrı commit, gerekçesiyle) bu liste de bir sonraki değişiklikte
uzatılır. Yalnız standart kütüphane: kapı yayın koşucusunda da koşar.
"""

#: (commit, işleyen saati, ayrıştırılmış içeriğin özü) — ders_olcum.onkayit_gecmisi ile aynı biçim.
BEKLENEN = (
    ("a985e126", "2026-10-16T08:29:06+00:00", "b766ce8e94f6fcc48474fa5d7ba19aa3370be9c1a6c6149d594e66d12afe9eff"),
    ("d001aeeb", "2026-10-16T08:55:50+00:00", "7eb7be76e7ac8bc79f69a4c2c556eb3fda0b559f6fb79908a3d999c0c9bfcfc9"),
    ("a7d4b1a5", "2026-10-16T10:28:36+00:00", "7eb7be76e7ac8bc79f69a4c2c556eb3fda0b559f6fb79908a3d999c0c9bfcfc9"),
    ("38694c3b", "2026-10-16T20:48:02+00:00", "7eb7be76e7ac8bc79f69a4c2c556eb3fda0b559f6fb79908a3d999c0c9bfcfc9"),
)

#: İlk sonuçların görüldüğü commit: koşu çıktısını okuyan ilk kod (ders ölçümü ve figürler) bu commit'tedir. Ön kaydın
#: İÇERİĞİNİ değiştiren her commit onun atası olmalıdır (sonuçlardan önce); sonraki kayıtlar yalnız yorum değiştirebilir.
ILK_SONUC = ("8aa94c7e", "2026-10-16T10:23:57+00:00")


def denetle(gecmis: list[dict] | None) -> list[str]:
    """Ölçülen geçmiş beklenenle aynı mı ve içerik değiştiren her kayıt sonuçlardan önce mi (`sonuctan_once`)."""
    if not gecmis:
        return ["ön kaydın geçmişi ölçülemedi (git geçmişi eksik)"]
    hata = []
    olcu = [(g.get("commit"), g.get("zaman"), g.get("icerik_ozu")) for g in gecmis]
    if olcu != [tuple(x) for x in BEKLENEN]:
        hata.append("ön kaydın geçmişi beklenen geçmişle aynı değil: "
                    + ", ".join(f"{c} {t}" for c, t, _ in olcu) + " ↔ beklenen "
                    + ", ".join(f"{c} {t}" for c, t, _ in BEKLENEN))
    for g in gecmis:
        if g.get("degisen_bolum") and g.get("sonuctan_once") is not True:
            hata.append(f"ön kaydın içeriğini değiştiren {g.get('commit')} ilk sonuçlardan ({ILK_SONUC[0]}) önce değil")
    return hata
