# Bülten yazım rehberi

Bu dosya, günlük ve haftalık bülteni **yazan** katmanın görev tarifidir. Bültenin
ölçülen kısmı (piyasa fotoğrafı, takvim, göstergeler, hat hat değişim) otomatik
koşudan gelir ve yazan taraf ona **dokunmaz**. Yazan taraf dört alanı doldurur:
`yorum`, `ozet`, `gundem` ve — yalnız yayımlanmış bir sayı düzeltiliyorsa —
`duzeltmeler`.

Hedef kitle profesyonel trader. Jargon açıklanır ama seviye düşürülmez.

---

## Akış

0. **Önce zincire bak: `python3 bulten/zincir.py`.** Tek komut, ağsız, saniye
   sürer. Bülten üç halkalı bir zincirdir — veri tazeleme → ölçüm → yazı — ve
   ilk iki halka GitHub'ın zamanlanmış tetikleyicisine bağlıdır. O tetikleyici
   bu depoda ölçülebilir biçimde güvenilmez: kayda geçen zamanlanmış koşuların
   TAMAMI 30–60 dakika gecikmeli başladı, sabah penceresindekiler ise hiç
   başlamadı (26.08'de ölçüm, 27.08'de hem veri hem ölçüm). Araç ne eksikse
   söyler ve çıkış koduyla ne yapacağını bildirir:

   | kod | anlamı | yapılacak |
   |---|---|---|
   | 0 | ölçüm hazır, yazı bekleniyor | 1. adımdan devam et |
   | 1 | ölçüm yok / boş ölçüyle üretilmiş / veri bayat | **iş akışlarını tetikle** (aşağı bak) |
   | 2 | bugünün bülteni zaten yazılmış | yapacak bir şey yok |
   | 3 | cumartesi | bülten üretilmez |
   | 4 | yalnız pazar: haftalık bülten tamam, teknik analiz bekliyor | "Haftalık teknik analiz" bölümüne geç |

   **Kod 1 ise: bülteni YEREL ÜRETMEYE ÇALIŞMA.** Rutin metni "dosya yoksa
   `python3 bulten.py --tur gunluk` ile üret" diyor; bu, yazı katmanının koştuğu
   bulut oturumunda İŞLEMİYOR. Oturumun ağ politikası piyasa ve haber uçlarını
   kapatıyor — yfinance, bütün RSS kaynakları ve resmî yayım siteleri CONNECT
   aşamasında 403 dönüyor. 27.08.2026'da denendi: 0 enstrümanlık piyasa
   fotoğrafı, 0 haber, 15 engel. Üstelik deneme kirlilik de bırakıyor (piyasa
   önbelleği ve takvim arşivi boş veriyle üzerine yazılıyor); commit'ten önce o
   dosyaları geri al.

   Doğrusu ölçümü ağı ve anahtarları olan yerde koşturmak. Sırayla:
   **`veri.yml` (Veri tazeleme)** → koşunun commit'ini bekle → **`bulten.yml`
   (Günlük bülten)** → commit'ini bekle → `git pull` → `zincir.py`yi yeniden
   koştur. Kod 0 olunca yaz. 27.08'de böyle yapıldı ve bülten zamanında çıktı.

   **AYNI KAPALI AĞ, DENETİMİN BİR UYARISINI SAHTE YAPIYOR — onu arıza sanma.**
   Yazı katmanının oturumunda `bulten/denetim.py` (ve `bulten/tazeleme.py`)
   "yayım takvimi okunamadı — 18 hattın TAMAMI kör koşu listesinde" der. Bu bir
   depo kusuru DEĞİL, bu oturumun kapalı ağının izidir: tazeleme takvimi ağdan
   çözülüyor, çözülemeyince araç güvenli tarafa düşüp her hattı "kör koşu"
   sayıyor. 11.09.2026'da ölçüldü — aynı gün aynı ölçüt BULUTTA koştu ve takvimi
   sorunsuz okudu; oradaki gerçek uyarı çok daha dar çıktı ("bugün tazelenmesi
   gereken ama tazelenemeyen hatlar: USD/TRY devalüasyon hızı, DİBS verim
   eğrisi"). Yani yerelde ölçüt 18 hattı birden şişiriyor, bulutta iki hattı
   adıyla veriyor. **Hangi hattın bugün bayat olduğunu yerelden değil,
   `bulten.yml` koşusunun kaydından oku**; yerel liste hiçbir şey söylemiyor.
   Bunu bildirime "arıza" diye yazmak, ölçülmemiş bir şeyi ölçülmüş gibi
   göstermenin bir biçimi olur — bu depoda bir kez yapıldı ve commit mesajına
   geçti.

   **Zinciri saat değil RUTİN sürükler.** Zincirin en güvenilir halkası
   GitHub'ın zamanlayıcısı değil, seni ateşleyen bulut rutinidir — o her sabah
   koşuyor. Zamanlanmış koşular koşarsa işini azaltır; koşmazsa eksik halkayı
   sen tamamlarsın. Bu bir istisna değil, tasarımın kendisi.

   **Eksik halka bulursan BİLDİR.** Depodaki nöbetçi (`nobetci.yml`) bülten
   çıkmadığında iş akışını düşürüp e-posta gönderiyor — ama o da bir GitHub
   cron'u, yani aynı zamanlayıcının insafında. Zamanlayıcı topluca düşerse
   alarmı da düşer. GitHub'a hiç bağlı olmayan tek kanal senin bildirimin.
   Bu yüzden zinciri elle tamamladığın her sabah bunu bildirimde YAZ: hangi
   halka düştü, ne tetiklendi, bülten kaçta çıktı. Sessizce onarmak, arızayı
   görünmez kılar — ve bu zincirin asıl kusuru zaten görünmez olmasıydı.
   Bildirimde gecikme DAKİKASI ve darboğaz halka yazılır — "gecikti" değil,
   kaç dakika ve hangi halka; `zincir.py` ikisini de basıyor.

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
3. **Yaz.** Aşağıdaki bölümleri doldur; yamayı `yama.json` dosyasına yaz.
4. **Denetle — yazmadan.** `python3 bulten/yaz.py yama.json --damga "<okuduğun
   olusturma>" --denetle`: yama bellekte uygulanır, denetim o sonuç üzerinde
   koşar, dosyaya yazılmaz. Çıkış kodu 0 olana kadar düzelt. Denetim güven
   değil ölçüm içindir: "atladığımız bir şey var mı" sorusunun cevabını o verir.
   (Eski akış `denetim.py`yi doğrudan çağırıyordu; o araç DİSKTEKİ dosyayı okur,
   yani yazı henüz dosyada yokken koşuyordu.)
5. **Kaydet.** Aynı komut `--denetle` olmadan: `python3 bulten/yaz.py yama.json
   --damga "<okuduğun olusturma>"`. Kapı iki kez sorar — damga tutmuyorsa (çıkış
   3) bülteni yeniden oku ve metni güncel ölçüye göre gözden geçir; denetim
   ENGEL üretiyorsa (çıkış 5) dosya YAZILMAZ, engelleri gider. Ölçüm katmanından
   gelen ve senin gideremeyeceğin bir engel varsa (ör. kapanmamış seansın barı)
   bunu BİLDİR; `--engelle-yaz` yalnız bilinçli istisnadır ve engeller dosyaya
   işlenir.
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

Dört alan: `yorum`, `ozet`, `gundem` ve — yalnız gerektiğinde — `duzeltmeler`.

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

### `duzeltmeler` — yayımlanmış bir sayının düzeltme kaydı

Denetimin "YAYIMLANAN SAYI DEĞİŞTİ" uyarısına verilen cevabın YAPISAL eşi.
Metindeki "yayımlanan X yerine gerçek değer Y" kalıbı kalır (okur metinde
görür); aynı düzeltme bir de liste olarak yazılır ki sayfa onu "Düzeltmeler"
bölümünde bassın ve site bütün bültenlerin düzeltmelerini `/duzeltmeler/`
sayfasında tek listede toplayabilsin. Her kayıt dört alan taşır:

```json
"duzeltmeler": [
  {"alan": "Brent günlük değişim, 28.08 kapanışı",
   "eski": "−%11,36", "yeni": "−%1,74",
   "sebep": "vadeli devir düzeltmesi kurulamamıştı; ham kontrat kapanışı yayımlandı"}
]
```

`tarih` boş bırakılırsa bugünün tarihi yazılır. `alan`, `eski`, `yeni` eksikse
yazma reddedilir — neyin neye düzeltildiğini söylemeyen kayıt okura hesap
vermez. Liste yamada bütünüyle yazılır. Düzeltme yoksa alan hiç gönderilmez.
Sebep okur diliyle yazılır: "ölçü kusuru" değil, kusurun ne olduğu.

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
4. **Olağandışılık da haftalık okunur.** Bölümün adı haftaya bakışta
   "Haftanın olağandışı hareketleri"dir ve sıralama haftalık hareketi
   HAFTALIK oynaklığa böler. Denetim bunu ölçer ve karışmışsa ENGEL üretir.
   Buradaki asıl bilgi çoğu zaman ham listeyle σ listesinin AYRIŞMASIDIR:
   30.08.2026'da haftanın en büyük ham hareketi BIST Bankacılık'ın %5,98'iydi
   ama o endeksin kendi haftalık oynaklığı %5,9 olduğu için yalnız 1,0σ —
   yani manşet büyük, hareket sıradan. Büyük olanı olağandışı sanmak, haftanın
   hikâyesini yanlış yere kurar.
5. **Tema metinleri haftalık kesitle yazılır.** "Bugünkü kesitte", "bugün
   sınanacak" gibi günlük dili haftaya bakışta kullanma; hafta içinde
   gerçekleşmiş bir olayı "yarın olacak" diye bırakma.

## Haftalık teknik analiz (pazar, haftalık bültenden SONRA)

Pazar rutini haftalık bülteni bitirince ikinci bir yayını yazar: **haftalık
teknik analiz bülteni** (sitede `/teknik/`). İş bölümü bültenle aynı: ölçüm
deterministik (`teknik/olc.py`, pazar 15:33 TR'de koşar), yorum senin. Ölçüm
ÜÇ zaman diliminde gelir — **1 saatlik, 4 saatlik, günlük** — her dilimde
göstergeler, pivot destek/direnç bölgeleri, regresyon kanalı ve **yapı ölçümü**
(`dilimler.<kod>.yapi`): son salınım tepeleri/dipleri ve zamanları, tepe/dip
yönleri, `karakter` (yükseliş/düşüş yapısı, sıkışma, genişleme), `cift_tepe` /
`cift_dip` bayrakları.

Akış:

1. `site/src/data/teknik/<bugün>.json` var mı bak. Yoksa ölçüm koşusu düşmüş
   demektir: `Haftalık teknik analiz` iş akışını tetikle, bitmesini bekle,
   depoyu tazele. Ölçümsüz teknik yorum YAZILMAZ. (Nöbetçinin pazar koşusu
   teknik bülteni de denetler: yazılmamışsa alarm çalar.)
2. JSON'u ve 18 grafiği (enstrüman başına 1S/4S/G) oku. `olcum_zamani`
   değerini not et — yazarken `--damga` olarak vereceksin.
3. Her enstrüman için yorum yaz (`us2y`, `us10y`, `dxy`, `eurusd`, `usdchf`,
   `xu100`; 250–400 kelime, HTML) + bir `giris`. Yorumun İSKELETİ SABİT —
   dört `<h4>` başlığı:
   - **`<h4>Günlük</h4>`** — ana çerçeve: trend (SMA50/200, kanal, 52h konum,
     haftalık h10/h40 bağlamı), momentum (RSI, MACD), günlük yapı.
   - **`<h4>4 saatlik</h4>`** — ara çerçeve: günlük trendin İÇİNDEKİ hareket;
     yapı karakteri, dilimin kendi seviyeleri.
   - **`<h4>1 saatlik</h4>`** — kısa vade: son günlerin akışı, dilimin kendi
     destek/dirençleri; buradaki sinyalin ömrünün kısa olduğu unutulmaz.
   - **`<h4>Ortak görüş</h4>`** — dilimler AYNI yönü mü gösteriyor?
     Hizalanma varsa söyle ("üç dilim de yükseliş yapısında"); çelişki varsa
     hangisine neden öncelik verdiğini söyle (kural: büyük dilim çerçeveyi,
     küçük dilim zamanlamayı verir). İki yönlü senaryo + geçersizlik seviyesi
     BURADA kurulur ve hangi dilimin seviyesine dayandığı yazılır.
   - **Formasyon adlandırma kuralı**: bir formasyonu ("çift tepe", "sıkışma
     üçgeni", "yükselen kanal"…) ancak yapı ölçümü destekliyorsa adlandır —
     `cift_tepe`/`cift_dip` bayrağı, `sikisma` bayrağı ya da tepe/dip
     dizisinin kendisi. Adlandırdığın formasyonun dayandığı noktaları
     (seviyeler, zamanlar — hepsi ölçümde) metne yaz; okur formasyonu
     grafikte o noktalarla bulabilmeli. Ölçümün desteklemediği formasyon
     anılmaz — uydurma yok.
4. Yaz: `python3 teknik/yaz.py yama.json --damga <olcum_zamani>`. Kapı,
   yorumda geçen ve ölçümde karşılığı olmayan her sayıyı REDDEDER; bir seviye
   gerekliyse ve ölçümde yoksa önce `teknik/olc.py`'ye ölçtürülür. `yazili`
   ancak giriş + altı yorumun tamamı dolunca `true` olur.
5. Commit + push; yayını senin push'un tetikler (yayin.yml push'a bağlı).

Kurallar bültenle ortak: uydurma yok, her sayı ölçümden, geri alma kalıbı
burada da geçerli (geçen haftaki senaryo tutmadıysa haftaya açıkça yazılır —
"geçen hafta X demiştik, Y oldu"). Teknik yorum yatırım tavsiyesi değildir ve
sayfa bunu söyler; metinde tavsiye dili ("alın", "satın") KULLANILMAZ —
senaryo dili kullanılır.

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

### Rutin metninin rehberden SAPTIĞI yerler (27.08.2026'da ölçüldü)

Rutin metinleri okunabiliyor. Okundu ve üç yerde bu rehberle çeliştikleri
görüldü. Aracı onları düzeltemiyor (güncelleme reddediliyor), o yüzden burada
yazılıdırlar; rutin "rehbere birebir uy" dediği için çelişkide REHBER esastır.
Kalıcı çözüm rutin metnini claude.ai arayüzünden düzeltmektir.

| rutin ne diyor | rehber ne diyor | durum |
|---|---|---|
| "Dosya yoksa `python3 bulten.py --tur gunluk` ile üret" | Üretme — o oturumda ağ kapalı, 0 enstrümanlık fotoğraf çıkar ve önbellek kirlenir; iş akışlarını tetikle | **Araçla kapatıldı**: `bulten.py` 40 enstrümanın altında dosyayı YAZMIYOR (çıkış 4) |
| `python3 bulten/yaz.py yama.json` (damgasız) | `--damga "<olusturma>"` ver | Araçla kapatıldı: damga verilmese de yama dosyasının zamanı ölçümle kıyaslanıyor |
| `zincir.py` hiç geçmiyor | 0. adım zincire bakmaktır | **Araçla ÖLÇÜLDÜ**: `yaz.py` gecikmeyi zincir raporundan bağımsız kaydeder ve `gecikme.yml` alarmı zincir raporuna hiç bakmadan verir. Dayatılamıyor, ama artık görünmüyor da değil |

**Silip yeniden kurmak da çözüm değil.** 27.08.2026'da denendi: aracının
kurduğu bir rutin ateşlendiğinde depoya erişemiyor (sınama koşusu 24 saniyede,
tek bir dosyaya dokunamadan bitti). Mevcut rutinlerin taşıdığı kaynak depo
bağlantısının `create_trigger`'da karşılığı yok. Yani düzeltme yalnız
claude.ai arayüzünden yapılabilir.

Üçüncü satır hâlâ DAYATILAMIYOR: rutinin bu aracı koşturmasını sağlayacak bir
karşılık yok. Zincire bakmayan bir koşu, eksik halkayı fark etmeden yazmaya
kalkışır; o durumda da ilk satırdaki kapı devreye girer ve sakat ölçü
yazılmaz. Yani en kötü hâlde bülten çıkmaz — yanlış bülten çıkmaz.

Ama satırın maliyeti artık GÖRÜNÜYOR ve bu bilerek araca bağlandı: gecikme
kaydı `yaz.py`nin yan etkisidir (bülteni yazmanın başka yolu yok, hiçbir
bayrak gerekmiyor), alarmı taşıyan iş akışı zincir raporuna hiç bakmıyor ve
uyandırıcısı bir cron değil. Yani rutin bu rehberin tek satırını okumasa bile
gecikme ölçülür, kaydedilir ve haber verilir. Rehbere yazılmış bir kural,
"rutin metnine yazıldı" kadar zayıftır; bu bölümün varlık sebebi de zaten o.

**Rutini bir aracı yeniden kuramaz.** Mevcut iki rutin (hafta içi 04:15 UTC,
pazar 14:45 UTC) hesabın arayüzünden oluşturuldu; aracının onları güncelleme ya
da silme yetkisi yok. Aracının kurduğu bir rutin ise depoya erişemez: yeni
oturuma depo bağlanmadığı için özel depo klonlanamaz. Yani rutin metnini
değiştirmenin tek yolu **claude.ai arayüzü**; oradan değiştirilecek bir şey
yoksa yeni kural buraya yazılır ve rutin onu okuyarak öğrenir.

## Tekrar — iki eksen

Bültenin tekrarı iki ayrı yerde ölçülür ve ikisi ayrı kusurdur.

**Sayı içi.** Aynı olgu birden çok bölümde yeniden ANLATILMAZ. Bir olgu bir kez
tam anlatılır; ikinci geçişinde ya üzerine yeni bir işlem yapılır (aynı faiz
taşıma hesabına girer) ya da tek cümleyle anılıp geçilir.

**Günler arası.** *Bir sayı, önceki sayıyı özetlemez.* Okur dünkü bülteni
okudu; bugünkü sayı DEĞİŞENİ anlatır. Ölçüldü (07.09.2026, 13 sayı): senin
yazdığın düzyazı bu sınavı zaten geçiyor — gündem %0,6, yorum %0,3 birebir
örtüşüyor. Tökezlediğimiz iki yer şunlar oldu:

- **Söz defteri** ardışık iki sayı arasında %91,4 örtüşüyordu, çünkü 4.816
  sözcüklük bölüm her sabah yeniden basılıyordu. Artık ölçüm katmanı kaydı
  `degisti`/`duran` diye işaretliyor ve sayfa yalnız DEĞİŞENİ tam metinle
  basıyor. Sana düşen: bir kaydın metnini ancak gerçekten değiştiyse güncelle.
  Aynı sözü yeni sözcüklerle yeniden yazmak, kaydı "değişti" diye işaretler ve
  tekrarı geri getirir.
- **Özet** 24–25.08'de önceki sayıdan %97–100 aynen kopyalanmıştı. Özet, o
  günün özetidir; dünkü özetin üzerine tarih atmak değil.

Kapı `bulten/denetim.py`de ve ENGEL DEĞİL UYARI: sakin bir haftada iki sayının
benzemesi meşrudur, vadesi gelen bir söz yeniden anılmalıdır. Uyarı hangi
bölümün sürüklediğini adıyla söyler — hedef, sayfa düzyazısının %30'unun
altında.

## Kurallar

**Atıf disiplini.** `%1,5`'i aşan her hareket metinde **anılmalı** ve sebebi
yazılmalı. Sebebi bilinmiyorsa "sebebi netleşmedi" yaz — en görünür manşeti
sürücü diye göstermek en kötü seçenek. (2026-08-17 haftasında ABD Hazinesi'nin
tahvil geri alımı USD ve faizlerdeki asıl sürücüydü ve bülten bunu tamamen
atlamıştı; `onem_puani` ve ABD Hazine kaynağı bu yüzden eklendi.)

**Metin kendi ayakları üstünde dursun.** Yazdığın `yorum` ve `gundem`
bölümleri yalnız sitede okunmuyor: aynı metin X'e tek gönderi olarak da çıkıyor
ve orada ne sayfa, ne tablo, ne de başka bir bölüm var. Gönderi
`tweet/denetim.py` kapısından geçer (tavsiye dili, link — tweetlerde HİÇ link
kullanılmaz, çıplak alan adı dahil —, HTML kalıntısı, site
atfı, sayı ortasında kesik cümle, sorumluluk notu); kapı düşerse gönderim
durur ve o sabah X'te hiçbir şey çıkmaz — yani metnin tweete uygunluğu senin
sorumluluğun. Gönderiyi önceden görmek için: `python3 tweet/gonder.py --kuru`. Bu yüzden sayfa
mobilyasına atıf yapma — "bu sayfadaki piyasa fotoğrafında", "yukarıdaki pano",
"ayrıntısı jeopolitik bölümünde", "bu bültenin takip ettiği" gibi ifadeler
kullanma. Söylemek istediğin şeyi kendi cümlesi içinde tamamla: "fotoğrafta
yok" yerine "51 satırın tamamı 28 Ağustos kapanışına ait", "jeopolitik
bölümünde" yerine gelişmeyi orada bir cümleyle söyle.

Sigorta araçta: `tweet/uret.py` bu izleri taşıyan CÜMLEYİ düşürür (ve
göndergesi silindiği için öksüz kalan devamını da). Yani kural çiğnendiğinde
tweet bozulmaz — ama SENİN cümlen kaybolur ve okur onu X'te hiç görmez.
Metni baştan bağlamsız yazmak, cümleni kurtarmanın tek yolu.

**Kod dili yasak.** Okuyucuya hiçbir şey söylemeyen geliştirici dili sayfaya
girmez: dosya adı, alan adı, "eşikler ayar.py içinde", "itp_b_sabit" gibi.
Denetim bunu ölçer ve engeller (`ortak/okur_dili.py`, tek tanım). "Koşu" ve
"veri tarihi" okura verilen kayıt adlarıdır, yasak değildir.

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

**FX haber endeksi bültenden ÖNCE tazelenir — bak.** Hat hafta içi her sabah
04:53'te koşuyor, yani ölçümden 90 dakika önce; panodaki "FX haber endeksi —
sepet spread'i" satırı o koşudan gelir. Panoda yalnız spread var, çünkü hattın
uçları (en alıcı / en satıcı varlık) her gün başka bir varlığa ait ve sürüm
kıyası anlamsız olurdu. Günün haber tonunda anlatmaya değer bir şey olup
olmadığını görmek için proje sayfasına bak: hangi varlık uçta, kaç makaleyle,
bir önceki okumaya göre ne kadar döndü. **Spread'in saati ayrıdır**: o GDELT
haftalık arşivinden gelir ve hattın günlük tarihinden birkaç gün geridedir —
panoda kendi tarihiyle yazar, o tarihle anlat.

**Haber tonundaki olağandışı hareketler ANILMAK ZORUNDA.** Ölçüm katmanı FX
haber endeksinin günün en olağandışı üç hareketini sıralayıp bülteninin "Haber
tonu" grubuna basar; denetim bunları metinde ARAR ve bulamazsa ENGEL üretir.
Sebebini haber akışından bul; netleşmiyorsa "sebebi netleşmedi" yaz — ama
sessiz geçme.

Üç şeye dikkat: (1) **Kıyas penceresi sabit değil.** Hat günlük koşmaya yeni
geçti; tarihçedeki eski aralıklar haftalarca. Olay cümlesi kaç günlük dönüş
olduğunu yazar, sen de metinde yaz — "endeks döndü" demek, ne kadar sürede
döndüğünü söylemeden yanıltır. (2) **Sıralama eşikle yapılmıyor.** Sabit eşik
denendi ve ölçüldü: snapshot'tan snapshot'a 15 varlığın 9-12'si kategori
değiştiriyor, yani eşik her gün on sahte olay üretirdi. Listede olmak "büyük
hareket" demek değil, "bugünün en büyüğü" demektir. (3) **σ henüz yok.** Hattın
oynaklık tarihçesi standart sapma için yetene kadar sıralama ham büyüklüğe göre
yapılır ve olay cümlesi bunu söyler; o hâlde "olağandışı" değil "en büyük" diye
yaz.

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
- *"Bugün tazelenmesi gereken ama tazelenemeyen hatlar: …"* — bu hatların
  sayısı dünkü sürümde. Günün haberini onların üstüne kurma; kullanacaksan
  kendi tarihiyle kullan ("kredi verisi 3 Eylül'de kaldı"). Bültende yazılacak
  şey hattın BAYATLIĞIDIR; koşunun geciktiği, hangi iş akışının düştüğü okuru
  ilgilendirmez ve okur diline girmez.

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

**Her satırın kendi bar tarihine bak.** Piyasa fotoğrafındaki her satır hangi
GÜNÜN kapanışını taşıdığını yazar. Bugünün tarihini taşıyan bir satır, ancak o
piyasa kapandıysa kullanılabilir; kapanmadıysa o satırın "günlük değişim"i dünkü
seansı değil geceliği ölçer ve işareti dünküyle ters olabilir. Denetim bunu artık
ENGEL sayıyor (`kapanmamış seansın barı`), ama engelin çıkmaması satırların hepsi
aynı güne aittir demek değildir: bülten 26 Ağustos kapanışlarıyla 27 Ağustos'ta
kapanmış bir Asya seansını aynı sayfada taşıyabilir. Hangi satırın hangi güne ait
olduğunu METİNDE söyle.

**Bir düzeltme yaptıysan GENELLEŞTİR.** Bu, 27.08.2026'nın asıl dersi. O sabahki
metin enerjide bir ölçü hatası fark etti, doğru teşhis etti ve düzgün bir geri
alma yazdı — sonra aynı paragrafın devamında, aynı hatayı taşıyan metal
rakamlarını düzeltmeden yayımladı. Aradaki tek fark, enerjide korumanın var
olması ve hatanın bir gün önce göze çarpmış olmasıydı. Bir ölçü kusuru
bulduğunda soru "bu seriyi düzelttim mi" değil, **"bu kusur başka nerede
olabilir"** olmalı: aynı kaynaktan gelen, aynı yoldan geçen bütün satırları
gözden geçir.

**Haber başlığı ölçüyü DOĞRULAMAZ.** Aynı sabah, yanlış ölçüyü destekleyen bir
başlık bulundu ("Gold Rises…") ve teyit sayıldı; oysa o başlık iki gün önceki
harekete aitti. Bir başlığın hangi güne ait olduğunu kontrol etmeden ölçüyle
eşleştirme. Ölçü ile haber çelişiyorsa varsayılan, ÖLÇÜYÜ sorgulamaktır — haberi
ölçüye uydurmak değil.

**"YAYIMLANAN SAYI DEĞİŞTİ" uyarısı ciddidir.** Denetim, aynı SERİNİN aynı güne
ait değerini önceki üç bültende yayımladığımızla karşılaştırır — piyasa
satırlarının günlük değişimi, TL faiz seti, gösterge şeridi, türev büyüklükler
(bacak bar günleri aynıysa) ve rejim panosu (girdi günleri aynıysa). Temiz
geçtiğinde seri başına kaç çift kıyaslandığını da yazar: "türev 0/9" kıyas
yapılmadığı, "temiz" olmadığı anlamına gelir.
Listelenen her sayı için ya sebebi bul (meşru revizyon) ya da metinde
"yayımlanan X yerine gerçek hareket Y" kalıbıyla geri al **ve aynı düzeltmeyi
`duzeltmeler` alanına yapısal kayıt olarak yaz** (yukarıda). Metinde kalıp var
ama kayıt yoksa denetim uyarı düşer. Listenin uzun olması tek bir ölçüm
kusuruna işaret eder; tek tek değil, KAYNAĞINI ara.

**Bir ölçüyü kendi içinde ÇAPRAZLA.** 31.08.2026'da denetimin "yayımlanan sayı değişti"
uyarısı on iki satır listeledi ve liste tek bir sebebe çıkmadı — İKİ ayrı kusur vardı,
ikisi de ancak ölçünün kendi içindeki tutarlılığa bakılarak ayrıldı:

- **Dolar endeksi çaprazları tutuyor mu?** Endeks (DX-Y.NYB) ile `=X` çaprazları AYNI
  günü ölçer; endeksin günlük değişimi kabaca ağırlıklı çapraz değişimlerine eşit
  olmalıdır (EUR %57,6 · JPY %13,6 · GBP %11,9 · CAD %9,1 · SEK %4,2 · CHF %3,6; euro ve
  sterlin ters işaretle). O sabah endeks %0,54 yükselmişken çaprazların ima ettiği hareket
  ≈ %0,00'dı; pazar günkü ölçüde ise ≈ %0,44 ile tutarlıydı. Yani BUGÜNKÜ çapraz okumaları
  açık seansın etkisini taşıyordu. Çaprazların günlük değişimi üzerinden hüküm kurulmadı ve
  bunun sebebi metinde yazıldı.
- **Günlük ve haftalık kayma AYNI büyüklükte mi?** Bir satırda `d1` ile `h1` aynı miktarda
  kaydıysa değişen şey kıyas barı değil SON FİYATTIR. Metallerde ikisi de birebir aynı
  kaydı (altın −1,12 puan, gümüş −1,14, bakır −1,48); yani pazar günkü kapanış eksikti,
  bugünkü tam. Orada geri alma kalıbı kullanıldı.

Kural: liste uzunsa önce "hangi satırlar aynı aileden" diye bak, sonra o ailenin İÇ
tutarlılığını sına. Tek sebep aramak, iki kusuru birbirine karıştırmaya yol açar.

**"Vadeli devir düzeltmesi kurulamadı" uyarısı seviyeleri iptal eder.** O
satırlarda gösterilen fiyat ham kontrat kapanışıdır; önceki yayımla
kıyaslanamaz ve seviyeden türeyen rafineri marjları üzerinden yorum kurulamaz.
Günlük yüzde değişimler etkilenmez — onları kullan, seviyeyi kullanma.

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

**Defteri düzeltmek SAYFAYI düzeltmez.** Tema bölümü bültene ÖLÇÜM anında
işlenir; yazı katmanı `temalar.json`'u ondan sonra günceller. Yani defteri
düzeltip yazmak, sayfada eski metni bırakır. Bu iki kez yayına çıktı: 28.08.2026'da
sayfa bir gün önce geri alınmış rakamları yeniden bastı, 30.08.2026'da haftaya
bakış "çürütücü ölçüt bugün sınanacak — Warsh'ın Jackson Hole konuşması" dedi ve
konuşma iki gün önce yapılmıştı. Doğru sıra: **önce defteri güncelle, sonra
ölçümü `--yeniden-olc` ile yeniden kur, sonra yaz.** Denetim artık sayfadaki
görüntü ile defteri karşılaştırıyor ve ayrışıyorlarsa ENGEL üretiyor.

**Bir ölçünün BOŞ görünmesi, ölçülen şeyin OLMAMASI demek değildir.** Bu,
30.08.2026'nın dersi ve pahalıya mal oldu: bülten üç hafta boyunca "gevşemenin
resmî ölçüsü yok, ağırlıklı ortalama fonlama maliyeti donuk" yazdı. TCMB o seriyi
her gün yayımlıyordu ve 24 Ağustos'ta 40,00'dan 37,00'ye indirmişti; değeri
eleyen kendi geçerlilik kapımızdı (fonlama tabanı 5 mlr TL eşiğinin altında).
Panoda bir satır "güncel değil" diyorsa **sebebini oku** — satır artık sebebi
kendi üstünde taşıyor. Sebebi okumadan "ölçü yok" yazmak, okura yanlış bilgi
vermektir. Fazla likidite rejiminde TCMB parasının marjinal fiyatını fonlama
değil sterilizasyon belirler; faiz setindeki "Marjinal TCMB faizi" satırı o
rejimde hangi ölçünün geçerli olduğunu söyler.

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
