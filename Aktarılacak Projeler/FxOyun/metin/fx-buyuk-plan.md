---
title: 'FX Gün İçi Oyun Planı 9: Büyük Mum — Oyun Planı ve 2024 Sınaması'
description: "Büyük mum okumalarından 2018–2023 verisiyle seçilip 2024 sonrası hiç görülmeden kaydedilen giriş planı: seçim kuralı, taranan {{ plan.aday }} aday, seçilen üç giriş, on iki referans giriş ve 2024 → döneminin sonucu. Sonunda büyük mum için bir oyun planı."
pubDate: 2026-10-20
tags: ['fx', 'gun-ici', 'oyun-plani', 'buyuk-mum', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "2018–2023'ün en iyi üç büyük mum girişi 2024 sonrasında tutmadı; on iki referans girişin hiçbiri de artıda değil. 5 dakikadaki geri verme 2024 sonrasında da görüldü, 1 saatteki devam yalnız nokta tahmini olarak; ikisi de her girişte maliyetten küçük. Büyük mum bir işlem sinyali değil, bir okuma: nerede kovalanmaz, nerede limitin dolması kötü haberdir, nerede masadan kalkılır."
seviye: 'orta'
onkosul: ['fx-buyuk-mum', 'fx-buyuk-suzgec', 'fx-buyuk-giris']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Önceki üç ders büyük mumu okudu, süzdü ve girişin biçimini ölçtü. Bu ders o çalışmanın sınavıdır. 2018–2023'ün sonucu
görülerek bir seçim kuralı yazıldı, kural o dönemin tablosuna uygulandı ve seçilen girişler, 2024 ve sonrasının
fiyatları hiçbir hesaba girmeden, ön kayıtla birlikte kaydedildi. Sonra aynı kurallar 2024 → döneminde
({{ ON.dis_bitis }} tarihine kadar) koşturuldu. Bu dersin 2024 → sayılarının hepsi o sınamadan.

## Kısaca

Kısa cevap: 5 dakikada büyük mumu kovalamazsın, 1 saatte tersine girmezsin. İki eğilim de 2018–2023'te ölçülebiliyor,
5 dakikadaki 2024 sonrasında da; ikisi de maliyetten sonra işlem çıkarmıyor. Limit maliyeti düşürür, kenar yaratmaz.

- **Seçilen üç girişin üçü de tutmadı.** 2018–2023'te iki yarıda da artı olan en iyi girişler 2024 sonrasında eksi ya da
  sıfırdaydı. En iyisi (1 saatte, aynı yönde koşudan sonraki büyük mumda mumun {{ Y.25 }} geri çekilmesine limit) 2018–2023'te
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.ic.R }} R verdi, 2024 sonrasında
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.R }} R.
- **On iki referans girişin hiçbiri artıda değil.** Büyük mumdan sonra "mumun yönünde gir", "yarısına limitle katıl",
  "tersine gir", "uzamayı sat" girişleri her dilimde maliyetten sonra eksi.
- **Hüküm: {{ hukum_cumle }}.** Hiçbiri "zayıf" ya da "çalışıyor" almadı.
- **Davranış kısmen sürdü, kenar sürmedi.** 5 dakikadaki hafif geri verme 2024 sonrasında da aralığıyla görüldü;
  1 saatteki devam 2024 sonrasında yalnız nokta tahmini olarak sürdü ({{ D.60.dis.net_24 }} ATR, aralık
  {{ D.60.dis.net_24_alt }} … {{ D.60.dis.net_24_ust }}). İkisi de her girişte maliyetten küçük (6. ders, Dilim dilim
  okuma).

## Bu dersi masada nasıl kullanırsın

Tablolar işlem listesi değildir; on beş girişin hepsi çalışmıyor. Masada kullanılan, arkalarındaki sıradır. Büyük mum
6. dersin tanımıyla okunur (6. ders, Büyük mum nasıl tanımlandı). Şema sırayı verir: dilim, takvimdeki haber, kapanışın
yeri, seans.

