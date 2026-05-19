import re
from fontTools.ttLib import TTFont
from config import NAME_ID_MAP, SUPPORTED_SCRIPTS

# ========== 基础解析函数 ==========
# def get_best_cmap(font: TTFont) -> dict:
#     cmap_tables = []
#     for table in font["cmap"].tables:
#         if table.isUnicode():
#             cmap_tables.append(table.cmap)
#     if not cmap_tables:
#         return {}
#     glyph_to_codes = {}
#     for cmap in cmap_tables:
#         for code, glyph in cmap.items():
#             glyph_to_codes.setdefault(glyph, []).append(code)
#     best_cmap = {}
#     for glyph, codes in glyph_to_codes.items():
#         if len(codes) == 1:
#             best_cmap[codes[0]] = glyph
#         else:
#             best_cmap[codes[0]] = glyph
#     return best_cmap

def get_best_cmap(font: TTFont) -> dict:
    """获取最佳的 Unicode cmap 表"""
    return font.getBestCmap() or {}

def get_font_names_smart(font: TTFont) -> list[str]:
    raw_names = set()
    for record in font["name"].names:
        if record.nameID in (1, 16, 17):
            try:
                name = record.toStr().strip()
                if name:
                    # 清洗乱码和非常规字符
                    cleaned = re.sub(r'[^\w\u4e00-\u9fff\s\-\._/／\(\)，,]', '', name)
                    cleaned = cleaned.strip(' -_/／.')
                    if cleaned and not any(c in cleaned for c in "?'’£Ä\x00"):
                        raw_names.add(cleaned)
            except:
                continue
    if not raw_names:
        return ["unknown"]
    name_list = list(raw_names)
    to_remove = set()
    for i in range(len(name_list)):
        for j in range(i+1, len(name_list)):
            if name_list[i] in name_list[j]:
                to_remove.add(name_list[i])
            elif name_list[j] in name_list[i]:
                to_remove.add(name_list[j])
    final = [n for n in name_list if n not in to_remove]
    return final if final else ["unknown"]

def get_font_license_info(font: TTFont) -> tuple[str, str]:
    candidates = []
    for record in font["name"].names:
        if record.nameID in (13, 0):
            try:
                text = record.toStr().lower()
                if text:
                    candidates.append(text)
            except:
                pass
    full_text = " ".join(candidates)
    if not full_text:
        return ("Unknown", "授权信息不明")

    license_patterns = [
        (r"\b(sil|ofl|open font license)\b", "OFL"),
        (r"\b(gpl|gnu general public license)\b", "GPL"),
        (r"\b(lgpl|lesser general public license)\b", "LGPL"),
        (r"\b(agpl|affero general public license)\b", "AGPL"),
        (r"\bmit\s+license\b", "MIT"),
        (r"\b(bsd\s+license|bsd-style|bsd\s+2-clause|bsd\s+3-clause)\b", "BSD"),
        (r"\bapache\s+license\b", "Apache"),
        (r"\b(ubuntu font license|ufl)\b", "UFL"),
        (r"\b(ipa font license|ipa)\b", "IPA"),
        (r"\b(arphic public license)\b", "Arphic"),
        (r"\b(creative commons.*?by-sa)\b", "CC-BY-SA"),
        (r"\b(creative commons.*?by)\b", "CC-BY"),
        (r"\b(cc0)\b", "CC0"),
        (r"\b(mozilla public license)\b", "MPL"),
        (r"\b(eclipse public license)\b", "EPL"),
        (r"\b(artistic license)\b", "Artistic"),
        (r"\b(zlib/libpng license)\b", "Zlib"),
        (r"\b(iscl? license)\b", "ISC"),
        (r"\b(wtfpl)\b", "WTFPL"),
        (r"\b(unicode license)\b", "Unicode"),
        (r"\b(free|opensource|open source)\b", "Free"),
    ]

    for pattern, license_name in license_patterns:
        if re.search(pattern, full_text):
            if license_name != "Free":
                return (license_name, full_text)
    if re.search(r"\b(free|opensource|open source)\b", full_text):
        return ("Free", full_text)
    return ("Unknown", full_text)

def get_font_weight(font: TTFont) -> str:
    for record in font["name"].names:
        if record.nameID == 17:
            try:
                weight = record.toStr().strip()
                if weight:
                    return weight
            except:
                pass
    for record in font["name"].names:
        if record.nameID == 2:
            try:
                weight = record.toStr().strip()
                if weight:
                    return weight
            except:
                pass
    return "Regular"

