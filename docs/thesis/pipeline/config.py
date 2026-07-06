from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.parent.resolve()

DEFAULT_DOC_BAB_1_4 = SCRIPT_DIR / 'BAB I - BAB IV.docx'
DEFAULT_DOC_THESIS = SCRIPT_DIR / 'Tesis_ITSNU_v10_Final.docx'

FRONT_MATTER_PATH = SCRIPT_DIR / 'front_matter' / 'FRONT_MATTER_DRAFT.docx'
BIB_PATH = SCRIPT_DIR / 'reference' / 'referensi_MENDELEY_OPTIMIZED.bib'

# ─── Format Constants ───
PAPER_SIZE = (21, 29.7)
MARGIN_TOP = 4
MARGIN_BOTTOM = 3
MARGIN_LEFT = 4
MARGIN_RIGHT = 3

FONT_BODY = 'Times New Roman'
FONT_SIZE_BODY = 12
FONT_SIZE_TABLE = 10
FONT_SIZE_ABSTRAK = 12  # v3: TNR 12 (was 11 in v1.7)

LINE_SPACING_BODY = 480
LINE_SPACING_BIB = 240
LINE_SPACING_CAPTION = 240
LINE_SPACING_ABSTRAK = 240  # v3: 1 spasi

SPACE_AFTER_BODY = 0
SPACE_BEFORE_BODY = 0
SPACE_AFTER_CAPTION = 240  # v3: 1 spasi (was 3 spasi/720 in v1.7)
SPACE_BEFORE_CAPTION = 0

FIRST_LINE_INDENT = 720
HANGING_INDENT = 720

LATIN_PHRASES = [
    'a priori', 'de facto', 'per se', 'in vitro', 'in vivo',
    'ad hoc', 'ad infinitum', 'et seq', 'bona fide', 'ceteris paribus',
    'cum laude', 'et cetera', 'ex officio', 'per annum', 'per capita',
    'vice versa', 'circa', 'de jure', 'a posteriori',
]

STD_BORDERS = ['top', 'bottom', 'insideH']
BORDER_PROPS = {
    'top': {'val': 'single', 'sz': '4', 'space': '0', 'color': 'auto'},
    'left': {'val': 'single', 'sz': '4', 'space': '0', 'color': 'auto'},
    'bottom': {'val': 'single', 'sz': '4', 'space': '0', 'color': 'auto'},
    'right': {'val': 'single', 'sz': '4', 'space': '0', 'color': 'auto'},
    'insideH': {'val': 'single', 'sz': '4', 'space': '0', 'color': 'auto'},
    'insideV': {'val': 'single', 'sz': '4', 'space': '0', 'color': 'auto'},
}

ORPHAN_MARKS = ['Rai, K. D.']

# ─── BAB V Constants ───
BAB5_SECTIONS = [
    '5.1 Simpulan',
    '5.2 Implikasi',
    '5.3 Keterbatasan Penelitian',
    '5.4 Saran',
]
BAB5_TARGET_WORDS = 500
BAB5_TARGET_CITES = 2
BAB5_HEADINGS = ['BAB V', 'KESIMPULAN DAN SARAN']
BAB5_H2_REQUIRED = ['5.1 Simpulan', '5.4 Saran']
BAB5_H2_OPTIONAL = ['5.2 Implikasi', '5.3 Keterbatasan Penelitian']
