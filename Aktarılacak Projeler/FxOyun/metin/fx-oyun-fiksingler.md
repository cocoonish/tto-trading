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

Fiksing bir kurun resmî olarak ölçüldüğü kısa penceredir; Londra'daki WM/R kuru 16:00 çevresindeki beş dakikadan
hesaplanır. Bazı fon, şirket ve saklama işlemleri o kura bağlanır; işlemi üstlenen banka riskini çoğu zaman fiksing
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

Grafikte güçlü koşu, fiksinge giden yarım saatin beş dakikalık mumlarının aynı yöne dizilmesidir; sınıfı veren tek tek
mumlar değil, yarım saatin toplamıdır. Masada önce üç seviye çizilir: koşunun başladığı yer, yarısı ve ucu.

{{# sema kosu-guclu }}

Yarıya geri çekilme beklenir ve çoğu zaman erken gelir (ortanca süre Londra'da {{ A.ic.wmr.guclu.orta_dk }}, Tokyo'da
{{ A.ic.tokyo_fiks.guclu.orta_dk }} dakika). Başa dönüş beklenmez: koşunun öbür ucunun kırılması şansla aynı sıklıkta.
Yarıya gelen fiyatın ucuna yeniden gitmesi de seyrek. Fiksingden sonraki saatin en olası görüntüsü, fiyatın koşunun
ucu ile başı arasında durmasıdır.

Bu durumda yapmazsın: fiksingden hemen sonra koşunun ucunu aşan ilk mumun arkasından girmezsin, hedefi koşunun
başladığı yere koymazsın, yarıya gelen fiyatı yeni bir yönün başlangıcı diye okumazsın.

{{# kart guclu-kosu }}

{{# ornek wmr-guclu }}

İki gün fiksinge kadar birbirinin aynısıdır: gölgeli mumlar (①) aynı yöne dizilir ve fiksingdeki fiyat koşunun ucuna
yakındır. Üstteki günde fiyat fiksingden sonra koşunun yarısına (②) iner, ilk dokunuş ③'te görülür ve ④'e kadar
koşunun başladığı yere varmaz. Alttaki günde ilk mumlar üstteki kadar kararsızdır, ama fiyat yarıya hiç gelmez,
koşunun ucunu aşar ve pencere boyunca yarının koşu tarafında kalır; ③ bu yüzden yoktur. Fiksing anında iki günü
ayıracak bir şey grafikte yoktur; üstteki gün ancak sonu bilindiği için "belli" görünür. İki gün kuralı ne doğrular ne
yanlışlar: kural birinci türün daha sık geldiğini söyler, ikincinin gelmeyeceğini değil.

### Normal ve reddedilen koşu

Normal koşu {{ Y.ic.fiksing.normal.orta }}, reddedilen koşu {{ Y.ic.fiksing.reddedilen.orta }} yarısını geri verdi;
aynada {{ Y.ic.fiksing.normal.orta_ayna }} ve {{ Y.ic.fiksing.reddedilen.orta_ayna }}. Geri verme çoğu zaman hemen olur:
ortanca süre {{ A.ic.wmr.normal.orta_dk }} dakika. Fark burada da aynı yönde ama güçlü koşudakinden küçük.

### Masada: normal ve reddedilen koşu

Normal ya da reddedilen koşuda yarım saat bir yöne gitmiştir ama gövde dolu değildir, ya da bir uçta uzun bir fitil
durur. Masada fark edilecek ilk şey, fiksingdeki fiyatın koşunun yarısına ne kadar yakın olduğudur.

{{# sema kosu-normal }}

Yarı yakın olduğu için geri verme hızlıdır, ama yakınlığın kendisi bir şey söylemez: yön bilgisi olmayan bir yolda da
fiyat yakın bir seviyeye sık dokunur ve gerçek payın aynadan farkı burada güçlü koşudakinden küçüktür. Reddedilen
koşunun uzun fitili "piyasa o seviyeyi reddetti" diye okunmaya elverişlidir; ölçülen davranış ise normal koşununkine
yakın.

Bu durumda yapmazsın: yarıya dokunuşu bir giriş sinyali saymazsın, yüksek kazanma oranlı bir tepkiyi kârlı sanmazsın,
reddedilen fitili normal koşudan güçlü bir okuma gibi işlemezsin.

{{# kart normal-kosu }}

{{# ornek tokyo-normal }}

İki günün yarım saati (①) birbirine benzer: koşu var ama düzenli değil, ve fiksingdeki fiyat koşunun yarısından (②)
çok uzakta değil. Üstteki günde fiyat fiksingden sonra yarıya dokunur (③) ve ④'e kadar ne ucuna geri gider ne öbür
ucunu kırar. Alttaki günde fiyat yarıya hiç dokunmaz, koşunun ucunu aşar ve geri gelmez. Fiksing anında masadaki tek
bilgi yarının yakınlığıdır ve o bilgi iki gün için de aynıdır; üstteki günün okuması ancak sonradan okuma gibi
görünür. İki gün kuralı ne doğrular ne yanlışlar: normal koşuda yarıya dönüş zaten sık olan bir harekettir, ölçünün
yakaladığı bu sıklığın şanstan yalnız biraz yüksek olmasıdır.

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

Londra'da bu okuma çoğu zaman yanlıştır. Tokyo'da ilerleme payı daha yüksek, ama kırılan uçtan giren tepki iki
fiksingin toplamında maliyetten sonra eksi kaldı. Dar aralık maliyeti de büyütür: stop öbür kenarın ötesinde ve
yakındır, aynı makas yakın bir stopun daha büyük bir parçasıdır.

Bu durumda yapmazsın: Londra'da sessiz bir fiksingden sonraki kırılımı kovalamazsın, Tokyo'nun yüksek payını "orada
kırılım işler" diye okumazsın.

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

İki dönemde aynı tutan tek okuma, ay sonunda güçlü koşunun fiksingden sonra öbür günlerden de seyrek sürmesidir. Geri
vermenin ay sonunda daha sık olduğu bir dönemde görüldü, öbüründe görülmedi; şemadaki ③ bu yüzden bir beklenti değil,
açık bir sorudur.

Bu durumda yapmazsın: fiksingden sonraki uzamayı ay sonu akışının devamı sayıp pozisyona eklemezsin, ay sonunda geri
vermeye daha çok güvenmezsin, Tokyo fiksinginin ay sonu farkını okumaya katmazsın.

{{# kart ay-sonu }}

## Trend

Fiksingde de trend bir şey değiştirmiyor: güçlü koşu trend yönündeyken {{ T.fiksing.guclu.trendle.devam }}, trende
karşıyken {{ T.fiksing.guclu.karsi.devam }} sürdü.

<details>
<summary>Trend ayrımı tablosu (2018–2023)</summary>

{{# trend fiksing }}

</details>

## Bu okumaları işleme çevirmek

"Fiksingden sonra koşu geri verilir" sözünün işlem hâli şudur: fiksing anında koşunun tersine gir, stopu koşunun
ucunun {{ ref_tampon }} koşu boyu ötesine koy, hedefi koşunun yarısına koy. Sessiz fiksingde tepki kırılan uçtan
girmektir. 2024 → dönemindeki sonuç:

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

Giriş piyasa emridir ve makas ile kaymayı fiksing anında öder. Stop koşunun ucunun {{ ref_tampon }} koşu boyu
ötesindedir; güçlü koşuda fiyat fiksingden sonra ucunu çoğu zaman bu kadar aşar. Hedef koşunun yarısıdır; fiyat oraya
sık gelir, ama stopu gördükten sonra geldiğinde işlem çoktan kapanmıştır. Normal koşuda tablo tersine döner: hedef
yakın, stop uzak, kazanma oranı yüksek, başa baş için gereken oran ondan da yüksek.

Bu durumda yapmazsın: maliyetsiz sonucun artı olmasını işlem sayısıyla büyüyecek bir kenar sanmazsın, çünkü maliyet her
işlemde yeniden ödenir; stopu ucun hemen ötesine sıkıştırıp riski küçültmezsin, çünkü aynı makas R cinsinden büyür.

{{# kart ters-giris }}

## Emri nereye koyarsın

Bu bölüm fiksingi bir işlem gerekçesi saymaz; başka bir gerekçeyle fiksing penceresinde emir verecek biri için dersin
ölçtüğü davranışın emrin yeri hakkında ne söylediğini yazar. Pencere Tokyo'da Tokyo 09:25–10:55 (TSİ 03:25–04:55),
Londra'da Londra 15:30–17:00'dir (TSİ 17:30–19:00, İngiltere kış saatinde 18:30–20:00).

- **Giriş.** Piyasa emri girişte makas ve kayma öder; limit girişte ödemez, çıkışta öder (8. ders, Limit neden ucuz
  görünür: ters seçim). Limit yalnız fiyat ona geldiğinde dolar: koşunun yarısına konan bir limit geri vermenin olduğu
  günlerde dolar, koşunun sürdüğü günlerde boşta kalır. 8. ders bunu büyük mumda ölçtü; fiksing için ölçülmedi, ama
  geometri aynıdır. Koşunun ucunun kırılmasına stop emriyle girmek, şanstan seyrek süren uzamayı kaymayla almaktır
  (3. ders, Sınıf sınıf, şansın payıyla; 8. ders, Ucun kırılması).
- **Stop.** Koşunun tersindeysen stop ucun ötesindedir, güçlü koşuda o mesafe kısadır ve fiksingden sonraki ilk uzama
  onu sık alır (3. ders, Bu okumaları işleme çevirmek). Koşunun yönündeysen stopun yarı ile uç arasındaysa geri verme
  onu sık görür; başın ötesindeyse fiksing davranışı ona şanstan sık gelmez (3. ders, Sınıf sınıf, şansın payıyla).
  Stopu yaklaştırmak aynı makası R cinsinden büyütür; normal koşunun tersine giren tepkide ortanca risk zaten
  {{ B.referans.fiksing.normal.dis.risk_pip }} pip (8. ders, Stop uzaklığı ve maliyet).
- **Hedef.** Geri vermeyi bekleyen hedef koşunun yarısıdır, başladığı yer değil. Koşunun yönündeki hedef fiksingden
  sonraki uzamaya, ay sonunda hiç dayanmaz (3. ders, Sınıf sınıf, şansın payıyla; 3. ders, Ay sonu).
- **İptal.** Ölçüm fiksingden sonraki {{ AN.wmr.pencere }} dakikayı okur; pencere dolunca fiksinge bağlı bir emrin
  dayanağı kalmaz. Pencerenin ikinci yarısının ayrı davranışı bu derste ölçülmedi.
- **Haber.** Serinin takvimindeki büyük haberlerin (ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararları)
  hiçbiri fiksing pencerelerine denk gelmez, yani ölçümün haber anlarına eklediği ek kayma burada yoktur (1. ders,
  Kazanma oranı ile net sonuç). Takvim dışı yerel veriler ve WM/R'nin beş dakikasında (Londra 16:00 çevresi, TSİ
  18:00, İngiltere kış saatinde 19:00) makasın davranışı bu derste ölçülmedi.

## Sık yapılan hatalar

- **Fiksingden sonra koşuyu kovalamak.** Sürme payı iki dönemde de aynanın altında, ay sonunda Londra'da daha da
  altında. Dayanak: 3. ders, Sınıf sınıf, şansın payıyla; 3. ders, Ay sonu.
- **Hedefi koşunun başladığı yere koymak.** Geri verme şanstan sık, tam dönüş değil. Dayanak: 3. ders, Sınıf sınıf,
  şansın payıyla.
- **Geri vermeyi işlem saymak.** Maliyetsiz sonuç küçük, makas ve kayma ondan büyük. Dayanak: 3. ders, Bu okumaları
  işleme çevirmek; 5. ders, Maliyet nereye gidiyor.
- **Yüksek kazanma oranını kâr sanmak.** Normal koşunun tersine giren tepki işlemlerin yarısından çoğunu kazandı, ama
  başa baş daha yüksek bir oran istiyordu. Dayanak: 1. ders, Kazanma oranı ile net sonuç.
- **Stopu koşunun ucuna yapıştırmak.** Güçlü koşuda fiyat fiksingden sonra ucunu biraz aşar; tersine giren işlemlerin
  çoğu bu yüzden stopta bitti. Dayanak: 3. ders, Bu okumaları işleme çevirmek; 8. ders, Stop uzaklığı ve maliyet.
- **Sessiz Londra fiksinginden sonraki kırılımı akış sanmak.** Dayanak: 3. ders, Sessiz fiksing.
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
   kış saatinde 19:00–20:00) dolunca fiksinge bağlı emirleri çektin mi?

## Grafik okuma alıştırmaları

**1.** Londra fiksingi, İngiltere yaz saati. TSİ 17:30 ile 18:00 arasında fiyat altı mumla aynı yöne gitti ve
fiksingdeki fiyat koşunun ucuna yakın (Şekil M2'deki gibi). TSİ 18:05'te biten mum koşunun ucunu aşarak kapanıyor. Ne
yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Kovalamazsın: koşunun sürme payı şansın altında ve bu ilk uzama tam da seyrek süren harekettir (3. ders, Sınıf sınıf,
şansın payıyla). Tersine de bu mumla girmezsin: ucu aşan mum, tersine girenin stopunun alındığı yerdir (3. ders, Bu
okumaları işleme çevirmek). Üç seviyeyi işaretleyip fiyatın yarıya gelip gelmediğine bakarsın; gelmezse kural
yanlışlanmış olmaz.

</details>

**2.** Tokyo fiksingi. TSİ 03:25 ile 03:55 arasındaki koşunun gövdesi dolu değil ve fiksingdeki fiyat yarıya çok yakın
(Şekil M4'teki gibi). Masadaki biri yarıya dönüşün neredeyse kesin olduğunu, tersine girip yarıyı hedeflemenin kolay
bir işlem olduğunu söylüyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Yarıya dönüş sık olur, ama yarı yakın olduğu için aynada da sık olur (3. ders, Normal ve reddedilen koşu). Hedef yakın,
stop uzak: işlemlerin çoğu kazanır, kazanan küçük kazanır ve başa baş için gereken oran ölçülen kazanma oranının
üstünde kalır (1. ders, Kazanma oranı ile net sonuç; 3. ders, Bu okumaları işleme çevirmek). Girmezsin, yalnız izlersin.

</details>

**3.** Ayın son Londra iş günü, İngiltere kış saati. TSİ 18:30 ile 19:00 arasında güçlü bir aşağı koşu var (Şekil M7).
Başka bir gerekçeyle aşağı yönlü bir pozisyon taşıyorsun ve hedefin koşunun ucunun epey altında. Ne yaparsın, ne
yapmazsın?

<details>
<summary>Çözüm</summary>

Hedefini fiksingden sonraki uzamaya bağlamazsın: ay sonunda koşunun sürmesi öbür günlerden de seyrek, iki dönemde de
(3. ders, Ay sonu). Geri vermenin daha sık olacağını da varsaymazsın. Stopun yarı ile uç arasındaysa geri verme onu sıradan
bir günde de sık görür; bunu fiksingden önce bilirsin (3. ders, Sınıf sınıf, şansın payıyla).

</details>

**4.** Tokyo fiksingi, TSİ 03:55. Başka bir gerekçeyle güçlü koşunun tersine girmek istiyorsun (Şekil M8). Piyasa emri mi,
koşunun ucuna limit mi; stop ve hedef nerede, emir ne zaman çekilir?

<details>
<summary>Çözüm</summary>

Piyasa emri makas ve kaymayı fiksing anında öder. Ucuna konan limit girişte ödemez ama yalnız fiyat koşunun yönünde
yeniden yürürse dolar; büyük mumda bu tür tersine limit maliyetten önce kapanışta piyasa emrinden kötü çıktı (8. ders,
Limit neden ucuz görünür: ters seçim; fiksing için ölçülmedi). Stop ucun ötesinde, hedef yarıdadır (3. ders, Bu
okumaları işleme çevirmek). Fiksingden bir saat sonra, Tokyo 10:55'te (TSİ 04:55), dolmamış emrin fiksing dayanağı
kalmaz.

</details>

## Fiksing için masa kartı

- **Fiksinge koşan fiyattan sonra bir geri çekilme beklenir.** Koşunun yarısına kadar geri gelmesi şanstan sıktır;
  güçlü koşuda ortanca süre çeyrek saat, normal koşuda birkaç dakika.
- **Geri verme beklenir, dönüş beklenmez.** Koşunun başladığı yer şanstan sık kırılmaz.
- **Fiksingden sonra koşunun yönünde yeni işlem açmak, sürmeyen bir hareketi kovalamaktır.** Koşunun sürme payı
  şansın altında; ay sonunda Londra'da daha da altında.
- **Sessiz bir Londra fiksinginden sonraki kırılım çoğu zaman bir yere gitmez.**
- **Fiksingdeki küçük kenar işlenebilir değil.** Geri vermenin büyüklüğü makas ve kaymayı karşılamıyor; plan burada
  da işlem önermiyor.
