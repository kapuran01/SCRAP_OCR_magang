# Verifikasi Berkas Calon Peserta Magang (Prototipe)

Prototipe sederhana untuk studi kasus AI Engineer Intern. Programnya membaca berkas pendaftar
(KTP, ijazah, SKCK, hasil MCU) dalam bentuk PDF, lalu:

1. **Preprocessing**: PDF diubah jadi gambar 300 dpi, area dokumen dipotong, ukuran disamakan (sisi panjang 2000 px), cek buram, diluruskan, kontras diperbaiki
2. **OCR**: PaddleOCR (kalau tidak bisa, otomatis pakai Tesseract). Kotak teks digabung per baris dan diberi ID
3. **Klasifikasi dokumen**: sementara pakai kata kunci (rencananya MobileNetV3)
4. **Ekstraksi data**: LLM lokal Qwen2.5 lewat Ollama. Kalau Ollama belum jalan, pakai regex sederhana
5. **Validasi (rule engine)**: cek aturan R1–R9, lalu menentukan status `LOLOS`, `PERLU_REVIEW`, `TIDAK_LOLOS`, atau `UNGGAH_ULANG`

Semua data di folder `data/dummy` adalah **data fiktif** yang dibuat dengan `buat_dummy.py`.
Tata letak dokumen dummy dibuat mirip aslinya: KTP (latar biru, Gol. Darah sebaris dengan jenis kelamin),
ijazah (nama di tengah tanpa label, tulisan LULUS), SKCK (label dua bahasa), dan surat MCU klinik.
Foto hanya siluet, logo dibuat generik (tidak meniru lambang resmi), semua isinya karangan,
dan setiap dokumen diberi watermark "SPESIMEN - DATA FIKTIF".
Sengaja **tidak memakai KTP asli dari internet** karena berisi data pribadi orang lain (lihat UU No. 27 Tahun 2022 tentang PDP).

> Ini masih prototipe, belum aplikasi jadi. Tujuannya untuk menunjukkan alurnya jalan dari awal sampai akhir.

## Struktur folder

```
├── main.py              # program utama
├── buat_dummy.py        # membuat dokumen dummy + ground truth
├── evaluasi.py          # bandingkan hasil dengan ground truth
├── split_data.py        # contoh pembagian data (grouped k-fold) untuk melatih klasifikasi nanti
├── config.yaml          # semua pengaturan & ambang
├── src/
│   ├── preprocessing.py
│   ├── ocr.py
│   ├── klasifikasi.py
│   ├── ekstraksi.py     # prompt LLM + fallback regex + hitung confidence
│   ├── skema.py         # skema Pydantic per jenis dokumen
│   └── validasi.py      # rule engine R1-R9
└── data/dummy/P001 ... P005
```

## Langkah menjalankan (Windows + VS Code)

Saya pakai Windows dan Python 3.11.

**1. Buka proyek di VS Code**
Ekstrak zip, lalu di VS Code pilih **File > Open Folder** dan pilih folder `verifikasi-berkas-magang`.

