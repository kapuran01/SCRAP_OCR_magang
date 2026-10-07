# Script untuk membuat dokumen dummy (KTP, ijazah, SKCK, MCU) dalam bentuk PDF hasil "scan".
# Semua data di sini FIKTIF, cuma buat nyoba pipeline.
# Dokumennya sengaja dibuat sebagai gambar (bukan teks) supaya memang harus dibaca pakai OCR,
# terus dikasih noise + sedikit miring biar mirip hasil scan/foto beneran.

import os
import json
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FOLDER_OUTPUT = "data/dummy"
# pakai font serif (Times) karena huruf "I" di font sans (Arial) bentuknya cuma garis,
# Tesseract sering salah baca jadi "|" atau "]". PaddleOCR sebenarnya lebih tahan.
FONT_PATH = "C:/Windows/Fonts/times.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/timesbd.ttf"
FONT_ITALIC_PATH = "C:/Windows/Fonts/timesi.ttf"

if not os.path.exists(FONT_PATH):
    # fallback buat Linux
    FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
    FONT_BOLD_PATH = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    FONT_ITALIC_PATH = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

random.seed(42)

# data pendaftar fiktif + skenario yang mau dites
pendaftar_list = [
    {
        "id": "P001", "skenario": "program studi tidak sesuai syarat",
        "provinsi": "PROVINSI JAWA TENGAH", "kota": "KOTA SEMARANG", "gol_darah": "O", "tgl_terbit": "12-03-2019", "warna_foto": (178, 34, 34),
        "nama": "GOKU KAMEHAME", "jk": "LAKI-LAKI", "tempat_lahir": "SEMARANG", "tgl_lahir": "15-05-2001",
        "nik": "3374011505010001", "alamat": "JL. MERDEKA NO. 10", "rtrw": "002/003",
        "kel": "PLEBURAN", "kec": "SEMARANG SELATAN",
        "nama_ijazah": "GOKU KAMEHAME", "no_ijazah": "IJZ-2024-000123", "jenjang": "S1",
        "prodi": "TEKNIK MENCARI CINTA SEJATI", "kampus": "UNIVERSITAS CONTOH NUSANTARA", "tgl_lulus": "20-08-2024",
        "no_skck": "SKCK/0123/X/2026", "skck_berlaku": "01-04-2027",
        "no_mcu": "MCU/2026/0456", "tgl_mcu": "20-09-2026", "kesimpulan": "LAYAK",
        "status_diharapkan": "TIDAK_LOLOS",
    },
    {
        "id": "P002", "skenario": "SKCK sudah tidak berlaku",
        "provinsi": "PROVINSI JAWA TENGAH", "kota": "KOTA SEMARANG", "gol_darah": "A", "tgl_terbit": "04-09-2020", "warna_foto": (40, 70, 160),
        "nama": "SITI RAHMAWATI", "jk": "PEREMPUAN", "tempat_lahir": "KENDAL", "tgl_lahir": "21-08-2002",
        "nik": "3374026108020002", "alamat": "JL. PANDANARAN NO. 45", "rtrw": "004/001",
        "kel": "RANDUSARI", "kec": "SEMARANG SELATAN",
        "nama_ijazah": "SITI RAHMAWATI", "no_ijazah": "IJZ-2024-000456", "jenjang": "S1",
        "prodi": "SISTEM INFORMASI", "kampus": "UNIVERSITAS CONTOH NUSANTARA", "tgl_lulus": "15-09-2024",
        "no_skck": "SKCK/0456/II/2026", "skck_berlaku": "10-08-2026",
        "no_mcu": "MCU/2026/0789", "tgl_mcu": "18-09-2026", "kesimpulan": "LAYAK",
        "status_diharapkan": "TIDAK_LOLOS",
    },
    {
        "id": "P003", "skenario": "nama di ijazah beda dengan KTP",
        "provinsi": "PROVINSI JAWA TENGAH", "kota": "KOTA SEMARANG", "gol_darah": "B", "tgl_terbit": "17-01-2018", "warna_foto": (178, 34, 34),
        "nama": "ANDI PRATAMA", "jk": "LAKI-LAKI", "tempat_lahir": "DEMAK", "tgl_lahir": "03-11-2000",
        "nik": "3374010311000003", "alamat": "JL. SULTAN AGUNG NO. 7", "rtrw": "001/005",
        "kel": "WONOTINGAL", "kec": "CANDISARI",
        "nama_ijazah": "ANDI PRASETYO", "no_ijazah": "IJZ-2023-000789", "jenjang": "S1",
        "prodi": "TEKNIK ELEKTRO", "kampus": "INSTITUT TEKNOLOGI CONTOH", "tgl_lulus": "28-02-2024",
        "no_skck": "SKCK/0789/IX/2026", "skck_berlaku": "15-03-2027",
        "no_mcu": "MCU/2026/1011", "tgl_mcu": "22-09-2026", "kesimpulan": "LAYAK",
        "status_diharapkan": "PERLU_REVIEW",
    },
    {
        "id": "P004", "skenario": "hasil MCU belum diunggah",
        "provinsi": "PROVINSI JAWA TENGAH", "kota": "KOTA SEMARANG", "gol_darah": "-", "tgl_terbit": "22-06-2021", "warna_foto": (40, 70, 160),
        "nama": "DEWI LESTARI", "jk": "PEREMPUAN", "tempat_lahir": "SALATIGA", "tgl_lahir": "09-01-2003",
        "nik": "3374024901030004", "alamat": "JL. SETIABUDI NO. 112", "rtrw": "003/002",
        "kel": "SRONDOL KULON", "kec": "BANYUMANIK",
        "nama_ijazah": "DEWI LESTARI", "no_ijazah": "IJZ-2025-000321", "jenjang": "D3",
        "prodi": "TEKNIK INFORMATIKA", "kampus": "POLITEKNIK CONTOH", "tgl_lulus": "30-07-2025",
        "no_skck": "SKCK/0321/VIII/2026", "skck_berlaku": "20-02-2027",
        "no_mcu": None, "tgl_mcu": None, "kesimpulan": None,
        "status_diharapkan": "UNGGAH_ULANG",
    },
    {
        "id": "P005", "skenario": "foto KTP buram",
        "provinsi": "PROVINSI JAWA TENGAH", "kota": "KOTA SEMARANG", "gol_darah": "AB", "tgl_terbit": "09-11-2019", "warna_foto": (178, 34, 34),
        "nama": "RIZKY HIDAYAT", "jk": "LAKI-LAKI", "tempat_lahir": "UNGARAN", "tgl_lahir": "12-06-2001",
        "nik": "3374011206010005", "alamat": "JL. NGESREP TIMUR NO. 3", "rtrw": "005/002",
        "kel": "SUMURBOTO", "kec": "BANYUMANIK",
        "nama_ijazah": "RIZKY HIDAYAT", "no_ijazah": "IJZ-2024-000654", "jenjang": "S1",
        "prodi": "ILMU KOMPUTER", "kampus": "UNIVERSITAS CONTOH NUSANTARA", "tgl_lulus": "25-08-2024",
        "no_skck": "SKCK/0654/IX/2026", "skck_berlaku": "05-03-2027",
        "no_mcu": "MCU/2026/1213", "tgl_mcu": "21-09-2026", "kesimpulan": "LAYAK",
        "status_diharapkan": "UNGGAH_ULANG",
        "ktp_buram": True,
    },
]


