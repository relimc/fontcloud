#!/usr/bin/env python3
"""
字体处理命令行工具
用法:
    python cli.py <字体文件或目录> [选项]
    python cli.py --sync-db
    python cli.py --generate-masks <图片目录> [--mask-target <目标目录>] [--mask-delete] [--mask-size <尺寸>]
"""
import os
import sys
import argparse
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import DEFAULT_INPUT_PATH, DEFAULT_OUTPUT_DIR, DEFAULT_GENERATE_PREVIEW, DEFAULT_EXPORT_JSON, PREVIEWS_DIR
from core.utils import find_font_files
from core.db_sync import sync_metadata_to_db
from core.preview_generator import preprocess_mask_image
from config import FONTS_DIR, JSONS_DIR, MASK_PRESETS_DIR
from PIL import Image
import tempfile
from pathlib import Path
from core.process_font import process_font
from core.db_sync import sync_single_font
import shutil
from web.routes import get_db_connection
from dotenv import load_dotenv
load_dotenv()

def batch_generate_masks(source_dir: str, target_dir: str, delete_original: bool = False, size: int = 800):
    """
    批量将 source_dir 中的图片转换为蒙版，保存到 target_dir。
    支持递归扫描子目录。
    """
    source = Path(source_dir)
    target = Path(target_dir)
    if not source.exists():
        print(f"错误: 源目录不存在 {source}")
        return
    target.mkdir(parents=True, exist_ok=True)

    exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
    image_files = []
    for ext in exts:
        image_files.extend(source.rglob(f'*{ext}'))
    if not image_files:
        print(f"未找到任何图片文件在 {source}")
        return

    success_count = 0
    fail_count = 0
    for img_path in image_files:
        if '_mask' in img_path.stem:
            continue
        try:
            # 使用临时文件处理，避免污染源目录
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_img = Path(tmpdir) / img_path.name
                shutil.copy2(img_path, tmp_img)
                mask_array = preprocess_mask_image(str(tmp_img), size=size, delete_original=False)
                output_name = f"{img_path.stem}_mask{img_path.suffix}"
                output_path = target / output_name
                Image.fromarray(mask_array).save(output_path)
                print(f"已生成蒙版: {output_path}")
                if delete_original:
                    img_path.unlink()
                    print(f"已删除原始图片: {img_path}")
            success_count += 1
        except Exception as e:
            print(f"处理 {img_path} 失败: {e}")
            fail_count += 1

    print(f"\n批量生成蒙版完成: 成功 {success_count} 个，失败 {fail_count} 个。")


def sync_from_fonts(force=False):
    """
    以 data/fonts 目录下的字体文件为准，同步数据库：
    - 对每个字体文件，确保数据库中有对应记录（生成预览图、JSON 并同步）
    - 删除数据库中孤立记录（字体文件不存在）
    """
    from core.process_font import process_font
    from core.db_sync import sync_single_font

    font_files = list(FONTS_DIR.glob("**/*.ttf")) + list(FONTS_DIR.glob("**/*.otf")) + \
                 list(FONTS_DIR.glob("**/*.ttc")) + list(FONTS_DIR.glob("**/*.otc"))
    if not font_files:
        print("data/fonts 目录下未找到任何字体文件。")
        return

    print(f"找到 {len(font_files)} 个字体文件，开始处理...")
    db_font_names = set()
    processed = 0

    # 第一步：处理所有字体文件
    for font_file in font_files:
        font_name_with_ext = font_file.name  # 完整文件名（含扩展名）
        db_font_names.add(font_name_with_ext)

        # 检查数据库是否已有记录
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT font_name FROM font_metadata WHERE font_name = %s", (font_name_with_ext,))
                exists = cursor.fetchone() is not None
        finally:
            conn.close()

        if exists and not force:
            print(f"字体 {font_name_with_ext} 已存在，跳过处理（使用 --force 强制重新生成）")
            continue

        print(f"处理字体: {font_file}")
        success, error_msg, new_basename = process_font(
            str(font_file),
            str(FONTS_DIR),
            generate_preview_flag=True,
            export_json_flag=True,
            copy_font=False  # 文件已在 fonts 目录，无需复制
        )
        if success:
            # 同步到数据库
            json_path = JSONS_DIR / f"{font_name_with_ext}_metadata.json"
            if json_path.exists():
                sync_single_font(json_path)
                print(f"已同步: {font_name_with_ext}")
            else:
                print(f"警告: 未找到 JSON 文件 {json_path}")
        else:
            print(f"处理失败: {error_msg}")
        processed += 1

    # 第二步：清理数据库孤立记录
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT font_name FROM font_metadata")
            all_db_fonts = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    orphan_fonts = [name for name in all_db_fonts if name not in db_font_names]
    if orphan_fonts:
        print(f"发现 {len(orphan_fonts)} 个孤立记录（字体文件不存在），是否删除？(y/n)")
        confirm = input().strip().lower()
        if confirm == 'y':
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    for name in orphan_fonts:
                        cursor.execute("DELETE FROM font_metadata WHERE font_name = %s", (name,))
                        print(f"已删除数据库记录: {name}")
                        # 删除关联的预览图和 JSON 文件
                        preview_file = PREVIEWS_DIR / f"{name}_preview.png"
                        if preview_file.exists():
                            preview_file.unlink()
                        for lang in ['简','繁','日','韩','英']:
                            lang_preview = PREVIEWS_DIR / f"{name}_{lang}_preview.png"
                            if lang_preview.exists():
                                lang_preview.unlink()
                        json_file = JSONS_DIR / f"{name}_metadata.json"
                        if json_file.exists():
                            json_file.unlink()
                conn.commit()
            finally:
                conn.close()
        else:
            print("已取消删除。")
    else:
        print("没有孤立记录。")

    print(f"同步完成。处理了 {processed} 个字体。")


