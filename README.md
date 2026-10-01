📌 Proje Nedir?

RootLens, mikroservis sistemlerinde oluşan anormal davranışları tespit etmeyi ve problemin hangi servisten kaynaklandığını belirlemeyi amaçlayan bir analiz platformudur.

Mikroservis sistemlerinde bir işlem birçok farklı servisten geçebilir. Bu nedenle bir hata oluştuğunda problemin kaynağını bulmak zorlaşabilir.

RootLens temel olarak şu soruya cevap vermeyi hedefler:

Sistemde ne sorun var, nerede başladı ve olası nedeni nedir?

🎯 Projenin Amacı

RootLens ile:

Mikroservislerin sağlık durumunu izlemek,

Metrics, logs ve traces verilerini toplamak,

Anormal davranışları tespit etmek,

Farklı telemetri kaynaklarını birlikte değerlendirmek,

Problemin olası kök nedenini belirlemek,

Sonucu tek bir dashboard üzerinden göstermek

hedeflenmektedir.

🔄 Sistem Nasıl Çalışıyor?

Sistemin tamamının mantığı kısaca şöyledir:

ASTRONOMY SHOP
Test ettiğimiz mikroservis sistemi
        │
        │ Çalışırken telemetri üretir
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
              Sonucu kullanıcıya
                    gösterir

Kısacası kim ne yapıyor?

Astronomy Shop → veriyi üreten sistemdir.

OpenTelemetry → verileri toplar.

Prometheus → metrikleri tutar/sorgular.

OpenSearch → logları tutar/sorgular.

Jaeger → isteklerin servisler arasındaki yolunu gösterir.

RootLens Analyzer → bu verileri analiz eden bizim geliştirdiğimiz bölümdür.

RootLens Dashboard → sonucu kullanıcıya gösteren bizim geliştirdiğimiz arayüzdür.

🛒 Astronomy Shop Nedir?

Astronomy Shop, OpenTelemetry tarafından geliştirilen açık kaynaklı bir mikroservis demo sistemidir.

Astronomy Shop bizim geliştirdiğimiz sistem değildir.

RootLens'i test edebilmek için çalışan gerçekçi bir mikroservis sistemine ihtiyacımız olduğu için kullanıyoruz.

İçerisinde örneğin:

Frontend

Cart

Checkout

Payment

Shipping

Product Catalog

Recommendation

Email

gibi birbirleriyle haberleşen servisler bulunur.

Neden kullanıyoruz?

RootLens'in analiz edebilmesi için önce analiz edilecek bir sistem ve bu sistemden gelen veriler gerekir.

Bu nedenle:

Astronomy Shop = Analiz edilen sistem
RootLens       = Analizi yapan sistem

Resmî Astronomy Shop / OpenTelemetry Demo:
https://github.com/open-telemetry/opentelemetry-demo

Dokümantasyon:
https://opentelemetry.io/docs/demo/

📊 Veriler Nereden Geliyor?

Projede sabit bir veri seti kullanılmamaktadır.

Verileri çalışan mikroservis sistemi üretmektedir.

Astronomy Shop çalışırken servisler birbirleriyle iletişim kurar ve telemetri verileri oluşur.

RootLens üç temel veri türünden yararlanacaktır:

📈 Metrics

Sistemin sayısal durumudur.

Örneğin:

İstek süresi

Hata oranı

Servis performansı

Neden?
Bir servisin normalden farklı davranıp davranmadığını anlamak için.

📄 Logs

Servislerin oluşturduğu olay ve hata kayıtlarıdır.

Neden?
Bir hata meydana geldiğinde ne olduğunu anlamak için.

🔗 Traces

Bir isteğin servisler arasında izlediği yolu gösterir.

Örneğin:

Frontend → Checkout → Payment → Shipping

Neden?
Problemin hangi servis veya servisler arasındaki iletişim sırasında başladığını anlamak için.

🛠️ Hangi Teknolojiyi Neden Kullanıyoruz?

Teknoloji

RootLens'teki Görevi

Astronomy Shop

Analiz edeceğimiz mikroservis sistemini sağlar

Docker

Servisleri container olarak çalıştırır

Docker Compose

Çok sayıdaki container'ı birlikte yönetir

OpenTelemetry

Mikroservislerden telemetri toplar

Prometheus

Metrics verilerini sağlar

OpenSearch

Log verilerini sağlar

Jaeger

Trace verilerini gösterir

Python / FastAPI

RootLens analiz/backend tarafında kullanılır

React

RootLens Dashboard arayüzünde kullanılır

Git

Kod değişikliklerini takip eder

GitHub

Kodları, dokümantasyonu ve proje gelişimini saklar

🐳 Docker Neden Gerekli?

Astronomy Shop tek bir program değildir.

Birçok servis aynı anda çalışmaktadır:

