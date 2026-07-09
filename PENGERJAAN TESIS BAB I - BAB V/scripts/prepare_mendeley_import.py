#!/usr/bin/env python3
"""
prepare_mendeley_import.py
Backup + validasi BibTeX + generate checklist sebelum re-import ke Mendeley.
"""

import os, re, shutil, sys
from datetime import datetime

BASE = "."
BIB_FILE = os.path.join(BASE, "referensi.bib")
PDF_DIR = os.path.join(BASE, "reference/referensi_pdf")
CHECK_PY = os.path.join(BASE, "check/check_pedoman.py")

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = os.path.join(BASE, f"_BEFORE_MENDELEY_{ts}/")
CHECKLIST_FILE = os.path.join(BASE, "MENDELEY_IMPORT_CHECKLIST.txt")

errors = []
warnings = []

def log(msg, level="INFO"):
    print(f"  [{level}] {msg}")

def parse_bibtex(filepath):
    """Parse BibTeX file into list of entry dicts.
    Handles nested braces by tracking depth manually."""

    def strip_braces(s):
        """Remove outer braces and unescape."""
        s = s.strip()
        if s.startswith('{') and s.endswith('}'):
            # Count depth to verify matching
            depth = 0
            for i, c in enumerate(s):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                if depth == 0 and i < len(s) - 1:
                    return s  # premature close, keep as-is
            return s[1:-1].strip()
        return s

    with open(filepath, "r") as f:
        content = f.read()

    # Remove comment lines
    lines = content.split('\n')
    clean = '\n'.join(l for l in lines if not l.strip().startswith('%'))

    entries = []
    i = 0
    while True:
        at = clean.find('@', i)
        if at == -1:
            break
        brace = clean.find('{', at)
        if brace == -1:
            break

        # Extract type and key
        header = clean[at + 1:brace]
        entry_type = header.split()[0].strip().lower()

        # Find matching closing brace
        depth = 1
        j = brace + 1
        while j < len(clean) and depth > 0:
            if clean[j] == '{':
                depth += 1
            elif clean[j] == '}':
                depth -= 1
            j += 1

        body = clean[brace + 1:j - 1]

        # Split key from body
        key_end = body.find(',')
        if key_end == -1:
            i = j
            continue
        citation_key = body[:key_end].strip()
        rest = body[key_end + 1:]

        # Parse field=value pairs (split at top-level commas)
        pairs = []
        cur = ''
        depth = 0
        for c in rest:
            if c == '{':
                depth += 1
                cur += c
            elif c == '}':
                depth -= 1
                cur += c
            elif c == ',' and depth == 0:
                if cur.strip():
                    pairs.append(cur.strip())
                cur = ''
            else:
                cur += c
        if cur.strip():
            pairs.append(cur.strip())

        fields = {}
        for p in pairs:
            eq = p.find('=')
            if eq != -1:
                fname = p[:eq].strip().lower()
                fval = p[eq + 1:].strip()
                fields[fname] = strip_braces(fval)

        entries.append({
            "type": entry_type,
            "key": citation_key,
            "fields": fields,
        })
        i = j

    return entries

def validate_entries(entries):
    """Validate each entry has required fields for its type."""
    required = {
        "article": ["author", "title", "journal", "year"],
        "inproceedings": ["author", "title", "booktitle", "year"],
        "incollection": ["author", "title", "booktitle", "publisher", "year"],
        "book": ["author", "title", "publisher", "year"],
        "misc": ["author", "title", "year", "howpublished", "note"],
        "techreport": ["author", "title", "institution", "year"],
    }

    optional_doi = ["article", "inproceedings", "incollection", "book"]

    for e in entries:
        t = e["type"]
        key = e["key"]
        fields = e["fields"]

        # 1. Check required fields
        req = required.get(t, [])
        for field in req:
            if field not in fields:
                msg = f"{key} ({t}): missing required field '{field}'"
                errors.append(msg)
                log(msg, "ERROR")

        # 2. Recommend DOI/url for academic entries
        if t in optional_doi:
            has_id = "doi" in fields or "url" in fields
            if not has_id:
                msg = f"{key} ({t}): no DOI or URL (may be OK, verify)"
                warnings.append(msg)
                log(msg, "WARN")

        # 3. For @misc: must have publisher, url, howpublished
        if t == "misc":
            for f in ["publisher", "url", "howpublished"]:
                if f not in fields:
                    msg = f"{key} ({t}): missing '{f}'"
                    errors.append(msg)
                    log(msg, "ERROR")

        # 4. For @article: check journal not empty
        if t == "article":
            j = fields.get("journal", "")
            if not j:
                msg = f"{key} ({t}): journal field is empty"
                errors.append(msg)
                log(msg, "ERROR")

        # 5. Check for @online (Mendeley doesn't support it well)
        if t == "online":
            msg = f"{key}: masih menggunakan @online! Harus diganti @misc"
            errors.append(msg)
            log(msg, "ERROR")

    return len(errors) == 0

