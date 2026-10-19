---
title: 'FX Gün İçi Stratejiler 7: Süzgeçler — EMA20 ve Oynaklık Şartı Kuralları Kurtarır mı'
description: "Kuralların üstüne altı süzgeç koyduk: günlük EMA20 yönünde işlem, 60 dakikalık trend yönünde işlem, oynaklık şartı, dar yapı ve ikili bileşimleri. Süzgeçler sonuçtan önce yazıldı; {{ O.suzgec.coklu.sinama | n }} sınamanın hiçbiri kuralı güvenilir biçimde kâra geçirmedi."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders', 'risk']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Bir kuralı yalnız günlük EMA20 yönünde ya da yalnız oynaklık yüksekken işlemek kazanma oranını ve sonucu biraz oynatıyor, kaybı kâra çevirmiyor. Altı süzgeç önceden yazıldı; 2018–2023'e bakarak seçilen süzgeçle {{ O.suzgec.hukum.calismiyor | n }} kural çalışmıyor, hiçbiri çalışıyor hükmü almadı."
seviye: 'giris'
onkosul:
  - fx-gunici-sonuc
  - fx-gunici-stop-hedef
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders gün içi FX kurallarının ayrıntılı sınamasındandır ve arşivdedir. Gün içi seri şimdi açılış, fiksing ve haber anlarının oyun planı olarak beş derste: [1 · İlk mumu okumak](/arastirma/fx-oyun-okuma/) · [2 · Açılışlar](/arastirma/fx-oyun-acilislar/) · [3 · Fiksingler](/arastirma/fx-oyun-fiksingler/) · [4 · Haber mumları](/arastirma/fx-oyun-haberler/) · [5 · Backtest](/arastirma/fx-oyun-backtest/).</div>

Önceki ders stop ve hedefin kaybı kâra çevirmediğini gösterdi. Sık sorulan ikinci soru şu: kurala bir **süzgeç**
eklesek? Örneğin yalnız fiyat günlük 20 günlük ortalamanın (EMA20) üstündeyken alsak, altındayken satsak. Ya da
kırılımı yalnız piyasa yeterince oynakken işlesek. Bu ders altı süzgecin sonucunu veriyor.

Kısa cevap: **hayır.** Süzgeçler sonuçtan önce yazıldı ve her kuralda 2018–2023'e bakarak biri seçildi. Seçilen
süzgeçle 2024 → döneminde {{ O.suzgec.hukum.calisiyor | n }} kural çalışıyor, {{ O.suzgec.hukum.zayif | n }} kural zayıf,
{{ O.suzgec.hukum.calismiyor | n }} kural çalışmıyor{{? O.suzgec.hukum.calisiyor == 0 }}.

## Altı süzgeç

Süzgeç bir işlemi ya tutar ya atar. Atılan işlemin yerine o gün başka bir sinyal aranmaz; kuralın geri kalanı (giriş,
stop, hedef, saatler) önceden kayıtlı varsayılanında kalır. Her süzgeç yalnız giriş anında bilinen bilgiyi kullanır:
bugünün kapanışı ya da bugünün oynaklığı süzgece girmez.

{{! suzgec_tanim }}

Süzgeçler, eşikleri, seçim kuralı ve hüküm kuralı ayrı bir ön kayıtta yazıldı ve ön kayıt
{{ O.suzgec.zaman.onkayit.zaman | tarih }} günü, ölçüm kodundan önce depoya girdi. Bir not: 60 dakikalık trend, oynaklık
ve yapının büyüklüğü bu serinin arşiv derslerinde koşul olarak zaten ölçülmüştü; onların kaba sonucu süzgeçler
yazılmadan önce biliniyordu. Günlük EMA20 ise ilk kez burada ölçüldü.

## Sonuç: kural kural

{{! suzgec_kural_tablo }}

{{! sekil kisa-suzgec "Süzgeçle de sonuç çoğunlukla eksi" }}

Şekilde her satır bir kural. Gri çizgi altı süzgecin 2024 → sonuçlarının aralığı. Çizgilerin çoğu baştan sona sıfırın
solunda: altı süzgeçten herhangi birinin artı sonuç verdiği kural sayısı {{ O.suzgec.herhangi_oos_arti | n }}, bunlardan
2018–2023'te de artı olan {{ O.suzgec.herhangi_iki_arti | n }}{{? O.suzgec.herhangi_iki_arti <= 1 }}. Seçilen süzgeçlerin
2024 → ortalaması işlem başına {{ O.suzgec.ort.secilen_oos | ra }} R, süzgeçsiz kuralların ortalaması
{{ O.suzgec.ort.yok_oos | ra }} R{{? O.suzgec.ort.secilen_oos < 0 and O.suzgec.ort.secilen_oos > O.suzgec.ort.yok_oos }}.
Süzgeç ortalamada kaybı biraz küçültüyor; kâra çevirmiyor.

{{! suzgec_gecen }}

## Süzgeç süzgeç

{{! suzgec_ozet_tablo }}

Tablodan okunanlar:

