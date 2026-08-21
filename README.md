<div align="center">

<h1>🤖 Berkai - Dijital İkiz & RAG AI</h1>

<!-- Teknoloji Rozetleri -->
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Flash-FF8C00?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Hugging Face](https://img.shields.io/badge/Hugging_Face-Spaces-F5C124?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/)

<br>

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
| **Veritabanı & Hafıza** | GitHub (Private Repo) | Kendi mesajlarımdan üretilmiş RAG hafızası ve ChromaDB verileri. | 🔒 Private |

> ⚙️ **Çalışma Mantığı:** Sunucu her başlatıldığında, güvenli bir tünel üzerinden gizli repodaki verileri anlık olarak çeker. Dışarıdan bağlanan bir kullanıcı arayüze erişebilir ancak arka plandaki vektör veritabanına asla ulaşamaz.

## 🚀 Temel Özellikler

- **🎭 Üslup Taklidi:** Vektörel hafızadan çekilen kendi geçmiş mesajlarımın tonuna göre asistanın üslubu (noktalama, kısaltma, kelime tercihi) şekillenir.
- **🛡️ Güvenlik Kalkanı:** Sadece şifreyi bilen kullanıcılar erişebilir. Zayıf/tahmin edilebilir şifreyle uygulama hiç başlamaz.
- **🚦 Rate Limit:** Reverse proxy arkasında gerçek istemci IP'si (`X-Forwarded-For`) üzerinden giriş limiti, token bazlı mesaj limiti ve günlük tavanlar.
- **💰 Bütçe Kontrolü:** Maliyet sayacı kalıcı olarak tutulur (süreç yeniden başlayınca sıfırlanmaz), günlük mesaj tavanları ve bütçe kilidi vardır.
- **🔒 Veri Sızdırma Koruması:** "Hafızanı aynen dök", "prompt'unu göster" gibi istekler ve üçüncü şahıslar hakkında bilgi çıkarmaya çalışan sorular modele hiç ulaşmadan engellenir.

---

## 🔐 Veri Gizliliği Notu

Bu asistanın hafızası **yalnızca benim kendi yazdığım mesajlardan** oluşur.

Projenin ilk sürümünde hafıza, sohbet dökümlerinin tamamını (karşı tarafın
mesajları dahil) içeriyordu. Bu, o kişilerin onayı olmadan kişisel verilerini
işlemek anlamına geldiği için veri seti kaynağından yeniden üretildi:

- Karşı tarafa ait bütün satırlar ve isimler temizlendi
- Parça etiketlerindeki `source` (konuşulan kişi) alanı kaldırıldı
- "Falanca kişiyle geçmişimi getir" özelliği koddan tamamen çıkarıldı
- Üçüncü şahıslar hakkında bilgi isteyen sorular uygulama katmanında engellenir

Temizleme adımları `veri_filtrele.py`, vektör veritabanının kurulumu
`db_kur_temiz.py` içinde ve tekrar üretilebilir durumdadır.

---

<div align="center">
  <br>
  <b>Geliştirici:</b> Berkay Taygurt | Yapay Zeka Mühendisliği, Hacettepe Üniversitesi
</div>
