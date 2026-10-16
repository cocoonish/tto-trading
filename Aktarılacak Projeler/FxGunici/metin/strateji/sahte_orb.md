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

Varsayılan iki mumluk pencere verir ve 1R hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.pencere == 2 and B.varsayilan.seviye == "orb" and B.varsayilan.hedef == "1R" and B.varsayilan.stop_turu == "sert" }} Kural, kırılımın aksine, hareketin sürmesini değil geri
gelmesini bekler; daha uzak hedefler (2R, gün sonu) ızgarada ayrıca ölçülüyor.

### Örnekler

{{! sekil ornek "Örnek günler — Sahte ORB" }}

{{! ornek }}

Figürde noktalı mavi çizgiler açılış aralığı, mavi bant aralığa geri dönen sinyal mumudur; kırmızı stop,
aralığın dışındaki gezintinin ucudur. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir: geri dönüş başlıyor, sonra kırılım yeniden başlayıp stop'u alıyor.

### Sonuçlar

{{! sonuclar }}

Kırılım dersindeki Londra açılış aralığı kuralıyla birlikte okunmalı: iki kural aynı aralığa zıt bahis yapar.
Biri kaybettiriyorsa öbürünün kazandırması gerekmez — iki kural da maliyet öder, ve geri dönüşü bekleyen kural
yalnız geri dönülen günlerde işlem açar.

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Aralığı işaretle.** Londra 08:00'den ilk mum (TSİ 10:00 ya da 11:00, İngiltere'nin saatine göre).
4. **Kırılımı gör, girme.** Aralığın dışında kapanış bir sinyal değil, bir hazırlıktır.
5. **Geri dönüşü bekle.** En çok iki mum içinde aralığın içinde kapanış; giriş sonraki dakikada, ters yönde.
6. **Stop gezintinin ucunda, hedef 1R.** Pencere Londra 14:00'te kapanır (TSİ 16:00 ya da 17:00).
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
