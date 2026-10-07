# Tahap OCR. Utamanya PaddleOCR, kalau tidak bisa (misal model belum ke-download) pakai Tesseract.
# Hasil akhirnya daftar BARIS: {id, teks, bbox, confidence}

import re

_paddle = None
_engine_aktif = None


def _ocr_paddle(img, cfg):
    global _paddle
    if _paddle is None:
        from paddleocr import PaddleOCR
        # PaddleOCR versi 3.x
        _paddle = PaddleOCR(
            lang=cfg["ocr"]["paddle_lang"],
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    hasil = _paddle.predict(img)
    kotak_list = []
    for res in hasil:
        for teks, skor, box in zip(res["rec_texts"], res["rec_scores"], res["rec_boxes"]):
            x1, y1, x2, y2 = [int(v) for v in box]
            kotak_list.append({"teks": teks, "bbox": [x1, y1, x2, y2], "confidence": float(skor)})
    return kotak_list


def _ocr_tesseract(img, cfg):
    import pytesseract
    if cfg["ocr"].get("tesseract_cmd"):
        pytesseract.pytesseract.tesseract_cmd = cfg["ocr"]["tesseract_cmd"]
    data = pytesseract.image_to_data(img, lang=cfg["ocr"]["tesseract_lang"],
                                     output_type=pytesseract.Output.DICT)
    kotak_list = []
    for i in range(len(data["text"])):
        teks = data["text"][i].strip()
        conf = float(data["conf"][i])
        if teks == "" or conf < 0:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        kotak_list.append({"teks": teks, "bbox": [x, y, x + w, y + h], "confidence": conf / 100})
    return kotak_list


def baca_kotak_teks(img, cfg):
    global _engine_aktif
    engine = cfg["ocr"]["engine"]
    if engine in ("auto", "paddle") and _engine_aktif != "tesseract":
        try:
            hasil = _ocr_paddle(img, cfg)
            _engine_aktif = "paddle"
            return hasil
        except Exception as e:
            if engine == "paddle":
                raise
            print(f"  [!] PaddleOCR gagal ({str(e)[:60]}...), pindah ke Tesseract")
            _engine_aktif = "tesseract"
    return _ocr_tesseract(img, cfg)


def _tanda_baca_saja(teks):
    return re.fullmatch(r"[\W_]+", teks) is not None


def gabung_per_baris(kotak_list):
    """Kotak-kotak teks yang sejajar (y tengahnya dekat) digabung jadi satu baris"""
    kotak_list = sorted(kotak_list, key=lambda k: (k["bbox"][1] + k["bbox"][3]) / 2)
    baris_list = []
    for kotak in kotak_list:
        x1, y1, x2, y2 = kotak["bbox"]
        y_tengah = (y1 + y2) / 2
        tinggi = y2 - y1
        if baris_list:
            terakhir = baris_list[-1]
            if abs(y_tengah - terakhir["y_tengah"]) < 0.5 * max(tinggi, terakhir["tinggi"]):
                terakhir["kotak"].append(kotak)
                n = len(terakhir["kotak"])
                terakhir["y_tengah"] = (terakhir["y_tengah"] * (n - 1) + y_tengah) / n
                continue
        baris_list.append({"kotak": [kotak], "y_tengah": y_tengah, "tinggi": tinggi})

    # dalam satu baris kadang ada dua "kolom" yang jauh (misal teks FOTO di samping data KTP),
    # jadi kalau jarak horizontalnya terlalu jauh dipisah jadi baris sendiri
    lebar_konten = max((k["bbox"][2] for k in kotak_list), default=1)
    segmen_list = []
    for b in baris_list:
        kotak = sorted(b["kotak"], key=lambda k: k["bbox"][0])
        segmen = [kotak[0]]
        for k in kotak[1:]:
            jarak = k["bbox"][0] - segmen[-1]["bbox"][2]
            # jarak label ke ":" di formulir juga lumayan jauh, jadi kalau kata berikutnya
            # diawali ":" jangan dipisah (itu nilai dari label tsb). OCR kadang baca ":" jadi ";"
            if jarak > 0.2 * lebar_konten and not k["teks"].startswith((":", ";")):
                segmen_list.append(segmen)
                segmen = [k]
            else:
                segmen.append(k)
        segmen_list.append(segmen)

    hasil = []
    for kotak in segmen_list:
        teks = " ".join(k["teks"] for k in kotak)
        bbox = [min(k["bbox"][0] for k in kotak), min(k["bbox"][1] for k in kotak),
                max(k["bbox"][2] for k in kotak), max(k["bbox"][3] for k in kotak)]
        # tanda baca kayak ":" sering confidence-nya rendah, jadi tidak dihitung
        conf_list = [k["confidence"] for k in kotak if not _tanda_baca_saja(k["teks"])]
        conf = min(conf_list) if conf_list else min(k["confidence"] for k in kotak)
        # confidence khusus bagian nilai (setelah ":"), karena kata label tidak penting buat datanya
        conf_nilai = conf
        idx_titik_dua = next((i for i, k in enumerate(kotak) if ":" in k["teks"]), None)
        if idx_titik_dua is not None:
            kata_nilai = [k for k in kotak[idx_titik_dua:] if not _tanda_baca_saja(k["teks"])]
            if kata_nilai:
                conf_nilai = min(k["confidence"] for k in kata_nilai)
        hasil.append({"teks": teks, "bbox": bbox, "confidence": round(conf, 3),
                      "confidence_nilai": round(conf_nilai, 3)})
    return hasil


def engine_yang_dipakai():
    return _engine_aktif or "tesseract"
