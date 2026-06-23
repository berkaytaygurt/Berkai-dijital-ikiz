import os
import sqlite3
import re
import json
import secrets
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# ─── GÜVENLİK: ZORUNLU ŞİFRE KONTROLÜ ────────────────────────
# .env dosyasında APP_PASSWORD tanımlı değilse uygulama HİÇ AÇILMASIN.
# Sabit/zayıf bir varsayılan şifre ("berkay123" gibi) kodun içinde
# durmasın — biri .env'i unutursa/silerse açık şifreyle internete
# çıkmasın.
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
if not APP_PASSWORD:
    raise RuntimeError(
        "❌ APP_PASSWORD tanımlı değil! .env dosyasına APP_PASSWORD=... ekle "
        "(ya da hosting panelinde environment variable olarak gir). "
        "Güvenlik için varsayılan/sabit şifreyle çalıştırmıyoruz."
    )

# ─── PROFİL JSON ─────────────────────────────────────────────
try:
    with open("berkay_profil.json", "r", encoding="utf-8") as f:
        BERKAY_SABIT_PROFIL = json.dumps(json.load(f), ensure_ascii=False, indent=2)
    print("✅ Profil JSON yüklendi.")
except Exception as e:
    print("⚠️ Profil JSON bulunamadı:", e)
    BERKAY_SABIT_PROFIL = "Berkay Taygurt."

# ─── CHROMADB ────────────────────────────────────────────────
VERITABANI_KLASORU = "./berkay_tam_hafiza_db"
print("🚀 RAG Hafızası Yükleniyor...")
embeddings   = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_store = Chroma(persist_directory=VERITABANI_KLASORU, embedding_function=embeddings)

# ─── SQLITE ──────────────────────────────────────────────────
session_conn = sqlite3.connect("berkai_oturum_hafizasi.db", check_same_thread=False)
session_conn.execute("""
    CREATE TABLE IF NOT EXISTS oturum_mesajlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kisi TEXT, rol TEXT, mesaj TEXT, zaman TEXT
    )
""")
session_conn.commit()

# ─── GEMINI ──────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.85,
    max_tokens=250,
    thinking_budget=0
)

# ─── GÜVENLİK: TOKEN + RATE LIMIT ────────────────────────────
aktif_oturumlar = {}   # token → isim
giris_denemeleri = {}  # ip → [timestamp listesi]

BUTCE_LIMITI_USD = 3.0     # ~100 TL
RATE_LIMIT_GIRIS = 5       # aynı IP'den 5 dakikada max 5 giriş denemesi
RATE_LIMIT_MESAJ = 60      # aynı token'dan dakikada max 60 mesaj
mesaj_sayaci = {}           # token → [timestamp listesi]

def ip_rate_limit_kontrol(ip):
    """Brute-force koruması: 5 dakikada 5'ten fazla giriş denemesini engelle."""
    simdi = time.time()
    pencere = 300  # 5 dakika
    denemeler = giris_denemeleri.get(ip, [])
    denemeler = [t for t in denemeler if simdi - t < pencere]
    if len(denemeler) >= RATE_LIMIT_GIRIS:
        return False
    denemeler.append(simdi)
    giris_denemeleri[ip] = denemeler
    return True

def mesaj_rate_limit_kontrol(token):
    """Spam koruması: Aynı token dakikada 60'tan fazla mesaj gönderemesin."""
    simdi = time.time()
    pencere = 60  # 1 dakika
    mesajlar = mesaj_sayaci.get(token, [])
    mesajlar = [t for t in mesajlar if simdi - t < pencere]
    if len(mesajlar) >= RATE_LIMIT_MESAJ:
        return False
    mesajlar.append(simdi)
    mesaj_sayaci[token] = mesajlar
    return True

# ─── MALİYET ─────────────────────────────────────────────────
GIRIS_FIYATI   = 0.30
CIKIS_FIYATI   = 2.50
TOPLAM_MALIYET = 0.0
TOPLAM_GIRIS_TOKEN = 0
TOPLAM_CIKIS_TOKEN = 0

