---
title: 'FX Gün İçi Oyun Planı 2: Açılışlar'
description: "Tokyo, Londra ve New York açılışlarının ilk {{ AN.londra_acilis.tf }} dakikası: güçlü, normal, reddedilen ve küçük ilk mumdan sonra fiyat ne yapıyor, bunun ne kadarı mumun kendi şeklinden geliyor, trend bunu değiştiriyor mu, ve bu davranışa dayanan tepkiler maliyetten sonra ne verdi."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Açılışın ilk mumu çoğu zaman yarısına geri döner ve güçlü mum çoğu zaman devam ediyor gibi görünür; ikisi de mumun kendi şeklinden geliyor, fiyat yön bilgisi taşımıyor. Ders açılışların oyun planını sınıf sınıf verir: ne beklenir, ne kadar sürer, neye işlem açılmaz."
seviye: 'giris'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Açılış bir seansın ilk sözüdür. Tokyo'da gece birikmiş emirler, Londra'da günün en büyük likiditesinin gelişi, New
York'ta hisse piyasasıyla birlikte ABD'nin masaya oturması. Üçünde de ilk {{ AN.londra_acilis.tf }} dakika günün ilk
aralığını çizer ve işlemcilerin çoğu o aralığa göre plan yapar. Bu ders o aralıktan sonra fiyatın genelde ne yaptığını
ve bunun ne kadarının bir şey söylediğini anlatır.

{{# an_tablo acilis }}

## Plan tek cümlede

**Açılışın ilk mumu bir aralık çizer, bir yön değil.** Yarısına dönmesi de, güçlü mumun devam etmesi de mumun kendi
şeklinin verdiği paydır; fiyatın yönü rastgele olsaydı da aynı sayılar çıkardı. Açılış bir işlem fırsatı değil, günün
ilk referanslarını işaretleme anıdır.

## Bu dersi masada nasıl kullanırsın

Bu ders masada bir işlem listesi değil, bir yasak listesidir. Açılıştan önce saati ve takvimi bilirsin; ilk mum
kapanınca sınıfına bakarsın; sınıf neyi bekleyeceğini ve neyi yapmayacağını söyler. Hiçbir adım "şimdi gir" demez,
çünkü sınanan tepkilerin hiçbiri maliyetten sonra artıda kalmadı (aşağıda, "Bu okumaları işleme çevirmek").

{{# karar acilis-akis }}

### Açılış saatleri TSİ'de

Türkiye yıl boyunca aynı saatte kalır, İngiltere ve ABD yaz saatine geçer:

- **Tokyo 09:00:** TSİ her gün 03:00 (Japonya yaz saati uygulamaz). İlk mum 03:15'te kapanır, pencere 06:15'te biter.
- **Londra 08:00:** TSİ İngiltere yaz saatinde 10:00, kış saatinde 11:00. İlk mum 10:15'te (kışın 11:15'te) kapanır,
  pencere 13:15'te (kışın 14:15'te) biter.
- **New York 09:30:** TSİ ABD yaz saatinde 16:30, kış saatinde 17:30. İlk mum 16:45'te (kışın 17:45'te) kapanır,
  pencere 18:45'te (kışın 19:45'te) biter.

ABD yaz saatine İngiltere'den iki üç hafta önce geçer, sonbaharda bir hafta sonra çıkar. O haftalarda Londra açılışı
TSİ 11:00'de, New York açılışı TSİ 16:30'dadır: saat her ülkenin kendi kuralıyla okunur.

### Açılıştan önce neye bakılır

- **Bu açılışın tipik ilk mumu.** Sınıf, ilk mumun boyunu o açılışın kendi geçmişiyle kıyaslar; Londra'nın sıradan
  mumu Tokyo'nunkinden büyüktür (1. ders, İlk mumun dört sınıfı).