Frontend
Checkout
Payment
Cart
Shipping
Recommendation
Product Catalog
OpenTelemetry Collector
Prometheus
OpenSearch
...

Bunların her birini bilgisayara ayrı ayrı kurmak yerine Docker container'ları içerisinde çalıştırıyoruz.

Docker Compose ise bu container'ların birlikte başlatılmasını ve yönetilmesini sağlar.

Yani:

Docker
   ↓
Servisleri container haline getirir

Docker Compose
   ↓
Bu container'ları birlikte yönetir

💻 Kurulum ve Sistemi Çalıştırma

1. Gerekli Programlar

Bilgisayarda şunların kurulu olması gerekir:

Git

Projeyi GitHub'dan bilgisayara almak için:

https://git-scm.com/

Kontrol:

git --version

Docker Desktop

Mikroservisleri ve diğer container'ları çalıştırmak için:

https://www.docker.com/products/docker-desktop/

Docker Desktop'ı açtıktan sonra kontrol:

docker --version

Docker Compose kontrolü:

docker compose version

2. Projeyi GitHub'dan İndirme

Terminal veya VS Code terminalini açın.

git clone https://github.com/betulyilddiz/GEDIK-2026-BITIRME-GRUP4.git

Proje klasörüne girin:

cd GEDIK-2026-BITIRME-GRUP4

VS Code'da açmak için:

code .

3. Docker'ın Çalıştığını Kontrol Etme

Önce Docker Desktop açık olmalıdır.

Terminal:

docker info

Docker bilgileri geliyorsa Docker çalışmaktadır.

4. Astronomy Shop'u Başlatma

Astronomy Shop klasörüne girin:

cd astronomy-shop

Önce mevcut Compose dosyalarını kontrol edin:

dir

Repository'de bulunan Compose yapılandırmasına göre Astronomy Shop başlatılır.

Tek compose.yaml kullanılan proje sürümünde:

docker compose up -d

kullanılır.

-d sayesinde container'lar arka planda çalışmaya devam eder.

Önemli: OpenTelemetry Demo'nun güncel sürümü birden fazla Compose dosyası kullanabilmektedir. Bu nedenle bu repository'de bulunan Astronomy Shop sürümünün Compose dosyaları esas alınmalıdır.

5. Sistem Gerçekten Çalışıyor mu?

Terminalde:

docker ps

çalıştırılır.

Bu komut çalışan container'ları gösterir.

Örneğin:

frontend
checkout
payment
shipping
recommendation
product-catalog
otel-collector
prometheus
opensearch
...

gibi servislerin çalıştığı görülebilir.

Daha ayrıntılı Compose durumu için:

docker compose ps

6. Bundan Sonra Ne Oluyor?

Docker servisleri ayağa kaldırdıktan sonra sistem kendi içinde çalışmaya başlar.

1. Astronomy Shop çalışır
            ↓
2. Mikroservisler birbirleriyle haberleşir
            ↓
3. Metrics, logs ve traces oluşur
            ↓
4. OpenTelemetry bunları toplar
            ↓
5. Prometheus / OpenSearch / Jaeger'a aktarılır
            ↓
6. RootLens bu kaynaklardan verileri alır
            ↓
7. RootLens Analyzer verileri analiz eder
            ↓
8. Sonuç RootLens Dashboard'da gösterilir

Yani Docker yalnızca uygulamayı açmıyor; analiz edeceğimiz bütün mikroservis ortamını ayağa kaldırıyor.

7. RootLens'i Çalıştırma

Ana proje klasörüne geri dönün:

cd ..

RootLens klasörüne girin:

cd rootlens

Bu klasör içerisinde bizim geliştirdiğimiz RootLens platformu bulunmaktadır.

RootLens'in mevcut Docker Compose yapılandırması kullanılarak Analyzer, Dashboard ve gerekli RootLens servisleri başlatılır.

RootLens klasöründeki Compose dosyasının kesin adı ve çalıştırma komutu repository'deki mevcut yapı kontrol edilerek burada sabitlenmelidir.

Başlatıldıktan sonra çalışan RootLens container'larını görmek için:

docker ps

kullanılır.

8. Sistemin Tam Çalışma Akışı

Sistemi çalıştırdığımızda arka planda olan şey tam olarak şudur:

KULLANICI / LOAD GENERATOR
            │
            ▼
     ASTRONOMY SHOP
            │
     Servisler çalışır
            │
            ▼
   TELEMETRİ OLUŞUR
            │
     ┌──────┼──────┐
     ▼      ▼      ▼
  Metrics  Logs  Traces
     │      │      │
     ▼      ▼      ▼
Prometheus OpenSearch Jaeger
     │      │      │
     └──────┼──────┘
            ▼
     ROOTLENS ANALYZER
            │
      Verileri inceler
            │
            ▼
      Anomali Tespiti
            │
            ▼
      Kök Neden Analizi
            │
            ▼
     ROOTLENS DASHBOARD
            │
            ▼
      Kullanıcı Sonucu
            Görür

