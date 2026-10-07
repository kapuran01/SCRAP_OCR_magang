# Tahap preprocessing: PDF -> gambar -> potong area dokumen -> samakan ukuran -> cek buram -> luruskan -> perbaiki kontras

import os
import cv2
import fitz  # PyMuPDF
import numpy as np


def cek_file(path_pdf, ukuran_maks_mb=1):
    """Cek file sebelum diproses. Return (ok, alasan)"""
    if not os.path.exists(path_pdf):
        return False, "file belum diunggah"
    if not path_pdf.lower().endswith(".pdf"):
        return False, "file bukan PDF"
    ukuran_mb = os.path.getsize(path_pdf) / (1024 * 1024)
    if ukuran_mb > ukuran_maks_mb:
        return False, f"ukuran file {ukuran_mb:.2f} MB, maksimal {ukuran_maks_mb} MB"
    return True, ""


def pdf_ke_gambar(path_pdf, dpi=300):
    doc = fitz.open(path_pdf)
    daftar_gambar = []
    for halaman in doc:
        pix = halaman.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        daftar_gambar.append(img)
    doc.close()
    return daftar_gambar


def potong_area_dokumen(img, margin=30):
    """Buang area putih kosong di sekitar dokumen.
    Penting buat KTP yang di-scan di kertas A4, kalau tidak dipotong tulisannya jadi kecil sekali."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, biner = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    biner = cv2.morphologyEx(biner, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))  # hilangkan bintik noise
    ys, xs = np.where(biner > 0)
    if len(xs) == 0:
        return img
    h, w = img.shape[:2]
    y1, y2 = max(ys.min() - margin, 0), min(ys.max() + margin, h)
    x1, x2 = max(xs.min() - margin, 0), min(xs.max() + margin, w)
    return img[y1:y2, x1:x2]


def samakan_ukuran(img, sisi_panjang=2000):
    h, w = img.shape[:2]
    skala = sisi_panjang / max(h, w)
    if skala < 1:
        interp = cv2.INTER_AREA
    else:
        interp = cv2.INTER_CUBIC
    return cv2.resize(img, (int(w * skala), int(h * skala)), interpolation=interp)


def skor_ketajaman(img):
    # varians laplacian, makin kecil makin buram
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def luruskan(img):
    """Koreksi kemiringan kecil.
    Awalnya pakai minAreaRect dari semua piksel teks (cara yang banyak di tutorial), tapi untuk satu halaman
    penuh hasilnya sering ngaco (pernah dapat 8 derajat padahal aslinya cuma 0.8).
    Jadi sekarang kata-kata ditebalkan ke samping supaya jadi "blok baris", lalu diambil median sudut tiap baris."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    biner = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    blok = cv2.dilate(biner, cv2.getStructuringElement(cv2.MORPH_RECT, (35, 3)))
    kontur, _ = cv2.findContours(blok, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    daftar_sudut = []
    for k in kontur:
        (_, _), (w, h), sudut = cv2.minAreaRect(k)
        if w < h:
            w, h = h, w
            sudut = sudut - 90
        if sudut > 45:
            sudut -= 90
        if sudut < -45:
            sudut += 90
        if w > 200 and w / max(h, 1) > 6:  # hanya blok yang panjang (baris teks)
            daftar_sudut.append(sudut)
    if not daftar_sudut:
        return img  # misal KTP dengan latar bermotif, tidak ketemu baris yang jelas
    sudut = float(np.median(daftar_sudut))
    if abs(sudut) < 0.2 or abs(sudut) > 10:
        return img
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), sudut, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def perbaiki_kontras(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def proses_gambar(img, cfg):
    """Return (gambar_bersih, skor_tajam). Cek buram dilakukan sebelum denoise."""
    img = potong_area_dokumen(img)
    img = samakan_ukuran(img, cfg["preprocessing"]["sisi_panjang"])
    skor = skor_ketajaman(img)
    img = luruskan(img)
    img = perbaiki_kontras(img)
    return img, skor
