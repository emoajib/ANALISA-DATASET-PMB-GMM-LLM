import re
import functools
import hashlib
import os
import json
import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderRateLimited

EMBEDDING_CACHE_FILE = "data/embedding_cache.json"

def get_text_hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:16]

def load_embedding_cache():
    if os.path.exists(EMBEDDING_CACHE_FILE):
        try:
            with open(EMBEDDING_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Cache load error: {e}")
    return {}

def save_embedding_cache(cache_dict):
    os.makedirs(os.path.dirname(EMBEDDING_CACHE_FILE), exist_ok=True)
    with open(EMBEDDING_CACHE_FILE, 'w') as f:
        json.dump(cache_dict, f)

_embedding_cache = None
_model = None
_tokenizer = None

ABBR_ENTRIES = [
    (r'\bjk\b', 'jakarta'),
    (r'\bjkt\b', 'jakarta'),
    (r'\bbdg\b', 'bandung'),
    (r'\bsby\b', 'surabaya'),
    (r'\bjbr\b', 'jawa barat'),
    (r'\bjtl\b', 'jawa tengah'),
    (r'\bjtm\b', 'jawa timur'),
    (r'\bbks\b', 'bekasi'),
    (r'\btgr\b', 'tangerang'),
    (r'\bdpk\b', 'daerah pariwisata'),
    (r'\bpkl\b', 'pekalongan'),
    (r'\bbtl\b', 'batang'),
    (r'\bpw\b', 'pemalang'),
    (r'\bts\b', 'tegal'),
    (r'\bbkl\b', 'bakalon'),
    (r'\bslg\b', 'slawi'),
    (r'\bwns\b', 'wonosobo'),
    (r'\bpwkt\b', 'purwakarta'),
    (r'\bklm\b', 'kulon progo'),
    (r'\bbny\b', 'banyuwangi'),
    (r'\bjmb\b', 'jember'),
    (r'\bsk\b', 'sukabumi'),
    (r'\bcrb\b', 'cilacap'),
    (r'\bkds\b', 'kendal'),
    (r'\bsrn\b', 'semarang'),
    (r'\bpwr\b', 'purwodadi'),
    (r'\bkjm\b', 'kajen'),
    (r'\btmg\b', 'temanggung'),
    (r'\bwlt\b', 'walisanga'),
    (r'\bitsnu\b', 'institut teknologi satu nusantara'),
    (r'\bitsnupkl\b', 'institut teknologi satu nusantara pekalongan'),
    (r'\bs1\b', 'sarjana'),
    (r'\bd3\b', 'diploma tiga'),
    (r'\bd4\b', 'diploma empat'),
    (r'\bmi\b', 'manajemen informatika'),
    (r'\bti\b', 'teknologi informasi'),
    (r'\bsi\b', 'sistem informasi'),
    (r'\bpt\b', 'perguruan tinggi'),
    (r'\bkab\b', 'kabupaten'),
    (r'\bkec\b', 'kecamatan'),
    (r'\bdesa\b', 'desa'),
    (r'\bds\b', 'desa'),
    (r'\bbidikmisi\b', 'beasiswa bidikmisi'),
    (r'\bkipk\b', 'beasiswa kip kuliah'),
    (r'\bpip\b', 'beasiswa pip'),
    (r'\bkip\b', 'beasiswa kip kuliah'),
    (r'\bji\b', 'jiwa'),
    (r'\bsd\b', 'sekolah dasar'),
    (r'\bsmp\b', 'sekolah menengah pertama'),
    (r'\bsma\b', 'sekolah menengah atas'),
    (r'\bma\b', 'madrasah aliyah'),
    (r'\bmts\b', 'madrasah tsanawiyah'),
    (r'\bno\b', 'nomor'),
    (r'\bgg\b', 'gang'),
]

def preprocess(text):
    if not text or str(text).strip() == "" or str(text).lower() == "nan":
        return ""
    t = re.sub(r"[^a-z0-9\s]", " ", str(text).lower()).replace("\s+", " ").strip()
    for pat, rep in ABBR_ENTRIES:
        t = re.sub(pat, rep, t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()

def get_embedding(text, model=None, tokenizer=None, dim=768):
    global _embedding_cache, _model, _tokenizer
    
    if _embedding_cache is None:
        _embedding_cache = load_embedding_cache()
    
    t = preprocess(text) or "unknown"
    key = get_text_hash(t)
    
    if key in _embedding_cache:
        # JSON loads gives us a list directly
        emb = _embedding_cache[key]
        return emb if dim == 768 else emb[:dim]
    
    # Load model only once
    if _model is None or _tokenizer is None:
        model_name = "indobenchmark/indobert-base-p1"
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModel.from_pretrained(model_name)
        _model.eval()
    
    inputs = _tokenizer(
        t, return_tensors="pt", truncation=True, max_length=512, padding=True
    )
    with torch.no_grad():
        outputs = _model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    result = embeddings.tolist() if dim == 768 else embeddings.tolist()[:dim]
    _embedding_cache[key] = result  # Store as list, not string
    save_embedding_cache(_embedding_cache)  # Auto-save to disk
    return result


def get_embeddings_batch(texts, model=None, tokenizer=None, dim=768, batch_size=16):
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = load_embedding_cache()
    
    if model is None or tokenizer is None:
        model_name = "indobenchmark/indobert-base-p1"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        model.eval()
    
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        processed = [preprocess(t) or "unknown" for t in batch]
        inputs = tokenizer(
            processed, return_tensors="pt", truncation=True, max_length=512, padding=True
        )
        with torch.no_grad():
            outputs = model(**inputs)
        batch_emb = outputs.last_hidden_state.mean(dim=1).numpy()
        for j, emb in enumerate(batch_emb):
            t = processed[j]
            key = get_text_hash(t)
            result = emb.tolist() if dim == 768 else emb.tolist()[:dim]
            _embedding_cache[key] = str(result)
            results.append(result)
    save_embedding_cache(_embedding_cache)
    return results

def post_process_persona(persona):
    corrections = {
        "Pekerjan": "Pekalongan",
        "Pecalangan": "Pekalongan",
        "Pecelangan": "Pekalongan",
        "Pekaongan": "Pekalongan",
        "Pekerangan": "Pekalongan",
        "Pekerolan": "Pekalongan",
        "Pecakongan": "Pekalongan",
        "Pekaolon": "Pekalongan",
        "Sulawesi Tengah": "Jawa Tengah",
        "Sulawesi Barat": "Jawa Tengah",
        "Sulawesi Selatan": "Jawa Tengah",
        "Kalimantan": "Jawa Tengah",
        "Sumatera Utara": "Jawa Tengah",
        "Provinsi Sulawesi": "Provinsi Jawa Tengah",
        "Provinsi Kalimantan": "Provinsi Jawa Tengah",
        "Bidikmisi": "Bidikmisi",
        "Kipk": "KIPK",
        "Kualifikasi I": "KIPK",
        "Beasiswa Pip": "Beasiswa PIP",
        "Umum": "Umum",
        "Informatika": "S1 Informatika",
        "Teknologi Informasi": "S1 Teknologi Informasi",
        "D3 Akuntansi": "D3 Akuntansi",
        "UNNES": "ITSNU Pekalongan",
        "UNP": "ITSNU Pekalongan",
        "UNPemula": "ITSNU Pekalongan",
        "Institute Teknologi Sesuatu Nusantara": "ITSNU Pekalongan",
        "ITSNU Pekalongan": "ITSNU Pekalongan",
        "ITS NU Pekalongan": "ITSNU Pekalongan",
        "ITS NUSANTARA Pekalongan": "ITSNU Pekalongan",
        "Universitas Negeri Surakarta": "ITSNU Pekalongan",
        "Institusi Teknologi Superlir": "ITSNU Pekalongan",
        "S1 S1": "S1",
    }
    for wrong, correct in corrections.items():
        persona = persona.replace(wrong, correct)
    return persona

def jaccard_similarity(set1, set2):
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0

def centroid_drift(centers1, centers2):
    if len(centers1) != len(centers2):
        return float("inf")
    return np.mean(
        [
            np.sqrt(np.sum((np.array(c1) - np.array(c2)) ** 2))
            for c1, c2 in zip(centers1, centers2)
        ]
    )

@functools.lru_cache(maxsize=1024)
def geocode_location(text, timeout=10):
    geolocator = Nominatim(user_agent="pmb_analysis")
    try:
        location = geolocator.geocode(text, timeout=timeout)
        if location:
            return location.latitude, location.longitude
    except GeocoderRateLimited:
        import time
        time.sleep(60)
        try:
            location = geolocator.geocode(text, timeout=timeout)
            if location:
                return location.latitude, location.longitude
        except Exception:
            pass
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None

def avg(values):
    if len(values) == 0:
        return 0
    return float(np.mean(values))

def rnd(value, decimals=3):
    return round(value, decimals)

def detect_col(hs, pats):
    for p in pats:
        f = next((h for h in hs if re.search(p, str(h), re.I)), "")
        if f:
            return f
    return ""

def detect_year(row):
    for v in row.values():
        cleaned = re.sub(r"\D", "", str(v))
        if cleaned:
            n = int(cleaned[:4])
            if 2019 <= n <= 2024:
                return n
    return None

def pct(a, b):
    return 0 if b == 0 else round(a / b * 100, 1)

LLM_CACHE_FILE = "data/llm_cache.json"
_llm_cache = None

def load_llm_cache():
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache
    if os.path.exists(LLM_CACHE_FILE):
        try:
            with open(LLM_CACHE_FILE, 'r') as f:
                _llm_cache = json.load(f)
                return _llm_cache
        except Exception as e:
            print(f"LLM cache load error: {e}")
    _llm_cache = {}
    return _llm_cache

def save_llm_cache():
    global _llm_cache
    if _llm_cache:
        os.makedirs(os.path.dirname(LLM_CACHE_FILE), exist_ok=True)
        with open(LLM_CACHE_FILE, 'w') as f:
            json.dump(_llm_cache, f)

def get_llm_hash(prompt, provider, max_tokens):
    return hashlib.md5(f"{prompt}|{provider}|{max_tokens}".encode()).hexdigest()[:16]