- **Günlük EMA20 yönünde işlem** kazanma oranını medyanda yalnız {{ O.suzgec.ozet.ema20.isabet_fark_oos_medyan | pu }}
  puan değiştiriyor, işlem başına sonucu {{ O.suzgec.ozet.ema20.fark_oos_medyan | ra }} R{{? abs(O.suzgec.ozet.ema20.fark_oos_medyan) < 0.01 }}.
  Gün içi bir işlemin sonucu, fiyatın günlük ortalamanın hangi tarafında olduğuna neredeyse bağlı değil.
- **Oynaklık şartı** sonucu en çok iyileştiren süzgeç: {{ O.suzgec.ozet.oynak.kural | n }} kuralın
  {{ O.suzgec.ozet.oynak.oos_iyi | n }} tanesinde 2024 →'de iyileşme, medyanda {{ O.suzgec.ozet.oynak.fark_oos_medyan | r3 }} R.
  Ama iyileşmenin çoğu maliyetten geliyor: maliyetten önceki sonuç medyanda yalnız
  {{ O.suzgec.ozet.oynak.brut_fark_oos_medyan | r3 }} R değişiyor, oynak günlerde stop ise
  {{ O.suzgec.ozet.oynak.risk_orani_oos_medyan | s2 }} kat geniş{{? O.suzgec.ozet.oynak.risk_orani_oos_medyan > 1.1 and O.suzgec.ozet.oynak.brut_fark_oos_medyan < O.suzgec.ozet.oynak.fark_oos_medyan }}.
  Aynı pip maliyeti geniş stopta riskin daha küçük bir parçası olur; önceki dersin dar stop tablosunun tersi. Kural
  daha iyi yön bulmuyor, aynı maliyeti daha büyük bir hareketin üstüne yayıyor; ve yine de kaybettiriyor.
- **Dar yapı** sonucu kötüleştiriyor: 2024 →'de iyileştirdiği kural sayısı yalnız {{ O.suzgec.ozet.dar.oos_iyi | n }}{{? O.suzgec.ozet.dar.oos_iyi <= 5 }}.
  Dar yapı dar stop demektir ve dar stopta maliyet büyür.
- **İyileşme bir dönemden ötekine taşınmıyor.** Bir süzgecin 2018–2023'te bir kurala kazandırdığı ile 2024 →'de
  kazandırdığı arasındaki sıra ilintisi EMA20'de {{ O.suzgec.ozet.ema20.sira_ilinti | s2 }}, oynaklık şartında
  {{ O.suzgec.ozet.oynak.sira_ilinti | s2 }}, ikisi birlikte {{ O.suzgec.ozet.ema20_oynak.sira_ilinti | s2 }}{{? O.suzgec.ozet.oynak.sira_ilinti < 0.2 and O.suzgec.ozet.ema20_oynak.sira_ilinti < 0.2 }}.
  Geçmişte hangi kurala yaradığına bakarak süzgeç seçmek, bugün hangi kurala yarayacağını söylemiyor.

## Şansla ne beklenir

{{ O.suzgec.coklu.sinama | n }} süzgeçli sonucu ({{ O.suzgec.kural_n | n }} kural × {{ O.suzgec.suzgec_n | n }} süzgeç) 2024 →'de tek tek de ölçtük. Hiçbir süzgecin
kazandırmadığı bir dünyada bile, %95 aralığının alt ucu şansla sıfırın üstüne çıkan yaklaşık
{{ O.suzgec.coklu.sans_beklenen | s1 }} sonuç beklenir. Gerçekte bu sayı {{ O.suzgec.coklu.alt_uc_arti | n }}{{? O.suzgec.coklu.alt_uc_arti <= O.suzgec.coklu.sans_beklenen }};
çoklu sınamaya göre düzeltilince (Benjamini–Hochberg) geçen sonuç sayısı {{ O.suzgec.coklu.bh_n | n }}.

Parite parite bakınca tablo kalabalıklaşıyor ama sonuç değişmiyor: {{ O.suzgec.hucre.n | n }} kural × parite ×
süzgeç hücresinin iki dönemde de en az {{ O.suzgec.esik.asgari | n }} işlemle iki dönemde de artı olanı
{{ O.suzgec.hucre.iki_arti | n }}. Bu kadar çok hücre denendiğinde birkaçının iki dönemde de şansla artı çıkması
beklenir; hangileri olacağı önceden bilinemezdi.

## Pratikte

- **Süzgeç bir avantaj yaratmaz; işlemleri seçer.** Kuralın kendisi maliyetten önce kazandırmıyorsa, işlemlerin bir
  kısmını atmak kalan kısmı kazandırmaz.
- **Kazanma oranındaki küçük artışa aldanmayın.** EMA20 gibi bir süzgeç kazanma oranını bir iki puan oynatabilir;
  işlem başına net sonuca bakın.
- **"Oynaklık yüksekken işle" bir maliyet kuralıdır.** Geniş stop maliyetin payını küçültür; yön bilgisi eklemez. Aynı
  sonucu stopu maliyetin birkaç katı uzağa koyarak da görürsünüz (önceki ders).
- **Süzgeci önceden yazın.** Sonuca bakarak seçilen süzgeç, o sonucun şansını da seçer. Burada süzgeçler ve seçim kuralı
  ölçümden önce yazıldı; yine de geçen tek sonuç zayıf kaldı.

Sonraki ders: bir kuralı kendiniz denemek isterseniz kontrol listesi.
