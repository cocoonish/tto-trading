---
title: 'FX Gün İçi Oyun Planı 5: Backtest — Plan 2024 Sonrasında Ne Verdi'
description: "Oyun planının bütün tepkileri, 2018–2023 (planın yazıldığı dönem) ve 2024 → (planın hiç sınanmadığı dönem) arasında, gerçek alış-satış fiyatları ve maliyetle: kazanma oranı, işlem başına net sonuç, maliyetin payı, güven aralığı ve hüküm; sonunda günün haritası."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Planın tepkilerinin hiçbiri 2024 sonrasında 'çalışıyor' hükmü almadı. Sık gelen anlarda yüksek kazanma oranlı tepkiler maliyetten sonra kaybettirdi; açılışta kenar maliyetten önce de yok, fiksingte küçük bir kenar var ve maliyet onu yiyor. Tek artı adaylar merkez bankası kararlarında, birkaç karar gününe dayanıyor."
seviye: 'orta'
onkosul: ['fx-oyun-okuma', 'fx-oyun-acilislar', 'fx-oyun-fiksingler', 'fx-oyun-haberler']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Önceki dört ders bir oyun planı yazdı: hangi anda, hangi ilk mumdan sonra fiyatın genelde ne yaptığı ve bunun ne
kadarının şansın ötesinde olduğu. Bu ders o planın **işleme çevrilmiş** hâlinin sonucunu verir. Planın tepkileri
2018–2023 verisinden yazıldı ve 2024 sonrası veride hiç koşturulmadan kaydedildi; burada iki dönemin sonucu yan yana
durur. Hüküm yalnız 2024 → döneminden verilir ({{ ON.dis_bitis }} tarihine kadar).

## Kısaca

- **Davranış iki dönemde aynı kaldı.** Açılışta ilk mumun yön bilgisi taşımaması, fiksingte koşunun şanstan sık geri
  verilmesi iki dönemde de görüldü.
- **Davranıştan para çıkmadı.** {{ ref_sayi }} referans tepkinin ve {{ islem_sayi }} işlem tepkisinin hiçbiri
  "çalışıyor" hükmü almadı. İşlem tepkilerinde {{ islem_zayif }} zayıf, {{ islem_calismiyor }} çalışmıyor,
  {{ islem_olculemedi }} ölçülemedi.
- **Kazanma oranı yüksek kurulabildi.** Açılışta yarım R hedefli tepkiler işlemlerin
  {{ B.referans.acilis.normal.dis.kazanma }}–{{ B.referans.acilis.guclu.dis.kazanma }} kadarını kazandı; başa baş için
  {{ B.referans.acilis.guclu.dis.basabas }} gerekiyordu.
- **Tek artı adaylar merkez bankası kararlarında.** Güçlü karar mumunun yönünde kalmak 2024 → döneminde
  {{ B.islem.mb.guclu.dis.n }} işlemde ({{ B.islem.mb.guclu.dis.gun_n }} karar günü) {{ B.islem.mb.guclu.dis.R }} R verdi.
  {{ ON.hukum_en_az }} işlemin altında hüküm kurulmaz.

## Bu dersi masada nasıl kullanırsın

Bu ders planın sınav kâğıdıdır ve masada da öyle kullanılır. Önceki dört ders ilk mumdan sonra fiyatın genelde ne
yaptığını söyledi; bu ders o okumaların hiçbirinin maliyetten sonra bir işlem olmadığını söylüyor. Masadaki karşılığı:
okumalar ekranda kalır, emir defteri boş kalır. Aralığı, yarıyı, koşunun bittiği yeri işaretlersin; bunları bir
işlemin sebebi saymazsın. Başka bir gerekçeyle masadaysan ders üç şey söyler: emrin o anda hangi maliyeti ödeyeceği,
hangi kurulumun yalnız kazanma oranı yüksek olduğu için kâr gibi göründüğü, ve bir kuralı ne zaman kural
sayabileceğin. Merdiven, bir kuralı masaya getirmeden önce sorulacak beş soruyu sırayla verir.

