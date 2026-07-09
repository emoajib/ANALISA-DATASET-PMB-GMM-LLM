#!/usr/bin/env python3
"""
STRATEGI B: Generate Diagram Baru + Replace di DOCX
====================================================
Menghasilkan diagram Kerangka Konseptual 4 Fase dan menggantinya di DOCX.

Fase 1: Ekstraksi Fitur (Biru)
Fase 2: Segmentasi Probabilistik (Hijau)
Fase 3: Otomasi Analisis LLM (Oranye)
Fase 4: Validasi Expert (Ungu)

Output: 
  - /tmp/kerangka_konseptual_v2.png (1417x800)
  - BAB I - BAB IV.docx (updated)
"""

import os
import io
import zipfile
import shutil
import re
from PIL import Image, ImageDraw, ImageFont

# ─── KONFIGURASI ────────────────────────────────────────────────────────────

import sys, os
from pipeline import utils

DOCX_PATH = str(utils.get_doc_path())
DOCX_BAK  = DOCX_PATH + ".bak_gambar"
OUTPUT_PNG = "/tmp/kerangka_konseptual_v2.png"

# Canvas
WIDTH = 1417
HEIGHT = 800
BG_COLOR = (255, 255, 255)

# Font paths
FONT_TNR       = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
FONT_TNR_BOLD  = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
FONT_TNR_ITALIC = "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"

# Phase colors (header background)
COLORS = {
    "blue":   (41, 128, 185),    # Fase 1
    "green":  (46, 204, 113),    # Fase 2
    "orange": (230, 126, 34),    # Fase 3
    "purple": (142, 68, 173),    # Fase 4
}
COLOR_LIGHT = {
    "blue":   (214, 234, 248),
    "green":  (214, 245, 224),
    "orange": (251, 230, 210),
    "purple": (235, 220, 240),
}
COLOR_BORDER = {
    "blue":   (21, 67, 96),
    "green":  (22, 100, 60),
    "orange": (135, 75, 20),
    "purple": (75, 35, 90),
}

# ─── GENERATE DIAGRAM ──────────────────────────────────────────────────────

print("🔷 Generating diagram...")

# Load fonts
font_title    = ImageFont.truetype(FONT_TNR_BOLD, 22)
font_subtitle = ImageFont.truetype(FONT_TNR, 14)
font_phase    = ImageFont.truetype(FONT_TNR_BOLD, 13)
font_item     = ImageFont.truetype(FONT_TNR, 11)
font_small    = ImageFont.truetype(FONT_TNR, 10)
font_italic   = ImageFont.truetype(FONT_TNR_ITALIC, 11)
font_source   = ImageFont.truetype(FONT_TNR_ITALIC, 10)

img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
draw = ImageDraw.Draw(img)