def font(ukuran, tebal=False, miring=False):
    if miring:
        return ImageFont.truetype(FONT_ITALIC_PATH, ukuran)
    return ImageFont.truetype(FONT_BOLD_PATH if tebal else FONT_PATH, ukuran)


def tulis_baris(draw, x, y, label, isi, lebar_label=330, ukuran=30):
    draw.text((x, y), label, font=font(ukuran), fill=(20, 20, 20))
    draw.text((x + lebar_label, y), ": " + isi, font=font(ukuran), fill=(20, 20, 20))


def halaman_kosong():
    # A4 kira-kira 150 dpi
    return Image.new("RGB", (1240, 1754), (255, 255, 255))


def gambar_ktp(p):
    """KTP fiktif dengan tata letak mirip KTP elektronik asli.
    Foto cuma siluet dan semua datanya karangan, jangan pakai KTP orang beneran."""
    halaman = halaman_kosong()
    W, H = 1012, 640

    # latar biru muda bergradasi
    grad = np.linspace(0, 1, W)[None, :, None]
    warna_kiri, warna_kanan = np.array([214, 232, 246]), np.array([186, 214, 238])
    latar = (warna_kiri * (1 - grad) + warna_kanan * grad) * np.ones((H, 1, 1))
    kartu = Image.fromarray(latar.astype(np.uint8))

    # watermark tulisan miring tipis-tipis seperti di KTP asli
    wm = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    dw = ImageDraw.Draw(wm)
    for baris in range(0, H * 2, 90):
        dw.text((0, baris), "KARTU TANDA PENDUDUK   " * 6, font=font(34, True), fill=(160, 195, 225, 70))
    wm = wm.rotate(25, center=(W, H)).crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
    kartu.paste(wm, (0, 0), wm)
    d = ImageDraw.Draw(kartu)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=24, outline=(120, 140, 160), width=3)

    hitam = (15, 15, 25)
    f_judul = font(30, True)
    for i, teks in enumerate([p["provinsi"], p["kota"]]):
        lebar = d.textlength(teks, font=f_judul)
        d.text(((W - lebar) / 2 - 40, 18 + i * 38), teks, font=f_judul, fill=hitam)
    d.text((30, 105), "NIK", font=font(38, True), fill=hitam)
    d.text((200, 105), ": " + p["nik"], font=font(38, True), fill=hitam)

    isi = [
        ("Nama", p["nama"], 0),
        ("Tempat/Tgl Lahir", p["tempat_lahir"] + ", " + p["tgl_lahir"], 0),
        ("Jenis Kelamin", p["jk"], 0),
        ("Alamat", p["alamat"], 0),
        ("RT/RW", p["rtrw"], 40),
        ("Kel/Desa", p["kel"], 40),
        ("Kecamatan", p["kec"], 40),
        ("Agama", p.get("agama", "ISLAM"), 0),
        ("Status Perkawinan", p.get("status_kawin", "BELUM KAWIN"), 0),
        ("Pekerjaan", p.get("pekerjaan", "PELAJAR/MAHASISWA"), 0),
        ("Kewarganegaraan", "WNI", 0),
        ("Berlaku Hingga", "SEUMUR HIDUP", 0),
    ]
    for i, (label, nilai, indent) in enumerate(isi):
        y = 165 + i * 37
        d.text((30 + indent, y), label, font=font(22), fill=hitam)
        d.text((250, y), ": " + nilai, font=font(22), fill=hitam)
        if label == "Jenis Kelamin":
            # golongan darah sebaris dengan jenis kelamin, sama seperti KTP asli
            d.text((500, y), "Gol. Darah : " + p.get("gol_darah", "O"), font=font(22), fill=hitam)

    # foto: siluet saja (bukan wajah orang)
    fx, fy, fw, fh = 760, 150, 200, 250
    d.rectangle([fx, fy, fx + fw, fy + fh], fill=p.get("warna_foto", (178, 34, 34)))
    d.ellipse([fx + 55, fy + 40, fx + 145, fy + 140], fill=(225, 225, 225))
    d.rounded_rectangle([fx + 20, fy + 150, fx + 180, fy + fh + 40], radius=60, fill=(225, 225, 225))
    d.rectangle([fx, fy + fh, fx + fw, fy + fh + 45], fill=tuple(int(c) for c in latar[0, -1]))
    d.rectangle([fx, fy, fx + fw, fy + fh], outline=(90, 90, 90), width=2)

    for i, teks in enumerate([p["kota"].replace("KOTA ", "").replace("KABUPATEN ", ""), p.get("tgl_terbit", "12-03-2019")]):
        f = font(22)
        lebar = d.textlength(teks, font=f)
        d.text((fx + (fw - lebar) / 2, fy + fh + 15 + i * 30), teks, font=f, fill=hitam)

    # tanda tangan asal-asalan (garis bergelombang)
    xs = np.linspace(fx + 10, fx + 190, 60)
    ys = fy + fh + 115 + 18 * np.sin((xs - fx) / 9) * np.exp(-(xs - fx) / 220)
    d.line(list(zip(xs, ys)), fill=(25, 25, 60), width=3)

    halaman.paste(kartu, (114, 150))
    return halaman