{{# karar sinav }}

İlk iki soru sonuca bakmadan cevaplanır, son üçü sayıya bakar; sonuçtan sonra yazılmış bir kural ilk soruda düşer.
Bu dersin tepkileri ilk iki sorudan geçer: plan 2024 sonrası sınanmadan kaydedildi. Açılış ve fiksing tepkileri
dördüncü soruda durur. Merkez bankası satırlarından işlemi az olanlar üçüncü soruda durur; eşiği geçenler merdivenin
sonuna "zayıf" hükmüyle, aday olarak varır.

## Tepki nedir, nasıl seçildi

Plan her an ailesinde (açılış, fiksing, ABD verisi, merkez bankası) ve her ilk mum sınıfında bir **tepki** yazar. İki
tür vardır.

- **Referans tepki** planın kendi okumasının en düz işlem hâlidir. Yön sınıflarında ilk mumun yarısına limitle mumun
  yönünde girmek ve yarım R hedeflemek; küçük mumda kırılan uçtan girmek; fiksingde koşunun tersine girip koşunun
  yarısını hedeflemek. 2024 sonrası sonucuna bakılmadan yazıldı; 2018–2023 sonucu yazılırken biliniyordu. Amacı
  "okuma doğruysa kazanma oranı yüksek olur" sözünü sınamaktır.
- **İşlem tepkisi**, her hücrede 2018–2023'te denenen {{ aday_alt }} ila {{ aday_ust }} adayın içinden, önceden yazılmış
  kuralla seçildi: en az {{ ON.secim_en_az }} işlemi olan ve maliyetten sonra artıda kalanların en iyisi. Bu kural
  gereği seçilen her tepkinin 2018–2023 sonucu artıdır; kanıt 2024 → sonucudur. Böyle bir aday çıkmayan hücrede plan
  "izle, işlem açma" der. {{ izle_sayi }} hücre bu durumdaydı; {{ islem_sayi }} hücrede işlem tepkisi seçildi.

Trend seçime girmedi: gözlemde trend ilk mumdan sonraki davranışı belirgin değiştirmiyordu.

## Kazanma oranı ve net sonuç

Her tepkinin 2024 → dönemindeki kazanma oranı ve işlem başına net sonucu (dairenin büyüklüğü işlem sayısı):

{{# sekil 01_kazanma_net "Açılış ve fiksing tepkileri: kazanma oranı yüksek ya da düşük, hepsi eksi" }}

Şekilde iki küme var. Büyük daireler açılış ve fiksing tepkileri: yüzlerce, kimi binlerce işlem, ve hepsi sıfırın
altında. Açılışta kazanma oranları yarının üstünde ama yarım R'lik kazanç kaybı karşılamıyor. Fiksingde güçlü koşunun
tersine giren tepki işlemlerin yalnız {{ B.referans.fiksing.guclu.dis.kazanma }} kadarını kazandı; kazananı ortalama
{{ B.referans.fiksing.guclu.dis.kazanc }} R getirdi, başa baş için {{ B.referans.fiksing.guclu.dis.basabas }} yetiyordu,
o oran da tutmadı. Sağ üstteki küçük noktalar merkez bankası kararları: hem kazanma oranı hem net sonuç yüksek, ama her
biri en çok {{ mb_n_ust }} işlem. O kümede iki ölçünün birlikte yükselmesi birkaç iyi kararın ikisini birden yukarı
itmesi olabilir; ayrılmadı.

Aritmetik açılışta en açık hâlindedir. Güçlü ilk mumun yarısına limitle girip yarım R hedefleyen tepkide kazanan işlem
ortalama {{ B.referans.acilis.guclu.dis.kazanc }} R kazandı, kaybeden ortalama {{ B.referans.acilis.guclu.dis.kayip }} R
kaybetti. Bu ikisiyle başa baş için işlemlerin {{ B.referans.acilis.guclu.dis.basabas }} kadarını kazanmak gerekir; tepki
{{ B.referans.acilis.guclu.dis.kazanma }} kazandı. Kazanma oranı istenen yere çekilebilir (hedef yaklaştıkça yükselir),
ama başa baş oranı da onunla birlikte yükselir.

### Masada: kazanma oranının yanına başa baş oranı

Bu bulgunun ekrandaki görüntüsü sıradan bir açılıştır: güçlü ilk mum ucuna yakın kapanır, fiyat yarıya döner, limit
dolar ve çoğu gün kısa süre sonra yarım R'lik hedef gelir. Gün gün izleyen için bu bir başarı serisidir. Şema aynı
dolumdan çıkan iki yolu yan yana koyar.

{{# sema yarim-r }}

Kazanma oranı her zaman başa baş oranıyla birlikte okunur: ortalama kayıp, ortalama kazanç ile ortalama kaybın
toplamına bölünür. Yarım R kazanıp bir R kaybeden kurulum maliyetsiz bile üç işlemden ikisini kazanmak zorundadır;
maliyet kazancı küçültür, kaybı büyütür. Güçlü açılış mumunda kazanma oranı
{{ B.referans.acilis.guclu.dis.kazanma }}, gereken {{ B.referans.acilis.guclu.dis.basabas }} (5. ders, Kazanma oranı
ve net sonuç).

{{# kart yuksek-kazanma }}

Bu durumda yapmazsın: hedefi yaklaştırıp kazanma oranını yükseltmeyi iyileştirme saymazsın, başa baş oranı da onunla
yükselir; birkaç günlük kazanç serisini kenarın kanıtı saymazsın.

{{# ornek acilis-yari }}

İki gün ③ işaretine kadar birbirinin aynısıdır: ① Londra açılışının ucuna yakın kapanan ilk mumu, ② mumun yarısı,
③ fiyatın yarıya dokunduğu ve limitin dolduğu an. Ayrım dolumdan sonra başlar. Üstteki günde fiyat yarıdan mumun kendi
ucuna yürür ve yarım R'lik hedef yolda kalır; alttaki günde yarıdan devam eder, mumun öbür ucunu kırar ve ④ işaretinde
(izleme penceresinin sonu) mumun yönünün tersindedir. Dolum anında iki günü ayıran bir işaret ekranda yoktur, çünkü
açılış mumu yön bilgisi taşımıyor (1. ders, Şans ne verirdi: yolun aynası); karar ancak sonradan "belli" görünür.
Tek bir gün kuralı ne doğrular ne yanlışlar; aritmetiğin neden binlerce işlemle okunduğunu gösterir.

## Referans tepkiler

{{# bacaklar referans }}

Açılış ve fiksingin {{ sik_sayi }} referans tepkisinin hepsi "çalışmıyor" ve hepsinin güven aralığı sıfırın altında.
Haber anlarında işlem sayıları küçük; merkez bankası kararlarında normal ve küçük mumun referans tepkisi 2024 →
döneminde artıda, ikisinin de aralığı sıfırı kapsıyor ("zayıf").

## Maliyet nereye gidiyor

Her tepkinin maliyetsiz (aynı kurallar orta fiyatla, makas ve kayma olmadan) ve maliyetli sonucu:

{{# sekil 02_maliyet "Maliyetten önce ve sonra: açılışta kenar yok, fiksingte küçük kenar maliyete gidiyor" }}

Üç ayrı hikâye var.

- **Açılışta kenar maliyetten önce de yok.** Yarısına limitle girilen tepkilerin maliyetsiz sonucu sıfıra yakın ya da
  eksi (güçlü mumda {{ B.referans.acilis.guclu.dis.brut }} R, normal mumda {{ B.referans.acilis.normal.dis.brut }} R);
  küçük mumun kırılımı da öyle ({{ B.referans.acilis.kucuk.dis.brut }} R). Maliyet, sıfırı belirgin bir eksiye
  çeviriyor: küçük mum küçük stop demektir ve makas o stopun görünür bir parçasıdır.
- **Fiksingde küçük bir kenar var, maliyet onu yiyor.** Koşunun tersine girmenin maliyetsiz sonucu 2018–2023'te normal
  koşuda {{ B.referans.fiksing.normal.ic.brut }} R, 2024 → döneminde {{ B.referans.fiksing.normal.dis.brut }} R. Bu,
  fiksing dersinde şansla kıyaslanan geri vermenin işlem hâlidir. Maliyet
  ({{ B.referans.fiksing.normal.dis.maliyet }} R) ondan büyük.
- **Merkez bankasında maliyetsiz sonuç artı.** Küçük karar mumunun kırılımında maliyetsiz
  {{ B.referans.mb.kucuk.dis.brut }} R, maliyetli {{ B.referans.mb.kucuk.dis.R }} R; az işlemle.

### Masada: maliyeti ekranda görmek

Maliyet grafikte bir mum olarak görünmez; dolum fiyatı ile orta fiyat arasındaki farkta durur. Onu görmek için emir
anındaki makası ve planlanan riski (girişten stopa) pip olarak okur, birini ötekine bölersin: bölüm işlemin R
cinsinden maliyetidir. Piyasa ve stop emirleri bunun üstüne kayma öder; açıklamadan iki dakika önce ile on beş dakika
sonrası arasında kayma daha büyüktür (1. ders, Kazanma oranı ile net sonuç).

{{# sema makas-stop }}

Masada bunu görmenin yolu her işlemin yanına ikinci bir sonuç yazmaktır: aynı işlem, alış ile satışın ortasından, makas
ve kayma olmadan. İki sonucun farkı ödediğin maliyettir. Maliyetsiz sonuç sıfırın çevresinde dolaşıyorsa kenar yoktur
ve emri ucuzlatmak onu yaratmaz (8. ders, Bu sonuç nasıl okunmalı).

{{# kart kucuk-stop }}

Bu durumda yapmazsın: maliyeti "birkaç pip" diye riskten ayrı okumazsın; stopu maliyet küçülsün diye uzaklaştırıp
bunu kenar saymazsın, uzak stop payı küçültür ama yön bilgisini değiştirmez (8. ders, Stop uzaklığı ve maliyet).

## İşlem tepkileri

{{# bacaklar islem }}

İşlem tepkilerinin 2024 → dönemindeki birikimli sonucu, işlem işlem:

{{# sekil 03_egri "İşlem tepkilerinin 2024 sonrasında birikimli sonucu" }}

- Merkez bankasında **güçlü karar mumunun yönünde** kalmak {{ B.islem.mb.guclu.dis.n }} işlemin
  {{ B.islem.mb.guclu.dis.kazanma }} kadarını kazandı (net {{ B.islem.mb.guclu.dis.R }} R). İşlemler yalnız
  {{ B.islem.mb.guclu.dis.gun_n }} karar gününe düşüyor; aynı kararda dört paritenin işlemi birlikte hareket eder. İşlem
  düzeyindeki aralık ({{ B.islem.mb.guclu.dis.alt }} … {{ B.islem.mb.guclu.dis.ust }}) bu yüzden olduğundan dardır;
  karar günlerinden yeniden örneklenen aralık {{ B.islem.mb.guclu.dis.gun_alt }} … {{ B.islem.mb.guclu.dis.gun_ust }}.
  Yılda birkaç olay gelen bir kural için bu bir başlangıçtır, sonuç değil.
- Merkez bankasında **reddedilen karar mumu** {{ B.islem.mb.reddedilen.dis.n }} işlemde
  ({{ B.islem.mb.reddedilen.dis.gun_n }} karar günü) {{ B.islem.mb.reddedilen.dis.R }} R, **normal karar mumu**
  {{ B.islem.mb.normal.dis.n }} işlemde {{ B.islem.mb.normal.dis.R }} R ("{{ B.islem.mb.normal.hukum }}").
- ABD verisinde **güçlü veri mumu** 2024 → döneminde {{ B.islem.veri.guclu.dis.R }} R, **küçük veri mumu**
  {{ B.islem.veri.kucuk.dis.R }} R ("{{ B.islem.veri.kucuk.hukum }}").

### Masada: birkaç karar gününe dayanan bir aday

Merkez bankası satırları dersin en dikkat çekici ve masada en kolay yanlış okunan satırlarıdır. Ekranda büyük bir
karar mumu görürsün: ilk beş dakika ucuna yakın kapanır ve dört paritede birden aynı yöne bakar.

{{# sema karar-mumu }}

Bu satırı kural değil aday olarak tutarsın: işlemler {{ B.islem.mb.guclu.dis.gun_n }} karar gününe düşüyor ve hüküm
kuralı {{ ON.hukum_en_az }} işlemin altında hüküm kurmaz. Aynı kararın dört paritedeki işlemi tek bir olayın dört
kopyasıdır; sayacı karar günü olarak tutarsın (5. ders, İşlem tepkileri).

{{# kart karar-aday }}

Bu durumda yapmazsın: bir sonraki kararı beklerken adayın stopunu, hedefini ya da giriş anını değiştirmezsin; ilk
mumu basın toplantısının da söylediği şey saymazsın, çünkü toplantının ayrı etkisi ölçülmedi (4. ders, Merkez bankası
kararları).

## İzle, işlem açma

Bu hücrelerde 2018–2023'te denenen hiçbir aday maliyetten sonra artıda kalmadı. Tabloda denenen aday sayısı ve en
iyisinin sonucu:

{{# izle }}

Açılış ve fiksinglerin bütün hücreleri burada. Plan bu anlarda okumayı sürdürür ama işlem önermez.

### Masada: "izle" satırında masada ne kalır

"İzle, işlem açma" bir boşluk değildir; masadaki işi değiştirir. İşlemin yerine referansları işaretlemek, olanı
deftere yazmak ve başka bir gerekçeyle açılmış bir pozisyonun o andan nasıl etkileneceğini bilmek kalır. Fiksing en
açık örnektir: davranış gerçek, işlem değil.

{{# sema fiksing-geri }}

{{# kart fiksing-izle }}

Bu durumda yapmazsın: geri vermeyi maliyetini bilmeden işlemezsin, küçük kenar makas ve kaymadan küçüktür (5. ders,
Maliyet nereye gidiyor); "izle" satırının bir gün işleme döneceğini umup kuralı her gün yeniden ayarlamazsın.

{{# ornek wmr-kosu }}

İki günde de ① Londra fiksingine giden otuz dakikalık koşudur ve fiksinge kadar ekranda birbirine benzer; ② koşunun
yarısıdır. Üstteki günde fiyat fiksingden sonra koşuyu geri verir, ③ işaretinde yarıya dokunur ve ④ işaretinde
(izleme penceresinin sonu) fiksingdeki seviyenin gerisindedir. Alttaki günde fiksing koşunun sonu değildir: kısa bir
duraklamadan sonra fiyat koşunun yönünde yürür, yarıya gelmez, ③ hiç oluşmaz ve ④ işaretinde fiksingdeki seviyenin
ötesindedir. Emrin konabileceği tek anda, fiksingde, iki gün ayırt edilemez. Geri verme şanstan sık geldiği için
üstteki gün daha sık görülür (3. ders, Sınıf sınıf, şansın payıyla), ama sıklık farkı maliyeti karşılamaz. İki gün
kuralı ne doğrular ne yanlışlar; fiksingin bir sinyal değil bir an olduğunu gösterir.

## Günün haritası

Planın bütün okumaları tek tabloda, günün sırasıyla. Saatler TSİ; parantez içi İngiltere, Avrupa ya da ABD kış
saatinde.

| TSİ | An | Ne beklenir | Ne yapılmaz |
|---|---|---|---|
| {{ AN.tokyo_acilis.tsi_yaz }} | Tokyo açılışı | İlk {{ AN.tokyo_acilis.tf }} dakika bir aralık çizer; yön bilgisi yok | Güçlü mumu kovalamak, yarısında katılmak |
| {{ AN.tokyo_fiks.tsi_yaz }} | Tokyo fiksingi | Fiksinge koşu varsa bir geri çekilme | Fiksingden sonra koşunun yönünde girmek |
| {{ AN.londra_acilis.tsi_yaz }} ({{ AN.londra_acilis.tsi_kis }}) | Londra açılışı | Normal mumda birkaç dakika içinde yarısına dönüş | Yarıya dönüşü bir giriş sinyali saymak |
| {{ AN.boe.tsi_yaz }} ({{ AN.boe.tsi_kis }}) | BoE kararı | Tutanak kararla birlikte gelir; olay az | İlk mumdan hüküm kurmak |
| {{ AN.ecb.tsi_yaz }} ({{ AN.ecb.tsi_kis }}) | ECB kararı | Basın toplantısı yarım saat sonra | İlk mumu son söz saymak |
| {{ AN.nfp.tsi_yaz }} ({{ AN.nfp.tsi_kis }}) | ABD verisi | İlk mumun itişi şanstan seyrek sürer | Veri mumunun yönünde kalmak |
| {{ AN.ny_acilis.tsi_yaz }} ({{ AN.ny_acilis.tsi_kis }}) | New York açılışı | Açılışlardaki gibi: aralık, yön değil | Sessiz açılışın kırılımına girmek |
| {{ AN.wmr.tsi_yaz }} ({{ AN.wmr.tsi_kis }}) | Londra fiksingi | Koşunun bir kısmı geri verilir; ay sonunda koşu daha da az sürer | Fiksingden sonra koşuyu kovalamak; geri vermeyi maliyetle işlemek |
| {{ AN.fomc.tsi_yaz }} ({{ AN.fomc.tsi_kis }}) | FOMC kararı | Güçlü ya da reddedilen mumun yönü 2024 sonrasında sürdü; birkaç karar günü | Sınanmamış bir adayı kural saymak |

### Masada: Tokyo'dan New York kapanışına bir işlem günü

Tablo günün okumalarını verir; masada aynı gün saat saat yaşanır. Planın hiçbir anı işlem önermediği için gün
işaretlemek, beklemek ve yazmaktan oluşur; masadan kalkmak günün meşru bir parçasıdır (5. ders, İzle, işlem açma).
Şemada sütunların genişliği süreyi değil sırayı gösterir.

{{# sema gun }}

- **TSİ {{ AN.tokyo_acilis.tsi_yaz }} — Tokyo açılışı (Tokyo 09:00).** Soru: ilk {{ AN.tokyo_acilis.tf }} dakikanın
  aralığı nerede? Uçları işaretlersin, güçlü mumu kovalamazsın (2. ders, Güçlü ilk mum).
- **TSİ {{ AN.tokyo_fiks.tsi_yaz }} — Tokyo fiksingi (Tokyo 09:55).** Soru: fiksinge koşu var mı? Varsa ucunu ve
  yarısını işaretlersin; fiksingden sonraki bir saat dolunca masadan kalkarsın (1. ders, İncelenen on an).
- **TSİ {{ AN.londra_acilis.tsi_yaz }} (İngiltere kış saatinde {{ AN.londra_acilis.tsi_kis }}) — Londra açılışı
  (Londra 08:00).** Soru: ilk mum hangi sınıfta? Sınıfı sonucu görmeden deftere yazarsın; normal mumda yarıya dönüş
  bir sinyal değildir (2. ders, Normal ve reddedilen ilk mum). İzlenen üç saat bitince, öğleden sonra açıklama yoksa
  masadan kalkarsın.
- **TSİ {{ AN.boe.tsi_yaz }}, {{ AN.ecb.tsi_yaz }}, {{ AN.nfp.tsi_yaz }} (İngiltere, Avrupa ve ABD kış saatinde birer
  saat geç) — BoE (Londra 12:00), ECB (Frankfurt 14:15), ABD verileri (New York 08:30).** Soru: açıklamanın
  penceresinde açık emrim var mı? Emirleri pencereden önce gözden geçirirsin; verinin ilk beş dakikasının yönünü
  sonraki iki saatin yönü saymazsın (4. ders, ABD verileri).
- **TSİ {{ AN.ny_acilis.tsi_yaz }} (ABD kış saatinde {{ AN.ny_acilis.tsi_kis }}) — New York açılışı (New York
  09:30).** Soru: açılış sessiz mi? Sessiz açılışın kırılımına girmezsin (2. ders, Küçük ilk mum).
- **TSİ {{ AN.wmr.tsi_yaz }} (İngiltere kış saatinde {{ AN.wmr.tsi_kis }}) — Londra fiksingi (Londra 16:00).** Soru:
  ayın son Londra iş günü mü? Ay sonunda güçlü koşu fiksingden sonra öbür günlerden de az sürer (3. ders, Ay sonu).
  Fiksingden sonraki bir saat dolunca, karar günü değilse günün masası biter.
- **TSİ {{ AN.fomc.tsi_yaz }} (ABD kış saatinde {{ AN.fomc.tsi_kis }}) — FOMC kararı (New York 14:00), yalnız karar
  günlerinde.** Soru: ilk mum hangi sınıfta? Adayın satırını deftere yazarsın, adayı kural saymazsın (5. ders, İşlem
  tepkileri).
- **TSİ 00:00 (ABD kış saatinde 01:00) — New York kapanışı (New York 17:00).** Soru: günün satırları dolu mu? Dolmayan
  limitleri ve "izle" satırlarında alınmayan işlemleri de yazarsın; defter kapanır.

{{# kart haber-acik }}

## Bir kuralı sınanmadan kullanmamak

Bu dersin yöntemi masada bir kurala uygulanabilecek dürüst yöntemdir ve sırası değişmez (1. ders, Bu planın dürüstlük
kuralları; 5. ders, Tepki nedir, nasıl seçildi).

1. **Kuralı sonuçtan önce yazarsın:** an, ilk mum sınıfı, emir türü, giriş, stop, hedef, süre ve hüküm eşiği. Sonradan
   doldurulan bir alan kuralı sınanmamış yapar.
2. **Bulunduğu dönemin sonucunu kanıt saymazsın.** Bu derste her işlem tepkisi 2018–2023'te artıda olduğu için
   seçildi; o artı seçimin kendisidir.
3. **Görülmemiş dönemde kuralı değiştirmezsin.** Değişen stop ya da hedef yeni bir kuraldır; sayaç sıfırdan başlar.
4. **Sayacı olay olarak tutarsın.** Aynı kararın dört paritedeki işlemi tek bir olaydır (5. ders, İşlem tepkileri).
5. **Hükmü önceden yazılmış kuralla verirsin:** {{ ON.hukum_en_az }} işlemin altında hüküm yok; aralık tümüyle sıfırın
   üstündeyse "çalışıyor", ortalama artı ama aralık sıfırı kapsıyorsa "zayıf", ortalama eksiyse "çalışmıyor".

Bedeli zamandır: yılda birkaç kez gelen bir an hüküm eşiğine yıllar sonra varır. Merkez bankası adaylarının bugün
"ölçülemedi" ya da "zayıf" kalmasının sebebi budur; beklemenin sonunda sonuç eksi de çıkabilir.

## Emri nereye koyarsın

Bu bölüm başka bir gerekçeyle bu anlardan birinde işleme girecek biri içindir. Planın tepkileri burada bir emir
haritasıdır; hiçbiri maliyetten sonra kazandırmadı ve aşağıdaki satırlar bunu değiştirmez (8. ders, Limit neden ucuz
görünür: ters seçim; 8. ders, Stop uzaklığı ve maliyet).

- **Güçlü, normal ve reddedilen ilk mumda limit.** Limit mumun yarısına, mumun yönünde; stop öbür ucun mum boyunun
  onda biri kadar ötesinde; hedef yarım R. Limit girişte makas ve kayma ödemez, çıkışta öder, ve yalnız fiyat aleyhine
  yürüdüğünde dolar: dolduysa mumun yönündeki okumanın o gün zayıfladığını bilirsin.
- **Küçük ilk mumda stop emri.** Kırılan uca konan stop emri kaymayı da öder ve fiyatın zaten yürüdüğü yerden alır (8.
  ders, Ucun kırılması); koruyucu stop yakın olduğu için maliyetin R'deki payı büyüktür.
- **Fiksingde ve karar mumunda piyasa emri.** Fiksingde koşunun tersine, stop koşunun ucunun ötesinde, hedef koşunun
  yarısı; karar mumunda kapanışta mumun yönünde, stop öbür ucun ötesinde ve uzak. İkisi de makası ve kaymayı girişte
  öder. Geri vermeyi limitle almak bu derste ölçülmedi.
- **Onay beklemek.** Bir mum daha beklemek girişi daha kötü bir fiyata taşır; onaydan sonraki girişin maliyetten
  önceki sonucu kapanıştaki girişten belirgin farklı çıkmadı (8. ders, Onay mumu).
- **Haber penceresinde.** Açıklamadan iki dakika önce ile on beş dakika sonrası arasında makas açılır ve stop emri
  genişleyen makasla dolar: stopun yeri değişmez, dolduğu fiyat değişir (4. ders, Haber anları için masa kartı).
- **İptal.** Emir anın izlenen süresi bitince ya da ömrüne bir açıklama düşünce çekilir. Dolmayan limit kaçan bir
  kazanç değil, deftere yazılacak bir satırdır.

## Kendi defterini tutmak

Bu dersin sonuçları bir defterden geldi: her alan olaydan önce tanımlanmıştı. Kendi defterin aynı soruyu
sorabilmelidir: bu kural görülmemiş günlerde maliyetten sonra ne verdi?

| Alan | Ne yazılır | Neden |
|---|---|---|
| An ve saat | Anın adı, yerel saat, TSİ, yaz ya da kış saati | Aynı an yılda iki TSİ saatinde gelir |
| Olay | Parite ve olay kimliği; aynı kararın dört paritesi tek kimlik | Sayaç olay sayar (5. ders, İşlem tepkileri) |
| İlk mum sınıfı | Mum kapanır kapanmaz, sonuçtan önce | Sonradan yapılan sınıflama sonucu seçer (1. ders, İlk mumun dört sınıfı) |
| Kural | Adı ve yazıldığı gün; değiştiyse yeni ad | Değişen kural yeni bir sınamadır (1. ders, Bu planın dürüstlük kuralları) |
| Emir | Tür, planlanan giriş, stop, hedef, süre | R'nin paydası planlanan risktir |
| Risk ve makas | İkisi de pip, emir anında | Maliyetin R'deki payı (8. ders, Stop uzaklığı ve maliyet) |
| Dolum | Doldu mu, fiyat, kayma | Dolmayan limit de satırdır (8. ders, Limit neden ucuz görünür: ters seçim) |
| Çıkış ve sonuç | Hedef, stop ya da süre; maliyetli ve orta fiyattan maliyetsiz R | İkisinin farkı ödediğin maliyettir (5. ders, Maliyet nereye gidiyor) |

"İzle" anlarında alınmayan işlem de bir satırdır; kuralın dışında başka bir gerekçeyle açılan işlemler ise ayrı bir
sayfada durur, yoksa kuralın sonucu senin seçimlerinle karışır.

## Sık yapılan hatalar

- **Kazanma oranını tek başına okumak.** Yakın hedef kazanma oranıyla birlikte başa baş oranını da yükseltir.
  Dayanak: 5. ders, Kazanma oranı ve net sonuç.
- **Kuralın bulunduğu dönemin sonucunu kanıt saymak.** Seçim artıyı şart koştuğu için o artı seçimin tanımıdır.
  Dayanak: 5. ders, Tepki nedir, nasıl seçildi.
- **Davranışı kâr sanmak.** Fiksingde geri verme şanstan sıktır ama maliyetsiz kenarı maliyetten küçüktür. Dayanak: 5.
  ders, Maliyet nereye gidiyor; 3. ders, Sınıf sınıf, şansın payıyla.
- **İşlem saymak, olay saymamak.** Bir kararın dört paritedeki işlemi birlikte hareket eder ve aralığı olduğundan dar
  gösterir. Dayanak: 5. ders, İşlem tepkileri.
- **Limitin dolum oranını iyi haber saymak.** Limit fiyat aleyhine yürüdüğünde dolar. Dayanak: 8. ders, Limit neden
  ucuz görünür: ters seçim.
- **Kuralı ara sonuca göre ayarlamak.** Her ayar görülmemiş dönemi biraz daha örneklem içine çevirir. Dayanak: 1. ders,
  Bu planın dürüstlük kuralları.

## Masa kontrol listesi

1. Saatler yaz mı kış mı? Londra açılışı TSİ {{ AN.londra_acilis.tsi_yaz }} mi {{ AN.londra_acilis.tsi_kis }} mi; New
   York açılışı TSİ {{ AN.ny_acilis.tsi_yaz }} mi {{ AN.ny_acilis.tsi_kis }} mi?
2. Takvimde açıklama var mı (BoE TSİ {{ AN.boe.tsi_yaz }}, ECB TSİ {{ AN.ecb.tsi_yaz }}, ABD verisi TSİ
   {{ AN.nfp.tsi_yaz }}, FOMC TSİ {{ AN.fomc.tsi_yaz }}; kış saatinde birer saat geç) ve penceresinde emrim var mı?
3. Bugün ayın son Londra iş günü mü (Londra fiksingi TSİ {{ AN.wmr.tsi_yaz }}, İngiltere kış saatinde
   {{ AN.wmr.tsi_kis }})?
4. Bu anın satırı "izle, işlem açma" mı?
5. Kural sonuçtan önce yazıldı mı ve bu dönemde değişmedi mi?
6. İlk mumun sınıfını sonucu görmeden yazdım mı?
7. Riskim ve makas kaç pip, maliyetin R'deki payı ne; başa baş oranı ne?
8. Emrin türü ne ve hangi saatte (TSİ) çekilecek?
9. New York kapanışında (TSİ 00:00, ABD kış saatinde 01:00) dolmayan limitler dahil bütün satırlar dolu mu?

## Grafik okuma alıştırmaları

**1.** Bir hafta boyunca Londra açılışının güçlü ilk mumunda yarıya limitle giren, yarım R hedefleyen kuralı izledin
("Güçlü açılış mumu: aynı dolum, iki yol" şeması). On işlemin altısı hedefe, dördü stopa gitti. "Altısı kazandı, kural
çalışıyor" deniyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Altı işlem yarım R'den üç R getirdi, dört işlem dört R götürdü: maliyetten önce bir R kayıp. Başa baş için üç işlemden
ikisi gerekir; on işlemde bu altıdan fazlasıdır. Kuralı "çalışıyor" saymazsın, on işlem hüküm eşiğinin de altındadır;
satırları maliyetli ve maliyetsiz sonuçlarıyla yazar, kuralı değiştirmezsin (5. ders, Kazanma oranı ve net sonuç).

</details>

**2.** FOMC kararının (New York 14:00, TSİ {{ AN.fomc.tsi_yaz }}; ABD kış saatinde {{ AN.fomc.tsi_kis }}) ilk beş
dakikası dört paritede güçlü bir mumla kapandı ("Güçlü karar mumu" şeması). Defterine kaç olay yazarsın? Adayı riskle
kurar mısın?

<details>
<summary>Çözüm</summary>

Dört satır, tek olay kimliği; sayaç bir karar günü artar. Adayı riskle kurmazsın: hükmü "ölçülemedi", işlemleri
birkaç karar gününe dayanıyor. Kuralı bu karara bakarak değiştirmezsin (5. ders, İşlem tepkileri).

</details>

**3.** Ayın son Londra iş günü, Londra fiksingine (Londra 16:00, TSİ {{ AN.wmr.tsi_yaz }}; İngiltere kış saatinde
{{ AN.wmr.tsi_kis }}) güçlü bir koşu geldi ("Londra fiksingine koşu" şeması); fiksingden sonra fiyat koşunun yönünde
birkaç pip daha yürüdü. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Kovalamazsın: ay sonunda güçlü koşu fiksingden sonra öbür günlerden de az sürer (3. ders, Ay sonu). Tersine de
girmezsin: geri vermenin maliyetsiz kenarı maliyetten küçüktür ve plan burada "izle" der (5. ders, Maliyet nereye
gidiyor). Ucu ve yarıyı işaretler, fiksingden sonraki bir saati yazarsın.

</details>

**4.** Sessiz bir New York açılışında (New York 09:30, TSİ {{ AN.ny_acilis.tsi_yaz }}; ABD kış saatinde
{{ AN.ny_acilis.tsi_kis }}) küçük ilk mumun üst ucu kırıldı; makas ekranda açık ("Aynı makas, iki stop" şeması).
Kırılıma stop emriyle girmeyi düşünüyorsun.

<details>
<summary>Çözüm</summary>

Makası riske bölersin: küçük stopta pay büyüktür ve stop emri kayma da öder. Açılışta küçük mumun kırılımının
maliyetsiz sonucu sıfıra yakındır (5. ders, Maliyet nereye gidiyor) ve sessiz açılışın kırılımı sinyal değildir (2.
ders, Küçük ilk mum). Girmezsin; stopu uzaklaştırmak payı küçültür, kenar yaratmaz (8. ders, Stop uzaklığı ve maliyet).

</details>

## Bu sonuç nasıl okunmalı

- **Okumalar iki dönemde aynı kaldı.** Açılışta ve fiksingte fiyatın davranışı iki dönemde de aynı. Bu okumaların
  başka bir kurulumu iyileştirip iyileştirmediği bu seride ölçülmedi.
- **Plan bir işlem sistemi olarak kazandırmıyor.** Açılışta okumanın kenarı maliyetten önce de yok; fiksingde var ama
  maliyeti karşılayacak kadar büyük değil.
- **Kazanma oranı kurulabilir, kâr kurulamadı.** Yakın hedefle işlemlerin çoğunu kazanmak mümkün; ama açılış ve
  fiksinglerde 2018–2023'te denenen stop ve hedef bileşimlerinin hiçbiri bu maliyetle net sonucu artıya çevirmedi.
- **Merkez bankası kararları izlenecek tek yer.** Artı sonuç 2024 → döneminde orada; ama birkaç karar gününe dayanıyor.
  Bir kural olması için bundan sonraki kararlarda, bugünkü hâliyle değiştirilmeden sınanması gerekir.

## Ölçülmeyenler

- Gerçek sürpriz: veri ve kararlarda beklentiye göre sapma ölçülmedi; ilk mum sapmanın vekilidir.
- Basın toplantısının karar metninden ayrı etkisi.
- Gün içi dokunuşların sırası dakikadan kısa sürelerde (aynı dakikada stop ve hedef görülürse stop sayıldı).
- Piyasa derinliği, kısmi dolum, komisyon ve emir gecikmesi.
- {{ pariteler }} dışındaki pariteler ve beş dakikadan kısa ilk mumlar.

Veri Dukascopy'nin bir dakikalık alış ve satış fiyatlarıdır (2018 başından {{ veri_bitis }} tarihine kadar).