def generate_checklist(entries):
    """Generate Mendeley import checklist."""
    lines = []
    lines.append("=" * 72)
    lines.append("MENDELEY IMPORT CHECKLIST")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Langkah: Hapus collection lama di Mendeley, lalu import referensi.bib")
    lines.append("Beri tanda [x] setelah diverifikasi di Mendeley.")
    lines.append("")
    lines.append(f"{'No':<4} {'[ ]':<6} {'Key':<24} {'Type':<15} {'Title'}")
    lines.append("-" * 72)

    type_names = {
        "article": "Journal Article",
        "inproceedings": "Conference Proc.",
        "incollection": "Book Chapter",
        "book": "Book",
        "misc": "Misc/Web",
        "techreport": "Tech Report",
    }

    for i, e in enumerate(entries, 1):
        tname = type_names.get(e["type"], e["type"])
        title = e["fields"].get("title", "(no title)")
        # Clean up LaTeX from title
        title = re.sub(r'\{[^}]*\}', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) > 50:
            title = title[:47] + "..."
        lines.append(f"{i:<4} {'[ ]':<6} {e['key']:<24} {tname:<15} {title}")

    lines.append("-" * 72)
    lines.append(f"Total entries: {len(entries)}")
    lines.append("")

    # Summary by type
    lines.append("DISTRIBUSI TIpe ENTRY:")
    type_counts = {}
    for e in entries:
        type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1
    for t, c in sorted(type_counts.items()):
        lines.append(f"  {t}: {c}")
    lines.append("")

    if errors:
        lines.append("ERRORS (harus diperbaiki sebelum import):")
        for e in errors:
            lines.append(f"  - {e}")
    if warnings:
        lines.append("WARNINGS (perlu dicek manual):")
        for w in warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)

def backup():
    """Create timestamped backup."""
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Backup referensi.bib
    if os.path.exists(BIB_FILE):
        shutil.copy2(BIB_FILE, BACKUP_DIR)
        log(f"Copied referensi.bib → {BACKUP_DIR}")

    # Backup reference/referensi_pdf/
    pdf_backup = os.path.join(BACKUP_DIR, "reference/referensi_pdf")
    if os.path.exists(PDF_DIR):
        shutil.copytree(PDF_DIR, pdf_backup, dirs_exist_ok=True)
        count = len([f for f in os.listdir(pdf_backup) if f.endswith(".pdf")])
        log(f"Copied {count} PDFs → {pdf_backup}")

    # Get backup size
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(BACKUP_DIR):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    log(f"Backup size: {total_size / 1024 / 1024:.1f} MB")
    return True

def run_check_pedoman():
    """Run check/check_pedoman.py if exists."""
    if os.path.exists(CHECK_PY):
        log("Running check/check_pedoman.py...")
        result = os.system(f"python3 \"{CHECK_PY}\"")
        if result == 0:
            log("check/check_pedoman.py: PASSED")
            return True
        else:
            log("check/check_pedoman.py: FAILED", "ERROR")
            return False
    else:
        log("check/check_pedoman.py not found, skipping")
        return None

def main():
    print("=" * 60)
    print("  PREPARE MENDELEY IMPORT")
    print("=" * 60)
    print()

    # Step 1: Backup
    print("[1/4] Backup referensi.bib + reference/referensi_pdf/ ...")
    backup()
    print()

    # Step 2: Parse & validate
    print("[2/4] Validasi BibTeX entries ...")
    if not os.path.exists(BIB_FILE):
        log(f"File not found: {BIB_FILE}", "ERROR")
        sys.exit(1)

    entries = parse_bibtex(BIB_FILE)
    log(f"Parsed {len(entries)} entries from referensi.bib")

    is_valid = validate_entries(entries)
    print()

    # Step 3: Generate checklist
    print("[3/4] Generate MENDELEY_IMPORT_CHECKLIST.txt ...")
    checklist = generate_checklist(entries)
    with open(CHECKLIST_FILE, "w") as f:
        f.write(checklist)
    log(f"Checklist written to {CHECKLIST_FILE}")
    print()

    # Step 4: Run check/check_pedoman.py
    print("[4/4] Final verification ...")
    run_check_pedoman()
    print()

    # Summary
    print("=" * 60)
    if errors:
        print(f"  RESULT: {len(errors)} ERROR(S) — PERBAIKI DULU SEBELUM IMPORT!")
        for e in errors:
            print(f"    • {e}")
    else:
        print("  RESULT: ✅ Semua entry valid, siap import ke Mendeley")
    if warnings:
        print(f"  Warnings: {len(warnings)} (cek manual)")
    print(f"  Backup:   {BACKUP_DIR}")
    print(f"  Checklist: {CHECKLIST_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
