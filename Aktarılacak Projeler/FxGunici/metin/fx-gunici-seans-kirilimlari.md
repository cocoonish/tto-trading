---
title: 'FX Gün İçi Stratejiler 2: Seans Kırılımları — Londra Açılışı, Asya Aralığı, New York İlk Dengesi'
description: "Bir seansın ilk aralığının kırılmasına dayanan dört kural, dört majör paritede ve 2018–2026 bid/ask verisiyle: Londra açılış aralığı kırılımı (ORB), Asya aralığı kırılımı ve New York ilk dengesinin iki çıpayla (masaların sabahı ve hisse açılışı) kırılımı. Her biri için kural, örnek günler, örneklem içi ve dışı sonuç, maliyet, rastgele yön sınaması, koşullar, kontrol listesi ve hüküm."
pubDate: 2026-10-17
tags: ['fx', 'gun-ici', 'kirilim', 'orb', 'backtest', 'ders']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Seans açılışında oluşan aralığın kırılmasına girmek gün içi işlem kitaplarının en eski kuralıdır. Bu ders dört biçimini aynı makineyle ölçer: Londra'nın ilk mumu, gecenin aralığı ve New York'un iki ayrı açılışı. Dördü de hiçbir paritede önceden kayıtlı hüküm kuralının şartlarını sağlamıyor: maliyetten sonra kanıtlanmış bir kenar yok.{{! kural_iddia calisan_yok orb asya nyib_0800 nyib_0930 }}"
seviye: 'orta'
onkosul:
  - fx-gunici-giris
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders serinin ayrıntılı yöntem notlarındandır ve arşivdedir. Serinin sade hâli üç kısa derste: [1 · Hangisi işe yarıyor?](/arastirma/fx-gunici-sonuc/) · [2 · Stop ve hedef](/arastirma/fx-gunici-stop-hedef/) · [3 · Kontrol listesi](/arastirma/fx-gunici-kontrol/).</div>

Bir seans açıldığında o seansın katılımcıları ilk dakikalarda fiyatın nerede durması gerektiği üzerine pazarlık
eder; bu pazarlığın sonucu bir **açılış aralığıdır**. Kırılım kuralları aralığın dışına çıkışı yeni bir yönün
başlangıcı sayar. Bu derste dört biçimi var: **Londra açılış aralığı** (Avrupa masalarının ilk mumu), **Asya
aralığı** (gecenin tamamı), ve **New York ilk dengesi** iki çıpayla — New York masalarının sabahı (08:00 New York;
{{! tsi "" "New York 08:00" }}) ve ABD hisse açılışı (09:30 New York; {{! tsi "" "New York 09:30" }}).

Dördü de aynı soruyu sorar: kırılan aralık bir bilgi mi taşıyor, yoksa yalnız stop emirlerinin yeri mi? İlk
cevap kırılım kuralını, ikinci cevap fade dersindeki başarısız kırılım kuralını haklı çıkarır. İki aileyi aynı
seviyelerle ayrı ayrı ölçmenin değeri buradadır: biri kaybettiriyorsa öbürünün kazandırması gerekmez — ikisi de
maliyet öder.

Sonuçlar her stratejide aynı dizide verilir (giriş dersinde tanımlandı): varsayılanın birikimli eğrisi ve
örneklem dışı tablosu, işlemlerin anatomisi, zaman dilimi kıyası, parametre ızgarası ve örneklem içi seçim, maliyet
merdiveni, rastgele yön sınaması, yıl ve oynaklık rejimleri, giriş saatine göre sonuç ve koşul analizi. Dört kuraldan
üçünün varsayılanı önceden kayıtlıdır; birininki türetilmiştir ve bölümünde adıyla yazılır.{{? T.turetilmis_bilesim == 4 and len(T.turetilmis_birim) == 1 and T.turetilmis_birim[0] == "nyib_0800" }}

## Londra açılış aralığı kırılımı (ORB)

{{! strateji orb }}

## Asya aralığı kırılımı

{{! strateji asya }}

## New York ilk dengesi — 08:00

{{! strateji nyib_0800 }}

## New York ilk dengesi — 09:30

{{! strateji nyib_0930 }}

## Dört kuralın özeti

{{! ders_ozet }}

<div class="pratik">
  <span class="etiket">Pratik — seans kırılımları</span>

{{! pratik_islem asya "Alıştırma 1" tuzak }}

{{! pratik_islem nyib_0930 "Alıştırma 2" }}

</div>

## Kaynaklar

{{! kaynaklar fx-gunici-seans-kirilimlari }}

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
