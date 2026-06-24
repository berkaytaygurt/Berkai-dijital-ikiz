import os
import sqlite3
import re
import json
import secrets
import time
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

# ─── ÇEVRE DEĞİŞKENLERİ VE API KEY ───────────────────────────
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# ─── GÜVENLİK: ZORUNLU ŞİFRE KONTROLÜ ────────────────────────
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
if not APP_PASSWORD:
    raise RuntimeError(
        "❌ APP_PASSWORD tanımlı değil! Ayarlardan APP_PASSWORD ekle "
        "Güvenlik için varsayılan/sabit şifreyle çalıştırmıyoruz."
    )

# ─── GİZLİ GITHUB'DAN VERİ ÇEKME (SADECE KLASÖR YOKSA) ───────
VERITABANI_KLASORU = "./berkay_tam_hafiza_db"

if not os.path.exists(VERITABANI_KLASORU):
    print("🚀 Hafıza ve profil gizli GitHub reposundan çekiliyor...")
    gh_token = os.environ.get("GITHUB_TOKEN")
    
    # Senin tam GitHub adın ve repon:
    repo_url = f"https://{gh_token}@github.com/berkaytaygurt/berkai-veri.git"
    
    subprocess.run(["git", "clone", repo_url, "gecici_klasor"])
    
    # 1. DB Klasörünü ana dizine çıkar
    os.rename("gecici_klasor/berkay_tam_hafiza_db", VERITABANI_KLASORU)
    
    # 2. JSON Profil dosyasını ana dizine çıkar
    if os.path.exists("gecici_klasor/berkay_profil.json"):
        os.rename("gecici_klasor/berkay_profil.json", "berkay_profil.json")

# ─── PROFİL JSON ─────────────────────────────────────────────
try:
    with open("berkay_profil.json", "r", encoding="utf-8") as f:
        BERKAY_SABIT_PROFIL = json.dumps(json.load(f), ensure_ascii=False, indent=2)
    print("✅ Profil JSON yüklendi.")
except Exception as e:
    print("⚠️ Profil JSON bulunamadı:", e)
    BERKAY_SABIT_PROFIL = "Berkay Taygurt."

# ─── CHROMADB (GEMINI EMBEDDING İLE) ─────────────────────────
print("🚀 RAG Hafızası Yükleniyor...")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vector_store = Chroma(persist_directory=VERITABANI_KLASORU, embedding_function=embeddings)

# SQLITE 
session_conn = sqlite3.connect("berkai_oturum_hafizasi.db", check_same_thread=False)
session_conn.execute("""
    CREATE TABLE IF NOT EXISTS oturum_mesajlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kisi TEXT, rol TEXT, mesaj TEXT, zaman TEXT
    )
""")
session_conn.commit()

#GEMINI 
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.85,
    max_tokens=250,
    thinking_budget=0
)

#: TOKEN + RATE LIMIT
aktif_oturumlar = {}
giris_denemeleri = {}

BUTCE_LIMITI_USD = 3.0
RATE_LIMIT_GIRIS = 5
RATE_LIMIT_MESAJ = 60
mesaj_sayaci = {}

def ip_rate_limit_kontrol(ip):
    simdi = time.time()
    pencere = 300
    denemeler = giris_denemeleri.get(ip, [])
    denemeler = [t for t in denemeler if simdi - t < pencere]
    if len(denemeler) >= RATE_LIMIT_GIRIS:
        return False
    denemeler.append(simdi)
    giris_denemeleri[ip] = denemeler
    return True

def mesaj_rate_limit_kontrol(token):
    simdi = time.time()
    pencere = 60
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

def keyword_ara(isim, konusulan_kisi, max_sonuc=5):
    sonuclar = []
    kisi_temiz = konusulan_kisi.lower().strip()
    yetkili = kisi_temiz in ["berkay", "berkay taygurt"]
    try:
        hepsi = vector_store.get(include=["documents","metadatas"])
        for doc, meta in zip(hepsi.get("documents",[]), hepsi.get("metadatas",[])):
            if meta and "source" in meta:
                kaynak = meta["source"].lower().strip()
                if not yetkili and kaynak != kisi_temiz:
                    continue
            
            if doc and isim.lower() in doc.lower():
                sonuclar.append(doc)
            if len(sonuclar) >= max_sonuc:
                break
    except:
        pass
    return sonuclar

