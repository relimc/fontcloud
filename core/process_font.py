# core/process_font.py
import shutil
from pathlib import Path
from config import FONTS_DIR, PREVIEWS_DIR, JSONS_DIR
from core.utils import open_font_safe, sanitize_filename, build_display_name_from_family_names
from core.font_parser import get_font_names_smart, get_supported_languages, get_font_weight
from core.preview_generator import generate_preview, generate_lang_preview, generate_font_title_preview
from core.metadata_exporter import export_font_metadata

def process_font(font_path: str, output_dir: str, generate_preview_flag: bool, export_json_flag: bool, copy_font: bool = False):
    """
    处理单个字体文件，返回 (success: bool, error_msg: str, new_basename: str or None)
    """
    created_files = []
    font_path = Path(font_path)
    new_basename = None

    try:
        if not font_path.is_file():
            raise FileNotFoundError(f"文件不存在 {font_path}")

        # 打开字体获取信息
        font = open_font_safe(str(font_path))
        family_names = sorted(get_font_names_smart(font))
        weight = get_font_weight(font)
        supported_langs_str = get_supported_languages(font)
        font.close()

        # 生成基础名称
        new_basename = sanitize_filename("／".join(family_names))
        # 附加字重（避免重复）
        if weight and weight.lower() != 'regular':
            weight_clean = weight.lower().replace(' ', '')
            basename_clean = new_basename.lower().replace(' ', '')
            if weight_clean not in basename_clean:
                new_basename = f"{new_basename}_{weight}"
                new_basename = sanitize_filename(new_basename)

        ext = font_path.suffix.lower()
        if ext not in (".ttf", ".otf", ".ttc", ".otc"):
            print(f"警告: 未知字体扩展名 {ext}，仍将尝试处理")
        new_font_name = f"{new_basename}{ext}"
        output_font_path = FONTS_DIR / new_font_name

        # 复制字体文件（可选）
        if copy_font:
            if output_font_path.exists():
                output_font_path.unlink()
                print(f"删除已存在的字体文件: {output_font_path}")
            shutil.copy2(font_path, output_font_path)
            created_files.append(output_font_path)
            print(f"字体已复制并重命名: {output_font_path}")
        else:
            print(f"跳过复制字体，重命名后的名称应为: {new_font_name}")

        # 生成预览图
        if generate_preview_flag:
            # 词云预览图（列表页用）
            preview_path = PREVIEWS_DIR / f"{output_font_path.stem}_preview.png"
            if preview_path.exists():
                preview_path.unlink()
            generate_preview(str(font_path), str(preview_path), new_basename)
            created_files.append(preview_path)

            # 多语言竖排预览图（详情页轮播）
            lang_order = ['简', '繁', '日', '韩', '英']
            for lang in lang_order:
                if lang in supported_langs_str:
                    lang_preview_path = PREVIEWS_DIR / f"{output_font_path.stem}_{lang}_preview.png"
                    if lang_preview_path.exists():
                        lang_preview_path.unlink()
                    generate_lang_preview(str(font_path), str(lang_preview_path), lang)
                    created_files.append(lang_preview_path)

            display_name_for_title = build_display_name_from_family_names(family_names, None, weight)
            title_preview_path_small = PREVIEWS_DIR / f"{output_font_path.stem}_title_small.png"
            generate_font_title_preview(str(font_path), str(title_preview_path_small), display_name_for_title)

        # 导出 JSON 元数据
        if export_json_flag:
            json_path = JSONS_DIR / f"{output_font_path.name}_metadata.json"
            if json_path.exists():
                json_path.unlink()
            export_font_metadata(str(font_path), str(json_path), output_font_path.name)
            created_files.append(json_path)

        return (True, None, new_basename)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"处理 {font_path} 时出错: {error_msg}")
        # 回滚：删除所有已创建的文件
        for f in created_files:
            if f.exists():
                f.unlink()
                print(f"已回滚删除: {f}")
        return (False, error_msg, None)