- **Pencereye düşen an.** New York açılışı ABD verisinden (New York 08:30, TSİ ABD yaz saatinde 15:30, kış saatinde
  16:30) bir saat sonra gelir; veri günlerinin açılışı bu derste ayrı ölçülmedi, o gün önce veri anı okunur (4. ders,
  ABD verileri). Tokyo penceresinin ilk saatinde Tokyo fiksingi (TSİ 03:55), New York penceresinin son saatinde çoğu
  hafta Londra fiksingi (Londra 16:00, TSİ İngiltere yaz saatinde 18:00, kış saatinde 19:00) vardır (3. ders).
- **Günlük trend.** Not edilir, karar ölçütü olmaz (aşağıda, "Trend bir şey değiştiriyor mu").

## İlk mumdan sonra fiyat nereye gidiyor

İlk mum kapandıktan sonra ortalama fiyat, mumun yönünde ve mumun boyu cinsinden. Sıfır çizgisi ilk mumun kapanışıdır;
yukarı, mumun yönüne devam demektir.

{{# sekil 01_patika "Açılıştan sonra ortalama fiyat yolu, ilk mumun yönünde" }}

Çizgilerin hepsi sıfıra yakın dolaşıyor. Güçlü bir açılış mumundan sonra bile ortalama fiyat mumun yönünde yol
almıyor: devam ettiği günlerle döndüğü günler ortalamada birbirini götürüyor.

## Sınıf sınıf, şansın payıyla

Her sınıfta yarısına dönüş, devam ve dönüş payı; yanında yolun aynasında, yani yön rastgele olsaydı, aynı payın
değeri. Üç açılışın toplamı:

{{# ayna acilis }}

Gerçek pay ile aynadaki pay her satırda birkaç puan içinde. Açılışın ilk mumu, kendi şeklinin ötesinde, fiyatın
sonraki iki üç saati hakkında bir şey söylemiyor. Her açılış tek tek, iki dönemde:

{{# davranis acilis }}

{{# sekil 02_devam_donus "Devam ve dönüş: üç açılış, üç sınıf, gerçek ve ayna" }}

### Güçlü ilk mum

Fiyat açılışta bir yöne gitmiş ve o yönde kapanmış. Devam payı ({{ Y.ic.acilis.guclu.devam }}) dönüşten
({{ Y.ic.acilis.guclu.donus }}) yüksek, ve bu fark akla "yön var" dedirtir. Aynada da aynı fark çıkıyor
({{ Y.ic.acilis.guclu.devam_ayna }} ve {{ Y.ic.acilis.guclu.donus_ayna }}): güçlü mum ucuna yakın kapandığı için
kendi ucunun yarım mum boyu ötesi, öbür ucundan çok daha yakındır. 2024 → döneminde de aynı: gerçek
{{ Y.dis.acilis.guclu.devam }}, ayna {{ Y.dis.acilis.guclu.devam_ayna }}.

Güçlü mum yarısına dönmeyi genelde biraz zaman alarak yapar. Yarısına dönenlerde ortanca süre Londra'da
{{ A.ic.londra_acilis.guclu.orta_dk }}, Tokyo'da {{ A.ic.tokyo_acilis.guclu.orta_dk }}, New York'ta
{{ A.ic.ny_acilis.guclu.orta_dk }} dakika.

Oyun planı şöyle okur:

- Güçlü mumun yönü bir işlem gerekçesi değildir. Kovalamak da, yarısına gelince katılmak da maliyetten sonra
  kaybettirdi (aşağıda).
- Güçlü mumun iki ucu günün ilk referanslarıdır. Gün içinde fiyat bu uçlara geldiğinde ne yaptığı bu derste
  ölçülmedi.

### Masada: güçlü ilk mum

Güçlü mum ekranın en ikna edici görüntüsüdür ve iki tuzağı vardır: devam payı mumun geometrisinden gelir (ucuna yakın
kapanan mumun kendi ucu yakındır), ve yarıya dönüş normal mumdan yavaştır, yani ilk birkaç mumda dönmemesi bir şey
söylemez.

{{# sema guclu-kovalama }}

{{# kart guclu-mum }}

Bu durumda yapmazsın: kapanışın ardından piyasa emriyle kovalamazsın (2018–2023'te bu sınıfın en iyi tepkisiydi ve
yine eksi kaldı: işlem başına {{ I.acilis.guclu.R }} R); uzadı diye mumun tersine de girmezsin, dönüş payı aynadakiyle
aynı.

{{# ornek guclu-londra }}

İki günün ilk mumları birbirine çok benziyor: ① ikisinde de uzun, ucuna yakın kapanan bir açılış mumu. Üstteki günde
fiyat ② yarıya geri iniyor, ③ ilk dokunuşu gösteriyor ve ④ pencerenin sonunda fiyat kapanışın gerisinde. Alttaki günde
③ yok: fiyat yarıya hiç dönmeden mumun yönünde bir mum boyu daha yol alıyor. İlk mumun kapandığı dakikada iki ekran
arasında okunacak bir fark yoktu; ayrım ancak saatler sonra, ③ gelince ya da gelmeyince görünür. Tek bir gün kuralı ne
doğrular ne yanlışlar; kural, iki günü birlikte taşıyan binlerce olayın sayısıdır.

### Normal ve reddedilen ilk mum

Açılışların çoğu buraya düşer. Normal mum {{ Y.ic.acilis.normal.orta }} yarısına döndü ve bu çoğu zaman hemen olur:
ortanca süre Londra'da {{ A.ic.londra_acilis.normal.orta_dk }}, New York'ta {{ A.ic.ny_acilis.normal.orta_dk }}
dakika. Ama normal mum ortasına yakın kapanır, yani yarısına dönüş aynada da {{ Y.ic.acilis.normal.orta_ayna }}.
Devam ile dönüş eşit ({{ Y.ic.acilis.normal.devam }} ve {{ Y.ic.acilis.normal.donus }}).

Reddedilen mum işlemcilerin çoğunun güçlü bir işaret saydığı mumdur: "o seviyede satıcı var". Sayılar bu okumayı
desteklemiyor. Reddin yönünde devam {{ Y.ic.acilis.reddedilen.devam }}, dönüş {{ Y.ic.acilis.reddedilen.donus }};
aynada {{ Y.ic.acilis.reddedilen.devam_ayna }} ve {{ Y.ic.acilis.reddedilen.donus_ayna }}. Fitil bir şey söylüyorsa
bile, açılıştan sonraki saatlere taşımıyor.

### Masada: normal ve reddedilen ilk mum

Normal mumda en sık görülen şey en anlamlı şey sanılır: fiyat birkaç dakikada yarıya döner ve bu bir "geri test" gibi
görünür. Oysa kapanış zaten yarıya yakındır; dokunuş şeklin sonucudur ve ardından fiyat iki uca eşit sıklıkta gider.

{{# sema normal-yari }}

Reddedilen mumda tuzak bir hikâyedir: uzun fitil "orada satıcı var" diye okunur. Ölçülen ise reddin yönünde devam ile
fitilin ucunun kırılmasının hemen hemen eşit sıklıkta olduğudur. Fitilin ucu bir referanstır; fiyat gün içinde oraya
döndüğünde ne yaptığı bu derste ölçülmedi.

{{# sema reddedilen-iki-yol }}

{{# kart reddedilen-mum }}

Bu durumda yapmazsın: yarıya dokunuşu giriş sinyali saymazsın; fitili duvar sayıp işlemi reddin yönüne, stopu fitilin
hemen ötesine kurmazsın, çünkü fitilin ucu reddin yönündeki devam kadar sık kırılır.

{{# ornek reddedilen-ny }}

İki gün de ① aynı biçimde başlıyor: küçük gövdeli, bir yanında uzun fitil taşıyan bir ilk mum. Üstteki günde fiyat
reddin yönünde yarım mum boyu ilerliyor, alttaki günde önce fitilin ucu kırılıyor. ③ işareti, varsa, ② yarıya ilk
dokunuşu gösterir ve hangi yolun geleceğini söylemez; ④ iki günün ne kadar ayrıldığını gösterir. Karar anında ①
dışında bakılacak bir şey yoktu ve ① iki günde aynı şeyi söylüyordu. Bu derste iki son hemen hemen eşit sıklıktadır;
panellerin sırası bir eğilim değildir, ve tek bir örnek "satıcı vardı" okumasını ne doğrular ne yanlışlar.

### Küçük ilk mum

Açılış sessiz geçmiş: ilk mum tipik boyun altında. Akla gelen tepki, aralık kırıldığında kırılan tarafa gitmektir
("sıkışma patlar"). Kırılan tarafta fiyatın bir mum boyu daha ilerleme payı:

{{# kucuk acilis }}

Bu payın tek başına bir anlamı yok; anlamı tepkinin sonucundadır, o da aşağıda: kırılımın yönüne girmek maliyetten
önce sıfıra yakın, maliyetten sonra eksi.

### Masada: küçük ilk mum

Sessiz açılışta bir uç kırılınca "sıkışma patladı" diye atlamak doğaldır. Ama mum küçük olduğu için stop da küçüktür ve
aynı makas küçük bir riskin büyük bir parçasıdır: kırılım maliyetten önce sıfıra yakın, sonra eksi.

{{# sema kucuk-kirilim }}

{{# kart kucuk-mum }}

## Trend bir şey değiştiriyor mu

Günlük trend yönünde açılan güçlü bir mumun daha sık devam etmesi beklenir. 2018–2023'te üç açılışın toplamında
trend yönündeki güçlü mum {{ T.acilis.guclu.trendle.devam }}, trende karşı olanı {{ T.acilis.guclu.karsi.devam }},
trend yatayken {{ T.acilis.guclu.yatay.devam }} devam etti. Trend sayıyı değiştirmiyor. Bütün sınıflar:

<details>
<summary>Trend ayrımı tablosu (2018–2023)</summary>

{{# trend acilis }}

</details>

### Masada: trend

Günlerdir yükselen bir grafikte güçlü bir yukarı açılış "iki teyit" gibi durur. Ölçülen şudur: güçlü mumun devam payı
trend yönünde, trende karşı ve yatayken birkaç puan içinde aynı. Trend emrin yerini, stopu ya da hedefi değiştirecek
bir bilgi taşımadı; trend yönünde diye kovalamazsın, karşı diye tersine girmezsin.

{{# sema trend-iki-yol }}

{{# kart trend-guclu }}

## Bu okumaları işleme çevirmek

Her sınıf için akla ilk gelen tepki sınandı. Yön sınıflarında: mumun yarısına limit emirle mumun yönünde gir, stopu
öbür ucun {{ ref_tampon }} mum boyu ötesine koy, yarım R hedefle. Küçük mumda: kırılan uçtan gir, stopu öbür ucun
{{ ref_tampon }} mum boyu ötesine koy, yarım R hedefle. 2024 → dönemindeki sonuç:

{{# kisa referans acilis }}

Kazanma oranları yüksek, dördü de "çalışmıyor". İki şey birlikte kaybettiriyor:

- **Maliyetten önce kenar yok.** Aynı kurallar orta fiyatla, makas ve kayma olmadan sınandığında da sonuç sıfıra yakın
  ya da eksi: güçlü mumda {{ B.referans.acilis.guclu.dis.brut }} R, normal mumda {{ B.referans.acilis.normal.dis.brut }} R,
  küçük mumun kırılımında {{ B.referans.acilis.kucuk.dis.brut }} R. Limit emir yalnız fiyat geri geldiğinde dolar, ve
  geri gelen günlerden sonrası yazı turadır.
- **Maliyet sıfırı eksiye çeviriyor.** Açılış mumu küçüktür, stop da küçüktür (ortanca risk normal mumda
  {{ B.referans.acilis.normal.dis.risk_pip }}, küçük mumda {{ B.referans.acilis.kucuk.dis.risk_pip }} pip). Makas bu
  stopun görünür bir parçasıdır: normal mumda maliyetin payı {{ B.referans.acilis.normal.dis.maliyet }} R, küçük mumun
  kırılımında (kayma da ödenir) {{ B.referans.acilis.kucuk.dis.maliyet }} R.

2018–2023'te açılışın her sınıfında beş altı tepki daha denendi: kapanışta mumun yönünde girmek, daha uzak hedef,
daha geniş stop. Hiçbiri maliyetten sonra artıda kalmadı. En iyisi güçlü mumda kapanışta mumun yönünde girmekti
({{ I.acilis.guclu.ad }}): işlem başına {{ I.acilis.guclu.R }} R. Yarısına limitle girmekle arasında belirgin fark
yok, ve kovalamak 2024 sonrasında sınanmadı. Plan bu hücrelerde "izle, işlem açma" der; ayrıntı
[backtest dersinde](/arastirma/fx-oyun-backtest/).

## Emri nereye koyarsın

Bu bölüm işlem önermez. Başka bir gerekçeyle (günlük bir görüş, bir pozisyonun kapatılması) açılış penceresinde emir
verecek olan için, bu dersin ve 8. dersin giriş biçimi sonuçlarını ilk mumdan sonraki duruma uygular.

- **Piyasa emri** makası ve kaymayı öder; güçlü mumun kapanışında kovalamanın kendisidir.
- **Limit emir** yarıya konur, girişte makas ödemez, çıkışta öder; ama yalnız fiyat geri geldiğinde, yani piyasa
  girişinin kaybettiği günlerde dolar (8. ders, Limit neden ucuz görünür: ters seçim). Normal mumda hemen dolması iyi
  fiyat değil, şeklin sonucudur.
- **Stop emri** (küçük mumun kırılımı) kayma öder ve fiyatı yürüdüğü yerden alır (8. ders, Ucun kırılması); maliyetin
  payı normal mumda {{ B.referans.acilis.normal.dis.maliyet }} R, küçük mumun kırılımında
  {{ B.referans.acilis.kucuk.dis.maliyet }} R'ydi.
- **Onay mumu** daha kötü fiyattan girer; onayın bilgisi kaçan fiyatı ancak karşılar (8. ders, Onay mumu). Açılışta
  ayrıca ölçülmedi.

**Stop** öbür ucun {{ ref_tampon }} mum boyu ötesindeydi: birkaç pip, makas onun görünür bir parçası. Daha yakını
maliyeti R cinsinden büyütür (8. ders, Stop uzaklığı ve maliyet), daha genişi 2018–2023'te artıda kalmadı. **Hedef**
yarım R kazanma oranını yükseltir, net sonucu değil (1. ders, Kazanma oranı ile net sonuç). **İptal:** emir ilk mumun
kapanışından bir saat sonra düşer (TSİ Tokyo 04:15, Londra 11:15 · kışın 12:15, New York 17:45 · kışın 18:45), pozisyon
pencerenin sonunda kapanır; pencereden sonrası için ölçülmüş dayanak yok. **Haber penceresi:** açılış pencerelerine
serinin ölçtüğü veri ve karar anları düşmez, sınanan tepkiler haber kayması ödemedi; fiksing ya da veri penceredeyse
emri öncesinde çekmek bir tercihtir, bu derste ölçülmedi.

## Sık yapılan hatalar

- **Güçlü mumu kapanışta kovalamak:** devam görüntüsü şekilden gelir ve tepki maliyetten sonra eksi kaldı (2. ders,
  Güçlü ilk mum).
- **Yarıya dokunuşu dönüş sanmak:** normal mumda dokunuş aynada da aynı sıklıktadır (2. ders, Normal ve reddedilen ilk
  mum).
- **Fitili satıcı kanıtı saymak:** reddin yönünde devam ile fitilin kırılması hemen hemen eşit (aynı bölüm).
- **Sessiz açılışın kırılımına atlamak:** maliyet küçük stopun büyük parçasıdır (2. ders, Küçük ilk mum; 8. ders, Ucun
  kırılması).
- **Trendi teyit saymak:** trend devam payını değiştirmiyor (2. ders, Trend bir şey değiştiriyor mu).
- **Yüksek kazanma oranını kenar sanmak:** oran yarının üstünde, başa baş için gerekenin altında (2. ders, Bu okumaları
  işleme çevirmek).
- **Açılışı yanlış ülkenin saatiyle beklemek:** İngiltere ve ABD yaz saatine farklı haftalarda geçer (bu dersin saat
  listesi).

## Masa kontrol listesi

1. Hangi açılış, TSİ kaçta? Tokyo 03:00; Londra 10:00 (İngiltere kış saatinde 11:00); New York 16:30 (ABD kış saatinde
   17:30). Bu hafta bir ülke saat değiştirdi mi?
2. New York açılışıysa TSİ 15:30'da (ABD kış saatinde 16:30) ABD verisi var mı?
3. Pencerede fiksing var mı: Tokyo'da TSİ 03:55, New York'ta TSİ 18:00 (İngiltere kış saatinde 19:00)?
4. Bugünkü ilk mum bu açılışın tipik boyundan belirgin uzun mu, kısa mı?
5. İlk mum kapandı mı (TSİ Tokyo 03:15; Londra 10:15, kışın 11:15; New York 16:45, kışın 17:45)?
6. Sınıfı ne; iki ucu ve yarıyı işaretledim mi?
7. Kovalamak, fitile göre girmek ya da kırılıma atlamak aklımdan geçiyor mu? Hangi ölçüm buna izin veriyor?
8. Pencere bitti mi (TSİ Tokyo 06:15; Londra 13:15, kışın 14:15; New York 18:45, kışın 19:45)? Bittiyse masadan
   kalkarım.

## Grafik okuma alıştırmaları

**1.** Londra açılışı, İngiltere yaz saati. TSİ 10:15'te güçlü bir ilk mum ucunda kapandı ve sonraki mum aynı yönde
açılıyor; ekranda herkes "kırıldı" diyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Uçları ve yarıyı işaretlersin, kovalamazsın: devam görüntüsü şekilden gelir ve kapanışta mumun yönünde girmek bu
sınıfın en iyi tepkisiyken bile maliyetten sonra eksi kaldı (2. ders, Güçlü ilk mum).

</details>

**2.** New York açılışında üstte uzun fitilli, küçük gövdeli bir ilk mum; günlük trend aşağı. "Fitil de trend de aşağı
diyor" denir. Ne yaparsın?

<details>
<summary>Çözüm</summary>

Fitilin ucunu, alt ucu ve yarıyı işaretlersin, işlem gerekçesi kurmazsın: reddin yönünde devam ile fitilin kırılması
hemen hemen eşit, trend de devam payını değiştirmiyor (2. ders, Normal ve reddedilen ilk mum; Trend bir şey değiştiriyor
mu).

</details>

**3.** ABD'nin yaz saatine geçtiği pazardan sonraki hafta; İngiltere henüz geçmedi. Londra ve New York açılışları TSİ
kaçta, Londra fiksingi New York penceresinin içinde mi?

<details>
<summary>Çözüm</summary>

Londra TSİ 11:00 (İngiltere kış saati), New York TSİ 16:30 (ABD yaz saati); New York penceresi 18:45'te biter, Londra
fiksingi o hafta TSİ 19:00'dadır ve pencerenin dışında kalır (bu dersin saat listesi).

</details>

## Açılış için masa kartı

- **İlk {{ AN.londra_acilis.tf }} dakika bir aralık çizer.** Üst ve alt ucu günün ilk referanslarıdır.
- **Normal mumda yarısına dönüş birkaç dakika içinde beklenir.** Bu, mumun şeklinin sonucudur; ne alış ne satış
  sebebidir.
- **Güçlü mumun "devam ediyor" görüntüsü yanıltıcıdır.** Yön rastgele olsaydı da aynı oranda devam ederdi.
- **Fitile ve trende anlam yükleme.** İkisi de sayılarda görünmüyor.
- **Sessiz açılışın kırılımı bir sinyal değildir.** Kırılımın yönüne girmek maliyetten önce de kazandırmadı.
- **Açılışta masada kalmanın sebebi işlem değil, referanstır.** Plan bu anda işlem önermiyor.
