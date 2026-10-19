---
title: 'FX Gün İçi Stratejiler 7: Bir Kuralı Denemeden Önce — Kontrol Listesi'
description: "Bir gün içi FX kuralını kendiniz sınamak ya da uygulamak istiyorsanız önce bakılacak altı şey: maliyetinizin pip karşılığı, stopun maliyete oranı, kazanma oranı yerine işlem başına net sonuç, kaç işlemin yeteceği, ayarların önceden yazılması ve ileriye dönük izleme."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders', 'risk']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Kuralların sonucunu önceki dersler anlattı; bu ders, bir kuralı kendiniz denemek isterseniz neye bakmanız gerektiğini sayılarla veriyor: maliyetin pip karşılığı, stopun maliyete oranı, net sonuç, gereken işlem sayısı, önceden yazılmış ayarlar ve adayların ileriye dönük izlenmesi."
seviye: 'giris'
onkosul:
  - fx-gunici-sonuc
  - fx-gunici-stop-hedef
---

Önceki dersler iki şey gösterdi: sınanan kuralların hiçbiri maliyetten sonra güvenilir biçimde kazandırmıyor, ve stop ile
hedefi değiştirmek bunu değiştirmiyor. Bu ders bir adım geri çekilip pratik bir soru soruyor: bir kuralı kendiniz denemek
ya da birinin önerdiği bir kuralı değerlendirmek isterseniz, neye bakmanız gerekir?

## 1. Maliyetinizi pip olarak bilin

Her işlem bir kez tam makas öder (yarısı girişte, yarısı çıkışta) ve her dolumda, yani girişte ve çıkışta, biraz kayma olur. Bu serinin sınamasında
kullanılan maliyet:

{{! kisa_parite_maliyet }}

Kendi aracı kurumunuzun makası farklıdır; aynı saatte birkaç gün boyunca kendiniz not edin. Sınamada kullandığınız maliyet
gerçekte ödediğinizden küçükse, sınama sonucu gerçekte olacağından iyi çıkar.

## 2. Stopu maliyete göre koyun

Aynı pip maliyeti, stop daraldıkça riskin daha büyük bir parçası olur. Serinin işlemleri stop uzaklığına göre üçe
bölündüğünde:

<div class="sayi-tablo">

| Stop | Medyan stop (pip) | Maliyet (R) | İşlem başına net (R) |
|---|---|---|---|
| Dar | {{ O.basarisiz.olcek.ucte_bir.oos.R[0] | s1 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet[0] | s2 }} | {{ O.basarisiz.olcek.ucte_bir.oos.net[0] | r }} |
| Orta | {{ O.basarisiz.olcek.ucte_bir.oos.R[1] | s1 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet[1] | s2 }} | {{ O.basarisiz.olcek.ucte_bir.oos.net[1] | r }} |
| Geniş | {{ O.basarisiz.olcek.ucte_bir.oos.R[2] | s1 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet[2] | s2 }} | {{ O.basarisiz.olcek.ucte_bir.oos.net[2] | r }} |

</div>

_2024 → dönemi, kuralların varsayılan ayarları; her kural–parite bileşiminin işlemleri kendi içinde stop uzaklığına göre
üçe bölündü, hücre bileşimlerin medyanı._

Geniş stoplu işlemler daha az kaybettiriyor{{? O.basarisiz.olcek.ucte_bir.oos.net[0] < O.basarisiz.olcek.ucte_bir.oos.net[1] and O.basarisiz.olcek.ucte_bir.oos.net[1] < O.basarisiz.olcek.ucte_bir.oos.net[2] }},
ama kazandırmıyor{{? O.basarisiz.olcek.ucte_bir.oos.net[2] < 0 }}. Fark neredeyse tamamen maliyetten geliyor: pip
cinsinden maliyet üç dilimde de birbirine yakın, R cinsinden ise dar stopta geniş stopun yaklaşık üç katı. Tablo bir
seçim kuralı değildir: geniş stoplu işlemleri ayıklamak bir kuralı kazandırmaz, yalnız maliyetin nerede ağırlaştığını
gösterir. Pratik kural: **stop,
maliyetinizin en az birkaç katı uzakta olmalı.** Dar stop "riski küçültmez"; yalnız maliyeti büyütür.

## 3. Kazanma oranına değil, işlem başına net sonuca bakın

İkinci dersin ana sonucu: kazanma oranı stop ve hedefle istediğiniz yere çekilebilir, işlem başına net sonuç
çekilemez. Bir kuralı değerlendirirken sorulacak tek soru şudur: **maliyet düşüldükten sonra, işlem başına ortalama kaç R
kazandırıyor?** Kazanma oranı yalnız, kâra geçmek için gereken oranla yan yana yazıldığında bir şey söyler.

## 4. Kaç işlem yeter?