def logo_generik(d, cx, cy, r, teks="", warna=(60, 60, 60)):
    # logo bulat sederhana, sengaja TIDAK meniru lambang resmi (Garuda/Polri/dll)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=warna, width=3)
    d.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], outline=warna, width=1)
    if teks:
        f = font(int(r * 0.6), True)
        lebar = d.textlength(teks, font=f)
        d.text((cx - lebar / 2, cy - r * 0.38), teks, font=f, fill=warna)


def siluet_foto(d, x, y, w, h, warna_latar):
    d.rectangle([x, y, x + w, y + h], fill=warna_latar, outline=(90, 90, 90), width=2)
    d.ellipse([x + w * 0.3, y + h * 0.15, x + w * 0.7, y + h * 0.52], fill=(225, 225, 225))
    d.rounded_rectangle([x + w * 0.12, y + h * 0.58, x + w * 0.88, y + h], radius=int(w * 0.3), fill=(225, 225, 225))
    d.rectangle([x, y, x + w, y + h], outline=(90, 90, 90), width=2)


def tanda_tangan(d, x, y, lebar=180):
    xs = np.linspace(x, x + lebar, 60)
    ys = y + 18 * np.sin((xs - x) / 9) * np.exp(-(xs - x) / (lebar * 1.2))
    d.line(list(zip(xs, ys)), fill=(25, 25, 60), width=3)


