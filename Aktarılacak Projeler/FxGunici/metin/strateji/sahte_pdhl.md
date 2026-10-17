### Ne

Başarısız kırılım, seviye olarak **dünün tepesi ve dibiyle**: fiyat önceki günün tepesinin üstünde (ya da dibinin
altında) kapanır, bir ya da iki mum içinde kırılan seviyenin berisine dönerse ters yönde girilir. Yapı kırılımları
dersindeki önceki gün tepe/dip kuralının aynasıdır.

### Piyasa mantığı

Dünün uçları günlerdir izlenen seviyelerdir ve stopların en kalabalık olduğu yerlerden biridir. Bir günün tepesinin
kısa bir süre aşılıp geri dönülmesi grafik okumasında "likidite avı" (*liquidity grab*, *stop hunt*) diye anılır.
Bu kural o okumayı mekanik bir tanıma bağlar: aşılan seviye kapanışla geri alınırsa aşış başarısız sayılır.

### Kurallar

- **Seviye.** Önceki FX işlem gününün (17:00 → 17:00 New York; gün dönümü {{! tsi "" "New York 17:00" }})
  orta fiyattan tepesi ve dibi.
- **Kırılım, geri dönüş, stop.** Sahte ORB ile aynı. Kırılım mumu seviyeyi kesen mumdur (önceki kapanış içeride
  ya da uçta): seviye Asya saatlerinde aşılmışsa ve fiyat Londra açıldığında hâlâ dışarıdaysa, pencerenin ilk mumu
  bir kırılım sayılmaz; kural fiyatın içeri dönüp seviyeyi yeniden kesmesini bekler. Kesiş tanımı "pencere"
  parametresine anlam verir: dışarıda her kapanış bir kırılım sayılsaydı, içeride kapanan ilk mum neredeyse her zaman dışarıda
  kapanmış bir mumun hemen ardından gelirdi ve en kısa pencere (bir mum) onu zaten yakalardı.
- **Pencere.** Londra 08:00 → 14:00 New York ({{! tsi "→" "Londra 08:00" "New York 14:00" }}); gün başına tek
  işlem.

{{! kural }}

Varsayılan: 15 dakikalık mumlar, iki mumluk pencere, 1R hedef.{{? B.varsayilan.tf == 15 and B.varsayilan.pencere == 2 and B.varsayilan.seviye == "pdhl" and B.varsayilan.hedef == "1R" and B.varsayilan.stop_turu == "sert" }}

### Örnekler

{{! sekil ornek "Örnek günler — Sahte PDH/PDL" }}

{{! ornek }}

Noktalı mavi çizgiler dünün tepesi ve dibi, mavi bant içeri dönen sinyal mumudur. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir: {{! tuzak "geri dönüş başlıyor, sonra kırılım yeniden başlayıp stopu alıyor." "geri dönüş başlıyor ama sürmüyor; işlem stopa değmeden zararla kapanıyor ({cikis})." }}

### Sonuçlar

{{! sonuclar }}

**Ön kaydın harfiyle.** Ön kaydın harfi iki yerde bu dersteki okumadan farklı okunabilir; iki okuma da ilk
sonuçlardan önce sabitlendi ve hüküm onlarla verilir. Kırılım mumu: ön kayıt kırılımı "bir mum seviyenin dışında
kapanır" diye tanımlar ve önceki kapanışı sormaz. Harfiyle okunursa pencerenin ilk mumu dışarıda kapandığında,
seviye Asya saatlerinde aşılmış olsa da, o mum bir kırılımdır ve açılıştan sonraki geri alınış işlem verir. Geri
dönüş: harfe göre dönüş mumu dünün aralığının içinde kapanır ve karşı ucun ötesinde kapanan mum ters yönde yeni bir
kırılımdır; bu ölçüm yalnız kırılan seviyeyi sorar. Harfin iki okuması aynı koşuda ayrıca, her biri tek başına
ölçüldü. {{! yorum_cumle }}

{{! yorum }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Dünün tepe ve dibi.** 17:00 New York'ta ({{! tsi "" "New York 17:00" }}) kapanan günün uçları.
4. **Kırılımı gör, girme; geri dönüşü bekle.** En çok iki mum içinde kırılan seviyenin berisinde kapanış.
5. **Stop gezintinin ucunda, hedef 1R.** Pencere 14:00 New York'ta kapanır (TSİ 21:00 ya da 22:00).
6. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
