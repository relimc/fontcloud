import re
import os
from pathlib import Path
from fontTools.ttLib import TTFont, TTLibFileIsCollectionError
from config import INVALID_FILENAME_CHARS

def sanitize_filename(name: str) -> str:
    name = re.sub(INVALID_FILENAME_CHARS, "_", name)
    name = name.strip(". ")
    if not name:
        name = "unknown"
    return name

def open_font_safe(font_path: str):
    try:
        return TTFont(font_path, fontNumber=0)
    except TTLibFileIsCollectionError:
        return TTFont(font_path, fontNumber=0)
    except Exception as e:
        raise RuntimeError(f"无法打开字体文件: {e}")

def find_font_files(path: str) -> list[Path]:
    path = Path(path)
    if path.is_file():
        if path.suffix.lower() in (".ttf", ".otf", ".ttc", ".otc"):
            return [path]
        else:
            print(f"跳过非字体文件: {path}")
            return []
    elif path.is_dir():
        font_files = []
        for ext in ("*.ttf", "*.otf", "*.ttc", "*.otc"):
            font_files.extend(path.rglob(ext))
        return font_files
    else:
        print(f"错误: 路径无效 {path}")
        return []

from core.font_parser import choose_preferred_name

def build_display_name_from_family_names(family_names: list, custom_info: dict = None, font_weight: str = '') -> str:
    if custom_info and custom_info.get('custom_font_name'):
        return custom_info['custom_font_name']
    # 优先选择中文等名称，避免英文名
    display_name = choose_preferred_name(family_names) or (family_names[0] if family_names else "Unknown")
    # 去除可能存在的扩展名（安全处理）
    if '.' in display_name:
        display_name = display_name.rsplit('.', 1)[0]
    if font_weight and font_weight.lower() != 'regular':
        if font_weight.lower() not in display_name.lower():
            display_name = f"{display_name} {font_weight}"
    return display_name