Gerçek bir kenar küçükse, onu şanstan ayırmak çok işlem ister. Aşağıdaki tablo, belli bir sıklıkla ve sürede işlem
yapan bir kuralın, işlem başına en az ne kadar kazandırması gerektiğini gösteriyor ki sonuç şanstan ayırt edilebilsin:

{{! kisa_guc_tablo }}

Günde bir işlem yapan bir kural, bir yıllık kayıtla ancak işlem başına {{ O.basarisiz.guc.mde.tablo.gunde."1" | s2 }} R'lik
bir kenarı gösterebilir; ayda bir işlem yapan bir kural için bu eşik {{ O.basarisiz.guc.mde.tablo.ayda."1" | s2 }} R.
Bu serideki kuralların maliyetten önceki ortalama kenarı işlem başına {{ O.basarisiz.ayrisim.oos.ort.brut | r3 }} R; tablonun
en küçük hücresinin bile çok altında{{? O.basarisiz.ayrisim.oos.ort.brut < O.basarisiz.guc.mde.tablo.gunde."10" }}.

## 5. Ayarları önceden yazın, sonra bakın

Bir kuralı denerken en kolay yanılgı, çok sayıda ayarı deneyip en iyisini seçmektir. Stop ve hedef dersinde bunu ölçtük: 2018–2023
döneminde en iyi çıkan {{ O.kisa.secim.n | n }} ayar o dönemde işlem başına {{ O.kisa.secim.is_r | ra }} R kazandırıyordu,
2024 →'de ortalama {{ O.kisa.secim.oos_r | ra }} R kaybettirdi{{? O.kisa.secim.oos_r < 0 and O.kisa.secim.is_r > 0 }}.
Doğru sıra şudur: kuralı, stopu, hedefi, saatleri ve "işe yarıyor" demenin şartını **sonuca bakmadan** yazın; sonra bir
kez sınayın. Sonucu gördükten sonra değiştirdiğiniz her ayar, sınamayı biraz daha az güvenilir yapar.

## 6. Adayları ileriye dönük izleyin

Serinin en belirgin adayı GBP/USD'de Londra fiksingi momentumunun ay sonu işlemleri (birinci ders); ikincisi başarısız
haber kırılımında süreyle çıkış (beşinci ders). Birincisinin kuralı basit:
ayın son iş günü Londra 15:50–15:55 mumunun ({{! tsi "" "Londra 15:50–15:55" }}) yönünde Londra 15:55'te
({{! tsi "" "Londra 15:55" }}) girilir, Londra 16:00'da ({{! tsi "" "Londra 16:00" }}) çıkılır. Bu alt küme sonuçlar
görüldükten sonra seçildiği için geçmiş veri onu kanıtlayamaz. Geriye tek dürüst yol kalıyor: kuralı bugünden itibaren
değiştirmeden izlemek.

Bunun ne kadar süreceği de hesaplanabilir. Ayda bir işlemle, ölçülen kenar ({{ O.basarisiz.guc.gbp.senaryo.gozlenen.mu | r }} R)
gerçek olsa bile onu güvenilir biçimde göstermek yaklaşık {{ O.basarisiz.guc.gbp.senaryo.gozlenen.yil | s0 }} yıl sürer;
gerçek kenar bunun yarısıysa yaklaşık {{ O.basarisiz.guc.gbp.senaryo.yari.yil | s0 }} yıl. Tek bir paritede ayda bir işlem,
kısa sürede hüküm verecek bir sınama değildir.

## Kontrol listesi

Bir gün içi FX kuralını kullanmadan önce:

1. **Maliyet.** Paritenin makasını ve kaymasını pip olarak biliyor musunuz? Sınama o maliyetle mi yapıldı?
2. **Stop.** Stop, maliyetin en az birkaç katı uzakta mı?
3. **Net sonuç.** İşlem başına sonuç maliyetten sonra artı mı? Kazanma oranına değil, buna bakın.
4. **Örneklem dışı.** Sonuç, kuralın ayarlarını seçerken bakılmamış bir dönemde de artı mı?
5. **İşlem sayısı.** Kayıt, o büyüklükte bir kenarı şanstan ayıracak kadar uzun mu?
6. **Önceden yazım.** Kural, stop, hedef ve başarı şartı sonuca bakmadan mı yazıldı?
7. **Kaynak.** Kenarın bir sebebi var mı: belli bir saatte tekrar eden bir akış, bir haber, bir maliyet avantajı?

Bu serideki kuralların hiçbiri, dört paritenin hiçbirinde, üçüncü maddeyi güvenilir biçimde geçmedi. Listeyi geçen bir kural bulursanız, onu da önce küçük
bir tutarla ve yazılı kurallarla izleyin.

Bu serinin ayrıntılı backtest notları — her kuralın tam tanımı, parametre ızgaraları, koşul analizleri ve yöntem —
[arşivdeki dokuz derste](/arastirma/fx-gunici-giris/) duruyor.
