# Bülten yazım rehberi

Bu dosya, günlük ve haftalık bülteni **yazan** katmanın görev tarifidir. Bültenin
ölçülen kısmı (piyasa fotoğrafı, takvim, göstergeler, hat hat değişim) otomatik
koşudan gelir ve yazan taraf ona **dokunmaz**. Yazan taraf dört alanı doldurur:
`yorum`, `ozet`, `gundem`.

Hedef kitle profesyonel trader. Jargon açıklanır ama seviye düşürülmez.

---

## Akış

1. **Bülteni oku ve damgasını not al.** `site/src/data/bulten/<bugün>.json`.
   İçinde ölçülmüş her şey var: 51 enstrümanlık piyasa fotoğrafı, TL faiz seti
   ve DİBS eğrisi, takvim, taranmış haberler (`haberler.kurum`,
   `haberler.haber`), kilit gelişmeler (`haberler.kilit`), izlenen temalar
   (`temalar`), rejim panosu (`rejim`), olağandışılık sıralaması
   (`piyasa.en_cok_hareket.sigma`), söz defteri (`izleme`), "ne bekleniyordu,
   ne geldi" (`sonuclar`) ve hat hat değişim. **`olusturma` alanını hemen
   kaydet** — yamayı uygularken bu damgayı vereceksin; ölçüm sen yazarken
   yenilenirse yama reddedilir ve metni güncel ölçüye göre gözden geçirirsin
   (26.08.2026'da bu kaza gerçekten oldu: yazı 04:31'de yazıldı, ölçüm 05:01'de
   yeniden kuruldu, sayfa ölçülmeyen sayıları anlattı).
