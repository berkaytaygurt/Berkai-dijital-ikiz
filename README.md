<div align="center">

#Berkai - Dijital İkiz & RAG AI

### Yapay Ama Doğal Dostunuz

*Berkay'a ulaşamadığınız anlarda yerini aratmayacak dijital bir dost.*

[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-FF8C00?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Hugging Face](https://img.shields.io/badge/Hugging_Face-Spaces-F5C124?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/)

<h3><a href="https://bekolomaniac-berkai.hf.space"><b>berkai konuş</b></a></h3>

</div>

---

## 📌 Proje Özeti
Bu proje, **LangChain, ChromaDB ve Google Gemini** mimarisi kullanılarak geliştirilmiş, bağlam farkındalığına sahip (context-aware) kişisel bir yapay zeka asistanıdır. Berkai, sadece soğuk sorulara cevap veren standart bir bot değil; kullanıcının kimliğini tanıyan, geçmiş diyalogları hatırlayan ve aradaki samimiyet derecesine göre üslubunu dinamik olarak ayarlayabilen doğal bir "dijital ikiz" simülasyonudur.

## 🏗️ Hibrit Sistem Mimarisi

Maliyet optimizasyonu ve veri gizliliğini en üst düzeyde tutmak için sistem iki izole parçaya ayrılmıştır:

| Bileşen | Konum | İşlev | Gizlilik |
| :--- | :--- | :--- | :--- |
| **Ön Yüz & Sunucu** | Hugging Face (Docker) | Arayüz yayını ve Flask routing. Uçucu (ephemeral) çalışır. | 🔓 Public |
| **Veritabanı & Hafıza** | GitHub (Private Repo) | Kişi profilleri, RAG hafızası ve ChromaDB verileri. | 🔒 Private |

> ⚙️ **Çalışma Mantığı:** Sunucu her başlatıldığında, güvenli bir tünel üzerinden gizli repodaki verileri anlık olarak çeker. Dışarıdan bağlanan bir kullanıcı arayüze erişebilir ancak arka plandaki vektör veritabanına asla ulaşamaz.

## 🚀 Temel Özellikler

- **🎭 Dinamik Üslup Adaptasyonu:** Vektörel hafızadan çekilen geçmiş sohbetlerin tonuna göre asistanın üslubu (resmi/samimi) otomatik şekillenir.
- **🛡️ Güvenlik Kalkanı:** Sadece önceden tanımlı şifreyi bilen kullanıcılar sisteme erişebilir.
- **🚦 Gelişmiş Rate Limit:** Kötü niyetli kullanımı engellemek için IP tabanlı giriş ve token tabanlı mesaj limitleri aktiftir.
- **💰 Bütçe Kontrolü:** Maksimum aylık API maliyeti kilitleri sisteme hard-coded olarak entegre edilmiştir.

---

<div align="center">
  <b>Geliştirici:</b> Berkay Taygurt | Yapay Zeka Mühendisliği, Hacettepe Üniversitesi
</div>
