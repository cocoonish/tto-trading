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

### Normal ve reddedilen koşu

Normal koşu {{ Y.ic.fiksing.normal.orta }}, reddedilen koşu {{ Y.ic.fiksing.reddedilen.orta }} yarısını geri verdi;
aynada {{ Y.ic.fiksing.normal.orta_ayna }} ve {{ Y.ic.fiksing.reddedilen.orta_ayna }}. Geri verme çoğu zaman hemen olur:
ortanca süre {{ A.ic.wmr.normal.orta_dk }} dakika. Fark burada da aynı yönde ama güçlü koşudakinden küçük.

### Sessiz fiksing

Fiksinge giden mum küçükse fiksing anında piyasada ciddi bir akış görünmez. Fiksingden sonra fiyatın kırılan tarafta
bir mum boyu daha ilerleme payı:

{{# kucuk fiksing }}

Londra fiksinginde sessiz bir fiksingden sonraki kırılım çoğu zaman bir yere gitmiyor: kırılan tarafta bir mum boyu
ilerleme {{ K.ic.wmr.ilerle }} (2024 → {{ K.dis.wmr.ilerle }}). Tokyo'da pay daha yüksek
({{ K.ic.tokyo_fiks.ilerle }}, 2024 → {{ K.dis.tokyo_fiks.ilerle }}). Londra fiksingi Avrupa masalarının günü kapattığı
saate, Tokyo fiksingi ise Asya gününün ortasına denk gelir; fark buradan geliyor olabilir, bu derste ölçülmedi.

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

## Fiksing için masa kartı

- **Fiksinge koşan fiyattan sonra bir geri çekilme beklenir.** Koşunun yarısına kadar geri gelmesi şanstan sıktır;
  güçlü koşuda ortanca süre çeyrek saat, normal koşuda birkaç dakika.
- **Geri verme beklenir, dönüş beklenmez.** Koşunun başladığı yer şanstan sık kırılmaz.
- **Fiksingden sonra koşunun yönünde yeni işlem açmak, sürmeyen bir hareketi kovalamaktır.** Koşunun sürme payı
  şansın altında; ay sonunda Londra'da daha da altında.
- **Sessiz bir Londra fiksinginden sonraki kırılım çoğu zaman bir yere gitmez.**
- **Fiksingdeki küçük kenar işlenebilir değil.** Geri vermenin büyüklüğü makas ve kaymayı karşılamıyor; plan burada
  da işlem önermiyor.
