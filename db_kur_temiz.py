# -*- coding: utf-8 -*-
"""
TEMIZ VEKTOR VERITABANI KURULUMU
================================
Girdi : berkay_sadece_ben.json  (veri_filtrele.py ciktisi - sadece Berkay'in metni)
Cikti : ./berkay_sadece_ben_db  (ChromaDB)

Eski db_birlestir.py'den farklari:
  1) Filtrelenmis veriyi okur (baskalarinin mesajlari yok).
  2) Cok uzun bloklari boler. gemini-embedding-001'in girdi siniri ~2048
     token; ham veride 300 bin karakterlik bloklar vardi ve bunlar
     sessizce kirpiliyordu, yani icerigin cogu hic aranabilir degildi.
  3) Toplu (batch) gomme + hata halinde tekrar deneme yapar, boylece
     yarida kalip API kredisini bosa harcamaz.

Calistirmadan once .env icinde GOOGLE_API_KEY olmali.
"""
import json
import io
import os
import shutil
import sys
import time

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("HATA: .env icinde GOOGLE_API_KEY yok.")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

GIRDI_DOSYASI = "berkay_sadece_ben.json"
VERITABANI_KLASORU = "./berkay_sadece_ben_db"

MAX_KARAKTER = 1500   # ~500-600 token, API sinirinin cok altinda guvenli bolge
BINDIRME = 150        # parcalar arasi ortak baglam
YIGIN = 100           # tek seferde gonderilecek metin sayisi


def uzun_bloku_bol(metin, limit=MAX_KARAKTER, bindirme=BINDIRME):
    """Uzun metni once satir sinirlarina saygi gostererek boler."""
    if len(metin) <= limit:
        return [metin]

    parcalar = []
    tampon = ""
    for satir in metin.split("\n"):
        aday = (tampon + "\n" + satir).strip() if tampon else satir

        if len(aday) <= limit:
            tampon = aday
            continue

        if tampon:
            parcalar.append(tampon)

        if len(satir) <= limit:
            tampon = satir
        else:
            # tek satir bile cok uzun -> bindirmeli kayan pencere
            bas = 0
            while bas < len(satir):
                son = bas + limit
                parcalar.append(satir[bas:son])
                bas = son - bindirme if son - bindirme > bas else son
            tampon = ""

    if tampon:
        parcalar.append(tampon)
    return [p for p in parcalar if p.strip()]


def main():
    with io.open(GIRDI_DOSYASI, encoding="utf-8") as f:
        veri = json.load(f)

    metinler, metadatalar = [], []
    bolunen = 0
    for kayit in veri:
        parcalar = uzun_bloku_bol(kayit["text"])
        if len(parcalar) > 1:
            bolunen += 1
        for parca in parcalar:
            metinler.append(parca)
            metadatalar.append(dict(kayit["metadata"]))

    print(f"{len(veri)} blok okundu -> {len(metinler)} parca "
          f"({bolunen} blok uzun oldugu icin bolundu)")
    toplam_karakter = sum(len(m) for m in metinler)
    print(f"Toplam {toplam_karakter:,} karakter (~{toplam_karakter // 3:,} token) gomulecek")
    print(f"En uzun parca: {max(len(m) for m in metinler)} karakter")

    if os.path.exists(VERITABANI_KLASORU):
        print(f"\n'{VERITABANI_KLASORU}' zaten var, siliniyor (yeniden kurulacak)...")
        shutil.rmtree(VERITABANI_KLASORU)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vector_store = Chroma(
        persist_directory=VERITABANI_KLASORU,
        embedding_function=embeddings,
    )

    print(f"\nGomme basliyor ({YIGIN}'lik yiginlar halinde)...")
    baslangic = time.time()
    eklenen = 0

    for i in range(0, len(metinler), YIGIN):
        yigin_metin = metinler[i:i + YIGIN]
        yigin_meta = metadatalar[i:i + YIGIN]

        for deneme in range(4):
            try:
                vector_store.add_texts(texts=yigin_metin, metadatas=yigin_meta)
                eklenen += len(yigin_metin)
                break
            except Exception as e:
                bekle = 2 ** deneme * 5
                print(f"  [!] Yigin {i // YIGIN + 1} hata verdi ({type(e).__name__}), "
                      f"{bekle} sn sonra tekrar denenecek: {str(e)[:120]}")
                time.sleep(bekle)
        else:
            print(f"  [X] Yigin {i // YIGIN + 1} 4 denemede de basarisiz, atlaniyor.")

        gecen = time.time() - baslangic
        print(f"  {eklenen}/{len(metinler)} parca gomuldu ({gecen:.0f} sn)")

    print(f"\nTAMAM. {eklenen} parca '{VERITABANI_KLASORU}' klasorune yazildi.")
    print(f"Toplam sure: {time.time() - baslangic:.0f} sn")


if __name__ == "__main__":
    main()
