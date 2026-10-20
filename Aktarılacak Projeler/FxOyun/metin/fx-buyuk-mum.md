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
turadan ayırt edilemiyor. İki dönemde de aralığıyla tutan ölçü 5 dakikadaki geri vermedir.

{{# sekil 03_geri "Geri çekilme şanstan sık mı" }}

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

## Büyüklük değişince

Mum büyüdükçe davranışın değiştiği sık söylenir: "5 ATR'lik mum artık aşırıdır, döner". Kovalar:

{{# kova }}

Kovalar büyüdükçe olay sayısı hızla düşer: 5 dakikada 2–3 ATR'lik mumlar olayların {{ D.5.ic.kova_2-3_pay }} kadarı, 5
ATR ve üstü {{ D.5.ic.kova_5+_pay }}. Küçük kovalarda tek tek sayılar oynak; iki dönemde aynı yöne bakan bir büyüklük
etkisi yok. 5 ATR'lik bir mumun 2 ATR'lik bir mumdan daha güvenilir bir dönüş işareti olduğunu bu veri göstermiyor.

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