2. **Kilit gelişmeleri araştır.** `haberler.kilit` listesindeki her maddeyi,
   `%1,5`'i aşan her fiyat hareketini VE `piyasa.en_cok_hareket.sigma`
   listesinde **2σ'yı aşan** her hareketi kaynağına inerek anla. İki eşik
   farklı soruları yakalar: yüzde eşiği büyük hareketi, σ eşiği olağandışı
   hareketi. Yüzdesi küçük diye 2σ'lık bir hareketi atlama — 26.08'de günün
   asıl haberi (kredi endekslerinin 1,6σ'lık ortak hareketi) ham listede hiç
   görünmüyordu. Manşete bakıp sebep uydurma; hareketin gerçek sürücüsünü bul.
3. **Yaz.** Aşağıdaki bölümleri doldur.
4. **Denetle.** `python3 bulten/denetim.py` — çıkış kodu 0 olana kadar düzelt.
   Denetim güven değil ölçüm içindir: "atladığımız bir şey var mı" sorusunun
   cevabını o verir.
5. **Kaydet.** Yamayı `python3 bulten/yaz.py yama.json --damga "<okuduğun
   olusturma>"` ile uygula. Damga tutmazsa uygulama reddedilir: bülteni yeniden
   oku, sayıları güncel ölçüye karşı gözden geçir, yeni damgayla tekrar dene.
6. **Push et — YAYINLAMA.** `git add -A && git commit -m "bülten: <tarih>
   yazı katmanı" && git pull --rebase --autostash && git push`. Push'tan sonrası
   senin işin değil: ayrı bir iş akışı siteyi public depoya çıkarır. `yayinla.py`
   ELLE ÇAĞRILMAZ — public depoya yazma yetkisi bulut iş akışında duruyor,
   yazı katmanının oturumunda yok; çağırmak boşuna hataya çıkar.
   (Bu satır eskiden "sonra `python3 yayinla.py`" diyordu ve rutinin metniyle
   çelişiyordu. Rutin "rehbere birebir uy" dediği için çelişki rehberin
   aleyhineydi.)

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

## Haftalık bültene özgü görevler

Pazar günkü "haftaya bakış" günlük akışın üstüne üç iş ekler:

1. **Haftanın karnesi.** Hafta içinde kapanan TÜM izleme kayıtlarını gözden
   geçir: notsuz kapanmış olan varsa `isabet` notunu düş ya da neden
   ölçülemez olduğunu kayda yaz. Haftalık yorum, karnenin o haftaki dökümünü
   bir paragrafla verir — kaç çağrı tuttu, kaçı tutmadı, en öğretici yanılgı
   hangisiydi. Okur haftalık bültende hesap görmek ister.
2. **Kıyas penceresi haftalıktır.** "Geçen hafta bu saatte neredeydik" sorusu
   günlük "son yayımdan bu yana"dan farklıdır; haftalık değişim kolonlarını
   (`h1`) ve rejim panosunun hafta içindeki yönünü kullan. Bir günlük gürültüyü
   haftanın hikâyesi yapma.
3. **Önümüzdeki haftanın her takvim maddesi `beklenti` bölümünde tek tek
   işlenir** ve sayısal beklentisi olan her madde için takvim kaydının
   `beklenti_sayi` alanının dolu olduğunu doğrula — sürpriz ölçümü ancak o
   alanla çalışır; serbest metinden sayı türetilmez.

## Rutin nerede duruyor — ve neden bu rehber esas

Yazı katmanını her sabah bir bulut görevi (claude.ai Routine) ateşliyor. O
görevin metni **depoda değil**, hesabın rutin ayarlarında duruyor. Bunun iki
sonucu var ve ikisi de bu rehberin biçimini belirliyor:

**Rehber esastır, rutin metni yalnız işaret.** Rutin metni "önce
`bulten/YAZIM.md` oku, rehbere birebir uy" diyor. İkisi çelişirse rehber
kazanır — çünkü rehber depoda, sürüm geçmişiyle ve denetimle birlikte yaşıyor;
rutin metni ise ayrı bir arayüzde durur, kimse ona bakmaz ve sessizce eskir.
Yeni bir kural koyulacaksa **buraya** yazılır.

**Mekanik sigortalar rutin metnine değil, DEPODAKİ ARAÇLARA konur.** Rutin
metni bir aracı eski biçimiyle çağırırsa sigorta sessizce devre dışı kalır —
26.08 kazası tam buradan çıktı. Ama sigortayı "eksikse düş" diye kurmak da
yanlış olur: bu sefer de rutin, kendi metnini düzeltemediği için her sabah
düşer. Doğrusu, sigortanın açık argüman olmadan da SÜRMESİ.

`yaz.py` bunu iki kademede yapıyor:

- `--damga <okuduğun olusturma>` verilirse damga karşılaştırılır. Kesin ölçü,
  rehberin istediği budur.
- Verilmezse yama dosyasının değiştirilme zamanı taban sigorta olur: bültenin
  `olusturma` damgası yamadan sonraysa ölçüm yazı bittikten sonra yeniden
  kurulmuş demektir ve yama reddedilir. Aradaki dar pencereyi (bülteni okuma
  ile yamayı yazma arası) kaçırabilir, o yüzden taban olmaktan öteye geçmez.
- `--damgasiz` her ikisini de bilerek atlar.

Bir kuralı "rutin metnine yazdım" diye tamam sayma; araç onu kendi başına
dayatabiliyor mu, ona bak.

**Rutini bir aracı yeniden kuramaz.** Mevcut iki rutin (hafta içi 04:15 UTC,
pazar 14:45 UTC) hesabın arayüzünden oluşturuldu; aracının onları güncelleme ya
da silme yetkisi yok. Aracının kurduğu bir rutin ise depoya erişemez: yeni
oturuma depo bağlanmadığı için özel depo klonlanamaz. Yani rutin metnini
değiştirmenin tek yolu **claude.ai arayüzü**; oradan değiştirilecek bir şey
yoksa yeni kural buraya yazılır ve rutin onu okuyarak öğrenir.

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

**Rejim panosunu omurga yap.** `rejim` alanı günün "neredeyiz" cevabını dokuz
satırda verir (reel faiz ileri/geri, taşıma makası, reel kredi, REDK sapması,
eğri eğimi, **enflasyon risk primi**, **makroihtiyati ayrışma**, rezerv
kalitesi). Yorumun tezi bu satırların GERİLİMİNDEN kurulur: hangi ikisi
birbiriyle çelişiyor, hangisi önce kırılır. Panoyu sayı sayı kopyalama — sayfada
zaten duruyor; senin işin çelişkiyi cümleye çevirmek.

Panonun iki yeni satırı, geri kalanının SORAMADIĞI soruyu soruyor:

- **Enflasyon risk primi (2y)** — diğer satırlar politikanın ne kadar SIKI
  olduğunu ölçer; bu satır piyasanın o sıkılığın SONUCUNA inanıp inanmadığını.
  İkisi aynı anda birbirine zıt olabilir ve bültenin en verimli gerilimi orada:
  reel faiz tarihî yüksekliğinde dururken piyasa hedefin tutmayacağını
  fiyatlıyorsa, sıkılık henüz beklentiyi çevirmemiş demektir.
- **Makroihtiyati ayrışma** — "reel kredi büyümesi" toplamın ne yaptığını
  söyler; bu satır sınırın İÇİNDE kalanla DIŞINA taşan arasındaki farkı. Fark
  açıldıkça toplamdaki yavaşlama politikadan değil bileşim kaymasından geliyor
  olabilir; freni toplam kredi büyümesinden okumak yanıltır.

**Söz kapatırken not düş.** Bir izleme kaydını kapatıyorsan `isabet` alanını
doldur (tuttu | tutmadi | kismen); ölçülemeyen kayıtlar notsuz kapanabilir ama
bunu bilinçli seç. `sonuclar` bölümünde "geldi" görünen her satırın sürprizini
metinde yorumla — tablo ne olduğunu söyler, neden olduğunu sen söylersin.

**Temalara bağla.** `temalar` defterindeki canlı temalara atıf yap: günün
gelişmesi hangi tezi doğruladı, hangisini çürüttü.

**Kıyas noktası.** Her sayının yanında neye göre değiştiği yazar: bir gün mü,
bir hafta mı, yıl başından beri mi.

**Tekrar.** Bin kelimede en fazla 7 ağır tekrar. Aynı cümleyi bölümden bölüme
taşıma.

**Denetimin veri uyarılarını ciddiye al.** Denetim artık ölçüm katmanının
CANLILIĞINI de ölçüyor: veri iş akışı her koşuda nabzını atıyor ve denetim o
damganın yaşına bakıyor. İki uyarı doğrudan sana:

- *"Veri iş akışı N saattir koşmadı"* — ölçüm katmanı bayat olabilir. Yazmadan
  önce hatların veri tarihlerini (pano ve "hat hat değişim") gözden geçir;
  bayat bir hattın sayısını günün haberi gibi anlatma.
- *"Son veri koşusunun tazeleme adımı 'failure' ile bitti"* — bazı hatlar
  çekilememiş. Hangilerinin eski kaldığını veri tarihlerinden bul ve metinde
  o hatlara dayanan hüküm kurma.

Üçüncü uyarı seri düzeyinde:

- *"Hattın saati ilerlerken donmuş N seri"* — bir hattın ana tarihi her gün
  ilerlerken İÇİNDEKİ bir seri donmuş. Sayfada o değer hattın güncel tarihiyle
  aynı başlığın altında duruyor ama ait olduğu gün çok daha eski. Böyle bir
  sayıyı metne alacaksan **kendi tarihiyle** al ("12 Haziran'dan bu yana
  fiyatlanmayan üç yıllık nokta"), günün kesiti gibi değil.

  Bu uyarı yalnız SEBEBİ BİLİNMEYEN seriler için çıkar. Bir seriyi araştırıp
  sebebini bulduğunda ilgili proje sayfasına yaz ve `ayar.KARANLIK_BILINEN`e
  ekle; denetim onu bundan sonra sebebiyle birlikte geçen ölçüt olarak yazar.
  Susturmanın tek yolu önce anlamaktır — açıklaması olmayan hiçbir donuk seri
  listeden düşmez.

Bu uyarılar engel değildir — bayat veriyle de bülten yazılır, yeter ki bayatlık
BİLİNEREK yazılsın. 26.08'de veri hattı düştü ve aşağı akıştaki hiçbir katman
bunu bilemiyordu; bu ölçütler o boşluğu kapatıyor.

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

Bir istisna var ve onu bilerek kullanabilirsin: **geri alınan sayı**. Önceki
bir yayımın yanlış sayısını düzeltiyorsan "yayımlanan −%11,36 yerine gerçek
hareket −%1,74" biçiminde yaz — denetim `<yanlış> yerine <doğru>` kalıbını
tanıyor ve düzeltmenin doğrusu ölçülen katmanda bulunduğu sürece yanlış sayıyı
uyarıya çevirmiyor. Kalıbın dışına çıkarsan (araya cümle sınırı girerse ya da
düzeltilen değer de ölçülmemişse) uyarı geri gelir; bu kasıtlı.