KISILIK_SORUSU_TETIKLEYICILERI = [
    "ben nasıl biriyim", "beni nasıl tanımlarsın", "benim hakkımda ne düşünüyorsun",
    "benim karakterim nasıl", "ben ne tip biriyim", "benim hakkımda",
    "beni nasıl görüyorsun", "bence ben nasılım", "ben kimim",
    "benim için ne düşünüyorsun", "beni anlat", "beni tarif et"
]

def kisilik_sorusu_mu(mesaj):
    m = mesaj.lower().strip()
    return any(t in m for t in KISILIK_SORUSU_TETIKLEYICILERI)

def hafizayi_ara(konusulan_kisi, sorgu):
    parcalar = []
    kisi_temiz = konusulan_kisi.lower().strip()
    yetkili = kisi_temiz in ["berkay", "berkay taygurt"]

    # "Ben nasıl biriyim" gibi soyut/kişilik sorularında, normal similarity
    # search bu cümleye "anlamca yakın" chunk arar — ama soru hiçbir spesifik
    # konuyla ilgili olmadığı için sonuçlar zayıf/rastgele kalabilir. Bu
    # durumda sorguyu görmezden gelip, o kişiye ait TÜM geçmişten daha
    # GENİŞ bir örneklem çekiyoruz (k=10 -> k=25), model kendi sentezini
    # daha çok veriyle yapabilsin.
    genis_tarama = kisilik_sorusu_mu(sorgu)
    k_degeri = 25 if genis_tarama else 10

    try:
        kisi_sonuc = vector_store.similarity_search(
            query=(kisi_temiz if genis_tarama else sorgu),
            k=k_degeri,
            filter={"source": kisi_temiz}
        )
        for i, doc in enumerate(kisi_sonuc):
            parcalar.append(f"[{konusulan_kisi} ile geçmiş {i+1}]:\n{doc.page_content}")
    except:
        pass

    if yetkili:
        try:
            genel = vector_store.similarity_search(query=sorgu, k=10)
            for i, doc in enumerate(genel):
                if not any(doc.page_content in p for p in parcalar):
                    parcalar.append(f"[Genel hafıza {i+1}]:\n{doc.page_content}")
        except:
            pass

    for isim in mesajdaki_isimleri_bul(sorgu) - {konusulan_kisi}:
        for doc in keyword_ara(isim, konusulan_kisi):
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

def hyde_hafiza_zenginlestir(gelen_mesaj, oturum_gecmisi, konusulan_kisi):
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
    kisi_temiz = konusulan_kisi.lower().strip()
    yetkili = kisi_temiz in ["berkay", "berkay taygurt"]

    for isim in isimler[:8]:
        try:
            filtre = None if yetkili else {"source": kisi_temiz}
            sonuclar = vector_store.similarity_search(query=isim, k=3, filter=filtre)
            if any(isim.lower() in doc.page_content.lower() for doc in sonuclar):
                hafizada_olanlar.append(isim)
        except:
            pass

    if not hafizada_olanlar:
        return ""

    return f"Sohbetlerinde geçen ilgili isimler: {', '.join(hafizada_olanlar)}"

def arkadaslar_sorusu_mu(mesaj):
    m = mesaj.lower()
    return any(t in m for t in ["arkadaş","aga","tanıyor","tanıdık","kimle","kimi","kimler","kişi","konuş","sohbet"])

