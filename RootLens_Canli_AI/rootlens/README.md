# RootLens — Mikroservislerde Anomali Tespiti ve Kök Neden Analizi

RootLens, mikroservis mimarisine sahip uygulamalarda oluşan performans sorunlarını ve hataları **metrik, log ve trace verilerini birlikte kullanarak** incelemek amacıyla geliştirilen bir bitirme projesidir.

Projenin nihai hedefi, sistemdeki anormal davranışları otomatik tespit etmek ve soruna neden olabilecek servisleri öncelik sırasına göre belirlemektir.

**Mevcut durum:** Projenin 5. ve 6. hafta çalışmaları kapsamında telemetri toplama, veri kalitesi kontrolü, başlangıç düzeyi eşik tabanlı analiz, zaman pencerelerine göre veri birleştirme ve deney etiketleme altyapısı geliştirilmiştir. Analiz ve Deney paneli metrik, log, trace, istatistiksel birleşik yöntem ve One-Class SVM'i aynı test pencerelerinde çalıştırır. Trace çağrılarından servis ilişkilerini çıkarır, kök neden adaylarını sıralar ve etiketli test pencerelerinden karşılaştırma tablosu hesaplar. Canlı kontrollü deneyler ve nihai tez sonuçları ayrıca hazırlanır.

## 1. Projenin Amacı

Bir mikroservis uygulamasında hata oluştuğunda sorunun hangi servisten kaynaklandığını bulmak zor olabilir. Bir servisteki problem, diğer servislerin performansını da etkileyebilir.

RootLens şu sorulara cevap verebilecek bir sistem geliştirmeyi amaçlar:

- Sistemde normal dışı bir durum var mı?
- Hangi servisler bu durumdan etkileniyor?
- Problem ne zaman başladı?
- Metrik, log ve trace verileri birlikte değerlendirildiğinde hangi servis olası kök neden olabilir?

## 2. Sistem Mimarisi

Proje, test ortamı olarak OpenTelemetry Demo uygulaması **Astronomy Shop**'u kullanır.

Veri akışı:

```text
Astronomy Shop
    |
    | Mikroservislerin çalışması ve test işlemleri
    v
Metrik + Log + Trace
    |
    v
OpenTelemetry Collector
    |
    +----> Prometheus  (Metrikler)
    |
    +----> OpenSearch  (Loglar)
    |
    +----> Jaeger      (Trace verileri)
                  |
                  v
           RootLens Backend
                  |
       +----------+----------+
       |                     |
       v                     v
  Veri Toplama          Veri Kalitesi
       |                     |
       +----------+----------+
                  |
                  v
       Zaman Pencerelerine Göre
           Veri Birleştirme
                  |
                  v
          Deney Etiketleme
                  |
                  v
      Anomali Tespiti ve RCA
       (Tek kaynaklı ve birleşik)
                  |
                  v
          RootLens Dashboard
```

**Not:** Şema projenin hedef mimarisini gösterir. Bütün aşamalar henüz tamamlanmamıştır.

## 3. Kullanılan Teknolojiler

| Teknoloji | Görevi |
|---|---|
| Docker ve Docker Compose | Servisleri container ortamında çalıştırmak |
| Astronomy Shop | Test edilecek mikroservis uygulaması |
| OpenTelemetry | Telemetri verilerini üretmek ve iletmek |
| Prometheus | Metrik verilerini sorgulamak |
| OpenSearch | Log verilerini sorgulamak |
| Jaeger | Servisler arasındaki istekleri ve trace verilerini incelemek |
| Python / FastAPI | RootLens analiz API'sini geliştirmek |
| SQLite | Toplanan örnekleri ve deney etiketlerini saklamak |
| React | RootLens kullanıcı arayüzünü geliştirmek |
| Pytest | Python birim testlerini çalıştırmak |

## 4. Proje Klasör Yapısı

```text
rootlens/
├── frontend/
│   └── src/
├── services/
│   ├── analyzer/
│   │   ├── main.py
│   │   ├── week5.py
│   │   ├── week6.py
│   │   ├── test_analyzer.py
│   │   ├── test_week5.py
│   │   ├── test_week6.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── order/
│   └── payment/
├── docker-compose.yml
├── otelcol-config.yml
├── otelcol-config-check.yml
└── README.md
```

`astronomy-shop/` klasörü ana proje dizininde test ortamını içerir.

Yerel veritabanları, Python önbellekleri ve yedek dosyalar kaynak kod deposuna eklenmemelidir.

## 5. Kurulum ve Çalıştırma

### Gereksinimler

- Docker Desktop
- Docker Compose
- Git
- Geliştirme ortamında gerekli olduğunda Python ve Node.js

### Canlı Order ve Payment laboratuvarı

