---
title: 'FX Gün İçi Oyun Planı 6: Büyük Mum — 2, 3, 4, 5 ATR''den Sonra Ne Oluyor'
description: "Aralığı önceki ATR'nin en az iki katı olan bir 5 dakikalık, 15 dakikalık ya da 1 saatlik mumdan sonra fiyat genelde ne yapıyor: devam mı, geri çekilme mi, tam dönüş mü? 2018–2023'ün {{ D.5.ic.n }} + {{ D.15.ic.n }} + {{ D.60.ic.n }} büyük mumu, şansın vereceği payla kıyaslı ve 2024 sonrasında yeniden ölçülmüş."
pubDate: 2026-10-20
tags: ['fx', 'gun-ici', 'oyun-plani', 'buyuk-mum', 'atr', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Büyük bir mumdan sonra fiyatın çoğu zaman mumun yarısına döndüğü doğru, ama bunun büyük kısmı mumun kendi şeklinden gelir. Şansın payı düşülünce kalan şu: 5 dakikada hafif bir geri verme (iki dönemde de), 15 dakikada daha zayıf bir geri verme, 1 saatte hafif bir devam (2024 sonrasında yalnız nokta tahmini olarak). 5 dakikadaki makastan küçük; 1 saatteki makastan büyük ama stoplu ve hedefli bir işlemde maliyeti karşılamıyor."
seviye: 'orta'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Grafikte bir mum öbürlerinden belirgin uzun çıktığında iki refleks yarışır. Biri "momentum geldi, mumun yönüne bin"
der; öbürü "fazla gitti, geri gelecek, tersine gir" der. Bu ders ve sonraki üçü o iki refleksi ölçer. Önce büyük mumdan
sonra fiyatın ne yaptığını (bu ders), sonra hangi koşulda hangi refleksin daha haklı çıktığını (7. ders), sonra girişin
nasıl yapılacağını (8. ders) ve en sonda 2018–2023 verisinden yazılıp 2024 sonrasında sınanan bir oyun planını
(9. ders).

Seri önceki derslerdeki gibi iki dönemli çalışır. Bütün okumalar 2018–2023 verisinden yapıldı; giriş planı o dönemden
yazılıp 2024 ve sonrasının fiyatları hiçbir hesaba girmeden kaydedildi. 2024 → döneminin sayıları ({{ ON.dis_bitis }} tarihine
kadar) aynı kurallarla sonradan ölçüldü ve her tabloda yan yana durur.

## Kısaca

- **Büyük mum sık.** Aralığı önceki ATR'nin en az iki katı olan mum 5 dakikalık grafikte bir parite için günde ortalama
  {{ D.5.ic.gunde }} kez görüldü (kümenin devamı, kararsız mumlar ve öbür dışarıda bırakılanlar sayılmadan). Yani "büyük mum" nadir bir olay
  değil, günün sıradan bir parçası.
- **Mumun yarısına dönüş çok sık, ama çoğu şekilden.** 5 dakikalık büyük mumların {{ D.5.ic.geri_0.5 }} kadarında fiyat
  sonraki 24 mum içinde mumun yarısına geri geldi. Fiyatın yönü rastgele olsaydı da {{ D.5.ic.ayna_geri_0.5 }}
  gelecekti: büyük mum çoğu zaman ucuna yakın kapanır ve yarısı kapanıştan kısa bir mesafededir. Farkın kendisi
  ({{ D.5.ic.geri_0.5_fark }} puan) küçük ama iki dönemde de aynı yönde.
- **Hangi yöne önce 1 ATR?** Kapanışın 1 ATR yukarısı ile 1 ATR aşağısı arasında önce mumun yönündeki seviyenin
  görülme payı: 5 dakikada {{ D.5.ic.sim_1.0 }}, 15 dakikada {{ D.15.ic.sim_1.0 }}, 1 saatte {{ D.60.ic.sim_1.0 }}. Yazı
  turada bu pay {{ Y.50 }} olurdu. 5 dakikada hafif bir dönüş eğilimi var; 1 saatlik pay yazı turadan ayırt edilemiyor.
- **Ortalama yol küçük.** 24 mum sonra fiyat mumun yönünde ortalama 5 dakikada {{ D.5.ic.net_24 }} ATR, 1 saatte
  {{ D.60.ic.net_24 }} ATR yol aldı. 5 dakikada bu {{ D.5.ic.net24_pip }} pip ediyor ve tipik makas tek başına bundan
  büyük. 1 saatte {{ D.60.ic.net24_pip }} pip ve makastan büyük, ama stoplu ve hedefli bir işlemde maliyetten önce
  işlem başına {{ G.60.ic.devam:piyasa:s2:h1.brut }} R'ye iniyor (8. ders).
- **Makas büyük mumun kapanışında açılmıyor.** Büyük mumun kapanış dakikasında makas, mumdan önceki bir saatin
  {{ D.5.ic.makas_mum_kat }} katıydı; iki katını aştığı mum {{ D.5.ic.makas_mum_iki }}. Mumun içinde açılan makas da
  sonucu taşımıyor: aşağıda.

## Bu dersi masada nasıl kullanırsın

Bu ders bir giriş kuralı vermez; büyük mum kapandığında soruların sırasını verir. İlk sorular mumun bu dersin olayı
olup olmadığını sorar: FX gününün devri, haftanın açılışı ve kümenin ikinci mumu ölçüye girmedi. Takvimdeki büyük
haberin mumu sayıların içinde ama küçük bir parçası (aşağıda); 7. ders onu ayrı ölçtü ve okuma çıkarmadı. Sonra dilim
sorulur ve cevabı bir "yapma" listesidir; şemanın hiçbir dalı "gir" demez.

{{# karar akis }}

## Büyük mum nasıl tanımlandı

**ATR** (ortalama gerçek aralık) bir mumun "olağan" boyunun ölçüsüdür. Her mumun **gerçek aralığı** yüksek ile düşüğün
farkıdır; mum bir önceki kapanıştan boşlukla açıldıysa o boşluk da aralığa eklenir. ATR({{ SB.atr_n }}) bu gerçek
aralıkların son {{ SB.atr_n }} mum üzerinden yumuşatılmış ortalamasıdır (Wilder ortalaması; TradingView'deki ATR
göstergesiyle aynı yumuşatma). Tek fark: önceki mum bitişik değilse (hafta sonu, tatil ya da eksik mum) boşluk sayılmaz.

Bir mum, aralığı (yüksek − düşük) **kendisinden önceki** mumun ATR'sinin en az {{ SB.esik }} katıysa büyük sayıldı. Ölçü
yalnız geçmişten kurulur: mum kapandığı anda büyük olup olmadığı bilinir, sonrasına bakılmaz. Her dilim kendi ATR'siyle
ölçüldü; 5 dakikalık mum 5 dakikalık ATR ile, 1 saatlik mum 1 saatlik ATR ile. Büyüklük dört kovaya ayrıldı: 2–3,
3–4, 4–5 ve 5 ATR ve üstü.

**Yön** mumun kapanış eksi açılışıdır. Gövdesi aralığının beşte birinden küçük mum (uzun fitilli, kararsız mum) yön
ölçülerine girmedi; 5 dakikada {{ SAY.5.kararsiz }} böyle mum vardı.

Dört tür mum dışarıda bırakıldı ve sayıldı:

- **Kümenin devamı.** Önceki {{ SB.kume_once }} mumdan biri de büyükse mum sayılmadı; yalnız kümenin **ilk** büyük mumu
  olaydır. Arka arkaya gelen üç büyük mum aynı haberin üç parçasıdır ve ayrı ayrı sayılırsa aynı olay üç kez
  ölçülürdü. 5 dakikalık grafikte {{ SAY.5.buyuk }} büyük mumdan {{ SAY.5.kume }} tanesi böyle çıktı.
- **Yeniden açılış.** Altı saatten uzun bir boşluktan (hafta sonu, tatil) sonraki ilk 60 dakika. O dakikalarda kotasyon
  seyrek ve geniştir; aralık fiyatın değil kotasyonun hareketidir ({{ SAY.5.yeniden_acilis }} mum).
- **Devir.** New York saatiyle 16:50–17:10 aralığına değen mum (TSİ, ABD yaz saatinde 23:50–00:10, kış saatinde
  00:50–01:10; 1 saatlik grafikte New York 16:00 ve 17:00 mumları). FX gününün devrinde makas sıçrar ve alış-satış
  ortasından ölçülen aralığı şişirir ({{ SAY.5.devir }} mum).
- **Eksik veri.** Mumun ya da sonraki 24 mumun dakikalarının beşte birinden fazlası kotasyonsuz ({{ SAY.5.eksik }} mum).
  İzleme penceresi saatle ölçüldüğü için cuma günü piyasa kapanışına yakın mumların penceresi hafta sonuna taşar ve bu
  kurala takılır. 1 saatlik grafikte etki büyük: pencere bir gün sürdüğü için perşembe akşamından sonraki mumlar ölçüye
  girmez. Bütün dönemde (2018 → {{ ON.dis_bitis }}) bu kurala takılan 1 saatlik {{ SAYT.60.eksik }} mumun
  {{ SAYT.60.eksik_cuma }} tanesi cuma mumuydu; ABD istihdam raporunun (cuma) 1 saatlik mumu hiçbir 1 saatlik ölçüde
  yok. 15 dakikada bu sayılar {{ SAYT.15.eksik }} ve {{ SAYT.15.eksik_cuma }}.

Takvimdeki büyük haberin mumu dışarıda bırakılmadı: 2018–2023'ün {{ D.5.ic.n }} 5 dakikalık olayından
{{ S.5.haber.haber.ic.n }} tanesi haber mumudur. 7. ders onu ayrı ölçer.

Her şey {{ pariteler }} paritelerinde ve alış ile satışın ortasından (orta fiyat) ölçüldü. 2018–2023'te yön ölçülerine
giren olay sayısı 5 dakikada {{ D.5.ic.n }}, 15 dakikada {{ D.15.ic.n }}, 1 saatte {{ D.60.ic.n }}.

{{# sekil 01_ornek "Üç dilimde birer büyük mum" }}

Şekildeki üç mumu sayıyla okumak tanımı somutlaştırır. 5 dakikalık mum ({{ O.5.gun }}, başlangıcı
TSİ {{ O.5.saat }}) {{ O.5.yon }} yönlüydü: aralığı {{ O.5.R_pip }} pip, kendisinden önceki 5 dakikalık ATR {{ O.5.A_pip }} pip,
oran {{ O.5.kat }}. Sonraki 24 mumda fiyat mumun yarısına {{ O.5.geri50 }}, mumun ucunu {{ O.5.uc }} ve 24 mumun
sonunda mumun yönünde {{ O.5.net24 }} ATR'deydi. 15 dakikalık mum ({{ O.15.gun }}, başlangıcı TSİ {{ O.15.saat }}, {{ O.15.yon }})
{{ O.15.R_pip }} pip, ATR {{ O.15.A_pip }} pip; sonrasında yarısına {{ O.15.geri50 }}, ucunu {{ O.15.uc }}, 24 mum sonra
{{ O.15.net24 }} ATR. 1 saatlik mum ({{ O.60.gun }}, başlangıcı TSİ {{ O.60.saat }}, {{ O.60.yon }}) {{ O.60.R_pip }} pip, ATR
{{ O.60.A_pip }} pip; sonrasında yarısına {{ O.60.geri50 }}, ucunu {{ O.60.uc }}, bir gün sonra {{ O.60.net24 }} ATR.

Üç örnek üç farklı hikâye anlatır ve bu dersin konusu tam olarak budur: tek bir büyük mumun ardından ne olacağı
grafikte hep "belliydi" gibi görünür. Ölçülmesi gereken, binlerce büyük mumun ortalamasıdır.

### Masada: büyük mumu ekranda tanımak

Bir mumun "büyük" olduğuna gözle karar vermek kolaydır ve yanıltıcıdır. Gözün kıyas noktası ekrandaki öbür mumlardır;
bu dersin kıyas noktası ise bir önceki mumun ATR'sidir. Masada tanıma üç adımdır. Önce aynı dilimde ATR göstergesini
açarsın ({{ SB.atr_n }} mum, Wilder yumuşatması) ve değeri büyük mumun **bir önceki** mumunda okursun: büyük mumun
kendi ATR değeri büyük mumu da içerir ve eşiği kendiliğinden yükseltir. Sonra mumun yüksek ile düşüğünün farkını o
değerle kıyaslarsın; en az iki katıysa mum bu dersin anlamında büyüktür. En sonda gövdeye bakarsın: gövde aralığın
beşte birinden kısaysa mumun yönü yoktur ve yön okuması yapılmaz.

{{# sema tanima }}

Devir penceresine ve hafta açılışının ilk saatine değen mum da dersin dışındadır.

## Ne ölçüldü

Büyük mum kapandıktan sonra fiyat 24 mum boyunca izlendi: 5 dakikalık grafikte iki saat, 15 dakikalıkta altı saat,
1 saatlikte bir gün. Birim, olayın ATR'sidir. Ölçüler:

- **±1 ATR'den hangisi önce.** Kapanışın bir ATR mumun yönünde ve bir ATR tersindeki iki seviye. Hangisi önce görüldü?
  Bu ölçü simetriktir: yön bilgisi olmayan bir fiyatta iki seviye eşit olasıdır ve beklenen pay {{ Y.50 }}. Aynı dakikada
  ikisi birden görülen ya da hiçbiri görülmeyen olay bu ölçüye girmedi.
- **Geri çekilme.** Fiyat mumun ucundan mumun boyunun {{ Y.25 }}, {{ Y.50 }} ve {{ Y.62 }} kadarı geri geldi mi; mumun öbür ucuna
  kadar döndü mü.
- **Mumun ucunu aştı mı.** Fiyat 24 mum içinde mumun kendi ucunun ötesine geçti mi.
- **Net hareket.** 6 ve 24 mum sonra fiyat, kapanıştan mumun yönünde kaç ATR yol aldı.

## Ayna: şansın vereceği pay

Bu dersin ana fikri şudur: büyük bir mumdan sonra "fiyat genelde yarısına döner" cümlesi doğrudur ve neredeyse hiçbir
şey söylemez. Sebep mumun şekli. Büyük mum çoğu zaman ucuna yakın kapanır; mumun yarısı kapanıştan, mumun boyunun
yarısından biraz az bir mesafededir ve fiyat her yöne biraz dalgalandığı için o mesafeyi yön bilgisi olmadan da sık
geçer.

Şansın payını ölçmek için önceki derslerdeki **ayna** kullanıldı. Her olayda mumdan sonraki gerçek yol, mumun kapanışına
göre ters çevrildi: kapanıştan on pip yukarı giden bir dakika, aynada on pip aşağı gider. Aynı ölçüler aynalanmış yolda
yeniden hesaplandı. Aynanın oynaklığı ve mum geometrisi gerçek yolla birebir aynıdır, yalnız yön tersine dönmüştür.
Yani **gerçek pay eksi ayna payı mumun yön bilgisidir**; ayna payının kendisi geometrinin kendiliğinden ürettiği
orandır.

{{# davranis }}

«+1 ATR önce» sütununda ayna yoktur, çünkü o ölçü simetriktir: aynası tam tersidir ve beklenen pay {{ Y.50 }}. Öbür
iki geri çekilme sütununda iki sayı yan yanadır: önce gerçek, sonra ayna. Son sütun 24 mum sonraki ortalama hareket ve
hafta düzeyinde yeniden örneklenmiş {{ Y.95 }} aralığıdır: aynı gün dört paritede büyük mum çıkabilir ve 1 saatlik
yol ertesi güne taşar; bunlar birbirinden bağımsız sayılmaz.

{{# sekil 02_yol "Büyük mumdan sonra ortalama yol" }}

### Masada: yarıya dönüş bir işaret değil

Ayna bölümünün masadaki karşılığı tek cümledir: fiyatın büyük mumun yarısına dönmesi, mumun "döndüğünü" söylemez.
Yarı kapanışa yakındır; fiyatın oraya uğraması için bir yön gerekmez, sıradan dalgalanma yeter.

{{# sema yari-geometri }}

Yarıya dönüş 5 dakikada {{ D.5.ic.geri_0.5 }}, yönsüz bir yolda {{ D.5.ic.ayna_geri_0.5 }}: gördüğün dönüşlerin
neredeyse hepsi, bir yön bilgisi olmasa da göreceğin dönüşlerdir.

{{# kart yari-dokunus }}

Yarıya dönen olayları sayıp tutulan bir defterin şansla tutturacağı oran zaten aynanın payıdır.

## Dilim dilim okuma

**5 dakika: hafif geri verme.** Fiyat ±1 ATR'den önce mumun tersindekini daha sık gördü ({{ D.5.ic.sim_1.0_ters }};
2024 → {{ D.5.dis.sim_1.0_ters }}). Mumun yarısına dönüş aynadan {{ D.5.ic.geri_0.5_fark }} puan sık
(2024 → {{ D.5.dis.geri_0.5_fark }} puan). 24 mum sonra ortalama {{ D.5.ic.net_24 }} ATR (2024 → {{ D.5.dis.net_24 }}).
Üç ölçü de aynı yöne bakıyor. ±1 ATR payı ve yarısına dönüş iki dönemde de aralığıyla tutuyor; 24 mum sonraki yolun
aralığı 2018–2023'te sıfırın altında ({{ D.5.ic.net_24_alt }} … {{ D.5.ic.net_24_ust }}), 2024 sonrasında sıfırı
kapsıyor ({{ D.5.dis.net_24_alt }} … {{ D.5.dis.net_24_ust }}). Ama büyüklüğe dikkat: 5 dakikalık bir ATR'nin medyanı
{{ D.5.ic.A_pip }} pip; 24 mumluk ortalama hareket {{ D.5.ic.net24_pip }} pip. Aynı paritelerde makasın medyanı
{{ D.5.ic.makas_once }} pip.

**15 dakika: zayıf bir geri verme.** Yarısına dönüş aynadan {{ D.15.ic.geri_fark1 }} puan sık (aralık
{{ D.15.ic.geri_fark_alt }} … {{ D.15.ic.geri_fark_ust }}); 2024 → {{ D.15.dis.geri_fark1 }} puan (aralık
{{ D.15.dis.geri_fark_alt }} … {{ D.15.dis.geri_fark_ust }}). ±1 ATR payı {{ D.15.ic.sim_1.0 }} (2024 →
{{ D.15.dis.sim_1.0 }}), 24 mum sonra {{ D.15.ic.net_24 }} ATR (2024 → {{ D.15.dis.net_24 }}). 24 mum sonraki yol iki
dönemde de sıfırdan ayırt edilemiyor; ±1 ATR payı 2018–2023'te yazı turadan ayırt edilemiyor, 2024 sonrasında
aralığın üst ucu {{ Y.50 }} sınırında ({{ D.15.dis.sim_alt }} … {{ D.15.dis.sim_ust }}). 15 dakikalık büyük mum, 5 dakikalığın geri verme eğilimi ile 1 saatliğin devam eğilimi
arasında, geri verme tarafına yakın duruyor.

**1 saat: hafif devam.** ±1 ATR'den önce mumun yönündeki {{ D.60.ic.sim_1.0 }} (2024 → {{ D.60.dis.sim_1.0 }}). Yarısına
dönüş aynadan seyrek değil, sık da değil ({{ D.60.ic.geri_0.5_fark }} puan). 24 mum (bir gün) sonra fiyat mumun yönünde
ortalama {{ D.60.ic.net_24 }} ATR ({{ Y.95 }} aralık {{ D.60.ic.net_24_alt }} … {{ D.60.ic.net_24_ust }}) ve 2024 → döneminde
{{ D.60.dis.net_24 }} ATR yol aldı (aralık {{ D.60.dis.net_24_alt }} … {{ D.60.dis.net_24_ust }}). 2018–2023'te aralık
sıfırın üstünde, 2024 sonrasında nokta tahmini aynı yönde ama aralık sıfırı kapsıyor; yön payı da iki dönemde yazı
turadan ayırt edilemiyor. İki dönemde de aralığıyla tutan ölçüler 5 dakikadaki geri verme ve 15 dakikadaki küçük
yarıya dönüş farkıdır.

{{# sekil 03_geri "Geri çekilme şanstan sık mı" }}

### Masada: 5 dakikada kovalamazsın

5 dakikalık büyük mumdan sonraki tek ölçülmüş eğilim hafif bir geri vermedir ve büyüklüğü makastan küçüktür. Kapanışta
mumun yönünde piyasa emriyle giren işlemci ortalama olarak geri vermenin içine girer ve üstüne makası öder (8. ders, 5
dakika). Mumun tersine kapanışta giren işlemci geri vermeyi maliyetten önce yakalar, ama maliyetten sonra eksidedir.
Geri verme bir işlem değil, bir uyarıdır: mumun yönünde gireceksen kapanıştan girmezsin.

Hangi 5 dakikalık mumda bu uyarı daha güçlü? 7. ders iki yer buldu ve ikisi de iki dönemde aynı yöne bakıyor:
kapanışı ucuna yakın mum ve Asya seansındaki mum (Asya: New York 17:00 ile Londra 07:00 arası; TSİ iki ülke de yaz
saatindeyken 00:00–09:00, ikisi de kış saatindeyken 01:00–10:00). Londra seansında (Londra 07:00 ile New York 08:00 arası; TSİ iki ülke de yaz saatindeyken
09:00–15:00, ikisi de kış saatindeyken 10:00–16:00) aynı eğilim yarı yarıya küçük (7. ders, 5 dakika).

{{# sema kovalama }}

{{# kart bes-dk-uc }}

Gerçek grafiklerde numaralar sabittir: ① olay mumu, ② mumun yarısı, ③ fiyatın yarıya ilk dokunduğu an, ④ izleme
penceresinin sonu. Şemalarda ise numaralar şemanın altındaki maddelere bağlıdır.

{{# ornek uc-kapanis }}

İki gün de EUR/USD'de, Londra seansında, takvimde haber yokken gelen aşağı yönlü 5 dakikalık büyük mumdur; ikisi de
uzun gövdeli ve dibine yakın kapanır. Üstteki günde (24 Kasım 2023, mum TSİ 15:40'ta başlar) fiyat önce mumun yönünde
bir buçuk mum boyundan fazla daha iner (TSİ 16:30), sonra döner: yarıya ancak kapanıştan bir saat sonra, TSİ 16:47'de
dokunur (③), TSİ 17:15'te mumun tepesini kırar ve ④'te (TSİ 17:45) tepenin de üstündedir. Alttaki günde (13 Kasım
2023, mum TSİ 15:00'te başlar) fiyat yarıya hiç dönmez, ③ yoktur; kapanıştan sonraki ikinci mumda mumun dibini kırar ve
④'te (TSİ 17:05) dibin belirgin altındadır. Tek bir çift gün kuralı ne doğrular ne yanlışlar. İki günde de kapanışta
mumun yönünde giren işlem (stop 2 ATR, hedef 1 R) hedefini ilk saat içinde görürdü; üstteki günde yarıya konan limit
altı mumluk bekleme süresinde dolmazdı. Kovalamama kuralının dayanağı bu iki günün sonucu değil, binlerce olayın
ortalaması ve kapanışta ödenen makastır; ortalamanın içinde kovalayanın kazandığı günler de vardır.

### Masada: 15 dakikada okuma zayıf

15 dakikalık büyük mumda iki dönemde tutan tek şey yarıya dönüşün aynadan biraz sık olmasıdır; ne kovalama ne tersine
giriş gerekçesi taşır. Mumu bağlam olarak not edersin (7. ders, 15 dakika).

### Masada: 1 saatte tersine girmezsin

1 saatlik büyük mumda ortalama yol bir gün boyunca mumun yönündedir: 2018–2023'te aralığıyla, 2024 sonrasında yalnız
nokta tahmini olarak. Bu küçük devamın masadaki en önemli sonucu bir giriş değil, bir yasaktır: mumun tersine giren
işlemci bu yolun karşısında durur. 8. ders bunu giriş biçimleriyle ölçtü: stop 2 ATR, hedef 1 R satırında 1 saatte
tersine giriş biçimleri 2018–2023'te maliyetten önce de eksiydi, 2024 sonrasında maliyetten önce sıfırın çevresinde
kaldı, maliyetten sonra iki dönemde de eksi (8. ders, 15 dakika ve 1 saat).

Mumun yönündeki devam ise bir işlem çıkarmıyor: stoplu ve hedefli bir işlemde maliyetten önce işlem başına
{{ G.60.ic.devam:piyasa:s2:h1.brut }} R. Kapanışı yarısının gerisinde kalan fitilli 1 saatlik mumda ve günlük trend
yatayken mumun yönü korunmuyor (7. ders, 1 saat); bu iki hâl tersine girmenin gerekçesi değildir, yalnız mumun yönünün
bağlam olarak okunmadığı yerlerdir.

{{# sema bir-saat }}

{{# kart bir-saat-uc }}

{{# ornek saat-uc }}

İki gün de GBP/USD'de, takvimde haber yokken dibine yakın kapanan aşağı yönlü 1 saatlik büyük mumdur. Üstteki günde
(24 Ekim 2023, mum TSİ 10:00–11:00, Londra seansı) fiyat ilk saatte mumun dibini kırar, yarıya hiç dönmez (③ yok) ve
ertesi güne kadar inmeye devam eder; ④'te (25 Ekim, TSİ 11:00) kapanışın yaklaşık dört mum boyu altındadır. Alttaki
günde (22 Kasım 2023, mum TSİ 16:00–17:00, Londra–New York örtüşmesi) fiyat da önce mumun yönünde gider ve sonraki iki
saatte dibin bir buçuk mum boyundan fazla altına iner; sonra gece boyunca toparlanır, yarıya ancak ertesi gün TSİ
11:30'da döner (③), hemen ardından mumun tepesini de kırar ve ④'te (23 Kasım, TSİ 17:00) mumun içinde, yarının
üstündedir. Alttaki gün geriye bakınca "tersine girmeliydim" dedirtir; oysa kapanışta tersine giren, 1 ATR'lik de
2 ATR'lik de stopunu ilk saatte görürdü. Tersine girmeme kuralı tam dönüşün olmayacağını söylemez; ortalama yolun
tersine girişin aleyhine olduğunu söyler.

## Yarısına dönen fiyat ne kadar sürede dönüyor

Yarısına dönüşün medyan süresi: 5 dakikalık grafikte {{ D.5.ic.geri_dk }} dakika, 15 dakikalıkta
{{ D.15.ic.geri_dk }} dakika, 1 saatlikte {{ D.60.ic.geri_dk }} dakika. Yani yarısına dönenlerin yarısında dönüş ilk
bir iki mum içinde gelir. Bu, 8. dersteki limit emirlerin neden çoğu zaman dolduğunu açıklar; dolmanın neden iyi haber olmadığını 8. ders
gösterir.

Büyük mumların 5 dakikada {{ D.5.ic.geri_50_uc }} kadarında (ayna {{ D.5.ic.ayna_geri_50_uc }}) fiyat önce yarısına
dönüp sonra yeniden mumun ucuna gitti; yarısına dönenler içinde bu pay {{ D.5.ic.geri_50_uc_kosul }} (ayna
{{ D.5.ic.ayna_geri_50_uc_kosul }}). 1 saatte {{ D.60.ic.geri_50_uc }} (ayna {{ D.60.ic.ayna_geri_50_uc }}), yarısına
dönenler içinde {{ D.60.ic.geri_50_uc_kosul }} (ayna {{ D.60.ic.ayna_geri_50_uc_kosul }}). Geri çekilip yeniden uca gitmek
("geri çekilmede katıl" okuması) şansla beklenen kadar sık.

### Masada: geri çekilmeyi ne kadar beklersin

Ölçülen limit ve stop emirleri büyük mum kapandıktan sonra {{ SB.bekle }} mum bekledi, dolmazsa çekildi (8. ders, On
bir giriş biçimi). Süre bitince emri çekersin; dolmayan limiti fiyatın peşinden kaydırmak kovalamanın yavaş hâlidir.
Dolum iyi haber değildir: limitin dolduğu olaylarda aynı anda piyasadan girilen işlem çoğunlukla kaybederdi ve bunun
büyük kısmı geometridir, çünkü limit fiyat mumun hareketini geri aldığında dolar (8. ders, Limit neden ucuz görünür:
ters seçim).

{{# sema bekleme }}

{{# kart yari-bekleme }}

## Büyüklük değişince

Mum büyüdükçe davranışın değiştiği sık söylenir: "5 ATR'lik mum artık aşırıdır, döner". Kovalar:

{{# kova }}

Kovalar büyüdükçe olay sayısı hızla düşer: 5 dakikada 2–3 ATR'lik mumlar olayların {{ D.5.ic.kova_2-3_pay }} kadarı, 5
ATR ve üstü {{ D.5.ic.kova_5+_pay }}. Küçük kovalarda tek tek sayılar oynak; iki dönemde aynı yöne bakan bir büyüklük
etkisi yok. 5 ATR'lik bir mumun 2 ATR'lik bir mumdan daha güvenilir bir dönüş işareti olduğunu bu veri göstermiyor.

### Masada: büyüklük okumayı değiştirmez

Kovalar iki dönemde aynı yöne bakmıyor (5 dakikalık 4–5 ATR'lik mum 2018–2023'te belirgin geri verdi, 2024 sonrasında
vermedi; 7. ders, 5 dakika); 5 ATR'lik mumu 2 ATR'likten farklı okumazsın. Stop girişten 2 ATR uzakta kaldığı için
mumun boyu stopu da değiştirmez; stopu mumun öbür ucuna koymak ve pozisyon büyüklüğü bu seride ölçülmedi.

{{# kart cok-buyuk }}

## Makas büyük mumda açılıyor mu

Büyük mum anında işlem yapmanın makas yüzünden pahalı olduğu sık söylenir. Ölçüldü: mumun kapanış
dakikasındaki makas mumdan önceki 60 dakikanın medyan makasıyla, sonraki dakikaların açılışındaki makas da aynı tabanla
kıyaslandı.

{{# makas }}

Büyük mumların çoğunda kapanış dakikasında makas açılmıyor; iki katını aşan mumlar azınlıkta.

Makasın mumun **içinde** açılması ayrı bir sorudur. Orta fiyatın yükseği, alış ve satış yükseklerinin ortalamasıdır;
mum içinde makas bir an açılırsa orta fiyatın aralığı şişer ve mum, fiyat o kadar gitmediği hâlde "büyük" görünür.
5 dakikalık büyük mumların içinde makasın en geniş anı, mumdan önceki saatin medyan makasının medyanda
{{ TEK.5.ic.makas_ici_kat }} katıydı. Sınamak için yalnız alış ve yalnız satış fiyatıyla ölçülen iki aralığın küçüğü de
2 ATR'yi geçen mumlar ayrıca ölçüldü; 5 dakikada olayların {{ TEK.5.ic.pay }} kadarı (2024 → {{ TEK.5.dis.pay }}). O
mumlarda yarısına dönüş aynadan {{ TEK.5.ic.tum.geri_fark }} puan sık (aralık {{ TEK.5.ic.tum.geri_fark_alt }} …
{{ TEK.5.ic.tum.geri_fark_ust }}; 2024 → {{ TEK.5.dis.tum.geri_fark }} puan) ve 24 mum sonra ortalama
{{ TEK.5.ic.tum.net }} ATR (2024 → {{ TEK.5.dis.tum.net }}): geri verme makasın yarattığı bir görüntü değil.

Yani büyük mumdan sonra girişin pahalı olmasının sebebi makasın açılması değil, hareketin kendisinin küçük olması:
5 dakikada ortalama geri verme makastan küçük, 1 saatte ortalama devam makastan büyük ama stop ve hedefle kurulan bir
işlemde makas ve kaymayı karşılamıyor.

### Masada: makas penceresi

Sıradan büyük mumun kapanışında makas açılmıyor; "makas kapansın diye beklerim" bir gerekçe değildir, girişi pahalı
yapan hareketin küçüklüğüdür. FX gününün devri ve hafta açılışı bu dersin dışındadır. Takvimdeki büyük haberin
penceresinde piyasa ve stop emirlerine ek kayma varsayıldı; haberdeki makas bu seride ölçülmedi (8. ders, Ölçülmeyenler).

{{# kart makas-devir }}

## Emri nereye koyarsın

Bu bölüm, büyük mumdan bağımsız bir gerekçeyle (başka bir seviye, başka bir okuma, bir pozisyonun riskini kapatma
ihtiyacı) işleme girecek olan içindir. Büyük mum o gerekçeyi güçlendirmez; yalnız emrin nereye ve nasıl konacağını
değiştirir. Dört giriş biçiminin masadaki anlamı 8. dersin ölçümünden gelir.

- **Piyasa emri, kapanışta.** Makası ve kaymayı girişte öder; 5 dakikada maliyetin en büyük olduğu biçimlerden biridir
  (8. ders, 5 dakika). Mumun yönünde kapanışta piyasa emri 5 dakikada geri vermenin içine girer. Başka bir gerekçen
  zamanı dayatıyorsa bu biçim kalır; onu hız için seçersin, fiyat için değil.
- **Limit, mumun yarısına ya da çeyrek geri çekilmesine.** Girişte makas ve kayma ödemez, çıkışta öder. Maliyeti en
  az olan biçimdir ama en çok bilgi kullanan biçim değildir: fiyat sana geldiğinde dolar, yani tam da hareketin geri
  alındığı olaylarda (8. ders, Limit neden ucuz görünür: ters seçim). Altı mumluk pencereyle sınırlarsın.
- **Stop emri, mumun ucunun kırılmasına.** Fiyat yeni bir uç yaparsa girer; kaymayı öder ve fiyatın zaten yürüdüğü
  yerden alır. 5 dakikada maliyetten sonra eksi (8. ders, Ucun kırılması). Dakika verisinde stop emrinin dolduğu
  dakikanın içi görünmez ve bu biçimin sonucu o yüzden ayrıca bir varsayım taşır (8. ders, Ölçülmeyenler).
- **Onay mumundan sonra piyasa.** Sonraki mumun, büyük mumun kapanışının ötesinde kapanmasını beklersin. Onay gelmezse
  işlem yoktur; gelirse giriş daha kötü bir fiyattan yapılır ve onayın taşıdığı bilgi kaçırılan fiyatın bedelini ancak
  karşılar (8. ders, Onay mumu). 1 saatte 2018–2023'te en az kaybeden biçim oldu; 2024 sonrasında bu sıra korunmadı.

**Stop.** Stopu büyük mumun öbür ucunun ötesine koyarsın; mumun boyu riskin ölçüsüdür. Stopu mumun içine, yarının
hemen arkasına çekmek 8. dersin ölçtüğü tuzaktır: 5 dakikada stop 1 ATR'deyken maliyet R cinsinden 2 ATR'dekinden
belirgin büyük, ve olayların önemli bir kısmında risk o kadar küçük kalıyor ki işlem hiç açılamıyor (8. ders, Stop
uzaklığı ve maliyet).

**Hedef.** Hedef riskin katı olarak yazılır. 8. dersin ızgarası 1 ve 2 R'lik hedefleri ölçtü. Maliyetten sonra sıfırın
üstüne çıkan tek yer 1 saatte, hedefi 2 R olan geri çekilme limitleriydi ve büyüklükleri sıfırdan ayırt edilemeyecek
kadar küçüktü (8. ders, 15 dakika ve 1 saat). Hedefi 2 R olan çeyrek geri çekilme limiti süzgeçli bir hâliyle 9.
dersin planına seçildi ve 2024 sonrasında tutmadı (9. ders, Seçilen girişler). Hedefi uzaklaştırmak bir kenar yaratmaz, yalnız kazanma oranını düşürür.

**Emri ne zaman çekersin.** Limit ya da stop emri altı mumda dolmadıysa çekersin; bu serinin ölçtüğü emir ömrü budur.
Takvimdeki büyük bir haber pencerenin içine düşüyorsa emri haberden önce çekmek akla yatkındır, çünkü haber mumunda
okuma yok (7. ders, Fade mi, devam mı: okuma tablosu); ama emrin haberden önce çekilmesinin etkisi bu derste ölçülmedi.

**Haber penceresinde ne değişir.** Piyasa ve stop emirleri daha çok kayar; limit kendi fiyatından dolar, ama aynı
pencerede çıkış (stop ya da süre dolunca) yine kayar (8. ders, girişteki maliyet varsayımı). Haberin kendi mumu bu
dersin olayı değildir.

## Sık yapılan hatalar

1. **"Yarısına döndü, demek ki tersine haklıydım."** Yarıya dönüşün çoğu mumun şeklinden gelir; yönü olmayan bir yol
   da yarıya neredeyse aynı sıklıkta uğrardı. Dayanak: 6. ders, Ayna: şansın vereceği pay.
2. **5 dakikalık büyük mumu kapanışta mumun yönünde kovalamak.** Ortalama yol 5 dakikada mumun tersinedir ve giriş
   makası öder; kapanışta piyasa girişinin maliyeti 5 dakikada en büyüklerden biridir. Dayanak: 6. ders, Dilim dilim
   okuma; 8. ders, 5 dakika.
3. **1 saatlik büyük mumu "fazla gitti" diye tersine işlemek.** 1 saatte ortalama yol mumun yönündedir ve tersine giriş
   biçimlerinin hepsi maliyetten önce de eksidir. Dayanak: 6. ders, Dilim dilim okuma; 8. ders, 15 dakika ve 1 saat.
4. **5 ATR'lik mumu 2 ATR'likten güvenilir bir dönüş işareti saymak.** Büyüklük kovaları iki dönemde aynı yöne
   bakmıyor. Dayanak: 6. ders, Büyüklük değişince.
5. **Limitin dolmasını iyi haber saymak.** Limit, piyasa girişinin kaybettiği olaylarda dolar; dolum, zayıflamış bir
   hareketle birlikte gelir. Dayanak: 8. ders, Limit neden ucuz görünür: ters seçim.
6. **Stopu mumun içine çekip riski "küçültmek".** Makas ve kayma pip cinsinden sabittir; stop yaklaştıkça aynı maliyet
   daha büyük bir R olur. Dayanak: 8. ders, Stop uzaklığı ve maliyet.
7. **Devir mumunu, hafta açılışını ya da haber mumunu sıradan bir büyük mum gibi okumak.** Devirde ve açılışta aralık
   kotasyonun hareketidir; haber mumunda okuma yok. Dayanak: 6. ders, Büyük mum nasıl tanımlandı; 7. ders, Fade mi,
   devam mı: okuma tablosu.
8. **"Onayı bekledim, artık güvenli."** Onay beklemek olayların bir kısmında hiç işlem açmamak, gelen onayda da daha
   kötü bir fiyattan girmek demektir; maliyetten önceki sonuç kapanışta girişten belirgin farklı değil. Dayanak: 8.
   ders, Onay mumu.

## Masa kontrol listesi

Büyük bir mum kapandığında sırayla:

1. **Saat kaç?** Mum FX gününün devrine (New York 16:50–17:10; TSİ ABD yaz saatinde 23:50–00:10, kış saatinde
   00:50–01:10) ya da haftanın açılışından sonraki ilk saate (pazar akşamı New York 17:00 civarı; TSİ ABD yaz saatinde
   pazartesi 00:00, kış saatinde 01:00) değiyorsa bu dersin olayı değil.
2. **Takvimde büyük haber var mı?** ABD istihdam ve enflasyon verisi New York 08:30 (TSİ ABD yaz saatinde 15:30, kış
   saatinde 16:30), Fed kararı New York 14:00 (TSİ ABD yaz saatinde 21:00, kış saatinde 22:00), ECB kararı Frankfurt
   14:15 (TSİ Avrupa yaz saatinde 15:15, kış saatinde 16:15), BoE kararı Londra 12:00 (TSİ İngiltere yaz saatinde
   14:00, kış saatinde 15:00). Mum o haberin mumuysa okuma yok.
3. **Mum gerçekten büyük mü?** Aralığı, bir önceki mumun ATR değerinin en az iki katı mı?
4. **Önceki üç mumda başka büyük mum var mı?** Varsa kümenin devamıdır, yeni bir olay değil.
5. **Gövde aralığın beşte birinden büyük mü?** Değilse mumun yönü yok.
6. **Dilim hangisi?** 5 dakikada kovalamazsın, 1 saatte tersine girmezsin, 15 dakikada ikisi de belirgin değil.
7. **Kapanış mumun neresinde, seans hangisi?** Ucunda kapanan 5 dakikalık mumda ve Asya seansında (Londra 07:00'den
   önce; TSİ İngiltere yaz saatinde 09:00'dan, kış saatinde 10:00'dan önce) geri verme en belirgin; 1 saatlik fitilli
   mumda mumun yönü korunmuyor.
8. **Başka bir gerekçen var mı?** Yoksa masadan kalkarsın; büyük mum tek başına bir giriş değil.
9. **Varsa emir yazılı mı?** Emir biçimi, stop (mumun öbür ucunun ötesinde), hedef (riskin katı olarak) ve emrin altı
   mumluk penceresi.
10. **Masadan ne zaman kalkacaksın?** Pencere bittiğinde, emir dolmadan; ya da takvimdeki büyük bir haber pencereye
    düşmeden önce.

## Grafik okuma alıştırmaları

**1.** 5 dakikalık EUR/USD grafiği, saat Londra 03:40 (TSİ İngiltere yaz saatinde 05:40, kış saatinde 06:40), takvimde
haber yok. {{# atif sema kovalama }}'teki gibi, ucunda kapanan yukarı yönlü bir büyük mum; aralığı önceki mumun ATR'sinin üç katı. Kısa
vadeli bir alış gerekçen zaten var. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Mum Asya seansında ve ucunda kapandı: 5 dakikadaki geri vermenin en belirgin olduğu iki koşul bir arada (7. ders, 5
dakika). Kapanışta piyasa emriyle kovalamazsın. Alış gerekçen büyük mumdan bağımsızsa emri mumun yarısına limit olarak
koyarsın, stopu mumun alt ucunun ötesine, altı mumluk pencereyle; limit dolarsa mumun yönündeki okumanın zayıfladığını
bilirsin (8. ders, Limit neden ucuz görünür: ters seçim). Mumun tersine de "Asya'da geri verir" diye girmezsin: geri
vermenin büyüklüğü makastan küçük (6. ders, Dilim dilim okuma).

</details>

**2.** 1 saatlik GBP/USD grafiği, Londra 09:00'da başlayan bir mum (TSİ İngiltere yaz saatinde 11:00, kış saatinde
12:00), takvimde haber yok, ucunda kapandı, aralığı ATR'nin dört katı. {{# atif sema bir-saat }}'daki gibi grafik "uzamış" görünüyor ve
tersine bir işlem düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Tersine girmezsin: 1 saatte ortalama yol mumun yönündedir ve tersine giriş biçimlerinin hepsi maliyetten önce de eksi
(6. ders, Dilim dilim okuma; 8. ders, 15 dakika ve 1 saat). Mumun dört ATR olması bunu değiştirmez (6. ders, Büyüklük
değişince). Mumun yönünde de büyük mum tek başına bir işlem değildir. 7. ders Londra seansında başlayan 1 saatlik
büyük mumun iki dönemde de mumun yönünde gittiğini buldu, ama aralık yalnız bir dönemde sıfırın üstünde (7. ders, 1
saat); bu bir bağlamdır, giriş değil.

</details>

**3.** 15 dakikalık EUR/USD grafiğinde ABD enflasyon verisinin mumu (New York 08:30; TSİ ABD yaz saatinde 15:30, kış
saatinde 16:30) aşağı yönlü ve ucunda kapandı; aralığı ATR'nin altı katı. Masadaki biri "bu kadar büyük haber mumu
döner" diyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Haber mumunda okuma yok: olay az ve 24 mum sonraki yolun aralığı sıfırın iki yanına geniş açılıyor (7. ders, Fade mi,
devam mı: okuma tablosu). 9. dersin seçim kuralı 5 dakikada ve 1 saatte tam da haber mumunu ucundan tersine işleyen
adayları seçti ve ikisi de 2024 sonrasında tutmadı (9. ders, Seçilen girişler). Tersine girmezsin; mumun altı ATR
olması bunu değiştirmez.

</details>

**4.** 5 dakikalık grafikte yarıya koyduğun limit üçüncü mumda doldu ({{# atif sema bekleme }}'deki ② gibi); fiyat sonra yarıdan dönüp
mumun ucuna doğru gidiyor ve pozisyonu büyütmeyi düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Yarıya dönüp yeniden uca gitmek şansla beklenen kadar sık; bir "geri çekilmede katıl" onayı değil (6. ders, Yarısına
dönen fiyat ne kadar sürede dönüyor). Limitin dolması da iyi haber değildi (8. ders, Limit neden ucuz görünür: ters
seçim). Pozisyonu büyütmezsin; baştaki stop ve hedef geçerli kalır. Bu serinin ölçtüğü girişlerde ekleme yoktu;
eklemenin sonucu bu derste ölçülmedi.

</details>

## Bu sonuç nasıl okunmalı

Büyük mum bir **bilgi** taşıyor, ama çok az. 5 dakikada bir parça geri verme, 1 saatte bir parça devam. 5 dakikadaki
iki dönemde de aralığıyla tutuyor; 1 saatteki 2018–2023'te aralığıyla, 2024 sonrasında yalnız nokta tahminiyle aynı
yönde. İkisi de bir işlemin maliyetini karşılamadığı için tek başına işlem değil (8. ders). Büyük
mumdan sonra yarısına dönüşü bekleyen bir işlemci haklı çıkar, ama aynı haklılık yönü bilmeyen birine de düşerdi.
Ayna bunu ölçer.

Sonraki ders bu küçük bilginin nerede yoğunlaştığına bakar: hangi seansta, hangi kapanışta, hangi trendde mumun
tersine girmek (fade) daha haklı, hangisinde mumun yönü.

Seride üç sözcük tek anlamda kullanılır. **Geri çekilme**, fiyatın mumun ucundan mumun boyunun belli bir oranı kadar
geri gelmesidir (bir ölçü). **Geri verme**, ortalama yolun mumun tersine olmasıdır (bir eğilim). **Fade**, mumun tersine
işleme girmektir (bir karar).

## Ölçülmeyenler

- **Gerçek işlem hacmi.** Dukascopy hacmi bir likidite vekilidir, piyasanın tamamının hacmi değil.
- **Dört majör dışı pariteler, hisse, emtia.** Ölçüm yalnız {{ pariteler }} için.
- **Mumun içi.** Büyük mumun dakikalarının sırası (önce yükselip mi düştü) ölçüye girmedi; yalnız açılış, kapanış ve uçlar.
- **Haberin içeriği.** Takvimdeki büyük haberler (ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararları) yalnız
  "var/yok" olarak işaretlendi; beklentiye göre sürpriz ölçülmedi.