def tulis_tengah(d, y, teks, f, warna=(15, 15, 15), lebar_halaman=1240):
    lebar = d.textlength(teks, font=f)
    d.text(((lebar_halaman - lebar) / 2, y), teks, font=f, fill=warna)


def gambar_ijazah(p):
    """Tata letak mengikuti template ijazah kosong (nomor di kanan atas, nama di tengah tanpa label,
    tulisan LULUS besar, pasfoto di bawah). Logo dan isinya fiktif."""
    img = halaman_kosong()
    d = ImageDraw.Draw(img)
    # logo kampus fiktif samar di tengah (watermark)
    wm = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(wm).ellipse([370, 520, 870, 1020], outline=(200, 200, 200, 110), width=10)
    img.paste(wm, (0, 0), wm)

    d.text((800, 70), "No. Ijazah : " + p["no_ijazah"], font=font(24), fill=(15, 15, 15))
    logo_generik(d, 120, 110, 45, "UC")
    d.text((180, 85), p["kampus"], font=font(20, True), fill=(15, 15, 15))
    d.text((180, 112), "Kota Semarang", font=font(18), fill=(15, 15, 15))
    logo_generik(d, 620, 200, 55, "")

    tulis_tengah(d, 290, p["kampus"], font(32, True))
    tulis_tengah(d, 340, "IJAZAH", font(64, True))
    tulis_tengah(d, 450, "Dengan ini menyatakan bahwa:", font(28))
    tulis_tengah(d, 505, p["nama_ijazah"], font(42, True))
    for i, (label, nilai) in enumerate([("tempat, tanggal lahir", p["tempat_lahir"] + ", " + p["tgl_lahir"]),
                                        ("Nomor Induk Mahasiswa", p.get("nim", "A11.2020.0" + p["id"][-2:] + "17"))]):
        tulis_baris(d, 200, 600 + i * 55, label, nilai, lebar_label=380, ukuran=28)
    tulis_tengah(d, 730, "L U L U S", font(54, True))
    tulis_tengah(d, 810, "dari", font(28))
    isi = [("Program Studi", p["prodi"]),
           ("Jenjang", p["jenjang"] + (" (SARJANA)" if p["jenjang"] == "S1" else " (DIPLOMA)")),
           ("Perguruan Tinggi", p["kampus"]),
           ("Tanggal Lulus", p["tgl_lulus"])]
    for i, (label, nilai) in enumerate(isi):
        tulis_baris(d, 200, 880 + i * 60, label, nilai, lebar_label=380, ukuran=28)
    d.text((200, 1130), "setelah memenuhi seluruh persyaratan akademik sesuai peraturan yang berlaku.",
           font=font(26), fill=(15, 15, 15))

    siluet_foto(d, 420, 1260, 180, 240, (230, 230, 230))
    d.text((760, 1240), "Semarang, " + p["tgl_lulus"], font=font(26), fill=(15, 15, 15))
    d.text((760, 1285), "Rektor,", font=font(26), fill=(15, 15, 15))
    tanda_tangan(d, 770, 1400)
    d.text((760, 1470), "Prof. Dr. Contoh Rektor", font=font(26, True), fill=(15, 15, 15))
    d.text((760, 1505), "NIP. 196501011990031001", font=font(24), fill=(15, 15, 15))
    return img


