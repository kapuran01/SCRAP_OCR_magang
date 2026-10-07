# Tahap ekstraksi: teks OCR -> JSON terstruktur.
# Cara utama pakai LLM lokal (Qwen2.5 lewat Ollama).
# Kalau Ollama belum jalan, pakai ekstraksi regex sederhana supaya pipeline tetap bisa dicoba.

import re
import json
import requests
from rapidfuzz import fuzz
from pydantic import ValidationError

from src.skema import SKEMA

PROMPT_TEMPLATE = """Ubah teks hasil OCR dokumen berikut menjadi JSON sesuai skema.
Tugas ini hanya ekstraksi data, bukan menilai kelayakan peserta.

Aturan:
1. Ambil data hanya dari baris teks yang diberikan. Jangan menebak atau mengarang data.
2. Untuk setiap field, tulis nilainya dan ID baris asalnya pada "baris_sumber".
   Satu field boleh berasal dari beberapa baris.
3. Jika field tidak ditemukan atau tidak terbaca, isi "nilai": null dan "baris_sumber": [].
4. Perbaiki salah baca OCR hanya jika konteksnya jelas, lalu isi "dikoreksi": true.
   - Pada angka (NIK, nomor dokumen, tanggal): O -> 0, I/l -> 1, S -> 5, B -> 8
   - Pada nama dan alamat: 0 -> O, 1 -> I, 5 -> S
5. Tanggal ditulis YYYY-MM-DD, NIK 16 digit tanpa spasi, nama dan alamat huruf kapital.
6. Untuk MCU, ambil kesimpulannya saja: LAYAK, TIDAK LAYAK, atau LAYAK DENGAN CATATAN.
7. Jawab hanya dengan JSON, tanpa penjelasan.

Skema ({jenis}):
{skema}

Baris teks (ID | teks):
{baris}
"""


# ---------------------------------------------------------------- LLM (Ollama)

def ollama_tersedia(cfg):
    try:
        r = requests.get(cfg["llm"]["ollama_url"] + "/api/tags", timeout=3)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def buat_prompt(baris_list, jenis):
    kelas = SKEMA[jenis]
    # contoh skema dibuat satu baris per field biar prompt tidak terlalu panjang
    isi_skema = ",\n".join(f'  "{f}": {{"nilai": "...", "baris_sumber": ["L.."], "dikoreksi": false}}'
                           for f in kelas.model_fields)
    skema = "{\n" + isi_skema + "\n}"
    teks_baris = "\n".join(f"{b['id']} | {b['teks']}" for b in baris_list)
    return PROMPT_TEMPLATE.format(jenis=jenis, skema=skema, baris=teks_baris)


def panggil_llm(baris_list, jenis, cfg):
    prompt = buat_prompt(baris_list, jenis)
    kelas = SKEMA[jenis]
    for percobaan in range(2):  # kalau gagal, ulang sekali
        r = requests.post(cfg["llm"]["ollama_url"] + "/api/chat", json={
            "model": cfg["llm"]["model"],
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        }, timeout=cfg["llm"]["timeout_detik"])
        r.raise_for_status()
        isi = r.json()["message"]["content"]
        try:
            data = json.loads(isi)
            # kadang LLM membungkus jawaban, misal {"KTP": {...}}
            if len(data) == 1 and isinstance(list(data.values())[0], dict) and list(data.keys())[0] not in kelas.model_fields:
                data = list(data.values())[0]
            return kelas.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"    JSON dari LLM tidak valid (percobaan {percobaan + 1}): {str(e)[:80]}")
    return None


# ---------------------------------------------------------------- fallback regex

PETA_ANGKA = str.maketrans({"O": "0", "o": "0", "D": "0", "I": "1", "L": "1", "l": "1", "|": "1", "S": "5", "B": "8", "Z": "2"})
PETA_HURUF = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "]": "I", "|": "I"})

