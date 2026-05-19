# metadata_exporter.py
import json
from config import PLATFORM_NAMES, MAC_ENCODING_NAMES, WIN_ENCODING_NAMES, MAC_LANG_NAMES, WIN_LANG_NAMES, NAME_ID_MAP
from core.font_parser import get_best_cmap, get_font_license_info, get_supported_languages
from core.utils import open_font_safe

def export_font_metadata(font_path: str, output_path: str, font_display_name: str):
    """
    导出字体完整元数据为 JSON 文件。
    font_display_name: 重命名后的字体名（含扩展名）
    """
    font = open_font_safe(font_path)
    try:
        name_tree = {}
        for record in font["name"].names:
            plat = record.platformID
            if plat not in (1, 3):
                continue
            plat_name = PLATFORM_NAMES.get(plat, f"platform_{plat}")
            if plat == 1:
                enc_name = MAC_ENCODING_NAMES.get(record.platEncID, f"enc_id_{record.platEncID}")
                lang_name = MAC_LANG_NAMES.get(record.langID, f"lang_{record.langID}")
            else:  # plat == 3
                enc_name = WIN_ENCODING_NAMES.get(record.platEncID, f"enc_id_{record.platEncID}")
                lang_name = WIN_LANG_NAMES.get(record.langID, f"lang_{record.langID}")
            name_id = record.nameID
            field_name = NAME_ID_MAP.get(name_id, f"name_id_{name_id}")
            try:
                value = record.toStr().strip()
                if not value:
                    continue
                name_tree.setdefault(plat_name, {}).setdefault(enc_name, {}).setdefault(lang_name, {})[field_name] = value
            except:
                continue

        cmap = get_best_cmap(font)
        total_chars = len(cmap)
        license_type, _ = get_font_license_info(font)
        commercial_license = "unknown" if license_type == "Unknown" else license_type.lower()
        supported_langs = get_supported_languages(font)

        metadata = {
            "font_name": font_display_name,   # 存储含扩展名的完整文件名
            **name_tree,
            "commercial_license": commercial_license,
            "total_characters": total_chars,
            "supported_languages": supported_langs,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"字体元数据已导出: {output_path}")
    finally:
        font.close()