# 🔍 RootLens

## Mikroservis Sistemlerinde Çok Kaynaklı Telemetri Verileri ile Anomali Tespiti ve Otomatik Kök Neden Analizi

### 🎓 Proje Bilgileri

-   **Kurum:** İstanbul Gedik Üniversitesi
-   **Bölüm:** Bilgisayar Mühendisliği
-   **Ders:** MFK420 -- Mezuniyet Projesi ve Tezi
-   **Danışman:** Dr. Öğr. Üyesi Hikmet Canlı
-   **Proje Ekibi:** Betül Yıldız, Fatıma İsalı, Muhammed Emir Tel

------------------------------------------------------------------------

## 📌 Proje Nedir?

**RootLens**, mikroservis tabanlı sistemlerde oluşan anormal
davranışları tespit etmeyi ve problemin olası kök nedenini belirlemeyi
amaçlayan bir analiz platformudur.

Mikroservis sistemlerinde bir işlem birçok farklı servisten geçebilir.
Bu nedenle bir hata oluştuğunda problemin hangi servisten
kaynaklandığını bulmak zorlaşabilir.

RootLens temel olarak şu soruya cevap vermeyi hedefler:

> **Sistemde ne sorun var, nerede başladı ve olası nedeni nedir?**

------------------------------------------------------------------------

## 🎯 Projenin Amacı

RootLens ile:

-   Mikroservislerin sağlık durumunun izlenmesi,
-   **Metrics, logs ve traces** verilerinin toplanması,
-   Normal dışı davranışların tespit edilmesi,
-   Farklı telemetri kaynaklarının birlikte değerlendirilmesi,
-   Problemin olası kök nedeninin belirlenmesi,
-   Sonuçların tek bir dashboard üzerinden gösterilmesi

hedeflenmektedir.

------------------------------------------------------------------------

## 🔄 Sistem Nasıl Çalışıyor?

Proje iki ana bölümden oluşmaktadır:

-   **Astronomy Shop:** Analiz ettiğimiz mikroservis test sistemi.
-   **RootLens:** Telemetri verilerini analiz etmek için geliştirdiğimiz
    platform.

``` text
ASTRONOMY SHOP
Test ettiğimiz mikroservis sistemi
        │
        │ Telemetri üretir
        ▼
OPENTELEMETRY
Telemetriyi toplar
        │
        ├─────────────┬─────────────┐
        ▼             ▼             ▼
   PROMETHEUS     OPENSEARCH      JAEGER
    Metrics          Logs          Traces
        │             │             │
        └─────────────┴─────────────┘
                      │
                      ▼
              ROOTLENS ANALYZER
               Verileri işler
                      │
                      ▼
                ANOMALİ TESPİTİ
                      │
                      ▼
              KÖK NEDEN ANALİZİ
                      │
                      ▼
              ROOTLENS DASHBOARD
          Sonucu kullanıcıya gösterir
```

### Kısacası kim ne yapıyor?

-   **Astronomy Shop** → Analiz edeceğimiz sistemi ve telemetri
    verilerini üretir.
-   **OpenTelemetry** → Mikroservislerden telemetriyi toplar.
-   **Prometheus** → Metrik verilerini tutar ve sorgulamamızı sağlar.
-   **OpenSearch** → Log verilerini tutar ve sorgulamamızı sağlar.
-   **Jaeger** → Bir isteğin servisler arasında izlediği yolu (trace)
    gösterir.
-   **RootLens Analyzer** → Bu verileri işleyen ve analiz eden bizim
    geliştirdiğimiz bölümdür.
-   **RootLens Dashboard** → Sistem durumunu ve analiz sonuçlarını
    kullanıcıya gösteren arayüzümüzdür.
-   **Docker / Docker Compose** → Bütün servisleri container'lar halinde
    birlikte çalıştırmamızı sağlar.

------------------------------------------------------------------------

## 🛒 Astronomy Shop Nedir ve Neden Kullanıyoruz?

**Astronomy Shop**, OpenTelemetry tarafından geliştirilen açık kaynaklı
bir mikroservis demo uygulamasıdır. **RootLens ekibi tarafından
geliştirilmemiştir.**

