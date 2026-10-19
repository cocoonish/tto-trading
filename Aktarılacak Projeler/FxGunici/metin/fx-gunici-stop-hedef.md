---
title: 'FX Gün İçi Stratejiler 6: Stop ve Hedef — Kazanma Oranı Neden Kâr Getirmiyor'
description: "Hedefi yaklaştırınca kazanma oranı yükselir, uzaklaştırınca düşer; kâr ise neredeyse hiç değişmez. {{ O.kisa.toplam.n | n }} farklı stop ve hedef ayarında ölçülmüş sonuç, kâra geçmek için gereken kazanma oranının basit hesabı ve dar stopun gizli maliyeti."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders', 'risk']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Stop ve hedef, kazancı sık ve küçük mü yoksa seyrek ve büyük mü alacağınızı seçer; olmayan bir avantajı yaratmaz. {{ O.kisa.toplam.n | n }} ayarın eşli kıyası: hedefi uzatmak kazanma oranını düşürüyor ama sonucu değiştirmiyor, stopu yaklaştırmak sonucu kötüleştiriyor."
seviye: 'giris'
onkosul:
  - fx-gunici-sonuc
---

Önceki üç ders her kuralın stop/hedef tablosunu tek tek verdi. Bu ders aynı soruyu bütün kurallar için birlikte sorar
ve arkasındaki aritmetiği anlatır.

Bir işlem kuralının kazanma oranını yükseltmenin en kolay yolu hedefi yaklaştırmaktır: fiyatın 10 pip gitmesi 30 pip
gitmesinden daha sık olur. Ama kazanma oranı kâr değildir. Bu ders, aynı kuralı farklı stop ve hedeflerle denediğimiz
{{ O.kisa.toplam.n | n }} ayarın sonucuyla bunu gösteriyor ve kâra geçmek için gereken kazanma oranının basit hesabını
veriyor.

## Kâra geçmek için gereken kazanma oranı

Bir kuralın kâra geçmesi için kazanma oranının şu eşiği aşması gerekir:

$$\text{gereken kazanma oranı} = \frac{\text{ortalama kayıp}}{\text{ortalama kazanç} + \text{ortalama kayıp}}$$

Hedef stop kadar uzaksa (1R) ve maliyet yoksa kazanç ile kayıp eşittir, gereken oran %50'dir. Hedef stopun iki katı
uzaksa (2R) gereken oran üçte bire iner. Hedefi uzatmak gereken oranı düşürür, ama hedefe ulaşma sıklığı da düşer. İkisi
birbirini götürür: fiyatın yönü hakkında bir bilginiz yoksa hiçbir stop–hedef bileşimi kazandırmaz.

**Maliyet işin hesabını değiştirir.** Her işlemde makas ve kayma ödersiniz; kazanan işlem bu kadar az kazanır, kaybeden
bu kadar çok kaybeder. Bu serinin işlemlerinde ölçülen medyan maliyet {{ O.basarisiz.basabas.maliyet_pip.medyan | s1 }}
pip. Aşağıdaki tablo bu maliyetle, stop uzaklığına göre gereken kazanma oranını veriyor:

{{! kisa_maliyet_stop }}

Tablonun pratik dersi: **dar stop maliyeti büyütür.** Beş pip stoplu bir işlemde maliyet riskin üçte birine yaklaşır ve
1R hedefle kâra geçmek için işlemlerin üçte ikisine yakını kazanmalıdır. Stop ne kadar genişse maliyet o kadar küçük bir
pay olur.

## Bir örnek: yalnız hedef değişiyor

Londra açılış aralığı kırılımında (ORB) stop, giriş saati ve mum aynı kalsın, yalnız hedef değişsin. New York {{ K.gun_sonu_et | t }}'teki
gün sonu ({{! gun_sonu_tsi }}) "hedef yok" seçeneğinin çıkış anıdır.

{{! kisa_hedef_ornek orb }}

Hedef uzadıkça kazanma oranı belirgin biçimde düşüyor; işlem başına sonuç ise üç hedefte de eksi ve birbirine yakın.

## Bütün ayarlar: eşli kıyas

Aynı soruyu bütün kurallar ve pariteler için sorduk. Her çiftte kural, parite ve öbür bütün ayarlar aynı; yalnız tek bir
seçim değişiyor.

{{! kisa_esli_tablo }}

Üç sonuç okunuyor:

- **Hedefi uzatmak** kazanma oranını {{ O.kisa.esli.hedef.d_isabet | pu }} puan değiştiriyor, işlem başına sonucu
  yalnız {{ O.kisa.esli.hedef.d_r | r3 }} R{{? abs(O.kisa.esli.hedef.d_r) < 0.02 and O.kisa.esli.hedef.d_isabet < -0.05 }}.
  Kazanma oranı değişiyor, kâr değişmiyor.
