### Ne

Önceki FX işlem gününün tepesi (*previous day high*, PDH) ve dibi (*previous day low*, PDL) bugünün en çok
izlenen iki seviyesidir. Kural, fiyat bu seviyelerden birini kapanışla **kestiğinde** kesiş yönünde işleme girer:
dünün tepesinin üstünde kapanış alış, dünün dibinin altında kapanış satış.

### Piyasa mantığı

Dünün uçları, dün o seviyelerde dönen piyasanın bugün yeniden sınayacağı yerlerdir; çoğu masanın stopu ve
kırılım emri de oradadır. Kırılım savunusu: dünün aralığından çıkan fiyat, dünün dengesini terk etmiştir ve
emirler tetiklendikçe hareket hızlanır. Karşı savunu fade dersinin "sahte önceki gün tepe/dip" kuralıdır: aynı
seviyenin aşılıp geri dönülmesi stop toplamanın ta kendisidir. İkisi aynı seviyeyle sınanıyor; hangisinin daha sık
olduğu ölçünün kendisidir.

### Kurallar

- **Seviyeler.** Önceki FX işlem gününün (17:00 → 17:00 New York; gün dönümü
  {{! tsi "" "New York 17:00" }}) orta fiyattan tepesi ve dibi.
- **Pencere.** Gün başından (17:00 New York; {{! tsi "" "New York 17:00" }}) ya da Londra 08:00'den 14:00 New York'a kadar kapanan mumlar
  ({{! tsi "→" "Londra 08:00" "New York 14:00" }}).
- **Sinyal.** Seviyeyi **kesen** ilk kapanış: bir önceki mum kesilen seviyenin berisinde ya da tam seviyede
  kapanmış (öbür seviyenin ötesinde de olabilir), bu mum seviyenin ötesinde kapanmış.
  Fiyat pencere açılmadan seviyenin dışındaysa önce içeri girmesi, sonra yeniden kesmesi gerekir. Gün başına tek
  işlem.
- **Stop.** Sinyal mumunun karşı ucu ya da seviyenin {{= "0,5" }} × ATR(14) içi (alışta tepenin altında, satışta dibin
  üstünde).

{{! kural }}

Varsayılan pencereyi Londra açılışında başlatır, stopu sinyal mumunun karşı ucuna koyar ve 2R hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.baslangic == "londra" and B.varsayilan.stop_kurali == "sinyal_mumu" and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }}
Gece seansının kırılımları bu yüzden dışarıda kalır: Asya'da kesilen bir seviye Londra açılışında yeniden
kesilmedikçe sinyal üretmez.

### Örnekler

{{! sekil ornek "Örnek günler — PDH/PDL" }}

{{! ornek }}

Figürde noktalı mavi çizgiler dünün tepesi ve dibi, mavi bant seviyeyi kesen sinyal mumudur. Sinyal mumunun
boyu riski belirler: seviyeyi uzun bir mumla kesen kırılımın stopu da uzaktır. Kaybeden örnek lehine yarım R'ye
ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir: seviye
kesiliyor, kırılım bir süre ilerliyor ve fiyat dünün aralığına geri dönüyor.

### Sonuçlar

{{! sonuclar }}

### Koşullar

{{! kosullar }}

Dünün aralığının ATR'ye oranı bu kuralın en doğal koşuludur: dar bir dünün uçları bugüne yakındır ve kolay
kesilir, geniş bir dünün uçlarına ancak güçlü bir hareket ulaşır. Bu kuralda "aralık / günlük ATR" ile "önceki gün
aralığı / ATR" aynı ölçüdür ve tek değişken sayılır.{{? E.varsayilan.kosul[2].degisken == "onceki_gun_range_atr" and E.varsayilan.kosul[2].hukum == "esdeger" and G.varsayilan.kosul[2].hukum == "esdeger" and J.varsayilan.kosul[2].hukum == "esdeger" and A.varsayilan.kosul[2].hukum == "esdeger" }} Hangisinin kırılımı taşıdığını ölçüm
söyler: {{! kosul_tek range_atr }}.

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Seviyeleri işaretle.** 17:00 New York'ta kapanan günün tepesi ve dibi (TSİ 00:00, ABD kış saatinde 01:00).
4. **Pencere.** Londra 08:00 (TSİ 10:00 ya da 11:00) → 14:00 New York (TSİ 21:00 ya da 22:00).
5. **Kesişi bekle.** Önceki kapanış içeride, bu kapanış dışarıda; giriş sonraki dakikada.
6. **Stop sinyal mumunun karşı ucunda, hedef 2R.**
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