def maliyet_hesapla(cevap_obj):
    global TOPLAM_MALIYET, TOPLAM_GIRIS_TOKEN, TOPLAM_CIKIS_TOKEN
    try:
        k = cevap_obj.usage_metadata
        g, c = k.get("input_tokens", 0), k.get("output_tokens", 0)
    except:
        try:
            k = cevap_obj.response_metadata.get("usage_metadata", {})
            g, c = k.get("prompt_token_count", 0), k.get("candidates_token_count", 0)
        except:
            return 0.0
    maliyet = (g / 1_000_000 * GIRIS_FIYATI) + (c / 1_000_000 * CIKIS_FIYATI)
    TOPLAM_GIRIS_TOKEN += g
    TOPLAM_CIKIS_TOKEN += c
    TOPLAM_MALIYET += maliyet
    print(f"💰 {g}g+{c}c → ${maliyet:.6f} | Toplam: ${TOPLAM_MALIYET:.6f}")
    return maliyet

# ─── OTURUM HAFIZASI ─────────────────────────────────────────
def oturum_kaydet(kisi, rol, mesaj):
    session_conn.execute(
        "INSERT INTO oturum_mesajlari (kisi,rol,mesaj,zaman) VALUES (?,?,?,?)",
        (kisi, rol, mesaj, datetime.now().isoformat())
    )
    session_conn.commit()

def oturum_getir(kisi, limit=8):
    cursor = session_conn.execute(
        "SELECT rol, mesaj FROM oturum_mesajlari WHERE kisi=? ORDER BY id DESC LIMIT ?",
        (kisi, limit)
    )
    rows = cursor.fetchall()
    rows.reverse()
    return rows

# ─── ARAMA FONKSİYONLARI ─────────────────────────────────────
KARA_LISTE = {
    "whatsapp","sistem","grup","yönetici","admin",
    "sen","ben","siz","biz","mesaj","arama",
    "berkaytaygurt","berkay","berkai"
}

def taninan_kisileri_cek():
    try:
        hepsi = vector_store.get()
        isimler = set()
        for meta in (hepsi.get("metadatas") or []):
            if meta and "source" in meta:
                isim = meta["source"].replace("\u200e","").strip()
                if isim and len(isim) > 2 and isim.lower() not in KARA_LISTE:
                    isimler.add(isim)
        return sorted(isimler)
    except:
        return []

TANINAN_KISILER = taninan_kisileri_cek()
print(f"👥 {len(TANINAN_KISILER)} kişi bulundu")

def akilli_sorgu(gelen_mesaj, oturum_gecmisi):
    if len(gelen_mesaj.split()) <= 3 and oturum_gecmisi:
        son = " ".join([m for _, m in oturum_gecmisi[-3:]])
        return f"{son} {gelen_mesaj}"[:300]
    return gelen_mesaj

def mesajdaki_isimleri_bul(mesaj):
    kelimeler = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]+", mesaj)
    bulunanlar = set()
    for k in kelimeler:
        if len(k) < 3:
            continue
        for kisi in TANINAN_KISILER:
            if k.lower() == kisi.lower() or k.lower() in kisi.lower():
                bulunanlar.add(kisi)
    return bulunanlar

def keyword_ara(isim, max_sonuc=5):
    sonuclar = []
    try:
        hepsi = vector_store.get(include=["documents","metadatas"])
        for doc in hepsi.get("documents",[]):
            if doc and isim.lower() in doc.lower():
                sonuclar.append(doc)
            if len(sonuclar) >= max_sonuc:
                break
    except:
        pass
    return sonuclar

def hafizayi_ara(konusulan_kisi, sorgu):
    parcalar = []
    try:
        kisi_sonuc = vector_store.similarity_search(
            query=sorgu, k=5, filter={"source": konusulan_kisi.lower().strip()}
        )
        for i, doc in enumerate(kisi_sonuc):
            parcalar.append(f"[{konusulan_kisi} ile geçmiş {i+1}]:\n{doc.page_content}")
    except:
        pass
    try:
        genel = vector_store.similarity_search(query=sorgu, k=5)
        for i, doc in enumerate(genel):
            if not any(doc.page_content in p for p in parcalar):
                parcalar.append(f"[Genel hafıza {i+1}]:\n{doc.page_content}")
    except:
        pass
    for isim in mesajdaki_isimleri_bul(sorgu) - {konusulan_kisi}:
        for doc in keyword_ara(isim):
            if not any(doc in p for p in parcalar):
                parcalar.append(f"[{isim} hakkında]:\n{doc}")
    return "\n\n".join(parcalar)

