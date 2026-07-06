"""
PII Sanitizer — Privacy gatekeeper.

Memastikan TIDAK ADA data individu mahasiswa yang dikirim ke cloud.
Hanya statistik agregat + label abstrak yang diizinkan keluar.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

PII_PATTERNS = [
    r'\b\d{16}\b',
    r'\b\d{2}\.\d{2}\.\d{2}\.\d{4}\b',
    r'\b(?:08|62|\+62)\d{8,12}\b',
    r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    r'\b(?:Jl\.|Jalan|Gang|Gg\.|RT\s?\d+|RW\s?\d+)\s\w+',
    r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b',
]


class PIISanitizer:
    """Sanitasi profil klaster: hapus PII, pertahankan statistik agregat."""

    def sanitize_cluster_profile(self, cluster_data: dict[str, Any]) -> dict[str, Any]:
        sanitized = {
            "cluster_id": cluster_data.get("ci", 0) + 1,
            "label": f"Klaster_{cluster_data.get('ci', 0) + 1}",
            "n": cluster_data.get("n", 0),
            "pct": round(cluster_data.get("pct", 0.0), 2),
            "topProdi": self._abstract_text(cluster_data.get("topProdi", [])),
            "topJalur": self._abstract_text(cluster_data.get("topJalur", [])),
            "topKab": self._abstract_text(cluster_data.get("topKab", [])),
            "representative": f"Pendaftar_Representatif_Klaster_{cluster_data.get('ci', 0) + 1}",
        }
        sanitized_str = json.dumps(sanitized)
        pii_found = self._detect_pii(sanitized_str)
        if pii_found:
            logger.warning(f"[PIISanitizer] PII detected: {pii_found}. Redacting...")
            sanitized = self._force_remove_pii(sanitized, pii_found)
        return sanitized

    def sanitize_metrics_payload(
        self, year: int, ari: float, fase_from: str, fase_to: str,
        cluster_profiles: list[dict],
        centroid_drift: float | None = None, jaccard: float | None = None,
    ) -> dict[str, Any]:
        return {
            "konteks": "Analisis segmentasi mahasiswa baru ITSNU Pekalongan",
            "periode": f"{year-1}→{year}",
            "fase_transisi": f"{fase_from} → {fase_to}",
            "metrik_stabilitas": {
                "ari": round(float(ari), 4),
                "jaccard": round(float(jaccard), 4) if jaccard is not None else None,
                "centroid_drift": round(float(centroid_drift), 4) if centroid_drift is not None else None,
            },
            "klaster": [self.sanitize_cluster_profile(cl) for cl in cluster_profiles],
            "catatan": "Data telah melalui sanitasi PII. Nama dan alamat spesifik telah dianonimkan.",
        }

    def _abstract_text(self, items: list, max_items: int = 3) -> list[str]:
        return [p[0] for p in items[:max_items]] if items else ["Tidak diketahui"]

    def _detect_pii(self, text: str) -> list[str]:
        found = []
        for pattern in PII_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                found.extend(matches)
        return found

    def _force_remove_pii(self, data: dict, pii_list: list[str]) -> dict:
        data_str = json.dumps(data)
        for pii in pii_list:
            data_str = data_str.replace(pii, "[REDACTED]")
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            logger.error("[PIISanitizer] Gagal parse setelah redaksi.")
            return {"error": "PII_SANITIZATION_FAILED", "label": "DATA_REDACTED"}
