import os
from pathlib import Path
import os
from werkzeug.security import generate_password_hash, check_password_hash

# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据根目录
DATA_DIR = BASE_DIR / 'data'

# 子目录
FONTS_DIR = DATA_DIR / 'fonts'
PREVIEWS_DIR = DATA_DIR / 'previews'
JSONS_DIR = DATA_DIR / 'jsons'
TEMP_DIR = DATA_DIR / 'temp'
MASKS_DIR = DATA_DIR / 'masks'
ICON_MASKS_DIR = MASKS_DIR / 'icon_masks'
MASK_PRESETS_DIR = MASKS_DIR / 'mask_presets'

# 确保目录存在
for dir_path in [FONTS_DIR, PREVIEWS_DIR, JSONS_DIR, TEMP_DIR, ICON_MASKS_DIR, MASK_PRESETS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 数据库配置（请根据实际情况修改）
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "font_metadata"),
    "charset": "utf8mb4",
}

SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-secret-key")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
FORCE_DOWNLOAD = os.getenv("FORCE_DOWNLOAD", "False").lower() == "true"  # 强制提供下载链接开关（False：非开源只显示自定义链接）



# 默认字体输入路径（可修改）
DEFAULT_INPUT_PATH = r"E:\work\font\files"   # 按需修改
DEFAULT_OUTPUT_DIR = str(FONTS_DIR)
DEFAULT_GENERATE_PREVIEW = True
DEFAULT_EXPORT_JSON = True

# 预览图参数
PREVIEW_WIDTH = 800
PREVIEW_MARGIN = 20
LINE_HEIGHT = 40
FONT_SIZE = 24

# 文件名非法字符正则
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\s]'



# 预设字符集（用于字符蒙版和随机模式）
PRESET_CHARS = [
    '福', '寿', '喜', '乐', '安', '康', '爱', '梦', '飞', '龙', '凤', '春', '夏', '秋', '冬',
    '梅', '兰', '竹', '菊', '山', '水', '风', '月', '花', '鸟', '鱼', '虫', '琴', '棋', '书', '画',
    '愛', '夢', '飛', '龍', '鳳', '春', '夏', '秋', '冬', '梅', '蘭', '竹', '菊', '風', '月', '書', '畫',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    'あ', 'い', 'う', 'え', 'お', 'か', 'き', 'く', 'け', 'こ',
    'さ', 'し', 'す', 'せ', 'そ', 'た', 'ち', 'つ', 'て', 'と',
    'な', 'に', 'ぬ', 'ね', 'の', 'は', 'ひ', 'ふ', 'へ', 'ほ',
    'ま', 'み', 'む', 'め', 'も', 'や', 'ゆ', 'よ', 'ら', 'り',
    'る', 'れ', 'ろ', 'わ', 'を', 'ん',
    'ア', 'イ', 'ウ', 'エ', 'オ', 'カ', 'キ', 'ク', 'ケ', 'コ',
    'サ', 'シ', 'ス', 'セ', 'ソ', 'タ', 'チ', 'ツ', 'テ', 'ト',
    'ナ', 'ニ', 'ヌ', 'ネ', 'ノ', 'ハ', 'ヒ', 'フ', 'ヘ', 'ホ',
    'マ', 'ミ', 'ム', 'メ', 'モ', 'ヤ', 'ユ', 'ヨ', 'ラ', 'リ',
    'ル', 'レ', 'ロ', 'ワ', 'ヲ', 'ン',
    'ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
    'ㅏ', 'ㅑ', 'ㅓ', 'ㅕ', 'ㅗ', 'ㅛ', 'ㅜ', 'ㅠ', 'ㅡ', 'ㅣ',
    '0','1','2','3','4','5','6','7','8','9',
    '❤', '★', '☆', '☀', '☁', '☂', '☃', '☎', '☕', '♔', '♕', '♖', '♗', '♘', '♙',
    '♠', '♡', '♢', '♣', '♤', '♥', '♦', '♧', '✿', '❀', '🌸', '🌼', '🌻', '🌺',
    '⌘', '⌛', '⌨', '⏰', '⏳', '⛅', '⛪', '⛺', '⚽', '⚾', '🏀', '🏈', '🏆', '🏠', '🏡',
]

# ========== 映射表（用于元数据导出） ==========
PLATFORM_NAMES = {
    0: "unicode", 1: "mac", 2: "iso", 3: "win",
}
MAC_ENCODING_NAMES = {
    0: "enc_id_en", 1: "enc_id_jp", 2: "enc_id_tc", 3: "enc_id_kr", 25: "enc_id_cn",
}
WIN_ENCODING_NAMES = {
    0: "enc_id_symbol", 1: "enc_id_unicode_bmp", 2: "enc_id_shift_jis",
    3: "enc_id_prc", 4: "enc_id_big5", 5: "enc_id_wan_sung", 6: "enc_id_johab",
}
WIN_LANG_NAMES = {
    1028: "tw", 1033: "en", 1041: "jp", 1042: "kr", 2052: "cn", 3076: "hk", 5124: "mo",
}
MAC_LANG_NAMES = {
    0: "en", 11: "jp", 19: "tw", 23: "kr", 33: "cn",
}
NAME_ID_MAP = {
    0: "copyright_notice", 1: "font_family_name", 2: "font_subfamily_name",
    3: "unique_font_identifier", 4: "full_font_name", 5: "version_string",
    6: "postScript_name_for_the_font", 7: "trademark", 8: "manufacturer",
    9: "designer", 10: "description", 11: "url_of_vendor", 12: "url_of_designer",
    13: "license_description", 14: "license_info_url", 16: "typographic_family_name",
    17: "typographic_subfamily_name", 18: "compatible_full", 19: "sample_text",
    20: "postScript_cid_findfont_name", 21: "wws_family_name", 22: "wws_subfamily_name",
    23: "light_background_palette", 24: "dark_background_palette",
    25: "variations_postscript_name_prefix",
}