# ─── ANA FONKSİYON ───────────────────────────────────────────
# ─── ANA FONKSİYON ───────────────────────────────────────────
def berkai_cevap_ver(konusulan_kisi, gelen_mesaj):
    oturum      = oturum_getir(konusulan_kisi, limit=8)
    sorgu       = akilli_sorgu(gelen_mesaj, oturum)
    eski_baglam = hafizayi_ara(konusulan_kisi, sorgu)
    uslup       = uslup_cek(sorgu, k=8)

    hyde_sonuc = hyde_hafiza_zenginlestir(gelen_mesaj, oturum, konusulan_kisi)

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

    system_prompt = f"""Sen Berkay Taygurt'sun. dostların sana bazen beko veya berkay  da diyebilir. Bu senin sabit kimlik profilin:

{BERKAY_SABIT_PROFIL}

═══ DİNAMİK ÜSLUP VE KARAKTER (EN ÖNEMLİ KURAL) ═══
Senin konuşma tarzın SABİT DEĞİLDİR, karşındaki kişiye göre tamamen değişir.
Aşağıdaki "GEÇMİŞ ANILARIN" kısmına bakarak bu kişiyle geçmişte NASIL konuştuğunu analiz et.
- Eğer geçmişte bu kişiye karşı 'aga', 'kanka', 'la' gibi kelimeler kullanıp rahat konuştuysan, ŞU AN DA ÖYLE KONUŞ.
- Eğer geçmişte bu kişiye karşı kibar, saygılı, adıyla (örn: 'Hatice') hitap ederek, daha düzgün bir dil kullandıysan, ŞU AN DA KESİNLİKLE KİBAR VE MESAFELİ OL. Sakın kaba kelimeler kullanma.
- Üslubunu tamamen karşındakinin kim olduğuna ve geçmiş diyaloglarınıza göre otomatik olarak ayarla. 

─── "BEN NASIL BİRİYİM", "BENİ NASIL TANIMLARSIN", "BENİM HAKKIMDA NE DÜŞÜNÜYORSUN" TARZI SORULAR ───
Bu tarz bir soru geldiğinde ASLA parça parça, çekingen, "hmm bilmem" tavrı takınma ve ASLA karşı soru sorup detay isteme (örn: "ne demek istiyorsun" deme). Aşağıdaki GEÇMİŞ ANILARIN bölümündeki ham mesajları KENDİN SENTEZLE: o kişinin karakterine dair 2-4 net, somut gözlem çıkar (mizacı, neyle uğraştığı, neye taktığı, nasıl biri olduğu, aranızdaki anılardan çıkan izlenim) ve TEK CEVAPTA, doğrudan, akıcı bir şekilde anlat — sanki yıllardır tanıdığın birini bir cümlede özetliyormuşsun gibi. "Yapısı şöyle, şunu çok yapar, bana hep böyle davranır" tarzında kesin ve iddialı konuş, "sanırım", "belki", "tam bilmiyorum ama" gibi çekingen ifadeler KULLANMA. Elindeki veri azsa bile, var olan küçük ipuçlarından emin bir tarif çıkar, hiç bilgi yokmuş gibi davranma.

─── SORU SORMA YASAĞI (ASLA İHLAL ETME) ───
VARSAYILAN DAVRANIŞ: Cevabını düz bir ifadeyle bitir ve sus. 
- Karşındaki sana bir şey anlattığında veya teklif ettiğinde, "Neden?", "Nasıl olacak?", "Niye?" gibi ASİSTAN/ROBOT soruları SORMA. Karşındakini sorguya çekme.
- Sadece anladığını belirt, kendi fikrini söyle, kestirip at veya onaylama yap ama konuyu uzatmak için ASLA soru sorma. Muhabbeti devam ettirme çabasına girme.
- Bu yasak, kişilik/tanımlama sorularında da geçerli: "ne demek istiyorsun", "ne açıdan" gibi açıklama isteyen sorular sorma, direkt cevap ver.

─── BİLGİ VE GİZLİLİK KURALI ───
1. GENEL BİLGİ (futbol, film, oyun, gündem): Direkt cevap ver.
2. KİŞİSEL DETAYLAR: Karşındaki kişi BAŞKA BİR ARKADAŞIN hakkında soru sorarsa, kesinlikle üçüncü şahısların sırlarını verme! "başkasının gıybetini bana yaptırma şimdi" diyerek konuyu kapat. ama  o kişiyle alakalı övgü veya tanıdğına dair kısa bir şeyler diyebilirsin.

Karşındaki: {konusulan_kisi}

═══ GEÇMİŞTEKİ KENDİ YAZIM ÖRNEKLERİN (Noktalama/Büyük harf tarzını kopyala) ═══
{uslup if uslup else "kısa, samimi, whatsapp tarzı yaz"}

═══ BU KİŞİYLE GEÇMİŞ ANILARIN (Bu kişiye nasıl davranman gerektiğini buradan çıkar) ═══
{eski_baglam if eski_baglam else "Bu kişiyle belirgin bir geçmiş yok, doğal davran."}
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
IZINLI_DOSYALAR = {"index.html", "style.css", "script.js", "favicon.ico", "berkai.png"}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:dosya_adi>")
def dosya_gonder(dosya_adi):
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

    # 🚨 GÜNCELLEME: Açılış mesajı tam istediğin standart forma çekildi. Soru sorma yasaklandı.
    tanitim, _ = berkai_cevap_ver(
        isim,
        f"[SİSTEM: İlk mesaj. Karşındakine sadece 'merhaba {isim.lower()} ben berkai benimle konuşabilirsin' tarzında çok kısa, düz bir giriş yap. Başka hiçbir şey deme, soru sorma, uzatma.]"
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
    print(f"\n🚀 Berkai → http://0.0.0.0:7860")
    print(f"💰 Bütçe limiti: ${BUTCE_LIMITI_USD}\n")
    app.run(host="0.0.0.0", port=7860, debug=False)
