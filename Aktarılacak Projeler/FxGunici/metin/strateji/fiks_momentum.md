### Ne

Fade dersindeki fiksing dönüşünün tersi: fiksinge giden dakikalarda fiyat bir yöne itiliyorsa itiş fiksinge kadar
**sürer** varsayımı. Kural fiksingden önceki mumun yönünde, fiksingden bir mum önce girer ve tam fiksingde çıkar.

### Piyasa mantığı

Fiksingde doldurulacak büyük emirler pencere açılmadan önce de fiyatı etkiler: emri alan banka riskini pencereden
önce kısmen kapatabilir, katılımcılar net akışın yönünü fiyattan okumaya çalışır. Bankaların fiksing çevresindeki
işlemleri 2014'ten itibaren düzenleyici cezalarına konu oldu; hesaplama penceresinin bir dakikadan beş dakikaya
genişletilmesi (2015) o sürecin sonucudur. Momentum savunusu, net fiksing akışının fiyatı pencereye doğru tek yönde
ittiğini ve son dakikalardaki hareketin bu itişin izi olduğunu söyler. Kuralın riski fade dersindeki fiksing dönüşünün
konusudur: itiş fiksingde bitebilir, hatta fiksingden önce tersine dönebilir.

### Kurallar

- **Sinyal mumu.** Londra 16:00'dan iki mum önce başlayan mum (5 dakikalık mumda 15:50–15:55;
  {{! tsi "" "Londra 15:50–15:55" }}).
- **Giriş.** Sinyal mumunun yönünde, 16:00'dan bir mum önce (Londra 15:55; {{! tsi "" "Londra 15:55" }}).
- **Çıkış.** Londra 16:00 ({{! tsi "" "Londra 16:00" }}); stopsuz (ızgarada sert ve kapanış stopu da var: girişten 1 × ATR uzakta).
- **R birimi.** Girişteki ATR(14), aynı zaman dilimi.
- **Günler.** Bütün işlem günleri; ay sonu (ayın son Londra iş günü) ayrıca raporlanır.

{{! kural }}

Varsayılan 5 dakikalık mumlarla 15:50–15:55'in yönünde 15:55'te girer, 16:00'da çıkar.{{? B.varsayilan.tf == 5 and B.varsayilan.tur == "momentum" and B.varsayilan.stop_turu == "yok" }} İşlem beş dakika sürer
ve fiksing penceresinin ilk yarısına (15:57:30 → 16:00) uzanır; çıkış penceresinin ortasındadır.

### Örnekler

{{! sekil ornek "Örnek günler — Fiksing momentumu" }}

{{! ornek }}

Noktalı mavi çizgiler sinyal mumunun tepesi ve dibi, mavi bant sinyal mumunun kendisidir. Kuralın stopu olmadığı için figürde stop çizgisi yoktur; R birimi girişteki ATR'dir. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir.

### Sonuçlar

{{! sonuclar }}

Beş dakikalık bir işlemde maliyetin payını havuzun iki sayısı gösteriyor: örneklem dışında maliyetten önce işlem
başına {{ H.oos.brut_r | r }} R, sonra {{ H.oos.beklenti_r | r }} R.

### Ay sonu

{{! ay_sonu }}

_Önceden kayıtlı varsayılan, net R; her parite iki satır: bütün dönem ve örneklem dışı (2024 →). Fark p: ay
sonu ile öbür günlerin ortalama farkı, Welch t (iki yönlü)._

Ay sonu, portföy yeniden dengelemesinin fiksinge en büyük akışı taşıdığı gün olarak bilinir (Melvin ve Prins,
2015) ve momentum savunusu en çok o gün için kurulur. Örneklem küçüktür: EUR/USD'de ay sonu kümesi bütün dönemde
{{ E.varsayilan.ay_sonu.ay_sonu.tum.n | n }}, örneklem dışında {{ E.varsayilan.ay_sonu.ay_sonu.oos.n | n }} işlem. {{! ay_sonu_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Saat.** 15:50–15:55 Londra: TSİ 17:50–17:55 (İngiltere yaz saati) ya da 18:50–18:55.
4. **Yönü oku, 15:55'te gir, 16:00'da çık** (Londra; {{! tsi "→" "Londra 15:55" "Londra 16:00" }}). Stop yok; R
   birimi girişteki ATR.
5. **Maliyeti önce hesapla.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
