---
title: 'FX Gün İçi Oyun Planı 3: Fiksingler'
description: "Tokyo fiksingi ve Londra'nın WM/R fiksingi: fiyat fiksinge kadar koşunca fiksingden sonra ne yapıyor? Koşu ne sıklıkla geri veriliyor, ne sıklıkla tersine dönüyor, ay sonu bunu değiştiriyor mu, ve fiksingde koşunun tersine girmek maliyetten sonra ne verdi."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'fiksing', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Fiksinge koşan fiyat fiksingden sonra koşunun yarısını sık geri verir, ama koşunun başladığı yere nadiren döner. Ay sonunda güçlü koşu daha da az devam eder. Geri vermeyi yakalamaya çalışan tepki ise maliyetten sonra kaybettiriyor. Ders fiksinglerin oyun planını verir."
seviye: 'orta'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Fiksing bir kurun resmî olarak "o anda" ölçüldüğü dakikadır. Bazı fon, şirket ve saklama işlemleri o kura bağlanır;
işlemi üstlenen banka riskini çoğu zaman fiksing çevresinde piyasada kapatır. Bu yüzden fiksinge doğru fiyat bazen bir
yöne **koşar**, ve fiksing geçtiğinde o koşuyu taşıyan akışın bittiği düşünülür. İşlemcilerin bildiği eski söz
şudur: "fiksingden sonra koşu geri verilir." Bu ders sözün sayısını verir.

