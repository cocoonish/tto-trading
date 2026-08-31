# Planlı ihraç takvimi arşivi

Her İç Borçlanma Stratejisi dokümanının getirdiği takvim, geldiği gün burada
sürümlenir. `.strategy_history.json` ayların HEDEF tutarını zaten sürümlüyordu;
takvimin kendisi (hangi senet, hangi vade, hangi gün) sürümlenmiyordu — yani
"bu strateji neyi değiştirdi" sorusu ancak git geçmişi kazınarak
cevaplanabiliyordu ve bir analiz o kazımaya dayanamaz.

Dosya adı: `<yayım tarihi>_<dönem>.csv`. İçerik, o gün üretilmiş
`hazine_planlanan_ihaleler.csv`'nin aynısıdır.

DİKKAT — arşivdeki tahmin sütunları o günün yöntemiyle üretilmiştir. Sürümler
arası karşılaştırma yapılırken tahminler AYNI yöntemle yeniden hesaplanmalıdır
(bkz. `vade_proj.py`), yoksa yöntem değişikliği strateji değişikliği sanılır.
