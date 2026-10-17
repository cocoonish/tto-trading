---
title: 'FX Gün İçi Stratejiler 8: Metodoloji — Veri, Saat, Yürütme, Ön Kayıt ve Ölçülmeyenler'
description: "Serinin bütün sayılarının nasıl üretildiği: Dukascopy 1 dakikalık bid/ask arşivinin indirilmesi ve denetimi, saat ve yaz saati kuralları, yürütme mekaniği (giriş, stop, hedef, gün sonu, maliyet), örneklem bölmesi, sonuçtan önce yazılan ön kayıt ve sonradan yapılan her şey, seçim ve sağlamlık ölçüleri, haber takviminin kaynakları ve dışarıda kalan olaylar, ve bu serinin ölçmediği şeylerin listesi."
pubDate: 2026-10-16
tags: ['fx', 'gun-ici', 'backtest', 'metodoloji', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · BLS, Fed, ECB, BoE resmî kaynakları · önceden kayıt'
ozet: "Bir backtest'in sonucu, nasıl ölçüldüğü kadar güvenilirdir. Bu ders serinin makinesini açar: hangi fiyat, hangi saat, hangi dolum kuralı; ne önceden yazıldı, ne sonradan yapıldı; ve hangi soruların hiç sorulmadığı."
seviye: 'ileri'
onkosul:
  - fx-gunici-giris
---

Önceki yedi ders sonuçları anlattı. Bu ders sonuçların nasıl üretildiğini anlatır ve iki amaca hizmet eder. Birincisi
denetlenebilirlik: bir okurun bir sayıya itiraz edebilmesi için o sayının hangi fiyattan, hangi saatte ve hangi
kuralla ölçüldüğünü bilmesi gerekir. İkincisi dürüstlük: bir backtest'in en sık kusuru bir kuralın sonuca bakılarak
seçilmesi ya da değiştirilmesidir. Burada neyin sonuçtan önce yazıldığı, neyin sonradan yapıldığı ve gerekçesi
adıyla durur.

## Veri: kaynak, indirme, arşiv

Fiyat verisi Dukascopy'nin herkese açık beslemesinden gelir: her parite ve her UTC günü için iki dosya, 1 dakikalık
**bid** ve **ask** mumları. İki taraf ayrı indirildiği için her dakikanın gerçek makası bilinir: alış ask'tan, satış
bid'den yürütülür ve makas maliyete ayrıca eklenmez, fiyatın kendisindedir.

Strateji mumları (5, 15, 60 dakika) 1 dakikalık orta fiyattan kurulur ve UTC saatine çıpalıdır. 5 ve 15 dakikalık
mumlarda seans açılışları (Londra 08:00, New York 08:00 ve 09:30; {{! tsi "·" "Londra 08:00" "New York 08:00" "New York 09:30" }}) her zaman bir mumun başına düşer. 60 dakikalık
mumlarda her kural kendi çıpasını kullanır: saatlik mum saat başında başlar, New York ilk dengesi — 09:30 kuralında
ise :30'da. Saat başı çıpanın New York 08:30 verileriyle ({{! tsi "" "New York 08:30" }}) ilişkisi aşağıda, ön kaydın
yorum gerektiren yerleri arasında.
Haber kurallarının mumları her zaman olay dakikasından başlar: ilk haber mumu olay dakikası ile bir mum
sonrası arasıdır.

Arşiv dört paritede örneklemin bütün iş günlerini kapsar. UTC cumartesisi arşivde yoktur: FX cuma 17:00'de (New
York; {{! tsi "" "New York 17:00" }}) kapanır, pazar aynı saatte açılır ve UTC cumartesisinin bütün dakikaları kapalı piyasadır (ilk iki yılın bütün
cumartesileri kaynakta boştur).

{{! arsiv_ozet }}

{% if T.eksik_birim %}_{{ T.eksik_birim | n }} parite-yılda {{ T.inmeyen_gun | n }} gün arşivde yok: o günler ölçümde
yoktur ve sonuçların kapsamı bu kadar eksiktir._{% else %}_Dört paritede örneklemin her günü arşivde._{% endif %}

Veri denetimi giriş dersinde (kapsam, tatil, makas, sıçrama adayı ve Dukascopy'nin kendi saatlik mumlarıyla çapraz
sınama). Denetim veriyi **değiştirmez**: sıçrama adayları sayılır ve listelenir, düzeltilmez ya da atılmaz.

**Tatil** fiyattan değil takvimden gelir: 25 Aralık ve 1 Ocak hafta içine düştüğünde stratejiler o gün işlem açmaz.
Günün kapsamından okunan bir tatil bayrağı gün bitmeden bilinemezdi; takvim önceden bilinir. Arşivde kapsamı {{! kalite_esik tatil in }}
altında kalan işlem günleri dört paritede de tam bu günlerdir ({{ O.veri.tatil_uyum.EURUSD.takvim | n }} gün).{{? O.veri.tatil_uyum.EURUSD.ayni and O.veri.tatil_uyum.GBPUSD.ayni and O.veri.tatil_uyum.USDJPY.ayni and O.veri.tatil_uyum.AUDUSD.ayni }}
Örneklemin iki kenarında baştan sona kapsanmayan işlem günü de işlem açmaz.

## Saat

Bütün zaman damgaları UTC olarak saklanır; yerel saatler (Londra, New York, Frankfurt) IANA saat dilimi tablosundan
çevrilir ve hiçbir saat farkı elle yazılmaz. FX günü New York 17:00'de ({{! tsi "" "New York 17:00" }}) başlar ve biter. İşlem saatleri okura TSİ
olarak verilir (UTC+3, yaz saati yok); olay saatleri ayrıca kendi yerel saatleriyle. Yaz saati geçişleri her yıl
için elle yazılmış bir listeye karşı sınanır; Londra ile New York'un farklı haftalarda saat değiştirdiği ara dönemler
giriş dersindeki tablodadır.

Saatin doğru işlendiğinin bağımsız bir sınaması da var: ABD tarım dışı istihdam verisi 08:30 New York'ta
({{! tsi "" "New York 08:30" }}) yayımlanır, yani damgalar doğruysa yayım günlerinde 1 dakikalık mum aralığının ortalaması yazın da kışın da tam o
dakikada zirve yapmalıdır. Sınama yalnız günü takvimden alır, dakikayı fiyattan ölçer. {% if O.veri.kalite.EURUSD.damga.yaz.zirve_dk == 0 and O.veri.kalite.EURUSD.damga.kis.zirve_dk == 0 %}EUR/USD'de
yapıyor: yaz saatindeki {{ O.veri.kalite.EURUSD.damga.yaz.gun | n }} günün de kış saatindeki
{{ O.veri.kalite.EURUSD.damga.kis.gun | n }} günün de ortalama aralığı 08:30 dakikasında en yüksek. Bir saatlik yaz
saati hatası zirveyi altmış dakika öteye taşırdı.{% else %}EUR/USD'de zirve yaz saatinde
{{ O.veri.kalite.EURUSD.damga.yaz.zirve_dk | n }}, kış saatinde {{ O.veri.kalite.EURUSD.damga.kis.zirve_dk | n }}
dakika kayık: damgalar sınanmalı.{% endif %}

