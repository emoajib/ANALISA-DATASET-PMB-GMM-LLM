# @pro — Architecture & Strategic Integrity Audit Report

**Document:** FULL TESIS FINAL.docx
**Reviewer:** @pro (Architecture & Strategic Integrity)
**Date:** 11 July 2026

---

## 1. Pipeline Logic Flow (BAB III → BAB IV → BAB V)

| BAB III Module | BAB IV Section | Status |
|---|---|---|
| 3.1–3.2 Desain & Diagram Alur | (Metodologi, tidak perlu hasil terpisah) | 🟢 |
| 3.3 Business Understanding | 4.1 Deskripsi Data Time Series | 🟢 |
| 3.4 Data Collection | 4.1.1 Gambaran Umum Dataset | 🟢 |
| 3.5 Data Understanding | 4.1.1 + 4.1.2 Distribusi Prodi | 🟢 |
| 3.6 Data Preparation | 4.2 Hasil Otomasi Data Preparation | 🟢 |
| 3.7 PCA Reduction | 4.2.3 Hasil PCA Dimensionality Reduction | 🟢 |
| 3.8 GMM Modeling | 4.3 Segmentasi Probabilistik GMM | 🟢 |
| 3.9 Time Series Analysis | 4.4 Time Series & Structural Break | 🟢 |
| 3.10 Evaluasi Multi Level | 4.5 Evaluasi Multi Level | 🟢 |
| 3.11 Otomasi Analisis LLM | 4.6.5 + 4.7 Otomasi LLM Hybrid | 🟢 |
| 3.12 Deployment | 4.8 Strategi Rekrutmen Prediktif | 🟢 |
| 3.14 Validasi Expert | 4.9 Hasil Validasi Pakar | 🟢 |

- **Status:** 🟢 **All modules from BAB III are represented in BAB IV.**
- **Finding:** Tidak ada modul yang disebut di metode tapi hilang di hasil. Tidak ada hasil yang tidak didukung metode.
- **Catatan:** Modul 3.11 (Otomasi LLM) di metode mencakup 4 fungsi: (a) ekstraksi fitur → 4.2.2, (b) generasi persona → 4.6.5, (c) reasoning kausal → 4.7.1, (d) ringkasan naratif → 4.7.2. Semua tercakup.
- **Recommendation:** 🟢 Tidak perlu perubahan.

---

## 2. Hypothesis → Evidence Chain

### H1: ARI < 0.30 pada transisi 2019→2020 sebagai structural break

- **Evidence Location:** 4.4 (Tabel 4.6) + 4.10.1
- **Tabel 4.6 Values:** All 5 transitions ARI < 0.30. Range: −0.0102 to −0.0037.
- **4.10.1 Narrative:** Explicitly states "H1 dikonfirmasi melampaui ekspektasi — seluruh 5 transisi."
- **Status:** 🟢 **Confirmed, evidence strong.**
- **Finding:** H1 actually exceeded expectations (original hypothesis only expected 2019→2020 break, but all 5 transitions show breaks). This is properly discussed.
- **Recommendation:** 🟢 No change needed.

### H2: Cosine similarity > 0.70

- **Evidence Location:** 4.2.2 (Tabel 4.4) + 4.10.1
- **Tabel 4.4 Values:** All > 0.70 threshold individually.
- **Status:** 🟡 **Confirmed qualitatively, but numerical discrepancy in stated average.**
- **Finding (CRITICAL):** Tabel 4.4 states "Rata-rata keseluruhan 0.9990" but the individual transition values shown are: 0.9973, 0.8024, 1.0000, 0.8009, 0.8095. The arithmetic mean of these 5 values is **0.8820**, NOT 0.9990. This is a mathematical impossibility unless the average is computed via a non-standard method or the individual values are misreported.
- **Recommendation:** 🔴 **Verify the cosine similarity calculation.** Either the individual values in Tabel 4.4 are incorrect, or the stated average of 0.9990 is incorrect (possibly confused with the pairwise embedding similarity computation method). This must be resolved before final submission.

### H3: GMM > K-Means untuk soft clustering

