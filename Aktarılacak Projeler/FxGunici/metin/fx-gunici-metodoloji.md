---
title: 'FX Gün İçi Stratejiler 8: Metodoloji — Veri, Saat, Yürütme, Ön Kayıt ve Ölçülmeyenler'
description: "Serinin bütün sayılarının nasıl üretildiği: Dukascopy 1 dakikalık bid/ask arşivinin indirilmesi ve denetimi, saat ve yaz saati kuralları, yürütme mekaniği (giriş, stop, hedef, gün sonu, maliyet), örneklem bölmesi, sonuçtan önce yazılan ön kayıt ve sonradan yapılan her şey, seçim ve sağlamlık ölçüleri, haber takviminin kaynakları ve dışarıda kalan olaylar, ve bu serinin ölçmediği şeylerin listesi."
pubDate: 2026-10-16
tags: ['fx', 'gun-ici', 'backtest', 'metodoloji', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · BLS, Fed, ECB, BoE resmî kaynakları · önceden kayıt'
ozet: "Bir backtest'in sonucu, nasıl ölçüldüğü kadar güvenilirdir. Bu ders serinin makinesini açar: hangi fiyat, hangi saat, hangi dolum kuralı; ne önceden yazıldı, ne sonradan yapıldı; ve hangi soruların hiç sorulmadığı."
seviye: 'ileri'
onkosul:
  - fx-gunici-giris
---

Önceki yedi ders sonuçları anlattı. Bu ders sonuçların nasıl üretildiğini anlatır ve iki amaca hizmet eder. Birincisi
denetlenebilirlik: bir okurun bir sayıya itiraz edebilmesi için o sayının hangi fiyattan, hangi saatte ve hangi
kuralla ölçüldüğünü bilmesi gerekir. İkincisi dürüstlük: bir backtest'in en sık kusuru bir kuralın sonuca bakılarak
seçilmesi ya da değiştirilmesidir. Burada neyin sonuçtan önce yazıldığı, neyin sonradan yapıldığı ve gerekçesi
adıyla durur.

## Veri: kaynak, indirme, arşiv

Fiyat verisi Dukascopy'nin herkese açık beslemesinden gelir: her parite ve her UTC günü için iki dosya, 1 dakikalık
**bid** ve **ask** mumları. İki taraf ayrı indirildiği için her dakikanın gerçek makası bilinir: alış ask'tan, satış
bid'den yürütülür ve makas maliyete ayrıca eklenmez, fiyatın kendisindedir.

Strateji mumları (5, 15, 60 dakika) 1 dakikalık orta fiyattan kurulur ve UTC saatine çıpalıdır. 5 ve 15 dakikalık
mumlarda seans açılışları (Londra 08:00, New York 08:00 ve 09:30) her zaman bir mumun başına düşer. 60 dakikalık
mumlarda her kural kendi çıpasını kullanır: saatlik mum saat başında başlar, New York 09:30 ilk dengesinde ise
:30'da. Haber kurallarının mumları her zaman olay dakikasından başlar: ilk haber mumu olay dakikası ile bir mum
sonrası arasıdır.

Arşiv parite × yıl birimlerinden oluşur ve bir birim ancak istenen bütün günleri indiğinde tamamlanmış sayılır;
inmeyen gün yeniden istenir. Cumartesi dosyası istenmez: FX cuma 17:00'de (New York) kapanır, pazar 17:00'de açılır
ve UTC cumartesisinin bütün dakikaları kapalı piyasadır (2018 ve 2019'da istenen bütün cumartesi dosyaları boş
döndü). Her birimin içerik özü (SHA-256) künyede durur ve dosya her okunuşta ona karşı sınanır: arşivde sessizce
değişen bir dosya ölçüme giremez.

{{! arsiv_ozet }}

{% if T.eksik_birim %}_Tamamlanmayan {{ T.eksik_birim | n }} yıl biriminde {{ T.inmeyen_gun | n }} gün inmedi:
o günler ölçümde yoktur, hangi günler oldukları künyede adıyla durur ve sonuçların kapsamı bu kadar eksiktir._{% else %}_Bütün yıl
birimleri tamamlandı: dört paritede istenen her gün indi._{% endif %}

Veri denetimi giriş dersinde (kapsam, tatil, makas, sıçrama adayı ve Dukascopy'nin kendi saatlik mumlarıyla çapraz
sınama). Denetim veriyi **değiştirmez**: sıçrama adayları sayılır ve listelenir, düzeltilmez ya da atılmaz.

**Tatil** fiyattan değil takvimden gelir: 25 Aralık ve 1 Ocak hafta içine düştüğünde stratejiler o gün işlem açmaz.
Günün kapsamından okunan bir tatil bayrağı gün bitmeden bilinemezdi; takvim önceden bilinir. Arşivde kapsamı %50'nin
altında kalan işlem günleri dört paritede de tam bu günlerdir ({{ O.veri.tatil_uyum.EURUSD.takvim | n }} gün).{{? O.veri.tatil_uyum.EURUSD.ayni and O.veri.tatil_uyum.GBPUSD.ayni and O.veri.tatil_uyum.USDJPY.ayni and O.veri.tatil_uyum.AUDUSD.ayni }}
Örneklemin iki kenarında baştan sona kapsanmayan işlem günü de işlem açmaz.

## Saat

Bütün zaman damgaları UTC olarak saklanır; yerel saatler (Londra, New York, Frankfurt) IANA saat dilimi tablosundan
çevrilir ve hiçbir saat farkı elle yazılmaz. FX günü New York 17:00'da başlar ve biter. İşlem saatleri okura TSİ
olarak verilir (UTC+3, yaz saati yok); olay saatleri ayrıca kendi yerel saatleriyle. Yaz saati geçişleri her yıl
için elle yazılmış bir listeye karşı sınanır; Londra ile New York'un farklı haftalarda saat değiştirdiği ara dönemler
giriş dersindeki tablodadır.

Saatin doğru işlendiğinin bağımsız bir sınaması da var: ABD tarım dışı istihdam verisi 08:30 New York'ta
yayımlanır, yani damgalar doğruysa ayın ilk cumalarında 1 dakikalık mum aralığının ortalaması yazın da kışın da tam o
dakikada zirve yapmalıdır. {% if O.veri.kalite.EURUSD.damga.yaz.zirve_dk == 0 and O.veri.kalite.EURUSD.damga.kis.zirve_dk == 0 %}EUR/USD'de
yapıyor: yaz saatindeki {{ O.veri.kalite.EURUSD.damga.yaz.gun | n }} günün de kış saatindeki
{{ O.veri.kalite.EURUSD.damga.kis.gun | n }} günün de ortalama aralığı 08:30 dakikasında en yüksek. Bir saatlik yaz
saati hatası zirveyi altmış dakika öteye taşırdı.{% else %}EUR/USD'de zirve yaz saatinde
{{ O.veri.kalite.EURUSD.damga.yaz.zirve_dk | n }}, kış saatinde {{ O.veri.kalite.EURUSD.damga.kis.zirve_dk | n }}
dakika kayık: damgalar sınanmalı.{% endif %}

Ay sonu, ayın son **Londra iş günüdür** (WM/R fiksingi Londra'da hesaplanır). İngiltere ve Galler resmî tatilleri
kuralla hesaplanır (Paskalya'ya bağlı günler, mayıs ve ağustos tatilleri, kraliyet etkinlikleri için konan özel
günler adıyla) ve elle yazılmış bir listeye karşı sınanır.

## Yürütme mekaniği

- **Sinyal ve giriş.** Sinyal, strateji mumunun orta fiyat kapanışıyla verilir; giriş bir sonraki mumun ilk
  dakikasının açılışındadır (alış ask'tan, satış bid'den). Sinyalin görüldüğü fiyattan girilmez.
- **Stop.** Sert stop emir tarafında dakika dakika izlenir; fiyat stop'un ötesinde açılırsa (boşluk) dolum açılış
  fiyatındandır. Kapanış stop'u, mumun orta fiyat kapanışı stop'un ötesindeyse bir sonraki mumun açılışında kapatır.
  Varsayılanı stop'suz olan iki kuralın (fiksing ve gün içi momentum) stop'lu kombinasyonlarında stop, yürütülen
  giriş fiyatından 1·ATR uzağa konur.
- **Hedef.** Limit emirdir ve kaymaz. Stop ile hedef aynı strateji mumunun içinde değmişse sıra 1 dakikalık
  veriyle çözülür; aynı dakikada ikisi birden değmişse **stop** sayılır (tutucu varsayım).
- **Gün sonu ve tek pozisyon.** Bütün pozisyonlar en geç {{ K.gun_sonu_et | t }} New York'ta kapanır; gece ve hafta
  sonu pozisyon taşınmaz. Aynı anda parite başına tek pozisyon vardır; açık pozisyon varken gelen sinyal atlanır.
  Haber kurallarında kural bütün olaylara birlikte uygulanır: bir olayın pozisyonu açıkken gelen başka bir olayın
  sinyali (ör. aynı gün FOMC kararından sonra basın toplantısının sinyali) alınmaz.
- **Maliyet.** Makas gerçek bid/ask'tadır. Üstüne her piyasa dolumuna (giriş, zaman çıkışı, stop) temel senaryoda
  {{ K.temel_kayma_pip | s1 }} pip kayma eklenir; haber penceresinde (olay dakikasına göre
  {{ K.haber_pencere_dk[0] | n }} ile +{{ K.haber_pencere_dk[1] | n }} dakika arası) kayma {{ K.haber_kayma_pip | s1 }}
  pip daha büyüktür. Maliyet merdiveni aynı kuralı dört kaymayla yeniden koşar (dolum başına
  {{ K.kayma_pip[0] | s1 }} · {{ K.kayma_pip[1] | s1 }} · {{ K.kayma_pip[2] | s1 }} · {{ K.kayma_pip[3] | s1 }} pip);
  haber penceresinin ek kayması her basamakta aynı kalır. Ayrıca bir **yalnız makas** koşusu var: kayma da haber
  kayması da sıfır, maliyet yalnız gerçek bid/ask. Merdiven aynı işlemlerin değil aynı kuralın yeniden koşusudur:
  kayma dolum fiyatını değiştirir, R katı hedefin seviyesi ve stop'a ya da hedefe değilen dakika onunla değişebilir,
  tek pozisyon kuralı yüzünden alınan işlemler de.
- **R.** Bir işlemin R'si net sonucunun planlanan riske oranıdır: yürütülen giriş fiyatından stop seviyesine uzaklık.
  Stop'suz kurallarda R bir ölçek birimidir: fiksingde kuralın kendi mumlarından girişteki ATR(14), gün içi
  momentumda girişteki 60 dakikalık ATR(14).
- **MFE ve MAE.** İşlemin lehine ve aleyhine en büyük hareketi: girişten çıkışa, dakika dakika, yürütülebilir
  fiyatla (alışta bid, satışta ask), R cinsinden. Hedefin dolduğu dakikada dakikanın içindeki sıra bilinmediği için o
  dakikanın ters ucu MAE'ye girer; gerçekleşen sonuç her zaman ikisinin arasındadır. Örnek günlerin "kaybeden" ve
  "tuzak" tanımları bu ölçüden okunur.

**İleriye bakma sınaması.** Bir kural geleceğe bakıyorsa (bugünün henüz kapanmamış tepesini, sonraki mumun fiyatını
ya da günün kapanışını kullanıyorsa) bunu yakalamanın yolu veriyi bir anda kesmektir. Sınama gerçek arşivde değil,
gerçek seans yapısıyla üretilmiş {{ K.ileri_bakma.sentetik_gun | n }} iş günlük sentetik bir 1 dakikalık seride (haber
olaylarıyla birlikte) ve {{ K.ileri_bakma.kesim_n | n }} kesim anında yapılır: New York sabahı, Londra sabahı, Londra
açılışından önce ve UTC gece yarısından hemen sonra.{{? K.ileri_bakma.kesim_n == 4 and K.ileri_bakma.kesim[0].an == "new_york_sabahi" and K.ileri_bakma.kesim[1].an == "londra_sabahi" and K.ileri_bakma.kesim[2].an == "londra_acilis_oncesi" and K.ileri_bakma.kesim[3].an == "utc_gece_yarisi_sonrasi" }}
Kesim günün ortasına da düşer, çünkü günün bütününden kurulan bir alan (ör. kapsamdan okunan bir tatil bayrağı)
yalnız böyle bir kesimde sinyal siler. Her birimde ilk kesimde varsayılan ve ızgaradan rastgele seçilmiş
{{ K.ileri_bakma.ornek_ilk_rastgele | n }} kombinasyon, öbür kesimlerde varsayılan ve
{{ K.ileri_bakma.ornek_oteki_rastgele | n }} kombinasyon iki kez yeniden koşulur: bir kez veri kesim anında kesilerek,
bir kez o andan sonraki bütün fiyatlar başka bir yürüyüşle değiştirilerek. Kesimden önce verilen her sinyal üç koşuda
birebir aynı olmalıdır; varsayılanın kesimden önce açılmış işlemlerinin giriş fiyatı, stop'u ve R'si de geleceğin
değişmesinden etkilenmemelidir. Sınama gerçek fiyatla yapılmadığı için bir kuralın kazancı hakkında bir şey söylemez;
yalnız hesabın gelecekten bilgi almadığını gösterir.

## Örneklem, seçim ve sağlamlık

Örneklem içi {{ K.baslangic | tarih }} → {{ K.ic_bitis | tarih }}, örneklem dışı {{ K.dis_baslangic | tarih }} →
{{ K.bitis | tarih }}. Her kural iki biçimde ölçülür. **Varsayılan**, veriye bakmadan seçilmiş ders kitabı hâlidir;
hükmü o verir. **Seçilen**, parametre ızgarasından yalnız örneklem içinde, günlük R serisinin yıllık Sharpe'ıyla ve en
az {{ K.secim.asgari_islem | n }} işlem (haber kurallarında {{ K.secim.asgari_islem_haber | n }}) şartıyla seçilen
kombinasyondur; örneklem dışında ayrıca sınanır. {{ T.birim | n }} birimin ızgaralarında toplam
{{ T.kombinasyon | n }} kombinasyon var.

- **Deflated Sharpe** (Bailey ve López de Prado, 2014): ızgaradan seçilen en iyi kombinasyonun günlük Sharpe'ı, o
  ızgaranın deneme sayısıyla şansla beklenen en yüksek Sharpe'a karşı sınanır. Beklenen en yüksek Sharpe iki biçimde
  kurulur: denemelerin kendi Sharpe'larının yayılımından (Bailey ve López de Prado'nun önerisi) ve yalnız örnekleme
  gürültüsünden (her deneme sıfır kenarlı olsaydı tek bir günlük Sharpe'ın varyansı 1/(T−1), T gün sayısı). Seçilen
  Sharpe'ın eşiği aşma olasılığı %95 ya da üstüyse sınama geçer.
- **Yürüyen pencere:** {{ K.saglamlik.walk_forward_ilk_test_yili | t }}'den itibaren her yıl için yalnız önceki
  yılların verisiyle seçim yapılır ve o yılda sınanır. Seçimin asgari işlem şartı, örneklem içi şartın yıl başına
  payıdır; şartı sağlayan kombinasyonu olmayan yıl sınanmaz ve sınanan yıllar adıyla yazılır.
- **Aralık:** işlem başına net R'nin %95 aralığı {{ K.hukum_kurali.bootstrap_tekrar | n }} tekrarlı bootstrap'le; en
  az {{ K.uygulama_esik.bootstrap | n }} işlem ister. Dört paritenin havuzunda aynı günün bütün paritelerdeki işlemleri
  birlikte örneklenir (gün kümeli bootstrap): aynı gün dört paritede açılan işlemler aynı haberi ve aynı dolar
  hareketini taşır, bağımsız sayılsalardı aralık olduğundan dar çıkardı.
- **Rastgele yön:** alınan her işlemin aynası kurulur: aynı giriş dakikası, ters yön, aynı risk uzaklığı (stop ve hedef
  ters yönde girişe aynı uzaklıkta) ve aynı planlı çıkış (zaman ya da gün sonu çıkışı aynı dakikada). Her tekrarda
  her işlem için gerçeği ya da aynası yazı turayla seçilir ve ortalama alınır; {{ K.hukum_kurali.rastgele_tekrar | n }}
  tekrar. Kuralın yüzdeliği, gerçek ortalamanın altında kalan karışımların payıdır. En az
  {{ K.uygulama_esik.rastgele | n }} işlem ister.
- **Hüküm:** örneklem dışı (2024 →) net ortalama artı, aralığın alt ucu sıfırın üstünde ve rastgele yön dağılımında
  {{ K.hukum_kurali.rastgele_esik_yuzdelik | n }}. yüzdelik ya da üstü ise **çalışıyor**; ortalama artı ama öbür
  şartlardan biri tutmuyorsa ya da işlem sayısı o şartı kurmaya yetmiyorsa **zayıf**; ortalama sıfır ya da eksiyse
  **çalışmıyor**; örneklem dışında hiç işlem yoksa **ölçülemedi**. {{ K.uygulama_esik.az_islem | n }}'den{{? K.uygulama_esik.az_islem == 20 }} az işlemli
  sonuç **az işlem** diye işaretlenir; işaret hükmü değiştirmez. Brüt sonucun aralığı sıfırın üstünde ama net sonuç
  sıfır ya da eksiyse ayrıca **maliyet** bayrağı.
- **Koşullar:** on dört değişken{{? len(K.kosul.degiskenler) == 14 }}; sürekli değişkenlerde kova sınırları (terciller)
  yalnız örneklem içinden kurulur ve örneklem dışına taşınır. Koşulsuz ortalama değişkenin tanımlı olduğu
  işlemlerden alınır. Örneklem içinde koşulsuz ortalamanın üstündeki, en az {{ K.kosul.asgari_kova_islem | n }}
  işlemli kovalar seçilir; seçim örneklem dışında artı kalır, öbür kovaları aşar ve en az
  {{ K.uygulama_esik.kosul_oos | n }} işlemle ölçülürse "tuttu". Hiçbir kova seçilmediyse ya da bütün kovalar
  seçildiyse sınama kurulamaz ve adıyla yazılır. Bütün işlemlerde aynı değeri taşıyan iki değişken tek sayılır.
  Kontrol listesine aday olarak yalnız en az iki paritede aynı kovayla tutan koşul girer.

### Ön kayıt

Kuralların, ızgaraların, varsayılanların ve hüküm kuralının hepsi tek bir ön kayıt dosyasında, hiçbir backtest
sonucu görülmeden yazıldı ve kaydedildi. Dosyanın bütün geçmişi:

{{! onkayit_tablo }}

[Ön kaydın tam metni](/arastirma/fx-gunici/onkayit.toml) sayfayla birlikte yayımlanır; dosyanın SHA-256 özü
`{{ K.onkayit_ozu | t }}`. İkinci kayıt haber devam tablosunu ekledi: o anda fiyat ve takvim verisinin ilk iki
parçası (EUR/USD 2018'in ilk fiyat dosyası ve FOMC duyurularının ham sayfaları) indirilmişti ama hiçbiri okunmamış,
takvim ayrıştırılmamış ve hiçbir haber olayı ölçülmemişti. Üçüncü kayıt yalnız ikinci kaydın açıklama notunu
düzeltti; kuralların içeriği aynı kaldı.{{? len(K.onkayit_gecmisi) == 3 and len(K.onkayit_gecmisi[1].degisen_bolum) == 1 and K.onkayit_gecmisi[1].degisen_bolum[0] == "haber_devam" and len(K.onkayit_gecmisi[2].degisen_bolum) == 0 }}

### Ön kayıttan sonra yapılanlar

Ön kaydın metni yukarıdaki üç kayıttan sonra değişmedi. Ölçüm ise ön kaydın açık bıraktığı yerlerde kararlar verdi,
bir iki yerde ön kayda sonradan hizalandı ve ön kayıtta olmayan ölçüler ekledi. Hepsi aşağıda; hükmün hangi pencerede
ve hangi şartlarla okunduğunu değiştirenler başta.

**Ön kaydın açık bıraktığı ya da yorum gerektiren yerler**

- **Hüküm penceresi.** Ön kayıt varsayılan için bütün dönemi örneklem dışı sayar, çünkü varsayılan hiçbir veriye
  bakmadan yazıldı; seçilenin örneklem dışı ise 2024 →'dir. İki sonuç aynı veride kıyaslansın diye ikisinin de hükmü
  2024 → penceresinden verilir; varsayılanın bütün dönem hükmü her tabloda yan sütunda durur. İki pencerenin hükmü
  {{! pencere_ayrisan }}.
- **Birimler.** Ön kayıt {{ K.aile_n | n }} kural ailesi kaydetti; ölçüm {{ T.birim | n }} birimle yapılır. Dört aile
  bölündü: New York ilk dengesi başlangıç saatine (08:00 · 09:30), başarısız kırılım seviyesine (açılış aralığı · Asya
  aralığı · önceki gün), pivot ve fiksing türüne (dönüş · kırılım; momentum · dönüş).{{? len(K.bolunen_aile) == 4 and K.bolunen_aile[0] == "fiks" and K.bolunen_aile[1] == "nyib" and K.bolunen_aile[2] == "pivot" and K.bolunen_aile[3] == "sahte" }}
  Pivot ve fiksingin ön kaydı her tür için ayrı varsayılan taşır.{{? ON.pivot.varsayilan_donus and ON.pivot.varsayilan_kirilim and ON.fiks.varsayilan_momentum and ON.fiks.varsayilan_donus }}
  Başarısız kırılımın ön kayıtlı varsayılanı seviye belirtmez; üç birim aynı varsayılanı kendi seviyesiyle kullanır.{{? ON.sahte.varsayilan.seviye == None }}
  New York ilk dengesinin ön kayıtlı varsayılanı 09:30 başlangıcıdır; 08:00 biriminin varsayılanı ondan yalnız
  başlangıç değiştirilerek türetildi, yani ön kayıtlı değildir.{{? ON.nyib.varsayilan.baslangic_et == "09:30" }}
  Bölünmenin bir sonucu daha var: seçim ve deflated Sharpe'ın deneme sayısı ailenin değil birimin ızgarasıdır.
- **Uygulama eşikleri.** Ön kayıt hüküm kuralının şartlarını yazar ama asgarilerini yazmaz: %95 aralığı en az
  {{ K.uygulama_esik.bootstrap | n }} işlemle kurulur, rastgele yön sınaması en az {{ K.uygulama_esik.rastgele | n }}
  işlemle koşar, koşul analizinin "tuttu" hükmü örneklem dışında en az {{ K.uygulama_esik.kosul_oos | n }} işlem
  ister. Asgariyi karşılamayan sınama kurulmaz ve "çalışıyor"un şartı sağlanmamış sayılır. "Ölçülemedi" yalnız
  örneklem dışında hiç işlem olmayan bileşimdir; az işlemli sonuç hükmünü taşır ve işaretlenir.
- **Tatil.** Ön kayıt tatili tanımlamaz. Tatil takvimden gelir (yukarıda); günün kapsamından okunsaydı gün bitmeden
  bilinemeyecek bir bilgi kullanılmış olurdu.
- **Haber kurallarında tek pozisyon.** Ön kaydın ortak mekaniği "tek pozisyon" der. Haber kurallarında olaylar ayrı
  ayrı koşulup birleştirilir ve kural parite başına bütün olaylara birlikte uygulanır.

**Ölçümün ön kayda sonradan hizalandığı yerler**

- **Ay sonunun tanımı.** Ön kayıt ay sonunu ayın son Londra iş günü olarak tanımlar ve ölçüm de öyle yapar. Ayın son
  hafta içi gününden ayrıştığı aylar, son hafta içi günü bir İngiltere tatiline düşen aylardır:
  {{ K.ay_sonu_kayan | ay_liste }}. O aylarda ay sonu bir önceki iş günüdür.
- **Fiksing ve momentumda stop'un yeri.** Ön kayıt stop'lu fiksing ve momentum kombinasyonlarında stop'u 1·ATR uzağa
  koyar ve R'yi yürütülen giriş fiyatından ölçer; ölçüm stop'u da yürütülen giriş fiyatından 1·ATR uzağa koyar, yani
  bu kombinasyonlarda R birimi ATR'nin kendisidir. Hizalama sonuçlar görüldükten sonra yapıldı: stop sinyal mumunun
  kapanışından ölçüldüğünde, girişi bir mum geciken dönüş kombinasyonlarında fiyat o mumda stop'a yaklaşabiliyor,
  planlanan risk birkaç pipe iniyor ve R'ye bölünen sonuç aşırı büyük değerlere fırlıyordu. Stop'suz varsayılanlar
  etkilenmez; değişen, ızgaranın stop'lu kombinasyonları ve onların arasından yapılan seçimdir.

**Ön kayıtta olmayan ve hükme girmeyen ölçüler**

- **Maliyet.** Başabaş kayma (işlem başına net R'yi sıfıra indiren dolum başına kayma) iki dönemde, bütün dönem ve
  2024 →, R'den ölçülür. Yalnız makas koşusu (kayma ve haber kayması sıfır) merdivenin yanına eklendi; ön kaydın
  merdiveni aynen duruyor.
- **Deflated Sharpe'ın ikinci eşiği.** Ön kayıt Bailey ve López de Prado'nun deflated Sharpe'ını ister. Denemeler
  birbirine çok benzediğinde (aynı kuralın komşu parametreleri) Sharpe'larının yayılımı küçük çıkar ve eşik,
  bağımsız denemelerin şansla üreteceği en yüksek Sharpe'ın altına iner; ikinci eşik o bağımsız denemeler sınırıdır.
- **Havuzun aralığı** gün kümeli bootstrap'le kurulur (yukarıda).
- **Koşul analizinin üç ayrıntısı.** Koşulsuz ortalama değişkenin tanımlı olduğu işlemlerden alınır; aynı ölçünün iki
  adı (Asya aralığı kuralında "aralık" ile "Asya aralığı") tek değişken sayılır; kontrol listesine yalnız en az iki
  paritede aynı kovayla tutan koşul aday olarak girer.
- **Ters seçim.** Koşul analizinin "tuttu" sayısının ne kadarının şansla açıklanabileceğini görmek için aynı ölçüt,
  örneklem içinde ortalamanın altında kalan kovalar seçilerek de koşulur; karşılaştırma dersinde.
- **Örnek günler.** Her kuralın üç örnek işlemi örneklem dışındaki uygun işlemlerden seçilir: kazanan net en az yarım
  R kazandıran, kaybeden en az yarım R kaybettiren ve işlem boyunca lehine yarım R'ye ulaşmamış, tuzak lehine en az
  yarım R gittikten sonra zararla kapanmış işlemdir. Seçim sabit bir çekilişle yapılır (ön kaydın tohumundan,
  kuralın, paritenin ve etiketin adından türer), sonuca bakılarak yapılmaz ve üç örnek ayrı günlerdedir. Uygun işlem
  yoksa kazanan ve kaybeden için yedek tanım (net artı · net eksi) kullanılır ve örneğin altında yazılır. Her örnek
  işlem ayrıca dolum başına yarım pip ek kaymayla yeniden koşulur; alıştırmaların "dolum daha kötü olsaydı" şıkkı bu
  koşudan cevaplanır.{{? K.ornek.esik == 0.5 and K.ornek.ek_kayma == 0.5 }}
- **Kuyruk duyarlılığı.** R ortalaması her işlemi riskine göre büyüklükler; riski makas düzeyine inen tek bir işlem
  ortalamayı taşıyabilir. Her kuralın sonucu ayrıca en iyi işlem çıkarılarak ve beklenen gidiş-dönüş maliyeti
  (girişteki makas, iki dolumun kayması ve haber penceresindeyse haber kayması) riskin yarısını aşan işlemler
  çıkarılarak yeniden ölçülür. R'nin bir tabanı ön kayda girmez; bu ölçü yalnız böyle bir tabanın ne değiştireceğini
  gösterir.
- **Pip ortalaması ve aralığı.** R ortalaması her işlemi riskine göre büyüklükler, pip ortalaması her işlemde aynı
  büyüklükle işlem yapanın sonucudur; ikisinin işareti ayrıştığında strateji dersleri bunu adıyla yazar ve pip
  ortalamasının %95 aralığını da verir.
- **Haber dakikasının makası.** Olay anına göre makasın seyri betimleyici bir ölçüdür; hiçbir kurala ve hükme girmez.

## Haber takvimi

Her olayın saati resmî bir kaynaktan geldi ve kaynak iki türlüdür. **Tarih tarih**: ABD tarım dışı istihdam ve TÜFE
için BLS'nin yayım sayfalarının ambargo satırı (BLS'nin sitesi otomatik istekleri reddettiği için Internet Archive'daki
kopyalarından; her kopyanın arşiv zaman damgası kayıtta), FOMC kararı için karar metninin yayım satırı ("For release
at 2:00 p.m. EDT"), ECB basın toplantısı için karar duyurusunun kendi cümlesi. **Kuraldan**: BoE kararları perşembe
12:00 (Para Politikası Kurulu'nun yayım kuralı; tarih her özetin kendi sayfasından), ECB karar saati ECB'nin 27 Haziran
2022 duyurusundan: {{ O.takvim.sayim.ECB_karar.saat_aralik."13:45 Europe/Berlin"[1] | tarih }} toplantısına kadar 13:45,
{{ O.takvim.sayim.ECB_karar.saat_aralik."14:15 Europe/Berlin"[0] | tarih }} toplantısından itibaren 14:15 Frankfurt. Her
toplantıda kuralın verdiği karar saatinin, duyurunun yazdığı basın toplantısı saatiyle eşleştiği ayrıca sınandı (13:45
↔ 14:30, 14:15 ↔ 14:45).

**FOMC basın toplantısı** saati en zor bulunanıdır. Ne karar metni ne basın toplantısı sayfası onu yazar: sayfadaki tek
saat kararın yayım saatidir. Fed'in aylık etkinlik takvimi basın toplantısını ayrı satırla yalnız
{{ O.takvim.fomc_takvim_donemi.ilk | ay_uzun }} toplantısından itibaren listeler ve o tarihten bu yana
{{ O.takvim.fomc_takvim_donemi.toplanti | n }} toplantının {{ O.takvim.fomc_takvim_donemi.satirli | n }} tanesinde
satır var{% if len(O.takvim.fomc_takvim_donemi.satirsiz) == 1 %} ({{ O.takvim.fomc_takvim_donemi.satirsiz[0] | ay_uzun }}
toplantısında yok){% endif %}{{? O.takvim.fomc_takvim_donemi.satirli == O.takvim.kunye.fomc.basin_saat_kaynagi.takvim and O.takvim.fomc_takvim_donemi.ilk == O.takvim.kunye.fomc.basin_saat_tarih.takvim[0] }}{% if O.takvim.kunye.fomc.basin_saat_kaynagi.duyuru == 1 %};
daha önce tek bir toplantının saatini ayın duyurusu yazar ({{ O.takvim.kunye.fomc.basin_saat_tarih.duyuru[0] | tarih }}){% endif %}.
Kalan {{ O.takvim.kunye.fomc.basin_saat_kaynagi.kural | n }} toplantının saati Fed'in 13 Mart 2013 duyurusundaki
kuraldan gelir: olağan toplantılarda kararın yayım saati {{ O.takvim.kunye.fomc.kural.karar | t }}, başkanın basın
toplantısının başlangıcı "yaklaşık" {{ O.takvim.kunye.fomc.kural.basin | t }} (New York).{{? len(O.takvim.kunye.fomc.kural.yineleme) == 2 and O.takvim.kunye.fomc.kural.yineleme[0].tarih == "2024-08-09" and O.takvim.kunye.fomc.kural.yineleme[1].tarih == "2025-09-05" and O.takvim.kunye.fomc.kural.yineleme[0].saat == O.takvim.kunye.fomc.kural.basin and O.takvim.kunye.fomc.kural.yineleme[1].saat == O.takvim.kunye.fomc.kural.basin }}
Kural Fed'in 2024 ve 2025 toplantı takvimi duyurularında aynen yinelenir.{{? O.takvim.kunye.fomc.kuraldan_farkli == 0 }} Tarih
tarih kaydı olan toplantıların hepsi kuralla aynı saati taşır. Kural yalnız kararı kuralın saatinde yayımlanan olağan
toplantıya uygulandı{% if not O.takvim.sayim.FOMC_basin.olaganustu %}; olağanüstü toplantıların basın toplantısı
kaynakta saatsiz olduğu için takvimde yok{% endif %}. Fiyat kuralla tutarlı: basın toplantısının ilk 15 dakikasında
EUR/USD'nin ortalama dakikalık aralığı, hemen önceki 15 dakikanın (kararın ilk yarım saatinin ikinci yarısı) medyanda
{{ O.takvim.sinama.basin_bilgi.FOMC_basin.EURUSD.medyan | s2 }} katı; {{ O.takvim.sinama.basin_bilgi.FOMC_basin.EURUSD.n | n }}
toplantının {{ O.takvim.sinama.basin_bilgi.FOMC_basin.EURUSD.birden_buyuk | n }} tanesinde 1'in üstünde. Bu bir
doğrulama değildir: oran fiyatın kuralın saatinden sonra hızlandığını gösterir, toplantının hangi dakikada
başladığını göstermez. "Yaklaşık" kelimesi ölçünün sınırıdır; konuşmanın gerçek başlangıcı bir iki dakika kayabilir.
Karar ile basın toplantısının karşılaştırması bir saatlik pencereyle kurulduğu için böyle bir kayma onun içinde kalır;
5 dakikalık ilk haber mumunda ise kayma mumun önemli bir parçasıdır ve N1–N5'in basın toplantısı sonuçları bu
belirsizliği taşır.

Takvimin dışarıda bıraktığı ya da düzelttiği kayıtlar:

{{! takvim_sorun }}

Olağanüstü FOMC toplantıları takvimde kendi saatleriyle durur ({{! olaganustu FOMC_karar }}); saatini
kaynağın yazmadığı olağanüstü ECB ve BoE kararları dışarıdadır, çünkü saati tahmin edilen bir olay haber penceresini
yanlış yere koyardı.

**Fiyat sınaması.** Her olayın saati ayrıca 1 dakikalık fiyattan sınandı. Sıçrama oranı, olay dakikası ve sonraki iki
dakikanın en büyük dakikalık aralığının olaydan önceki otuz ile üç dakika arasının medyan aralığına oranıdır. Resmî
saatte oran {{ O.takvim.sinama.kural.esik | s1 }} ya da üstündeyse olay doğrulanır; bir saat ya da yarım saat önce ya da
sonra oran eşiği aşıyor ve resmî saatinkinin en az iki katıysa çelişki sayılır; ikisi de değilse piyasa o dakikada
kımıldamamıştır (sessiz). Sınama yalnız raporlar: resmî belge birincil kaynaktır ve hiçbir olay fiyat yüzünden
dışarıda bırakılmadı. Çelişki veren olaylar:

{{! celiski }}

{% if len(O.takvim.sinama.celiski_olay) == 2 and O.takvim.sinama.celiski_olay[0].tarih == "2019-12-12" and O.takvim.sinama.celiski_olay[1].tarih == "2020-04-10" %}İkisinin de açıklaması
kaynağın kendisinde. 12 Aralık 2019 ECB toplantısında aday saat basın toplantısının içine düşüyor: o gün fiyatı
kararın kendisi değil toplantı oynattı. 10 Nisan 2020 TÜFE'si Paskalya cumasında, dakikalık aralıkların çok dar
olduğu ince bir piyasada yayımlandı; aday saatlerdeki sıradan gürültü resmî saatten "daha iyi" oturdu.{% else %}Çelişki
veren olayların açıklaması tek tek yazılmalıdır; bu liste değişti.{% endif %}

## Ölçülmeyenler

Bu serinin cevaplamadığı sorular, sonuçların sınırlarıyla birlikte:

- **Gerçek sürpriz.** Açıklanan verinin piyasa beklentisinden (anket medyanı) farkı yok; haber dersindeki büyüklük
  kovaları ilk mumun hareketinden kurulan bir vekildir.
- **Piyasa derinliği.** Dolumlar en iyi bid/ask'tan, sınırsız likiditeyle yapılır; büyük bir emrin fiyatı itmesi ve
  kısmi dolum modellenmez. Kayma sabit pip olarak eklenir.
- **Başka bir likidite kaynağı.** Makas Dukascopy'nin kendi kotasyonudur; bir bankanın ya da başka bir platformun
  gördüğü makastan farklı olabilir. Maliyet merdiveni bu farka duyarlılığı gösterir.
- **Komisyon ve ücretler.** Makas ve kayma dışında maliyet yok sayıldı.
- **Gecelik taşıma.** Bütün pozisyonlar gün sonunda kapandığı için faiz farkı (swap) doğmaz; gece taşıyan bir kuralın
  sonucu farklı olurdu.
- **Gecikme.** Emrin iletilmesi ve kuyruğa girmesi modellenmez; giriş, sinyal mumundan sonraki dakikanın açılışıdır.
- **Gerçek işlem hacmi.** FX'te merkezî hacim yoktur; VWAP kuralları kotasyon likiditesini ağırlık olarak kullanır.
- **Daha kısa zaman dilimleri.** 5 dakikanın altındaki mumlar ve tick verisi ölçülmedi.
- **Başka pariteler.** Yalnız dört majör (EUR/USD, GBP/USD, USD/JPY, AUD/USD); çapraz kurlar ve gelişen piyasa paraları
  yok.
- **Pozisyon büyüklüğü.** Her işlem 1 R'dir; kaldıraç, portföy düzeyinde risk ve kuralların birleşimi ölçülmedi.
- **Uyarlanan kurallar.** Yürüyen pencere dışında rejime göre değişen ya da öğrenen bir model denenmedi.
{% if not T.fomc_basin %}- **FOMC basın toplantıları.** Saatleri resmî kaynaklardan okunamadığı için bu ölçümde basın
  toplantısı olayları ve FOMC karar ile basın toplantısı karşılaştırması yok.
{% endif %}
## Yeniden üretim

Bütün zincir tek komutla yeniden koşar: birim sınamaları (ileriye bakma sınaması dahil), arşivin künyeye karşı
sınanması, veri denetimi, takvimin kurulması ve fiyatla sınanması, bütün stratejilerin koşusu, ölçüm dosyası, şekiller
ve ders metinleri; Python bağımlılıkları sürümleriyle sabittir. Derslerdeki ölçüm sayıları ölçüm dosyasından yazılır.
Bir doğrulayıcı dersleri ölçümden yeniden üretip yayımlanan metinle karşılaştırır ve metindeki her ondalık sayının ve
yüzdenin ya ölçümden ya da adıyla bildirilmiş bir tanım sabitinden (%95 aralığı gibi) geldiğini sınar; ölçümle ayrışan
bir ders yayına giremez. Doğrulayıcının kapsamı bu kadardır: kural tanımlarının sabitleri ve takvim kayıtlarının
tarihleri gibi tam sayılar ve tarihler metne elle yazılıdır; onların doğruluğu kaynağın ve birim sınamalarının işidir.

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
