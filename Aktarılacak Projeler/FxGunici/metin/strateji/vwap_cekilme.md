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

- **VWAP.** VWAP dönüşündekiyle aynı (çapa FX günü başı ya da Londra 08:00; çapadan sonraki ilk 60 dakika sinyal
  yok).
- **Trend.** Son N mumun hepsi VWAP'ın aynı yanında kapandı (N on iki ya da altı).
- **Sinyal.** Mum VWAP'a değer (yükselişte dibi VWAP'a iner ya da altına geçer) ve trend yanında kapanır (yükselişte
  VWAP'ın üstünde). Trend sürdükçe aynı gün yeni dokunuşlar yeni sinyal verir; aynı anda tek pozisyon.
- **Stop.** Sinyal mumunun karşı ucu (alışta dibi). Sinyal en geç 16:00 New York.

{{! kural }}

Varsayılan VWAP'ı Londra açılışında başlatır, trendi on iki mumla tanımlar ve 2R hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.capa == "londra" and B.varsayilan.n == 12 and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }} On iki on beş
dakikalık mum üç saattir ve çapadan sonraki ilk saat sayılmaz; varsayılanın ilk sinyali en erken Londra 12:00–12:15
mumunda gelebilir.

### Örnekler

{{! sekil ornek "Örnek günler — VWAP geri çekilmesi" }}

{{! ornek }}

Figürdeki mavi çizgi sinyal anındaki VWAP'tır.

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

Bu kural trendin sürmesine bahis yaptığı için 60 dakikalık trend değişkeni (fiyatın 50 mumluk üstel ortalamaya
göre yeri) ayrıca okunmalı: kuralın kendi trend tanımıyla aynı yönü gösterdiği günler ile ters gösterdiği günler.

### Kontrol listesi

1. **Çapa Londra 08:00**; ilk saat sinyal yok.
2. **Trendi say.** On iki mum üst üste VWAP'ın aynı yanında kapanış.
3. **Dokunuşu bekle.** Mum VWAP'a değip trend yanında kapanır; giriş sonraki dakikada.
4. **Stop mumun karşı ucunda, hedef 2R.** Sinyal en geç 16:00 New York.
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