def text_bbox(draw, text, font):
    """Get text bounding box."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def draw_phase_box(draw, x, y, box_w, box_h, title, items, color_key):
    """Draw a phase box with colored header, white body, and border."""
    color = COLORS[color_key]
    light = COLOR_LIGHT[color_key]
    border = COLOR_BORDER[color_key]
    
    # Shadow
    draw.rounded_rectangle(
        [(x + 3, y + 3), (x + box_w + 3, y + box_h + 3)],
        radius=6, fill=(220, 220, 220)
    )
    
    # Main box background (light fill)
    draw.rounded_rectangle(
        [(x, y), (x + box_w, y + box_h)],
        radius=6, fill=light, outline=border, width=2
    )
    
    # Header bar (colored)
    header_h = 36
    draw.rounded_rectangle(
        [(x, y), (x + box_w, y + header_h)],
        radius=6, fill=color
    )
    # Cover bottom corners of header
    draw.rectangle([(x, y + header_h - 6), (x + box_w, y + header_h)], fill=color)
    
    # Phase number circle
    phase_num = list(COLORS.keys()).index(color_key) + 1
    circle_r = 11
    cx, cy = x + 22, y + header_h // 2
    draw.ellipse([(cx - circle_r, cy - circle_r), (cx + circle_r, cy + circle_r)], 
                 fill=(255, 255, 255, 200))
    draw.ellipse([(cx - circle_r, cy - circle_r), (cx + circle_r, cy + circle_r)], 
                 outline=border, width=2)
    # Draw number
    num_text = str(phase_num)
    nw, nh = text_bbox(draw, num_text, font_phase)
    draw.text((cx - nw // 2, cy - nh // 2 - 1), num_text, fill=border, font=font_phase)
    
    # Title text (white, bold)
    tw, th = text_bbox(draw, title, font_phase)
    draw.text((x + 40, y + (header_h - th) // 2 - 1), title, fill=(255, 255, 255), font=font_phase)
    
    # Items
    item_y = y + header_h + 10
    for item in items:
        item_str = item
        is_bold = item.startswith("•")
        fnt = font_item if not is_bold else font_item
        
        # Check if item has italic part (marked with *...*)
        if item.startswith("• "):
            text_part = item[2:]
            if "*" in text_part:
                # Split by asterisks
                parts = text_part.split("*")
                x_pos = x + 14
                for i, part in enumerate(parts):
                    if part:
                        f = font_italic if i % 2 == 1 else font_item
                        draw.text((x_pos, item_y), part, fill=(40, 40, 40), font=f)
                        pw, _ = text_bbox(draw, part, f)
                        x_pos += pw
            else:
                draw.text((x + 14, item_y), text_part, fill=(40, 40, 40), font=font_item)
        else:
            draw.text((x + 14, item_y), item, fill=(40, 40, 40), font=font_item)
        
        item_y += 18

    return item_y

def draw_arrow(draw, x1, y1, x2, y2, color=(100, 100, 100), lw=2):
    """Draw arrow from (x1,y1) to (x2,y2)."""
    draw.line([(x1, y1), (x2, y2)], fill=color, width=lw)
    # Arrowhead
    arrow_size = 10
    # Calculate angle
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    # Arrowhead points
    ax1 = x2 - arrow_size * math.cos(angle - 0.4)
    ay1 = y2 - arrow_size * math.sin(angle - 0.4)
    ax2 = x2 - arrow_size * math.cos(angle + 0.4)
    ay2 = y2 - arrow_size * math.sin(angle + 0.4)
    draw.polygon([(x2, y2), (ax1, ay1), (ax2, ay2)], fill=color)


# ─── LAYOUT ─────────────────────────────────────────────────────────────────

# Title
title1 = "KERANGKA KONSEPTUAL PENELITIAN"
title2 = "Hybrid Pipeline IndoBERT–GMM–LLM untuk Optimalisasi Rekrutmen ITSNU Pekalongan"

t1w, t1h = text_bbox(draw, title1, font_title)
draw.text((WIDTH // 2 - t1w // 2, 15), title1, fill=(20, 20, 20), font=font_title)
t2w, t2h = text_bbox(draw, title2, font_subtitle)
draw.text((WIDTH // 2 - t2w // 2, 15 + t1h + 4), title2, fill=(60, 60, 60), font=font_subtitle)

# Input box (Data PMB)
input_y = 70
input_w, input_h = 220, 45
input_x = WIDTH // 2 - input_w // 2
draw.rounded_rectangle(
    [(input_x, input_y), (input_x + input_w, input_y + input_h)],
    radius=8, fill=(245, 245, 245), outline=(80, 80, 80), width=2
)
# Input label
draw.text((input_x + 10, input_y + 5), "INPUT:", fill=(80, 80, 80), font=font_phase)
draw.text((input_x + 10, input_y + 22), "Data PMB ITSNU Pekalongan 2019–2024", 
          fill=(30, 30, 30), font=font_item)

# Arrow from input to phase 1
arrow_from_y = input_y + input_h

# Phase boxes layout
box_w = 290
box_h = 280
gap = 30
total_width = 4 * box_w + 3 * gap
start_x = (WIDTH - total_width) // 2
phase_y = arrow_from_y + 25

# Horizontal arrows between phases
arrow_y = phase_y + box_h // 2

# Draw phases
phases = [
    ("FASE 1", "Ekstraksi Fitur", "blue", [
        "• Text Preprocessing",
        "• IndoBERT Embedding",
        "  (768-dimensi)",
        "• PCA Dimensionality",
        "  Reduction (95%)",
        "• StandardScaler",
    ]),
    ("FASE 2", "Segmentasi Prob.", "green", [
        "• GMM Clustering",
        "  (k-means++, full cov)",
        "• 6 Periode (2019–2024)",
        "• Time Series Analysis",
        "  (ARI / Jaccard)",
        "• Structural Break",
    ]),
    ("FASE 3", "Otomasi LLM", "orange", [
        "• Llama 3.2 3B (Ollama)",
        "• Persona Generation",
        "• Causal Reasoning",
        "• Ringkasan Naratif",
        "• Strategi Personalisasi",
    ]),
    ("FASE 4", "Validasi Expert", "purple", [
        "• Expert-in-the-Loop",
        "  (Human-in-the-Loop)",
        "• Validasi Tim PMB",
        "• Kalibrasi Output AI",
        "• Implikasi Kebijakan",
        "  Institusional",
    ]),
]

phase_boxes = []
for i, (label, title, key, items) in enumerate(phases):
    x = start_x + i * (box_w + gap)
    draw_phase_box(draw, x, phase_y, box_w, box_h, title, items, key)
    phase_boxes.append((x, x + box_w))
    # Phase label at bottom
    lw, lh = text_bbox(draw, label, font_phase)
    draw.text((x + box_w // 2 - lw // 2, phase_y + box_h + 6), label, 
              fill=COLORS[key], font=font_phase)

# Draw horizontal arrows between phases
for i in range(3):
    x1 = phase_boxes[i][1]
    x2 = phase_boxes[i + 1][0]
    draw_arrow(draw, x1 + 5, arrow_y, x2 - 5, arrow_y, color=(120, 120, 120))

# Arrow from fase 4 down to output
output_arrow_y = phase_y + box_h + 30

# Output box
output_w, output_h = 260, 50
output_x = WIDTH // 2 - output_w // 2
output_y = output_arrow_y + 15

# Arrow from phase 4 to output
draw_arrow(draw, phase_boxes[3][0] + box_w // 2, phase_y + box_h + 22,
           output_x + output_w // 2, output_y - 5, color=(120, 120, 120))

# Arrow from phase 1-2-3 to output (showing all feed into output)
# Draw a bracket-like connector
for i in range(4):
    bx = phase_boxes[i][0] + box_w // 2
    by = phase_y + box_h
    draw.line([(bx, by), (bx, by + 15)], fill=(160, 160, 160), width=1)

# Horizontal connector
connector_y = phase_y + box_h + 15
draw.line([(phase_boxes[0][0] + box_w // 2, connector_y), 
           (phase_boxes[3][0] + box_w // 2, connector_y)], 
          fill=(160, 160, 160), width=1)

# Down to output
draw.line([(WIDTH // 2, connector_y), (WIDTH // 2, output_y - 5)], 
          fill=(160, 160, 160), width=2)
# Arrowhead
draw.polygon([
    (WIDTH // 2, output_y - 1),
    (WIDTH // 2 - 6, output_y - 10),
    (WIDTH // 2 + 6, output_y - 10)
], fill=(160, 160, 160))

# Draw output box
draw.rounded_rectangle(
    [(output_x, output_y), (output_x + output_w, output_y + output_h)],
    radius=8, fill=(245, 245, 245), outline=(41, 128, 185), width=2
)
draw.text((output_x + 10, output_y + 5), "OUTPUT:", fill=(41, 128, 185), font=font_phase)
draw.text((output_x + 10, output_y + 24), "Strategi Rekrutmen Prediktif 2025", 
          fill=(30, 30, 30), font=font_item)

# Source text at bottom
source_text = "Sumber: Kerangka konseptual penelitian, diadaptasi dari Scrucca et al. (2024), Koto et al. (2020), dan Grattafiori et al. (2024)"
sw, sh = text_bbox(draw, source_text, font_source)
draw.text((WIDTH // 2 - sw // 2, HEIGHT - 22), source_text, fill=(100, 100, 100), font=font_source)

# ─── SAVE ───────────────────────────────────────────────────────────────────

img.save(OUTPUT_PNG, "PNG")
print(f"✅ Diagram saved: {OUTPUT_PNG} ({img.size[0]}x{img.size[1]}px, {os.path.getsize(OUTPUT_PNG) / 1024:.0f}KB)")

# ─── REPLACE IN DOCX ───────────────────────────────────────────────────────

print("\n🔷 Replacing image in DOCX...")

# Backup original
shutil.copy2(DOCX_PATH, DOCX_BAK)
print(f"✅ Backup created: {DOCX_BAK}")

# Read new image
with open(OUTPUT_PNG, "rb") as f:
    new_img_data = f.read()

# Open and modify DOCX
modified = False
with zipfile.ZipFile(DOCX_PATH, "r") as zin:
    docx_data = {}
    for item in zin.namelist():
        docx_data[item] = zin.read(item)

# Replace image2.png
if "word/media/image2.png" in docx_data:
    old_size = len(docx_data["word/media/image2.png"])
    docx_data["word/media/image2.png"] = new_img_data
    new_size = len(new_img_data)
    print(f"✅ Replaced word/media/image2.png: {old_size} bytes → {new_size} bytes")
    modified = True
else:
    print(f"❌ word/media/image2.png not found in DOCX!")
    # Try to find any image2*
    for key in docx_data:
        if "image2" in key:
            print(f"   Found alternative: {key}")

# Update EMU dimensions in document.xml if needed
# New image is 1417x800, display width same (14.29cm = 5143500 EMU)
# New display height = 800/1417 * 5143500 = 2904143 EMU
if modified:
    doc_xml = docx_data["word/document.xml"].decode("utf-8")
    
    # Find the specific extent for rId9 (image2)
    # The pattern is: wp:extent with cx=5143500 and cy=2038350
    old_extent = 'cx="5143500" cy="2038350"'
    new_extent = 'cx="5143500" cy="2904000"'  # Adjusted for new aspect ratio
    if old_extent in doc_xml:
        doc_xml = doc_xml.replace(old_extent, new_extent)
        print(f"✅ Updated EMU dimensions: {old_extent} → {new_extent}")
    else:
        print(f"⚠️ Could not find exact EMU dimensions. Trying regex...")
        # Try regex for rId9 context
        doc_xml = re.sub(
            r'(r:embed="rId9")[^>]*wp:extent[^>]*cx="(\d+)"\s+cy="(\d+)"',
            lambda m: m.group(0).replace(f'cy="{m.group(3)}"', 'cy="2904000"'),
            doc_xml
        )
        print(f"✅ Updated EMU dimensions via regex")
    
    # Update description text: "tiga lapisan fungsional" → "empat fase fungsional"
    old_text = 'tiga lapisan fungsional yang bekerja secara berurutan">'
    new_text = 'empat fase fungsional yang bekerja secara berurutan dalam pipeline hybrid">'
    if old_text in doc_xml:
        doc_xml = doc_xml.replace(old_text, new_text)
        print(f"✅ Updated description: 'tiga lapisan fungsional' → 'empat fase fungsional'")
    else:
        # Try without the closing tag
        old_text2 = 'tiga lapisan fungsional yang bekerja secara berurutan'
        new_text2 = 'empat fase fungsional yang bekerja secara berurutan dalam pipeline hybrid'
        if old_text2 in doc_xml:
            doc_xml = doc_xml.replace(old_text2, new_text2)
            print(f"✅ Updated description (v2)")
        else:
            print(f"⚠️ Could not find text: '{old_text2}'")
            for m in re.finditer(r'tiga lapisan fungsional', doc_xml):
                print(f"   Found at position {m.start()}: ...{doc_xml[m.start()-30:m.end()+80]}...")
    
    # Simple replacements for layer names (these are single w:t elements)
    replacements = [
        ("Lapisan pertama", "Fase pertama"),
        ("Lapisan kedua", "Fase kedua"),
        ("Lapisan ketiga", "Fase ketiga"),
    ]
    for old, new in replacements:
        if old in doc_xml:
            doc_xml = doc_xml.replace(old, new)
            print(f"✅ Replaced '{old}' → '{new}'")
        else:
            print(f"⚠️ Could not find '{old}'")
    
    # Add 4th phase description after phase 3 ends
    # Phase 3 ends with "strategi rekrutmen prediktif 2025." 
    old_end = 'strategi rekrutmen prediktif 2025'
    if old_end in doc_xml:
        # The text may be followed by </w:t> or .
        fase4_text = ' 2025. Fase keempat adalah validasi expert: output LLM divalidasi oleh Tim PMB ITSNU Pekalongan melalui kerangka Expert-in-the-Loop, menghasilkan kalibrasi output AI dan implikasi kebijakan institusional yang kontekstual.'
        doc_xml = doc_xml.replace(old_end + '.', fase4_text)
        print(f"✅ Added Fase 4 description")
    else:
        print(f"⚠️ Could not find 'strategi rekrutmen prediktif 2025'")
        for m in re.finditer(r'strategi rekrutmen prediktif', doc_xml):
            print(f"   Found at position {m.start()}: ...{doc_xml[m.start():m.end()+100]}...")
    
    docx_data["word/document.xml"] = doc_xml.encode("utf-8")

# Write updated DOCX
output_docx = DOCX_PATH  # overwrite original (we have backup)
with zipfile.ZipFile(output_docx, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in docx_data:
        zout.writestr(item, docx_data[item])

print(f"\n✅ DOCX updated: {output_docx}")
print(f"   New file size: {os.path.getsize(output_docx) / 1024:.0f} KB")

# ─── VERIFICATION ───────────────────────────────────────────────────────────

print("\n🔷 Verification:")
with zipfile.ZipFile(output_docx, "r") as z:
    info = z.getinfo("word/media/image2.png")
    print(f"   image2.png in DOCX: {info.file_size} bytes ({info.compress_size} bytes compressed)")

# Check doc still valid
try:
    test_zip = zipfile.ZipFile(output_docx, "r")
    test_zip.testzip()
    test_zip.close()
    print(f"✅ DOCX archive is valid (no corruption)")
except Exception as e:
    print(f"❌ DOCX archive corrupted: {e}")

print(f"\n📋 Summary:")
print(f"   - New diagram: {OUTPUT_PNG}")
print(f"   - DOCX backup: {DOCX_BAK}")
print(f"   - Updated DOCX: {output_docx}")
print(f"   - Changes: image replacement, EMU dimension update, text update")
