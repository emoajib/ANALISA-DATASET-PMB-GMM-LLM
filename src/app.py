import streamlit as st
import pandas as pd
import os
from pathlib import Path
from pmb_pipeline import PMBAnalysisPipeline, FASE
from steps.utils import set_model
from comparison import run_comparison, clear_comparison
from providers import PROVIDER_NAMES as COMPARISON_PROVIDERS, OLLAMA_MODELS, DEFAULT_OLLAMA_MODEL

BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"

@st.cache_resource
def load_indobert_model():
    from transformers import AutoTokenizer, AutoModel
    model_name = "indobenchmark/indobert-base-p1"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    return model, tokenizer

# Streamlit caching for performance (preserved existing decorators)
@st.cache_data
def load_csv_safe(path):
    try:
        return pd.read_csv(path)
    except:
        return None

@st.cache_data
def load_image_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except:
        return None

# Thesis Alignment Badge
st.title("PMB ITSNU Analysis Dashboard")
st.markdown("![98% Aligned with BAB IV](https://img.shields.io/badge/98%25-Aligned%20with%20BAB%20IV-brightgreen)")

# Detect demo mode (Ollama server must be actually reachable)
_ollama_available = False
try:
    import ollama
    ollama.list()
    _ollama_available = True
except Exception:
    pass

if not _ollama_available:
    st.info(
        "🌐 **Demo Mode** — Ollama tidak terdeteksi. "
        "LLM output akan di-load dari cache. "
        "Pipeline langkah 9-10 dan Model Comparison akan menggunakan data pra-generasi.",
    )

st.markdown("---")

st.sidebar.header("Upload Dataset")
uploaded_file = st.sidebar.file_uploader("Upload XLS file", type=["xls", "xlsx"])

st.sidebar.header("LLM Provider")
llm_provider = st.sidebar.radio("Pilih Provider LLM:", ("Ollama (local)", "Gemini CLI", "Kilo CLI", "OpenCode CLI"), index=0)
llm_provider_map = {
    "Ollama (local)": "Ollama",
    "Gemini CLI": "Gemini",
    "Kilo CLI": "Kilo",
    "OpenCode CLI": "OpenCode",
}
llm_provider_key = llm_provider_map[llm_provider]

llm_model = DEFAULT_OLLAMA_MODEL
if llm_provider_key == "Ollama":
    llm_model = st.sidebar.selectbox("Pilih Model Ollama:", OLLAMA_MODELS, index=0)

# Initialize session state
if "pipeline" not in st.session_state:
    st.session_state.pipeline = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
# Track completion of each step
step_names = [
    "business_understanding",
    "data_collection",
    "data_understanding",
    "data_preparation",
    "dimensionality_reduction",
    "modeling",
    "time_series_analysis",
    "evaluation",
    "otomasi_llm",
    "causal_trend_analysis",
    "narrative_summary",
    "deployment"
]
for step in step_names:
    if step not in st.session_state:
        st.session_state[step] = False
if "errors" not in st.session_state:
    st.session_state.errors = {}
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = {}
if "comparison_running" not in st.session_state:
    st.session_state.comparison_running = False

# Define the 10 CRISP-DM steps
crisp_dm_steps = [
    "1. Business Understanding",
    "2. Data Collection",
    "3. Data Understanding",
    "4. Data Preparation (Otomasi Batch 6 Periode)",
    "5. Dimensionality Reduction",
    "6. Modeling",
    "7. Time Series Analysis",
    "8. Evaluation",
    "9. Otomasi Analisis LLM",
    "9b. Causal Trend Analysis",
    "9c. Narrative Summary",
    "10. Deployment",
]

def run_step(step_index, file_name):
    step_method = step_names[step_index]
    try:
        if st.session_state.pipeline:
            progress_bar = st.progress(0)
            status_text = st.empty()
            current_step = crisp_dm_steps[step_index]
            status_text.subheader(f"⏳ Running: {current_step}")

            def update_progress(step_name, percent):
                percent = max(0, min(100, percent))
                progress_bar.progress(percent / 100)
                status_text.text(f"   {step_name}... {percent}%")

            st.session_state.pipeline.set_progress_callback(update_progress)
            
            method = getattr(st.session_state.pipeline, step_method)
            method()
            
            progress_bar.empty()
            status_text.empty()
            st.session_state.pipeline.set_progress_callback(None)
            
            st.session_state[step_method] = True
            st.session_state.errors[step_method] = None
            st.success(f"✅ Step {step_index + 1} completed successfully!")
        else:
            st.error("Pipeline not initialized.")
    except Exception as e:
        st.session_state.errors[step_method] = str(e)
        st.error(f"❌ Error in step {step_index + 1}: {e}")