def gambar_skck(p):
    """Tata letak mengikuti SKCK (label dua bahasa, nomor kanan atas, foto kiri bawah).
    Lambang dan nama satuan polisi fiktif."""
    img = halaman_kosong()
    d = ImageDraw.Draw(img)
    hitam = (15, 15, 15)
    for i, t in enumerate(["KEPOLISIAN NEGARA REPUBLIK INDONESIA", "DAERAH CONTOH", "RESOR KOTA CONTOH"]):
        d.text((90, 60 + i * 30), t, font=font(20, True), fill=hitam)
    d.text((820, 70), "Nomor : " + p["no_skck"], font=font(24), fill=hitam)
    logo_generik(d, 620, 200, 50, "")
    tulis_tengah(d, 275, "SURAT KETERANGAN CATATAN KEPOLISIAN", font(34, True))
    tulis_tengah(d, 318, "POLICE RECORD", font(24, miring=True))
    d.text((120, 380), "Diterangkan bersama ini bahwa:", font=font(26), fill=hitam)
    d.text((120, 410), "This is to certify that:", font=font(20, miring=True), fill=(80, 80, 80))

    isi = [("Nama", "Name", p["nama"]),
           ("Jenis Kelamin", "Sex", p["jk"]),
           ("Kebangsaan", "Nationality", "INDONESIA"),
           ("Agama", "Religion", p.get("agama", "ISLAM")),
           ("Tempat dan Tgl. Lahir", "Place and date of birth", p["tempat_lahir"] + ", " + p["tgl_lahir"]),
           ("Alamat Sekarang", "Current address", p["alamat"]),
           ("Pekerjaan", "Occupation", p.get("pekerjaan", "PELAJAR/MAHASISWA")),
           ("Nomor Kartu Tanda Penduduk", "Identity card number", p["nik"])]
    for i, (lbl, eng, nilai) in enumerate(isi):
        y = 470 + i * 64
        d.text((120, y), lbl, font=font(26), fill=hitam)
        d.text((120, y + 29), eng, font=font(18, miring=True), fill=(80, 80, 80))
        d.text((560, y), ": " + nilai, font=font(26), fill=hitam)

    d.text((120, 1000), "Tidak memiliki catatan atau keterlibatan dalam kegiatan kriminal apapun.", font=font(26), fill=hitam)
    tgl_awal = "01-" + p["skck_berlaku"][3:5] + "-" + str(int(p["skck_berlaku"][6:]) - 1)
    for i, (lbl, eng, nilai) in enumerate([("Untuk keperluan", "For the purpose", "MELAMAR PROGRAM MAGANG"),
                                           ("Berlaku dari tanggal", "Valid from", tgl_awal),
                                           ("Sampai dengan", "To", p["skck_berlaku"])]):
        y = 1070 + i * 64
        d.text((120, y), lbl, font=font(26), fill=hitam)
        d.text((120, y + 29), eng, font=font(18, miring=True), fill=(80, 80, 80))
        d.text((560, y), ": " + nilai, font=font(26), fill=hitam)

    siluet_foto(d, 120, 1300, 180, 240, (178, 34, 34))
    d.text((700, 1300), "Dikeluarkan di : SEMARANG", font=font(24), fill=hitam)
    d.text((700, 1335), "KEPALA KEPOLISIAN RESOR KOTA CONTOH", font=font(22, True), fill=hitam)
    tanda_tangan(d, 760, 1450)
    # stempel bulat samar
    stempel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(stempel).ellipse([640, 1360, 860, 1580], outline=(90, 90, 170, 90), width=6)
    img.paste(stempel, (0, 0), stempel)
    return img


