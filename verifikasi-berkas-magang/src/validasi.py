# Rule engine: cek aturan R1 - R9 lalu tentukan status berkas.
# R1 (kelengkapan file) dicek duluan di main.py sebelum OCR.

from datetime import date
from rapidfuzz import fuzz

from src.skema import FIELD_WAJIB
from src.ocr import engine_yang_dipakai

NIK_TERDAFTAR = set()  # anggap saja ini database pendaftar periode ini


def _tgl(s):
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def _nilai(rekap, jenis, field):
    return rekap.get(jenis, {}).get(field, {}).get("nilai")


def _conf(rekap, jenis, field):
    return rekap.get(jenis, {}).get(field, {}).get("confidence", 0.0)


def cek_nik(rekap):
    """R4: NIK 16 digit + tanggal lahir & jenis kelamin di dalam NIK harus cocok"""
    nik = _nilai(rekap, "KTP", "nik") or ""
    tgl = _tgl(_nilai(rekap, "KTP", "tanggal_lahir") or "")
    jk = (_nilai(rekap, "KTP", "jenis_kelamin") or "").upper()
    if len(nik) != 16 or not nik.isdigit():
        return False, f"NIK tidak 16 digit ({nik})"
    if tgl is None:
        return False, "tanggal lahir tidak terbaca, NIK tidak bisa dicek silang"
    dd, mm, yy = int(nik[6:8]), int(nik[8:10]), int(nik[10:12])
    perempuan = dd > 40
    if perempuan:
        dd -= 40
    if (dd, mm, yy) != (tgl.day, tgl.month, tgl.year % 100):
        return False, "tanggal lahir di NIK tidak sama dengan tanggal lahir di KTP"
    if perempuan != ("PEREMPUAN" in jk):
        return False, "jenis kelamin tidak sesuai dengan kode NIK"
    return True, ""


def _bersihkan_nama(nama):
    # buang gelar, contoh "BUDI SANTOSO, S.KOM." -> "BUDI SANTOSO"
    return (nama or "").split(",")[0].strip().upper()


def cek_nama(rekap, cfg):
    """R5: nama di semua dokumen harus mirip dengan KTP"""
    nama_ktp = _bersihkan_nama(_nilai(rekap, "KTP", "nama"))
    masalah = []
    for jenis in ["IJAZAH", "SKCK", "MCU"]:
        nama_lain = _bersihkan_nama(_nilai(rekap, jenis, "nama"))
        if not nama_lain:
            continue
        skor = fuzz.ratio(nama_ktp, nama_lain)
        if skor < cfg["ambang"]["kemiripan_nama"]:
            masalah.append(f"nama di {jenis} ({nama_lain}) beda dengan KTP ({nama_ktp}), kemiripan {skor:.0f}%")
    return len(masalah) == 0, masalah


def ambang_aktif(cfg):
    """Ambang confidence sesuai OCR engine yang sedang dipakai"""
    a = {"confidence_yakin": cfg["ambang"]["confidence_yakin"],
         "confidence_minimal": cfg["ambang"]["confidence_minimal"]}
    a.update(cfg["ambang"].get("per_engine", {}).get(engine_yang_dipakai(), {}))
    return a


def format_valid(rekap, jenis, field, cfg):
    """Validasi format sederhana, dipakai sebagai 'cek silang' untuk field yang tidak ada pasangannya"""
    nilai = (_nilai(rekap, jenis, field) or "").upper()
    if field.startswith("tanggal") or field == "berlaku_hingga":
        return _tgl(nilai) is not None
    if field == "jenjang":
        return nilai in ["D3", "D4", "S1", "S2"]
    if field == "kesimpulan":
        return nilai in ["LAYAK", "TIDAK LAYAK", "LAYAK DENGAN CATATAN"]
    if field == "program_studi":
        return nilai in cfg["program"]["prodi_diizinkan"]
    return False