def uslup_cek(sorgu, k=6):
    try:
        sonuclar = vector_store.similarity_search(query=sorgu, k=k)
        satirlar = []
        for doc in sonuclar:
            for satir in doc.page_content.split("\n"):
                satir = satir.strip()
                if satir.lower().startswith(("berkaytaygurt:","berkay:")):
                    temiz = satir.split(":",1)[1].strip()
                    if temiz and len(temiz) > 5:
                        satirlar.append(temiz)
        return "\n".join(satirlar[:12])
    except:
        return ""

def hyde_hafiza_zenginlestir(gelen_mesaj, oturum_gecmisi):
    """
    HyDE — Doğru kullanım:
    Gemini'den olası isimler üretir, sadece ChromaDB'de GERÇEKTEN GEÇENLERI döner.
    Geçmeyenleri sessizce atar — "bilmiyorum" dedirtmez, genel bilgiyle devam eder.
    """
    TETIKLEYICILER = [
        "kim var", "kimler var", "kadro", "oyuncular", "hangi oyuncu",
        "takımda kim", "kadroda kim", "kim oynuyor", "transfer",
        "gitti mi", "geldi mi", "aldılar mı", "hala var mı", "oynuyor mu"
    ]
    if not any(t in gelen_mesaj.lower() for t in TETIKLEYICILER):
        return ""

    baglamli = gelen_mesaj
    if oturum_gecmisi:
        son = " ".join([m for _, m in oturum_gecmisi[-2:]])
        baglamli = f"{son} {gelen_mesaj}"

    try:
        tahmin = llm.invoke([
            SystemMessage(content="Sadece virgülle ayrılmış isimler yaz, başka hiçbir şey yazma."),
            HumanMessage(content=f'"{baglamli}" sorusuna verilebilecek 6-8 spesifik isim yaz. Örnek: "Talisca, Dzeko, Fred, Szymanski"')
        ])
        isimler = [i.strip() for i in tahmin.content.split(",") if i.strip()]
    except:
        return ""

    hafizada_olanlar = []
    for isim in isimler[:8]:
        try:
            sonuclar = vector_store.similarity_search(query=isim, k=3)
            if any(isim.lower() in doc.page_content.lower() for doc in sonuclar):
                hafizada_olanlar.append(isim)
        except:
            pass

    if not hafizada_olanlar:
        return ""

    return f"Sohbetlerinde geçen ilgili isimler: {', '.join(hafizada_olanlar)}"

def arkadaslar_sorusu_mu(mesaj):
    m = mesaj.lower()
    return any(t in m for t in ["arkadaş","tanıyor","tanıdık","kimle","kimi","kimler","kişi","konuş","sohbet"])