Windows'ta Python 3.11+ ve Node.js 22.12+ ile `rootlens/live.cmd` dosyasını açın.
Terminal açıkken http://127.0.0.1:8013 adresine gidin. **Ödeme hatası** veya
**Ödeme gecikmesi** seçip **Canlı deneyi başlat** düğmesine basın. İlk kurulum
internet ister. Deney yaklaşık 90–100 saniye sürer.

Order ve Payment ayrı süreçlerdir ve localhost üzerinden gerçek HTTP istekleri
alır. 36 normal eğitim isteği, 6 normal kontrol isteği ve 12 arızalı istek
gönderilir. Ödeme hatasında Payment HTTP 503 döndürür. Gecikme senaryosunda
Payment cevaptan önce üç saniye bekler. Ölçülen süre, durum kodu ve çağrı izi
SQLite’a kaydedilir. Model eğitimi ve deney sonuçları aynı panelde görünür.

Laboratuvarda üç telemetri türü yerel HTTP gözlemlerinden çıkar. Astronomy
Shop modu ise üç ayrı arka uca bağlanır. Akademik karşılaştırma için aşağıdaki
Astronomy Shop kurulumunda etiketli deneyler toplayın. Yerel veritabanı
`rootlens/data/live_lab.db` konumunda tutulur.

Linux/macOS veya elle çalıştırma için `rootlens/frontend` altında
`npm ci` ve `npm run build:live` çalıştırın. Sonra
`rootlens/services/analyzer` altında `python -m pip install -r requirements.txt`
ve `python live.py` komutlarını çalıştırın.

### Astronomy Shop ve RootLens köprüsünü çalıştırma

Windows'ta Docker Desktop hazırken `rootlens/astronomy-live.cmd` ile her iki
Compose yığınını başlatabilirsiniz. Linux/macOS veya elle çalıştırma adımları:

Docker Desktop açıkken depo kökünden:

```powershell
cd astronomy-shop
docker compose --env-file compose.demo.env -f compose.yaml -f compose.observability.yaml up -d --build
docker compose -f compose.rootlens.yaml up -d --build
```

Daha önce çalışan Astronomy Shop kurulumunda kendi `.env` dosyanız varsa ilk komutta
`--env-file compose.demo.env` yerine `--env-file .env` kullanabilirsiniz.

- Astronomy Shop: http://localhost:8080
- Senaryo ayarları: http://localhost:8080/feature
- RootLens paneli: http://localhost:5173
- Analyzer API dokümantasyonu: http://localhost:8002/docs

### Hızlı arayüz provası

Windows'ta Python 3.11+ ve Node.js 22.12+ kuruluysa `rootlens/preview.cmd` dosyasını
çalıştırın. Terminal açıkken http://127.0.0.1:8012 adresine gidip
**Örnek ödeme deneyini aç** düğmesine basın. İlk kurulumda internet gerekir.

Elle çalıştırmak için `rootlens/frontend` klasöründe `npm ci` ve
`npm run build:preview` çalıştırın. Ardından `rootlens/services/analyzer`
klasöründe `python -m pip install -r requirements.txt` ve `python preview.py`
çalıştırın. Prova, ayrı ve geçici bir veritabanındaki yapay telemetriyi kullanır.
Bu sonuçlar gerçek deney bulgusu olarak kullanılmaz.

### Canlı ara demo ve ilk karşılaştırma

1. RootLens → **Analiz ve Deney** ekranını açın. Astronomy Shop'ta normal checkout
   trafiği üretin ve **Telemetriyi kaydet** ile her dakika veri kaydedin. Varsayılan
   60 saniyelik pencere için One-Class SVM'de servis başına en az altı tam normal pencere gerekir. Başlangıç ve bitişi
   dakika sınırlarına denk getirmek tam pencereleri ayırmayı kolaylaştırır.
2. Kontrollü hatayı açın ve checkout işlemlerini tekrarlayın. Prometheus istek ve
   hata hızları son iki dakikayı özetler. Geçiş anındaki bu örnekleri sonuçlara
   katmamak için test aralığını arıza başladıktan iki dakika sonra başlatın.
   Test boyunca telemetriyi düzenli kaydedin ve sonunda arızayı kapatın.
3. Normal referans ile test aralığını girin. Dört yöntemin skorlarına, aday sıralamasına
   ve çağrı ilişkilerine bakın. **Seçili pencereye deney etiketi ekle** alanında
   deney günlüğünden doğruladığınız servis ve senaryo etiketlerini girin.
   Normal ve hatalı test pencerelerini ayrı etiketleyin. Analizi tekrar çalıştırın.

### Yöntem ve ölçüm

