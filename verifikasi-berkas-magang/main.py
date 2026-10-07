# Program utama: verifikasi berkas calon peserta magang
# Cara pakai:
#   python main.py data/dummy            -> proses semua pendaftar di folder
#   python main.py data/dummy/P001       -> proses satu pendaftar saja
#   python main.py data/dummy --tanpa-llm

import os
import sys
import json
import time
import argparse
import yaml

from src.preprocessing import cek_file, pdf_ke_gambar, proses_gambar
from src.ocr import baca_kotak_teks, gabung_per_baris, engine_yang_dipakai
from src.klasifikasi import klasifikasi_dokumen
from src.ekstraksi import ekstrak, ollama_tersedia
from src.validasi import tentukan_status

DOKUMEN_WAJIB = {"KTP": "ktp.pdf", "IJAZAH": "ijazah.pdf", "SKCK": "skck.pdf", "MCU": "mcu.pdf"}


def baca_config(path="config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def proses_ocr(path_pdf, cfg):
    """PDF -> preprocessing -> OCR -> daftar baris ber-ID"""
    semua_baris = []
    nomor = 1
    for i, img in enumerate(pdf_ke_gambar(path_pdf, cfg["preprocessing"]["dpi"])):
        img, skor = proses_gambar(img, cfg)
        if skor < cfg["ambang"]["laplacian_min"]:
            return {"status": "UNGGAH_ULANG", "alasan": f"gambar buram (skor ketajaman {skor:.1f})", "skor_tajam": skor}
        kotak = baca_kotak_teks(img, cfg)
        for b in gabung_per_baris(kotak):
            b["id"] = f"L{nomor:02d}"
            b["halaman"] = i + 1
            nomor += 1
            semua_baris.append(b)
    return {"status": "OK", "baris": semua_baris, "skor_tajam": skor}


def verifikasi_pendaftar(folder, cfg, pakai_llm):
    id_pendaftar = os.path.basename(os.path.normpath(folder))
    print(f"\n=== {id_pendaftar} ===")
    hasil = {"id_pendaftar": id_pendaftar, "dokumen": {}, "rekap": {}}

    # 1. cek unggahan (R1 bagian file)
    for jenis, nama_file in DOKUMEN_WAJIB.items():
        ok, alasan = cek_file(os.path.join(folder, nama_file), cfg["preprocessing"]["ukuran_file_maks_mb"])
        if not ok:
            print(f"  {jenis}: {alasan}")
            hasil.update(status="UNGGAH_ULANG", alasan=[f"R1: {jenis} {alasan}"])
            return hasil

    # 2. OCR + ekstraksi per dokumen
    catatan = []
    for jenis, nama_file in DOKUMEN_WAJIB.items():
        t0 = time.time()
        ocr = proses_ocr(os.path.join(folder, nama_file), cfg)
        if ocr["status"] != "OK":
            print(f"  {jenis}: {ocr['alasan']}")
            hasil.update(status="UNGGAH_ULANG", alasan=[f"R1: {jenis} {ocr['alasan']}"])
            return hasil

        jenis_terdeteksi, _ = klasifikasi_dokumen(ocr["baris"])
        if jenis_terdeteksi != jenis:
            catatan.append(f"R1: file di kolom {jenis} terdeteksi sebagai {jenis_terdeteksi} (kemungkinan salah unggah)")

        data, metode = ekstrak(ocr["baris"], jenis, cfg, pakai_llm)
        hasil["rekap"][jenis] = data.model_dump()
        hasil["dokumen"][jenis] = {
            "jenis_terdeteksi": jenis_terdeteksi,
            "skor_tajam": round(ocr["skor_tajam"], 1),
            "metode_ekstraksi": metode,
            "baris": ocr["baris"],  # disimpan buat ditampilkan ke admin (bbox)
        }
        print(f"  {jenis}: {len(ocr['baris'])} baris, terdeteksi {jenis_terdeteksi}, "
              f"ekstraksi {metode} ({time.time() - t0:.1f} s)")

    # 3. validasi
    status, alasan = tentukan_status(hasil["rekap"], cfg, catatan)
    hasil.update(status=status, alasan=alasan)
    return hasil


def tampilkan_ringkas(hasil):
    print(f"  -> STATUS: {hasil['status']}")
    for a in hasil["alasan"]:
        print(f"     - {a}")
    ktp = hasil["rekap"].get("KTP")
    if ktp:
        for f in ["nik", "nama", "tanggal_lahir"]:
            print(f"     {f:<14}: {ktp[f]['nilai']}  (conf {ktp[f]['confidence']:.2f}"
                  f"{', dikoreksi' if ktp[f]['dikoreksi'] else ''})")


def main():
    parser = argparse.ArgumentParser(description="Verifikasi berkas calon peserta magang (prototipe)")
    parser.add_argument("folder", help="folder satu pendaftar atau folder berisi banyak pendaftar")
    parser.add_argument("--tanpa-llm", action="store_true", help="pakai ekstraksi regex saja")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", default="hasil")
    args = parser.parse_args()

    cfg = baca_config(args.config)
    pakai_llm = cfg["llm"]["pakai_llm"] and not args.tanpa_llm
    if pakai_llm and not ollama_tersedia(cfg):
        print("[!] Ollama tidak terdeteksi, otomatis pakai ekstraksi regex")
        pakai_llm = False

    # bisa satu folder pendaftar atau folder berisi banyak pendaftar
    if os.path.exists(os.path.join(args.folder, "ktp.pdf")) or os.path.exists(os.path.join(args.folder, "ground_truth.json")):
        daftar_folder = [args.folder]
    else:
        daftar_folder = sorted(os.path.join(args.folder, d) for d in os.listdir(args.folder)
                               if os.path.isdir(os.path.join(args.folder, d)))
    if not daftar_folder:
        print("Tidak ada folder pendaftar")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)
    rangkuman = []
    for folder in daftar_folder:
        hasil = verifikasi_pendaftar(folder, cfg, pakai_llm)
        tampilkan_ringkas(hasil)
        with open(os.path.join(args.output, hasil["id_pendaftar"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(hasil, f, indent=2, ensure_ascii=False)
        rangkuman.append((hasil["id_pendaftar"], hasil["status"]))

    print(f"\nOCR engine: {engine_yang_dipakai()} | LLM: {'Ollama ' + cfg['llm']['model'] if pakai_llm else 'tidak (regex)'}")
    print("\nRANGKUMAN")
    for id_p, status in rangkuman:
        print(f"  {id_p}: {status}")
    print(f"\nHasil lengkap disimpan di folder '{args.output}/'")


if __name__ == "__main__":
    main()