# ─── ANA FONKSİYON ───────────────────────────────────────────
def berkai_cevap_ver(konusulan_kisi, gelen_mesaj):
    oturum      = oturum_getir(konusulan_kisi, limit=8)
    sorgu       = akilli_sorgu(gelen_mesaj, oturum)
    eski_baglam = hafizayi_ara(konusulan_kisi, sorgu)
    uslup       = uslup_cek(sorgu, k=8)

    hyde_sonuc = hyde_hafiza_zenginlestir(gelen_mesaj, oturum)

    oturum_metni = ""
    for rol, mesaj in oturum:
        ad = "Ben" if rol == "berkai" else konusulan_kisi
        oturum_metni += f"{ad}: {mesaj}\n"

    arkadas_blok = ""
    if arkadaslar_sorusu_mu(gelen_mesaj) and TANINAN_KISILER:
        arkadas_blok = f"\n═══ TANINDIĞIN KİŞİLER ═══\n{', '.join(TANINAN_KISILER)}\nDoğal anlat, liste gibi okuma.\n"

    hyde_blok = ""
    if hyde_sonuc:
        hyde_blok = f"\n═══ SOHBETLERDEN DOĞRULANAN İSİMLER ═══\n{hyde_sonuc}\nBu isimleri 'evet bunları konuşmuştuk/biliyorum' diye kullan. Listede olmayanlara genel bilginle cevap ver, 'bilmiyorum' deme.\n"

    system_prompt = f"""Sen Berkay Taygurt'sun. Bu senin sabit kimlik profilin:

{BERKAY_SABIT_PROFIL}

═══ KARAKTER — EN ÖNEMLİ ŞEY BU ═══
Sen sadece soru cevaplayan biri değilsin, gerçek bir arkadaşsın. Takılırsın, dalga geçersin, hafif komiksin, karşındakinin duygusuna/derdine de kafa yorarsın — "naber" sorusuna bile düz cevap değil, esprili/sahici bir tepki verirsin. Karşındaki bir şey anlatırsa sadece bilgi verme, ona da takıl, şaka yap, duygusuna ortak ol. Robotik, kuru, sıra cevap veren biri gibi olma. Aşağıdaki kurallar bu karakteri BOZMAMAK için var.

─── YAZIM TARZI — EN KRİTİK KURAL ───
Aşağıda KENDİ YAZIM ÖRNEKLERİN var. O cümlelerin kurulum biçimini, kelime seçimini, noktalama alışkanlığını taklit et. Düzgün/edebi cümle kurma. Whatsapp'ta nasıl yazıyorsan öyle yaz.

─── HER CEVABIN SONUNA SORU EKLEME ───
VARSAYILAN DAVRANIŞ: Cevabını soru sormadan, düz bir cümleyle bitir. Gerçek bir arkadaş her mesajına soru eklemez.
"niye sordun ki?", "ne oldu ki sordun?", "sen nasılsın bu aralar?", "ne var ne yok senden?", "iyi misin bu aralar?" gibi jenerik kapanış kalıplarını KULLANMA — mekanik duruyor.
Soru sormak istersen (cevapların azınlığında), o konuşmaya özel, bağlama uygun bir soru sor.

─── BİLGİ KURALI ───
İKİ TÜR BİLGİ VAR:
1. GENEL BİLGİ (futbol, film, oyun, teknoloji, gündem): Direkt cevap ver, "sayamam/aklıma gelmiyor" deme.
2. KİŞİSEL DETAYLAR (karşındakinin özel hayatı): Eğer GEÇMİŞ ANILARIN'da bilgi varsa kullan. Gerçekten yoksa geçiştir, "o kadar detay aklımda kalmamış" de — "hatırlamıyorum/hafızamda yok" gibi yapay zeka çağrıştıran ifadeler kullanma.

─── FİZİKSEL SORULAR ───
"Neredesin", "ne zaman gelirsin" → bahane bul ("şu an dışarıdayım" gibi), yapay zeka olduğunu söyleme.

─── HAFIZA / KİMLİK ───
Anıları kullan ama "mesajlarına baktım" deme, kendi aklından geliyormuş gibi söyle. Sen ÜÇÜNCÜ ŞAHIS bir "hafıza/asistan" değilsin, doğrudan Berkay'sın.

Karşındaki: {konusulan_kisi}

═══ KENDİ YAZIM ÖRNEKLERİN — BUNU TAKLİT ET ═══
{uslup if uslup else "kısa, samimi, whatsapp tarzı yaz"}

═══ GEÇMİŞ ANILARIN ═══
{eski_baglam if eski_baglam else "Bu konuda geçmiş yok."}
{hyde_blok}{arkadas_blok}
═══ BU OTURUMDAKİ SOHBET ═══
{oturum_metni if oturum_metni else "İlk mesaj."}"""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=gelen_mesaj)]
    cevap = llm.invoke(messages)
    cevap_metni = cevap.content

    try:
        if cevap.response_metadata.get("finish_reason","") == "MAX_TOKENS":
            k2 = SystemMessage(content=system_prompt + "\n\nBu sefer 1-2 cümleyle bitir.")
            cevap = llm.invoke([k2, HumanMessage(content=gelen_mesaj)])
            cevap_metni = cevap.content
    except:
        pass

    maliyet = maliyet_hesapla(cevap)
    oturum_kaydet(konusulan_kisi, "kullanici", gelen_mesaj)
    oturum_kaydet(konusulan_kisi, "berkai", cevap_metni)
    return cevap_metni, maliyet