**2. Buat virtual environment**
Buka terminal (Ctrl + \`) lalu jalankan:

```bash
py -3.11 -m venv venv
venv\Scripts\activate
```

Kalau di PowerShell muncul error "running scripts is disabled", jalankan dulu
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` lalu ulangi activate.
Setelah itu pilih interpreter-nya: **Ctrl + Shift + P > Python: Select Interpreter > venv**.

**3. Install library**

```bash
pip install -r requirements.txt
```

`paddlepaddle` ukurannya cukup besar. Kalau gagal install, hapus dua baris paddle di `requirements.txt`
dan install ulang, program tetap jalan pakai Tesseract.

**4. Install Tesseract (cadangan OCR)**
Download installer dari https://github.com/UB-Mannheim/tesseract/wiki, install, lalu isi path-nya di `config.yaml`:

```yaml
tesseract_cmd: "C:/Program Files/Tesseract-OCR/tesseract.exe"
```

**5. (Opsional) Install Ollama untuk LLM**
Install dari https://ollama.com, lalu di terminal:

```bash
ollama pull qwen2.5:7b
ollama list            # pastikan qwen2.5:7b sudah ada
```

Di Windows Ollama otomatis jalan di background. Kalau Ollama tidak ada, program otomatis pakai ekstraksi regex.

**6. Jalankan**

```bash
python buat_dummy.py             # (opsional) buat ulang dokumen dummy
python main.py data/dummy        # proses semua pendaftar
python main.py data/dummy/P001   # proses satu pendaftar saja
python main.py data/dummy --tanpa-llm
python evaluasi.py               # bandingkan hasil dengan ground truth
python split_data.py             # contoh pembagian data grouped k-fold
```

Atau lewat panel **Run and Debug** di VS Code (konfigurasinya sudah ada di `.vscode/launch.json`).
Waktu pertama kali jalan, PaddleOCR akan download model dulu jadi agak lama.

**7. Lihat hasil**
Setiap pendaftar punya file `hasil/<ID>.json` berisi status, alasan, data hasil ekstraksi + confidence,
dan semua baris OCR beserta bbox-nya.

### Kalau ada masalah

| Pesan | Solusi |
|---|---|
| `TesseractNotFoundError` | path `tesseract_cmd` di `config.yaml` belum benar |
| `PaddleOCR gagal ..., pindah ke Tesseract` | biasanya model belum ke-download (cek internet), program tetap jalan |
| `Ollama tidak terdeteksi` | Ollama belum jalan / belum install, program pakai regex |
| `ModuleNotFoundError: src` | jalankan dari folder utama proyek, bukan dari dalam folder `src` |

## Upload ke GitHub

```bash
git init
git add .
git commit -m "prototipe verifikasi berkas magang"
git branch -M main
git remote add origin https://github.com/<username>/verifikasi-berkas-magang.git
git push -u origin main
```

(buat repo kosong dulu di GitHub dengan nama yang sama)

## Skenario data dummy

| ID   | Skenario                         | Status yang diharapkan |
|------|----------------------------------|------------------------|
| P001 | program studi tidak sesuai syarat | TIDAK_LOLOS            |
| P002 | SKCK sudah tidak berlaku         | TIDAK_LOLOS            |
| P003 | nama di ijazah beda dengan KTP   | PERLU_REVIEW           |
| P004 | hasil MCU belum diunggah         | UNGGAH_ULANG           |
| P005 | foto KTP buram                   | UNGGAH_ULANG           |

## Contoh hasil (Tesseract + regex, tanpa LLM)

```
P001  program studi tidak sesuai syarat     TIDAK_LOLOS    TIDAK_LOLOS    OK
P002  SKCK sudah tidak berlaku              TIDAK_LOLOS    TIDAK_LOLOS    OK
P003  nama di ijazah beda dengan KTP        PERLU_REVIEW   PERLU_REVIEW   OK
P004  hasil MCU belum diunggah              UNGGAH_ULANG   UNGGAH_ULANG   OK
P005  foto KTP buram                        UNGGAH_ULANG   UNGGAH_ULANG   OK

Status benar : 5/5
Salah tolak  : 0  (target 0)
Akurasi field keseluruhan: 49/57 = 0.86
```

Field yang paling sering salah adalah nomor dokumen (misalnya angka romawi "IX" terbaca "1X"), tapi field ini
tidak dipakai untuk menentukan kelulusan. Kalau Tesseract kurang yakin membaca field penting, berkas akan masuk
`PERLU_REVIEW` dulu, bukan langsung ditolak.

Contoh alasan untuk P001: `R3: program studi TEKNIK MENCARI CINTA SEJATI tidak sesuai syarat`.

Hasil OCR bisa sedikit beda tiap kali dummy dibuat ulang (noise-nya acak), jadi angka akurasinya bisa naik turun.

## Catatan kalibrasi

- **Pelurusan dokumen**: awalnya pakai minAreaRect dari semua piksel teks, tapi di halaman MCU sudutnya
  terbaca 8 derajat padahal aslinya 0.8 derajat, jadi hasil OCR-nya kacau. Sekarang pakai median sudut
  tiap baris teks (lihat `luruskan()` di `preprocessing.py`).
- **Ambang buram**: di rancangan awal saya tulis varians Laplacian 100. Di data dummy, dokumen normal skornya
  sekitar 130–410 (KTP paling rendah karena latarnya bergradasi) dan dokumen buram cuma sekitar 2.
  Waktu masih pakai template lama, surat MCU skornya cuma ~88, jadi ambang 100 bakal salah menolak.
  Makanya di `config.yaml` saya pakai 40 supaya aman.
- **Ambang confidence per engine**: confidence Tesseract cenderung lebih rendah dari PaddleOCR,
  jadi ambangnya dibedakan (`per_engine` di config). Angkanya masih hasil coba-coba di data dummy.
- **Confidence field** dihitung dari confidence OCR bagian nilai (kata setelah ":"), bukan dari LLM.
  Kalau nilainya dikoreksi (misal O jadi 0), confidence dikali 0.9.

## Belum dikerjakan / TODO

- [ ] Klasifikasi dokumen pakai MobileNetV3 (sekarang masih kata kunci). Pembagian datanya sudah disiapkan di `split_data.py`
- [ ] Halaman review admin (rencananya pakai Streamlit, bbox di JSON sudah bisa dipakai untuk menandai bagian yang meragukan)
- [ ] Simpan ke database (sekarang masih file JSON, cek NIK ganda juga baru di memori)
- [ ] Uji dengan dokumen asli yang sudah disamarkan
