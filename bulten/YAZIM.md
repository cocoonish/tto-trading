# Bülten yazım rehberi

Bu dosya, günlük ve haftalık bülteni **yazan** katmanın görev tarifidir. Bültenin
ölçülen kısmı (piyasa fotoğrafı, takvim, göstergeler, hat hat değişim) otomatik
koşudan gelir ve yazan taraf ona **dokunmaz**. Yazan taraf dört alanı doldurur:
`yorum`, `ozet`, `gundem`.

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

## Haftalık teknik analiz (pazar, haftalık bültenden SONRA)

Pazar rutini haftalık bülteni bitirince ikinci bir yayını yazar: **haftalık
teknik analiz bülteni** (sitede `/teknik/`). İş bölümü bültenle aynı: ölçüm
deterministik (`teknik/olc.py`, pazar 15:33 TR'de koşar → altı enstrüman için
göstergeler, pivot destek/direnç bölgeleri, regresyon kanalı, Fibonacci ve
mum grafikleri), yorum senin.

Akış:

1. `site/src/data/teknik/<bugün>.json` var mı bak. Yoksa ölçüm koşusu düşmüş
   demektir: `Haftalık teknik analiz` iş akışını tetikle
   (`gh workflow run teknik.yml` karşılığı MCP çağrısı), bitmesini bekle,
   depoyu tazele. Ölçümsüz teknik yorum YAZILMAZ.
2. JSON'u ve altı enstrümanın grafiklerini oku. `olcum_zamani` değerini not et —
   yazarken `--damga` olarak vereceksin.
3. Her enstrüman için yorum yaz (`us2y`, `us10y`, `dxy`, `eurusd`, `usdchf`,
   `xu100`; 150–250 kelime, HTML paragraflar) + bir `giris` (haftanın teknik
   çerçevesi, makro bültenle bağ). Her yorumun iskeleti:
   - **Trend**: fiyat/getiri SMA50–SMA200'e ve regresyon kanalına göre nerede;
     haftalık çerçeve (h10/h40) günlükle aynı yönde mi.
   - **Momentum**: RSI günlük+haftalık, MACD histogramın yönü; uyumsuzluk
     varsa (fiyat yeni uç, RSI değil) SÖYLE ama ölçüsüyle.
   - **Seviyeler**: ölçümün verdiği pivot bölgelerinden ve Fibonacci'den
     İŞE YARAYANLARI seç, neden önemli olduklarını söyle (dokunuş sayısı,
     son dokunuş tarihi ölçümde var).
   - **İki yönlü senaryo + geçersizlik**: "X üstünde kalırsa … / Y altına
     sarkarsa …" — her senaryonun geçersizlik seviyesi ölçümden.
4. Yaz: `python3 teknik/yaz.py yama.json --damga <olcum_zamani>`. Kapı,
   yorumda geçen ve ölçümde karşılığı olmayan her sayıyı REDDEDER — seviye
   uydurma yok; bir seviye gerekliyse ve ölçümde yoksa önce `teknik/olc.py`'ye
   ölçtürülür. `yazili` ancak giriş + altı yorumun tamamı dolunca `true` olur
   ve sayfa ancak o zaman yayımlanır.
5. Commit + push; yayını `Haftalık teknik analiz` iş akışının push'u değil,
   senin push'un tetikler (yayin.yml push'a bağlı).

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
| `zincir.py` hiç geçmiyor | 0. adım zincire bakmaktır | Yalnız rehberde — rutin düzeltilene kadar boşluk |

**Silip yeniden kurmak da çözüm değil.** 27.08.2026'da denendi: aracının
kurduğu bir rutin ateşlendiğinde depoya erişemiyor (sınama koşusu 24 saniyede,
tek bir dosyaya dokunamadan bitti). Mevcut rutinlerin taşıdığı kaynak depo
bağlantısının `create_trigger`'da karşılığı yok. Yani düzeltme yalnız
claude.ai arayüzünden yapılabilir.

Üçüncü satır kapatılamadı: bir aracın dayatabileceği bir karşılığı yok. Zincire
bakmayan bir koşu, eksik halkayı fark etmeden yazmaya kalkışır; o durumda da
ilk satırdaki kapı devreye girer ve sakat ölçü yazılmaz. Yani en kötü hâlde
bülten çıkmaz — yanlış bülten çıkmaz.

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

**"YAYIMLANAN SAYI DEĞİŞTİ" uyarısı ciddidir.** Denetim, aynı enstrümanın aynı
bar gününe ait günlük değişimini önceki bültenlerde yayımladığımızla karşılaştırır.
Listelenen her sayı için ya sebebi bul (meşru revizyon) ya da metinde
"yayımlanan X yerine gerçek hareket Y" kalıbıyla geri al. Listenin uzun olması
tek bir ölçüm kusuruna işaret eder; tek tek değil, KAYNAĞINI ara.

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