# label bisa lebih dari satu karena tiap instansi beda-beda penulisannya
LABEL = {
    "KTP": {"nik": ["NIK"], "nama": ["Nama"], "ttl": ["Tempat/Tgl Lahir"], "jenis_kelamin": ["Jenis Kelamin"],
            "alamat": ["Alamat"], "rtrw": ["RT/RW"], "kel": ["Kel/Desa"], "kec": ["Kecamatan"]},
    "IJAZAH": {"nomor_ijazah": ["Nomor Ijazah", "No. Ijazah"], "nama": ["Nama"], "jenjang": ["Jenjang"],
               "program_studi": ["Program Studi"], "institusi": ["Perguruan Tinggi"],
               "tanggal_lulus": ["Tanggal Lulus"]},
    "SKCK": {"nomor_skck": ["Nomor"], "nama": ["Nama"], "berlaku_hingga": ["Sampai dengan", "Berlaku Hingga"]},
    "MCU": {"nomor_surat": ["Nomor"], "nama": ["Nama"], "tanggal_periksa": ["Tanggal Pemeriksaan"],
            "kesimpulan": ["Kesimpulan"]},
}


def cari_baris(baris_list, label):
    """Cari baris yang labelnya paling mirip. label boleh string atau list alternatif.
    Return (baris, nilai_setelah_titik_dua)"""
    if isinstance(label, list):
        hasil_terbaik = (None, None, 0)
        for lbl in label:
            b, v, skor = _cari_satu_label(baris_list, lbl)
            if skor > hasil_terbaik[2]:
                hasil_terbaik = (b, v, skor)
        return hasil_terbaik[0], hasil_terbaik[1]
    b, v, _ = _cari_satu_label(baris_list, label)
    return b, v


def _cari_satu_label(baris_list, label):
    terbaik, skor_terbaik, nilai_terbaik = None, 0, None
    jumlah_kata = len(label.split())
    for b in baris_list:
        teks = b["teks"]
        if ":" in teks:
            bagian_label, nilai = teks.split(":", 1)
        else:
            kata = teks.split()
            bagian_label, nilai = " ".join(kata[:jumlah_kata]), " ".join(kata[jumlah_kata:])
        skor = fuzz.ratio(bagian_label.strip().upper(), label.upper())
        if skor > skor_terbaik:
            terbaik, skor_terbaik, nilai_terbaik = b, skor, nilai.strip(" :;>=.-|")
    if skor_terbaik < 80:
        return None, None, 0
    return terbaik, nilai_terbaik, skor_terbaik


def koreksi(nilai, peta):
    baru = nilai.translate(peta)
    return baru, baru != nilai


def ke_tanggal_iso(teks):
    teks, berubah = koreksi(teks, PETA_ANGKA)
    m = re.search(r"(\d{2})[-/ .](\d{2})[-/ .](\d{4})", teks)
    if not m:
        return None, berubah
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}", berubah