- **Evidence Location:** 4.5.2 (Tabel 4.8) + 4.10.1
- **Status:** 🟡 **Confirmed qualitatively, but with methodological nuance.**
- **Finding:**
  1. **Tabel 4.8 heading inconsistency** — Daftar Tabel lists "(Data 2024, K=3)" but actual table heading says "(Data 2024, K=2)". The table data clearly uses K=2. **Fix the Daftar Tabel entry.**
  2. **Posterior probability range (0.514–1.000)** — The presence of posterior = 1.0 (especially in 2019) means some cluster assignments are effectively deterministic. This partially undermines the "soft clustering" argument. The thesis acknowledges this implicitly but should explicitly state that some years show near-deterministic assignments while others show probabilistic overlap.
  3. GMM's key advantage is correctly identified: (a) posterior probability enables LLM reasoning, (b) supports forecasting, (c) detects unexpected segments (D3 Akuntansi).
- **Recommendation:** 🟡 Fix K=3→K=2 in Daftar Tabel. Add explicit discussion of posterior = 1.0 cases.

---

## 3. Abstrak → Kesimpulan Alignment

| Claim in Abstract | Supported in Kesimpulan (5.1)? | Match? |
|---|---|---|
| 2.362 pendaftar | "Dari dataset 2.362 pendaftar" (L1643) | 🟢 Yes |
| K=2 konsisten | "K=2 secara konsisten untuk seluruh 6 periode" (L1643) | 🟢 Yes |
| Posterior probability 0.514–1.000 | "posterior probability berkisar 0,514--1,000" (L1643) | 🟢 Yes |
| 5 transisi structural break (ARI < 0.30) | "Seluruh 5 transisi... structural break dengan ARI < 0,30" (L1646) | 🟢 Yes |
| ARI range −0.0102 to −0.0037 | "kisaran −0,0102 hingga −0,0037" (L1646) | 🟢 Yes |
| Cosine similarity 0.999 | Not explicitly in 5.1 (but in 4.10.1) | 🟡 Indirect |
| 98%+ segmen mayoritas homogen | "mayoritas homogen (98%+)" (L1643) | 🟢 Yes |
| Hybrid Cognitive Pipeline | "Hybrid Cognitive Pipeline" mentioned (L1640, 1649) | 🟢 Yes |
| Rekomendasi rekrutmen 2025 | "peta prioritas segmen dan rekomendasi" (L1649) | 🟢 Yes |

- **Status:** 🟢 **Abstract and Kesimpulan are well-aligned.** All major claims in the abstract are supported in the conclusion section. No contradictory numbers found.
- **Finding:** Cosine similarity value of 0.999 is stated in Abstract but not explicitly repeated in Kesimpulan 5.1. This is acceptable since it appears in 4.10.1 (H2 confirmation).
- **Recommendation:** 🟢 Minor: consider adding cosine similarity 0.999 to 5.1 for completeness.

---

## 4. Table of Contents Integrity

- **Status:** 🟡 **One critical mismatch found.**

| Daftar Isi Entry | Actual Heading | Match? |
|---|---|---|
| Tabel 4.8 ... (Data 2024, K=3) | Tabel 4.8 ... (Data 2024, K=2) | 🔴 **MISMATCH** |
| 4.6.5 Persona Generation (sub-bab 4.6) | Heading 2 level (not Heading 3) | 🟡 Level error |