RootLens'i gerçekçi bir mikroservis sistemi üzerinde geliştirmek ve test
etmek için kullanıyoruz. İçerisinde Frontend, Cart, Checkout, Payment,
Shipping, Product Catalog, Recommendation ve Email gibi birbirleriyle
haberleşen servisler bulunur.

``` text
Astronomy Shop = Analiz edilen mikroservis sistemi
RootLens       = Analizi yapan bizim sistemimiz
```

-   **Resmî proje:**
    https://github.com/open-telemetry/opentelemetry-demo
-   **Dokümantasyon:** https://opentelemetry.io/docs/demo/

------------------------------------------------------------------------

## 📊 Veriler Nereden Geliyor?

Projede sabit bir veri seti kullanılmamaktadır. Veriler, çalışan
Astronomy Shop mikroservislerinin oluşturduğu **telemetri verilerinden**
elde edilmektedir.

### 📈 Metrics

Sistemin sayısal durumunu gösterir. Örneğin istek süresi, hata oranı ve
servis performansı.

**Neden kullanıyoruz?** Bir servisin normal davranışından sapıp
sapmadığını anlamak için.

### 📄 Logs

Servislerin çalışırken oluşturduğu olay ve hata kayıtlarıdır.

**Neden kullanıyoruz?** Bir problem oluştuğunda ne olduğunu ve hatayla
ilgili ayrıntıları incelemek için.

### 🔗 Traces

Bir isteğin mikroservisler arasında izlediği yolu gösterir.

``` text
Frontend → Checkout → Payment → Shipping
```

**Neden kullanıyoruz?** Problemin hangi servis veya servisler arasındaki
iletişim sırasında başladığını incelemek için.

------------------------------------------------------------------------

## 🛠️ Kullanılan Teknolojiler

  -----------------------------------------------------------------------
  Teknoloji                           RootLens'te Ne İşe Yarıyor?
  ----------------------------------- -----------------------------------
  **Astronomy Shop**                  Analiz edeceğimiz gerçekçi
                                      mikroservis test ortamını sağlar

  **Docker**                          Servisleri container'lar içerisinde
                                      çalıştırır

  **Docker Compose**                  Çok sayıdaki container'ı birlikte
                                      başlatır ve yönetir

  **OpenTelemetry**                   Mikroservislerden metrics, logs ve
                                      traces telemetrisi toplar

  **Prometheus**                      Metrik verilerini toplamak ve
                                      sorgulamak için kullanılır

  **OpenSearch**                      Log verilerini saklamak ve
                                      sorgulamak için kullanılır

  **Jaeger**                          Trace verilerini ve servisler
                                      arasındaki istek akışını incelemek
                                      için kullanılır

  **Python / FastAPI**                RootLens analiz/backend
                                      servislerinde kullanılır

  **React**                           RootLens Dashboard arayüzünde
                                      kullanılır

  **Git / GitHub**                    Kod değişikliklerini,
                                      dokümantasyonu ve proje gelişimini
                                      takip etmek için kullanılır
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 🐳 Docker Neden Kullanılıyor?

Astronomy Shop tek bir programdan değil, birçok mikroservisten oluşur.
Her servisi bilgisayara ayrı ayrı kurmak yerine servisleri **Docker
container'ları** içerisinde çalıştırıyoruz.

**Docker Compose** ise bu container'ların birlikte başlatılmasını,
durdurulmasını ve yönetilmesini sağlar.

``` text
Docker         → Servisleri container olarak çalıştırır.
Docker Compose → Container'ları birlikte yönetir.
```

------------------------------------------------------------------------

# 💻 Kurulum ve Sistemi Çalıştırma

## 1. Gerekli Programlar

### Git

Projeyi GitHub'dan bilgisayara almak için gereklidir.

https://git-scm.com/

Kontrol:

``` bash
git --version
```

### Docker Desktop

Mikroservisleri ve diğer container'ları çalıştırmak için gereklidir.

https://www.docker.com/products/docker-desktop/

Kontrol:

``` bash
docker --version
```

Docker Compose kontrolü:

``` bash
docker compose version
```

------------------------------------------------------------------------

## 2. Projeyi GitHub'dan İndirme

Terminal, PowerShell veya VS Code terminalini açın:

``` bash
git clone https://github.com/betulyilddiz/GEDIK-2026-BITIRME-GRUP4.git
```

