# RootLens — Mikroservislerde Anomali Tespiti ve Kök Neden Analizi

RootLens, mikroservis mimarisine sahip uygulamalarda oluşan performans sorunlarını ve hataları **metrik, log ve trace verilerini birlikte kullanarak** incelemek amacıyla geliştirilen bir bitirme projesidir.

Projenin nihai hedefi, sistemdeki anormal davranışları otomatik tespit etmek ve soruna neden olabilecek servisleri öncelik sırasına göre belirlemektir.

**Mevcut durum:** Projenin 5. ve 6. hafta çalışmaları kapsamında telemetri toplama, veri kalitesi kontrolü, başlangıç düzeyi eşik tabanlı analiz, zaman pencerelerine göre veri birleştirme ve deney etiketleme altyapısı geliştirilmiştir. Otomatik anomali tespiti ve kök neden analizi sonraki geliştirme aşamalarıdır.

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
       (Gelecek aşamalar)
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

### Adım 1 — Astronomy Shop'u çalıştırma

Ana proje dizinindeki `astronomy-shop` klasörüne geçin.

```powershell
cd astronomy-shop
docker compose up -d
```

Astronomy Shop'un kullandığı Compose yapılandırmasına göre ek dosyalar veya ortam ayarları gerekebilir.

### Adım 2 — RootLens'i çalıştırma

Ana proje dizinindeki `rootlens` klasörüne geçin.

```powershell
cd rootlens
docker compose up -d --build
```

Çalışan servisleri kontrol etmek için:

```powershell
docker compose ps
```

### Adım 3 — API ve arayüzü kontrol etme

Geliştirme ortamında kullanılan adresler:

- RootLens arayüzü: `http://localhost:5173`
- Analyzer API: `http://localhost:8002`
- API dokümantasyonu: `http://localhost:8002/docs`

Bu adresler Docker Compose port ayarlarına göre değişebilir.

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
- Otomatik anomali tespiti ve kök neden analizi henüz tamamlanmamıştır.
- Eğitim ve değerlendirme için ayrı veri dışa aktarım süreci sonraki geliştirme adımlarındadır.

## 10. Birim Testleri

Analyzer kaynak kodunun bulunduğu klasörde:

```powershell
cd rootlens/services/analyzer
python -m pytest -q test_week5.py test_week6.py
```

Komutun çalışması için Python ortamında `pytest` ve gerekli proje bağımlılıklarının kurulu olması gerekir.

**Güncel doğrulama durumu:** Docker container'ında `pytest` kurulmuş ancak test dosyaları container içinde bulunamadığından bu ortamda testler çalıştırılamamıştır. Bu nedenle Docker içindeki birim testler için başarılı sonuç iddia edilmemektedir.

## 11. Mevcut Durum ve Sonraki Çalışmalar

### Tamamlanan geliştirmeler

- Mikroservis test ortamının kurulması
- Telemetri kaynaklarına erişim ve veri toplama altyapısı
- Toplanan örneklerin saklanması
- Veri kalitesi kontrolleri
- Eşik tabanlı başlangıç analizi
- Zaman pencerelerine göre veri birleştirme
- Kontrollü deney etiketleme altyapısı

### Planlanan geliştirmeler

- Daha kapsamlı veri kümesi oluşturma
- Otomatik anomali tespit yöntemi geliştirme
- Servis bağımlılıklarını dikkate alan kök neden analizi
- Anomali ve kök neden sonuçlarını değerlendirme
- Dashboard üzerinde analiz sonuçlarını gösterme
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