# ─── FLASK ROUTES ─────────────────────────────────────────────

# 🚨 GÜVENLİK: Arbitrary File Read açığı kapatıldı.
# Eskiden "/<path:dosya_adi>" rotası, ana dizindeki HER dosyayı
# (örn. .env, berkai_guvenli.py, berkai_oturum_hafizasi.db) dışarıya
# servis ediyordu. Artık SADECE bu beyaz listedeki dosyalar açılabilir.
IZINLI_DOSYALAR = {"index.html", "style.css", "script.js", "favicon.ico", "berkai.png"}
# Not: Eğer projede resim/font gibi başka statik dosyalar varsa,
# bunları buraya tek tek eklemen gerekiyor. "*.png" gibi joker
# karakter KULLANMA — tek tek isim yazman güvenliği garanti eder.

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:dosya_adi>")
def dosya_gonder(dosya_adi):
    # Tam eşleşme + whitelist: path traversal (../../) ve gizli dosya
    # (.env, .git) erişimini birlikte engeller, çünkü os.path.basename
    # ile normalize edilmiş isim whitelist'teki tam isimle eşleşmek
    # zorunda.
    guvenli_ad = os.path.basename(dosya_adi)
    if guvenli_ad != dosya_adi or guvenli_ad not in IZINLI_DOSYALAR:
        abort(403)
    return send_from_directory(".", guvenli_ad)

@app.route("/baslat", methods=["POST"])
def baslat():
    ip = request.remote_addr

    if not ip_rate_limit_kontrol(ip):
        return jsonify({"hata": "Çok fazla deneme, 5 dakika bekle."}), 429

    data  = request.json or {}
    isim  = data.get("isim", "").strip()
    sifre = data.get("sifre", "").strip()

    if sifre != APP_PASSWORD:
        return jsonify({"hata": "Şifre yanlış!"}), 401
    if not isim:
        return jsonify({"hata": "İsim boş"}), 400

    token = secrets.token_hex(16)
    aktif_oturumlar[token] = isim

    tanitim, _ = berkai_cevap_ver(
        isim,
        "[SİSTEM: İlk mesaj. Kimliğini açıklama, 'hafızayım/asistanım' deme. Direkt Berkay gibi kısa ve samimi selamlama yap.]"
    )
    return jsonify({"cevap": tanitim, "isim": isim, "token": token})

@app.route("/sor", methods=["POST"])
def sor():
    data  = request.json or {}
    token = data.get("token", "").strip()
    mesaj = data.get("mesaj", "").strip()

    isim = aktif_oturumlar.get(token)
    if not isim:
        return jsonify({"hata": "Yetkisiz erişim. Lütfen önce giriş yap."}), 401

    if not mesaj_rate_limit_kontrol(token):
        return jsonify({"hata": "Çok hızlı mesaj gönderiyorsun, biraz bekle."}), 429

    if not mesaj:
        return jsonify({"hata": "Mesaj boş"}), 400

    if TOPLAM_MALIYET >= BUTCE_LIMITI_USD:
        return jsonify({"hata": "Aylık bütçe limitine ulaşıldı, sistem kilitlendi."}), 403

    cevap, maliyet = berkai_cevap_ver(isim, mesaj)
    return jsonify({"cevap": cevap, "maliyet": round(maliyet, 6)})

@app.route("/maliyet", methods=["GET"])
def maliyet_goster():
    return jsonify({
        "usd": round(TOPLAM_MALIYET, 6),
        "giris": TOPLAM_GIRIS_TOKEN,
        "cikis": TOPLAM_CIKIS_TOKEN,
        "limit": BUTCE_LIMITI_USD,
        "kalan_yuzde": round((1 - TOPLAM_MALIYET / BUTCE_LIMITI_USD) * 100, 1)
    })

if __name__ == "__main__":
    print(f"\n🚀 Berkai → http://localhost:5000")
    print(f"💰 Bütçe limiti: ${BUTCE_LIMITI_USD}\n")
    app.run(host="0.0.0.0", port=5000, debug=False)