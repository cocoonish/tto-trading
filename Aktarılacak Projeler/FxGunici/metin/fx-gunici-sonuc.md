---
title: 'FX Gün İçi Stratejiler 1: Hangisi İşe Yarıyor? — {{ O.basarisiz.kapsam.kural | n }} Kuralın Sonucu'
description: "Gün içi FX işlem kitaplarının en çok anılan {{ O.basarisiz.kapsam.kural | n }} kuralı dört majör paritede, gerçek alış-satış fiyatlarıyla ve maliyet düşülerek sınandı. Hangi kural ne kadar kazandırdı, kazanma oranı ne oldu, kâra geçmek için ne gerekiyordu — tek tabloda."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "{{ O.basarisiz.kapsam.kural | n }} gün içi kuralın hiçbiri maliyetten sonra güvenilir biçimde kazandırmıyor. Kuralların yön ve zaman tahmini maliyetten önce sıfıra yakın; ödenen makas ve kayma sonucu eksiye çeviriyor. Ders sonucu tek tabloda, kazanma oranı ve kâra geçmek için gereken kazanma oranıyla veriyor."
seviye: 'giris'
---

Bu seri tek bir soruya cevap verir: gün içi FX işlemlerinde sık önerilen kurallar, gerçek maliyetle uygulandığında para
kazandırıyor mu? Kısa cevap: **hayır.** Sınanan {{ O.basarisiz.kapsam.kural | n }} kuralın hiçbiri, dört paritenin
hiçbirinde, maliyetten sonra güvenilir bir kazanç göstermedi. Bu ders sonucu sade bir tabloyla verir. İkinci ders her kuralın
nasıl uygulandığını grafik üstünde adım adım gösterir (hangi saatte ne olursa ne yapılır). Sonraki üç ders kuralları
tek tek sonuçlarıyla anlatır (kırılım, dönüş, akış ve haber): backtest ne verdi, stop ve hedef nerede olsaydı ne
değişirdi. Altıncı ders stop ve hedefin genel aritmetiğini, yedincisi bir kuralı kendiniz denemeden önceki kontrol
listesini verir.

## Ne sınandı

- **Kurallar.** Gün içi işlem kitaplarında en çok geçen {{ O.basarisiz.kapsam.kural | n }} kural: açılış aralığı ve
  Asya aralığı kırılımları, önceki günün tepe ve dibi, pivot seviyeleri, sahte kırılımdan dönüş, VWAP'a dönüş, Londra
  fiksingi çevresindeki işlemler, gün içi momentum ve beş haber kuralı.
- **Piyasa.** {{ K.ciftler | pariteler }}; bir dakikalık gerçek alış ve satış fiyatları,
  {{ K.baslangic | tarih }} – {{ K.bitis | tarih }}.
- **Maliyet.** Her işlem gerçek alış-satış farkını (makas) öder; ayrıca her dolumda {{ K.temel_kayma_pip | s1 }} pip
  kayma, haber anında ek {{ K.haber_kayma_pip | s1 }} pip.
- **Dürüstlük kuralı.** Kuralların varsayılan ayarları ve "işe yarıyor" demenin şartı, sonuçlar görülmeden yazıldı;
  uygulamada sonradan değişen birkaç ayrıntının etkisi ayrıca ölçüldü ve varsayılan ayarların hiçbirinin hükmünü
  değiştirmedi. Hüküm 2024 → döneminden
  verilir; ayarlar o dönemin verisine bakılarak seçilmedi.

## Sonuç

Varsayılan ayarlarıyla {{ O.basarisiz.kapsam.bilesim | n }} kural–parite bileşiminin 2024 → dönemindeki hükmü:
{{ T.hukum_say.oos.calisiyor | n }} çalışıyor, {{ T.hukum_say.oos.zayif | n }} zayıf,
{{ T.hukum_say.oos.calismiyor | n }} çalışmıyor{{? T.hukum_say.oos.calisiyor == 0 }}. Bütün dönemde de sonuç aynı
yönde: {{ T.hukum_say.tum.calisiyor | n }} çalışıyor, {{ T.hukum_say.tum.zayif | n }} zayıf,
{{ T.hukum_say.tum.calismiyor | n }} çalışmıyor{{? T.hukum_say.tum.calisiyor == 0 }}.

Hükmün üç kademesi şöyle okunur. **Çalışıyor:** maliyetten sonra işlem başına ortalama sonuç artı, %95 güven
aralığının alt ucu sıfırın üstünde ve sonuç rastgele yönde açılan işlemlerin en az yüzde 95'inden iyi. **Zayıf:**
ortalama artı ama bu üç şarttan biri tutmuyor — yani artı sonuç şanstan ayrılamıyor. **Çalışmıyor:** ortalama sıfır ya
da eksi.

Aşağıdaki tablo her kuralı dört paritenin işlemleri birlikte gösterir. Okuması kolay iki sayı var: **kazanma oranı**
(kârla kapanan işlemlerin payı) ve **gereken kazanma oranı** (kuralın kazancı ve kaybının boyuna göre kâra geçmek
için gereken pay). Kazanma oranı gerekenin altındaysa kural para kaybettirir; ne kadar altındaysa o kadar çok.

{{! kisa_kural_tablo }}

{{! sekil kisa-kurallar "Kazanma oranı ve kâra geçmek için gereken oran" }}

Tablodaki "R", işlemin riskidir: girişle stop arasındaki uzaklık. İşlem başına {{= "−0,10" }} R, her işlemde riske edilen
tutarın onda birini kaybetmek demektir: riski bin dolar olan işlemlerde işlem başına ortalama yüz dolar.

