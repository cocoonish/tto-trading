# Bülten yazım rehberi

Bu dosya, günlük ve haftalık bülteni **yazan** katmanın görev tarifidir. Bültenin
ölçülen kısmı (piyasa fotoğrafı, takvim, göstergeler, hat hat değişim) otomatik
koşudan gelir ve yazan taraf ona **dokunmaz**. Yazan taraf dört alanı doldurur:
`yorum`, `ozet`, `gundem`.

Hedef kitle profesyonel trader. Jargon açıklanır ama seviye düşürülmez.

---

## Akış

1. **Bülteni oku.** `site/src/data/bulten/<bugün>.json`. İçinde ölçülmüş her şey
   var: 51 enstrümanlık piyasa fotoğrafı, TL faiz seti ve DİBS eğrisi, takvim,
   taranmış haberler (`haberler.kurum`, `haberler.haber`), kilit gelişmeler
   (`haberler.kilit`), izlenen temalar (`temalar`) ve hat hat değişim.
2. **Kilit gelişmeleri araştır.** `haberler.kilit` listesindeki her maddeyi ve
   `%1,5`'i aşan her fiyat hareketini kaynağına inerek anla. Manşete bakıp
   sebep uydurma; hareketin gerçek sürücüsünü bul.
3. **Yaz.** Aşağıdaki bölümleri doldur.
4. **Denetle.** `python3 bulten/denetim.py` — çıkış kodu 0 olana kadar düzelt.
   Denetim güven değil ölçüm içindir: "atladığımız bir şey var mı" sorusunun
   cevabını o verir.
5. **Kaydet.** Yamayı `python3 bulten/yaz.py yama.json` ile uygula.
6. **Yayınla.** `git add -A && git commit && git push`, sonra
   `python3 yayinla.py`.

---

## Doldurulacak alanlar

### `yorum` — "Günün / Haftanın okuması"
Bültenin tepesindeki okuma. Günlükte **en az 350**, haftalıkta **en az 600**
kelime. Günü tek bir teze bağla: ne oldu, neden oldu, ne değişti. HTML
paragraflar (`<p>…</p>`).

### `ozet`
- `ne_oldu` — geçmişe bakan özet (haftalıkta "geçen hafta").
- `ne_bekleniyor` — ileriye bakan özet (haftalıkta "önümüzdeki hafta").

### `gundem` — bölüm kimliği → HTML metin

Haber bölümleri, **her biri en az 200 kelime**:

| kimlik | içerik |
|---|---|
| `kilit` | Günün/haftanın kilit gelişmeleri, sürücü sırasıyla |
| `tr_makro` | Türkiye makro verisi ve TCMB |
| `tr_politika` | Türkiye politika ve düzenleme |
| `tr_piyasa` | BIST, TL faizler, DİBS, TL varlıklar |
| `global_makro` | Fed, ECB, ABD/AB verisi |
| `global_politika` | Jeopolitika, ticaret, seçim |
| `global_piyasa` | US/EU hisse, G10 FX, tahvil, emtia |
| `kurum_global` | Kurumsal duyurular (Hazine, IMF, merkez bankaları) |

Yazı bölümleri, **her biri en az 300 kelime**:

| kimlik | içerik |
|---|---|
| `faiz_fx_surucu` | Faiz ve döviz piyasasının sürücüleri |
| `emtia_surucu` | Emtia ve enerji: fiyat hareketinin sebebi (crack spread dahil) |
| `risk_firsat` | Riskler ve fırsatlar |
| `beklenti` | Yaklaşan veriler: beklentiler ve ne izlenmeli |

---

## Kurallar

**Atıf disiplini.** `%1,5`'i aşan her hareket metinde **anılmalı** ve sebebi
yazılmalı. Sebebi bilinmiyorsa "sebebi netleşmedi" yaz — en görünür manşeti
sürücü diye göstermek en kötü seçenek. (2026-08-17 haftasında ABD Hazinesi'nin
tahvil geri alımı USD ve faizlerdeki asıl sürücüydü ve bülten bunu tamamen
atlamıştı; `onem_puani` ve ABD Hazine kaynağı bu yüzden eklendi.)

**Kod dili yasak.** Okuyucuya hiçbir şey söylemeyen geliştirici dili sayfaya
girmez: dosya adı, alan adı, "hat koştu", "eşikler ayar.py içinde" gibi.
Denetim bunu ölçer ve engeller.

