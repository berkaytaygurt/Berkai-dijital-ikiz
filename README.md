# 🤖 Berkai - Dijital İkiz & RAG Tabanlı Yapay Zeka Asistanı
# Yapay Ama Doğal Dostunuz

> *"Berkay'a ulaşamadığınız anlarda yerini aratmayacak dijital bir dost."*

Bu proje, LangChain, ChromaDB ve Google Gemini mimarisi kullanılarak geliştirilmiş, bağlam farkındalığına sahip (context-aware) kişisel bir yapay zeka asistanıdır. Berkai, sadece soğuk sorulara cevap veren standart bir bot değil; kullanıcının kimliğini tanıyan, geçmiş diyalogları ve anıları hatırlayan, aradaki samimiyet derecesine göre üslubunu dinamik olarak ayarlayabilen doğal bir "dijital ikiz" simülasyonudur.

## 🏗️ Proje Mimarisi (Hibrit Sistem)

Maliyet optimizasyonu ve veri gizliliğini sağlamak amacıyla sistem ikiye ayrılmıştır:
* **Public Ön Yüz:** Uygulama arayüzü ve web sunucusu Hugging Face Spaces (Docker) üzerinde uçucu (ephemeral) olarak çalışır.
* **Private Veritabanı:** Kişi profilleri ve RAG hafızası (ChromaDB) ayrı bir gizli GitHub reposunda tutulur. Sunucu her başlatıldığında bu verileri güvenli bir tünel üzerinden anlık olarak çeker.

## 🚀 Kullanılan Teknolojiler

* **Backend:** Python 3.10, Flask
* **AI & NLP:** LangChain, Google Gemini 2.5 Flash, Generative AI Embeddings
* **Veri Yönetimi:** ChromaDB, SQLite
* **Deployment:** Hugging Face Spaces, Docker, Git

## 💡 Temel Özellikler

* **Doğal ve Dinamik Üslup:** Vektörel hafızadan çekilen geçmiş sohbetlerin tonuna göre asistanın üslubu otomatik şekillenir (resmi veya samimi).
* **Erişim ve Bütçe Kontrolü:** Sisteme özel kimlik doğrulama, IP tabanlı rate-limit ve token tabanlı maksimum maliyet kilitleri entegre edilmiştir.

---
**Geliştirici:** Berkay Taygurt | Yapay Zeka Mühendisliği, Hacettepe Üniversitesi