Ay sonu, ayın son **Londra iş günüdür** (WM/R fiksingi Londra'da hesaplanır). İngiltere ve Galler resmî tatilleri
kuralla hesaplanır (Paskalya'ya bağlı günler, mayıs ve ağustos tatilleri, kraliyet etkinlikleri için konan özel
günler adıyla) ve elle yazılmış bir listeye karşı sınanır.

## Yürütme mekaniği

- **Sinyal ve giriş.** Sinyal, strateji mumunun orta fiyat kapanışıyla verilir. Kural kendi giriş saatini
  tanımlamıyorsa giriş, bir sonraki mumun ilk dakikasının açılışındadır (alış ask'tan, satış bid'den); gün içi
  momentum 12:00 New York'ta ({{! tsi "" "New York 12:00" }}), fiksing dönüşü "gecikme" parametresi kadar mum sonra girer. Sinyalin görüldüğü
  fiyattan girilmez.
- **Alınmayan emir.** Stop seviyesi taşıyan emirde giriş tarafının kaymasız açılışı stopun ötesinde ya da tam
  üstündeyse, seviye hedefi yürütülen girişin (makas ve kayma dahil) gerisinde ya da tam üstündeyse, ya da giriş gün
  sonunda veya sonrasındaysa emir alınmaz. Stopun ölçütü ham açılıştır, hedefinki yürütülen fiyattır; hedef ölçütü bu yüzden
  kaymaya bağlıdır ve maliyet merdiveninin her basamağında atılan emir sayısı değişebilir. Alınmayan emirlerin
  sayısı strateji derslerinde, kural kural.
- **Stop.** Sert stop emir tarafında dakika dakika izlenir; fiyat stopun ötesinde açılırsa (boşluk) dolum açılış
  fiyatındandır. Kapanış stopu, mumun orta fiyat kapanışı stopun ötesindeyse bir sonraki mumun açılışında kapatır.
  Varsayılanı stopsuz olan üç kuralın (fiksing momentumu, fiksing dönüşü ve gün içi momentum) stoplu
  kombinasyonlarında stop, yürütülen giriş fiyatından 1·ATR uzağa konur.{{? ON.fiks.varsayilan_momentum.stop_turu == "yok" and ON.fiks.varsayilan_donus.stop_turu == "yok" and ON.momentum.varsayilan.stop_turu == "yok" }}
- **Hedef.** Limit emirdir ve kaymaz. Stop ile hedef aynı strateji mumunun içinde değmişse sıra 1 dakikalık
  veriyle çözülür; aynı dakikada ikisi birden değmişse **stop** sayılır (tutucu varsayım). Zaman hedefi girişten
  {{ ON.genel.desen_zaman_mum | n }} mum sonra{% if ON.haber.zaman_mum != ON.genel.desen_zaman_mum %} (haber kurallarında {{ ON.haber.zaman_mum | n }} mum){% endif %}, o mumun açılışında
  piyasa emriyle çıkar; stop o ana kadar açıktır, çıkış gün sonunu aşmaz.
- **Gün sonu ve tek pozisyon.** Bütün pozisyonlar en geç {{ K.gun_sonu_et | t }} New York'ta ({{! gun_sonu_tsi }})
  kapanır; gece ve hafta sonu pozisyon taşınmaz. Aynı anda parite başına tek pozisyon vardır; açık pozisyon varken gelen sinyal atlanır.
  Haber kurallarında kural bütün olaylara birlikte uygulanır: bir olayın pozisyonu açıkken gelen başka bir olayın
  sinyali (ör. aynı gün FOMC kararından sonra basın toplantısının sinyali) alınmaz.
- **Maliyet.** Makas gerçek bid/ask'tadır. Üstüne her piyasa dolumuna (giriş, zaman çıkışı, stop) temel senaryoda
  {{ K.temel_kayma_pip | s1 }} pip kayma eklenir; haber penceresinde (olay dakikasına göre
  {{ K.haber_pencere_dk[0] | n }} ile +{{ K.haber_pencere_dk[1] | n }} dakika arası) kayma {{ K.haber_kayma_pip | s1 }}
  pip daha büyüktür. Maliyet merdiveni aynı kuralı dört kaymayla yeniden koşar (dolum başına
  {{ K.kayma_pip[0] | s1 }} · {{ K.kayma_pip[1] | s1 }} · {{ K.kayma_pip[2] | s1 }} · {{ K.kayma_pip[3] | s1 }} pip);
  haber penceresinin ek kayması her basamakta aynı kalır. Ayrıca bir **yalnız makas** koşusu var: kayma da haber
  kayması da sıfır, maliyet yalnız gerçek bid/ask. Merdiven aynı işlemlerin değil aynı kuralın yeniden koşusudur:
  kayma dolum fiyatını değiştirir, R katı hedefin seviyesi ve stopa ya da hedefe değilen dakika onunla değişebilir,
  tek pozisyon kuralı yüzünden alınan işlemler de.
- **R.** Bir işlemin R'si net sonucunun planlanan riske oranıdır: yürütülen giriş fiyatından stop seviyesine uzaklık.
  Stopsuz kurallarda R bir ölçek birimidir: fiksingde kuralın kendi mumlarından girişteki ATR(14), gün içi
  momentumda girişteki 60 dakikalık ATR(14).
- **MFE ve MAE.** İşlemin lehine ve aleyhine en büyük hareketi: girişten çıkışa, dakika dakika, yürütülebilir
  fiyatla (alışta bid, satışta ask), R cinsinden. Hedefin dolduğu dakikada dakikanın içindeki sıra bilinmediği için o
  dakikanın ters ucu MAE'ye girer; gerçekleşen sonuç her zaman ikisinin arasındadır. Örnek günlerin "kaybeden" ve
  "tuzak" tanımları bu ölçüden okunur.

**İleriye bakma sınaması.** Bir kural geleceğe bakıyorsa (bugünün henüz kapanmamış tepesini, sonraki mumun fiyatını
ya da günün kapanışını kullanıyorsa) bunu yakalamanın yolu veriyi bir anda kesmektir. Sınama gerçek arşivde değil,
gerçek seans yapısıyla üretilmiş {{ K.ileri_bakma.sentetik_gun | n }} iş günlük sentetik bir 1 dakikalık seride (haber
olaylarıyla birlikte) yapılır ve her kesimde iki koşu ister: bir kez veri kesim anında kesilir, bir kez o andan sonraki
bütün fiyatlar başka bir yürüyüşle değiştirilir. İki türlü kesim var.

- **Sinyale çıpalı kesim.** Her kuralın varsayılanında, sentetik serideki sinyallerden {{ K.ileri_bakma.cipa_sayisi | n }}
  tanesinin karar anı çıpa olur ve veri iki yerde kesilir: kararın hemen ardından (giriş dakikası veride, sinyal
  mumundan sonraki mum henüz tamamlanmamış) ve bir mum sonra. Kararı kesimden geç olmayan bütün sinyaller üç koşuda
  birebir aynı olmalıdır ve çıpanın kendisi kıyaslananların içindedir: kesim gününde en az bir sinyal kıyaslanır.
  Bir ya da iki mum sonrasının fiyatına bakan bir kural burada düşer; sınamanın kendisi de bunu sınar (aralık
  kırılımının kararı bir ve iki mum sonraki kapanıştan verilecek biçimde bozulunca çıpalı kesim iki çıpada da
  düşer).{{? K.ileri_bakma.cipa_sayisi == 2 and len(K.ileri_bakma.cipa_ek_mum) == 2 }}
- **Sabit kesim.** {{ K.ileri_bakma.kesim_n | n }} kesim anı: New York sabahı, Londra sabahı, Londra açılışından önce ve
  UTC gece yarısından hemen sonra.{{? K.ileri_bakma.kesim_n == 4 and K.ileri_bakma.kesim[0].an == "new_york_sabahi" and K.ileri_bakma.kesim[1].an == "londra_sabahi" and K.ileri_bakma.kesim[2].an == "londra_acilis_oncesi" and K.ileri_bakma.kesim[3].an == "utc_gece_yarisi_sonrasi" }}
  Kesim günün ortasına da düşer, çünkü günün bütününden kurulan bir alan (ör. kapsamdan okunan bir tatil bayrağı)
  yalnız böyle bir kesimde sinyal siler. Her kuralda ilk kesimde varsayılan ve ızgaradan rastgele seçilmiş
  {{ K.ileri_bakma.ornek_ilk_rastgele | n }} kombinasyon, öbür kesimlerde varsayılan ve
  {{ K.ileri_bakma.ornek_oteki_rastgele | n }} kombinasyon koşulur. Kararı kesimden en az iki mum önce verilen
  sinyaller üç koşuda birebir aynı olmalıdır; varsayılanın kesimden önce açılmış işlemlerinin giriş fiyatı, stopu ve
  R'si de geleceğin değişmesinden etkilenmemelidir. İki mumluk pay bu kesimi bir iki mumluk ileri bakışa kör yapar; o
  sızıntıyı çıpalı kesim yakalar.
- **Koşul değişkenleri.** Koşul analizinin kovaları da girişin anında bilinen bilgiden kurulmalıdır. Önceden
  duyurulmayan bir karar (FOMC'nin olağanüstü toplantıları) ancak olduğu anda bilinir: sınama sentetik seride günün
  ortasına böyle bir olay koyar ve kararı olaydan önce verilen sinyallerin hiçbir koşul değişkeninin değişmediğini
  ister. Aynı olay planlanmış olsaydı günü baştan işaretlerdi; sınama bunu da ister, yani değişkenin takvimi gerçekten
  okuduğunu gösterir.{{? "test_kosul_degiskeni_olaganustu_olayi_gormez" in K.ileri_bakma.sinama }}

Yorum duyarlılığının harf okumaları da (aşağıda) iki kesimden geçer. Sınama gerçek fiyatla yapılmadığı için bir kuralın
kazancı hakkında bir şey söylemez. Kapsamı da sınırlıdır: bir sızıntının görünmesi için onu tetikleyen durumun sentetik
seride oluşması gerekir; görünmeyen bir sızıntının olmadığını kanıtlamaz.

## Örneklem, seçim ve sağlamlık

Örneklem içi {{ K.baslangic | tarih }} → {{ K.ic_bitis | tarih }}, örneklem dışı {{ K.dis_baslangic | tarih }} →
{{ K.bitis | tarih }}. Her kural iki biçimde ölçülür. **Varsayılan**, veriye bakmadan seçilmiş ders kitabı hâlidir;
hükmü o verir. **Seçilen**, parametre ızgarasından yalnız örneklem içinde, günlük R serisinin yıllık Sharpe'ıyla ve en
az {{ K.secim.asgari_islem | n }} işlem (haber kurallarında {{ K.secim.asgari_islem_haber | n }}) şartıyla seçilen
kombinasyondur; örneklem dışında ayrıca sınanır. Seçim {{ T.bilesim | n }} bileşimin {{ T.secilen_n | n }}
tanesinde kurulabildi{% if T.secimsiz %}; öbür {{ T.secimsiz | n }} bileşimde ızgaranın hiçbir kombinasyonu örneklem
içinde asgari işlem sayısına ulaşmadı: {{! secimsiz "n" }}. O bileşimlerde hüküm yalnız varsayılandan verilir{% endif %}. Günlük R serisi dönemin bütün tatil dışı FX işlem günlerini taşır
ve işlem açılmayan gün sıfırdır (ön kaydın tanımı); Sharpe ×√252 ile yıllıklandırılır. {{ T.birim | n }} kuralın ızgaralarında toplam
{{ T.kombinasyon | n }} kombinasyon var.

- **Deflated Sharpe** (Bailey ve López de Prado, 2014): ızgaradan seçilen en iyi kombinasyonun günlük Sharpe'ı, o
  ızgaranın deneme sayısıyla şansla beklenen en yüksek Sharpe'a karşı sınanır. Beklenen en yüksek Sharpe iki biçimde
  kurulur: yalnız örnekleme gürültüsünden (**gürültü eşiği**: her deneme sıfır kenarlı ve öbürlerinden bağımsız
  olsaydı tek bir günlük Sharpe'ın varyansı 1/(T−1), T gün sayısı) ve denemelerin kendi Sharpe'larının yayılımından (**yayılım eşiği**,
  Bailey ve López de Prado'nun önerisi). Seçilen Sharpe'ın eşiği aşma olasılığı %95 ya da üstüyse sınama geçer.
  Seçim tablolarındaki "DSR" yayılım eşiğine göredir; iki eşiğin ilişkisi aşağıda.
- **Yürüyen pencere:** {{ K.saglamlik.walk_forward_ilk_test_yili | t }}'den itibaren her yıl için yalnız önceki
  yılların verisiyle seçim yapılır ve o yılda sınanır. Seçimin asgari işlem şartı, örneklem içi şartın yıl başına
  payıdır; şartı sağlayan kombinasyonu olmayan yıl sınanmaz ve sınanan yıllar adıyla yazılır.
- **Aralık:** işlem başına net R'nin %95 aralığı {{ K.hukum_kurali.bootstrap_tekrar | n }} tekrarlı bootstrap'le; en
  az {{ K.uygulama_esik.bootstrap | n }} işlem ister. Parite başına aralık işlemleri bağımsız örnekler (ön kaydın
  okuması; aynı günün işlemleriyle kümeli duyarlılığı aşağıda). Dört paritenin havuzunda aynı günün bütün
  paritelerdeki işlemleri birlikte örneklenir (gün kümeli bootstrap): aynı gün dört paritede açılan işlemler aynı
  haberi ve aynı dolar hareketini taşır, bağımsız sayılsalardı aralık olduğundan dar çıkardı.
- **Rastgele yön:** alınan her işlemin aynası kurulur: aynı giriş dakikası, ters yön, aynı risk uzaklığı (stop ve hedef
  ters yönde girişe aynı uzaklıkta) ve aynı planlı çıkış (zaman ya da gün sonu çıkışı aynı dakikada). Her tekrarda
  her işlem için gerçeği ya da aynası yazı turayla seçilir ve ortalama alınır; {{ K.hukum_kurali.rastgele_tekrar | n }}
  tekrar. Kuralın yüzdeliği, gerçek ortalamanın altında kalan karışımların payıdır. En az
  {{ K.uygulama_esik.rastgele | n }} işlem ister.
- **Hüküm:** örneklem dışı (2024 →) net ortalama artı, aralığın alt ucu sıfırın üstünde ve rastgele yön dağılımında
  {{ K.hukum_kurali.rastgele_esik_yuzdelik | n }}. yüzdelik ya da üstü ise **çalışıyor**; ortalama artı ama öbür
  şartlardan biri tutmuyorsa ya da işlem sayısı o şartı kurmaya yetmiyorsa **zayıf**; ortalama sıfır ya da eksiyse
  **çalışmıyor**; örneklem dışında hiç işlem yoksa **ölçülemedi**. {{ K.uygulama_esik.az_islem | n }}'den{{? K.uygulama_esik.az_islem == 20 }} az işlemli
  sonuç **az işlem** diye işaretlenir; işaret hükmü değiştirmez. Brüt sonucun aralığı sıfırın üstünde ama net sonuç
  sıfır ya da eksiyse ayrıca **maliyet** bayrağı.
- **Koşullar:** on dört değişken{{? len(K.kosul.degiskenler) == 14 }}; sürekli değişkenlerde kova sınırları (terciller)
  yalnız örneklem içinden kurulur ve örneklem dışına taşınır. Koşulsuz ortalama değişkenin tanımlı olduğu
  işlemlerden alınır. Örneklem içinde koşulsuz ortalamanın üstündeki, en az {{ K.kosul.asgari_kova_islem | n }}
  işlemli kovalar seçilir; seçilen kovaların ortalaması örneklem dışında artı kalır, seçilmeyen kovaların birlikte
  ortalamasını (tamamlayanı) aşar ve en az {{ K.uygulama_esik.kosul_oos | n }} işlemle ölçülürse "tuttu". Seçilen
  kova, seçilmeyenlerden birinin altında kalsa da tutabilir. Hiçbir kova seçilmediyse ya da bütün kovalar
  seçildiyse sınama kurulamaz ve adıyla yazılır. Bütün işlemlerde aynı değeri taşıyan iki değişken tek sayılır.
  Kontrol listesine aday olarak yalnız en az iki paritede aynı kova seçimiyle tutan koşul girer.

### Ön kayıt

Kuralların, ızgaraların, kural ailelerinin varsayılanlarının ve hüküm kuralının şartlarının hepsi tek bir ön kayıt
dosyasında, hiçbir backtest sonucu görülmeden yazıldı ve kaydedildi. Ön kayıtta olmayan iki şey var: New York ilk
denge kırılımının 08:00 sürümünün varsayılanı (ön kayıtlı 09:30 sürümününkinden yalnız başlangıç saati değiştirilerek
türetildi; iki başlangıç {{! tsi "ve" "New York 08:00" "New York 09:30" }}) ve hüküm
kuralının şartlarının asgari işlem sayıları. İkisi de, ölçümün ön kaydın harfinden ayrıldığı yerler de
(varsayılanın hükmünün penceresi dahil: ön kayıt bütün dönemi ister, bu seri 2024 →'yü birincil sayar) aşağıda
adıyla durur.{{? ON.nyib.varsayilan.baslangic_et == "09:30" }} Dosyanın bütün geçmişi, ilk sonuçların
görüldüğü anla birlikte:

{{! onkayit_tablo }}

[Ön kaydın tam metni](/arastirma/fx-gunici/onkayit.toml) sayfayla birlikte yayımlanır; dosyanın SHA-256 özü
`{{ K.onkayit_ozu | t }}`. İkinci kayıt haber devam tablosunu ekledi: o anda fiyat ve takvim verisinin ilk iki
parçası (EUR/USD 2018'in ilk fiyat dosyası ve FOMC duyurularının ham sayfaları) indirilmişti ama hiçbiri okunmamış,
takvim ayrıştırılmamış ve hiçbir haber olayı ölçülmemişti. Sonraki {{ K.onkayit_gecmis_ozet.sonra | n }} kayıt ilk
sonuçlardan sonra yazıldı ve yalnız açıklama notudur: kuralların, ızgaraların, varsayılanların ve hüküm kuralının
içeriği ikinci kayıttakiyle birebir aynıdır.{{? K.onkayit_gecmis_ozet.once == 2 and K.onkayit_gecmis_ozet.sonra_icerik == 0 and len(K.onkayit_gecmisi[1].degisen_bolum) == 1 and K.onkayit_gecmisi[1].degisen_bolum[0] == "haber_devam" }} Bu notlar sonuçlardan sonra değişen uygulama
kurallarını ve ön kaydın harfinden ayrılan okumaları sayar; her birinin önceki hâli, zamanı ve ölçülmüş etkisi
aşağıdadır.

### Ön kayıttan sapmalar

Ölçüm dört yerde ön kaydın harfinden ayrılır. Biri ilk sonuçlardan sonra kararlaştırıldı, üçü ilk sonuçlardan önce
sabitlenmiş uygulamadadır.

- **Hüküm penceresi** (karar ilk sonuçlardan sonra, {{! karsi_olgu_zaman hukum_penceresi }}). Ön kayıt varsayılan
  için bütün dönemi örneklem dışı sayar ve hükmü oradan ister, çünkü varsayılan hiçbir veriye bakmadan yazıldı. Bu
  seri iki sonucu (varsayılan ve seçilen) aynı veride kıyaslamak için birincil hükmü 2024 → penceresinden verir;
  ön kaydın istediği bütün dönem hükmü her tabloda yan sütunda durur. Seçimin etkisi:
  {{! hukum_secim_etkisi }}; iki pencerede de "çalışıyor" hükmü alan bileşim yok{{? T.hukum_say.oos.calisiyor == 0 and T.hukum_say.tum.calisiyor == 0 and T.hukum_say.oos.olculemedi == 0 and T.hukum_say.tum.olculemedi == 0 }}. İki pencerenin hükmü {{! pencere_ayrisan }}.
- **Ailelerin kurallara bölünmesi ve deneme sayısı** (ilk sonuçlardan önce sabitlenmiş uygulama). Ön kayıt {{ K.aile_n | n }} kural ailesi kaydetti
  ve seçimi de deflated Sharpe'ın deneme sayısını da aile başına ister. Ölçüm dört aileyi kurallara böler (New York
  ilk dengesi başlangıç saatine, başarısız kırılım seviyesine, pivot ve fiksing türüne) ve ikisini de kural başına
  kurar: parite başına {{ K.aile_n | n }} yerine {{ T.birim | n }} seçim yapılır.{{? len(K.bolunen_aile) == 4 and K.bolunen_aile[0] == "fiks" and K.bolunen_aile[1] == "nyib" and K.bolunen_aile[2] == "pivot" and K.bolunen_aile[3] == "sahte" }}
  New York ilk dengesinin ön kaydı tek varsayılan taşır (başlangıç 09:30 New York; {{! tsi "" "New York 09:30" }});
  08:00 sürümünün ({{! tsi "" "New York 08:00" }}) varsayılanı ondan yalnız başlangıç saati değiştirilerek türetildi
  ve ön kayıtta yoktur.{{? ON.nyib.varsayilan.baslangic_et == "09:30" }}
  Pivot ve fiksingin ön kaydı her tür için ayrı varsayılan taşır.{{? ON.pivot.varsayilan_donus and ON.pivot.varsayilan_kirilim and ON.fiks.varsayilan_momentum and ON.fiks.varsayilan_donus }}
  Başarısız kırılımın ön kayıtlı varsayılanı seviye belirtmez; üç kural aynı varsayılanı kendi seviyesiyle
  kullanır.{{? ON.sahte.varsayilan.seviye == None }} Bölünmenin yönü tutucu değildir: daha az deneme şansla beklenen
  en yüksek Sharpe'ı, yani deflated Sharpe'ın eşiğini düşürür. {{! aile_dsr }}
- **Altı kuralın beş yerde dar ya da farklı okunması** (ilk sonuçlardan önce sabitlenmiş uygulama). Ölçüm altı
  kuralı beş yerde ön kaydın harfinden dar ya da farklı okur ve o okuma korunur:
  - VWAP kurallarında çapadan sonraki ilk 60 dakika: ölçüm kuralın durumunu da sıfırlar, yani trend sayacı ve bant
    dışı gezinti çapadan bir saat sonra başlar; harf yalnız sinyali yasaklar.
  - VWAP dönüşünde bandın içine dönüş: ölçüm yalnız çıkılan bandı sorar, üst bandın dışından dönen kapanış alt
    bandın da altında olsa sinyal verir; harf ("bandın içine kapanan ilk mum") kapanışın iki bandın arasında
    olmasını ister ve karşı bandın ötesindeki kapanışı o yanda yeni bir gezinti sayar.
  - Pivot kırılımı: ölçüm R1'i yalnız yukarı, S1'i yalnız aşağı kesişte sayar; harf her seviyenin günün ilk
    kesişini iki yönde de sayar.
  - Başarısız kırılımın kırılım mumu: ölçüm seviyeyi kesen mumu sayar; harf pencerenin ilk mumu dışarıda kapanırsa
    da sayar, yani seviye pencereden önce aşıldıysa açılıştaki geri alınış da kırılımdır. Kesiş tanımı ön kaydın
    "pencere" parametresine anlam verir: dışarıda her kapanış kırılım sayılsaydı içeride kapanan ilk mum neredeyse
    her zaman dışarıda kapanmış bir mumun hemen ardından gelirdi ve bir mumluk pencere onu zaten yakalardı.
  - Başarısız kırılımın geri dönüşü: ölçüm yalnız kırılan kenarı sorar, yukarı kırılımdan sonra alt kenarın da
    altında kapanan mum dönüş mumu sayılır ve satış verir; harf ("yeniden içeride kapanırsa") kapanışın aralığın
    içinde olmasını ister ve karşı kenarın ötesindeki kapanışı ters yönde yeni bir kırılım sayar (haber dersindeki
    N4 başarısız kırılımının kuralı).

  Harfin her okuması her koşuda ayrıca ve tek başına ölçülür (öbür okumalar bu serinin kuralında kalır) ve ilgili
  strateji derslerinde kuralın sonuçlarının yanında durur:

{{! yorum_ozet }}

- **Devam tablosunun etiketleri** (ilk sonuçlardan önce sabitlenmiş uygulama). Ön kaydın terimi "ayrışmıyor"
  her yönü ayrı ayrı sıfıra karşı sınar; tablo onu ölçtüğü şeyle, "kazanan yok" diye yazar. Ön kayıt asgari olay
  sayısına ulaşmayan hücreyi de "ayrışmıyor" sayar; ölçüm o hücreyi "yetersiz örneklem" diye ayrı etiketler. İki
  etiket de "kırılım kazanır" ya da "fade kazanır" değildir; hiçbir hüküm bu yüzden değişmez.

### Sonuçlardan sonra değişen uygulama kuralları

İlk sonuçların görüldüğü an: {{! ilk_sonuc_zaman }}. Koşunun sonuçları ilk kez o anda okundu. Dört paritenin ilk tam koşusu: {{! karsi_olgu_zaman tam_kosu }}.
Aşağıdaki kurallar ilk sonuçlardan sonra değişti; ön kaydın kuralları değişmedi,
değişen ölçümün uygulamasıdır. İşlemleri değiştiren her kuralın etkisi ölçüldü: kural tek başına eski hâline
döndürüldü, bütün koşu yeniden yapıldı ve sonuç bugünküyle bileşim bileşim kıyaslandı (öbür bütün kurallar
bugünkü hâliyle). Sıra hükme yakınlığa göredir.

- **"Ölçülemedi"nin eşiği** ({{! karsi_olgu_zaman olculemedi }}). Önce: örneklem dışında 20'den az işlemi olan
  bileşim ölçülemedi sayılırdı.{{? O.karsi_olgu.olculemedi.esik == 20 }} Bugün: yalnız hiç işlem yoksa; az işlemli sonuç hükmünü taşır ve
  "az işlem" diye işaretlenir (ön kayıt asgari yazmaz). Etkisi: {{! olculemedi_etki }}.
- **Stop seviyeli emirde ham açılış** ({{! karsi_olgu_zaman ham_acilis }}). Önce: yalnız kaymalı dolum sorulurdu;
  giriş tarafının açılışı stopun ötesinde olsa da kayma dolumu stopun berisine itiyorsa işlem açılır ve planlanan
  risk kayma kadar küçük olurdu. Bugün: kaymasız açılış stopun ötesindeyse işlem yok; kayma emirden sonra gelen bir
  maliyettir, olmayacak bir işlemi doğuramaz. Etkisi: {{! karsi_olgu ham_acilis }}
- **Giriş dakikasında boşluk** ({{! karsi_olgu_zaman bosluk_giris }}). Önce: sert stopun boşluk kuralı (stopun
  ötesinde açılan dakikada dolum açılıştan) yalnız girişten sonraki dakikalarda sorulurdu; giriş dakikasında makas
  stopu kapsıyorsa çıkış stop seviyesinden yazılırdı. Bugün: giriş dakikası dahil. Etkisi:
  {{! karsi_olgu bosluk_giris }}
- **Önceki gün ölçüleri tatili atlar** ({{! karsi_olgu_zaman onceki_gun }}). Önce: önceki günün tepesi, dibi,
  kapanışı ve açılışı, gün ATR'si ve yüzdeliği ve NR4/NR7 bir önceki satırdan kurulurdu; 25 Aralık ve 1 Ocak'tan
  sonraki günün "önceki günü" tatilin ince kotasyonuydu. Bugün: tatil olmayan son işlem gününden (ön kayıt "önceki
  FX işlem günü" der). Etkisi: {{! karsi_olgu onceki_gun }}
- **Fiksing ve gün içi momentumda stopun yeri** ({{! karsi_olgu_zaman stop_yeri }}; iki adımda). Önce: fiksingde
  stop sinyal mumunun kapanışından, o mumun ATR'si kadar uzaktaydı ve R birimi o mumun ATR'siydi; gün içi momentumda
  stop giriş dakikasının orta açılışından 1·ATR uzaktaydı. İlk adım ({{! karsi_olgu_zaman stop_yeri "1" }}) yalnız
  fiksingi değiştirdi: stop giriş dakikasının orta açılışına taşındı ve ATR girişten önce kapanan son mumdan alındı.
  Gecikmesiz girişte o mum sinyal mumunun kendisidir; girişi bir mum geciken kombinasyonlarda bir sonraki mumdur,
  yani o kombinasyonların R birimi stopsuz olanlarda da değişti. İkinci adım ({{! karsi_olgu_zaman stop_yeri "2" }})
  iki kuralda da stopu yürütülen girişe (makas ve kayma dahil) taşıdı. Bugün: ikisinde de stop yürütülen girişten,
  girişten önce kapanan son mumun ATR'si kadar uzaktadır ve R birimi tam o ATR'dir (ön kaydın tanımı); stopsuz ve
  gecikmesiz kombinasyonlar, varsayılanlar dahil, etkilenmez. Gerekçe: stop sinyal mumunun kapanışından ölçülürse,
  girişi bir mum geciken dönüş kombinasyonlarında fiyat o mumda stopa yaklaşabilir, planlanan risk birkaç pipe iner
  ve R'ye bölünen sonuç anlamsız büyür. Etkisi (iki adım birlikte): {{! karsi_olgu stop_yeri }}
- **Haber kurallarında tek pozisyon** ({{! karsi_olgu_zaman haber_tek_pozisyon }}). Önce: tek pozisyon kuralı olay
  × ofset grubunun içinde uygulanırdı; aynı gün FOMC kararı ve basın toplantısı iki ayrı pozisyon açabilirdi (iki
  olayın sonucu ayrı okunsun diye bilerek seçilmişti). Bugün: parite başına bütün olaylara birlikte (ön kaydın
  ortak mekaniği). Basın toplantısı satırları bu yüzden yalnız karar pozisyonunun kapandığı toplantılardan oluşur
  (haber dersinde). Etkisi: {{! karsi_olgu haber_tek_pozisyon }}
- **Devam tablosunda gün sonu** ({{! karsi_olgu_zaman devam_kirpma }}). Önce: ufku gün sonunu aşan gözlem gün
  sonuna kırpılırdı (motorun "gün sonunu aşamaz" okumasıyla aynı). Bugün: düşer, çünkü kırpılmış bir tutuş o hücrenin
  ufkunu ölçmez; ön kaydın aynı ifadesi böylece iki yerde iki biçimde uygulanır. Etkisi: {{! karsi_olgu devam_kirpma }}
- **Seçimde eşitlik** ({{! karsi_olgu_zaman secim_esitlik }}). Önce: örneklem içi Sharpe'lar kesin
  karşılaştırılırdı; işlem işlem aynı olan iki kombinasyon (ör. tek mum tutulan fiksing momentumunda kapanış stopu
  ile stopsuz) yalnız kayan nokta artığıyla ayrışır ve sonraki seçilebilirdi. Bugün: milyarda birden küçük fark
  eşitliktir ve ızgaradaki ilk alınır (ön kaydın eşitlik kuralı). Etkisi: {{! karsi_olgu secim_esitlik }}
- **Büyük olay günü ve olağanüstü kararlar** ({{! karsi_olgu_zaman haber_gunu_olaganustu }}). Önce: önceden
  duyurulmayan bir FOMC kararı da planlanmış olaylar gibi kendi gününü baştan "büyük olay günü" sayardı; o günün
  karardan önceki girişleri, olay anında bilinemeyen bir bilgiyle kovalanırdı (ileriye bakma). Bugün: önceden
  duyurulmayan olay günü yalnız FX gününün başında ya da öncesinde olmuşsa işaretler (giriş dersindeki koşul tablosu,
  ileriye bakma sınaması yukarıda). İşlemler bu değişkenden etkilenmez; değişen yalnız koşul analizinin kovalarıdır.
  Etkisi: {{! karsi_olgu haber_gunu_olaganustu }}
- **Ay sonu** ({{! karsi_olgu_zaman ay_sonu }}). Önce: ayın son hafta içi günü. Bugün: ayın son Londra iş günü
  (ön kaydın tanımı); ikisinin ayrıştığı aylar, son hafta içi gününün bir İngiltere tatiline düştüğü aylardır:
  {{ K.ay_sonu_kayan | ay_liste }}. Tanımın iki tüketicisi var: fiksingin ay sonu ayrımı ve her kuralın "ay sonu"
  koşul değişkeni. Etkisi: {{! karsi_olgu ay_sonu }}
- **Tatil** ({{! karsi_olgu_zaman tatil }}). Önce: kotasyonlu dakikaları günün yarısından az olan gün tatil
  sayılırdı. Bugün: takvimden (hafta içine düşen 25 Aralık ve 1 Ocak, örneklemin iki kenarında baştan sona
  kapsanmayan gün); günün kapsamı gün bitmeden bilinemez. Etkisi: iki tanım dört paritede de aynı günleri verir,
  hiçbir işlem değişmez.{{? O.veri.tatil_uyum.EURUSD.ayni and O.veri.tatil_uyum.GBPUSD.ayni and O.veri.tatil_uyum.USDJPY.ayni and O.veri.tatil_uyum.AUDUSD.ayni }}
- **Başabaş kayma** ({{! karsi_olgu_zaman basabas_r }}). Önce: pip ortalamasından. Bugün: serinin ölçüsünden,
  işlem başına net R'den. Hükme girmez.
- **Ön kayıtlı iki ölçünün koşuya girişi** ({{! karsi_olgu_zaman onkayitli_iki_olcu }}). Fiksingin ay sonu ayrımı
  ve gün içi momentumun öngörü regresyonu ön kayıtta vardı, ilk sonuçlarda koşulmamıştı. İkisi de hükme girmez.
- **Yalnız yazıya geçirilen iki kural.** Seviye hedefi yürütülen girişin gerisinde ya da tam üstündeyse işlem
  yoktur; girişi gün sonunda ({{ K.gun_sonu_et | t }} New York; {{! gun_sonu_tsi }}) ya da sonrasında olan sinyal alınmaz. İkisinin
  davranışı ilk koşudan beri aynıdır; alınmayan emirlerin sayısı strateji derslerindedir.

### Ön kaydın açık bıraktığı ya da yorum gerektiren yerler

- **Uygulama eşikleri.** Ön kayıt hüküm kuralının şartlarını yazar ama asgarilerini yazmaz: %95 aralığı en az
  {{ K.uygulama_esik.bootstrap | n }} işlemle kurulur, rastgele yön sınaması en az {{ K.uygulama_esik.rastgele | n }}
  işlemle koşar, koşul analizinin "tuttu" hükmü örneklem dışında en az {{ K.uygulama_esik.kosul_oos | n }} işlem
  ister. Üç asgari de ilk sonuçlardan önce sabitlenmiş uygulamadadır. Asgariyi karşılamayan sınama kurulmaz ve "çalışıyor"un
  şartı sağlanmamış sayılır.
- **Rastgele yön sınamasının kurgusu.** Ön kayıt yalnız "rastgele yön yüzdeliği"ni ister. Ölçüm her alınan işlemin
  aynasını kurar: aynı giriş dakikası, ters yön, aynanın kendi yürütülen girişinden aynı R uzaklığında stop ve
  hedef, aynı planlı çıkış; aynada tek pozisyon kuralı yoktur ve ayna kendi stopu ve hedefiyle yeniden yürütülür.
  Her tekrarda her işlem için gerçeği ya da aynası bağımsız yazı turayla seçilir.
- **Yürüyen pencerenin seçim şartı.** Ön kayıt genişleyen pencereyi ve ilk sınama yılını yazar. Seçimin asgari işlem
  şartı, örneklem içi şartın yıl başına payıdır (geçen her yıl için altıda biri); şartı sağlayan kombinasyonu
  olmayan yıl sınanmaz ve sınanan yıllar adıyla yazılır.
- **Oynaklık tercili.** Rejim tablosunun "düşük · orta · yüksek" oynaklığı, giriş gününün ATR'sinin son 252 işlem
  günündeki yüzdeliğinin üçte birlik sabit dilimleridir. Koşul analizindeki "oynaklık yüzdeliği" aynı değişkendir ama
  kova sınırları örneklem içindeki işlemlerin tercilleridir; iki tablonun kovaları bu yüzden birebir aynı değildir.
- **Emir geçerliliği.** Ön kayıt "giriş stopun ötesindeyse işlem yok" kuralını yalnız haber kırılımında (N1) yazar;
  ölçüm aynı kuralı stop seviyesi taşıyan her emre uygular ve seviye hedefi için eşini ekler (hedef yürütülen girişin
  gerisindeyse işlem yok).
- **60 dakikalık mumun çıpası.** Haber kuralları ve New York ilk dengesi — 09:30 dışındaki kurallarda saatlik mum
  saat başında başlar, yani New York 08:30 verisi ({{! tsi "" "New York 08:30" }}) New York 08:00–09:00 mumunun
  ({{! tsi "" "New York 08:00–09:00" }}) ortasına düşer. Tek bir saatlik ızgara Londra 08:00 açılışını
  ({{! tsi "" "Londra 08:00" }}) ve New York 08:30'u birlikte mum sınırına oturtamaz; Londra açılışı seçildi. Bu çıpayı 60
  dakikalık mumda {{! saat_capa }} kullanır. Sinyal penceresi New York 08:00'den önce başlayıp 09:00'dan sonra biten
  bir kuralda New York 08:00–09:00 mumunun hareketi ABD verisinin tepkisini de taşır.
- **Asya aralığının başlangıcı.** Ön kayıt aralığın başlangıcını Londra 00:00'da ({{! tsi "" "Londra 00:00" }}) sabit tutar, ızgara yalnız
  bitişini (Londra 07:00 · 08:00; {{! tsi "·" "Londra 07:00" "Londra 08:00" }}) sınar; Tokyo açılışı bu başlangıca en çok bir saat uzaktır.
- **Tatil.** Ön kayıt tatili tanımlamaz; tatil takvimden gelir (yukarıda).

### Ön kayıtta olmayan ve hükme girmeyen ölçüler

- **Maliyet.** Başabaş kayma (işlem başına net R'yi sıfıra indiren dolum başına temel kayma; haber penceresindeki
  dolumların {{ K.haber_kayma_pip | s1 }} pip ek kayması sabit tutulur) iki dönemde, bütün dönem ve 2024 →, R'den
  ölçülür. Yalnız makasla bile eksi kalan bileşimde iki hâl ayrılır: brütü (orta fiyattan orta fiyata) de eksiyse
  hiçbir maliyette başabaş yoktur ("orta fiyattan bile eksi"); brütü artıysa başabaş, sonucu sıfıra indiren makasın bu
  verinin makasına oranıdır, brüt R / (brüt R − yalnız makas R): maliyet makasla doğrusal ölçeklenir ve işlemler aynı
  kalır varsayımıyla. Yalnız makas koşusu (kayma ve haber kayması sıfır) merdivenin yanına eklendi; ön kaydın
  merdiveni aynen duruyor.
- **Deflated Sharpe'ın gürültü eşiği.** Ön kayıt Bailey ve López de Prado'nun deflated Sharpe'ını ister; onun
  eşiği denemelerin kendi Sharpe'larının yayılımından kurulur (**yayılım eşiği**). Denemeler gerçekten farklıysa
  (maliyet bazı kombinasyonları sistematik olarak eksiye iter) yayılım örnekleme gürültüsünden büyük çıkar ve eşik
  şişer; denemeler birbirine çok benziyorsa küçük çıkar ve eşik düşer. Ölçüm ikinci bir eşik de yazar: yalnız
  örnekleme gürültüsünden, her deneme sıfır kenarlı ve öbürlerinden bağımsız olsaydı (**gürültü eşiği**). Izgaranın
  kombinasyonları birbirinden bağımsız değildir (aynı kuralın komşu parametreleri); bağımsız deneme sayısı ızgaranın
  boyundan küçük olduğu için gürültü eşiği de bu yönden tutucudur. Bu seride {{! dsr_esik }}. Hiçbir
  seçimin deflated Sharpe olasılığı iki eşikle de %95'e ulaşmaz{{? T.dsr_ust == 0 and T.dsr_gurultu_ust == 0 }}; ikisi de hükme girmez.
- **Gün kümeli parite aralığı.** Hükmün aralığı ön kaydın okumasıyla işlemleri bağımsız örnekler. Aynı paritede aynı
  gün açılan işlemler aynı haberi ve aynı seans hareketini taşır; günde çok işlem açan kurallarda (VWAP dönüşü, iç
  mum) aralık olduğundan dar olabilir. Aynı iki ölçüt gün kümeli aralıkla da soruldu: {{! gun_kumeli }}.
  {{! gun_kumeli_yon }}
- **Havuzun aralığı** gün kümeli bootstrap'le kurulur (yukarıda).
- **Koşul analizinin üç ayrıntısı.** Koşulsuz ortalama değişkenin tanımlı olduğu işlemlerden alınır; aynı ölçünün iki
  adı (Asya aralığı kuralında "aralık" ile "Asya aralığı") tek değişken sayılır; kontrol listesine yalnız en az iki
  paritede aynı kova seçimiyle tutan koşul aday olarak girer.
- **Ters seçim.** Koşul analizinin "tuttu" sayısının ne kadarının şansla açıklanabileceğini görmek için aynı ölçüt,
  örneklem içinde ortalamanın altında kalan kovalar seçilerek de koşulur; karşılaştırma dersinde.
- **Örnek günler.** Her kuralın üç örnek işlemi örneklem dışındaki uygun işlemlerden seçilir: kazanan net en az yarım
  R kazandıran, kaybeden en az yarım R kaybettiren ve işlem boyunca lehine yarım R'ye ulaşmamış, tuzak lehine en az
  yarım R gittikten sonra zararla kapanmış işlemdir. Seçim sabit bir çekilişle yapılır (ön kaydın tohumundan,
  kuralın, paritenin ve etiketin adından türer), sonuca bakılarak yapılmaz ve üç örnek ayrı günlerdedir. Uygun işlem
  yoksa kazanan ve kaybeden için yedek tanım (net artı · net eksi) kullanılır ve örneğin altında yazılır. Her örnek
  işlem ayrıca dolum başına yarım pip ek kaymayla yeniden koşulur; alıştırmaların "dolum daha kötü olsaydı" şıkkı bu
  koşudan cevaplanır.{{? K.ornek.esik == 0.5 and K.ornek.ek_kayma == 0.5 }}
- **Kuyruk duyarlılığı.** R ortalaması her işlemi riskine göre ölçekler; riski makas düzeyine inen tek bir işlem
  ortalamayı taşıyabilir. Her kuralın sonucu ayrıca en iyi işlem çıkarılarak ve beklenen gidiş-dönüş maliyeti
  (girişteki makas, iki dolumun kayması ve haber penceresindeyse haber kayması) riskin yarısını aşan işlemler
  çıkarılarak yeniden ölçülür. R'nin bir tabanı ön kayda girmez; bu ölçü yalnız böyle bir tabanın ne değiştireceğini
  gösterir.
- **Pip ortalaması ve aralığı.** R ortalaması her işlemi riskine göre ölçekler, pip ortalaması her işlemde aynı
  büyüklükle işlem yapanın sonucudur; ikisinin işareti ayrıştığında strateji dersleri bunu adıyla yazar ve pip
  ortalamasının %95 aralığını da verir.
- **Haber dakikasının makası.** Olay anına göre makasın seyri betimleyici bir ölçüdür; hiçbir kurala ve hükme girmez.
- **Yerel tatiller.** Kurallar yalnız hafta içine düşen 25 Aralık ve 1 Ocak'ı işlem günü saymaz; İngiltere'nin banka
  tatillerinde Londra kapalıyken, ABD'nin federal tatillerinde New York'un bankaları kapalıyken de sıradan gün gibi
  işlem açarlar. Bu ölçü o günlerin sonucunu kural kural betimler; ön kayıtta yoktur, sınama yapılmaz ve hükme girmez.
  Verinin o günlerdeki kapsamı giriş dersinin veri tablosunda.

{{! tatil_betimi }}

## Haber takvimi

Her olayın saati resmî bir kaynaktan geldi ve kaynak iki türlüdür. **Tarih tarih**: ABD tarım dışı istihdam ve TÜFE
için BLS'nin yayım sayfalarının ambargo satırı (BLS'nin sitesi otomatik istekleri reddettiği için Internet Archive'daki
kopyalarından; her kopyanın arşiv zaman damgası kayıtta), FOMC kararı için karar metninin yayım satırı ("For release
at 2:00 p.m. EDT"), ECB basın toplantısı için karar duyurusunun kendi cümlesi; kuraldan ayrılan iki BoE kararının
saati BoE'nin önceden yayımladığı saat duyurusundan (aşağıdaki listede). **Kuraldan**: öbür BoE kararları perşembe
12:00 Londra ({{! tsi "" "Londra 12:00" }}; Para Politikası Kurulu'nun yayım kuralı, tarih her özetin kendi
sayfasından), ECB karar saati ECB'nin 27 Haziran 2022 duyurusundan: {{ O.takvim.sayim.ECB_karar.saat_aralik."13:45 Europe/Berlin"[1] | tarih }} toplantısına kadar 13:45 Frankfurt ({{! tsi "" "Frankfurt 13:45" }}),
{{ O.takvim.sayim.ECB_karar.saat_aralik."14:15 Europe/Berlin"[0] | tarih }} toplantısından itibaren 14:15 Frankfurt ({{! tsi "" "Frankfurt 14:15" }}). Her
toplantıda kuralın verdiği karar saatinin, duyurunun yazdığı basın toplantısı saatiyle eşleştiği ayrıca sınandı
(Frankfurt saatiyle karar 13:45 ↔ basın toplantısı 14:30, karar 14:15 ↔ basın toplantısı 14:45; basın toplantısı
{{! tsi "ya da" "Frankfurt 14:30" "Frankfurt 14:45" }}).

**FOMC basın toplantısı** saati en zor bulunanıdır. Ne karar metni ne basın toplantısı sayfası onu yazar: sayfadaki tek
saat kararın yayım saatidir. Fed'in aylık etkinlik takvimi basın toplantısını ayrı satırla yalnız
{{ O.takvim.fomc_takvim_donemi.ilk | ay_uzun }} toplantısından itibaren listeler ve o tarihten bu yana
{{ O.takvim.fomc_takvim_donemi.toplanti | n }} toplantının {{ O.takvim.fomc_takvim_donemi.satirli | n }} tanesinde
satır var{% if len(O.takvim.fomc_takvim_donemi.satirsiz) == 1 %} ({{ O.takvim.fomc_takvim_donemi.satirsiz[0] | ay_uzun }}
toplantısında yok){% endif %}{{? O.takvim.fomc_takvim_donemi.satirli == O.takvim.kunye.fomc.basin_saat_kaynagi.takvim and O.takvim.fomc_takvim_donemi.ilk == O.takvim.kunye.fomc.basin_saat_tarih.takvim[0] }}{% if O.takvim.kunye.fomc.basin_saat_kaynagi.duyuru == 1 %};
daha önce tek bir toplantının saatini ayın duyurusu yazar ({{ O.takvim.kunye.fomc.basin_saat_tarih.duyuru[0] | tarih }}){% endif %}.
Kalan {{ O.takvim.kunye.fomc.basin_saat_kaynagi.kural | n }} toplantının saati Fed'in 13 Mart 2013 duyurusundaki
kuraldan gelir: olağan toplantılarda kararın yayım saati {{ O.takvim.kunye.fomc.kural.karar | t }}, başkanın basın
toplantısının başlangıcı "yaklaşık" {{ O.takvim.kunye.fomc.kural.basin | t }} (New York; {{! tsi "ve" "New York 14:00" "New York 14:30" }}){{? O.takvim.kunye.fomc.kural.karar == "14:00" and O.takvim.kunye.fomc.kural.basin == "14:30" }}.{{? len(O.takvim.kunye.fomc.kural.yineleme) == 2 and O.takvim.kunye.fomc.kural.yineleme[0].tarih == "2024-08-09" and O.takvim.kunye.fomc.kural.yineleme[1].tarih == "2025-09-05" and O.takvim.kunye.fomc.kural.yineleme[0].saat == O.takvim.kunye.fomc.kural.basin and O.takvim.kunye.fomc.kural.yineleme[1].saat == O.takvim.kunye.fomc.kural.basin }}
Kural Fed'in 2024 ve 2025 toplantı takvimi duyurularında aynen yinelenir.{{? O.takvim.kunye.fomc.kuraldan_farkli == 0 }} Tarih
tarih kaydı olan toplantıların hepsi kuralla aynı saati taşır. Kural yalnız kararı kuralın saatinde yayımlanan olağan
toplantıya uygulandı{% if not O.takvim.sayim.FOMC_basin.olaganustu %}; olağanüstü toplantıların basın toplantısı
kaynakta saatsiz olduğu için takvimde yok{% endif %}. Fiyat kuralla tutarlı: basın toplantısının ilk 15 dakikasında
EUR/USD'nin ortalama dakikalık aralığı, hemen önceki 15 dakikanın (kararın ilk yarım saatinin ikinci yarısı) medyanda
{{ O.takvim.sinama.basin_bilgi.FOMC_basin.EURUSD.medyan | s2 }} katı; {{ O.takvim.sinama.basin_bilgi.FOMC_basin.EURUSD.n | n }}
toplantının {{ O.takvim.sinama.basin_bilgi.FOMC_basin.EURUSD.birden_buyuk | n }} tanesinde 1'in üstünde. Bu bir
doğrulama değildir: oran fiyatın kuralın saatinden sonra hızlandığını gösterir, toplantının hangi dakikada
başladığını göstermez. "Yaklaşık" kelimesi ölçünün sınırıdır; konuşmanın gerçek başlangıcı bir iki dakika kayabilir.
Karar ile basın toplantısının karşılaştırması bir saatlik pencereyle kurulduğu için böyle bir kayma onun içinde kalır;
5 dakikalık ilk haber mumunda ise kayma mumun önemli bir parçasıdır ve N1–N5'in basın toplantısı sonuçları bu
belirsizliği taşır.

Takvimin dışarıda bıraktığı ya da düzelttiği kayıtlar:

{{! takvim_sorun }}

Olağanüstü FOMC toplantıları takvimde kendi saatleriyle durur: {{! olaganustu FOMC_karar }}. Saatini
kaynağın yazmadığı olağanüstü ECB ve BoE kararları dışarıdadır, çünkü saati tahmin edilen bir olay haber penceresini
yanlış yere koyardı.

Takvimde durmak her ölçüye girmek demek değildir. Takvimdeki her olay haber makası tablosuna (arşivde dakikası olan
dakikalarıyla) ve o günün "büyük olay günü" işaretine girer; ama devam tablosu, beş haber stratejisi ve ortalama
patikalar olaydan önceki bir pencereye ve olay anının fiyatına ihtiyaç duyar. Bu ölçülere girmeyen olaylar:

{{! olcu_disi }}

**Fiyat sınaması.** Her olayın saati ayrıca 1 dakikalık fiyattan sınandı. Sıçrama oranı, olay dakikası ve sonraki iki
dakikanın en büyük dakikalık aralığının olaydan önceki otuz ile üç dakika arasının medyan aralığına oranıdır. Resmî
saatte oran {{ O.takvim.sinama.kural.esik | s1 }} ya da üstündeyse olay doğrulanır; bir saat ya da yarım saat önce ya da
sonra oran eşiği aşıyor ve resmî saatinkinin en az iki katıysa çelişki sayılır; ikisi de değilse sessiz: piyasa ne
resmî dakikada ne o dört aday saatte kımıldamıştır. Dört aday saat ancak bir saatlik kaymayı (yaz saati hatası) ve yarım
saatlik kaymayı (ECB kararında Frankfurt 13:45 ↔ 14:15; {{! tsi "↔" "Frankfurt 13:45" "Frankfurt 14:15" }}) yakalar; daha büyük bir kayma için resmî saatin altı saat öncesi ve sonrası yarım
saatte bir ayrıca taranır. {{! uzak_tarama }} Sınama yalnız raporlar: resmî belge birincil kaynaktır ve hiçbir olay
fiyat yüzünden dışarıda bırakılmadı. Çelişki veren olaylar:

{{! celiski }}

{% if len(O.takvim.sinama.celiski_olay) == 2 and O.takvim.sinama.celiski_olay[0].tarih == "2019-12-12" and O.takvim.sinama.celiski_olay[1].tarih == "2020-04-10" %}İkisinin de açıklaması
kaynağın kendisinde. 12 Aralık 2019 ECB toplantısında aday saat basın toplantısının içine düşüyor: o gün fiyatı
kararın kendisi değil toplantı oynattı. 10 Nisan 2020 TÜFE'si Paskalya cumasında, dakikalık aralıkların çok dar
olduğu ince bir piyasada yayımlandı; aday saatlerdeki sıradan gürültü resmî saatten "daha iyi" oturdu.{% else %}Çelişki
veren olayların açıklaması tek tek yazılmalıdır; bu liste değişti.{% endif %}

{{! sessiz }}

## Ölçülmeyenler

Bu serinin cevaplamadığı sorular, sonuçların sınırlarıyla birlikte:

- **Gerçek sürpriz.** Açıklanan verinin piyasa beklentisinden (anket medyanı) farkı yok; haber dersindeki büyüklük
  kovaları ilk mumun hareketinden kurulan bir vekildir.
- **Piyasa derinliği.** Dolumlar en iyi bid/ask'tan, sınırsız likiditeyle yapılır; büyük bir emrin fiyatı itmesi ve
  kısmi dolum modellenmez. Kayma sabit pip olarak eklenir.
- **Başka bir likidite kaynağı.** Makas Dukascopy'nin kendi kotasyonudur; bir bankanın ya da başka bir platformun
  gördüğü makastan farklı olabilir. Maliyet merdiveni bu farka duyarlılığı gösterir.
- **Komisyon ve ücretler.** Makas ve kayma dışında maliyet yok sayıldı.
- **Gecelik taşıma.** Bütün pozisyonlar gün sonunda kapandığı için faiz farkı (swap) doğmaz; gece taşıyan bir kuralın
  sonucu farklı olurdu.
- **Gecikme.** Emrin iletilmesi ve kuyruğa girmesi modellenmez; giriş, kuralın giriş dakikasının açılışıdır.
- **Pasif ya da limit yürütme.** Giriş ve piyasa çıkışları makası öder (alış ask'tan, satış bid'den); makasın bir
  kısmını kazanan bir limit girişi ya da orta fiyata yakın bir yürütme ölçülmedi. "Brüt" sonuç orta fiyattan orta
  fiyata ölçülür ve böyle bir yürütmenin üst sınırını verir, kendisini değil: limit emir her zaman dolmaz.
- **Yerel tatil süzgeci.** İngiltere ve ABD tatillerinde işlem açmayan bir kural sınanmadı; o günlerin sonucu
  yukarıda yalnız betimlendi.
- **Gerçek işlem hacmi.** FX'te merkezî hacim yoktur; VWAP kuralları kotasyon likiditesini ağırlık olarak kullanır.
- **Daha kısa zaman dilimleri.** 5 dakikanın altındaki mumlar ve tick verisi ölçülmedi.
- **Başka pariteler.** Yalnız dört majör ({{ K.ciftler | pariteler }}); çapraz kurlar ve gelişen piyasa paraları
  yok.
- **Pozisyon büyüklüğü.** Her işlem 1 R'dir; kaldıraç, portföy düzeyinde risk ve kuralların birleşimi ölçülmedi.
- **Uyarlanan kurallar.** Yürüyen pencere dışında rejime göre değişen ya da öğrenen bir model denenmedi.
{% if not T.fomc_basin %}- **FOMC basın toplantıları.** Saatleri resmî kaynaklardan okunamadığı için bu ölçümde basın
  toplantısı olayları ve FOMC karar ile basın toplantısı karşılaştırması yok.
{% endif %}
## Yeniden üretilebilirlik

Bu serinin sonuçlarını bir okurun yeniden kurması için gereken her şey açıktır: fiyat verisi Dukascopy'nin herkese
açık 1 dakikalık bid/ask beslemesidir ve dönemi yukarıdaki tablodadır; olay saatlerinin kaynakları haber takvimi
bölümünde tek tek yazılıdır; yürütme ve maliyet kuralları yukarıdadır; kuralların, ızgaraların ve hüküm kuralının
tam metni yayımlanan ön kayıttadır ve dosyanın özü yukarıdadır. Ölçüm deterministtir: aynı veri ve aynı kurallarla
her koşu aynı işlemleri ve aynı sayıları verir (bootstrap ve rastgele yön sabit tohumludur).

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