- **Kapanış stopu** (stop seviyesi aşıldığında beklemek, mum o seviyenin ötesinde kapanırsa çıkmak) kazanma oranını
  {{ O.kisa.esli.stop_turu.d_isabet | pu }} puan yükseltiyor; sonucu {{ O.kisa.esli.stop_turu.d_r | r3 }} R
  değiştiriyor{{? O.kisa.esli.stop_turu.d_isabet > 0 and O.kisa.esli.stop_turu.d_r <= 0 }}. Bedeli kuyrukta: kaybeden
  işlemler içinde riskin iki katından fazla kaybedenlerin payı kapanış stopunda {{ O.stop_cikis.kapanis_stop.pay_2r | yz0 }},
  sert stopta {{ O.stop_cikis.stop.pay_2r | yz0 }}.
- **Stopu yaklaştırmak** sonucu {{ O.kisa.esli.stop_yeri.d_r | r3 }} R kötüleştiriyor; sonucu iyileşen çiftlerin
  payı yalnız {{ O.kisa.esli.stop_yeri.b_iyi_pay | yz0 }}{{? O.kisa.esli.stop_yeri.d_r < 0 and O.kisa.esli.stop_yeri.b_iyi_pay < 0.5 }}.
  Sebep yukarıdaki tablo: dar stopta maliyet riskin daha büyük bir parçası.

Hedef türüne göre bütün ayarların özeti de aynı şeyi söylüyor:

{{! kisa_grup_tablo }}

{{! sekil kisa-stop-hedef "Kazanma oranı ne olursa olsun, sonuç çoğunlukla eksi" }}

Şekilde her nokta bir ayar. Noktalar yatayda geniş bir aralığa yayılıyor — kazanma oranı ayara göre çok değişiyor —
ama {{ O.kisa.toplam.n | n }} ayarın yalnız {{ O.kisa.toplam.oos_arti | n }} tanesi sıfır çizgisinin üstünde. Sağa
doğru bulut biraz yükseliyor: kazanma oranı %50'nin üstündeki {{ O.kisa.yuksek_isabet."0.5".n | n }} ayarın medyan sonucu
{{ O.kisa.yuksek_isabet."0.5".r | ra }} R, bütün ayarlarınki {{ O.kisa.toplam.r | ra }} R{{? O.kisa.yuksek_isabet."0.5".r > O.kisa.toplam.r and O.kisa.yuksek_isabet."0.5".r < 0 }}.
Daha az kaybettiriyorlar, ama onlar da kazandırmıyor.

## Yüksek kazanma oranının tuzağı

2024 → döneminde kazanma oranı {{= "%60" }}'ın üstünde olan {{ O.kisa.yuksek_isabet."0.6".n | n }} ayar var; bunların işlem
başına medyan sonucu {{ O.kisa.yuksek_isabet."0.6".r | ra }} R{{? O.kisa.yuksek_isabet."0.6".r < 0 }}. Yüksek kazanma
oranı çoğu zaman yakın hedefin işaretidir: küçük kazançlar sık gelir, arada gelen büyük kayıplar onları siler.

## "En iyi ayarı seçmek" de işe yaramıyor

Ayarların içinden 2018–2023'te en iyi çıkan {{ O.kisa.secim.n | n }} tanesini seçtik. O dönemde işlem başına ortalama
{{ O.kisa.secim.is_r | ra }} R kazandırıyorlardı; 2024 →'de ortalama {{ O.kisa.secim.oos_r | ra }} R kaybettirdiler
ve yalnız {{ O.kisa.secim.oos_arti | n }} tanesi artıda kaldı{{? O.kisa.secim.oos_r < 0 }}. Geçmişte en iyi görünen
ayar, çoğu zaman o geçmişin şansını yakalamış ayardır. {{ O.kisa.toplam.n | n }} ayarın
{{ O.kisa.toplam.ikisi_arti | n }} tanesi iki dönemde de artıda; ama hangileri olacağı önceden bilinemiyordu ve
çok sayıda ayar denendiğinde birkaçının şansla iki dönemde de artı çıkması beklenir.

## Pratikte

- **Hedefi kazanma oranına göre değil, maliyete göre seçin.** Yakın hedef maliyeti büyütür; uzak hedef kazanma oranını
  düşürür. Avantaj yoksa ikisi de kaybettirir.
- **Stopu maliyetin birkaç katı uzağa koyun.** Stop beş pip civarına indiğinde maliyet tek başına sonucu eksiye çeker.
- **Kapanış stopunu bilerek kullanın.** Kazanma oranını yükseltir, ama ara sıra riskin iki katından fazla kaybettirir.
- **Kazanma oranına değil, işlem başına net sonuca bakın.** Kazanma oranı ancak gereken oranla yan yana anlamlıdır.
- **Stop ve hedef bir avantaj yaratmaz; var olanı paketler.** Önce kuralın maliyetten önce kazandırdığını görmek gerekir.

Sonraki ders: kurala süzgeç eklemek (günlük EMA20, oynaklık şartı) sonucu değiştiriyor mu.
