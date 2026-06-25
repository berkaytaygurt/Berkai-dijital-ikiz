<div align="center">

<h1>🤖 Berkai - Dijital İkiz & RAG AI</h1>

<!-- Teknoloji Rozetleri -->
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-FF8C00?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Hugging Face](https://img.shields.io/badge/Hugging_Face-Spaces-F5C124?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/)

<br><br>

<h3>👇 <b>Sohbete Başlamak İçin Tıklayın</b> 👇</h3>

<!-- Tıklanabilir Yan Yana Görseller -->
<table>
  <tr>
    <td align="center">
      <a href="https://bekolomaniac-berkai.hf.space" target="_blank">
        <img src="https://github.com/user-attachments/assets/e694d84b-cc0f-405c-ae25-5cc09d8e3f57" width="320" alt="Giriş Ekranı" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
      </a>
    </td>
    <td align="center">
      <a href="https://bekolomaniac-berkai.hf.space" target="_blank">
        <img src="https://github.com/user-attachments/assets/e2f454d4-f6de-4ad2-a6e6-e88812e29d64" width="320" alt="Sohbet Ekranı" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
      </a>
    </td>
  </tr>
</table>

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
  <br>
  <b>Geliştirici:</b> Berkay Taygurt | Yapay Zeka Mühendisliği, Hacettepe Üniversitesi
</div>
