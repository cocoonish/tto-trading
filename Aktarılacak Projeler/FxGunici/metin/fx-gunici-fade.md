---
title: 'FX Gün İçi Stratejiler 4: Fade — Başarısız Kırılım, VWAP, Pivot ve Fiksing Dönüşü'
description: "Kırılımın tersine, ortalamaya ya da seviyeye dönüşe bahis yapan altı kural, dört majör paritede ve 2018–2026 bid/ask verisiyle: başarısız kırılım (turtle soup) üç seviyede — Londra aralığı, Asya aralığı, önceki gün tepe/dip —, VWAP'a dönüş, pivot dönüşü ve WM/R 16:00 fiksingi sonrası dönüş (ay sonu ayrı). Kural, örnek günler, sonuç, maliyet, rastgele yön sınaması, koşullar ve hüküm."
pubDate: 2026-10-16
tags: ['fx', 'gun-ici', 'fade', 'turtle-soup', 'vwap', 'fiksing', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Kırılım kurallarının aynası: fiyat bir seviyenin dışına taşıp geri döndüğünde, ortalamadan uzaklaştığında ya da fiksing akışı bittiğinde tersine girmek. Altı kuralın hangisinin geri dönüşü gerçekten yakaladığını, hangisinin yalnız stop'u yakın bir maliyet makinesi olduğunu ölçer."
seviye: 'orta'
onkosul:
  - fx-gunici-giris
  - fx-gunici-seans-kirilimlari
---

**Fade** (harekete karşı işlem), bir hareketin tersine işlem yapmaktır. Kırılım kuralları hareketin süreceğine bahis yapar;
fade kuralları hareketin aşırı olduğuna, likidite ya da akışla şiştiğine ve geri geleceğine. İki aile çoğu zaman aynı
seviyeye zıt bahis yapar ve bu ders o seviyeleri bilerek yeniden kullanır: başarısız kırılımın üç biçimi seans ve
yapı kırılımlarının Londra aralığına, Asya aralığına ve önceki günün uçlarına bakar; pivot dönüşü pivot kırılımının
aynasıdır.

Fade kurallarının ortak bir yapısal özelliği var: stop'ları çoğu zaman yakındır (gezintinin ucu, sinyal mumunun
ucu). Hedefleri ya sabit bir R katıdır (başarısız kırılımlarda 1R) ya da bir seviyedir (VWAP, pivot), ve seviye
hedefleri risk biriminde kısa değildir: yakın stop'la ölçüldüğünde VWAP dönüşünde hedefin uzaklığı
{{! hedef_uzaklik vwap_donus }}, pivot dönüşünde {{! hedef_uzaklik pivot_donus }}. EUR/USD'de örneklem dışında başarısız kırılımların ve pivot dönüşünün stop
medyanı, aynı seviyenin kırılım kuralınınkinden küçük (dersin sonundaki ikinci tablo){{? O.birim.sahte_orb.cift.EURUSD.varsayilan.oos.risk_pip < O.birim.orb.cift.EURUSD.varsayilan.oos.risk_pip and O.birim.sahte_asya.cift.EURUSD.varsayilan.oos.risk_pip < O.birim.asya.cift.EURUSD.varsayilan.oos.risk_pip and O.birim.sahte_pdhl.cift.EURUSD.varsayilan.oos.risk_pip < O.birim.pdhl.cift.EURUSD.varsayilan.oos.risk_pip and O.birim.pivot_donus.cift.EURUSD.varsayilan.oos.risk_pip < O.birim.pivot_kirilim.cift.EURUSD.varsayilan.oos.risk_pip }}. Yakın stop R'yi küçültür, maliyet ise R'den bağımsız olarak her işlemde aynı
pip kadar ödenir: aynı makas, riski küçük bir işlemde R cinsinden daha pahalıdır. Bu yüzden fade kurallarında
maliyet satırı kırılımlarınkinden daha belirleyicidir.

Son kural farklı bir yapıdadır: **fiksing dönüşü** bir seviyeye değil bir saate bakar — Londra 16:00'daki WM/R
fiksingi, akışın en yoğun toplandığı an. Ön kayıt fiksing kurallarının ay sonunda ayrıca raporlanmasını istedi;
tablosu bölümün içinde.

## Başarısız kırılım — Londra açılış aralığı

{{! strateji sahte_orb }}

## Başarısız kırılım — Asya aralığı

{{! strateji sahte_asya }}

## Başarısız kırılım — önceki gün tepe/dip

{{! strateji sahte_pdhl }}

## VWAP'a dönüş

{{! strateji vwap_donus }}

## Pivot dönüşü

{{! strateji pivot_donus }}

## WM/R 16:00 fiksingi — dönüş

{{! strateji fiks_donus }}

## Altı kuralın özeti

{{! ders_ozet }}

Kırılım dersleriyle aynı seviyelerin iki tarafı yan yana:

{{! ders_ozet orb sahte_orb asya sahte_asya pdhl sahte_pdhl pivot_kirilim pivot_donus }}

<div class="pratik">
  <span class="etiket">Pratik — fade</span>

{{! pratik_islem sahte_orb "Alıştırma 1" tuzak }}

{{! pratik_islem pivot_donus "Alıştırma 2" }}

</div>

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
