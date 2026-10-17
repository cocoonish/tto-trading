### Ne

Fade dersindeki VWAP dönüşünün trend tarafı: fiyat bir süredir VWAP'ın hep aynı yanında kapanıyorsa (yükselişte
üstünde) piyasa o yönde bir trend taşıyor demektir; fiyat VWAP'a **geri çekilip** yine trend yanında kapanırsa
trend yönünde girilir. VWAP burada bir hedef değil, trendin altındaki zemindir.

### Piyasa mantığı

Gün içi trendlerde VWAP, günün ortalama yürütme fiyatıdır: VWAP'ın üstündeki bir piyasada gün içinde alanların
ortalaması kârdadır. Geri çekilme savunusu, VWAP'a dönen fiyatın orada trendi taşıyan alıcılarla
karşılaşacağını söyler — "geri çekilmede al" kuralının mekanik bir biçimi. Kuralın zayıf noktası trendin tanımıdır:
on iki mumun VWAP'ın üstünde kapanması geçmişi tarif eder, trendin süreceğini söylemez; ve VWAP'a dokunuş bazen
geri çekilme değil dönüşün başıdır. FX hacmi üzerine aynı uyarı burada da geçerli: ağırlık kotasyon likiditesidir,
işlem hacmi değil.

### Kurallar

- **VWAP.** VWAP dönüşündekiyle aynı (çapa FX günü başı ya da Londra 08:00; {{! tsi "" "Londra 08:00" }}). Çapadan sonraki ilk 60 dakika sinyal
  yok ve o saatin kapanışları trend sayımına da girmez: sayım ilk saat dolunca başlar.
- **Trend.** Son N mumun hepsi VWAP'ın aynı yanında kapandı (N on iki ya da altı).
- **Sinyal.** Mum VWAP'a değer (yükselişte dibi VWAP'a iner ya da altına geçer) ve trend yanında kapanır (yükselişte
  VWAP'ın üstünde). Trend sürdükçe aynı gün yeni dokunuşlar yeni sinyal verir; aynı anda tek pozisyon.
- **Stop.** Sinyal mumunun karşı ucu (alışta dibi). Sinyal en geç 16:00 New York ({{! tsi "" "New York 16:00" }}).
- **Hedef.** 1R, 2R ya da zaman ({{ ON.genel.desen_zaman_mum | n }} mum).

{{! kural }}

Varsayılan VWAP'ı Londra açılışında başlatır, trendi on iki mumla tanımlar ve 2R hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.capa == "londra" and B.varsayilan.n == 12 and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }} On iki on beş
dakikalık mum üç saattir ve çapadan sonraki ilk saat sayılmaz; varsayılanın ilk sinyali en erken Londra 12:00–12:15
mumunda gelebilir.

Aynı sayım 60 dakikalık mumda Londra çapasıyla on iki mumu sığdırmaz: sayılabilen ilk mum Londra 09:00–10:00,
on ikincisi 20:00–21:00'dir; sinyal mumu en erken 21:00–22:00 olur, oysa sinyal en geç 16:00 New York'ta (Londra
21:00, saat geçişi haftalarında 20:00) kapanmalıdır. Izgaranın {{ B.kombinasyon | n }} kombinasyonundan bu altısı
(60 dakika, Londra çapası, on iki mum; üç hedef ve iki stop türüyle) dört paritede de hiç işlem açmaz; zaman dilimi
kıyasında 60 dakikalık satırın boş olması bu yüzdendir.{{? B.kombinasyon == 72 and E.izgara_ozet.islem_acan == 66 and G.izgara_ozet.islem_acan == 66 and J.izgara_ozet.islem_acan == 66 and A.izgara_ozet.islem_acan == 66 }}

### Örnekler

{{! sekil ornek "Örnek günler — VWAP geri çekilmesi" }}

{{! ornek }}

Figürdeki noktalı mavi çizgi sinyal anındaki VWAP (sinyal mumundan başlar; VWAP gün içinde yürür), mavi bant VWAP'a değip trend yanında kapanan sinyal mumudur.
Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip
zararla kapanan işlemdir: trend bir süre devam ediyor, sonra VWAP'a dokunuş dönüşün başı çıkıyor.

### Sonuçlar

{{! sonuclar }}

**Ön kaydın harfiyle.** Ön kayıt yalnız sinyali yasaklar ("çapadan sonraki ilk 60 dakika sinyal yok").
Sonuçlardan önce yazılan kod o saatin kapanışlarını trend sayımına da almaz (yukarıda); harfiyle okunursa sayım
çapadan başlar. O okumada 60 dakikalık Londra kombinasyonları da işlem açar: on iki mum Londra 08:00–20:00, sinyal
mumu 20:00–21:00'dir ve kapanışı 16:00 New York'a denk gelir (saat geçişi haftalarında gelmez).{{? E.yorum.bos_kombinasyon == 0 and G.yorum.bos_kombinasyon == 0 and J.yorum.bos_kombinasyon == 0 and A.yorum.bos_kombinasyon == 0 }}
Hüküm sonuçlardan önce yazılan okumayla verilir; harfin okuması aynı koşuda ayrıca ölçüldü. {{! yorum_cumle }}

{{! yorum }}

### Koşullar

{{! kosullar }}

Bu kural trendin sürmesine bahis yaptığı için 60 dakikalık trend değişkeni (fiyatın 50 mumluk üstel ortalamaya göre
yeri) onun en doğal koşuludur: kuralın kendi trend tanımıyla aynı yönü gösterdiği günler ile ters gösterdiği günler.
Ölçüm: {{! kosul_tek trend60 }}.

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Çapa Londra 08:00** (TSİ 10:00 ya da 11:00); ilk saat sinyal yok.
4. **Trendi say.** On iki mum üst üste VWAP'ın aynı yanında kapanış.
5. **Dokunuşu bekle.** Mum VWAP'a değip trend yanında kapanır; giriş sonraki dakikada.
6. **Stop mumun karşı ucunda, hedef 2R.** Sinyal en geç 16:00 New York (TSİ 23:00 ya da 00:00).
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