# ========== 多语言诗词库 ==========
POEMS = {
    '简': [
        {
            'title': '临江仙·滚滚长江东逝水',
            'author': '杨慎',
            'lines': [
                '滚滚长江东逝水，', '浪花淘尽英雄。', '是非成败转头空。',
                '青山依旧在，', '几度夕阳红。', '白发渔樵江渚上，',
                '惯看秋月春风。', '一壶浊酒喜相逢。', '古今多少事，',
                '都付笑谈中。'
            ]
        },
        {
            'title': '唐多令·芦叶满汀洲',
            'author': '刘过',
            'lines': [
                '芦叶满汀洲，', '寒沙带浅流。', '二十年重过南楼。',
                '柳下系船犹未稳，', '能几日，又中秋。', '黄鹤断矶头，',
                '故人曾到否？', '旧江山浑是新愁。', '欲买桂花同载酒，',
                '终不似，少年游。'
            ]
        }
    ],
    '繁': [
        {
            'title': '臨江仙·滾滾長江東逝水',
            'author': '楊慎',
            'lines': [
                '滾滾長江東逝水，', '浪花淘盡英雄。', '是非成敗轉頭空。',
                '青山依舊在，', '幾度夕陽紅。', '白髮漁樵江渚上，',
                '慣看秋月春風。', '一壺濁酒喜相逢。', '古今多少事，',
                '都付笑談中。'
            ]
        },
        {
            'title': '唐多令·蘆葉滿汀洲',
            'author': '劉過',
            'lines': [
                '蘆葉滿汀洲，', '寒沙帶淺流。', '二十年重過南樓。',
                '柳下繫船猶未穩，', '能幾日，又中秋。', '黃鶴斷磯頭，',
                '故人曾到否？', '舊江山渾是新愁。', '欲買桂花同載酒，',
                '終不似，少年遊。'
            ]
        }
    ],
    '日': [
        {
            'title': '芭蕉俳句集',
            'author': '松尾芭蕉',
            'lines': [
                '古池や', '蛙飛びこむ', '水の音', '閑かさや', '岩にしみ入る',
                '蝉の声', '柿食えば', '鐘が鳴るなり', '法隆寺', '秋深き'
            ]
        },
        {
            'title': '伊呂波歌',
            'author': '仮名',
            'lines': [
                'いろはにほへと', 'ちりぬるを', 'わかよたれそ', 'つねならむ',
                'うゐのおくやま', 'けふこえて', 'あさきゆめみし', 'ゑひもせす',
                'いろはにほへと', 'ちりぬるを'
            ]
        }
    ],
    '韩': [
        {
            'title': '임강선·곤곤장강동서수',
            'author': '양신',
            'lines': [
                '곤곤장강동서수,', '랑화도진영웅.', '시비성패전두공.',
                '청산의구재,', '기도석양홍.', '백발어초강저상,',
                '관간추월춘풍.', '일호탁주희상봉.', '고금다소사,',
                '도부소담중.'
            ]
        }
    ],
    '英': [
        {
            'title': 'The Road Not Taken',
            'author': 'Robert Frost',
            'lines': [
                'Two roads diverged in a yellow wood,',
                'And sorry I could not travel both',
                'And be one traveler, long I stood',
                'And looked down one as far as I could',
                'To where it bent in the undergrowth;',
                'Then took the other, as just as fair,',
                'And having perhaps the better claim,',
                'Because it was grassy and wanted wear;',
                'Though as for that the passing there',
                'Had worn them really about the same,'
            ]
        },
        {
            'title': 'Stopping by Woods on a Snowy Evening',
            'author': 'Robert Frost',
            'lines': [
                'Whose woods these are I think I know.',
                'His house is in the village though;',
                'He will not see me stopping here',
                'To watch his woods fill up with snow.',
                'My little horse must think it queer',
                'To stop without a farmhouse near',
                'Between the woods and frozen lake',
                'The darkest evening of the year.',
                'He gives his harness bells a shake',
                'To ask if there is some mistake.'
            ]
        }
    ]
}

SUPPORTED_SCRIPTS = [
    {
        "name": "Latin",
        "ranges": [(0x0000, 0x007F), (0x0080, 0x00FF)],
        "sample": "拉丁示例：The quick brown fox jumps over the lazy dog",
    },
    {
        "name": "Digits",
        "ranges": [(0x0030, 0x0039)],
        "sample": "数字示例：0 1 2 3 4 5 6 7 8 9",
    },
    {
        "name": "CJK",
        "ranges": [(0x4E00, 0x9FFF)],
        "sample": "汉字示例：字体预览 支持中文",
    },
    {
        "name": "Hiragana",
        "ranges": [(0x3040, 0x309F)],
        "sample": "平假名示例：ひらがな あいうえお",
    },
    {
        "name": "Katakana",
        "ranges": [(0x30A0, 0x30FF)],
        "sample": "片假名示例：カタカナ アイウエオ",
    },
    {
        "name": "Hangul",
        "ranges": [(0xAC00, 0xD7AF)],
        "sample": "韩文示例：한글 예시: 안녕하세요",
    },
    {
        "name": "Cyrillic",
        "ranges": [(0x0400, 0x04FF)],
        "sample": "西里尔示例：Кириллица: АБВГД",
    },
    {
        "name": "Greek",
        "ranges": [(0x0370, 0x03FF)],
        "sample": "希腊示例：Ελληνικά: ΑΒΓΔΕ",
    },
]