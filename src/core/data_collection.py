import logging

import matplotlib.pyplot as plt
import pandas as pd

from src.config import FASE, OUTPUTS_DIR
from src.config import PHASE_COLORS as FC
from src.core.preprocessor import detect_col, detect_year

logger = logging.getLogger(__name__)


class DataCollectionMixin:
    def business_understanding(self):
        logger.info(
            "BUSINESS UNDERSTANDING: Pemetaan kebutuhan rekrutmen ITSNU Pekalongan multi periode"
        )

    def data_collection(self):
        logger.info("DATA COLLECTION: Dataset sekunder calon mahasiswa ITSNU Pekalongan 2019–2024")
        all_rows = []
        self._report_progress("Opening Excel file...", 5)
        xl = pd.ExcelFile(self.file_path)
        self.hs = [
            "No",
            "Nama",
            "Tahun",
            "Asal Sekolah",
            "Program Studi",
            "Kecamatan",
            "Kabupaten",
            "Alamat",
            "Jenis Jalur",
        ]
        sheets = xl.sheet_names
        for si, sn in enumerate(sheets):
            self._report_progress(f"Reading sheet {sn} ({si+1}/{len(sheets)})", 10 + int(si / len(sheets) * 50))
            df = xl.parse(sn, header=None)
            if df.empty:
                continue
            data_rows = df.to_dict("records")
            for r in data_rows:
                row_dict = {self.hs[i]: r.get(i, "") for i in range(len(self.hs))}
                all_rows.append(row_dict)
        if not all_rows:
            raise ValueError("Data kosong")
        self._report_progress("Enriching rows with year detection...", 65)
        logger.info(f"Headers: {self.hs}")
        logger.info(f"First data row: {all_rows[0]}")
        enriched = [dict(r, _y=detect_year(r)) for r in all_rows if detect_year(r)]
        self.raw = enriched
        self.by_year = {}
        for r in enriched:
            y = r["_y"]
            if y not in self.by_year:
                self.by_year[y] = []
            self.by_year[y].append(r)
        self.cols = {
            "nama": detect_col(self.hs, ["nama", "name"]),
            "prodi": detect_col(self.hs, ["program studi", "program.studi", "program studi", "jurusan"]),
            "jalur": detect_col(self.hs, ["jenis jalur", "jenis.jalur", "jenis jalur", "jalur"]),
            "kab": detect_col(self.hs, ["kabupaten/kota", "kabupaten", "kab", "kota"]),
            "kec": detect_col(self.hs, ["kecamatan", "kec"]),
            "sekolah": detect_col(self.hs, ["asal sekolah", "sekolah", "asal_sekolah", "nama sekolah"]),
            "alamat": detect_col(self.hs, ["alamat", "alamat lengkap", "address"]),
        }
        if not self.cols["prodi"] or not self.cols["jalur"] or not self.cols["kab"]:
            raise ValueError("Kolom wajib tidak ditemukan")
        self.process_cols = [v for v in self.cols.values() if v and v != "No"]
        logger.info(f"Loaded {len(enriched)} rows from {len(xl.sheet_names)} sheets")
        self._report_progress("Data collection completed", 100)

    def data_understanding(self):
        logger.info("DATA UNDERSTANDING: Profil statistik deskriptif per periode")
        missing = {
            col: sum(1 for r in self.raw if not r.get(col))
            for col in self.cols.values()
            if col
        }
        logger.info(f"Missing values: {missing}")
        years = sorted(self.by_year.keys())
        dist = {y: len(self.by_year[y]) for y in years}
        plt.figure(figsize=(10, 6))
        plt.bar(dist.keys(), dist.values(), color=[FC[FASE[y]] for y in years])
        plt.title("Distribusi Pendaftar 2019–2024")
        plt.xlabel("Tahun")
        plt.ylabel("Jumlah")
        plt.savefig(str(OUTPUTS_DIR / "distribusi_pendaftar.png"))
        plt.close()
