---
title: 'FX Gün İçi Stratejiler 8: Metodoloji — Veri, Saat, Yürütme, Ön Kayıt ve Ölçülmeyenler'
description: "Serinin bütün sayılarının nasıl üretildiği: Dukascopy 1 dakikalık bid/ask arşivinin indirilmesi ve denetimi, saat ve yaz saati kuralları, yürütme mekaniği (giriş, stop, hedef, gün sonu, maliyet), örneklem bölmesi, sonuçtan önce yazılan ön kayıt ve sonradan değişen her madde, seçim ve sağlamlık ölçüleri, haber takviminin kaynakları ve dışarıda kalan olaylar, ve bu serinin ölçmediği şeylerin listesi."
pubDate: 2026-10-16
tags: ['fx', 'gun-ici', 'backtest', 'metodoloji', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · BLS, Fed, ECB, BoE resmî kaynakları · önceden kayıt'
ozet: "Bir backtest'in sonucu, nasıl ölçüldüğü kadar güvenilirdir. Bu ders serinin makinesini açar: hangi fiyat, hangi saat, hangi dolum kuralı; ne önceden yazıldı, ne sonradan değişti; ve hangi soruların hiç sorulmadığı."
seviye: 'ileri'
onkosul:
  - fx-gunici-giris
---

Önceki yedi ders sonuçları anlattı. Bu ders sonuçların nasıl üretildiğini anlatır ve iki amaca hizmet eder. Birincisi
denetlenebilirlik: bir okurun bir sayıya itiraz edebilmesi için o sayının hangi fiyattan, hangi saatte ve hangi
kuralla ölçüldüğünü bilmesi gerekir. İkincisi dürüstlük: bir backtest'in en sık kusuru bir kuralın sonuca bakılarak
seçilmesi ya da değiştirilmesidir. Burada neyin sonuçtan önce yazıldığı, neyin sonradan değiştiği ve değişenin
gerekçesi adıyla durur.

## Veri: kaynak, indirme, arşiv

Fiyat verisi Dukascopy'nin herkese açık beslemesinden gelir: her parite ve her gün için iki dosya, 1 dakikalık **bid**
ve **ask** mumları. İki taraf ayrı indirildiği için her dakikanın gerçek makası bilinir: alış ask'tan, satış bid'den
yürütülür ve makas maliyete ayrıca eklenmez, fiyatın kendisindedir. Strateji mumları (5, 15, 60 dakika) 1 dakikalık
orta fiyattan kurulur ve çıpalıdır: Londra 08:00 ve New York 08:30 gibi seans açılışları her zaman bir mumun başına
denk gelir.

Arşiv bulut koşucularında indirildi. Kaynak isteklerin önemli bir kısmını geri çevirir (HTTP 503 ve zaman aşımı);
indirici geri çevrilen dosyayı erteleyip yeniden ister ve bir yıl birimi ancak bütün günleri indiğinde tamamlanmış
sayılır. Bu yüzden birimler birden çok koşuda tamamlandı. Her birimin içerik özü (SHA-256) künyede durur ve dosya her
okunuşta ona karşı sınanır: arşivde sessizce değişen bir dosya ölçüme giremez.

{{! arsiv_ozet }}

{% if T.eksik_birim %}_Tamamlanmayan {{ T.eksik_birim | n }} yıl biriminde {{ T.inmeyen_gun | n }} işlem günü inmedi:
o günler ölçümde yoktur, hangi günler oldukları künyede adıyla durur ve sonuçların kapsamı bu kadar eksiktir._{% else %}_Bütün yıl
birimleri tamamlandı: dört paritenin bütün işlem günleri arşivde._{% endif %}

Veri denetimi giriş dersinde (kapsam, tatil, makas, sıçrama adayı ve Dukascopy'nin kendi saatlik mumlarıyla çapraz
sınama). Denetim veriyi **değiştirmez**: sıçrama adayları sayılır ve listelenir, düzeltilmez ya da atılmaz. Kapsamı
%50'nin altında kalan işlem günleri (Noel, yılbaşı) tatil sayılır ve stratejiler o günlerde işlem açmaz.

## Saat

Bütün zaman damgaları UTC olarak saklanır; yerel saatler (Londra, New York, Frankfurt) IANA saat dilimi tablosundan
çevrilir ve hiçbir saat farkı elle yazılmaz. FX günü New York 17:00'da başlar ve biter. İşlem saatleri okura TSİ
olarak verilir (UTC+3, yaz saati yok); olay saatleri ayrıca kendi yerel saatleriyle. Yaz saati geçişleri her yıl için elle yazılmış bir listeye karşı sınanır; Londra ile New
York'un farklı haftalarda saat değiştirdiği ara dönemler giriş dersindeki tablodadır.

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
- **Hedef.** Limit emirdir ve kaymaz. Stop ile hedef aynı strateji mumunun içinde değmişse sıra 1 dakikalık
  veriyle çözülür; aynı dakikada ikisi birden değmişse **stop** sayılır (tutucu varsayım).
- **Gün sonu ve tek pozisyon.** Bütün pozisyonlar en geç {{ K.gun_sonu_et | t }} New York'ta kapanır; gece ve hafta
  sonu pozisyon taşınmaz. Aynı anda tek pozisyon vardır; açık pozisyon varken gelen sinyal atlanır.
- **Maliyet.** Makas gerçek bid/ask'tadır. Üstüne her piyasa dolumuna (giriş, zaman çıkışı, stop) temel senaryoda
  {{ K.temel_kayma_pip | s1 }} pip kayma eklenir; maliyet merdiveni aynı işlemleri {{ K.kayma_pip[0] | s1 }},
  {{ K.kayma_pip[1] | s1 }}, {{ K.kayma_pip[2] | s1 }} ve {{ K.kayma_pip[3] | s1 }} pip kaymayla yeniden ölçer.
  Haber penceresinde (olaydan {{ K.haber_pencere_dk[0] | n }} dakikadan {{ K.haber_pencere_dk[1] | n }} dakikaya)
  kayma {{ K.haber_kayma_pip | s1 }} pip daha büyüktür.
- **R.** Bir işlemin R'si net sonucunun planlanan riske oranıdır: yürütülen giriş fiyatından stop seviyesine uzaklık.
  Stop'suz kurallarda R birimi girişteki ATR(14)'tür.

**İleriye bakma sınaması.** Her strateji biriminin varsayılanı ve rastgele seçilen dört kombinasyonu iki kez yeniden
koşulur: bir kez veri belirli bir anda kesilerek, bir kez o andan sonraki bütün fiyatlar bozularak. O andan önce
verilmiş her sinyal ve açılmış her işlem üç koşuda birebir aynı olmalıdır; bir kural geleceğe bakıyorsa kesmek ya da
bozmak geçmişteki sinyalini değiştirir ve sınama düşer.

## Örneklem, seçim ve sağlamlık

Örneklem içi {{ K.baslangic | tarih }} → {{ K.ic_bitis | tarih }}, örneklem dışı {{ K.dis_baslangic | tarih }} →
{{ K.bitis | tarih }}. Her kural iki biçimde ölçülür. **Varsayılan**, veriye bakmadan seçilmiş ders kitabı hâlidir;
hükmü o verir. **Seçilen**, parametre ızgarasından yalnız örneklem içinde, günlük R serisinin yıllık Sharpe'ıyla ve en
az {{ K.secim.asgari_islem | n }} işlem (haber kurallarında {{ K.secim.asgari_islem_haber | n }}) şartıyla seçilen
kombinasyondur; örneklem dışında ayrıca sınanır. {{ T.birim | n }} birimin ızgaralarında toplam
{{ T.kombinasyon | n }} kombinasyon var.

- **Deflated Sharpe** (Bailey ve López de Prado, 2014): ızgaradan seçilen en iyi kombinasyonun Sharpe'ı, o ızgaranın
  deneme sayısıyla şansla beklenen en yüksek Sharpe'a karşı sınanır.
- **Yürüyen pencere:** {{ K.saglamlik.walk_forward_ilk_test_yili | t }}'den itibaren her yıl için yalnız önceki
  yılların verisiyle seçim yapılır ve o yılda sınanır.
- **Aralık:** işlem başına net R'nin %95 aralığı {{ K.hukum_kurali.bootstrap_tekrar | n }} tekrarlı bootstrap'le.
- **Rastgele yön:** aynı giriş ve çıkış dakikaları, aynı risk, yön yazı turayla; {{ K.hukum_kurali.rastgele_tekrar | n }}
  tekrar.
- **Hüküm:** örneklem dışı net ortalama artı, aralığın alt ucu sıfırın üstünde ve rastgele yön dağılımında
  {{ K.hukum_kurali.rastgele_esik_yuzdelik | n }}. yüzdelik ya da üstü ise **çalışıyor**; ortalama artı ama öbür
  şartlardan biri tutmuyorsa **zayıf**; ortalama sıfır ya da eksiyse **çalışmıyor**. Brüt sonucun aralığı sıfırın
  üstünde ama net sonuç eksiyse ayrıca **maliyet** bayrağı.
- **Koşullar:** on dört değişken{{? len(K.kosul.degiskenler) == 14 }}; sürekli değişkenlerde kova sınırları (terciller)
  yalnız örneklem içinden kurulur ve örneklem dışına taşınır. Örneklem içinde ortalamanın üstündeki, en az
  {{ K.kosul.asgari_kova_islem | n }} işlemli kovalar seçilir; seçim örneklem dışında artı kalır, tamamlayanını aşar
  ve en az yirmi işlemle ölçülürse "tuttu".

### Ön kayıt

Kuralların, ızgaraların, varsayılanların ve hüküm kuralının hepsi tek bir ön kayıt dosyasında, hiçbir backtest
sonucu görülmeden yazıldı ve kaydedildi. Sonradan değişen her madde ayrı bir kayıtla, gerekçesiyle değişti:

{{! onkayit_tablo }}

[Ön kaydın tam metni](/arastirma/fx-gunici/onkayit.toml) sayfayla birlikte yayımlanır; dosyanın SHA-256 özü
`{{ K.onkayit_ozu | t }}`. İkinci kayıt haber devam tablosunu ekledi: o sırada depoya iki veri parçası inmişti
(EUR/USD 2018'in ilk fiyat parçası ve FOMC duyurularının ham sayfaları), ama hiçbiri okunmamış, takvim
ayrıştırılmamış ve hiçbir haber olayı ölçülmemişti. Üçüncü kayıt yalnız bu notun kendisini düzeltti.

### Ön kayıttan sonra yapılanlar

Dört şey ön kayıttan sonra yapıldı; hiçbiri bir kuralı, bir ızgarayı, bir varsayılanı ya da hüküm kuralını
değiştirmedi:

1. **İki eksik ölçü.** Ön kaydın istediği iki ölçü ilk koşulara girmemişti: fiksing kurallarında ay sonunun ayrı
   raporu ve gün içi momentumun öngörü gücü regresyonu (Newey–West standart hatasıyla). İkisi de tam koşudan önce
   eklendi.
2. **Ay sonunun tanımı.** Kod ayın son hafta içi gününü alıyordu; ön kayıt "ayın son Londra iş günü" diyor. Kod ön
   kayda göre düzeltildi (ön kayıt değil): ayın son hafta içi günü İngiltere tatiline düşen beş ay bir önceki iş
   gününe kaydı.
3. **Haber dakikasının makası.** Olay anına göre makasın seyri betimleyici bir ölçüdür; hiçbir kurala ve hükme girmez.
4. **Ters seçim.** Koşul analizinin "tuttu" sonuçları kısmi koşularda kalabalık göründü; ne kadarının şansla
   açıklanabileceğini ölçmek için aynı ölçüt, örneklem içinde en kötü kovalar seçilerek de koşuldu. Ön kayıtta yoktu,
   hiçbir hükmü değiştirmez; karşılaştırma dersinde.

## Haber takvimi

Her olayın saati kendi resmî kaynağından, tarih tarih okundu: ABD tarım dışı istihdam ve TÜFE için BLS'nin yayım
sayfalarının ambargo satırı (BLS'nin sitesi otomatik istekleri reddettiği için Internet Archive'daki kopyalarından;
her kopyanın arşiv zaman damgası kayıtta), FOMC için Fed'in basın duyuruları, ECB için karar duyuruları, BoE için Para
Politikası Kurulu kararlarının özet sayfaları. ECB karar saati {{ O.takvim.sayim.ECB_karar.saat_aralik."13:45 Europe/Berlin"[1] | tarih }}
toplantısına kadar 13:45, {{ O.takvim.sayim.ECB_karar.saat_aralik."14:15 Europe/Berlin"[0] | tarih }} toplantısından
itibaren 14:15 Frankfurt'tur; takvim her toplantının kendi saatini taşır.

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

Bütün zincir tek komutla yeniden koşar: arşivin künyeye karşı sınanması, veri denetimi, takvimin kurulması ve fiyatla
sınanması, bütün stratejilerin koşusu, ölçüm dosyası, şekiller ve ders metinleri. Derslerdeki her sayı ölçüm
dosyasından yazılır; bir doğrulayıcı dersleri ölçümden yeniden üretip yayımlanan metinle karşılaştırır ve metindeki
her ondalık sayının ölçümden geldiğini sınar. Elle yazılmış bir sayı ya da ölçümle ayrışan bir cümle yayına giremez.

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
