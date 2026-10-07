# Evaluasi hasil pipeline dibandingkan ground truth dummy.
# Jalankan main.py dulu supaya folder hasil/ terisi.
#   python evaluasi.py

import os
import json
import glob
from collections import defaultdict
from rapidfuzz.distance import Levenshtein


def normalisasi(x):
    if x is None:
        return ""
    return " ".join(str(x).upper().split())


def main(folder_dummy="data/dummy", folder_hasil="hasil"):
    benar = defaultdict(int)
    total = defaultdict(int)
    cer_total = defaultdict(float)
    jumlah_status_benar = 0
    jumlah_pendaftar = 0
    salah_tolak = 0

    print(f"{'ID':<6}{'Skenario':<38}{'Diharapkan':<15}{'Hasil':<15}")
    print("-" * 74)
    for path_gt in sorted(glob.glob(os.path.join(folder_dummy, "*", "ground_truth.json"))):
        with open(path_gt, encoding="utf-8") as f:
            gt = json.load(f)
        path_hasil = os.path.join(folder_hasil, gt["id_pendaftar"] + ".json")
        if not os.path.exists(path_hasil):
            print(f"{gt['id_pendaftar']}: belum ada hasil, jalankan main.py dulu")
            continue
        with open(path_hasil, encoding="utf-8") as f:
            hasil = json.load(f)

        jumlah_pendaftar += 1
        status, diharapkan = hasil["status"], gt["status_diharapkan"]
        tanda = "OK" if status == diharapkan else "beda"
        if status == diharapkan:
            jumlah_status_benar += 1
        # salah tolak = sistem bilang TIDAK_LOLOS padahal seharusnya tidak
        if status == "TIDAK_LOLOS" and diharapkan != "TIDAK_LOLOS":
            salah_tolak += 1
        print(f"{gt['id_pendaftar']:<6}{gt['skenario']:<38}{diharapkan:<15}{status:<15}{tanda}")

        # akurasi per field (hanya untuk dokumen yang sempat diekstrak)
        for jenis in ["KTP", "IJAZAH", "SKCK", "MCU"]:
            if jenis not in gt or jenis not in hasil["rekap"]:
                continue
            for field, nilai_gt in gt[jenis].items():
                kunci = f"{jenis}.{field}"
                prediksi = hasil["rekap"][jenis][field]["nilai"]
                a, b = normalisasi(prediksi), normalisasi(nilai_gt)
                total[kunci] += 1
                benar[kunci] += int(a == b)
                cer_total[kunci] += Levenshtein.distance(a, b) / max(len(b), 1)

    print(f"\nStatus benar : {jumlah_status_benar}/{jumlah_pendaftar}")
    print(f"Salah tolak  : {salah_tolak}  (target 0)")

    print(f"\n{'Field':<26}{'Akurasi':>10}{'CER':>10}")
    print("-" * 46)
    semua_benar, semua_total = 0, 0
    for kunci in sorted(total):
        akurasi = benar[kunci] / total[kunci]
        cer = cer_total[kunci] / total[kunci]
        semua_benar += benar[kunci]
        semua_total += total[kunci]
        print(f"{kunci:<26}{akurasi:>10.2f}{cer:>10.3f}")
    if semua_total:
        print(f"\nAkurasi field keseluruhan: {semua_benar}/{semua_total} = {semua_benar / semua_total:.2f}")
    print("Catatan: CER di sini dihitung dari nilai field akhir (setelah koreksi), jadi cuma perkiraan.")


if __name__ == "__main__":
    main()