def gambar_mcu(p):
    """Tata letak mengikuti formulir medical check up klinik. Nama klinik & isi fiktif."""
    img = halaman_kosong()
    d = ImageDraw.Draw(img)
    hitam, teal = (15, 15, 15), (20, 90, 100)
    logo_generik(d, 170, 110, 50, "KC", teal)
    d.text((250, 70), "KLINIK CONTOH SEHAT", font=font(46, True), fill=teal)
    d.text((250, 130), "Alamat : Jl. Contoh Raya No. 1, Kota Semarang", font=font(22), fill=hitam)
    d.line([(90, 175), (1150, 175)], fill=hitam, width=3)
    tulis_tengah(d, 215, "SURAT KETERANGAN HASIL MEDICAL CHECK UP", font(32, True))
    tulis_tengah(d, 260, "Nomor : " + p["no_mcu"], font(26))
    d.text((120, 330), "Yang bertanda tangan di bawah ini menerangkan bahwa:", font=font(26), fill=hitam)
    isi = [("Nama", p["nama"]), ("Jenis Kelamin", p["jk"]),
           ("Tempat/ Tanggal Lahir", p["tempat_lahir"] + ", " + p["tgl_lahir"]),
           ("Pekerjaan", p.get("pekerjaan", "PELAJAR/MAHASISWA")), ("Alamat", p["alamat"])]
    for i, (label, nilai) in enumerate(isi):
        tulis_baris(d, 120, 390 + i * 52, label, nilai, lebar_label=330, ukuran=26)

    tulis_tengah(d, 680, "HASIL PEMERIKSAAN", font(28, True))
    hasil = [("Tekanan Darah", "118/76 mmHg"), ("Tinggi / Berat Badan", "170 cm / 64 kg"),
             ("Penglihatan", "Normal"), ("Buta Warna", "Tidak"), ("Rontgen Thorax", "Dalam batas normal")]
    for i, (label, nilai) in enumerate(hasil):
        tulis_baris(d, 160, 740 + i * 48, "- " + label, nilai, lebar_label=330, ukuran=24)

    tulis_baris(d, 120, 1010, "Tanggal Pemeriksaan", p["tgl_mcu"], lebar_label=330, ukuran=26)
    tulis_baris(d, 120, 1065, "Kesimpulan", p["kesimpulan"], lebar_label=330, ukuran=28)
    d.text((780, 1180), "Semarang, " + p["tgl_mcu"], font=font(26), fill=hitam)
    d.text((780, 1220), "Dokter Pemeriksa,", font=font(26), fill=hitam)
    tanda_tangan(d, 790, 1330)
    d.text((780, 1400), "dr. Contoh Dokter", font=font(26, True), fill=hitam)
    return img