💥 Kontrollü Hata Nasıl Test Edilecek?

Örneğin sistem normal çalışırken:

Kullanıcı
   ↓
Checkout
   ↓
Payment
   ↓
Sipariş başarılı

Payment servisinde kontrollü bir yavaşlama/hata oluşturulduğunda:

Payment Service
      ↓
Anormal davranış
      ↓
Telemetri değişir
      ↓
RootLens veriyi alır
      ↓
Anomali tespit edilir
      ↓
Diğer telemetri kaynakları incelenir
      ↓
Olası kök neden belirlenir
      ↓
Dashboard'da gösterilir

Böylece RootLens'in yalnızca normal sistemi göstermesi değil, problemin nerede başladığını bulması hedeflenmektedir.

📋 Docker'da İşimize Yarayacak Komutlar

Çalışan container'ları göster

docker ps

Tüm container'ları göster

docker ps -a

Compose servislerini göster

docker compose ps

Logları göster

docker compose logs

Logları canlı takip et

docker compose logs -f

Belirli container'ın logunu göster

docker logs <container_adi>

Servisleri yeniden başlat

docker compose restart

Servisleri durdur

docker compose stop

Ortamı kapat

docker compose down

Değişikliklerden sonra yeniden build et

docker compose up -d --build

✅ Şu Ana Kadar Ne Yaptık?

Astronomy Shop tarafı

Mikroservis test ortamı hazırlandı.

Docker üzerinden servisler çalıştırıldı.

Servislerin birbirleriyle iletişimi incelendi.

Gerçek telemetri üreten bir test ortamı oluşturuldu.

Telemetri tarafı

OpenTelemetry altyapısı incelendi.

Prometheus erişimi test edildi.

OpenSearch erişimi test edildi.

Trace/Jaeger entegrasyonu üzerinde çalışılmaktadır.

RootLens tarafı

RootLens Analyzer oluşturuldu.

RootLens Dashboard oluşturuldu.

Telemetri kaynaklarından gerçek veri alma altyapısı üzerinde çalışıldı.

Kontrollü hata senaryoları için temel yapı oluşturuldu.

Proje yönetimi

14 haftalık Gantt planı oluşturuldu.

Literatür araştırmasına başlandı.

Proje GitHub repository'si oluşturuldu.

🚀 Bundan Sonra Ne Yapacağız?

ŞU AN
   ↓
Astronomy Shop çalışıyor
   ↓
RootLens temel yapısı oluşturuldu
   ↓
Telemetri kaynaklarına erişiliyor
   ↓
────────────────────────
SONRAKİ AŞAMALAR
   ↓
Metrics + Logs + Traces birlikte alınacak
   ↓
Kontrollü hatalar oluşturulacak
   ↓
Normal ve anormal davranış ayrılacak
   ↓
Anomali tespit mekanizması geliştirilecek
   ↓
Servisler arasındaki ilişkiler analiz edilecek
   ↓
Otomatik kök neden analizi geliştirilecek
   ↓
Sonuç RootLens Dashboard'da gösterilecek
   ↓
Test otomasyonu eklenecek
   ↓
CI/CD eklenecek
   ↓
Final sistem test edilecek

📁 Repository Yapısı

GEDIK-2026-BITIRME-GRUP4/
│
├── astronomy-shop/
│   └── Analiz ettiğimiz mikroservis sistemi
│
├── rootlens/
│   └── Bizim geliştirdiğimiz analiz platformu
│
├── RootLens_14_Haftalik_Gantt_Plani.xlsx
│   └── 14 haftalık proje planı
│
├── RootLens_Literatur_Taramasi.xlsx
│   └── Literatür araştırması
│
└── README.md
    └── Projenin açıklaması ve çalıştırma dokümantasyonu

🔗 Resmî Kaynaklar

OpenTelemetry: https://opentelemetry.io/

Astronomy Shop / OpenTelemetry Demo: https://github.com/open-telemetry/opentelemetry-demo

OpenTelemetry Demo Dokümantasyonu: https://opentelemetry.io/docs/demo/

Docker: https://www.docker.com/

Docker Compose: https://docs.docker.com/compose/

Prometheus: https://prometheus.io/

OpenSearch: https://opensearch.org/

Jaeger: https://www.jaegertracing.io/

FastAPI: https://fastapi.tiangolo.com/

React: https://react.dev/

📌 Projenin Tek Cümlelik Özeti

Astronomy Shop üzerinde çalışan mikroservislerden telemetri verilerini topluyoruz; RootLens bu verileri analiz ederek anormal davranışı ve problemin olası kök nedenini bulup kullanıcıya tek bir dashboard üzerinden göstermeyi hedefliyor.