- **Finding (CRITICAL):** Daftar Tabel entry for Tabel 4.8 says K=3 but actual table is K=2. This is a clear editorial error.
- **Finding (Structural):** 4.6.5 is formatted as Heading 2 (##) while it should be Heading 3 (###) since it's a sub-sub-section of 4.6. This creates a heading level inconsistency where 4.6.1–4.6.4 are L3 but 4.6.5 is L2.
- **Recommendation:** 🔴 Fix both: (1) Daftar Tabel → K=2, (2) Demote 4.6.5 from Heading 2 to Heading 3.

---

## 5. Structural Weaknesses

### 5.1 Heading Level Jumps

```
Before fix: ... 4.6.4 (L3) → 4.6.5 (L2) → 4.7 (L2)
After fix:   ... 4.6.4 (L3) → 4.6.5 (L3) → 4.7 (L2)
```

- **Status:** 🟡 **One heading level error** (4.6.5 should be L3 not L2).
- **Recommendation:** Fix in Word document.

### 5.2 Sections with < 3 paragraphs (too short)

| Section | Paragraphs | Issue |
|---|---|---|
| 1.4 Hipotesis Penelitian | 1 | Very short — could be expanded or merged |
| 1.6 Metode Penelitian | 1 | Very short — mentions "R&D" but very brief |
| 1.7 Sistematika Penulisan | 1 | Very short — could be elaborated |
| 2.6 CRISP DM Adaptif Time Series | 1 | Surprising for a core methodology reference |
| 3.3 Business Understanding | 1 | Very brief for a pipeline stage |
| 3.5 Data Understanding | 1 | Very brief for a pipeline stage |
| 3.7 PCA Reduction | 1 | Very brief |
| 3.12 Deployment | 1 | Very brief |
| 3.15 Etika Penelitian | 1 | Very brief |
| 4.2.3 Hasil PCA | 1 | Only a short paragraph |
| 4.10.3 Kontribusi Sistem Otomasi LLM | 2 | Reasonable but borderline |

- **Status:** 🟡 **11 sub-sections have only 1 paragraph; 4 more have only 2 paragraphs.**
- **Finding:** While many 1-paragraph sections are transitional or descriptive, sections like 3.3 (Business Understanding), 3.5 (Data Understanding), and 3.7 (PCA) represent pipeline stages that deserve more elaboration, even in the methodology chapter.
- **Recommendation:** 🟡 Consider expanding the most critical short sections (3.3, 3.5, 3.7, 3.12) to at least 2 paragraphs. The others are acceptable as transitional sections.

### 5.3 Overly Long Sections (> 10 paragraphs)

| Section | Paragraphs |
|---|---|
| 4.6.3 Profil Klaster Fase Recovery (2022–2024) | 29 |
| 4.6.2 Profil Klaster Fase COVID Crisis (2020–2021) | 19 |
| 4.6.1 Profil Klaster Fase Pre COVID (2019) | 10 |

- **Status:** 🟢 **Long sections are appropriately divided with tables, figures, and sub-narratives.** The 29-paragraph section (4.6.3) is justified given it covers 3 years of data across multiple dimensions.
- **Recommendation:** 🟢 No change needed.

---

## 6. Consistency of Numbering Across the Document

### 6.1 K-Scan Range

| Parameter | BAB III | BAB IV | Daftar Tabel | Consistent? |
|---|---|---|---|---|
| K-scan range | 2 to 6 | 2 to 6 (Table 4.5 shows K=2 to 7 with early stopping) | — | 🟢 YES |
| K optimal | K=2 | K=2 for all years | K=2 | 🟢 YES |
| Mentioned in Abstract | K=2 | — | — | 🟢 YES |
| Mentioned in Kesimpulan | — | K=2 for all 6 periods | — | 🟢 YES |

- **Status:** 🟢 **K=2 fully consistent across document.**

### 6.2 ARI Values

| Location | Value/Range | Consistent? |
|---|---|---|
| Tabel 4.6 | −0.0102 to −0.0037 | Reference |
| Narasi 4.4 | −0.0102 to −0.0037 | 🟢 Yes |
| Abstract | −0.0102 to −0.0037 | 🟢 Yes |
| 4.10.1 | −0.0102 to −0.0037 | 🟢 Yes |
| 5.1 Kesimpulan | −0.0102 to −0.0037 | 🟢 Yes |

- **Status:** 🟢 **ARI values fully consistent.**
- **Note:** Tabel 4.6 shows 2023→2024 value of −0.0088 which falls within the −0.0102 to −0.0037 range. ✓

### 6.3 Cosine Similarity Values

| Location | Value | Consistent? |
|---|---|---|
| Tabel 4.4 | Individual: 0.9973, 0.8024, 1.0000, 0.8009, 0.8095 | Reference |
| Tabel 4.4 (avg) | 0.9990 | 🔴 DISCREPANCY |
| Abstract | 0.999 | 🔴 Same issue |
| 4.10.1 | 0.9990 | 🔴 Same issue |

- **Status:** 🔴 **Numerical impossibility.**
- **Finding:** See section 2 (H2) for detailed analysis. The average 0.9990 cannot be derived from the listed values (actual average = 0.8820).
- **Recommendation:** 🔴 **URGENT: Audit the cosine similarity calculation pipeline.** Check whether the CSV output matches Tabel 4.4 values. If the individual values are wrong, correct them. If the average is wrong, correct it. Do not submit with this discrepancy.

### 6.4 Tabel 4.8 K Parameter

| Location | Stated K | Consistent? |
|---|---|---|
| Daftar Tabel | K=3 | 🔴 |
| Table heading | K=2 | Reference |
| Table data | K=2 | 🟢 |

- **Status:** 🔴 **Daftar Tabel entry mismatches actual table.**

---

## 7. Daftar Pustaka Completeness

### 7.1 Entry Count

- **Total entries (lines):** 62
- **Unique author-year combinations:** 44
- **Previous session count:** 44
- **Status:** 🟡 **44 unique references is consistent with previous count.**

### 7.2 Duplicate Entries

15 author-year pairs appear twice in Daftar Pustaka:

| Author | Year | Note |
|---|---|---|
| Aristovnik | 2021 | Both entries, different DOI formats (Sustainability vs Data in Brief) |
| Cahyadi | 2022 | Different journal formats |
| Dempster | 1977 | Same reference, different formatting |
| George | 2022 | Two different papers (a and b) — acceptable but marked as duplicate |
| Grattafiori | 2024 | Same reference, arXiv + full author list |
| Hubert | 1985 | Same reference, different formatting |
| Kotler | 2016 | Three entries for essentially same book |
| Koto | 2020 | COLING proceedings + full DOI |
| Mariscal | 2010 | Abbreviated + full |
| Parker | 2025 | Two identical entries (a and b) |
| El Said | 2021 | Same paper, different citation (El Said vs Said) |
| Subakti | 2022 | Different journal formats |
| Uddin | 2024 | Two different papers (a and b) — acceptable |

- **Status:** 🟡 **Many duplicates are formatting variants of the same reference.** This inflates the apparent count from 44 to 62. The thesis properly differentiates George 2022a/2022b, Uddin 2024a/2024b, and El Said 2021a/2021b as separate works, but the formatting duplicates (e.g., Grattafiori appearing twice with same DOI) are genuine duplicates.
- **Recommendation:** 🟡 **Consolidate formatting duplicates.** Keep only one entry per reference with consistent formatting (APA 7th recommended). The 44 unique count is adequate for a master's thesis.

### 7.3 Scrucca (2024)

- **Present:** ✅ Yes (L1703)
- **Status:** 🟢 Included.

### 7.4 Uncited References

- **Status:** 🟢 **All references appear to be cited in text.** The reverse check (text citations → references) shows good coverage. However, some references like "Shoaib et al. (2025)", "Lazaros et al. (2026)", "Saarela et al. (2026)", and "Fajardo-Ramos et al. (2025)" may need verification that they are indeed cited in the body text. These are recent 2025–2026 references that were potentially auto-generated by the LLM narrative module.

---

## 8. Additional Findings

### 8.1 Jaccard Similarity Anomaly

Tabel 4.6 shows Jaccard similarity for 2023→2024 = **0.0239**, which is dramatically different from the other 4 transitions (range 0.9726–0.9927). The text does not explicitly explain this anomaly.

- **Status:** 🟡 **Potentially valid but unexplained.** A sudden drop from ~0.98 to 0.02 is either a data error or a significant structural finding that deserves explicit discussion.
- **Recommendation:** 🟡 Add a sentence explaining why Jaccard drops to 0.0239 for 2023→2024.

### 8.2 Posterior Probability Range

The abstract and conclusion state posterior probability range 0.514–1.000. The upper bound of 1.0 indicates deterministic cluster assignments for some observations, which partially undermines the H3 argument that GMM's soft clustering is inherently superior to K-Means.

- **Status:** 🟡 **Methodological nuance.**
- **Finding:** The thesis should acknowledge that posterior = 1.0 cases exist but emphasize that even partial probabilistic assignments (e.g., posterior 0.514–0.999) still provide value that K-Means cannot.
- **Recommendation:** 🟡 Add a brief note in 4.10.1 (H3 discussion) acknowledging the posterior = 1.0 cases and explaining their implications.

### 8.3 Deployment Section (3.12 vs 4.8)

- **Status:** 🟢 Both sections exist and align. BAB III describes the deployment framework; BAB IV (4.8) presents the actual strategies.

---

## 9. Overall Prioritization of Fixes

### 🔴 CRITICAL (must fix before submission)

| # | Issue | Section | Effort | Impact |
|---|---|---|---|---|
| 1 | Cosine similarity average 0.9990 ≠ arithmetic mean of displayed values | 4.2.2, Abstract, 4.10.1 | Medium | High — numerical validity |
| 2 | Daftar Tabel: Tabel 4.8 K=3 → harus K=2 | Daftar Tabel | Low | High — consistency |

### 🟡 MODERATE (should fix)

| # | Issue | Section | Effort | Impact |
|---|---|---|---|---|
| 3 | 4.6.5 heading level L2 → L3 | 4.6.5 | Low | Medium — structure |
| 4 | Daftar Pustaka formatting duplicates (consolidate ~15 entries) | Daftar Pustaka | Medium | Medium — academic rigor |
| 5 | Jaccard 2023→2024 = 0.0239 unexplained | 4.4 | Low | Medium — clarity |
| 6 | Posterior = 1.0 cases not discussed | 4.10.1 H3 | Low | Medium — nuance |
| 7 | Some 1-paragraph sections (3.3, 3.5, 3.7, 3.12) | BAB III | Medium | Low — depth |

### 🟢 MINOR (consider if time permits)

| # | Issue | Section | Effort |
|---|---|---|---|
| 8 | Cosine similarity not explicitly in 5.1 | 5.1 | Low |
| 9 | "Shoaib 2025", "Lazaros 2026" etc. — verify in-text citation | All | Low |
| 10 | Abstract mentions "Hybrid Cognitive Pipeline" but 3.11 describes architecture | Abstract/3.11 | Low |

---

## 10. Overall Assessment

| Dimension | Grade | Assessment |
|---|---|---|
| **Pipeline Logic Flow** | 🟢 **A** | All BAB III modules map cleanly to BAB IV results |
| **Hypothesis → Evidence** | 🟡 **B+** | H1 solid; H2 has numerical issue; H3 nuanced but valid |
| **Abstract ↔ Conclusion** | 🟢 **A** | Excellent alignment, no contradictory claims |
| **TOC Integrity** | 🟡 **B** | One mismatch (K=3 vs K=2), one heading level error |
| **Structural Soundness** | 🟢 **A-** | Generally good; 4.6.5 heading level is the only structural flaw |
| **Numbering Consistency** | 🟡 **B-** | Cosine average is the major issue; ARI and K values are consistent |
| **Daftar Pustaka** | 🟡 **B** | 44 unique entries is adequate; ~15 formatting duplicates need consolidation |
| **Overall** | 🟡 **B+** | **Sound architecture with 2 critical issues to resolve** |

### Final Verdict

The thesis demonstrates **strong architectural coherence**: BAB III methodology flows logically into BAB IV results, hypothesis testing follows a clear evidence chain, and the abstract-conclusion alignment is well-maintained. The CRISP-DM adaptive time series framework is consistently applied throughout.

**Two issues require immediate correction before submission:**
1. 🔴 Cosine similarity numerical discrepancy (0.9990 ≠ 0.8820)
2. 🔴 Tabel 4.8 K parameter mismatch in Daftar Tabel (K=3 → K=2)

**Three issues strongly recommended:**
3. 🟡 Fix 4.6.5 heading level
4. 🟡 Consolidate duplicate references
5. 🟡 Explain Jaccard 2023→2024 anomaly

The architectural foundation is **sound** — no fundamental redesign is needed. The fixes are editorial and numerical in nature.
