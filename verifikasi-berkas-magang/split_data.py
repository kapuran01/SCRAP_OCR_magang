# Contoh pembagian data latih untuk model klasifikasi dokumen (MobileNetV3) nanti.
# Prinsipnya: semua dokumen milik satu pendaftar harus berada di bagian yang sama,
# supaya tidak ada data leakage (dokumen orang yang sama muncul di data latih DAN data uji).
#
# Langkah:
#   1. pisahkan 20% pendaftar sebagai data uji akhir (tidak disentuh sampai evaluasi terakhir)
#   2. sisanya dibagi pakai grouped k-fold (k=5, grup = pendaftar)
#
# Di data dummy cuma ada 5 pendaftar jadi jumlah fold-nya menyesuaikan.
# Untuk data asli targetnya 100-200 dokumen per jenis.

import os
import csv
import glob
import numpy as np
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

FOLDER = "data/dummy"
LABEL = {"ktp.pdf": "KTP", "ijazah.pdf": "IJAZAH", "skck.pdf": "SKCK", "mcu.pdf": "MCU"}

paths, labels, groups = [], [], []
for path in sorted(glob.glob(os.path.join(FOLDER, "*", "*.pdf"))):
    nama_file = os.path.basename(path)
    if nama_file not in LABEL:
        continue
    paths.append(path)
    labels.append(LABEL[nama_file])
    groups.append(os.path.basename(os.path.dirname(path)))  # grup = id pendaftar

paths, labels, groups = np.array(paths), np.array(labels), np.array(groups)
print(f"Total dokumen: {len(paths)} dari {len(set(groups))} pendaftar")

# 1. data uji akhir 20%
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
idx_sisa, idx_uji = next(gss.split(paths, labels, groups))
print(f"Data uji akhir : {sorted(str(g) for g in set(groups[idx_uji]))}")

# 2. grouped k-fold untuk sisanya
n_grup_sisa = len(set(groups[idx_sisa]))
k = min(5, n_grup_sisa)
gkf = GroupKFold(n_splits=k)
baris_csv = [(p, l, g, "uji_akhir") for p, l, g in zip(paths[idx_uji], labels[idx_uji], groups[idx_uji])]

for fold, (idx_latih, idx_val) in enumerate(gkf.split(paths[idx_sisa], labels[idx_sisa], groups[idx_sisa])):
    grup_latih = set(str(g) for g in groups[idx_sisa][idx_latih])
    grup_val = set(str(g) for g in groups[idx_sisa][idx_val])
    assert grup_latih.isdisjoint(grup_val), "ada pendaftar yang bocor ke dua bagian!"
    print(f"Fold {fold + 1}: latih {sorted(grup_latih)} | validasi {sorted(grup_val)}")
    for i in idx_val:
        baris_csv.append((paths[idx_sisa][i], labels[idx_sisa][i], groups[idx_sisa][i], f"fold_{fold + 1}"))

os.makedirs("data", exist_ok=True)
with open("data/split.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["path", "label", "pendaftar", "bagian"])
    w.writerows(baris_csv)
print("Pembagian disimpan di data/split.csv")
print("Augmentasi (rotasi, blur, kecerahan, JPEG) nanti HANYA diterapkan ke data latih tiap fold.")