## Neden kaybediyorlar

Sebep tek cümleye sığar: **kurallar fiyatın yönünü ve zamanını şanstan iyi tahmin etmiyor, ama her işlemde maliyet
ödüyor.**

- **Maliyetten önce sıfıra yakın.** Makas ve kayma düşülmeden işlem başına ortalama sonuç
  {{ O.basarisiz.ayrisim.oos.ort.brut | r3 }} R. Bu, yazı tura atan bir kuraldan ayırt edilemez.
- **Maliyet her işlemde.** Bir işlemin ortalama maliyeti {{ O.basarisiz.ayrisim.oos.ort.c | s2 }} R: yaklaşık
  {{ O.basarisiz.ayrisim.oos.ort.c_makas_pip | s1 }} pip makas ve {{ O.basarisiz.ayrisim.oos.ort.c_kayma_pip | s1 }}
  pip kayma. Sıfıra yakın bir kazançtan bu düşülünce sonuç eksiye döner.
- **Dar stop maliyeti büyütür.** İşlemlerin medyan stop uzaklığı {{ O.basarisiz.basabas.maliyet_pip.R_medyan | s1 }}
  pip, medyan maliyet {{ O.basarisiz.basabas.maliyet_pip.medyan | s1 }} pip. Stop daraldıkça aynı pip maliyeti riskin
  daha büyük bir parçası olur. İkinci ders bunu sayılarla gösteriyor.

Kurallar "yanlış" değil; tutturdukları yön ve zaman, ödenen maliyeti karşılamaya yetmiyor. Bir kural ancak maliyetten
büyük ve tekrar eden bir avantaj taşıyorsa kazandırır. Bu serideki kuralların hiçbirinde böyle bir avantaj ölçülmedi.

## Dikkat çeken bir alt küme: ay sonu fiksingi

Tabloda görünmeyen ama en çok dikkat çeken yer, Londra fiksingi momentumunun **yalnız ay sonu günlerindeki**
işlemleri. Kural, fiksingden
önceki beş dakikanın yönünde girer: Londra 15:50–15:55 mumuna bakar ({{! tsi "" "Londra 15:50–15:55" }}), 15:55'te
girer ({{! tsi "" "Londra 15:55" }}) ve tam fiksingde, Londra 16:00'da çıkar ({{! tsi "" "Londra 16:00" }}).

GBP/USD'de ay sonu işlemleri iki dönemde de artıda: 2018–2023'te {{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.n | n }}
işlemde işlem başına {{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.net | r }} R, 2024 →'de
{{ O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.n | n }} işlemde {{ O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.net | r }} R,
kazanma oranı {{ O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.isabet | yz1 }}{{? O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.net > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.net > 0 }}.
Bunu bir kural saymak için üç sebeple erken:

1. **Seçim sonradan yapıldı.** "Ay sonu" ayrımı, iki dönemin sonuçları görüldükten sonra öne çıktı. Çok sayıda alt küme
   arasından sonradan seçilen bir kazanan, şansla bulunmuş olabilir.
2. **İşlem az.** Ayda bir işlem, yılda yaklaşık {{ O.basarisiz.ay_sonu.olcek.islem_yil | s0 }} işlem eder. Bu kadar
   az işlemle bir kazancın gerçek olduğunu göstermek yıllar sürer (yedinci ders).
3. **Pariteler aynı şeyi söylemiyor.** Ay sonu işlemleri 2024 →'de USD/JPY'de de artıda
   ({{ O.basarisiz.ay_sonu.parite.USDJPY.oos.ay_sonu.net | r }} R), EUR/USD'de sıfıra yakın
   ({{ O.basarisiz.ay_sonu.parite.EURUSD.oos.ay_sonu.net | r }} R), AUD/USD'de eksi
   ({{ O.basarisiz.ay_sonu.parite.AUDUSD.oos.ay_sonu.net | r }} R){{? O.basarisiz.ay_sonu.parite.USDJPY.oos.ay_sonu.net > 0 and abs(O.basarisiz.ay_sonu.parite.EURUSD.oos.ay_sonu.net) < 0.05 and O.basarisiz.ay_sonu.parite.AUDUSD.oos.ay_sonu.net < 0 }}.
   Gerçek bir akış etkisi her paritede aynı yönde görünmeyebilir, ama bu dağınıklık şansla da uyumlu.

Dürüst sınama, bu kuralı bugünden itibaren yazılı ayarlarıyla izlemektir; geçmiş veri bu soruyu daha fazla cevaplayamaz.

## Özet

- {{ O.basarisiz.kapsam.kural | n }} kuralın hiçbiri, maliyetten sonra, güvenilir biçimde kazandırmıyor.
- Kurallar maliyetten önce yaklaşık başabaş; kayıp neredeyse tamamen makas ve kaymadan geliyor.
- Kazanma oranı tek başına bir şey söylemez; kâra geçmek için gereken oranla birlikte okunur.
- İki ileriye dönük aday var — GBP/USD ay sonu fiksingi ve (beşinci derste) başarısız haber kırılımında süreyle çıkış;
  ikisi de sonradan seçildi ve henüz kanıtlanmış değil.

Sonraki ders: kurallar adım adım — hangi saatte ne olursa ne yapılır.

Bu serinin ayrıntılı backtest notları — her kuralın tam tanımı, parametre ızgaraları, koşul analizleri ve yöntem —
[arşivdeki dokuz derste](/arastirma/fx-gunici-giris/) duruyor.
