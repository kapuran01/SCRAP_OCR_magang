# Klasifikasi jenis dokumen.
# Rencananya pakai MobileNetV3 yang dilatih (lihat split_data.py untuk pembagian datanya).
# Untuk prototipe ini sementara pakai kata kunci dari hasil OCR dulu.
# TODO: ganti ke model MobileNetV3 kalau data latih sudah cukup

from rapidfuzz import fuzz

KATA_KUNCI = {
    "KTP": ["NIK", "PROVINSI", "KEWARGANEGARAAN", "KEL/DESA"],
    "IJAZAH": ["IJAZAH", "PROGRAM STUDI", "LULUS", "TANGGAL LULUS"],
    "SKCK": ["CATATAN KEPOLISIAN", "POLICE RECORD", "KEPOLISIAN"],
    "MCU": ["MEDICAL CHECK UP", "HASIL PEMERIKSAAN", "KESIMPULAN", "DOKTER PEMERIKSA"],
}


def klasifikasi_dokumen(baris_list):
    semua_teks = " ".join(b["teks"].upper() for b in baris_list)
    skor = {}
    for jenis, kunci_list in KATA_KUNCI.items():
        skor[jenis] = sum(1 for k in kunci_list if fuzz.partial_ratio(k, semua_teks) >= 90)
    jenis_terbaik = max(skor, key=skor.get)
    if skor[jenis_terbaik] < 2:
        return "LAINNYA", skor
    return jenis_terbaik, skor