def main():
    parser = argparse.ArgumentParser(description="字体处理工具")
    parser.add_argument("input", nargs='?', default=None, help="字体文件或目录路径")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR, help=f"输出目录（默认 {DEFAULT_OUTPUT_DIR}）")
    parser.add_argument("--no-preview", dest="gen_preview", action="store_false", default=DEFAULT_GENERATE_PREVIEW, help="不生成预览图")
    parser.add_argument("--no-json", dest="export_json", action="store_false", default=DEFAULT_EXPORT_JSON, help="不导出元数据 JSON")
    parser.add_argument("--sync-db", action="store_true", help="仅同步 JSON 到数据库，不处理字体")
    parser.add_argument("--copy", action="store_true", help="复制字体文件到输出目录（默认不复制）")
    parser.add_argument("--workers", type=int, default=None, help="并发线程数（默认为 CPU 核心数）")
    parser.add_argument("--sync-from-fonts", action="store_true",
                        help="以 data/fonts 下的字体文件为准同步数据库，生成预览图和 JSON")
    parser.add_argument("--force", action="store_true", help="强制重新处理所有字体（即使数据库已存在）")
    # 批量生成蒙版参数
    parser.add_argument("--generate-masks", type=str, default=None, help="批量生成蒙版图片：指定原始图片目录")
    parser.add_argument("--mask-target", type=str, default=str(MASK_PRESETS_DIR), help="蒙版目标目录（默认 data/masks/mask_presets）")
    parser.add_argument("--mask-delete", action="store_true", help="生成蒙版后删除原始图片")
    parser.add_argument("--mask-size", type=int, default=800, help="蒙版尺寸（默认 800）")

    args = parser.parse_args()

    # 批量生成蒙版模式
    if args.generate_masks:
        batch_generate_masks(args.generate_masks, args.mask_target, args.mask_delete, args.mask_size)
        return

    # 数据库同步模式
    if args.sync_db:
        sync_metadata_to_db(str(JSONS_DIR))
        return

    if args.sync_from_fonts:
        sync_from_fonts(force=args.force)
        return

    # 字体处理模式
    input_path = args.input if args.input is not None else DEFAULT_INPUT_PATH
    if input_path is None:
        print("错误: 未指定输入路径，且未配置默认路径。")
        sys.exit(1)
    if not os.path.exists(input_path):
        print(f"错误: 输入路径不存在 {input_path}")
        sys.exit(1)

    font_files = find_font_files(input_path)
    if not font_files:
        print("未找到任何字体文件。")
        return

    workers = args.workers if args.workers else multiprocessing.cpu_count()
    print(f"找到 {len(font_files)} 个字体文件，使用 {workers} 个线程并发处理...")

    errors = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for font_file in font_files:
            future = executor.submit(
                process_font,
                str(font_file),
                str(FONTS_DIR),
                args.gen_preview,
                args.export_json,
                copy_font=args.copy
            )
            futures.append((font_file, future))

        for font_file, future in futures:
            try:
                success, error_msg, _ = future.result()
                if not success:
                    errors.append((font_file, error_msg))
            except Exception as e:
                errors.append((font_file, f"线程异常: {str(e)}"))

    if errors:
        print("\n" + "=" * 60)
        print(f"共 {len(errors)} 个字体处理失败:")
        for f, err in errors:
            print(f"  {f}: {err}")
        from pathlib import Path
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "failed_fonts.log"
        with open(log_file, "w", encoding="utf-8") as log:
            for f, err in errors:
                log.write(f"{f}\t{err}\n")
        print(f"\n失败详情已保存到 {log_file}")
    else:
        print("\n所有字体处理成功！")

    print("\n全部处理完成。")

if __name__ == "__main__":
    main()