# Proje panosu yazım rehberi

Bu dosya, `site/src/content/projeler/` altındaki **proje panolarının** görev
tarifidir — analizin `analiz/YAZIM.md`si neyse panonun bu. Pano bir yazı değil
bir ÖLÇÜM YÜZEYİDİR: kendi kaynağından beslenir, kendi ritminde tazelenir ve
her sayı kendi tarihini taşır. Metin kısa, sayılar canlı, şekillerin hesabı
anlatılmış olmalıdır.

Rehber esastır; kural buraya yazılır ve araca konur. Ölçülebilen her kural
`site/tools/sayfa_sinavi.py`de bir ölçüttür (1, 2, 2c, 11, 11b, 11c, 11d, 12, 17).

---

## Başlık

**Cümle düzeni.** İlk sözcük büyük, kalanlar küçük; özel adlar ve kısaltmalar
korunur (TCMB, TL, TÜFEX, DİBS, REDK, USD/TRY, GSYH). `&` yazılmaz, `ve`
yazılır. Ör. `TCMB net rezerv takibi`, `Yabancı pozisyonu: DİBS ve hisse
akımları`. Liste sayfasında ve ana sayfa tablosunda on yedi başlık alt alta
durur; iki üslup yan yana yayın kimliğini bozar. Sınav: `&` engel, Başlık
Düzeni uyarı (11b). **Gövdedeki bağlantı metni de sayfanın başlığını
taşır** (`<a href="/projeler/enflasyon/">Enflasyon panosu</a>`); slug'ın kendisi
("kredi-parasal") okura gitmez, "Kredi hattının" gibi açıklayıcı küçük harfli
metin serbesttir (11c, uyarı).

## Ön bilgi (frontmatter)

| alan | zorunlu | ne yazılır |
|---|---|---|
| `title` | evet | yukarıdaki kural |
| `description` | evet | 1–3 cümle, ne ölçüldüğü; **elle sayılmış sayı yok** ("13 grafik", "17 şekil" — şekil eklendiği gün eskir; künye sayar) |
| `pubDate` / `updatedDate` | evet / metin değişince | metnin tarihi; verinin tarihi ayrıdır ve şeritte görünür |
| `tags` | evet | küçük harf |
| `durum` | evet | `aktif` · `taslak` · `arsiv` |
| `kaynak` | evet — şema ve 11d engel | **okur adıyla** ("TCMB EVDS", "TÜİK"); seri kodları gövdedeki Kaynaklar bölümüne, kod biçiminde |
| `guncelleme` | evet — şema ve 11d engel | yayım ritmi, küçük harfle başlar; kaynağın yayım saati biliniyorsa parantezde yazılır: `her iş günü (TCMB gösterge kuru, 15:30)`, `aylık (TÜİK, ayın 3'ü 10:00)`; bilinmiyorsa ritim tek başına yeter (`aylık`); şekil numarası geçmez |

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
   dosyadan gelir; elle özet yazılmaz. **Uyarı satırları okura gider**, yani
   hattın Python'u onları okur dilinde yazar: kod/anahtar adı, grup kodu,
   backtick, ondalık nokta, ISO tarih yok (`ortak/okur_dili.kosu_kaydi_tara`;
   `guncelle.py` hat koşarken uyarır; sınav 17'de kod ve yapım dili engel,
   anahtar adı ve biçim uyarı). Sayı `ortak/bicim`den yazılır. Aynı kural `ozet.json`un
   CÜMLE olan her metin alanı için geçerli (`okur_dili.ozet_cumleleri`: boşluk
   içeren ve 40 karakterden uzun her metin değeri) — hepsi `<Deger>` ile sayfaya
   basılabilir, kapsam bir alan listesinden değil bu sözleşmeden türer.
5. **Kaynaklar** — seri kodları kod biçiminde (`TP.AB.A02`), yayım takvimi.

## Şeklin tarihi: hattın saati değil, ŞEKLİN saati

Her şeklin altında "veri <tarih>" yazar. Varsayılan, hattın ana saatidir
(`_tarih`) — ve bir hattın bütün figürleri aynı saatte DEĞİLSE bu yalan olur.
Üç basamak, sırayla:

1. MDX'te açık `tarihAnahtari="<anahtar>"` — yazarın kararı, kazanır.
2. Hattın **şekil saat defteri**: `ozet.json`'daki `_sekil_tarih` sözlüğü
   (`{"rejim.html": "2026-08-30", …}`), figürü ÇİZEN kod tarafından yazılır.
   Değer `null` ise "bu figürün ucu ölçülmedi" demektir ve tarih hiç basılmaz —
   yanlış bir tarih, tarihsizlikten kötüdür.
3. Hiçbiri yoksa `_tarih`.