def get_pil_encoding(font: TTFont) -> str | None:
    for table in font["cmap"].tables:
        if table.platformID == 3:
            if table.platEncID == 1:
                return None
            elif table.platEncID == 2:
                return "sjis"
            elif table.platEncID == 3:
                return "gb"
            elif table.platEncID == 4:
                return "big5"
            elif table.platEncID == 5:
                return "wans"
    for table in font["cmap"].tables:
        if table.isUnicode():
            return None
    return None

# ========== 获取支持的语言脚本 ==========
def get_supported_scripts(font: TTFont, cmap: dict) -> list[dict]:
    def char_supported(char: str) -> bool:
        return ord(char) in cmap
    def script_supported(ranges):
        for start, end in ranges:
            for code in range(start, end+1):
                if code in cmap:
                    return True
        return False
    def build_sample_text(sample, ranges):
        filtered = "".join(ch for ch in sample if char_supported(ch))
        if filtered:
            return filtered
        dynamic = []
        for start, end in ranges:
            for code in range(start, end+1):
                if code in cmap:
                    dynamic.append(chr(code))
                    if len(dynamic) >= 8:
                        break
            if len(dynamic) >= 8:
                break
        return "".join(dynamic)
    supported = []
    for script in SUPPORTED_SCRIPTS:
        if script_supported(script["ranges"]):
            sample_text = build_sample_text(script["sample"], script["ranges"])
            if sample_text:
                supported.append({"name": script["name"], "sample": sample_text})
    return supported

def choose_preferred_name(family_names: list[str]) -> str:
    def has_chinese(s): return any('\u4e00' <= c <= '\u9fff' for c in s)
    def has_japanese(s): return any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in s)
    def has_korean(s): return any('\uac00' <= c <= '\ud7af' for c in s)
    def has_english(s): return any('a' <= c.lower() <= 'z' for c in s)
    for name in family_names:
        if has_chinese(name): return name
    for name in family_names:
        if has_japanese(name): return name
    for name in family_names:
        if has_korean(name): return name
    for name in family_names:
        if has_english(name): return name
    return family_names[0] if family_names else "Unknown"

# ========== 语言支持检测（基于样本集和阈值） ==========
LANG_SAMPLES = {
    '简': [
        '的', '一', '是', '了', '我', '不', '人', '在', '他', '有', '这', '个', '上', '们', '来', '到', '说', '去', '和', '看',
        '中', '大', '为', '子', '你', '得', '生', '学', '法', '年', '出', '那', '要', '于', '就', '下', '进', '也', '家', '用'
    ],
    '繁': [
        '這', '個', '們', '來', '到', '說', '去', '為', '學', '於', '進', '體', '關', '係', '時', '間', '動', '機', '會', '過',
        '開', '關', '門', '問', '題', '點', '當', '對', '從', '後', '兩', '還', '麼', '沒', '實', '現', '書', '寫', '讀', '風'
    ],
    '日': [
        'の', 'に', 'は', 'を', 'た', 'が', 'で', 'ま', 'す', 'な', 'い', 'こ', 'と', 'し', 'て', 'い', 'も', 'か', 'よ', 'う', 'れ',
        'あ', 'い', 'う', 'え', 'お', 'か', 'き', 'く', 'け', 'こ', 'さ', 'し', 'す', 'せ', 'そ', '日', '本', '語'
    ],
    '韩': [
        '이', '그', '저', '것', '수', '년', '일', '월', '하', '지', '않', '었', '겠', '습', '니', '다', '요', '한', '국', '어',
        '안', '녕', '사', '랑', '해', '요', '나', '가', '고', '싶', '다'
    ],
    '英': [
        'a','b','c','d','e','f','g','h','i','j','k','l','m',
        'n','o','p','q','r','s','t','u','v','w','x','y','z',
        'A','B','C','D','E','F','G','H','I','J','K','L','M',
        'N','O','P','Q','R','S','T','U','V','W','X','Y','Z'
    ]
}
LANG_THRESHOLD = 0.7

def is_language_supported(font: TTFont, lang_code: str) -> bool:
    cmap = get_best_cmap(font)
    samples = LANG_SAMPLES.get(lang_code, [])
    if not samples:
        return False
    supported_count = 0
    for ch in samples:
        if len(ch) != 1:
            continue
        if ord(ch) in cmap:
            supported_count += 1
    ratio = supported_count / len(samples)
    return ratio >= LANG_THRESHOLD

def get_supported_languages(font: TTFont) -> str:
    order = ['简', '繁', '日', '韩', '英']
    supported = []
    for lang in order:
        if is_language_supported(font, lang):
            supported.append(lang)
    return ''.join(supported)

# SUPPORTED_SCRIPTS 需要从 config 导入，这里假定已在 config 中定义
from config import SUPPORTED_SCRIPTS