Her servis ve özellik için eşik, normal pencerelerin medyanına değişkenlik payı
eklenerek hesaplanır. Her kaynağın en yüksek normalize skoru kullanılır. Birleşik
yöntem en az iki değerlendirilebilir kaynağın skorlarının ortalamasını alır.
Skor 1'i geçerse servis penceresi anomali sayılır. Jaeger ve birleşik sıralama,
anomalili servisler arasında görülen alt servis çağrılarına öncelik verir.

One-Class SVM (RBF çekirdeği, `nu=0.10`), servis başına yalnızca önceki normal
pencerelerde gözlenen metrik, log ve trace özelliklerinden bir normal davranış
sınırı öğrenir. En az iki telemetri türünde ortak özellikleri olan altı normal
pencere gerekir. Test penceresinin model için gerekli özellikleri eksikse
model o pencereye skor vermez. Tahmin ve trace tabanlı kök neden sıralaması ayrı
adımlardır. Eğitimde anomali veya kök neden etiketleri kullanılmaz.

[One-Class SVM yöntem belgesi](https://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html)

Precision, recall, F1 ve yanlış alarm oranı tabloda yer alan tüm yöntemlerin
skor üretebildiği ortak etiketli servis pencerelerinden hesaplanır. Top-1, Top-3 ve API'deki MRR,
ortak etiketli kök neden pencereleri üzerinden ölçülür. Etiketler eşik veya aday
sıralaması hesabında kullanılmaz. Canlı değerlendirmede senaryoları ayrı tekrarlar
hâlinde kaydedin ve eşikleri test etiketlerine göre ayarlamayın. Sınırlı snapshot
toplama, kaydedilen log sayısının toplam sistem log hacmini temsil etmesini engeller.

### Olaylar ekranı: işlem seviyesinde ödeme hatası

1. `paymentFailure` ayarı `off` iken birden fazla checkout işlemi yapın.
   Normal başlangıç ve bitiş saatini not edin. Gecikme karşılaştırması için işlem başına
   en az beş normal span gerekir.
2. RootLens → **Olaylar** ekranında **Telemetriyi kaydet** düğmesine basın.
3. `paymentFailure` ayarını `100%` yapıp yeniden checkout deneyin. Hata aralığının
   başlangıç ve bitiş saatini not edin. Telemetriyi tekrar kaydedin ve bayrağı `off` yapın.
   Toplama, son 15 dakikadaki sınırlı sayıda checkout trace'ini alır.
4. İki aralığı Olaylar ekranına girip **Aralıkları analiz et** düğmesine basın.
   Analiz, açık hata statülerini ve normal referansın üzerindeki gecikmeleri işaretler.
   Bağlı trace'lerde hatanın yayıldığı üst servislerden önce alt servis adayları gösterilir.

Aynı analiz `GET /week7/anomalies` üzerinden çağrılabilir. Dört tarih parametresini
saat dilimi içeren ISO 8601 biçiminde gönderin. Bitiş anları aralığa dahil edilmez.

## 6. Beşinci Hafta — Telemetri Toplama ve İlk Analiz

Beşinci haftanın amacı, farklı telemetri kaynaklarından alınan verileri analiz edilebilir hâle getirmektir.

### Yapılan çalışmalar

- Prometheus, OpenSearch ve Jaeger üzerinden veri toplama altyapısı
- Toplanan örneklerin SQLite veritabanına kaydedilmesi
- Veri kalitesinin kontrol edilmesi
- Eksik veya geçersiz kayıtların incelenmesi
- Başlangıç düzeyinde eşik tabanlı analiz

### API uç noktaları

| Uç nokta | Görevi |
|---|---|
| `POST /week5/collect` | Telemetri örneklerini toplar |
| `GET /week5/samples` | Kaydedilen örnekleri listeler |
| `GET /week5/quality` | Veri kalitesi bilgilerini gösterir |
| `GET /week5/baseline` | Basit eşik tabanlı analiz gerçekleştirir |

**Önemli:** Eşik tabanlı başlangıç analizi, eğitilmiş bir yapay zekâ anomali modeli değildir.

## 7. Altıncı Hafta — Veri Birleştirme ve Etiketleme

Altıncı haftanın amacı, farklı kaynaklardan gelen telemetri örneklerini ortak bir analiz veri kümesinde bir araya getirmektir.

### Yapılan çalışmalar

- Verilerin servis bazında gruplandırılması
- Verilerin zaman pencerelerine ayrılması
- Metrik, log ve trace bilgilerinin aynı analiz penceresinde değerlendirilmesi
- Veri kümesinin kalite kontrolü
- Kontrollü deneyler için normal/anomali etiketlerinin kaydedilmesi

### API uç noktaları

| Uç nokta | Görevi |
|---|---|
| `GET /week6/dataset` | Birleştirilmiş analiz pencerelerini üretir |
| `GET /week6/quality` | Birleştirilmiş veri kalitesini gösterir |
| `GET /week6/labels` | Kaydedilmiş deney etiketlerini listeler |
| `POST /week6/labels` | Yeni deney etiketi kaydeder |

### Veri eşleştirme

Veriler, mümkün olduğunda gerçek olay zamanları kullanılarak ilgili zaman pencerelerine yerleştirilir.

Ancak tüm kaynaklarda aynı doğrulukta zaman bilgisi bulunmayabilir. Bu nedenle zaman penceresi eşleştirmesi, kesin olay ilişkisi veya kök neden bağlantısı olarak değerlendirilmemelidir.

`GET /week6/dataset` uç noktası veri kümesini dinamik olarak üretir; ayrı bir kalıcı birleşik tablo oluşturmaz.

### Deney etiketleri

Etiketler kontrollü test senaryolarına dayanır:

- `normal`: Normal çalışma olarak işaretlenen deney
- `anomaly`: Hata veya anormal davranış oluşturulan deney

Bu etiketler kullanıcı tarafından kaydedilir. Sistem henüz otomatik kök neden etiketi üretmez.

## 8. Kontrollü Hata Senaryoları

Test ortamında özellikle ödeme servisi üzerinden kontrollü senaryolar uygulanmıştır.

Örnek senaryolar:

- Normal ödeme akışının gözlemlenmesi
- `paymentFailure` özelliğiyle ödeme hatasının tetiklenmesi
- Jaeger üzerinden `PaymentService/Charge` işleminin incelenmesi
- İlgili zaman aralıklarının normal veya anomali olarak etiketlenmesi

Bu deneyler, ileride geliştirilecek anomali tespiti ve kök neden analizi yöntemleri için örnek veri oluşturmayı amaçlar.

**Not:** Bir trace içinde hata görülmemesi, uçtan uca sipariş işleminin başarıyla tamamlandığını tek başına kanıtlamaz.

## 9. Veri Kalitesi ve Sınırlamalar

Projenin mevcut sürümünde şu sınırlamalar bulunmaktadır:

- Her zaman penceresinde üç telemetri kaynağının tamamı bulunmayabilir.
- Bazı kayıtların servis bilgisi eksik olabilir.
- Veri birleştirme zaman penceresi temellidir; kesin trace ilişkisi henüz kurulmamıştır.
- Deney etiketleri manuel olarak kaydedilmektedir.
- Bazı servis ve zaman aralıklarında kaynak kapsamı yetersiz olabilir. Karşılaştırma ortak etiketli pencerelerin sayısını gösterir.
- Eğitim ve değerlendirme için ayrı veri dışa aktarım süreci sonraki geliştirme adımlarındadır.

## 10. Birim Testleri

Analyzer kaynak kodunun bulunduğu klasörde:

```powershell
cd rootlens/services/analyzer
python -m pytest -q
```

Komutun çalışması için Python ortamında `pytest` ve gerekli proje bağımlılıklarının kurulu olması gerekir.

Analyzer testleri geçici SQLite veritabanıyla normal, yavaş ve hatalı span örneklerini doğrular. Canlı senaryo doğrulaması Astronomy Shop ile ayrıca yapılır.

## 11. Mevcut Durum ve Sonraki Çalışmalar

### Tamamlanan geliştirmeler

- Mikroservis test ortamının kurulması
- Telemetri kaynaklarına erişim ve veri toplama altyapısı
- Toplanan örneklerin saklanması
- Veri kalitesi kontrolleri
- Eşik tabanlı başlangıç analizi
- Zaman pencerelerine göre veri birleştirme
- Kontrollü deney etiketleme altyapısı
- Jaeger tabanlı işlem analizi, beş yöntemli pencere analizi, kök neden sıralaması ve karşılaştırma ekranı

### Planlanan geliştirmeler

- Daha kapsamlı veri kümesi oluşturma
- Farklı canlı arıza türleri ve yüklerde tekrarlı, etiketli deneyler toplama
- F1 ve Top-k bulgularını, yanlış alarm örneklerini ve kaynak kaybı testlerini tez ve makalede raporlama
- Otomatik test ve CI/CD süreçlerini geliştirme

## 12. Akademik Kapsam

**Proje konusu:** Mikroservis Sistemlerinde Çok Kaynaklı Telemetri Verileri ile Anomali Tespiti ve Otomatik Kök Neden Analizi

**Üniversite:** İstanbul Gedik Üniversitesi

**Proje ekibi:**
- Betül Yıldız
- Fatıma Isalı
- Muhammed Emir Tel

**Danışman:** Dr. Öğr. Üyesi Hikmet Canlı

Bu proje akademik araştırma ve geliştirme amacıyla hazırlanmıştır.