# -*- coding: utf-8 -*-
"""
GIZLILIK FILTRESI
=================
Ham sohbet JSON'larindan SADECE Berkay'in yazdigi metni cikarir.
Karsi tarafin mesajlari, isimleri ve metadata'daki kaynak kisi atilir.

Neden: Vektor veritabanina baskalarinin ozel mesajlarini gomup disariya
acik bir servisten sunmak, o kisilerin rizasi olmadan kisisel veri islemek
demektir. Bu script o veriyi kaynagindan temizler.

Isleyis (iki asamali):
  1) NORMALIZE - Bazi bloklarda ham WhatsApp export satirlari
     ("17.05.2024 22:43 - Ahmet Karaca: ...") baska bir mesajin ICINE
     gomulu kalmis. Bunlari once ayri satirlara ayiriyoruz.
  2) DURUM MAKINESI - Satirlari sirayla gezip "su an kim konusuyor"
     bilgisini tutuyoruz. Sadece konusmaci Berkay iken gelen metni
     aliyoruz. Etiketsiz devam satirlari onceki konusmaciya ait sayilir,
     boylece Berkay'in cok satirli mesajlari korunur, baskasininki atilir.

Cikti: berkay_sadece_ben.json
"""
import json
import io
import os
import re
import collections

BENIM_ETIKETLERIM = {"berkaytaygurt", "berkay", "berkay taygurt"}

KAYNAK_DOSYALAR = [
    "22haziran_wp_veri.json",
    "22haziran_ig_veri.json",
    "21haziran_veri.json",
    "altin_veri_rag_link_temiz.json",
]

CIKTI_DOSYASI = "berkay_sadece_ben.json"
MIN_UZUNLUK = 15

# "17.05.2024 22:43 - " kalibi: gomulu bir konusma sirasinin basladigini gosterir
ZAMAN_DAMGASI = re.compile(r"(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}\s*-\s*)")
# Zaman damgasi (varsa) + "Isim: icerik"
SATIR = re.compile(
    r"^(?:\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}\s*-\s*)?([^:]{1,40}?):\s*(.*)$"
)
DAMGALI_SATIR = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}\s*-\s*")


def bilinen_konusmacilari_bul(tum_bloklar):
    """Veriden gercek konusmaci etiketlerini ogrenir.

    Iki kaynak: (a) zaman damgasi ile gelen etiketler -> kesin konusmaci,
    (b) satir basinda sik tekrar eden etiketler. Boylece "saat 5: yarim"
    gibi cumle ici iki nokta yanlislikla konusmaci sanilmaz.
    """
    damgali = set()
    sayac = collections.Counter()

    for text in tum_bloklar:
        for satir in ZAMAN_DAMGASI.sub(lambda m: "\n" + m.group(1), text).split("\n"):
            eslesme = SATIR.match(satir.strip())
            if not eslesme:
                continue
            etiket = eslesme.group(1).strip().lower()
            if DAMGALI_SATIR.match(satir.strip()):
                damgali.add(etiket)
            else:
                sayac[etiket] += 1

    sik_gecenler = {e for e, adet in sayac.items() if adet >= 10}
    return damgali | sik_gecenler | BENIM_ETIKETLERIM


def bloku_filtrele(text, bilinen_konusmacilar):
    """Bloktan sadece Berkay'a ait metni dondurur."""
    normalize = ZAMAN_DAMGASI.sub(lambda m: "\n" + m.group(1), text)

    benim_metnim = []
    aktif_konusmaci = None  # blogun basinda kimin konustugunu bilmiyoruz

    for ham_satir in normalize.split("\n"):
        satir = ham_satir.strip()
        if not satir:
            continue

        eslesme = SATIR.match(satir)
        etiket = eslesme.group(1).strip().lower() if eslesme else None

        if eslesme and (etiket in bilinen_konusmacilar or DAMGALI_SATIR.match(satir)):
            # Yeni bir konusma sirasi basladi
            aktif_konusmaci = etiket
            icerik = eslesme.group(2).strip()
        else:
            # Etiketsiz satir -> onceki konusmacinin mesajinin devami
            icerik = satir

        if aktif_konusmaci in BENIM_ETIKETLERIM and icerik:
            benim_metnim.append(icerik)

    return benim_metnim


def main():
    # Once tum ham metinleri topla ki konusmaci sozlugunu ogrenebilelim
    dosya_verileri = {}
    tum_bloklar = []
    for dosya in KAYNAK_DOSYALAR:
        if not os.path.exists(dosya):
            print(f"[!] {dosya} bulunamadi, atlaniyor.")
            continue
        with io.open(dosya, encoding="utf-8") as f:
            ham = json.load(f)
        dosya_verileri[dosya] = ham
        tum_bloklar.extend(k.get("text", "") for k in ham)

    bilinen = bilinen_konusmacilari_bul(tum_bloklar)
    baskalari = sorted(bilinen - BENIM_ETIKETLERIM)
    print(f"Tespit edilen konusmaci etiketi: {len(bilinen)} "
          f"(Berkay disinda {len(baskalari)} kisi filtrelenecek)")

    temiz_veri = []
    istatistik = []

    for dosya, ham in dosya_verileri.items():
        korunan, atilan = 0, 0
        for kayit in ham:
            satirlar = bloku_filtrele(kayit.get("text", ""), bilinen)
            birlesik = "\n".join(satirlar).strip()

            if len(birlesik) < MIN_UZUNLUK:
                atilan += 1
                continue

            # metadata.source karsi tarafin adiydi -> tamamen kaldiriliyor
            eski_meta = kayit.get("metadata", {}) or {}
            temiz_veri.append({
                "text": birlesik,
                "metadata": {
                    "type": eski_meta.get("type", "sohbet"),
                    "date": eski_meta.get("date", ""),
                    "speaker": "berkay",
                },
            })
            korunan += 1

        istatistik.append((dosya, len(ham), korunan, atilan))

    with io.open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(temiz_veri, f, ensure_ascii=False, indent=1)

    print("\n--- FILTRE OZETI ---")
    for dosya, ham_adet, korunan, atilan in istatistik:
        print(f"{dosya}: {ham_adet} blok -> {korunan} korundu, {atilan} atildi")

    toplam_karakter = sum(len(k["text"]) for k in temiz_veri)
    print(f"\nToplam {len(temiz_veri)} blok, {toplam_karakter:,} karakter -> {CIKTI_DOSYASI}")

    # --- DOGRULAMA ---
    kalan_damga = sum(1 for k in temiz_veri if ZAMAN_DAMGASI.search(k["text"]))
    kalan_isim = collections.Counter()
    for kayit in temiz_veri:
        for satir in kayit["text"].split("\n"):
            eslesme = SATIR.match(satir.strip())
            if eslesme:
                etiket = eslesme.group(1).strip().lower()
                if etiket in baskalari:
                    kalan_isim[etiket] += 1

    print("\n--- DOGRULAMA (hepsi 0 olmali) ---")
    print(f"Gomulu export zaman damgasi kalan blok : {kalan_damga}")
    print(f"Baskasina atfedilmis satir             : {sum(kalan_isim.values())}")
    if kalan_isim:
        print("  ", kalan_isim.most_common(10))


if __name__ == "__main__":
    main()