{{# an_tablo fiksing }}

Bu derste **ilk mum**, fiksinge giden {{ AN.wmr.tf }} dakikalık mumdur: koşunun kendisi. Sınıflar aynı kuralla
kurulur (güçlü koşu, normal koşu, reddedilen koşu, sessiz geçen fiksing) ve plan fiksingden sonraki
{{ AN.wmr.pencere }} dakikayı okur.

## Plan tek cümlede

**Fiksinge koşan fiyat koşunun bir kısmını geri verir ama dönmez; geri vermeyi yakalamaya çalışmak maliyetten sonra
kaybettirir.** Fiksingin işi koşuyu bitirmektir, tersine çevirmek değil.

## Fiksingden sonra fiyat nereye gidiyor

Fiksingden sonraki ortalama fiyat, koşunun yönünde ve koşunun boyu cinsinden. Sıfır çizgisi fiksing anındaki fiyattır;
aşağı, koşunun geri verilmesi demektir.

{{# sekil 01_patika "Fiksingden sonra ortalama fiyat yolu, koşunun yönünde" }}

Çizgiler fiksingden hemen sonra hafifçe aşağı iner ve orada kalır: ortalamada koşunun küçük bir kısmı geri verilir.
Büyük bir dönüş ortalamada yok.

## Sınıf sınıf

{{# davranis fiksing }}

### Güçlü koşu

Fiyat fiksinge kadar bir yöne güçlü gitmiş. İki fiksingin toplamında güçlü koşu fiksingden sonraki bir saatte
{{ D.ic.fiksing.guclu.orta }} yarısını geri verdi (2024 → {{ D.dis.fiksing.guclu.orta }}). Ama koşunun başladığı yeri
kıran yani gerçekten tersine dönen yalnız {{ D.ic.fiksing.guclu.donus }} (2024 → {{ D.dis.fiksing.guclu.donus }}).
Koşunun devam ettiği günler bile dönüşten daha sık: {{ D.ic.fiksing.guclu.devam }} (2024 → {{ D.dis.fiksing.guclu.devam }}).

Sayıların söylediği: güçlü bir koşudan sonra fiksing çoğu zaman bir **duraklama** getirir. Fiyat geri çekilir, bir
süre yatay gider, ve büyük bir hareket ne yukarı ne aşağı gelir. Açılışlarla karşılaştırınca fark açık: açılışta güçlü
mum yarısından sonra da yol alır; fiksingde koşu yarısına gelince çoğu zaman orada durur. Yarısını geri veren güçlü
koşuların yalnız {{ D.ic.fiksing.guclu.uc_orta }} kadarı koşunun ucuna geri gitti.

### Normal ve reddedilen koşu

Normal koşu {{ D.ic.fiksing.normal.orta }}, reddedilen koşu {{ D.ic.fiksing.reddedilen.orta }} yarısını geri verdi.
Devam ile dönüş burada birbirine yakın: normal koşuda {{ D.ic.fiksing.normal.devam }} ve
{{ D.ic.fiksing.normal.donus }}; 2024 → döneminde {{ D.dis.fiksing.normal.devam }} ve {{ D.dis.fiksing.normal.donus }}.
Küçük bir koşu küçük bir akıştır; fiksingten sonra fiyat yeniden günün geri kalanının işine döner.

### Sessiz fiksing

Fiksinge giden mum küçükse fiksing anında piyasada ciddi bir akış yoktur. Fiksingden sonra fiyat kırıldığı tarafta
ne kadar gidiyor:

{{# kucuk fiksing }}

Londra fiksinginde sessiz bir fiksingten sonraki kırılım çoğu zaman bir yere gitmiyor: kırılan tarafta bir mum boyu
ilerleme {{ K.ic.wmr.ilerle }} (2024 → {{ K.dis.wmr.ilerle }}). Londra fiksingi Avrupa masalarının günü kapattığı saate
denk gelir; sessiz geçen bir fiksingten sonra fiyat çoğu zaman sessiz kalıyor. Tokyo'da pay daha yüksek
({{ K.ic.tokyo_fiks.ilerle }}, 2024 → {{ K.dis.tokyo_fiks.ilerle }}); Tokyo fiksinginden sonra Asya günü sürdüğü için
fark buradan geliyor olabilir, bu derste ölçülmedi.

## Ay sonu

Ayın son Londra iş günü, portföylerin ay boyunca kurdaki değişime göre yeniden dengelendiği gündür ve bu işlemlerin
bir kısmının WM/R kuruna bağlandığı piyasada yaygın bir öncüldür; öncülün kendisi bu derste ölçülmedi. Ölçülen,
ay sonu fiksinginden sonraki fiyattır:

{{# sekil 02_ay_sonu "Ay sonu ile öbür günler: güçlü koşudan sonra devam ve geri verme" }}

{{# ay_sonu }}

Ay sonunda Londra fiksingine güçlü koşan fiyat, fiksingden sonra öbür günlerden daha da az devam ediyor:
{{ F.wmr.ic.ay_sonu.guclu.devam }} (öbür günler {{ F.wmr.ic.diger.guclu.devam }}); 2024 → döneminde
{{ F.wmr.dis.ay_sonu.guclu.devam }} (öbür günler {{ F.wmr.dis.diger.guclu.devam }}). Ay sonu koşusu bir haber değil
bir **akıştır**: fiksing geçince arkasında devam ettirecek bir şey kalmıyor. Ay sonunda geri verme payı ise iki dönemde
farklı: 2018–2023'te {{ F.wmr.ic.ay_sonu.guclu.orta }}, 2024 → döneminde {{ F.wmr.dis.ay_sonu.guclu.orta }}. Ay sonu
olayı yılda on iki kez ve paritede bir kez geldiği için örneklem küçüktür (2024 → döneminde güçlü koşu
{{ F.wmr.dis.ay_sonu.guclu.n }} olay); "ay sonunda koşu durur" okuması iki dönemde de aynı, "ay sonunda koşu geri
verilir" okuması değil.

Tokyo fiksinginde ay sonu ayrımı tutarlı değil: 2024 → döneminde normal koşudan sonra tersine dönüş ay sonunda
{{ F.tokyo_fiks.dis.ay_sonu.normal.donus }} (öbür günler {{ F.tokyo_fiks.dis.diger.normal.donus }}) ama 2018–2023'te
{{ F.tokyo_fiks.ic.ay_sonu.normal.donus }} ve {{ F.tokyo_fiks.ic.diger.normal.donus }}. İki dönemde aynı yöne
bakmayan bir fark plana girmez.

## Trend

{{# trend fiksing }}

Fiksingte de trend bir şey değiştirmiyor: güçlü koşu trend yönündeyken {{ T.fiksing.guclu.trendle.devam }}, trende
karşıyken {{ T.fiksing.guclu.karsi.devam }} devam etti.

## Bu okumaları işleme çevirmek

"Fiksingden sonra koşu geri verilir" sözünün işlem hâli şudur: fiksing anında koşunun tersine gir, stopu koşunun
ucunun hemen ötesine koy, hedefi koşunun yarısına koy. Sessiz fiksingte tepki kırılan uçtan girmektir. Sonuç:

{{# bacaklar referans fiksing }}

Dördü de "çalışmıyor". Güçlü koşuda tepkinin kazanma oranı düşük ({{ B.referans.fiksing.guclu.dis.kazanma }}); hedef
koşunun yarısı olduğu için kazanan işlem riskinin yaklaşık bir katını kazanıyor (ortalama
{{ B.referans.fiksing.guclu.dis.kazanc }} R) ve başa baş için {{ B.referans.fiksing.guclu.dis.basabas }} yetiyor, ama o
oran tutmuyor: işlemlerin {{ B.referans.fiksing.guclu.dis.stop_pay }} kadarı stopta, yani koşu fiksingten sonra
kendi ucunu bir kez daha aşınca bitti. Normal ve reddedilen
koşuda kazanma oranı yarının üstünde ({{ B.referans.fiksing.normal.dis.kazanma }} ve
{{ B.referans.fiksing.reddedilen.dis.kazanma }}), ama başa baş için {{ B.referans.fiksing.normal.dis.basabas }} gerekiyor.

Maliyetin payı burada açılışlardan büyük: fiksingde koşunun tersine girmek bir piyasa emridir, makas ve kayma öder.
Güçlü koşu tepkisinin maliyetsiz sonucu {{ B.referans.fiksing.guclu.dis.brut }} R, maliyet
{{ B.referans.fiksing.guclu.dis.maliyet }} R, net {{ B.referans.fiksing.guclu.dis.R }} R. Yani geri vermenin kendisi
de maliyetten önce sıfıra yakın: fiyat yarıya gelir ama yarıya gelişi, stop yakın olduğu için, bir kazanca
dönüşmüyor. Sessiz fiksingte kırılımın maliyetsiz sonucu artı ({{ B.referans.fiksing.kucuk.dis.brut }} R) ama dar stop
yüzünden maliyet ondan büyük ({{ B.referans.fiksing.kucuk.dis.maliyet }} R).

2018–2023'te fiksinglerin hiçbir sınıfında denenen hiçbir tepki maliyetten sonra artıda kalmadı; plan bütün fiksing
hücrelerinde "izle, işlem açma" der.

## Fiksing için masa kartı

- **Fiksinge koşan fiyat bir akışı taşır; fiksing o akışın sonudur.** Fiksingden sonraki ilk dakikalarda koşunun
  yönünde yeni bir işlem açmak, akış bittikten sonra ona katılmaktır.
- **Geri verme beklenir, dönüş beklenmez.** Koşu yarısına kadar geri gelebilir; koşunun başladığı yer çoğu zaman
  kırılmaz.
- **Ay sonunda Londra fiksingi koşuyu daha da kesin bitirir.** Ay sonu koşusu fiksingten sonra nadiren sürer.
- **Sessiz bir Londra fiksingi sessiz bir akşam demektir.** Arkasından gelen kırılım çoğu zaman bir yere gitmez.
- **Fiksingte koşunun tersine girmek bir maliyet işidir.** Geri vermenin büyüklüğü makas ve kaymayı karşılamıyor.
