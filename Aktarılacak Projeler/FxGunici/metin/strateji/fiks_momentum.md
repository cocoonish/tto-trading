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

- **Sinyal mumu.** Londra 16:00'dan iki mum önce başlayan mum (5 dakikalık mumda 15:50–15:55).
- **Giriş.** Sinyal mumunun yönünde, 16:00'dan bir mum önce (15:55).
- **Çıkış.** Londra 16:00; stop'suz (ızgarada sert ve kapanış stop'u da var: 1 × ATR).
- **R birimi.** Girişteki ATR(14), aynı zaman dilimi.
- **Günler.** Bütün işlem günleri; ay sonu (ayın son Londra iş günü) ayrıca raporlanır.

{{! kural }}

Varsayılan 5 dakikalık mumlarla 15:50–15:55'in yönünde 15:55'te girer, 16:00'da çıkar.{{? B.varsayilan.tf == 5 and B.varsayilan.tur == "momentum" and B.varsayilan.stop_turu == "yok" }} İşlem beş dakika sürer
ve fiksing penceresinin ilk yarısına (15:57:30 → 16:00) uzanır; çıkış penceresinin ortasındadır.

### Örnekler

{{! sekil ornek "Örnek günler — Fiksing momentumu" }}

{{! ornek }}

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

Beş dakikalık bir işlemde maliyetin payını havuzun iki sayısı gösteriyor: örneklem dışında maliyetten önce işlem
başına {{ H.oos.brut_r | r }} R, sonra {{ H.oos.beklenti_r | r }} R.

### Ay sonu

{{! ay_sonu }}

_Önceden kayıtlı varsayılan, net R. Ay sonu ve öbür günler bütün dönemde; fark Welch t ile (iki yönlü p). Son iki
sütun ay sonunun örneklem dışı karşılığı._

Ay sonu, portföy yeniden dengelemesinin fiksinge en büyük akışı taşıdığı gün olarak bilinir (Melvin ve Prins,
2015) ve momentum savunusu en çok o gün için kurulur. Küçük örneklem uyarısı burada da geçerli: EUR/USD'de ay sonu
kümesi bütün dönemde {{ E.varsayilan.ay_sonu.ay_sonu.tum.n | n }}, örneklem dışında {{ E.varsayilan.ay_sonu.ay_sonu.oos.n | n }} işlem.

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Saat.** 15:50–15:55 Londra (TSİ yazın 17:50–17:55, kışın 18:50–18:55).
2. **Yönü oku, 15:55'te gir, 16:00'da çık.**
3. **Maliyeti önce hesapla.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
