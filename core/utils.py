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