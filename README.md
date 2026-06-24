<div align="center">

<h1>🤖 Berkai - Dijital İkiz & RAG AI</h1>

<!-- Teknoloji Rozetleri -->
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-FF8C00?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Hugging Face](https://img.shields.io/badge/Hugging_Face-Spaces-F5C124?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/)

<br><br>

<!-- HTML Sohbet Kartı -->
<div style="background-color: #f8fafc; width: 300px; padding: 30px 20px; border-radius: 20px; border: 1px solid #e2e8f0; display: inline-block; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
  <img src="berkai.png" width="110" style="border-radius: 50%; border: 4px solid #f8fafc; margin-bottom: 5px;" alt="Berkai Profil">
  
  <h2 style="margin: 0; color: #0f172a; font-family: sans-serif;">Berkai</h2>
  <h4 style="margin: 5px 0 15px 0; color: #0f172a; font-family: sans-serif;">Yapay Ama Doğal Dostun</h4>
  
  <p style="color: #64748b; font-size: 14px; margin-bottom: 25px; font-family: sans-serif;">
    Berkay'ın dijital kopyasıyla sohbete başla
  </p>
  
  <a href="https://bekolomaniac-bekai.hf.space" target="_blank" style="display: inline-block; background-color: #2563eb; color: white; text-decoration: none; padding: 12px 0; width: 100%; border-radius: 10px; font-weight: bold; font-size: 16px; font-family: sans-serif;">
    Sohbete Başla
  </a>
</div>

<br><br>
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