Defter açan hatta sınav (18) girdi eksiğini UYARI, yarından ileri ya da
çözülemeyen tarihi ENGEL sayar. Ölçüldü: FX haber endeksinde GDELT panelleri
dört gün eskiyken "bugün" diye damgalanıyordu ve okur bunu tersinden okuyup
TAZE endeksi bayat sanıyordu.

**Karma figürde damga BAĞLAYICI, yani EN ESKİ bacaktır.** Bir figür iki seriyi
yan yana koyuyorsa sözü onların KIYASIDIR ve kıyas ancak ikisinin de ölçüldüğü
güne kadar kurulabilir; en taze bacağı yazmak öbürünü olduğundan yeni gösterir.
`min()` yapısal yazılır, bugünkü sıralamaya bakmaz — besleme sırası değişince
damga kendiliğinden öbür bacağa döner.

**Bacaklar birbirinden çok uzaksa damga İKİSİNİ birden yazabilir:**
`"aylık 30.06.2026 · haftalık 26.08.2026"`. Bileşen tanımadığı dizgeyi olduğu
gibi basar; sınav (18b) içindeki her tarihi ayrı ayrı sınar. Bu yol yalnız açık
anahtarla kullanılır — defterde çözülebilir tek bir tarih ya da `null` durur.
Ne zaman birleşik, ne zaman en eski: bacaklar aynı olguyu farklı ritimde
ölçüyorsa (ödemeler dengesi Şekil 12'de eurobond akımı aylık, ödeme takvimi
haftalık; aralarında 57 gün) tek gün hangi bacağı seçerse seçsin öbürü hakkında
yanıltıcı olur — birleşik yaz. Aynı ritimde olup biri bir–iki gün geriden
geliyorsa (TLREF kurun bir gün gerisinde) en eskisini yaz.

**Bir tarih AY ise ay yazılır.** Aylık gözlem dönemin ilk gününe damgalanır ve
onu `01.07.2026` diye yazmak okura o GÜNÜN ölçümü gibi görünür; `07.2026` yaz —
`ortak/bicim` ve `lib/bicim` ikisini de çözer, `AA.YYYY` ayın son gününe
demirlenir. `2026-Ç1` gibi bir dizge hiçbir tarafta ÇÖZÜLMEZ, anahtar olarak
kullanılamaz.

**Aynı figüre iki ilan konabilir ama çelişemez.** Açık anahtar ile defter
girdisi birlikte durursa bu bir güvenlik payıdır (defter bir gün yazılmazsa
sayfa yine doğru günü basar); ayrıştıkları gün figürün kendi alt başlığı ile
sayfadaki damga farklı tarih söyler — sınav (18c) bunu ENGEL sayar.

**Figürün İÇİNDEKİ tarih de okura görünür.** Alt yazıdaki "Çıpa: …" ile sayfa
damgası aynı kaynaktan gelmelidir; hat, figür saatlerini TEK bir fonksiyonda
tutup hem çizim koduna hem özet üreticisine oradan versin (`Kredi/veri.py`
içindeki `sekil_saatleri` kalıbı). İki ayrı liste bir gün sessizce ayrışır.

## Uydurma sayılarla örnek kutusu

Bir kutunun bütün sayıları formülü göstermek için SEÇİLMİŞSE (gerçek gözlem
değilse), kutu tarama dışına alınır:

```
{/* sinav-ornek: bu kutunun bütün sayıları uydurma — <gerekçe> */}
… kutu …
{/* /sinav-ornek */}
```

Gerekçe zorunlu, kapanış zorunlu (kapanmayan blok sınavı DÜŞÜRÜR — yoksa
sayfanın kalanı sessizce taramadan çıkardı). Anahtar bazlı `sinav-muaf`
yalnız TEK bir tarihsel alıntı için; bir kutunun tamamı için kullanılmaz,
çünkü o anahtarı sayfanın TAMAMINDA kör eder ve bir sonraki tesadüf için
hiçbir şey yapmaz. Ölçüldü: aynı kutu iki kez çarpıştı, ikincisi yayını
on iki saat durdurdu.

## Sayılar ve dil

- Türkçe yazım tek yerden (`lib/bicim`): ondalık virgül, binlik nokta, eksi
  U+2212, yüzde önde ("%1,48"), baz puan sonda ("−6,5 bp").
- Okura yazılır, yapıma değil: dosya adı, anahtar adı ve sürüm anlatısı
  ("ilk sürümde şöyleydi") sayfaya girmez (`ortak/okur_dili.py`; sınav 9 içerik
  dosyalarında engel, 9b derlenmiş çıktıda uyarı, 17 koşu kaydında engel).
  "Koşu" ve "veri tarihi" okura verilen kayıt adlarıdır ve şeritte/kutuda
  geçer; yasak olan koşunun İÇ adlarıdır (dosya, anahtar, grup kodu).
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