**Tavsiye dili yasak.** "Alın", "satın", "hedef fiyat", "pozisyon açın"
yazılmaz. Site analiz yayımlar, yatırım tavsiyesi vermez.

**Temalara bağla.** `temalar` defterindeki canlı temalara atıf yap: günün
gelişmesi hangi tezi doğruladı, hangisini çürüttü.

**Kıyas noktası.** Her sayının yanında neye göre değiştiği yazar: bir gün mü,
bir hafta mı, yıl başından beri mi.

**Tekrar.** Bin kelimede en fazla 7 ağır tekrar. Aynı cümleyi bölümden bölüme
taşıma.

**Beklenti halkası kapanıyor.** Bülten artık vakti geçmiş takvim olayları için
"ne bekleniyordu, ne geldi" bölümü basıyor. Üç kural:

- **Beklenti sütunu o gün yayımladığımız beklentidir.** `takvim_arsiv.json` her
  koşuda görülen takvim kaydının İLK hâlini saklar ve ezmez; sonradan
  güncellenmiş bir anketi geriye dönük yazmak, kendi çağrımızı düzeltmek olur.
- **Sürpriz yalnız sayısal beklenti varsa hesaplanır.** Serbest metin beklenti
  ("anket: yıl sonu %29,43 · 12 ay sonrası %23,69") sayıya ÇEVRİLMEZ; ayrıştırma
  tahmin üretir, tahminden hesaplanan sürpriz uydurma olur. Sayısal beklentin
  varsa takvim kaydının `beklenti_sayi` alanına yaz.
- **Gerçekleşme hattın kendi saatinden okunur.** Yayım anı ile verinin hatta
  düşmesi arasında saatler geçer; alanın veri tarihi olay gününden eskiyse bölüm
  "veri henüz hatta düşmedi" der. Elimizdeki eski sayıyı yeni yayım diye sunmak
  bu bölümün var oluş sebebine aykırıdır.

Bölüm otomatik dolar; yazan tarafın işi sürprizi METİNDE yorumlamaktır — tablo
ne olduğunu söyler, neden olduğunu söylemez.

**Söz defteri artık okura açık.** `izleme.json` bültenin JSON'una giriyor ve
sayfada "Söz defteri" bölümü olarak basılıyor: açık sözler vadeleriyle, yakın
zamanda kapananlar sonuçlarıyla. İki sonucu var. Birincisi, bir kaydın `soz` ve
`ne_bakilacak` alanları artık iç not değil **yayımlanan metindir** — okurun tek
başına anlayacağı şekilde yazılır. İkincisi, bir kaydı kapatırken `isabet`
alanı doldurulur:

| değer | ne zaman |
|---|---|
| `tuttu` | söz verilen beklenti gerçekleşti |
| `tutmadi` | gerçekleşmedi |
| `kismen` | yönü tuttu, büyüklüğü ya da zamanlaması tutmadı |

Alan boş bırakılırsa sayfa isabet oranını **vermez** — eksik veriyle övünmek
hesap vermenin tersidir. Ölçülemeyen kayıtlar (bir sorunun cevabının bulunması
gibi) notsuz kapatılabilir; denetim bunu uyarı olarak sayar, engel olarak değil.

**Sayıları uydurma.** Bültendeki her sayı ölçülen katmandan gelir. Ölçülmemiş
bir sayıya ihtiyaç varsa kaynağına in; hatırlayarak yazma.

Bu kural artık **ölçülüyor**. Denetim, ölçülen bir büyüklüğün adına yapışık her
sayıyı ölçülen katmanın tamamına karşı sınar ve karşılığı olmayanları listeler.
İşaret sözcükte taşınabilir ("%3,76 düşüşle" ile ölçülen −3,76 aynıdır),
yuvarlama serbesttir ("%36,9" ile 36,94 aynıdır), tarih ve süreler ("24
Ağustos", "52 haftalık") kapsam dışıdır. Liste **uyarıdır, engel değil**:
haberden gelen meşru bir sayının (bir eşik, bir tarife tutarı, ölçmediğimiz bir
alt endeks) ölçülen katmanda bulunmaması normaldir. Beklenen davranış listeye
bakıp her maddenin kaynağını doğrulamaktır — kalabalıksa büyük ihtimalle bir
şey ezberden yazılmıştır.
