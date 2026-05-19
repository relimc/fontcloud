import shutil
from pathlib import Path
from config import FONTS_DIR, PREVIEWS_DIR, JSONS_DIR
from core.utils import open_font_safe, sanitize_filename
from core.font_parser import get_font_names_smart, get_supported_languages
from core.preview_generator import generate_preview, generate_lang_preview
from core.metadata_exporter import export_font_metadata

def process_font(font_path: str, output_dir: str, generate_preview_flag: bool, export_json_flag: bool, copy_font: bool = False):
    """
    处理单个字体文件，返回 (success, error_msg, new_basename)
    """
    created_files = []
    font_path = Path(font_path)
    new_basename = None

    try:
        if not font_path.is_file():
            raise FileNotFoundError(f"文件不存在 {font_path}")

        # 1. 解析字体
        font = open_font_safe(str(font_path))
        family_names = sorted(get_font_names_smart(font))
        supported_langs_str = get_supported_languages(font)
        font.close()

        # 2. 新文件名
        new_basename = sanitize_filename("／".join(family_names))
        ext = font_path.suffix.lower()
        if ext not in (".ttf", ".otf", ".ttc", ".otc"):
            print(f"警告: 未知字体扩展名 {ext}，仍将尝试处理")
        new_font_name = f"{new_basename}{ext}"
        output_font_path = FONTS_DIR / new_font_name

        if copy_font:
            if output_font_path.exists():
                output_font_path.unlink()
            shutil.copy2(font_path, output_font_path)
            created_files.append(output_font_path)
            print(f"字体已复制并重命名: {output_font_path}")
        else:
            print(f"跳过复制字体，重命名后的名称应为: {new_font_name}")

        # 3. 预览图
        if generate_preview_flag:
            preview_path = PREVIEWS_DIR / f"{output_font_path.stem}_preview.png"
            if preview_path.exists():
                preview_path.unlink()
            generate_preview(str(font_path), str(preview_path), new_basename)
            created_files.append(preview_path)

            lang_order = ['简', '繁', '日', '韩', '英']
            for lang in lang_order:
                if lang in supported_langs_str:
                    lang_preview_path = PREVIEWS_DIR / f"{output_font_path.stem}_{lang}_preview.png"
                    if lang_preview_path.exists():
                        lang_preview_path.unlink()
                    generate_lang_preview(str(font_path), str(lang_preview_path), lang)
                    created_files.append(lang_preview_path)

        # 4. JSON 元数据
        if export_json_flag:
            json_path = JSONS_DIR / f"{output_font_path.name}_metadata.json"
            if json_path.exists():
                json_path.unlink()
            export_font_metadata(str(font_path), str(json_path), output_font_path.name)
            created_files.append(json_path)

        return (True, None, output_font_path.name)   # 返回完整文件名（含扩展名）

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"处理 {font_path} 时出错: {error_msg}")
        for f in created_files:
            if f.exists():
                f.unlink()
                print(f"已回滚删除: {f}")
        return (False, error_msg, None)