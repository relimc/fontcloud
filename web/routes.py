import json
import os
import tempfile
import shutil
import time
from pathlib import Path
from flask import render_template, request, jsonify, abort, send_file, current_app
import pymysql
from config import DB_CONFIG, PREVIEWS_DIR, TEMP_DIR, MASK_PRESETS_DIR, ICON_MASKS_DIR, FORCE_DOWNLOAD, ADMIN_USERNAME
from core.preview_generator import WordCloudGenerator, SHAPE_FUNCTIONS_DICT, preprocess_mask_image
from core.db_sync import sync_single_font
from core.font_parser import get_best_cmap, get_supported_scripts, get_font_license_info, get_font_weight, get_font_names_smart, choose_preferred_name, get_supported_languages
from core.utils import open_font_safe, sanitize_filename
from core.process_font import process_font  # 需要实现
from PIL import Image
from functools import wraps
from flask import request, Response, session
from flask import session, request, redirect, url_for, render_template
from functools import wraps
from config import ADMIN_USERNAME, ADMIN_PASSWORD


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def allowed_file(filename):
    return Path(filename).suffix.lower() in ('.ttf', '.otf', '.ttc', '.otc')

def register_routes(app):
    @app.route('/api/check-auth')
    def check_auth():
        print(session)
        if 'username' in session:
            return jsonify({'loggedIn': True})
        else:
            return jsonify({'loggedIn': False})

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login', methods=['POST'])
    def login():
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': '用户名或密码错误'}), 401

    @app.route('/logout')
    def logout():
        session.pop('username', None)
        return redirect(url_for('index'))

    @app.route('/detail/<path:font_name>')
    def detail_page(font_name):
        return render_template('detail.html', font_name=font_name)

    @app.route('/wordcloud-generator')
    def wordcloud_generator():
        return render_template('wordcloud.html')

    # ========== API 路由 ==========
    @app.route('/api/fonts')
    def api_fonts():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        offset = (page - 1) * per_page

        conn = get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                count_sql = "SELECT COUNT(*) as total FROM font_metadata"
                params = []
                if search:
                    count_sql += " WHERE font_name LIKE %s"
                    params.append(f"%{search}%")
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['total']

                sql = """
                    SELECT id, font_name, commercial_license, total_characters, metadata, supported_languages, custom_info, font_file_url
                    FROM font_metadata
                """
                if search:
                    sql += " WHERE font_name LIKE %s"
                sql += " ORDER BY id DESC LIMIT %s OFFSET %s"
                params += [per_page, offset]
                cursor.execute(sql, params)
                rows = cursor.fetchall()

                fonts = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    display_name = row['font_name']
                    try:
                        if 'win' in metadata and 'enc_id_unicode_bmp' in metadata['win']:
                            for lang in ['cn','tw','en']:
                                if lang in metadata['win']['enc_id_unicode_bmp']:
                                    name_data = metadata['win']['enc_id_unicode_bmp'][lang]
                                    if 'font_family_name' in name_data:
                                        display_name = name_data['font_family_name']
                                        break
                    except:
                        pass
                    preview_path = f"/preview/{row['font_name']}_preview.png"
                    custom_info = json.loads(row['custom_info']) if row['custom_info'] else {}
                    custom_license = custom_info.get('custom_license', '')
                    final_license = custom_license if custom_license else row['commercial_license']
                    fonts.append({
                        'font_name': row['font_name'],
                        'display_name': display_name,
                        'commercial_license': row['commercial_license'],
                        'total_characters': row['total_characters'],
                        'supported_languages': row.get('supported_languages', ''),
                        'preview_url': preview_path,
                        'final_license': final_license,
                        'custom_info': custom_info
                    })
                return jsonify({
                    'fonts': fonts,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                })
        finally:
            conn.close()

    @app.route('/api/font/<path:font_name>')
    def api_font_detail(font_name):
        conn = get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = """
                    SELECT font_name, commercial_license, total_characters, 
                           supported_languages, metadata, custom_info, font_file_url
                    FROM font_metadata WHERE font_name = %s
                """
                cursor.execute(sql, (font_name,))
                row = cursor.fetchone()
                if not row:
                    abort(404)

                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                custom_info = json.loads(row['custom_info']) if row['custom_info'] else {}
                font_file_url = row.get('font_file_url')
                custom_download_link = custom_info.get('custom_download_link', '')

                # 最终许可证
                custom_license = custom_info.get('custom_license', '')
                final_license = custom_license if custom_license else row['commercial_license']
                is_open_source = final_license != 'unknown'
                if FORCE_DOWNLOAD:
                    final_download_link = custom_download_link if custom_download_link else font_file_url
                else:
                    if is_open_source:
                        final_download_link = custom_download_link if custom_download_link else font_file_url
                    else:
                        final_download_link = custom_download_link if custom_download_link else None

                # 字重
                default_weight = 'Regular'
                for plat in ['win','mac']:
                    if plat in metadata:
                        for enc, enc_data in metadata[plat].items():
                            for lang, fields in enc_data.items():
                                if 'typographic_subfamily_name' in fields:
                                    default_weight = fields['typographic_subfamily_name']
                                    break
                                elif 'font_subfamily_name' in fields:
                                    default_weight = fields['font_subfamily_name']
                                    break
                            else:
                                continue
                            break
                        else:
                            continue
                        break
                final_weight = custom_info.get('custom_font_weight') or default_weight

                # name_records
                name_records = {}
                for plat in ['mac','win']:
                    if plat in metadata:
                        for enc, enc_data in metadata[plat].items():
                            for lang, fields in enc_data.items():
                                key = f"{plat}/{enc}/{lang}"
                                name_records[key] = fields

                preview_url = f"/preview/{row['font_name']}_preview.png"
                chars_preview_url = f"/preview/{row['font_name']}_chars.png"

                return jsonify({
                    'font_name': row['font_name'],
                    'commercial_license': row['commercial_license'],
                    'final_license': final_license,
                    'total_characters': row['total_characters'],
                    'supported_languages': row.get('supported_languages', ''),
                    'font_weight': final_weight,
                    'download_link': final_download_link,
                    'custom_download_link': custom_download_link,
                    'font_file_url': font_file_url,
                    'preview_url': preview_url,
                    'chars_preview_url': chars_preview_url,
                    'name_records': name_records,
                    'raw_metadata': metadata,
                    'custom_info': custom_info,
                })
        finally:
            conn.close()

    @app.route('/api/font/<path:font_name>/update', methods=['POST'])
    @login_required
    def update_font_custom_info(font_name):
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效数据'}), 400

        custom_info = {
            'custom_font_name': data.get('custom_font_name', ''),
            'custom_download_link': data.get('custom_download_link', ''),
            'custom_font_weight': data.get('custom_font_weight', ''),
            'custom_license': data.get('custom_license', '')
        }
        new_license = data.get('commercial_license', None)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT font_name FROM font_metadata WHERE font_name = %s", (font_name,))
                if not cursor.fetchone():
                    return jsonify({'error': '字体不存在'}), 404
                cursor.execute(
                    "UPDATE font_metadata SET custom_info = %s WHERE font_name = %s",
                    (json.dumps(custom_info, ensure_ascii=False), font_name)
                )
                if new_license is not None:
                    cursor.execute(
                        "UPDATE font_metadata SET commercial_license = %s WHERE font_name = %s",
                        (new_license, font_name)
                    )
                conn.commit()
                return jsonify({'message': '更新成功', 'custom_info': custom_info})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    @app.route('/api/mask-presets')
    def mask_presets():
        presets = []
        if MASK_PRESETS_DIR.exists():
            for f in MASK_PRESETS_DIR.iterdir():
                if f.suffix.lower() in ('.png','.jpg','.jpeg','.bmp'):
                    presets.append(f.name)
        return jsonify({'images': presets, 'characters': ['福','寿','喜','乐','安','康']})

    @app.route('/api/icon-masks')
    def icon_masks():
        icons = []
        if ICON_MASKS_DIR.exists():
            for f in ICON_MASKS_DIR.iterdir():
                if f.suffix.lower() in ('.png','.jpg','.jpeg','.bmp'):
                    icons.append(f.name)
        return jsonify(icons)

    @app.route('/preview/<path:filename>')
    def serve_preview(filename):
        file_path = PREVIEWS_DIR / filename
        if not file_path.resolve().is_relative_to(PREVIEWS_DIR.resolve()):
            abort(404)
        if not file_path.is_file():
            abort(404)
        return send_file(file_path)

    @app.route('/data/temp/<path:filename>')
    def serve_temp(filename):
        file_path = TEMP_DIR / filename
        if not file_path.resolve().is_relative_to(TEMP_DIR.resolve()):
            abort(404)
        if not file_path.is_file():
            abort(404)
        return send_file(file_path)

    @app.route('/data/fonts/<path:filename>')
    def download_font(filename):
        from config import FONTS_DIR, FORCE_DOWNLOAD
        import pymysql
        from config import DB_CONFIG

        # 1. 查询数据库获取字体的许可证信息
        conn = pymysql.connect(**DB_CONFIG)
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT commercial_license, custom_info FROM font_metadata WHERE font_name = %s",
                               (filename,))
                row = cursor.fetchone()
                if not row:
                    abort(404)
                custom_info = json.loads(row['custom_info']) if row['custom_info'] else {}
                custom_license = custom_info.get('custom_license', '')
                final_license = custom_license if custom_license else row['commercial_license']
                is_open_source = final_license != 'unknown'
        finally:
            conn.close()

        # 2. 根据开关和许可证决定是否允许下载
        if FORCE_DOWNLOAD or is_open_source:
            file_path = FONTS_DIR / filename
            if not file_path.resolve().is_relative_to(FONTS_DIR.resolve()):
                abort(404)
            if not file_path.is_file():
                abort(404)
            return send_file(file_path, as_attachment=True, download_name=file_path.name)
        else:
            # 非开源字体不允许直接下载
            abort(403, description="该字体为非开源字体，不提供下载链接")

    @app.route('/upload', methods=['POST'])
    @login_required
    def upload_fonts():
        from core.process_font import process_font
        from config import FONTS_DIR, JSONS_DIR

        if 'single_file' in request.files:
            file = request.files['single_file']
            if file.filename == '':
                return jsonify({'error': '未选择文件'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': '不支持的文件类型'}), 400

            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, file.filename)
            file.save(temp_path)

            try:
                success, error_msg, full_filename = process_font(
                    temp_path,
                    str(FONTS_DIR),
                    generate_preview_flag=True,
                    export_json_flag=True,
                    copy_font=True
                )
                if not success:
                    return jsonify({'error': f'处理失败: {error_msg}'}), 500

                json_path = JSONS_DIR / f"{full_filename}_metadata.json"
                sync_single_font(json_path)
                return jsonify({'message': '上传成功'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        elif 'batch_files' in request.files:
            files = request.files.getlist('batch_files')
            results = []
            for file in files:
                if not allowed_file(file.filename):
                    results.append({'filename': file.filename, 'error': '不支持的文件类型'})
                    continue
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, file.filename)
                file.save(temp_path)
                try:
                    success, error_msg, new_basename = process_font(
                        temp_path, str(FONTS_DIR), True, True, copy_font=True
                    )
                    if success:
                        json_path = JSONS_DIR / f"{new_basename}_metadata.json"
                        sync_single_font(json_path)
                        results.append({'filename': file.filename, 'success': True})
                    else:
                        results.append({'filename': file.filename, 'error': error_msg})
                except Exception as e:
                    results.append({'filename': file.filename, 'error': str(e)})
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({'results': results})

        return jsonify({'error': '无效请求'}), 400

    @app.route('/api/generate-wordcloud', methods=['POST'])
    def api_generate_wordcloud():
        """生成词云并返回图片URL"""
        import tempfile
        import shutil
        import time
        from flask import request, jsonify
        from werkzeug.utils import secure_filename
        from config import TEMP_DIR, MASK_PRESETS_DIR, ICON_MASKS_DIR
        from core.preview_generator import WordCloudGenerator, SHAPE_FUNCTIONS_DICT, preprocess_mask_image
        from PIL import Image

        mode = request.form.get('mode', 'random')
        text = request.form.get('text', '')
        shape_name = request.form.get('shape_name', '')
        icon_name = request.form.get('icon_name', '')
        custom_char = request.form.get('custom_char', '')
        custom_image = request.files.get('custom_image')
        preset_image = request.form.get('preset_image', '')
        font_file = request.files.get('font_file')
        custom_icon_image = request.files.get('custom_icon_image')

        if not text:
            text = "词云生成器\nWordCloud\nPython\n数据可视化\n字体工具"

        temp_font_dir = None
        temp_font_path = None
        default_font = "C:/Windows/Fonts/simhei.ttf"
        if not os.path.exists(default_font):
            default_font = None

        temp_dirs = []
        new_icon_name = None
        new_image_name = None

        try:
            if font_file:
                temp_font_dir = tempfile.mkdtemp()
                temp_dirs.append(temp_font_dir)
                temp_font_path = os.path.join(temp_font_dir, secure_filename(font_file.filename))
                font_file.save(temp_font_path)
            else:
                temp_font_path = default_font

            if not temp_font_path or not os.path.exists(temp_font_path):
                return jsonify({'error': '未提供有效字体文件，且系统默认字体不存在'}), 400

            out_fd, out_path = tempfile.mkstemp(suffix='.png')
            os.close(out_fd)

            wc_gen = WordCloudGenerator(text, temp_font_path)
            common_kwargs = {'size': 800, 'max_words': 200}

            if mode == 'shape' and shape_name:
                shape_func = SHAPE_FUNCTIONS_DICT.get(shape_name)
                if shape_func:
                    wc_gen.generate_with_shape(shape_func=shape_func, shape_name=shape_name, output_name=out_path, **common_kwargs)
                else:
                    return jsonify({'error': f'未知形状: {shape_name}'}), 400

            elif mode == 'icon':
                if custom_icon_image and custom_icon_image.filename:
                    original_name = secure_filename(custom_icon_image.filename)
                    base_name = os.path.splitext(original_name)[0]
                    target_name = f"{base_name}_mask.png"
                    target_path = ICON_MASKS_DIR / target_name
                    if not target_path.exists():
                        temp_icon_dir = tempfile.mkdtemp()
                        temp_dirs.append(temp_icon_dir)
                        temp_icon_path = os.path.join(temp_icon_dir, original_name)
                        custom_icon_image.save(temp_icon_path)
                        try:
                            mask_array = preprocess_mask_image(temp_icon_path, size=800, delete_original=True)
                        except Exception as e:
                            return jsonify({'error': f'图标处理失败: {str(e)}'}), 400
                        Image.fromarray(mask_array).save(target_path)
                    icon_path = str(target_path)
                    new_icon_name = base_name
                else:
                    if not icon_name:
                        return jsonify({'error': '请选择图标'}), 400
                    icon_path = None
                    for ext in ['.png','.jpg','.jpeg','.bmp']:
                        candidate = ICON_MASKS_DIR / f"{icon_name}{ext}"
                        if candidate.exists():
                            icon_path = str(candidate)
                            break
                    if not icon_path:
                        return jsonify({'error': f'未找到图标图片: {icon_name}'}), 400
                wc_gen.generate_with_icon_mask(icon_path=icon_path, output_name=out_path, **common_kwargs)

            elif mode == 'image':
                img_path = None
                if custom_image and custom_image.filename:
                    temp_img_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_img_dir)
                    temp_img_path = os.path.join(temp_img_dir, secure_filename(custom_image.filename))
                    custom_image.save(temp_img_path)
                    try:
                        mask_array = preprocess_mask_image(temp_img_path, size=800, delete_original=True)
                    except Exception as e:
                        return jsonify({'error': f'图片蒙版处理失败: {str(e)}'}), 400
                    base_name = os.path.splitext(secure_filename(custom_image.filename))[0]
                    target_filename = f"{base_name}_mask.png"
                    target_path = MASK_PRESETS_DIR / target_filename
                    Image.fromarray(mask_array).save(target_path)
                    new_image_name = target_filename
                    img_path = str(target_path)
                elif preset_image:
                    img_path = MASK_PRESETS_DIR / preset_image
                    if not img_path.exists():
                        return jsonify({'error': f'预设图片不存在: {preset_image}'}), 400
                    img_path = str(img_path)
                else:
                    return jsonify({'error': '请选择图片'}), 400
                if not os.path.exists(img_path):
                    return jsonify({'error': '图片文件不存在'}), 400
                wc_gen.generate_with_image(image_path=img_path, output_name=out_path, **common_kwargs)

            elif mode == 'character':
                char = custom_char if custom_char else '福'
                wc_gen.generate_with_character(char=char, output_name=out_path, **common_kwargs)

            else:
                wc_gen.generate_random(output_name=out_path, **common_kwargs)

            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            final_filename = f"wordcloud_{int(time.time())}_{os.path.basename(out_path)}"
            final_path = TEMP_DIR / final_filename
            shutil.move(out_path, final_path)
            url = f'/data/temp/{final_filename}'

            response_data = {'image_url': url}
            if new_icon_name:
                response_data['new_icon'] = new_icon_name
            if new_image_name:
                response_data['new_image'] = new_image_name
            return jsonify(response_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
        finally:
            for d in temp_dirs:
                if os.path.exists(d):
                    shutil.rmtree(d, ignore_errors=True)
            if 'out_path' in locals() and os.path.exists(out_path):
                os.remove(out_path)

    @app.route('/data/masks/icon_masks/<path:filename>')
    def serve_icon_mask(filename):
        from config import ICON_MASKS_DIR
        file_path = ICON_MASKS_DIR / filename
        if not file_path.resolve().is_relative_to(ICON_MASKS_DIR.resolve()):
            abort(404)
        if not file_path.is_file():
            abort(404)
        return send_file(file_path)

    @app.route('/data/masks/mask_presets/<path:filename>')
    def serve_mask_preset(filename):
        from config import MASK_PRESETS_DIR
        file_path = MASK_PRESETS_DIR / filename
        if not file_path.resolve().is_relative_to(MASK_PRESETS_DIR.resolve()):
            abort(404)
        if not file_path.is_file():
            abort(404)
        return send_file(file_path)