def ekstraksi_regex(baris_list, jenis):
    label = LABEL[jenis]
    hasil = {}

    def isi(field, nilai, sumber, dikoreksi=False):
        hasil[field] = {"nilai": nilai, "baris_sumber": sumber, "dikoreksi": dikoreksi}

    if jenis == "KTP":
        b, v = cari_baris(baris_list, label["nik"])
        if b:
            nik, berubah = koreksi(v.replace(" ", ""), PETA_ANGKA)
            isi("nik", re.sub(r"\D", "", nik), [b["id"]], berubah)
        b, v = cari_baris(baris_list, label["ttl"])
        if b and "," in v:
            tempat, tgl = v.split(",", 1)
            isi("tempat_lahir", tempat.strip().upper(), [b["id"]])
            tgl_iso, berubah = ke_tanggal_iso(tgl)
            isi("tanggal_lahir", tgl_iso, [b["id"]] if tgl_iso else [], berubah)
        # alamat digabung dari beberapa baris
        bagian, sumber = [], []
        for kunci in ["alamat", "rtrw", "kel", "kec"]:
            b, v = cari_baris(baris_list, label[kunci])
            if b:
                if kunci == "rtrw" and "/" in v:
                    rt, rw = v.split("/", 1)
                    v = f"RT {rt.strip()}/RW {rw.strip()}"
                bagian.append(v.upper())
                sumber.append(b["id"])
        if bagian:
            isi("alamat", ", ".join(bagian), sumber)
        b, v = cari_baris(baris_list, label["nama"])
        if b:
            v2, berubah = koreksi(v.upper(), PETA_HURUF)
            isi("nama", v2, [b["id"]], berubah)
        # di KTP asli "Gol. Darah" ada di baris yang sama dengan jenis kelamin,
        # jadi ambil kata LAKI-LAKI / PEREMPUAN-nya saja
        b, v = cari_baris(baris_list, label["jenis_kelamin"])
        if b:
            v_up = v.upper()
            if "PEREMPUAN" in v_up or fuzz.partial_ratio("PEREMPUAN", v_up) >= 85:
                isi("jenis_kelamin", "PEREMPUAN", [b["id"]], "PEREMPUAN" not in v_up)
            elif "LAKI" in v_up:
                isi("jenis_kelamin", "LAKI-LAKI", [b["id"]])
    else:
        for field, lbl in label.items():
            b, v = cari_baris(baris_list, lbl)
            if not b:
                continue
            if field.startswith("tanggal") or field == "berlaku_hingga":
                tgl_iso, berubah = ke_tanggal_iso(v)
                isi(field, tgl_iso, [b["id"]] if tgl_iso else [], berubah)
            elif field == "jenjang":
                # jenjang formatnya huruf + angka (S1, D3, D4) jadi koreksinya beda
                bersih = re.sub(r"[^A-Za-z0-9]", "", v.replace("$", "S")).upper()
                m = re.search(r"([SD])([1-4IL])", bersih)
                if m:
                    baru = m.group(1) + m.group(2).translate(PETA_ANGKA)
                    isi(field, baru, [b["id"]], baru != bersih)
                else:
                    isi(field, bersih or None, [b["id"]] if bersih else [], False)
            elif field.startswith("nomor"):
                isi(field, v.replace(" ", ""), [b["id"]])
            else:
                v2, berubah = koreksi(v.upper(), PETA_HURUF)
                isi(field, v2, [b["id"]], berubah)

    if jenis == "IJAZAH" and "nama" not in hasil:
        # di ijazah nama biasanya ditulis di tengah tanpa label "Nama :",
        # jadi diambil dari baris setelah kalimat "Dengan ini menyatakan bahwa"
        for i, b in enumerate(baris_list[:-1]):
            # (cek panjang teks dulu, soalnya partial_ratio teks pendek seperti "y" bisa dapat skor 100)
            if len(b["teks"]) >= 12 and fuzz.partial_ratio("MENYATAKAN BAHWA", b["teks"].upper()) >= 85:
                b_nama = baris_list[i + 1]
                v2, berubah = koreksi(b_nama["teks"].upper().strip(" :"), PETA_HURUF)
                isi("nama", v2, [b_nama["id"]], berubah)
                break

    return SKEMA[jenis].model_validate(hasil)


# ---------------------------------------------------------------- confidence

def hitung_confidence(data, baris_list, cfg):
    """confidence = confidence OCR terkecil dari baris sumber, dikali 0.9 kalau dikoreksi.
    Yang dipakai confidence bagian nilai saja (setelah ":"), bukan labelnya."""
    conf_per_id = {b["id"]: b.get("confidence_nilai", b["confidence"]) for b in baris_list}
    faktor = cfg["ambang"]["faktor_koreksi"]
    for nama_field in data.model_fields:
        f = getattr(data, nama_field)
        sumber = [s for s in f.baris_sumber if s in conf_per_id]
        if f.nilai is None or not sumber:
            f.confidence = 0.0
            continue
        c = min(conf_per_id[s] for s in sumber)
        if f.dikoreksi:
            c = c * faktor
        f.confidence = round(c, 3)
    return data


def ekstrak(baris_list, jenis, cfg, pakai_llm):
    data = None
    if pakai_llm:
        try:
            data = panggil_llm(baris_list, jenis, cfg)
        except requests.exceptions.RequestException as e:
            print(f"    [!] gagal memanggil Ollama: {str(e)[:80]}")
    metode = "llm"
    if data is None:
        data = ekstraksi_regex(baris_list, jenis)
        metode = "regex"
    data = hitung_confidence(data, baris_list, cfg)
    return data, metode
