# Skema data pakai Pydantic, supaya output LLM bisa dicek formatnya

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class NilaiField(BaseModel):
    nilai: Optional[str] = None
    baris_sumber: List[str] = []
    dikoreksi: bool = False
    confidence: float = 0.0  # ini diisi sistem, bukan dari LLM

    @field_validator("nilai", mode="before")
    @classmethod
    def ubah_ke_string(cls, v):
        # kadang LLM ngasih angka (misal tahun), jadi diubah ke string
        if v is None:
            return None
        v = str(v).strip()
        return v if v != "" else None


def _f():
    return Field(default_factory=NilaiField)


class DataKTP(BaseModel):
    nik: NilaiField = _f()
    nama: NilaiField = _f()
    tempat_lahir: NilaiField = _f()
    tanggal_lahir: NilaiField = _f()
    jenis_kelamin: NilaiField = _f()
    alamat: NilaiField = _f()


class DataIjazah(BaseModel):
    nama: NilaiField = _f()
    nomor_ijazah: NilaiField = _f()
    jenjang: NilaiField = _f()
    program_studi: NilaiField = _f()
    institusi: NilaiField = _f()
    tanggal_lulus: NilaiField = _f()


class DataSKCK(BaseModel):
    nama: NilaiField = _f()
    nomor_skck: NilaiField = _f()
    berlaku_hingga: NilaiField = _f()


class DataMCU(BaseModel):
    nama: NilaiField = _f()
    nomor_surat: NilaiField = _f()
    tanggal_periksa: NilaiField = _f()
    kesimpulan: NilaiField = _f()


SKEMA = {"KTP": DataKTP, "IJAZAH": DataIjazah, "SKCK": DataSKCK, "MCU": DataMCU}

# field yang wajib yakin (dipakai aturan R8)
FIELD_WAJIB = {
    "KTP": ["nik", "nama", "tanggal_lahir", "jenis_kelamin"],
    "IJAZAH": ["nama", "jenjang", "program_studi"],
    "SKCK": ["nama", "berlaku_hingga"],
    "MCU": ["nama", "kesimpulan"],
}