{{# karar plan-akis }}

Şemanın hiçbir kutusu "gir" demez; bu sınamanın sonucudur (9. ders, Hüküm kuralı). Mumdan bağımsız bir gerekçeyle
zaten işleme girecek biri için emrin kuralları "Emri nereye koyarsın" bölümündedir.

## Seçim kuralı

Kural, 2018–2023 ızgarası görüldükten sonra ve 2024 sonrasının fiyatları hiçbir hesaba girmeden ön kayda yazıldı:

1. Her dilim (5 dakika, 15 dakika, 1 saat) ve her yön (mumun yönünde, tersine) için aday girişler: 8. dersin ızgarasının
   bütün hücreleri (emir biçimi × stop × hedef), süzgeçsiz ya da 7. dersin süzgeçlerinden **tek bir** değerle.
2. Uygun aday: 2018–2023'te en az {{ ON.secim_en_az }} işlem, maliyetten sonra ortalaması sıfırın üstünde, **ve**
   2018–2020 ile 2021–2023 yarılarının ikisinde de sıfırın üstünde.
3. Uygunların içinden maliyetten sonra ortalaması en yüksek olan seçilir. Uygun aday yoksa o dilim ve yön için "işlem
   yok".

Kural toplam {{ plan.aday }} adayı taradı: bu kadar adayın en iyisini seçmek, onun 2018–2023 sonucunu şansla
şişirir; 2024 → dönemi o şişkinliği ölçer.

Stop emirli girişlerde dolum dakikasının sayılışı 2024 sınamasından sonra değişti (8. ders, Ölçülmeyenler). Seçim yeni
kuralla yeniden uygulandı: seçilen üç giriş, referanslar ve 2024 → sonuçları aynı kaldı; değişen tek şey, "işlem yok"
denen 15 dakika tersine hücresinin en iyi adayı oldu.

Seçimin bir sınırı var: 2024 sonrasının toplu davranışı bu seride başka kurallardan biliniyordu; büyük mumdan sonraki
davranışın ve bu girişlerin 2024 sonrası sonucu ise ölçülmemişti.

## Seçilen girişler

{{# bacaklar islem }}

Altı dilim × yön hücresinden {{ plan.islem_sayi }} hücrede kurala uyan bir aday çıktı, {{ plan.yok_sayi }} hücrede
çıkmadı. Seçilenlerin üçü de bir süzgeç taşıyor (ikisi haber mumu, biri koşudan sonraki büyük mum). Rastlantı değil:
süzgeçli adaylar kat kat fazladır ve küçük alt küme, şansın en kolay şişirdiği yerdir.

- **5 dakika, haber mumunu ucundan tersine.** 2018–2023'te {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.ic.n }} işlem,
  iki yarıda {{ P.5.ters.y1 }} ve {{ P.5.ters.y2 }} R. 2024 sonrasında {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.n }}
  işlem, {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.R }} R. Maliyetten önce
  {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.brut }} R.
- **1 saat, aynı yönde koşudan sonraki büyük mumda {{ Y.25 }} geri çekilmeye limit.** 2018–2023'te iki yarıda
  {{ P.60.devam.y1 }} ve {{ P.60.devam.y2 }} R. 2024 sonrasında {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.n }}
  işlem, {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.R }} R ({{ Y.95 }} aralık
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.alt }} … {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.ust }};
  hafta düzeyinde {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.hafta_alt }} …
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.hafta_ust }}). Maliyetten önce de eksi
  ({{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.brut }} R): 2018–2023'teki sonuç görülmemiş dönemde tekrarlanmadı.
- **1 saat, haber mumunu ucundan tersine.** 2018–2023'te {{ B.islem.60.ters:limit_uc:s1:h2.haber=haber.ic.R }} R (en küçük
  artı), 2024 sonrasında {{ B.islem.60.ters:limit_uc:s1:h2.haber=haber.dis.R }} R.

Kuralın "işlem yok" dediği hücreler ve o hücrelerin en iyi adayı:

