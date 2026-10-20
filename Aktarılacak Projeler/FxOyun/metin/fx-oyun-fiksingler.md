---
title: 'FX Gün İçi Oyun Planı 3: Fiksingler'
description: "Tokyo fiksingi ve Londra'nın WM/R fiksingi: fiyat fiksinge kadar koşunca fiksingden sonra ne yapıyor? Koşu şansın vereceğinden ne kadar sık geri veriliyor, ne kadar seyrek sürüyor, ay sonu bunu değiştiriyor mu, ve fiksingde koşunun tersine girmek maliyetten sonra ne verdi."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'fiksing', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Serinin şansın ötesinde bir şey söyleyen tek sık anı fiksing: fiksinge koşan fiyat fiksingden sonra koşunun yarısını şansın vereceğinden sık geri veriyor ve koşu şanstan seyrek sürüyor, iki dönemde de. Etki küçük: koşunun tersine girmenin maliyetsiz sonucu hafif artı, makas ve kayma onu eksiye çeviriyor."
seviye: 'orta'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Fiksing bir kurun resmî olarak ölçüldüğü kısa penceredir; Londra'daki WM/R kuru Londra 16:00 (TSİ 18:00, İngiltere
kış saatinde 19:00) çevresindeki beş dakikadan hesaplanır. Bazı fon, şirket ve saklama işlemleri o kura bağlanır; işlemi üstlenen banka riskini çoğu zaman fiksing
çevresinde piyasada kapatır. Bu yüzden fiksinge doğru fiyat bazen bir yöne **koşar**, ve fiksing geçtiğinde o koşuyu
taşıyan akışın bittiği düşünülür. İşlemcilerin bildiği eski söz şudur: "fiksingden sonra koşu geri verilir." Bu ders
sözün sayısını verir. Akışın kendisi bu verinin içinde görünmez; ölçülen yalnız fiyattır.

