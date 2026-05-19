import json
import pymysql
from pathlib import Path
from config import DB_CONFIG, FONTS_DIR

def sync_metadata_to_db(json_dir: str):
    json_dir = Path(json_dir)
    if not json_dir.exists():
        print(f"错误: 目录不存在 {json_dir}")
        return
    try:
        conn = pymysql.connect(
            host=DB_CONFIG["host"], port=DB_CONFIG["port"],
            user=DB_CONFIG["user"], password=DB_CONFIG["password"],
            charset=DB_CONFIG["charset"], autocommit=True,
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` CHARACTER SET utf8mb4")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS font_metadata (
                id INT AUTO_INCREMENT PRIMARY KEY,
                font_name VARCHAR(500) NOT NULL,
                commercial_license VARCHAR(50),
                total_characters INT,
                supported_languages VARCHAR(50),
                metadata JSON NOT NULL,
                custom_info JSON DEFAULT NULL,
                font_file_url VARCHAR(500) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_font_name (font_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("SHOW COLUMNS FROM font_metadata LIKE 'font_file_url'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE font_metadata ADD COLUMN font_file_url VARCHAR(500) DEFAULT NULL")
        cursor.execute("SHOW COLUMNS FROM font_metadata LIKE 'custom_info'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE font_metadata ADD COLUMN custom_info JSON DEFAULT NULL")

        json_files = list(json_dir.glob("*_metadata.json"))
        if not json_files:
            print(f"未找到任何 *_metadata.json 文件在 {json_dir}")
            cursor.close(); conn.close(); return

        insert_sql = """
            INSERT INTO font_metadata (font_name, commercial_license, total_characters, supported_languages, metadata, custom_info, font_file_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                commercial_license = VALUES(commercial_license),
                total_characters = VALUES(total_characters),
                supported_languages = VALUES(supported_languages),
                metadata = VALUES(metadata),
                custom_info = VALUES(custom_info),
                font_file_url = VALUES(font_file_url)
        """
        count = 0
        for json_path in json_files:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            font_name = data.get('font_name', json_path.stem.replace('_metadata',''))
            commercial_license = data.get('commercial_license', 'unknown')
            total_chars = data.get('total_characters', 0)
            supported_langs = data.get('supported_languages', '')
            metadata_json = json.dumps(data, ensure_ascii=False)
            custom_info = data.get('custom_info', {})
            # 生成 font_file_url
            font_file = FONTS_DIR / font_name
            if font_file.exists():
                font_file_url = f"/data/fonts/{font_file.name}"
            else:
                # 尝试不区分大小写匹配
                matched = None
                for f in FONTS_DIR.glob("*"):
                    if f.name.lower() == font_name.lower():
                        matched = f
                        break
                if matched:
                    font_file_url = f"/data/fonts/{matched.name}"
                else:
                    font_file_url = None
                    print(f"警告: 未找到字体文件 {font_name} 在 {FONTS_DIR}")
            cursor.execute(insert_sql, (font_name, commercial_license, total_chars, supported_langs, metadata_json, json.dumps(custom_info), font_file_url))
            count += 1
            print(f"已同步: {font_name}")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"同步完成，共处理 {count} 个文件。")
    except Exception as e:
        print(f"数据库操作失败: {e}")

def sync_single_font(json_path: Path):
    if not json_path.exists():
        print(f"JSON 文件不存在: {json_path}")
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    font_name = data.get('font_name', json_path.stem.replace('_metadata',''))
    commercial_license = data.get('commercial_license', 'unknown')
    total_chars = data.get('total_characters', 0)
    supported_langs = data.get('supported_languages', '')
    metadata_json = json.dumps(data, ensure_ascii=False)
    custom_info = data.get('custom_info', {})
    # 生成 font_file_url
    font_file = FONTS_DIR / font_name
    if font_file.exists():
        font_file_url = f"/data/fonts/{font_file.name}"
    else:
        matched = None
        for f in FONTS_DIR.glob("*"):
            if f.name.lower() == font_name.lower():
                matched = f
                break
        if matched:
            font_file_url = f"/data/fonts/{matched.name}"
        else:
            font_file_url = None
            print(f"警告: 未找到字体文件 {font_name} 在 {FONTS_DIR}")
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO font_metadata (font_name, commercial_license, total_characters, supported_languages, metadata, custom_info, font_file_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    commercial_license = VALUES(commercial_license),
                    total_characters = VALUES(total_characters),
                    supported_languages = VALUES(supported_languages),
                    metadata = VALUES(metadata),
                    custom_info = VALUES(custom_info),
                    font_file_url = VALUES(font_file_url)
            """, (font_name, commercial_license, total_chars, supported_langs, metadata_json, json.dumps(custom_info), font_file_url))
            conn.commit()
            print(f"已同步字体: {font_name} (链接: {font_file_url})")
    except Exception as e:
        print(f"同步失败: {e}")
    finally:
        conn.close()