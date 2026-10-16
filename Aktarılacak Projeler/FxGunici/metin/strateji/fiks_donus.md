### Ne

**WM/R fiksingi**, Londra 16:00'da hesaplanan ve en yaygın kullanılan döviz kuru ölçütlerinden biridir: endeks
fonları, saklama bankaları ve portföy değerlemesi bu kuru kullanır. 15 Şubat 2015'ten bu yana kur, 16:00'ı
ortalayan beş dakikalık pencerenin (15:57:30–16:02:30) işlemlerinden hesaplanır; öncesinde pencere bir dakikaydı.
Fiksingde yürütülmek istenen emirler o pencereye yığılır. Dönüş kuralı fiksinge giden son mumun **tersine** girer: fiksing akışının yarattığı fiyat baskısının fiksingden
sonra geri çekileceğine bahis.

### Piyasa mantığı

Fiksingde dolması istenen emir fiyata duyarsızdır: bir endeks fonu ay sonu ağırlığını o kurdan ayarlamak zorundadır,
fiyatın nerede olduğuna bakmaz. Bu tür akış fiyatı geçici olarak iter; akış bittiğinde iten güç de biter.
İki akademik çalışma bu kuralın dayanağıdır. Evans (2018) 21 paritede on yıllık veride fiksing çevresindeki fiyat
değişimlerinin olağandışı oynak olduğunu ve ardışık değişimlerin eksi ilintili olduğunu — yani hareketlerin geri
dönme eğiliminde olduğunu — buldu. Melvin ve Prins (2015) ay sonu fiksinginden önce kurların, uluslararası hisse
portföylerinin kur korumasını yeniden ayarladığı yönde hareket ettiğini ve bu yönün ayın hisse getirilerinden
tahmin edilebildiğini gösterdi. Dönüş kuralı ilk gözlemin mekanik bir biçimidir; ikinci gözlemin sinyali (ayın
hisse getirileri) bu derste sınanmıyor. Kuralın yapamadığı şey akışın
yönünü önceden bilmektir: fiksinge giden mumun yönünü akışın yönü sayar.

### Kurallar

- **Sinyal mumu.** Londra 16:00'da kapanan mum (15 dakikalık mumda 15:45–16:00). Mumun yönü (kapanış − açılış)
  akışın yönü sayılır.
- **Giriş.** Sinyal mumunun **tersi** yönde, 16:00 + "gecikme" mum sonra.
- **Çıkış.** "Tutma" mum sonra; stop'suz (ızgarada sert ve kapanış stop'u da var: girişten 1 × ATR uzakta).
- **R birimi.** Stop olmadığı için risk birimi girişteki ATR(14)'tür (aynı zaman dilimi).
- **Günler.** Bütün işlem günleri; ay sonu (ayın son Londra iş günü) ayrıca raporlanır.

{{! kural }}

Varsayılan 15:45–16:00 mumunun tersine 16:00'da girer ve iki mum (30 dakika) sonra çıkar.{{? B.varsayilan.tf == 15 and B.varsayilan.tur == "donus" and B.varsayilan.gecikme_mum == 0 and B.varsayilan.tutma_mum == 2 and B.varsayilan.stop_turu == "yok" }}
Gecikmesiz giriş, fiksing penceresinin henüz kapanmadığı dakikaya (16:00–16:02:30) düşer: bu bilerek seçilmiş
bir saldırganlıktır, ızgarada bir mum gecikmeli giriş de sınanıyor.

### Örnekler

{{! sekil ornek "Örnek günler — Fiksing dönüşü" }}

{{! ornek }}

Noktalı mavi çizgiler fiksinge giden sinyal mumunun tepesi ve dibi, mavi bant o mumun kendisidir. Kuralın stop'u olmadığı için figürde stop çizgisi yoktur; R birimi girişteki ATR'dir. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir.

### Sonuçlar

{{! sonuclar }}

### Ay sonu

Ön kayıt fiksing kurallarının ay sonunda ayrıca raporlanmasını istedi: ay sonu, endeks yeniden dengelemesinin
fiksinge en yoğun akışı taşıdığı gündür. Aynı kural, aynı işlemler; ay sonu için ayrı parametre seçilmedi.

{{! ay_sonu }}

_Önceden kayıtlı varsayılan, net R; her parite iki satır: bütün dönem ve örneklem dışı (2024 →). Fark p: ay
sonu ile öbür günlerin ortalama farkı, Welch t (iki yönlü)._

Ay sonu yılda on iki gündür: EUR/USD'de bütün dönemde {{ E.varsayilan.ay_sonu.ay_sonu.tum.n | n }}, örneklem dışında
{{ E.varsayilan.ay_sonu.ay_sonu.oos.n | n }} işlem; aralıklar bu yüzden geniştir. {{! ay_sonu_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Saat.** Londra 16:00: TSİ 18:00 (İngiltere yaz saati) ya da 19:00. Fiksing penceresi 15:57:30–16:02:30 Londra.
4. **Son mumu oku.** 15:45–16:00 mumunun yönü.
5. **Ters yönde gir, otuz dakika tut.** Stop yok; R birimi girişteki ATR.
6. **Ay sonunu ayrı düşün.** Ay sonu tablosu ayrı bir kural değil, aynı kuralın bir alt kümesi.
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