{{# an_tablo fiksing }}

Bu derste **ilk mum**, fiksinge giden {{ AN.wmr.tf }} dakikalık mumdur: koşunun kendisi. Sınıflar aynı kuralla
kurulur (güçlü koşu, normal koşu, reddedilen koşu, sessiz geçen fiksing) ve plan fiksingden sonraki
{{ AN.wmr.pencere }} dakikayı okur. İzleme fiksing saatinde başlar; WM/R'nin beş dakikalık penceresinin ikinci yarısı
izlenen sürenin içindedir.

## Plan tek cümlede

**Fiksinge koşan fiyat koşunun bir kısmını şansın vereceğinden sık geri verir ve koşu şanstan seyrek sürer; ama fark
küçüktür ve fiksingde koşunun tersine girmenin maliyeti onu yer.** Fiksing, serinin içinde fiyatın kendi şeklinin
ötesinde bir şey söylediği tek sık andır.

## Bu dersi masada nasıl kullanırsın

Fiksing bir kurulum değil, bir saattir. Ders o saatte fiyatın ne yapma eğiliminde olduğunu söyler, ve masada bunun
üç kullanımı var: neyi yapmayacağın (fiksingden sonra koşuyu kovalamazsın), başka bir gerekçeyle pozisyondaysan stopu ve
hedefi koşunun hangi seviyesine göre koyacağın, ve geri vermenin kendisini işlemeye kalktığında neden vazgeçtiğin
(geri verme gerçek ama makas ve kaymadan küçük). Merdiven, fiksinge yarım saat kala sorulacakları sırayla dizer: Tokyo
09:25–09:55 (TSİ 03:25–03:55) ya da Londra 15:30–16:00 (TSİ 17:30–18:00, İngiltere kış saatinde 18:30–19:00). Bir
soru seni sağa gönderdiyse aşağıya inmezsin.

{{# karar fiksing-akis }}

## Fiksingden sonra fiyat nereye gidiyor

Fiksingden sonraki ortalama fiyat, koşunun yönünde ve koşunun boyu cinsinden. Sıfır çizgisi fiksing anındaki fiyattır;
aşağı, koşunun geri verilmesi demektir.

{{# sekil 01_patika "Fiksingden sonra ortalama fiyat yolu, koşunun yönünde" }}

Çizgiler fiksingden hemen sonra hafifçe aşağı iner ve orada kalır: ortalamada koşunun küçük bir kısmı geri verilir.
Büyük bir dönüş ortalamada yok.

## Sınıf sınıf, şansın payıyla

Her sınıfta geri verme, devam ve dönüş payı; yanında yolun aynasında (yön rastgele olsaydı) aynı payın değeri. İki
fiksingin toplamı:

{{# ayna fiksing }}

Açılışlardan farkı burada. Her sınıfta, iki dönemde de, koşunun yarısını geri verme payı aynanın üstünde, sürme payı
aynanın altında. Güçlü koşuda 2018–2023'te geri verme gerçek {{ Y.ic.fiksing.guclu.orta }}, aynada
{{ Y.ic.fiksing.guclu.orta_ayna }} ({{ Y.ic.fiksing.guclu.orta_fark }} puan); sürme {{ Y.ic.fiksing.guclu.devam }} ve
{{ Y.ic.fiksing.guclu.devam_ayna }} ({{ Y.ic.fiksing.guclu.devam_fark }} puan). 2024 → döneminde de fark aynı yönde: geri verme {{ Y.dis.fiksing.guclu.orta_fark }}, sürme {{ Y.dis.fiksing.guclu.devam_fark }} puan.

Koşunun tersine dönmesi, yani koşunun öbür ucunun (fiksinge giden otuz dakikanın en düşüğünün ya da en yükseğinin)
kırılması ise şansla aynı sıklıkta: güçlü koşuda {{ Y.ic.fiksing.guclu.donus }} ve {{ Y.ic.fiksing.guclu.donus_ayna }}.
Fiksingden sonra fiyat geri çekilir, ama koşunun başladığı yere şanstan sık dönmez.

Her fiksing tek tek, iki dönemde:

{{# davranis fiksing }}

### Güçlü koşu

Fiyat fiksinge kadar bir yöne güçlü gitmiş. Yarısını geri verenlerde ortanca süre Tokyo'da
{{ A.ic.tokyo_fiks.guclu.orta_dk }}, Londra'da {{ A.ic.wmr.guclu.orta_dk }} dakika. Yarısını geri veren güçlü
koşuların yalnız {{ D.ic.fiksing.guclu.uc_orta }} kadarı koşunun ucuna geri gitti. Fiyat geri çekilince çoğu zaman
orada kalıyor. (Açılışta aynı oran {{ D.ic.acilis.guclu.uc_orta }}; ama açılış iki üç saat, fiksing bir saat
izleniyor, iki sayı aynı süreyi ölçmüyor.)

### Masada: fiksinge güçlü koşu

Grafikte güçlü koşu, fiksinge giden yarım saatin toplamda bir yöne belirgin gitmesidir; tek tek mumların aynı yöne
dizilmesi gerekmez, sınıfı yarım saatin toplamı verir. Masada önce üç seviye çizilir: koşunun başladığı yer, yarısı ve
ucu.

{{# sema kosu-guclu }}

Güçlü koşuların yaklaşık yarısı ({{ D.ic.fiksing.guclu.orta }}) yarıya geri çekilir; başa dönüş şanstan sık değildir.
Saatin en olası görüntüsü fiyatın koşunun ucu ile başı arasında durmasıdır.

{{# kart guclu-kosu }}

{{# ornek wmr-guclu }}

İki koşu (①) aynı sınıftadır ama biçimleri ayrılır: üstteki günde (26 Mayıs 2023) aşağı koşunun çoğu ilk çeyrek
saatte gelir ve fiyat fiksinge kadar dibin biraz üstünde yatay kalır; alttaki günde (25 Temmuz 2023) yükseliş son
yirmi beş dakikada gelir ve fiksingdeki fiyat tepenin hemen altındadır. Üstteki günde fiyat fiksingden sonra kırk
dakika dip ile yarı (②) arasında oyalanır, dibi yeniden kırmaz, yarıya ancak TSİ 18:52'de dokunur (③) ve ④'te yarının
hemen ötesinde biter. Alttaki günde fiyat ilk mumda tepeyi aşar, kısa bir geri çekilmede yarıya inmez (③ yok) ve TSİ
18:25'ten sonra yükselerek ④'te ucun koşu boyunun yarısından fazla ötesindedir. Biçim farkı bu derste ayrı bir okuma
olarak ölçülmedi; tek bir çift gün kuralı ne doğrular ne yanlışlar.

### Normal ve reddedilen koşu

Normal koşu {{ Y.ic.fiksing.normal.orta }}, reddedilen koşu {{ Y.ic.fiksing.reddedilen.orta }} yarısını geri verdi;
aynada {{ Y.ic.fiksing.normal.orta_ayna }} ve {{ Y.ic.fiksing.reddedilen.orta_ayna }}. Geri verme çoğu zaman hemen olur:
ortanca süre {{ A.ic.wmr.normal.orta_dk }} dakika. Fark burada da aynı yönde ama güçlü koşudakinden küçük.

### Masada: normal ve reddedilen koşu

Normal ya da reddedilen koşuda yarım saat bir yöne gitmiştir ama gövde dolu değildir, ya da bir uçta uzun bir fitil
durur. Masada fark edilecek ilk şey, fiksingdeki fiyatın koşunun yarısına ne kadar yakın olduğudur.

{{# sema kosu-normal }}

Yarı yakın olduğu için geri çekilme hızlıdır, ama yön bilgisi olmayan bir yolda da sık olur; reddedilen koşunun uzun
fitili de normal koşudan farklı bir davranış vermedi.

{{# kart normal-kosu }}

{{# ornek tokyo-normal }}

İki aşağı koşu (①) aynı sınıftadır ve iki günde de fiksingdeki fiyat yarıya (②) çok yakındır, ama üstteki koşu
(8 Eylül 2023) alttakinin (20 Kasım 2023) birkaç katıdır: dibini uzun bir fitille yapıp fiksinge kadar yarıya geri
gelmiştir, alttaki dar ve düzensizdir. Üstteki günde fiyat fiksingden sonraki beş dakikada yarıya dokunur (③), TSİ
04:25'te koşunun başına neredeyse varır ve ④'te yarının belirgin ötesindedir. Alttaki günde fiyat ilk mumda koşunun
dibini kırar, yarıya hiç dokunmaz (③ yok) ve ④'te dibin iki koşu boyundan fazla altındadır. Normal koşuda yarıya dönüş
zaten sık olan bir harekettir.

### Sessiz fiksing

Fiksinge giden mum küçükse fiksing anında piyasada ciddi bir akış görünmez. Fiksingden sonra fiyatın kırılan tarafta
bir mum boyu daha ilerleme payı:

{{# kucuk fiksing }}

Londra fiksinginde sessiz bir fiksingden sonraki kırılım çoğu zaman bir yere gitmiyor: kırılan tarafta bir mum boyu
ilerleme {{ K.ic.wmr.ilerle }} (2024 → {{ K.dis.wmr.ilerle }}). Tokyo'da pay daha yüksek
({{ K.ic.tokyo_fiks.ilerle }}, 2024 → {{ K.dis.tokyo_fiks.ilerle }}). Londra fiksingi Avrupa masalarının günü kapattığı
saate, Tokyo fiksingi ise Asya gününün ortasına denk gelir; fark buradan geliyor olabilir, bu derste ölçülmedi.

### Masada: sessiz fiksing

Sessiz bir fiksingin grafiği boştur ve boşluk bir şey yapma isteği doğurur: fiksingden sonra dar aralığın bir kenarı
kırılınca kırılım "akış şimdi geldi" diye okunur.

{{# sema sessiz-kirilim }}

{{# kart sessiz }}

## Ay sonu

Piyasadaki yaygın öncüle göre ayın son Londra iş günü portföyler ay boyunca kurdaki değişime göre yeniden dengelenir ve
bu işlemlerin bir kısmı WM/R kuruna bağlanır; öncülün kendisi bu derste ölçülmedi. Ölçülen, ay sonu fiksinginden
sonraki fiyattır:

{{# sekil 02_ay_sonu "Ay sonu ile öbür günler: güçlü koşudan sonra devam ve geri verme" }}

{{# ay_sonu }}

Ay sonunda Londra fiksingine güçlü koşan fiyatın fiksingden sonra sürme payı öbür günlerden de düşük:
{{ F.wmr.ic.ay_sonu.guclu.devam }} (öbür günler {{ F.wmr.ic.diger.guclu.devam }}); 2024 → döneminde
{{ F.wmr.dis.ay_sonu.guclu.devam }} (öbür günler {{ F.wmr.dis.diger.guclu.devam }}). Bir olası açıklama, ay sonu
koşusunun fiksingde biten bir akış olmasıdır; bu derste ölçülmedi. Ay sonunda geri verme payı ise iki dönemde farklı
yöne bakıyor: 2018–2023'te {{ F.wmr.ic.ay_sonu.guclu.orta }} (öbür günler {{ F.wmr.ic.diger.guclu.orta }}), 2024 →
döneminde {{ F.wmr.dis.ay_sonu.guclu.orta }} (öbür günler {{ F.wmr.dis.diger.guclu.orta }}). Ay sonu yılda on iki kez
gelir; 2024 → döneminde güçlü ay sonu koşusu dört paritede toplam {{ F.wmr.dis.ay_sonu.guclu.n }} olay. "Ay sonunda
koşu sürmez" okuması iki dönemde de aynı, "ay sonunda koşu daha çok geri verilir" okuması değil.

Tokyo fiksinginde ay sonu ayrımı tutarlı değil. 2024 → döneminde normal koşudan sonra tersine dönüş ay sonunda
{{ F.tokyo_fiks.dis.ay_sonu.normal.donus }} (öbür günler {{ F.tokyo_fiks.dis.diger.normal.donus }}), ama 2018–2023'te
{{ F.tokyo_fiks.ic.ay_sonu.normal.donus }} ve {{ F.tokyo_fiks.ic.diger.normal.donus }}. İki dönemde aynı yöne bakmayan
bir fark okumaya girmez.

### Masada: ay sonu günü

Ay sonunun grafikte bir izi yoktur; fark takvimdedir ve masaya önceden yazılır. Ayın son Londra iş günü Londra
fiksingi Londra 16:00'da, TSİ 18:00'de (İngiltere kış saatinde 19:00'da) gelir.

{{# sema ay-sonu }}

{{# kart ay-sonu }}

## Trend

Fiksingde de trend bir şey değiştirmiyor: güçlü koşu trend yönündeyken {{ T.fiksing.guclu.trendle.devam }}, trende
karşıyken {{ T.fiksing.guclu.karsi.devam }} sürdü.

<details>
<summary>Trend ayrımı tablosu (2018–2023)</summary>

{{# trend fiksing }}

</details>

## Bu okumaları işleme çevirmek

"Fiksingden sonra koşu geri verilir" sözünün sınanan işlem hâli şudur: fiksing anında koşunun tersine piyasa emriyle
girilir, stop koşunun ucunun {{ ref_tampon }} koşu boyu ötesine, hedef koşunun yarısına konur. Sessiz fiksingde tepki
aralığın iki kenarına birer stop emridir; biri dolunca öbürü iptal olur. 2024 → dönemindeki sonuç:

{{# kisa referans fiksing }}

Dördü de "çalışmıyor", ama sebebi açılışlardan farklı. Burada maliyetten önce küçük bir kenar var ve ayna ölçüsünün
bulduğu geri vermeyle uyumlu. Koşunun tersine girmenin maliyetsiz sonucu 2018–2023'te normal koşuda
{{ B.referans.fiksing.normal.ic.brut }} R, reddedilende {{ B.referans.fiksing.reddedilen.ic.brut }} R, güçlü koşuda
{{ B.referans.fiksing.guclu.ic.brut }} R. 2024 → döneminde küçüldü ({{ B.referans.fiksing.normal.dis.brut }},
{{ B.referans.fiksing.reddedilen.dis.brut }} ve {{ B.referans.fiksing.guclu.dis.brut }} R).

Maliyet ondan büyük. Fiksingde koşunun tersine girmek bir piyasa emridir, makas ve kayma öder, ve stop yakındır
(ortanca risk {{ B.referans.fiksing.normal.dis.risk_pip }} pip). Maliyetin payı normal koşuda
{{ B.referans.fiksing.normal.dis.maliyet }} R, güçlü koşuda {{ B.referans.fiksing.guclu.dis.maliyet }} R. Güçlü koşuda
kazanma oranı düşük ({{ B.referans.fiksing.guclu.dis.kazanma }}): hedef koşunun yarısı olduğu için kazanan işlem
riskinin yaklaşık bir katını kazanıyor (ortalama {{ B.referans.fiksing.guclu.dis.kazanc }} R) ve başa baş için
{{ B.referans.fiksing.guclu.dis.basabas }} yetiyor, ama işlemlerin {{ B.referans.fiksing.guclu.dis.stop_pay }} kadarı
stopta bitti: koşu fiksingden sonra ucunu {{ ref_tampon }} koşu boyu aşınca stopa geldi.

2018–2023'te fiksinglerin hiçbir sınıfında denenen tepkilerin (daha geniş stop, daha yakın ya da uzak hedef) hiçbiri
maliyetten sonra artıda kalmadı; plan bütün fiksing hücrelerinde "izle, işlem açma" der.

### Masada: koşunun tersine girmek

Geri vermenin en düz işlemi fiksing anında koşunun tersine girmektir. Şema bu işlemin üç seviyesini ve maliyetin
nereden geldiğini gösterir.

{{# sema ters-giris }}

Güçlü koşuda stop sık gelir ve kazanma oranı düşüktür. Normal koşuda tablo tersine döner: hedef yakın, stop uzak,
kazanma oranı yüksek, başa baş için gereken oran ondan da yüksek.

{{# kart ters-giris }}

## Emri nereye koyarsın

Emrin genel kuralları 1. derstedir (1. ders, Emri nereye koyarsın); fiksinge özgü olanlar şunlar. Pencere Tokyo
09:25–10:55 (TSİ 03:25–04:55), Londra 15:30–17:00'dir (TSİ 17:30–19:00, İngiltere kış saatinde 18:30–20:00).

- **Giriş.** Koşunun tersine sınanan giriş fiksing anında piyasa emridir; makas ve kaymayı o anda öder. Koşunun ucuna
  ya da yarısına konan limit fiksing için ölçülmedi. Sessiz fiksingde sınanan biçim iki kenara birer stop emridir;
  biri dolunca öbürü iptal olur (3. ders, Sessiz fiksing).
- **Stop.** Koşunun ucunun {{ ref_tampon }} koşu boyu ötesinde. Stopu daraltmak riski küçültmez, maliyeti R cinsinden
  büyütür; daha geniş stop da 2018–2023'te artıda kalmadı (3. ders, Bu okumaları işleme çevirmek). Koşunun yönündeysen
  yarı ile uç arasındaki stopu geri verme sık görür.
- **Hedef.** Koşunun yarısı, başladığı yer değil. Koşunun yönündeki hedef uzamaya az dayanır, ay sonunda daha da az
  ({{ F.wmr.ic.ay_sonu.guclu.devam }} ve {{ F.wmr.dis.ay_sonu.guclu.devam }}; öbür günlerde
  {{ F.wmr.ic.diger.guclu.devam }} ve {{ F.wmr.dis.diger.guclu.devam }}; 3. ders, Ay sonu).
- **Süre.** Bekleyen emir fiksing anından {{ AN.wmr.pencere }} dakika sonra düşer (ön kayıttaki süre, ölçülerek
  seçilmedi); dolan pozisyon ne hedefe ne stopa varırsa izlenen sürenin sonunda, yani aynı anda kapanır.
- **Haber.** Takvimdeki büyük haberler fiksing pencerelerine düşmez; WM/R'nin beş dakikasında makasın davranışı bu
  derste ölçülmedi.

## Sık yapılan hatalar

- **Hedefi koşunun başladığı yere koymak.** Geri verme şanstan sık, tam dönüş değil. Dayanak: 3. ders, Sınıf sınıf,
  şansın payıyla.
- **Ay sonunda geri vermeye daha çok güvenmek.** O fark iki dönemde ters yöne baktı. Dayanak: 3. ders, Ay sonu.
- **Fiksing okumasını trende göre değiştirmek.** Dayanak: 3. ders, Trend.

## Masa kontrol listesi

1. Hangi fiksing: Tokyo 09:55 (TSİ 03:55) mı, Londra 16:00 (TSİ 18:00, İngiltere kış saatinde 19:00) mı?
2. Bugün ayın son Londra iş günü mü?
3. Fiksinge giden yarım saat (Tokyo 09:25–09:55, TSİ 03:25–03:55; Londra 15:30–16:00, TSİ 17:30–18:00, İngiltere kış
   saatinde 18:30–19:00) hangi sınıfta: güçlü, normal, reddedilen ya da sessiz?
4. Koşunun başladığı yeri, yarısını ve ucunu işaretledin mi?
5. Fiksingdeki fiyat yarıya ne kadar yakın? Yakınsa yarıya dokunuş bir şey söylemeyecek.
6. Koşunun yönünde yeni bir işlem mi düşünüyorsun? Öyleyse durursun.
7. Geri vermeyi işlemek mi istiyorsun? Maliyetin geri vermeden büyük olduğunu biliyorsun.
8. Başka bir gerekçeyle pozisyondaysan stopun ve emrin koşunun üç seviyesine göre nerede?
9. Fiksingden sonraki bir saat (Tokyo 09:55–10:55, TSİ 03:55–04:55; Londra 16:00–17:00, TSİ 18:00–19:00, İngiltere
   kış saatinde 19:00–20:00) dolunca dolmayan emir düşer, hedefe ya da stopa varmayan pozisyon kapanır; ikisini de
   yaptın mı?

## Grafik okuma alıştırmaları

**1.** Londra fiksingi, İngiltere yaz saati. TSİ 17:30 ile 18:00 arasında fiyat altı mumla aynı yöne gitti ve
fiksingdeki fiyat koşunun ucuna yakın ({{# atif sema kosu-guclu }}'deki gibi). TSİ 18:05'te biten mum koşunun ucunu aşarak kapanıyor. Ne
yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Kovalamazsın: koşunun sürme payı şansın altında ve bu ilk uzama tam da seyrek süren harekettir (3. ders, Sınıf sınıf,
şansın payıyla). Tersine de bu mumla girmezsin: ucu aşan mum, tersine girenin stopunun alındığı yerdir (3. ders, Bu
okumaları işleme çevirmek). Üç seviyeyi işaretleyip fiyatın yarıya gelip gelmediğine bakarsın; gelmezse kural
yanlışlanmış olmaz.

</details>

**2.** Tokyo fiksingi. TSİ 03:25 ile 03:55 arasındaki koşunun gövdesi dolu değil ve fiksingdeki fiyat yarıya çok yakın
({{# atif sema kosu-normal }}'teki gibi). Masadaki biri yarıya dönüşün neredeyse kesin olduğunu, tersine girip yarıyı hedeflemenin kolay
bir işlem olduğunu söylüyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Yarıya dönüş sık olur, ama yarı yakın olduğu için aynada da sık olur (3. ders, Normal ve reddedilen koşu). Hedef yakın,
stop uzak: işlemlerin yarısından çoğu kazanır, kazanan küçük kazanır ve başa baş için gereken oran ölçülen kazanma oranının
üstünde kalır (1. ders, Kazanma oranı ile net sonuç; 3. ders, Bu okumaları işleme çevirmek). Girmezsin, yalnız izlersin.

</details>

**3.** Tokyo fiksingi, TSİ 03:55. Başka bir gerekçeyle güçlü koşunun tersine girmek istiyorsun ({{# atif sema ters-giris }}). Piyasa emri mi,
koşunun ucuna limit mi; stop ve hedef nerede, emir ne zaman çekilir?

<details>
<summary>Çözüm</summary>

Piyasa emri makas ve kaymayı fiksing anında öder. Ucuna konan limit girişte ödemez ama yalnız fiyat koşunun yönünde
yeniden yürürse dolar; büyük mumda bu tür tersine limit maliyetten önce kapanışta piyasa emrinden kötü çıktı (8. ders,
Limit neden ucuz görünür: ters seçim; fiksing için ölçülmedi). Stop koşunun ucunun {{ ref_tampon }} koşu boyu
ötesinde, hedef yarıdadır (3. ders, Bu okumaları işleme çevirmek). Dolmayan limit fiksingden bir saat sonra, Tokyo
10:55'te (TSİ 04:55) düşer; dolan pozisyon hedefe ya da stopa varmazsa aynı anda kapanır.

</details>

## Fiksing için masa kartı

- **Fiksinge koşan fiyattan sonra bir geri çekilme beklenir.** Koşunun yarısına kadar geri gelmesi şanstan sıktır;
  yarıya dönenlerde ortanca süre güçlü koşuda çeyrek saat, normal koşuda birkaç dakika.
- **Geri verme beklenir, dönüş beklenmez.** Koşunun başladığı yer şanstan sık kırılmaz.
- **Fiksingden sonra koşunun yönünde yeni işlem açmak, sürmeyen bir hareketi kovalamaktır.** Koşunun sürme payı
  şansın altında; ay sonunda Londra'da daha da altında.
- **Sessiz bir Londra fiksinginden sonraki kırılım çoğu zaman bir yere gitmez.**
- **Fiksingdeki küçük kenar işlenebilir değil.** Geri vermenin büyüklüğü makas ve kaymayı karşılamıyor; plan burada
  da işlem önermiyor.