def cek_keyakinan_dan_konsistensi(rekap, cfg):
    """Tahap 2: R4, R5, R8, R9. Return daftar masalah (kalau ada -> PERLU_REVIEW)"""
    masalah = []
    nik_ok, pesan_nik = cek_nik(rekap)
    if not nik_ok:
        masalah.append("R4: " + pesan_nik)
    nama_ok, pesan_nama = cek_nama(rekap, cfg)
    for p in pesan_nama:
        masalah.append("R5: " + p)

    # R8: field wajib harus cukup yakin. Kalau di rentang tengah, boleh lolos asal cek silangnya OK
    ambang = ambang_aktif(cfg)
    yakin, minimal = ambang["confidence_yakin"], ambang["confidence_minimal"]
    lolos_cek_silang = {("KTP", "nik"): nik_ok, ("KTP", "tanggal_lahir"): nik_ok,
                        ("KTP", "jenis_kelamin"): nik_ok}
    for jenis in ["KTP", "IJAZAH", "SKCK", "MCU"]:
        lolos_cek_silang[(jenis, "nama")] = nama_ok  # nama dicek silang antar dokumen (R5)
    for jenis, daftar_field in FIELD_WAJIB.items():
        for field in daftar_field:
            c = _conf(rekap, jenis, field)
            if c >= yakin:
                continue
            if c >= minimal and (lolos_cek_silang.get((jenis, field), False) or format_valid(rekap, jenis, field, cfg)):
                continue
            if c < minimal:
                masalah.append(f"R8: {jenis}.{field} tidak terbaca (confidence {c:.2f})")
            else:
                masalah.append(f"R8: {jenis}.{field} kurang yakin (confidence {c:.2f})")

    # R9: daftar ganda
    nik = _nilai(rekap, "KTP", "nik")
    if nik and nik in NIK_TERDAFTAR:
        masalah.append("R9: NIK sudah pernah mendaftar di periode ini")
    return masalah


def cek_syarat_program(rekap, cfg):
    """Tahap 3: R2, R3, R6, R7. Return (gagal_tidak_lolos, perlu_review)"""
    prog = cfg["program"]
    tgl_daftar = _tgl(prog["tanggal_pendaftaran"])
    gagal, review = [], []

    # R2 usia
    lahir = _tgl(_nilai(rekap, "KTP", "tanggal_lahir") or "")
    if lahir:
        usia = tgl_daftar.year - lahir.year - ((tgl_daftar.month, tgl_daftar.day) < (lahir.month, lahir.day))
        if not (prog["usia_min"] <= usia <= prog["usia_max"]):
            gagal.append(f"R2: usia {usia} tahun, syarat {prog['usia_min']}-{prog['usia_max']} tahun")

    # R3 pendidikan
    jenjang = (_nilai(rekap, "IJAZAH", "jenjang") or "").upper()
    prodi = (_nilai(rekap, "IJAZAH", "program_studi") or "").upper()
    if jenjang not in prog["jenjang_diizinkan"]:
        gagal.append(f"R3: jenjang {jenjang} tidak termasuk {prog['jenjang_diizinkan']}")
    if prodi not in prog["prodi_diizinkan"]:
        skor_max = max(fuzz.ratio(prodi, p) for p in prog["prodi_diizinkan"])
        if skor_max >= cfg["ambang"]["kemiripan_prodi_review"]:
            review.append(f"R3: program studi {prodi} mirip dengan daftar tapi tidak persis ({skor_max:.0f}%)")
        else:
            gagal.append(f"R3: program studi {prodi} tidak sesuai syarat")

    # R6 SKCK
    berlaku = _tgl(_nilai(rekap, "SKCK", "berlaku_hingga") or "")
    if berlaku and berlaku < tgl_daftar:
        gagal.append(f"R6: SKCK sudah tidak berlaku sejak {berlaku}")

    # R7 MCU -> kalau tidak layak tetap ke admin
    kesimpulan = (_nilai(rekap, "MCU", "kesimpulan") or "").upper()
    if kesimpulan != "LAYAK":
        review.append(f"R7: kesimpulan MCU '{kesimpulan}'")
    return gagal, review


def tentukan_status(rekap, cfg, catatan_awal=None):
    catatan_awal = catatan_awal or []
    masalah = catatan_awal + cek_keyakinan_dan_konsistensi(rekap, cfg)
    if masalah:
        status, alasan = "PERLU_REVIEW", masalah
    else:
        gagal, review = cek_syarat_program(rekap, cfg)
        if review:
            status, alasan = "PERLU_REVIEW", review + gagal
        elif gagal:
            status, alasan = "TIDAK_LOLOS", gagal
        else:
            status, alasan = "LOLOS", ["semua aturan R1-R9 terpenuhi"]

    # catat NIK supaya pendaftaran ganda ketahuan (R9)
    nik = _nilai(rekap, "KTP", "nik")
    if nik:
        NIK_TERDAFTAR.add(nik)
    return status, alasan