{{# yok }}

### Masada: seçilen ama tutmayan girişler

Üç girişin ikisi haber mumundan, yani 7. dersin "okuma yok" dediği yerden çıktı (7. ders, Fade mi, devam mı: okuma
tablosu): seçim kuralı okumayı bilmez, en yüksek ortalamayı arar, ve o ortalama çoğu zaman olayı az, dağılımı geniş
yerde şansla çıkar.

{{# sema uc-limit }}

1 saatlik giriş küçük alt kümenin dersini verir. Koşu süzgeci 24 mumluk yolu kendi başına ayırmıyordu (7. ders, 1
saat); ızgaranın tek bir hücresiyle birleşince iki yarıda artı göründü, 2024 sonrasında maliyetten önce de eksi kaldı.

{{# kart kosu-sonrasi }}

## Referans girişler

Her dilimde aynı dört giriş de koşturuldu: büyük mum için en sık söylenen dört tepkinin en düz hâli. Seçimden
bağımsızdırlar, 2018–2023'teki sonuçları da bu yüzden şişmemiştir.

{{# bacaklar referans }}

Referansların hepsi 2024 sonrasında maliyetten sonra eksi. Maliyetten önce 5 dakikada tersine piyasa girişi
({{ B.referans.5.ters:piyasa:s2:h1.dis.brut }} R) ve 1 saatte mumun yönündeki girişler sıfırın biraz üstünde: 6. dersin
okumaları burada da görünüyor, ama yine maliyetin altında.

{{# sekil 01_bacaklar "On beş girişin iki dönemi" }}

{{# sekil 02_egri "Seçilen üç giriş, birikimli" }}

### Masada: dört düz tepki

Referanslar en sık duyulan dört cümlenin ölçülmüş karşılığıdır; dördü aynı mumun üstüne üç çizgiyle konur.

{{# sema dort-tepki }}

Maliyetten önceki işaret mumun o dilimdeki küçük bilgisini söyler (5 dakikada tersine taraf, 1 saatte mumun yönü;
6. ders, Dilim dilim okuma); maliyetten sonrası on iki satırın on ikisinde eksi.

## Hüküm kuralı

Hüküm 2024 → dönemi için ön kaydın kuralıyla verildi: dört parite birlikte, ortalama net R'nin {{ Y.95 }} aralığı,
{{ ON.bootstrap }} tekrarlı ve **işlem günü düzeyinde** yeniden örneklemeyle, çünkü büyük mumlar dolar haberinde dört
paritede aynı anda olur. 1 saatlik işlemler ertesi güne
taşabildiği için tablolardaki ikinci aralık hafta düzeyindedir (FX haftası hafta sonu boşluğuyla biter); hükmü
değiştirmez. Aralığın alt ucu sıfırın üstündeyse "çalışıyor", ortalama artı ama alt uç sıfırın altındaysa "zayıf",
ortalama sıfır ya da eksiyse "çalışmıyor";
{{ ON.hukum_en_az }} işlemin altında "ölçülemedi". Sonuç: {{ hukum_calismiyor }} çalışmıyor, {{ hukum_zayif }} zayıf,
{{ hukum_calisiyor }} çalışıyor, {{ hukum_olculemedi }} ölçülemedi.

## Kendi seçim kuralını yazarken: tuzaklar

Bu dersin asıl öğrettiği, bir seçim kuralının nasıl yanıldığıdır:

1. **Aday sayısını saymamak.** Denediğin her süzgeç, stop ve hedef bir adaydır, not etmediklerin de (9. ders, Seçim
   kuralı).
2. **İki yarıyı ikinci bir sınav sanmak.** Seçilen üç girişin üçü de iki yarıda artıydı ve tutmadı; seçim o veriyle
   yapıldıktan sonra yarılar bağımsız bir kanıt olmaz (9. ders, Seçilen girişler).
3. **Küçük alt kümeye güvenmek.** Olay azaldıkça ortalama şansla kolay şişer (9. ders, Seçilen girişler).
4. **Maliyetten önceki sonuçla seçmek.** Maliyetten önce sıfırın biraz üstünde kalan girişlerin hepsi maliyetten sonra
   eksi (9. ders, Referans girişler).
5. **Görülmüş dönemi görülmemiş saymak ya da kuralı sonuçtan sonra değiştirmek.** İkisi de bu planda oldu ve ikisi de
   yazıldı (9. ders, Seçim kuralı).
6. **Olayları bağımsız saymak.** Dolar haberinde dört paritede aynı anda büyük mum çıkar; hükmü gün ya da hafta
   düzeyinde ve sonucu görmeden yazarsın (9. ders, Hüküm kuralı).
7. **Kıyas noktası koşturmamak.** Seçimin şişirmediği tek kıyas, aynı dilimin en düz tepkisidir (9. ders, Referans
   girişler).

## Büyük mum için oyun planı

Ölçümün söylediği bir giriş kuralı değil, bir dizi "yapmazsın"dır; her maddenin hangi dönemde tuttuğu içinde yazılı.

1. **Büyük mumu tek başına bir sinyal saymazsın.** Büyük mumdan sonra fiyatın önce hangi yöne 1 ATR gideceği 5 dakikada
   bir yazı turadan birkaç puan uzakta; 15 dakika ve 1 saatte yazı turadan ayırt edilemiyor (6. ders, Dilim dilim
   okuma).
2. **5 dakikada kovalamazsın; limitin dolmasını da iyi haber saymazsın.** Ucunda kapanan büyük mum, özellikle Asya'da,
   yarısını aynasından biraz sık geri verir (6. ders, Dilim dilim okuma; 7. ders, 5 dakika). Mumun yönünde gireceksen
   çeyrek ya da yarı geri çekilmeye konan limitle girersin; bu kenar değil, daha az kötü bir fiyattır: limit fiyatın geri
   çekildiği olaylarda dolar ve o olaylarda mumun yönündeki işlem çoğunlukla kaybeder (8. ders, Limit neden ucuz
   görünür: ters seçim).
3. **5 dakikada tersine girmenin küçük kenarını limit yok eder.** Geri verme kenarı kapanışta tersine piyasadan girene
   maliyetten önce kalır; mumun ucuna limitle bekleyene kalmaz (8. ders, 5 dakika).
4. **1 saatte tersine girmezsin.** 1 saatlik büyük mum ortalama bir gün boyunca mumun yönünde bir parça daha gider;
   2018–2023'te aralığıyla, 2024 sonrasında yalnız nokta tahmini olarak (6. ders, Dilim dilim okuma). Tersine giriş
   biçimleri 2018–2023'te maliyetten önce de eksiydi, 2024 sonrasında maliyetten önce sıfırın çevresinde kaldı
   (8. ders, 15 dakika ve 1 saat). Bu bir giriş değil, bir "tersine girmezsin" uyarısıdır.
5. **Stopu yaklaştırmazsın.** 5 dakikada 1 ATR'lik stopla makas ve kayma işlem başına R'nin önemli bir kısmını yer
   (8. ders, Stop uzaklığı ve maliyet).
6. **Haber mumunda okuma yok.** Takvimdeki büyük haberin mumu az ve 24 mum sonraki yolu, ortalaması bir yön
   söyleyemeyecek kadar dağınık (7. ders, Fade mi, devam mı: okuma tablosu). Seçimin iki girişi buradan çıktı ve 2024
   sonrasında tutmadı.

### Masada: planın altı maddesi

Her madde masada bir görüntüye karşılık gelir; aşağıda maddeler sırayla, her biri bir şema ya da bir kartla.

**Madde 1, tek başına sinyal yok.**

{{# sema iki-yol }}

**Madde 2, 5 dakikada kovalamazsın; limitin dolması iyi haber değil.** Kapanışta kovalamak kötü bir fiyattır; yarıya
konan limit de kazanan bir işlem değildir.

{{# sema yari-limit }}

{{# kart bes-dk-kovalama }}

**Madde 3, tersine girmenin küçük kenarını limit yok eder** ({{# atif sema uc-limit }}; 8. ders, 5 dakika).

{{# kart bes-dk-tersine }}

**Madde 4, 1 saatte tersine girmezsin.** Maddenin masadaki tek işi, "çok uzadı" diye kurulan ters işlemi plana
yazdırmamaktır.

{{# kart saat-tersine }}

**Madde 5, stopu yaklaştırmazsın.**

{{# sema stop-makas }}

**Madde 6, haber mumunda okuma yok.**

{{# kart haber-mumu }}

## Masada: üç örnek

6. dersin Şekil 01'indeki üç EUR/USD mumunu bu planla okumak, planın ne yaptığını ve ne yapmadığını gösterir.

**5 dakikalık mum** ({{ O.5.gun }}, başlangıcı TSİ {{ O.5.saat }}, {{ O.5.yon }}, {{ O.5.kat }} ATR) kapanışı
aralığının {{ O.5.kapanis }} kaldı. Plan kovalamamayı söyler (madde 2). Fiyat mumun yarısına {{ O.5.geri50 }}; yarıdaki
limit orada dolardı ve plan bunu bir uyarı sayar. Bu örnekte uyarı yanıldı: fiyat sonra mumun ucunu {{ O.5.uc }} ve 24
mum sonra mumun yönünde {{ O.5.net24 }} ATR'deydi.

**15 dakikalık mum** ({{ O.15.gun }}, başlangıcı TSİ {{ O.15.saat }}, {{ O.15.yon }}) için plan zayıf bir geri verme
beklentisinden fazlasını söylemez (7. ders, 15 dakika). Fiyat yarısına {{ O.15.geri50 }}, ucunu {{ O.15.uc }} ve 24 mum sonra
{{ O.15.net24 }} ATR'deydi.

**1 saatlik mum** ({{ O.60.gun }}, başlangıcı TSİ {{ O.60.saat }}, {{ O.60.yon }}) kapanışı aralığının
{{ O.60.kapanis }} kaldı. Plan tersine girmemeyi söyler (madde 4). Fiyat mumun yarısına {{ O.60.geri50 }}, ucunu
{{ O.60.uc }} ve bir gün sonra mumun yönünde {{ O.60.net24 }} ATR'deydi: tersine giren bir işlemci zarar ederdi, mumun
yönünde giren ise bir günün sonunda maliyetini çıkaramazdı.

Örneklerin hiçbiri planı sınamaz, sınaması yukarıdaki tablolardır; gösterdikleri, planın bir işlem kuralı değil bir
okuma sırası olduğudur.

Aşağıdaki iki çift ise kuralla seçildi: koşula uyan olaylardan 1 Aralık 2023'ten önceki, serinin başka bir yerinde
gösterilmemiş en son olay; biri dersin ölçtüğü eğilimle biten tipik gün, öbürü ters giden gün. Tarihleri ve fiyatları
figür gösterir. Gerçek grafiklerde ① olay mumu,
② mumun yarısı, ③ fiyatın yarıya ilk dokunduğu an, ④ izleme penceresinin sonudur.

{{# ornek plan-asya-5dk }}

İki gün de USD/JPY'de, Asya seansında, haber yokken ucunda kapanan 5 dakikalık bir büyük mum; kapandığı anda ayırt
edilemezler. Üstteki günde ① aşağı yönlü mum (TSİ 01:55) dibine yakın kapandı; fiyat bir sonraki mumun ilk dakikasında
③ yarıya dokundu, yani mumun yönündeki satış limiti orada dolardı. Aynı mumda öbür uç kırıldı ve fiyat bir saat kadar
yükseldi: yarıdaki satışın iki ATR'lik stopu TSİ 02:05 mumunda, kapanışta kovalayanınki ilk mumda görüldü. Fiyat mumun
dibine ancak TSİ 03:50'de indi; ④'te (TSİ 04:00) yeniden mumun içinde, kapanışın biraz üstündeydi. Alttaki günde ①
yukarı yönlü mum (TSİ 09:20, Londra 07:00 açılışından önce; TSİ İngiltere kış saatinde 10:00) sonraki ilk dakikada
çeyrek geri çekildi, yarıya hiç dönmedi (③ yok) ve ④'te (TSİ 11:25) tepesinin bir mum boyundan fazla yukarısındaydı.
Yarıdaki alış limiti dolmadı, kaçan işlem kazanandı; çeyrekteki limit ilk dakikada doldu ve bir R hedefini TSİ 10:05
mumunda gördü. İki günü ayıran, mum kapandıktan sonra gelen yarıya dokunuştur (8. ders, Limit neden ucuz görünür: ters
seçim); tek bir çift Asya'daki geri vermeyi ne doğrular ne yanlışlar.

{{# ornek plan-saat-kosu }}

Bu çift seçimin 1 saatlik girişinin durumundandır: önceki on iki mumda mumun yönünde en az iki ATR yürümüş bir
piyasada, haber olmadan gelen ve ucunda kapanan büyük mum; iki gün de EUR/USD'de, Londra ile New York'un örtüştüğü
saatlerde. Üstteki günde ① aşağı yönlü mumdan (TSİ 18:00) sonra fiyat çeyrek geri çekilme seviyesine bile gelmedi
(③ yok), bir sonraki saatte bir mum boyundan fazla düştü ve ④'te (ertesi gün TSİ 19:00) dibin iki mum boyundan fazla
altındaydı: çeyrek limit dolmadı, kaçan işlem kazanandı. Alttaki günde ① yukarı yönlü mumdan (TSİ 15:00) sonra çeyrek
limit ilk dakikada doldu ve seçilen girişin bir ATR'lik stopu aynı saatte görüldü; fiyat ③'te (TSİ 16:22) yarıya dokundu,
TSİ 17:00'de öbür ucu kırdı ve ④'te (ertesi gün TSİ 19:00) yarının hemen üstündeydi.

## Emri nereye koyarsın

Emrin biçimi, stop (girişten, limitle giriyorsan limitin fiyatından iki ATR; ölçülen stoplar bir ve iki ATR, mumun öbür
ucunun ötesi bu seride ölçülmedi), hedef (bir ya da iki R), altı mumluk ömür ve haber penceresi 8. dersin aynı adlı
bölümündedir (8. ders, Emri nereye koyarsın) ve bu planla aynıdır. Hiçbiri bir kenar değildir: stop iki ATR ve hedef
bir R ile ölçülen giriş biçimlerinin hepsi maliyetten sonra eksi (8. ders, Kısaca). Planın eklediği iki şey var:

- **Planın sustuğu mumlar.** 1 saatlik grafikte perşembe akşamından sonra açılan mumlar, FX gününün devrine değen mum
  (New York 16:50–17:10; TSİ ABD yaz saatinde 23:50–00:10, kış saatinde 00:50–01:10) ve hafta başı yeniden açılışın ilk
  saati ölçüye girmedi (6. ders, Büyük mum nasıl tanımlandı). Bu mumlarda plan bir şey söylemez.
- **Dolmayan limit.** Altı mum içinde dolmayan limitin peşinden kovalamazsın: limitin dolmadığı olaylar, mumun yönündeki
  piyasa girişinin daha sık kazandığı olaylardır (8. ders, Limit neden ucuz görünür: ters seçim). Süresine seans geçişi
  ya da takvimdeki büyük bir haberin penceresi düşen emri önceden çekersin; bu bir disiplin kuralıdır (masa uygulaması;
  ölçülmedi).

## Sık yapılan hatalar

- **Seçilen girişler tablosunu işlem listesi gibi okumak.** 2018–2023 sütunu seçimin kendisi, 2024 sütunu sınavı; üçü
  de tutmadı (9. ders, Seçilen girişler).

## Masa kontrol listesi

Büyük bir mum kapandığında sırayla:

1. Dilim 5 dakika, 15 dakika ya da 1 saat mi? Değilse bu seri bir şey ölçmedi.
2. Mum kümenin ilk büyük mumu mu? Önceki üç mumdan biri de büyükse aynı olayın devamıdır.
3. Mum FX gününün devrine ya da hafta başı açılışın ilk saatine mi değiyor (saatleri "Emri nereye koyarsın"
   bölümünde)? Öyleyse ölçüye girmedi.
4. Takvimde büyük bir haber (ABD istihdam ve enflasyon, Fed, ECB, BoE; saatleri 6. ders, Masa kontrol listesi) mumun
   içine düşüyor mu? Varsa masadan kalkarsın.
5. Dilim 1 saatse aklındaki işlem mumun tersine mi? Plana yazmazsın. Mum perşembe akşamından sonra mı açıldı? Ölçüye
   girmedi.
6. Dilim 5 dakikaysa kapanış uç çeyrekte mi, seans Asya mı (New York 17:00 ile Londra 07:00 arası; TSİ ABD ve İngiltere
   yaz saatinde 00:00–09:00, kış saatinde 01:00–10:00), önceki 4–24 mumda başka büyük mum var mı? Kovalamazsın.
7. Mumdan bağımsız bir gerekçen var mı? Yoksa masadan kalkarsın.
8. Varsa: limit çeyrek ya da yarı geri çekilmede mi, stop girişten iki ATR öte mi, planlanan risk üç pipin üstünde mi,
   limit dolarsa ne düşüneceğini not ettin mi?
9. Emir altı mum içinde dolmadıysa çekersin; süresine seans geçişi ya da haber penceresi düşüyorsa önceden çekersin
   (masa uygulaması; ölçülmedi).

## Grafik okuma alıştırmaları

**1.** 5 dakikalık EUR/USD grafiğinde Londra 08:30'da (TSİ İngiltere yaz saatinde 10:30, kış saatinde 11:30) başlayan
yukarı yönlü, üç ATR'lik bir büyük mum ucunda kapandı; takvimde haber yok. Daha büyük dilimdeki bir destek yüzünden
zaten alıcı olmayı düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Kapanışta kovalamazsın (9. ders, Büyük mum için oyun planı, madde 2). Gerekçen duruyorsa alış limitini çeyrek ya da
yarı geri çekilmeye, stopu girişten iki ATR öteye koyarsın; altı mum içinde dolmazsa çekersin (8. ders, On bir giriş
biçimi). Dolarsa okumanın zayıfladığını bilirsin (8. ders, Limit neden ucuz görünür: ters seçim). Büyük mum gerekçeni
güçlendirmez: 5 dakikada yön bilgisi değil, hafif bir geri verme taşır (6. ders, Dilim dilim okuma).

</details>

**2.** 1 saatlik GBP/USD grafiğinde New York 09:00'da (TSİ ABD yaz saatinde 16:00, kış saatinde 17:00) başlayan aşağı
yönlü, dört ATR'lik bir mum günün yeni dibini yaptı ve ucunda kapandı. Masadaki biri "ucun yarım ATR altına alış limiti
koyalım" diyor. Ne yaparsın?

<details>
<summary>Çözüm</summary>

Uzamayı almazsın: 1 saatlik büyük mumun ortalama yolu mumun yönündedir (6. ders, Dilim dilim okuma) ve "ucun yarım ATR
ötesine limit" referansı 1 saatte iki dönemde de maliyetten sonra eksi (9. ders, Referans girişler). Dört ATR olması da
bir dönüş işareti değildir (6. ders, Büyüklük değişince).

</details>

**3.** 5 dakikalık USD/JPY grafiğinde ABD enflasyon verisinin mumu (New York 08:30; TSİ ABD yaz saatinde 15:30, kış
saatinde 16:30) yukarı yönlü ve ucunda kapandı. 2018–2023 tablosu bu durum için "mumun ucuna tersine limit"i seçmişti.
Ne yaparsın?

<details>
<summary>Çözüm</summary>

Masadan kalkarsın: karar şemasının ({{# atif karar plan-akis }}) ikinci sorusu seni orada durdurur. Haber mumunda okuma
yok (7. ders, Fade mi, devam mı: okuma tablosu) ve o giriş 2024 sonrasında maliyetten sonra eksi kaldı (9. ders, Seçilen
girişler). Tablonun satırını plana kopyalamazsın.

</details>

**4.** Yarıya alış limiti şemasındasın ({{# atif sema yari-limit }}): limit ② noktasında doldu, fiyat bir mum daha düştü
ve stopa yaklaşıyor. Stopu yaklaştırmak ya da daha aşağıya ikinci bir alış limiti koymak aklından geçiyor. Ne yaparsın?

<details>
<summary>Çözüm</summary>

İkisini de yapmazsın. Ölçülen emirlerde stop sabitti; iz süren stop ve pozisyona ekleme bu seride ölçülmedi (9. ders,
Ölçülmeyenler). Ölçülen şey, limitin dolduğu olaylarda piyasa girişinin çoğunlukla kaybettiğidir; ikinci limit aynı ters
seçimin ikinci kez yaşanmasıdır (8. ders, Limit neden ucuz görünür: ters seçim).

</details>

## Bu sonuç nasıl okunmalı

Bu serinin önceki derslerinde de görülen tablo burada da tekrarlandı: davranış gerçek, kenar maliyetten küçük. Büyük
mumdan sonra fiyatın yaptığı şey tamamen rastgele değil: 5 dakikada biraz geri verir (iki dönemde de), 1 saatte biraz
devam eder (2018–2023'te aralığıyla, 2024 sonrasında yalnız nokta tahmini olarak). Ama "biraz" 5 dakikada bir pipin
altında, makas ise bir pipe yakın; 1 saatte iki pip kadar ve makastan büyük, ama stoplu ve hedefli bir işlemde
maliyetten önce ancak sıfırın biraz üstünde kalıyor. Seçim kuralının bulduğu artı
girişler, binlerce adayın içinden şansın en kolay şişirdiği küçük alt kümelerden çıktı ve görülmemiş dönemde söndü.

## Ölçülmeyenler

- **İki süzgeçli bileşimler** seçime girmedi (ön kayıt kuralı).
- **Dinamik çıkış, kısmi kâr, iz süren stop ve pozisyona ekleme** ölçülmedi.
- **Komisyon ve kısmi dolum** yok; limit dolumu tablodakinden kötü olabilir.
- **Dört majör dışı pariteler ve 1 saatten büyük dilimler** ölçülmedi.
- **Perşembe akşamından sonra açılan 1 saatlik mumlar.** 24 mumluk pencere hafta sonuna taştığı için ölçüye girmedi
  (6. ders, Büyük mum nasıl tanımlandı); ABD istihdam raporunun 1 saatlik mumu bu yüzden hiçbir 1 saatlik ölçüde yok.
