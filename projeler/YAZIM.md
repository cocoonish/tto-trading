# Proje panosu yazım rehberi

Bu dosya, `site/src/content/projeler/` altındaki **proje panolarının** görev
tarifidir — analizin `analiz/YAZIM.md`si neyse panonun bu. Pano bir yazı değil
bir ÖLÇÜM YÜZEYİDİR: kendi kaynağından beslenir, kendi ritminde tazelenir ve
her sayı kendi tarihini taşır. Metin kısa, sayılar canlı, şekillerin hesabı
anlatılmış olmalıdır.

Rehber esastır; kural buraya yazılır ve araca konur. Ölçülebilen her kural
`site/tools/sayfa_sinavi.py`de bir ölçüttür (1, 2, 11, 11b, 12).

---

## Başlık

**Cümle düzeni.** İlk sözcük büyük, kalanlar küçük; özel adlar ve kısaltmalar
korunur (TCMB, TL, TÜFEX, DİBS, REDK, USD/TRY, GSYH). `&` yazılmaz, `ve`
yazılır. Ör. `TCMB net rezerv takibi`, `Yabancı pozisyonu: DİBS ve hisse
akımları`. Liste sayfasında ve ana sayfa tablosunda on yedi başlık alt alta
durur; iki üslup yan yana yayın kimliğini bozar. Sınav: `&` engel, Başlık
Düzeni uyarı (11b).

## Ön bilgi (frontmatter)

| alan | zorunlu | ne yazılır |
|---|---|---|
| `title` | evet | yukarıdaki kural |
| `description` | evet | 1–3 cümle, ne ölçüldüğü; **elle sayılmış sayı yok** ("13 grafik", "17 şekil" — şekil eklendiği gün eskir; künye sayar) |
| `pubDate` / `updatedDate` | evet / metin değişince | metnin tarihi; verinin tarihi ayrıdır ve şeritte görünür |
| `tags` | evet | küçük harf |
| `durum` | evet | `aktif` · `taslak` · `arsiv` |
| `kaynak` | evet | **okur adıyla** ("TCMB EVDS", "TÜİK"); seri kodları gövdedeki Kaynaklar bölümüne, kod biçiminde |
| `guncelleme` | evet | yayım ritmi, küçük harfle başlar, parantezde kaynak ve saat: `her iş günü (TCMB gösterge kuru, 15:30)`, `aylık (TÜİK, ayın 3'ü 10:00)`; şekil numarası geçmez |

## Gövde

1. **Veri durumu şeridi kendiliğinden gelir** (`VeriDurumu`): manşet büyüklüğü,
   hattın son verisi, bayatlık hükmü, son koşunun uyarı sayısı. Şerit
   `lib/anaSayfa.ts`teki HAT_MANSET girdisinden okur; yeni panoya girdi
   eklenmeden sınav düşer (11).
2. **Güncel okuma** — sayfanın ilk bölümü; her oynak sayı `<Deger proje
   anahtar>` ile yazılır, yedek metin derleme günündeki değerdir. Tarihsel ve
   yöntemsel sabitler statik kalır (`{/* sinav-muaf: … */}`).
3. **Şekiller** — `<GrafikEmbed>`; altyazıda veri tarihi kendiliğinden yazılır
   (hattın saati); şeklin serisi başka ritimdeyse `tarihAnahtari` verilir. Her
   şeklin altında "bu seri nasıl hesaplanıyor": kaynak, formül, dönüşüm,
   varsayım.
4. **Koşu kutusu** (isteğe bağlı, `KosuKutusu`): son koşunun uyarı listesi
   dosyadan gelir; elle özet yazılmaz.
5. **Kaynaklar** — seri kodları kod biçiminde (`TP.AB.A02`), yayım takvimi.

## Sayılar ve dil

- Türkçe yazım tek yerden (`lib/bicim`): ondalık virgül, binlik nokta, eksi
  U+2212, yüzde önde ("%1,48"), baz puan sonda ("−6,5 bp").
- Okura yazılır, yapıma değil: dosya adı, anahtar adı, "hat koştu" sayfaya
  girmez (`ortak/okur_dili.py`, sınav 9).
- Tavsiye dili yok; senaryo dili.
- Uydurma yok: ölçülmeyen değer boş bırakılır, sebebi yazılır.

## Hat tarafı (sayfanın beslendiği yer)

- Hat `guncelle.py` kütüğündedir (`Hat(...)`): adımlar, kopya sözleşmesi
  (sitede gömülü HER dosya), tarih anahtarları. Kütük dışı hat, kapıların
  hiçbirinden geçmez.
- `ozet.json` sözleşmesi: `_tarih` hattın en yeni CANLI bacağının günü
  (`GG.AA.YYYY` · `AA.YYYY` · ISO); her oynak anahtarın kendi `<anahtar>_tarih`i;
  bayatlık hükmü `bayat: true/false` ya da `tazelik: 'güncel'|'bayat'` —
  alan yoksa şerit "bayatlık ölçülmüyor" yazar, "hat çalışıyor" yazmaz.
  Sınav 12 `_tarih`i çözer ve yarından ileri olmadığını sınar.
- Hattın çıktısı `site/public/projeler/<slug>/` altına kopyalanır; Plotly
  HTML'leri `site/tools/plotly_stil.py` ile ev stiline geçer.
