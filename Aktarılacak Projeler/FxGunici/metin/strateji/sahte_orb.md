### Ne

**Başarısız kırılım** kuralı kırılım dersinin aynasıdır: fiyat bir seviyenin dışında kapanır, birkaç mum içinde
yeniden içeride kapanırsa kırılımın **tersine** işleme girilir. Adı (*turtle soup*) Laurence Connors ve Linda
Bradford Raschke'nin *Street Smarts* kitabından gelir: kitaptaki kural, "kaplumbağaların" yirmi günlük
kırılım kuralını tersine oynuyordu. Burada aynı fikir gün içi seviyelere uygulanıyor; ilk seviye Londra açılış
aralığı, yani kırılım dersindeki ORB'nin seviyesi.

### Piyasa mantığı

Açılış aralığının hemen dışı stop emirlerinin en yoğun olduğu yerdir: aralığın içinde pozisyon alan herkes stop'unu
aralığın öbür ucunun biraz ötesine koyar. Fiyat oraya uzandığında bu emirler tetiklenir ve hareket kendini
besler; ama emirler bitince hareketi taşıyacak yeni alıcı (ya da satıcı) yoksa fiyat aralığa geri döner. Büyük
bir emri doldurmak isteyen bir katılımcı için bu likidite tam aradığı şeydir. Fade savunusu bu yüzden basittir:
kapanışla aralığa geri dönüş, dışarıdaki hareketin yeni bilgiye değil stop'lara dayandığını gösterir. Riski de
aynı yerden okunur: geri dönüş geçici olabilir ve kırılım gün içinde yeniden başlayabilir.

### Kurallar

- **Seviye.** Londra açılış aralığı: Londra 08:00'den itibaren ilk mum (kırılım dersindeki ORB aralığı).
- **Kırılım.** Bir mum aralığın dışında kapanır (önceki kapanış içeride ya da uçta).
- **Geri dönüş.** Sonraki "pencere" kadar mumun (bir ya da iki) içinde bir mum yeniden içeride kapanırsa kırılımın
  tersi yönde giriş; gelmezse o kırılım biter ve kural bir sonraki kırılımı bekler.
- **Stop.** Kırılım mumundan dönüş mumuna kadarki en uç fiyat (yukarı kırılımda en yüksek tepe).
- **Pencere.** Aralıktan sonra Londra 14:00'e kadar; gün başına tek işlem.

{{! kural }}

Varsayılan iki mumluk pencere verir ve 1R hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.pencere == 2 and B.varsayilan.seviye == "orb" and B.varsayilan.hedef == "1R" and B.varsayilan.stop_turu == "sert" }} Fade'in ders kitabı hedefi kısadır: kural, kırılımın aksine,
hareketin sürmesini değil geri gelmesini bekler. Daha uzak hedefler (2R, gün sonu) ızgarada ayrıca ölçülüyor.

### Örnekler

{{! sekil ornek "Örnek günler — Sahte ORB" }}

{{! ornek }}

Figürde mavi çizgiler açılış aralığıdır; kırmızı stop, aralığın dışındaki gezintinin ucudur.

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

Kırılım dersindeki Londra açılış aralığı kuralıyla birlikte okunmalı: iki kural aynı aralığa zıt bahis yapar.
Biri kaybettiriyorsa öbürünün kazandırması gerekmez — iki kural da maliyet öder, ve geri dönüşü bekleyen kural
yalnız geri dönülen günlerde işlem açar.

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Aralığı işaretle.** Londra 08:00'den ilk mum (TSİ 10:00 ya da 11:00).
2. **Kırılımı gör, girme.** Aralığın dışında kapanış bir sinyal değil, bir hazırlıktır.
3. **Geri dönüşü bekle.** En çok iki mum içinde aralığın içinde kapanış; giriş sonraki dakikada, ters yönde.
4. **Stop gezintinin ucunda, hedef 1R.** Pencere Londra 14:00'te kapanır (TSİ 16:00 ya da 17:00).
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
