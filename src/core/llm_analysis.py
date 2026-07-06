import concurrent.futures
import logging
import threading

from src.config import FASE
from src.core.preprocessor import flush_llm_cache, post_process_persona

logger = logging.getLogger(__name__)


class LlmAnalysisMixin:
    def generate_personas_only(self, provider=None):
        local_provider = "Ollama"
        local_model = "llama3.2:3b"
        logger.info(f"GENERATE_PERSONAS_ONLY: forced local provider={local_provider}")

        if not self.by_year:
            raise RuntimeError("Pipeline belum selesai Data Collection. 'by_year' kosong.")
        if not self.gmm_res:
            raise RuntimeError("Pipeline belum selesai Modeling. 'gmm_res' kosong.")

        tasks = []
        for y in list(self.by_year.keys()):
            for cl in self.gmm_res[y]["clusters"][:3]:
                tasks.append((y, cl))
        personas = {}
        total_tasks = len(tasks)
        completed = 0
        completed_lock = threading.Lock()

        def generate_persona(task):
            nonlocal completed
            y, cl = task
            top_prodi = cl["topProdi"][0][0] if cl["topProdi"] else "Tidak spesifik"
            top_jalur = cl["topJalur"][0][0] if cl["topJalur"] else "Tidak spesifik"
            top_kab = cl["topKab"][0][0] if cl["topKab"] else "Tidak spesifik"
            prompt = (
                f"Buat deskripsi persona mahasiswa ITSNU Pekalongan. "
                f"Asal: {top_kab}. Program Studi: {top_prodi}. Jalur: {top_jalur}. "
                f"Sertakan: latar belakang keluarga, motivasi kuliah, aktivitas kampus, prospek karir. "
                f"Bahasa Indonesia. Singkat dan padat, maksimal 75 kata."
            )
            try:
                response = self.generate_llm_response(prompt, local_provider, None, 400, model=local_model)
                persona = post_process_persona(response)
                if not persona or persona.startswith("["):
                    raise ValueError("Empty response")
            except Exception as e:
                logger.warning(f"Persona lokal gagal ({e}), menggunakan fallback...")
                persona = (
                    f"Mahasiswa ITSNU Pekalongan dari {top_kab}, memilih prodi {top_prodi} "
                    f"melalui jalur {top_jalur}. Berasal dari keluarga menengah di wilayah "
                    f"pesisir Jawa Tengah."
                )
            with completed_lock:
                completed += 1
                self._report_progress(
                    f"Persona {completed}/{total_tasks} (Llama 3.2 lokal)",
                    int(completed / total_tasks * 100),
                )
            return (y, cl["ci"] + 1, persona)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            futures = {executor.submit(generate_persona, task): task for task in tasks}
            for future in concurrent.futures.as_completed(futures):
                try:
                    y, ci, persona = future.result()
                    if y not in personas:
                        personas[y] = []
                    personas[y].append({"cluster": ci, "persona": persona})
                except Exception as e:
                    logger.warning(f"Failed to generate persona: {e}")
        flush_llm_cache()
        return personas

    def otomasi_llm(self):
        logger.info("OTOMASI ANALISIS LLM")
        self._report_progress("Generating personas...", 5)
        self.personas = self.generate_personas_only(self.llm_provider)
        self._report_progress("Causal trend analysis...", 60)
        self.causal_trend_analysis()
        self._report_progress("Narrative summary...", 85)
        self.narrative_summary()
        self._report_progress("LLM analysis completed", 100)

    def causal_trend_analysis(self):
        logger.info("ANALISIS TREN KAUSAL")
        self.causal_explanations = []
        years = sorted(self.by_year.keys())
        total_pairs = len(years) - 1
        for i in range(1, len(years)):
            self._report_progress(f"Reasoning {years[i-1]}→{years[i]}", 40 + (i / total_pairs) * 50)
            y1, y2 = years[i - 1], years[i]
            ari = next(
                (p["ari"] for p in self.ari_pairs if p["y1"] == y1 and p["y2"] == y2), 0
            )
            if self.hybrid and self.hybrid.cloud_available:
                logger.info(f"[Pipeline] 🌐 Causal analysis {y1}→{y2} via OpenRouter")
                clusters_y2 = self.gmm_res.get(y2, {}).get("clusters", [])
                clusters_y1 = self.gmm_res.get(y1, {}).get("clusters", [])
                centroid_d = next(
                    (p.get("drift") for p in self.centroid_drifts if p.get("y1") == y1 and p.get("y2") == y2), None
                )
                jaccard_val = next(
                    (p.get("jaccard") for p in self.jaccard_pairs if p.get("y1") == y1 and p.get("y2") == y2), None
                )
                try:
                    explanation = self.hybrid.causal_trend_analysis(
                        year_from=y1, year_to=y2,
                        fase_from=FASE.get(y1, str(y1)), fase_to=FASE.get(y2, str(y2)),
                        ari=ari, cluster_profiles_from=clusters_y1,
                        cluster_profiles_to=clusters_y2,
                        centroid_drift=centroid_d, jaccard=jaccard_val,
                    )
                    self.causal_explanations.append({"transisi": f"{y1}→{y2}", "penjelasan": explanation})
                    continue
                except Exception as e:
                    logger.warning(f"[Pipeline] Cloud causal gagal: {e}. Fallback lokal...")

            prompt = (
                f"Berikan analisis mendalam tentang perubahan kausal cluster mahasiswa dari tahun "
                f"{y1} ke {y2} dengan ARI {ari}, mempertimbangkan fase {FASE[y1]} ke {FASE[y2]}. "
                f"Jelaskan faktor-faktor yang mempengaruhi seperti kondisi ekonomi, kebijakan pendidikan, "
                f"dan dampak terhadap pola rekrutmen mahasiswa di ITSNU Pekalongan. "
                f"Sertakan rekomendasi strategis untuk penyesuaian program penerimaan."
            )
            try:
                explanation = self.generate_llm_response(prompt, self.llm_provider, None, 1500, model=self.llm_model)
            except Exception as e:
                logger.warning(f"LLM failed: {e}")
                explanation = (
                    f"Transisi dari fase {FASE[y1]} ({y1}) ke fase {FASE[y2]} ({y2}) "
                    f"menunjukkan perubahan signifikan dalam pola pendaftaran mahasiswa ITSNU "
                    f"Pekalongan, dengan ARI sebesar {ari}."
                )
            self.causal_explanations.append({"transisi": f"{y1}→{y2}", "penjelasan": explanation})

    def narrative_summary(self):
        logger.info("RINGKASAN NARATIF: Generate laporan otomatis")
        self._report_progress("Generating narrative summary...", 10)
        if self.hybrid and self.hybrid.cloud_available:
            logger.info("[Pipeline] 🌐 Narrative summary via OpenRouter")
            ari_summary = [
                {"transisi": p.get("transisi", ""), "ari": round(p.get("ari", 0), 4)}
                for p in self.ari_pairs[:5]
            ] if self.ari_pairs else []
            try:
                self._report_progress("Calling cloud LLM...", 50)
                self.narrative = self.hybrid.narrative_summary(
                    total_mahasiswa=len(self.raw),
                    proyeksi_2025=self.proj_2025,
                    avg_similarity=self.avg_sim,
                    ari_summary=ari_summary,
                )
                self._report_progress("Summary generated (cloud)", 90)
                return
            except Exception as e:
                logger.warning(f"[Pipeline] Cloud narrative gagal: {e}. Fallback lokal...")

        prompt = (
            f"Buat ringkasan naratif lengkap tentang PMB ITSNU Pekalongan 2019-2024 "
            f"dengan total {len(self.raw)} siswa, proyeksi {self.proj_2025} untuk 2025, "
            f"rata-rata kesamaan embedding {self.avg_sim}."
        )
        try:
            self._report_progress("Calling LLM...", 50)
            self.narrative = self.generate_llm_response(prompt, self.llm_provider, None, 2000, model=self.llm_model)
            self._report_progress("Summary generated", 90)
        except Exception:
            self.narrative = (
                f"Analisis komprehensif PMB ITSNU Pekalongan 2019-2024 mengungkap tren "
                f"longitudinal dengan total {len(self.raw)} pendaftar."
            )
        self._report_progress("Narrative summary completed", 100)