Proje klasörüne girin:

``` bash
cd GEDIK-2026-BITIRME-GRUP4
```

VS Code ile açmak için:

``` bash
code .
```

------------------------------------------------------------------------

## 3. Docker'ın Çalıştığını Kontrol Etme

Önce **Docker Desktop** açık olmalıdır.

``` bash
docker info
```

Docker bilgileri görüntüleniyorsa Docker çalışmaktadır.

------------------------------------------------------------------------

## 4. Astronomy Shop'u Çalıştırma

Astronomy Shop klasörüne girin:

``` bash
cd astronomy-shop
```

Klasördeki Compose dosyalarını görmek için:

``` bash
dir
```

Repository'deki Astronomy Shop sürümünde tek `compose.yaml`
kullanılıyorsa servisleri başlatmak için:

``` bash
docker compose up -d
```

`-d`, container'ların terminali meşgul etmeden arka planda çalışmasını
sağlar.

> **Not:** Astronomy Shop'un Compose yapısı sürüme göre değişebilir. Bu
> repository içerisinde bulunan Compose dosyaları esas alınmalıdır.

------------------------------------------------------------------------

## 5. Sistemin Çalıştığını Kontrol Etme

Çalışan container'ları görmek için:

``` bash
docker ps
```

Compose servislerinin durumunu görmek için:

``` bash
docker compose ps
```

Astronomy Shop çalıştığında frontend, checkout, payment, shipping,
recommendation, product-catalog, OpenTelemetry Collector ve telemetri
araçları gibi birçok servis/container çalışır.

------------------------------------------------------------------------

## 6. RootLens'i Çalıştırma

Ana proje klasörüne dönün:

``` bash
cd ..
```

RootLens klasörüne girin:

``` bash
cd rootlens
```

`rootlens/`, **bizim geliştirdiğimiz analiz platformunu** içerir.

RootLens klasöründeki mevcut Docker Compose yapılandırması kullanılarak
Analyzer, Dashboard ve gerekli RootLens servisleri başlatılır.

Çalışan RootLens container'larını kontrol etmek için:

``` bash
docker ps
```

> **Not:** RootLens'in kesin başlatma komutu repository içerisindeki
> güncel Compose dosyasının adına göre kullanılmalıdır.

------------------------------------------------------------------------

## 7. Sistem Açıldıktan Sonra Ne Oluyor?

``` text
1. Astronomy Shop mikroservisleri çalışır.
                     ↓
2. Servisler birbirleriyle haberleşir.
                     ↓
3. Metrics, logs ve traces telemetrisi oluşur.
                     ↓
4. OpenTelemetry telemetriyi toplar.
                     ↓
5. Prometheus / OpenSearch / Jaeger üzerinden veriler incelenir.
                     ↓
6. RootLens Analyzer bu kaynaklardan verileri alır.
                     ↓
7. Veriler analiz edilir.
                     ↓
8. Anormal davranış tespit edilir.
                     ↓
9. Olası kök neden belirlenir.
                     ↓
10. Sonuç RootLens Dashboard'da gösterilir.
```

------------------------------------------------------------------------

## 💥 Kontrollü Hata Senaryosu Nasıl Çalışacak?

Normal durumda:

``` text
Kullanıcı
   ↓
Checkout
   ↓
Payment
   ↓
Sipariş başarılı
```

Örneğin Payment servisinde kontrollü bir yavaşlama veya hata
oluşturulduğunda:

``` text
Payment Service
      ↓
Anormal davranış oluşur
      ↓
Telemetri verileri değişir
      ↓
RootLens verileri inceler
      ↓
Anomali tespit edilir
      ↓
Diğer telemetri kaynakları incelenir
      ↓
Olası kök neden belirlenir
      ↓
Dashboard'da gösterilir
```

Amaç yalnızca sistemde hata olduğunu göstermek değil, **problemin nerede
başladığını ve olası nedenini belirlemektir.**

------------------------------------------------------------------------

## 📋 Docker'da İşimize Yarayacak Komutlar

### Çalışan container'ları göster

``` bash
docker ps
```

### Tüm container'ları göster

``` bash
docker ps -a
```

### Compose servislerini göster

``` bash
docker compose ps
```