def spesimen(img):
    # watermark samar biar jelas ini dokumen contoh, bukan dokumen asli
    wm = Image.new("RGBA", (img.width * 2, img.height * 2), (0, 0, 0, 0))
    dw = ImageDraw.Draw(wm)
    for y in range(200, img.height * 2, 700):
        dw.text((300, y), "SPESIMEN - DATA FIKTIF", font=font(90, True), fill=(150, 150, 150, 35))
    wm = wm.rotate(35, center=(img.width, img.height))
    wm = wm.crop((img.width // 2, img.height // 2, img.width // 2 + img.width, img.height // 2 + img.height))
    img = img.convert("RGBA")
    img.alpha_composite(wm)
    return img.convert("RGB")


def efek_scan(img, buram=False):
    # miringkan sedikit + noise + kompres jpeg, biar kaya hasil scan HP
    sudut = random.uniform(-1.5, 1.5)
    img = img.rotate(sudut, expand=False, fillcolor=(255, 255, 255))
    if buram:
        img = img.filter(ImageFilter.GaussianBlur(radius=6))
    arr = np.array(img).astype(np.float32)
    arr += np.random.normal(0, 4, arr.shape)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def simpan_pdf(img, path):
    img = img.convert("RGB")
    img.save(path, "PDF", resolution=150, quality=70)
    ukuran_kb = os.path.getsize(path) / 1024
    print(f"  - {path} ({ukuran_kb:.0f} KB)")


def ke_iso(tgl):
    # "15-05-2001" -> "2001-05-15"
    if tgl is None:
        return None
    d, m, y = tgl.split("-")
    return f"{y}-{m}-{d}"


if __name__ == "__main__":
    for p in pendaftar_list:
        folder = os.path.join(FOLDER_OUTPUT, p["id"])
        os.makedirs(folder, exist_ok=True)
        print(f"Membuat dokumen {p['id']} ({p['skenario']})")

        simpan_pdf(efek_scan(spesimen(gambar_ktp(p)), buram=p.get("ktp_buram", False)), os.path.join(folder, "ktp.pdf"))
        simpan_pdf(efek_scan(spesimen(gambar_ijazah(p))), os.path.join(folder, "ijazah.pdf"))
        simpan_pdf(efek_scan(spesimen(gambar_skck(p))), os.path.join(folder, "skck.pdf"))
        if p["no_mcu"] is not None:
            simpan_pdf(efek_scan(spesimen(gambar_mcu(p))), os.path.join(folder, "mcu.pdf"))
        else:
            print("  - mcu.pdf sengaja tidak dibuat")

        # ground truth buat evaluasi nanti
        gt = {
            "id_pendaftar": p["id"],
            "skenario": p["skenario"],
            "status_diharapkan": p["status_diharapkan"],
            "KTP": {"nik": p["nik"], "nama": p["nama"], "tempat_lahir": p["tempat_lahir"],
                    "tanggal_lahir": ke_iso(p["tgl_lahir"]), "jenis_kelamin": p["jk"],
                    "alamat": f"{p['alamat']}, RT {p['rtrw'].split('/')[0]}/RW {p['rtrw'].split('/')[1]}, {p['kel']}, {p['kec']}"},
            "IJAZAH": {"nama": p["nama_ijazah"], "nomor_ijazah": p["no_ijazah"], "jenjang": p["jenjang"],
                       "program_studi": p["prodi"], "institusi": p["kampus"], "tanggal_lulus": ke_iso(p["tgl_lulus"])},
            "SKCK": {"nama": p["nama"], "nomor_skck": p["no_skck"], "berlaku_hingga": ke_iso(p["skck_berlaku"])},
        }
        if p["no_mcu"] is not None:
            gt["MCU"] = {"nama": p["nama"], "nomor_surat": p["no_mcu"], "tanggal_periksa": ke_iso(p["tgl_mcu"]),
                         "kesimpulan": p["kesimpulan"]}
        with open(os.path.join(folder, "ground_truth.json"), "w") as f:
            json.dump(gt, f, indent=2)

    print("Selesai. Semua data di atas fiktif.")