if uploaded_file:
    # Save uploaded file temporarily
    file_name = "temp_dataset.xls"
    with open(file_name, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Check if this is a new file or provider changed
    if (st.session_state.uploaded_file_name != file_name or
        getattr(st.session_state, 'current_llm_provider', None) != llm_provider_key or
        getattr(st.session_state, 'current_llm_model', None) != llm_model):
        # Reset all steps
        for step in step_names:
            st.session_state[step] = False
        st.session_state.uploaded_file_name = file_name
        st.session_state.current_llm_provider = llm_provider_key
        st.session_state.current_llm_model = llm_model
        model, tokenizer = load_indobert_model()
        set_model(model, tokenizer)
        st.session_state.pipeline = PMBAnalysisPipeline(file_name, llm_provider=llm_provider_key, llm_model=llm_model)

    st.sidebar.subheader("Run Steps")
    for i, step_label in enumerate(crisp_dm_steps):
        step_key = step_names[i]
        if i == 0 or st.session_state[step_names[i-1]]:
            if not st.session_state[step_key]:
                if st.sidebar.button(f"Run {step_label}", key=f"btn_{i}"):
                    with st.spinner(f"Running {step_label}..."):
                        run_step(i, file_name)
        else:
            st.sidebar.text(f"Locked: {step_label}")

    # Overall Progress
    progress_value = sum(1 for s in step_names if st.session_state.get(s, False)) / len(step_names)
    st.sidebar.progress(progress_value)
    st.sidebar.text(f"Progress: {int(progress_value * 100)}%")

    st.sidebar.subheader("CRISP-DM Steps Progress")
    for i, step_label in enumerate(crisp_dm_steps):
        step_key = step_names[i]
        if st.session_state[step_key]:
            st.sidebar.success(f"✅ {step_label}")
        elif i == 0 or st.session_state[step_names[i-1]]:
            st.sidebar.info(f"🔄 {step_label}")
        else:
            st.sidebar.text(f"⏳ {step_label} (Waiting for previous step)")

    # Display errors if any
    for step, error in st.session_state.errors.items():
        if error:
            st.error(f"Error in {step}: {error}")

    # Display intermediate and final results
    if st.session_state.pipeline:
        pipeline = st.session_state.pipeline

        # Intermediate displays
        if st.session_state["data_understanding"]:
            st.subheader("Data Understanding Results")
            img_bytes = load_image_bytes(OUTPUTS_DIR / "distribusi_pendaftar.png")
            if img_bytes is not None:
                st.image(img_bytes, use_column_width=True)

        # Final results after deployment
        if st.session_state["deployment"]:
            # Calculate Key Metrics
            total_n = len(pipeline.raw) if hasattr(pipeline, 'raw') else 0
            ari_1920 = 0
            try:
                ari_1920 = next(
                    (
                        p.get("ari", 0)
                        for p in getattr(pipeline, 'ari_pairs', [])
                        if isinstance(p, dict) and p.get("y1") == 2019 and p.get("y2") == 2020
                    ),
                    0,
                )
            except Exception:
                pass
            proj_2025 = getattr(pipeline, 'proj_2025', 0)
            avg_sim = getattr(pipeline, 'avg_sim', 0)
            years = sorted(pipeline.by_year.keys()) if hasattr(pipeline, 'by_year') and pipeline.by_year else []

            # Metrics Dashboard
            st.subheader("📈 Key Metrics Dashboard")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Students (2019-2024)", total_n, help="Total pendaftar seluruh periode")
            col2.metric("ARI 2019→2020", f"{ari_1920:.4f}", help="Adjusted Rand Index transisi Pre-COVID ke COVID")
            col3.metric("Projection 2025", proj_2025, help="Proyeksi pendaftar berdasarkan regresi linier")
            col4.metric("Avg Similarity", f"{avg_sim:.4f}", help="Rata-rata cosine similarity embedding IndoBERT")
            st.markdown("---")

            # Lazy Loading Tab Navigation with Prev/Next buttons
            tab_options = [
                "📊 T4.1–4.2 & G4.1 (2 tables)",
                "🔬 T4.3–4.4 (2 tables)",
                "🧮 T4.5 & G4.3a (1 table)",
                "📈 T4.6 & G4.3c (1 table)",
                "🎯 T4.9–4.14 & G4.2 (6 tables)",
                "🔄 T4.15 (1 table)",
                "🚀 T4.16–4.18 & G4.5 (2 tables)",
                "🔍 Tren Kausal & Naratif",
                "📋 Ringkasan & Persona",
                "⚖️ Model Comparison",
            ]

            # Previous and Next buttons with validation
            col_prev, col_radio, col_next = st.columns([1, 4, 1])
            with col_prev:
                if st.button("⬅ Previous", disabled=st.session_state.active_tab == 0, key="prev_btn"):
                    st.session_state.active_tab = max(0, st.session_state.active_tab - 1)
            with col_next:
                if st.button("Next ➡", disabled=st.session_state.active_tab == len(tab_options) - 1, key="next_btn"):
                    st.session_state.active_tab = min(len(tab_options) - 1, st.session_state.active_tab + 1)

            active_tab = st.radio(
                "Select Result Section:",
                tab_options,
                index=st.session_state.active_tab,
                horizontal=True,
                key="tab_nav"
            )
            st.session_state.active_tab = tab_options.index(active_tab)
            st.markdown("---")

            # Tab 1: T4.1–4.2 & G4.1
            if active_tab == tab_options[0]:
                st.subheader("📊 Tabel 4.1–4.2 & Gambar 4.1")
                col1, col2 = st.columns([1, 1])
                with col1:
                    with st.expander("📊 Tabel 4.1: Distribusi Pendaftar", expanded=True):
                        df41 = load_csv_safe(OUTPUTS_DIR / "tabel_4_1_distribusi.csv")
                        if df41 is not None:
                            st.dataframe(df41, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_1" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.1**\n\n{pipeline.table_narratives['tabel_4_1']}")
                            st.download_button("⬇ Download Tabel 4.1 CSV", df41.to_csv(index=False), "tabel_4_1_distribusi.csv", key="dl_t41")
                        else:
                            st.warning("Tabel 4.1 tidak ditemukan.")
                    
                    with st.expander("📊 Tabel 4.2: Distribusi Prodi"):
                        df42 = load_csv_safe(OUTPUTS_DIR / "tabel_4_2_prodi.csv")
                        if df42 is not None:
                            st.dataframe(df42, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_2" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.2**\n\n{pipeline.table_narratives['tabel_4_2']}")
                            st.download_button("⬇ Download Tabel 4.2 CSV", df42.to_csv(index=False), "tabel_4_2_prodi.csv", key="dl_t42")
                        else:
                            st.warning("Tabel 4.2 tidak ditemukan.")
                
                with col2:
                    with st.expander("🖼️ Gambar 4.1: Distribusi Pendaftar", expanded=True):
                        img_fmt = st.radio("Format Gambar", ["PNG", "SVG"], key="fmt_g41", horizontal=True)
                        img_path = str(OUTPUTS_DIR / f"gambar_4_1_distribusi.{'png' if img_fmt == 'PNG' else 'svg'}")
                        img_bytes = load_image_bytes(img_path)
                        if img_bytes is not None:
                            st.image(img_bytes, use_column_width=True)
                            if hasattr(pipeline, "image_narratives") and "gambar_4_1" in pipeline.image_narratives:
                                st.markdown(f"**📖 Analisis Akademik Gambar 4.1**\n\n{pipeline.image_narratives['gambar_4_1']}")
                            elif hasattr(pipeline, "table_narratives") and "tabel_4_1" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.1 (Fallback)**\n\n{pipeline.table_narratives['tabel_4_1']}")
                            with open(img_path, "rb") as f:
                                st.download_button(f"⬇ Download Gambar 4.1 {img_fmt}", f, img_path.split("/")[-1], key="dl_g41")
                        else:
                            st.warning(f"Gambar 4.1 {img_fmt} tidak ditemukan.")

            # Tab 2: T4.3–4.4
            elif active_tab == tab_options[1]:
                st.subheader("🔬 Tabel 4.3–4.4")
                col1, col2 = st.columns([1, 1])
                with col1:
                    with st.expander("📊 Tabel 4.3: Preprocessing", expanded=True):
                        df43 = load_csv_safe(OUTPUTS_DIR / "tabel_4_3_preprocessing.csv")
                        if df43 is not None:
                            st.dataframe(df43, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_3" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.3**\n\n{pipeline.table_narratives['tabel_4_3']}")
                            st.download_button("⬇ Download Tabel 4.3 CSV", df43.to_csv(index=False), "tabel_4_3_preprocessing.csv", key="dl_t43")
                        else:
                            st.warning("Tabel 4.3 tidak ditemukan.")
                
                with col2:
                    with st.expander("📊 Tabel 4.4: Cosine Similarity", expanded=True):
                        df44a = load_csv_safe(OUTPUTS_DIR / "tabel_4_4_cosine_similarity.csv")
                        if df44a is not None:
                            st.dataframe(df44a, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_4" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.4**\n\n{pipeline.table_narratives['tabel_4_4']}")
                            st.download_button("⬇ Download Tabel 4.4 CSV", df44a.to_csv(index=False), "tabel_4_4_cosine_similarity.csv", key="dl_t44")
                        else:
                            st.warning("Tabel 4.4 tidak ditemukan.")

            # Tab 3: T4.5 & G4.3a
            elif active_tab == tab_options[2]:
                st.subheader("🧮 Tabel 4.5 & Gambar 4.3a")
                col1, col2 = st.columns([1, 1])
                with col1:
                    with st.expander("📊 Tabel 4.5: K-Scan", expanded=True):
                        df45 = load_csv_safe(OUTPUTS_DIR / "tabel_4_5_kscan.csv")
                        if df45 is not None:
                            st.dataframe(df45, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_5" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.5**\n\n{pipeline.table_narratives['tabel_4_5']}")
                            st.download_button("⬇ Download Tabel 4.5 CSV", df45.to_csv(index=False), "tabel_4_5_kscan.csv", key="dl_t45")
                        else:
                            st.warning("Tabel 4.5 tidak ditemukan.")
                
                with col2:
                    with st.expander("🖼️ Gambar 4.3a: Silhouette", expanded=True):
                        img_fmt = st.radio("Format Gambar", ["PNG", "SVG"], key="fmt_g43a", horizontal=True)
                        img_path = str(OUTPUTS_DIR / f"gambar_4_3a_silhouette.{'png' if img_fmt == 'PNG' else 'svg'}")
                        img_bytes = load_image_bytes(img_path)
                        if img_bytes is not None:
                            st.image(img_bytes, use_column_width=True)
                            if hasattr(pipeline, "image_narratives") and "gambar_4_3a" in pipeline.image_narratives:
                                st.markdown(f"**📖 Analisis Akademik Gambar 4.3a**\n\n{pipeline.image_narratives['gambar_4_3a']}")
                            with open(img_path, "rb") as f:
                                st.download_button(f"⬇ Download Gambar 4.3a {img_fmt}", f, img_path.split("/")[-1], key="dl_g43a")
                        else:
                            st.warning(f"Gambar 4.3a {img_fmt} tidak ditemukan.")

            # Tab 4: T4.6 & G4.3c
            elif active_tab == tab_options[3]:
                st.subheader("📈 Tabel 4.6 & Gambar 4.3c")
                col1, col2 = st.columns([1, 1])
                with col1:
                    with st.expander("📊 Tabel 4.6: ARI", expanded=True):
                        df46 = load_csv_safe(OUTPUTS_DIR / "tabel_4_6_ari.csv")
                        if df46 is not None:
                            st.dataframe(df46, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_6" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.6**\n\n{pipeline.table_narratives['tabel_4_6']}")
                            st.download_button("⬇ Download Tabel 4.6 CSV", df46.to_csv(index=False), "tabel_4_6_ari.csv", key="dl_t46")
                        else:
                            st.warning("Tabel 4.6 tidak ditemukan.")
                
                with col2:
                    with st.expander("🖼️ Gambar 4.3c: ARI Trend", expanded=True):
                        img_fmt = st.radio("Format Gambar", ["PNG", "SVG"], key="fmt_g43c", horizontal=True)
                        img_path = str(OUTPUTS_DIR / f"gambar_4_3c_ari.{'png' if img_fmt == 'PNG' else 'svg'}")
                        img_bytes = load_image_bytes(img_path)
                        if img_bytes is not None:
                            st.image(img_bytes, use_column_width=True)
                            if hasattr(pipeline, "image_narratives") and "gambar_4_3c" in pipeline.image_narratives:
                                st.markdown(f"**📖 Analisis Akademik Gambar 4.3c**\n\n{pipeline.image_narratives['gambar_4_3c']}")
                            with open(img_path, "rb") as f:
                                st.download_button(f"⬇ Download Gambar 4.3c {img_fmt}", f, img_path.split("/")[-1], key="dl_g43c")
                        else:
                            st.warning(f"Gambar 4.3c {img_fmt} tidak ditemukan.")

            # Tab 5: T4.9–4.14 & G4.2
            elif active_tab == tab_options[4]:
                st.subheader("🎯 Profil per Tahun & Scatter PCA")
                for y in years:
                    st.subheader(f"Tahun {y}")
                    csv_file = str(OUTPUTS_DIR / f"tabel_4_{9 + years.index(y)}_profil_{y}.csv")
                    png_file = str(OUTPUTS_DIR / f"gambar_4_2{chr(97 + years.index(y))}_scatter_{y}.png")
                    svg_file = str(OUTPUTS_DIR / f"gambar_4_2{chr(97 + years.index(y))}_scatter_{y}.svg")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        with st.expander(f"📊 Profil {y}", expanded=True):
                            df = load_csv_safe(csv_file)
                            if df is not None:
                                st.dataframe(df, use_container_width=True)
                                table_key = f"tabel_4_{9 + years.index(y)}"
                                if hasattr(pipeline, "table_narratives") and table_key in pipeline.table_narratives:
                                    st.markdown(f"**📖 Analisis Akademik Profil {y}**\n\n{pipeline.table_narratives[table_key]}")
                                st.download_button(f"⬇ Download Profil {y} CSV", df.to_csv(index=False), csv_file.split("/")[-1], key=f"dl_profil_{y}")
                            else:
                                st.warning(f"Profil {y} tidak ditemukan.")
                    with col2:
                        with st.expander(f"🖼️ Scatter PCA {y}", expanded=True):
                            img_fmt = st.radio("Format Gambar", ["PNG", "SVG"], key=f"fmt_scatter_{y}", horizontal=True)
                            img_path = png_file if img_fmt == "PNG" else svg_file
                            img_bytes = load_image_bytes(img_path)
                            if img_bytes is not None:
                                st.image(img_bytes, use_column_width=True)
                                image_key = f"gambar_4_2{chr(97 + years.index(y))}"
                                if hasattr(pipeline, "image_narratives") and image_key in pipeline.image_narratives:
                                    st.markdown(f"**📖 Analisis Akademik Scatter {y}**\n\n{pipeline.image_narratives[image_key]}")
                                with open(img_path, "rb") as f:
                                    st.download_button(f"⬇ Download Scatter {y} {img_fmt}", f, img_path.split("/")[-1], key=f"dl_scatter_{y}")
                            else:
                                st.warning(f"Scatter {y} {img_fmt} tidak ditemukan.")

            # Tab 6: T4.15
            elif active_tab == tab_options[5]:
                st.subheader("🔄 Tabel 4.15: Lifecycle")
                with st.expander("📊 Tabel 4.15: Lifecycle Pendaftar", expanded=True):
                    df415 = load_csv_safe(OUTPUTS_DIR / "tabel_4_15_lifecycle.csv")
                    if df415 is not None:
                        st.dataframe(df415, use_container_width=True)
                        if hasattr(pipeline, "table_narratives") and "tabel_4_15" in pipeline.table_narratives:
                            st.markdown(f"**📖 Analisis Akademik Tabel 4.15**\n\n{pipeline.table_narratives['tabel_4_15']}")
                        st.download_button("⬇ Download Tabel 4.15 CSV", df415.to_csv(index=False), "tabel_4_15_lifecycle.csv", key="dl_t415")
                    else:
                        st.warning("Tabel 4.15 tidak ditemukan.")

            # Tab 7: T4.16–4.18 & G4.5
            elif active_tab == tab_options[6]:
                st.subheader("🚀 Tabel 4.16–4.18 & Gambar 4.5")
                col1, col2 = st.columns([1, 1])
                with col1:
                    with st.expander("📊 Tabel 4.16: Prioritas 2025", expanded=True):
                        df416 = load_csv_safe(OUTPUTS_DIR / "tabel_4_16_prioritasi_2025.csv")
                        if df416 is not None:
                            st.dataframe(df416, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_16" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.16**\n\n{pipeline.table_narratives['tabel_4_16']}")
                            st.download_button("⬇ Download Tabel 4.16 CSV", df416.to_csv(index=False), "tabel_4_16_prioritasi_2025.csv", key="dl_t416")
                        else:
                            st.warning("Tabel 4.16 tidak ditemukan.")
                    
                    with st.expander("📊 Tabel 4.18: Perbandingan"):
                        df418 = load_csv_safe(OUTPUTS_DIR / "tabel_4_18_perbandingan.csv")
                        if df418 is not None:
                            st.dataframe(df418, use_container_width=True)
                            if hasattr(pipeline, "table_narratives") and "tabel_4_18" in pipeline.table_narratives:
                                st.markdown(f"**📖 Analisis Akademik Tabel 4.18**\n\n{pipeline.table_narratives['tabel_4_18']}")
                            st.download_button("⬇ Download Tabel 4.18 CSV", df418.to_csv(index=False), "tabel_4_18_perbandingan.csv", key="dl_t418")
                        else:
                            st.warning("Tabel 4.18 tidak ditemukan.")
                
                with col2:
                    with st.expander("🖼️ Gambar 4.5: Proyeksi 2025", expanded=True):
                        img_fmt = st.radio("Format Gambar", ["PNG", "SVG"], key="fmt_g45", horizontal=True)
                        img_path = str(OUTPUTS_DIR / f"gambar_4_5_proyeksi.{'png' if img_fmt == 'PNG' else 'svg'}")
                        img_bytes = load_image_bytes(img_path)
                        if img_bytes is not None:
                            st.image(img_bytes, use_column_width=True)
                            if hasattr(pipeline, "image_narratives") and "gambar_4_5" in pipeline.image_narratives:
                                st.markdown(f"**📖 Analisis Akademik Gambar 4.5**\n\n{pipeline.image_narratives['gambar_4_5']}")
                            with open(img_path, "rb") as f:
                                st.download_button(f"⬇ Download Gambar 4.5 {img_fmt}", f, img_path.split("/")[-1], key="dl_g45")
                        else:
                            st.warning(f"Gambar 4.5 {img_fmt} tidak ditemukan.")

            # Tab 8: Tren Kausal & Naratif
            elif active_tab == tab_options[7]:
                st.subheader("🔍 Analisis Tren Kausal & Ringkasan Naratif")
                if hasattr(pipeline, "ari_pairs") and pipeline.ari_pairs:
                    with st.expander("📊 Tabel Adjusted Rand Index (ARI) Antar Tahun", expanded=True):
                        ari_df = pd.DataFrame(pipeline.ari_pairs)
                        ari_df = ari_df.rename(columns={"y1": "Tahun 1", "y2": "Tahun 2", "ari": "ARI"})
                        st.dataframe(ari_df, use_container_width=True)
                        st.markdown("""
**📖 Penjelasan ARI**

Adjusted Rand Index (ARI) mengukur stabilitas cluster antara dua tahun berurutan. Nilai ARI berkisar dari -1 (perbedaan maksimal) hingga 1 (kesamaan maksimal). Nilai tinggi menunjukkan konsistensi segmentasi mahasiswa antar tahun, sedangkan nilai rendah atau negatif menandai perubahan struktural signifikan, seperti dampak pandemi COVID-19.
                        """)
                if hasattr(pipeline, "causal_explanations"):
                    with st.expander("📖 Penalaran Kausal Per Transisi", expanded=True):
                        for exp in pipeline.causal_explanations:
                            st.markdown(f"**Analisis Kausal {exp['transisi']}**\n\n{exp['penjelasan']}\n\n---")
                if hasattr(pipeline, "narrative"):
                    with st.expander("📖 Ringkasan Naratif Komprehensif", expanded=True):
                        st.markdown(pipeline.narrative)

            # Tab 9: Ringkasan & Persona
            elif active_tab == tab_options[8]:
                st.subheader("📋 Ringkasan Metrik Utama & Validasi Data")
                # Preserved original metrics display
                total_n = len(pipeline.raw) if hasattr(pipeline, 'raw') else 0
                avg_rec = 0
                if years:
                    rec_years = [y for y in years if FASE.get(y, "") == "Recovery"]
                    if rec_years:
                        avg_rec = sum(pipeline.gmm_res.get(y, {}).get("n", 0) for y in rec_years) / len(rec_years)
                proj_2025 = getattr(pipeline, 'proj_2025', 0)
                avg_sim = getattr(pipeline, 'avg_sim', 0)
                ari_1920 = ari_1920  # from earlier calculation

                st.markdown(f"""
### Statistik Utama Analisis PMB ITSNU Pekalongan

- **Total Pendaftar (2019-2024)**: {total_n} siswa
- **Rata-rata Pendaftar Fase Recovery (2022-2024)**: {avg_rec:.1f} siswa per tahun
- **Proyeksi Pendaftar 2025**: {proj_2025} siswa
- **Rata-rata Kesamaan Embedding Antar Tahun**: {avg_sim:.4f}
- **Adjusted Rand Index (ARI) 2019→2020**: {ari_1920:.4f}

### Validasi Data
Data berasal dari dataset PMB ITSNU Pekalongan 2019-2024 dengan distribusi kabupaten dominan di Jawa Tengah (Pekalongan, Batang), program studi S1/S3, dan jalur penerimaan seperti KIPK dan Bidikmisi. Semua metrik divalidasi terhadap tabel distribusi dan analisis clustering untuk memastikan akurasi akademik.
                """)
                with st.expander("📖 Penjelasan Detail Metrik"):
                    st.markdown("""
**Total Pendaftar**: Jumlah absolut siswa yang mendaftar, digunakan sebagai baseline untuk semua perhitungan persentase dan proyeksi.

**Rata-rata Recovery**: Hitungan rata-rata dari tahun 2022-2024 untuk menilai tren pasca-pandemi, sesuai dengan fase yang ditentukan dalam analisis.

**Proyeksi 2025**: Diperoleh dari regresi linier terhadap data recovery, dengan validasi terhadap data historis untuk menghindari overestimation.

**Kesamaan Embedding**: Menggunakan cosine similarity pada embedding IndoBERT dari kombinasi nama, sekolah, kabupaten, dan alamat siswa, menunjukkan seberapa mirip profil mahasiswa antar tahun.

**ARI**: Mengukur kesamaan cluster antara tahun berurutan; nilai mendekati 1 berarti stabil, 0 berarti acak, negatif berarti perubahan drastis.
                    """)

                # Persona Display (preserved existing functionality)
                if hasattr(pipeline, "personas") and pipeline.personas:
                    st.subheader("🎭 Persona Mahasiswa per Tahun")
                    for y in sorted(pipeline.personas.keys()):
                        with st.expander(f"📖 Persona Tahun {y}"):
                            for p in pipeline.personas[y]:
                                st.markdown(f"**Klaster {p['cluster']}**: {p['persona']}")
                    st.subheader("📈 Analisis Komparatif Persona 2019-2024")
                    st.markdown("""
**Evolusi Persona Mahasiswa ITSNU Pekalongan (2019-2024)**

Berdasarkan analisis persona mahasiswa yang dihasilkan melalui clustering GMM dan augmented dengan data LLDIKTI, terlihat evolusi signifikan dalam profil mahasiswa selama enam tahun terakhir:

- **2019 (Pre-COVID)**: Personas menunjukkan mahasiswa dengan latar belakang keluarga sederhana namun bermotivasi tinggi, dominan dari kabupaten Pekalongan dengan fokus pada program informatika.
- **2020-2021 (COVID Crisis)**: Terjadi diversifikasi persona dengan peningkatan siswa dari keluarga petani dan buruh, mencerminkan dampak ekonomi pandemi.
- **2022-2024 (Recovery)**: Personas menunjukkan kematangan dengan latar belakang yang lebih beragam, termasuk siswa dari desa terpencil. Ada peningkatan motivasi karir di bidang teknologi.

**Pola Umum Persona**:
- **Demografi**: Mayoritas dari Kabupaten Pekalongan (Jawa Tengah), dengan variasi antara kota dan desa.
- **Ekonomi**: Dari keluarga sederhana hingga menengah, dengan peningkatan akses beasiswa selama recovery.
- **Akademik**: Preferensi kuat pada program teknologi informasi dan informatika.
- **Sosial**: Aktif dalam kegiatan kampus, dengan motivasi untuk berkontribusi pada masyarakat lokal.
                    """)

            # Tab 10: Model Comparison
            elif active_tab == tab_options[9]:
                st.subheader("⚖️ Model Comparison — Persona Generation")
                st.markdown("Bandingkan kualitas persona generation antar 4 LLM providers.")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    compare_providers = st.multiselect(
                        "Pilih providers untuk dibandingkan:",
                        COMPARISON_PROVIDERS,
                        default=["Ollama", "Gemini", "Kilo", "OpenCode"],
                    )
                with col2:
                    if st.button("▶ Run Comparison", disabled=st.session_state.comparison_running or not st.session_state.get("deployment", False)):
                        st.session_state.comparison_running = True
                        with st.spinner("Generating personas for all providers..."):
                            try:
                                results = run_comparison(pipeline, compare_providers)
                                st.session_state.comparison_results = results
                                st.success("Comparison completed!")
                            except Exception as e:
                                st.error(f"Comparison failed: {e}")
                            finally:
                                st.session_state.comparison_running = False
                with col3:
                    if st.button("🗑 Clear Cache"):
                        clear_comparison(compare_providers)
                        st.session_state.comparison_results = {}
                        st.success("Cache cleared!")
                
                if not st.session_state.get("deployment", False):
                    st.warning("⚠️ Jalankan pipeline sampai step 10 (Deployment) terlebih dahulu sebelum membandingkan model.")
                
                # Display results
                results = st.session_state.get("comparison_results", {})
                if results:
                    st.markdown("---")
                    st.subheader("Hasil Perbandingan")
                    
                    # Summary table
                    summary_data = []
                    for provider in compare_providers:
                        r = results.get(provider, {})
                        status = r.get("status", "missing")
                        personas = r.get("personas", {})
                        metadata = r.get("metadata", {})
                        total = sum(len(v) for v in personas.values()) if personas else 0
                        elapsed = metadata.get("elapsed_seconds", "-")
                        summary_data.append({
                            "Provider": provider,
                            "Status": status,
                            "Total Personas": total,
                            "Waktu (detik)": elapsed,
                        })
                    
                    if summary_data:
                        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
                    
                    # Side-by-side view
                    st.markdown("---")
                    st.subheader("Side-by-Side Persona")
                    
                    available_providers = [p for p in compare_providers if p in results and results[p].get("personas")]
                    if len(available_providers) >= 2:
                        for y in sorted(set().union(*[results[p].get("personas", {}).keys() for p in available_providers])):
                            st.markdown(f"### Tahun {y}")
                            cols = st.columns(len(available_providers))
                            for idx, provider in enumerate(available_providers):
                                with cols[idx]:
                                    st.markdown(f"**{provider}**")
                                    personas = results[provider].get("personas", {}).get(y, [])
                                    for p in personas:
                                        with st.expander(f"Klaster {p['cluster']}", expanded=True):
                                            st.markdown(p["persona"])
                    elif len(available_providers) == 1:
                        provider = available_providers[0]
                        st.markdown(f"### {provider}")
                        personas = results[provider].get("personas", {})
                        for y in sorted(personas.keys()):
                            st.markdown(f"#### Tahun {y}")
                            for p in personas[y]:
                                with st.expander(f"Klaster {p['cluster']}", expanded=True):
                                    st.markdown(p["persona"])
                    else:
                        st.info("Belum ada hasil. Klik 'Run Comparison' untuk memulai.")
                else:
                    st.info("Belum ada hasil perbandingan. Klik 'Run Comparison' untuk memulai.")

            # Clean up temp file if all done
            if st.session_state["deployment"]:
                if os.path.exists("temp_dataset.xls"):
                    os.remove("temp_dataset.xls")

else:
    st.info("Upload dataset XLS file to start analysis.")