### Logları göster

``` bash
docker compose logs
```

### Logları canlı takip et

``` bash
docker compose logs -f
```

### Belirli bir container'ın logunu göster

``` bash
docker logs <container_adi>
```

### Servisleri yeniden başlat

``` bash
docker compose restart
```

### Servisleri durdur

``` bash
docker compose stop
```

### Compose ortamını kapat

``` bash
docker compose down
```

### Değişikliklerden sonra yeniden build ederek başlat

``` bash
docker compose up -d --build
```

------------------------------------------------------------------------

## ✅ Şu Ana Kadar Yapılanlar

### Astronomy Shop

-   Mikroservis test ortamı hazırlandı.
-   Servisler Docker ortamında çalıştırıldı.
-   Servisler arası iletişim yapısı incelendi.
-   Gerçek telemetri üreten test ortamı oluşturuldu.

### Telemetri

-   OpenTelemetry tabanlı telemetri altyapısı incelendi.
-   Prometheus erişimi test edildi.
-   OpenSearch erişimi test edildi.
-   Jaeger/trace entegrasyonu üzerinde çalışılmaktadır.

### RootLens

-   RootLens Analyzer servisi oluşturuldu.
-   RootLens Dashboard oluşturuldu.
-   Gerçek telemetri kaynaklarına erişim üzerinde çalışıldı.
-   Kontrollü hata senaryoları için temel yapı oluşturuldu.

### Proje Yönetimi

-   14 haftalık Gantt planı oluşturuldu.
-   Literatür araştırmasına başlandı.
-   Proje GitHub repository'sinde sürüm kontrolü altına alındı.

------------------------------------------------------------------------

## 🚀 Sonraki Hedefler

``` text
Mevcut mikroservis ve telemetri ortamı
                ↓
Metrics + Logs + Traces entegrasyonu
                ↓
Kontrollü hata senaryoları
                ↓
Normal / anormal davranış ayrımı
                ↓
Anomali tespit mekanizması
                ↓
Servis ilişkilerinin analizi
                ↓
Otomatik kök neden analizi
                ↓
RootLens Dashboard'da sonuçların gösterilmesi
                ↓
Test otomasyonu
                ↓
CI/CD
                ↓
Final sistem ve performans testleri
```

------------------------------------------------------------------------

## 📁 Repository Yapısı

``` text
GEDIK-2026-BITIRME-GRUP4/
│
├── astronomy-shop/
│   └── Analiz ettiğimiz OpenTelemetry mikroservis sistemi
│
├── rootlens/
│   └── Bizim geliştirdiğimiz RootLens analiz platformu
│
├── RootLens_14_Haftalik_Gantt_Plani.xlsx
│   └── 14 haftalık proje planı
│
├── RootLens_Literatur_Taramasi.xlsx
│   └── Literatür araştırması
│
└── README.md
    └── Proje açıklaması ve çalıştırma dokümantasyonu
```

------------------------------------------------------------------------

## 🔗 Resmî Kaynaklar

-   **OpenTelemetry:** https://opentelemetry.io/
-   **Astronomy Shop / OpenTelemetry Demo:**
    https://github.com/open-telemetry/opentelemetry-demo
-   **OpenTelemetry Demo Dokümantasyonu:**
    https://opentelemetry.io/docs/demo/
-   **Docker:** https://www.docker.com/
-   **Docker Compose:** https://docs.docker.com/compose/
-   **Prometheus:** https://prometheus.io/
-   **OpenSearch:** https://opensearch.org/
-   **Jaeger:** https://www.jaegertracing.io/
-   **FastAPI:** https://fastapi.tiangolo.com/
-   **React:** https://react.dev/

------------------------------------------------------------------------

## 📌 Kısa Özet

> **Astronomy Shop üzerinde çalışan mikroservislerden telemetri verileri
> üretilir. OpenTelemetry bu verileri toplar; Prometheus metrikleri,
> OpenSearch logları ve Jaeger trace'leri incelememizi sağlar. RootLens
> Analyzer bu kaynaklardan gelen verileri analiz ederek anormal
> davranışı ve problemin olası kök nedenini belirlemeyi, RootLens
> Dashboard ise sonucu kullanıcıya tek bir ekranda göstermeyi
> hedefler.**
