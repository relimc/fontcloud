import random
import os
import jieba
import numpy as np
from PIL import Image, ImageDraw
from wordcloud import WordCloud
from config import ICON_MASKS_DIR, POEMS
from config import PRESET_CHARS

# ========== 轮廓配置 ==========
ENABLE_OUTLINE = False          # 是否启用轮廓（仅对 shape 和 image 模式有效）
OUTLINE_RANDOM = False          # 是否随机宽度（True: 1~5 随机; False: 固定为 1）
OUTLINE_WIDTH_RANGE = (1, 5)   # 随机范围
# ==============================

# ========== 预定义图标列表 ==========
DEFAULT_ICONS = [
    'fas fa-heart', 'fas fa-star', 'fas fa-plane', 'fas fa-cloud', 'fas fa-tree',
    'fas fa-cat', 'fas fa-dog', 'fas fa-dragon', 'fas fa-fish', 'fas fa-crown',
    'fas fa-music', 'fas fa-car', 'fas fa-bicycle', 'fas fa-rocket', 'fas fa-globe',
    'fas fa-camera', 'fas fa-coffee', 'fas fa-apple-alt', 'fas fa-snowflake', 'fas fa-lightbulb',
]

# ========== 形状生成函数 ==========
def create_circle_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse((50, 50, size - 50, size - 50), fill=0)
    return np.array(img)

def create_square_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    margin = size // 4
    draw.rectangle((margin, margin, size - margin, size - margin), fill=0)
    return np.array(img)

def create_triangle_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    center = size // 2
    height = int(size * 0.7)
    top = (center, size // 4)
    left = (center - height // 2, size - size // 4)
    right = (center + height // 2, size - size // 4)
    draw.polygon([top, left, right], fill=0)
    return np.array(img)

def create_heart_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    points = []
    for t in np.linspace(0, 2 * np.pi, 100):
        x = 16 * np.sin(t) ** 3
        y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
        x = size // 2 + x * size / 35
        y = size // 2 - y * size / 35
        points.append((x, y))
    draw.polygon(points, fill=0)
    return np.array(img)

def create_star_mask(size=800, points=5):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    center = size // 2
    outer_r = size * 0.4
    inner_r = outer_r * 0.4
    star_points = []
    for i in range(points * 2):
        angle = i * (2 * np.pi / (points * 2)) - np.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        x = center + r * np.cos(angle)
        y = center + r * np.sin(angle)
        star_points.append((x, y))
    draw.polygon(star_points, fill=0)
    return np.array(img)

def create_diamond_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    center = size // 2
    d = size * 0.6
    points = [
        (center, center - d // 2),
        (center + d // 2, center),
        (center, center + d // 2),
        (center - d // 2, center)
    ]
    draw.polygon(points, fill=0)
    return np.array(img)

def create_pentagon_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    center = size // 2
    r = size * 0.4
    points = []
    for i in range(5):
        angle = i * (2 * np.pi / 5) - np.pi / 2
        x = center + r * np.cos(angle)
        y = center + r * np.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=0)
    return np.array(img)

def create_hexagon_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    center = size // 2
    r = size * 0.4
    points = []
    for i in range(6):
        angle = i * (2 * np.pi / 6) - np.pi / 2
        x = center + r * np.cos(angle)
        y = center + r * np.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=0)
    return np.array(img)

def create_ellipse_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse((size // 4, size // 6, size - size // 4, size - size // 6), fill=0)
    return np.array(img)

def create_ring_mask(size=800):
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse((50, 50, size - 50, size - 50), fill=0)
    draw.ellipse((size // 3, size // 3, size - size // 3, size - size // 3), fill=255)
    return np.array(img)

SHAPE_FUNCTIONS = [
    ("圆形", create_circle_mask),
    ("正方形", create_square_mask),
    ("三角形", create_triangle_mask),
    ("心形", create_heart_mask),
    ("五角星", create_star_mask),
    ("菱形", create_diamond_mask),
    ("五边形", create_pentagon_mask),
    ("六边形", create_hexagon_mask),
    ("椭圆形", create_ellipse_mask),
    ("环形", create_ring_mask),
]


def preprocess_mask_image(image_path, size=800, delete_original=False):
    import cv2
    import numpy as np
    from PIL import Image

    # 处理已是蒙版的文件（透明背景或已有mask）
    if '_mask' in os.path.basename(image_path):
        pil_img = Image.open(image_path).convert('RGBA')
        background = Image.new('RGBA', pil_img.size, (255, 255, 255, 255))
        composite = Image.alpha_composite(background, pil_img).convert('L')
        mask_array = np.array(composite)
        mask_array = np.where(mask_array < 128, 0, 255).astype(np.uint8)
        mask_resized = cv2.resize(mask_array, (size, size), interpolation=cv2.INTER_LINEAR)
        return mask_resized

    base, ext = os.path.splitext(image_path)
    cached_path = f"{base}_mask{ext}"
    if os.path.exists(cached_path):
        img = cv2.imread(cached_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            return cv2.resize(img, (size, size), interpolation=cv2.INTER_LINEAR)

    # 读取原始图片，支持透明背景
    pil_img = Image.open(image_path).convert('RGBA')
    background = Image.new('RGBA', pil_img.size, (255, 255, 255, 255))
    composite = Image.alpha_composite(background, pil_img).convert('L')
    img = np.array(composite)

    # 二值化
    _, binary = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((5,5), np.uint8)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    dilated = cv2.dilate(closed, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        mask = np.ones_like(img) * 255
        cv2.drawContours(mask, contours, -1, 0, thickness=cv2.FILLED)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    else:
        mask = dilated

    # 确保填充区域为黑色（0），背景为白色（255）
    black_pixels = np.sum(mask == 0)
    white_pixels = np.sum(mask == 255)
    if black_pixels > white_pixels:
        mask = cv2.bitwise_not(mask)

    mask_resized = cv2.resize(mask, (size, size), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(cached_path, mask_resized)
    if delete_original and os.path.exists(image_path) and image_path != cached_path:
        os.remove(image_path)
    return mask_resized


def create_character_mask(char, font_path, size=800):
    """
    使用指定字体文件绘制汉字蒙版
    """
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        # 字体大小约为蒙版大小的 80%
        font = ImageFont.truetype(font_path, int(size * 0.8))
    except Exception as e:
        raise RuntimeError(f"无法加载字体 {font_path}: {e}")

    # 计算文字居中位置
    bbox = draw.textbbox((0, 0), char, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2 - bbox[0]
    y = (size - text_height) // 2 - bbox[1]

    # 绘制黑色字符（背景白色）
    draw.text((x, y), char, font=font, fill=(0, 0, 0, 255))
    mask_array = np.array(img)
    return mask_array

# ========== 词云生成器类 ==========
class WordCloudGenerator:
    def __init__(self, text, font_path):
        self.text = text
        self.font_path = font_path
        self.processed_text = None
        self._preprocess_text()
        # 缓存 cmap
        from core.font_parser import get_best_cmap
        from core.utils import open_font_safe
        font = open_font_safe(font_path)
        self.cmap = get_best_cmap(font)
        font.close()

    def _preprocess_text(self):
        word_list = jieba.cut(self.text, cut_all=False)
        self.processed_text = " ".join(word_list)

    def _save_only(self, wordcloud_obj, output_name):
        wordcloud_obj.to_file(output_name)

    def _get_random_icon(self):
        return random.choice(DEFAULT_ICONS)

    def _get_random_icon_path(self):
        """随机返回一个可用的图标蒙版图片路径"""
        icon_files = list(ICON_MASKS_DIR.glob('*.png')) + list(ICON_MASKS_DIR.glob('*.jpg'))
        if not icon_files:
            # 如果没有图标图片，则返回 None（调用方应降级）
            return None
        return str(random.choice(icon_files))

    def _get_random_mask_image(self, mask_dir='mask'):
        if not os.path.isdir(mask_dir):
            raise FileNotFoundError("mask目录不存在")
        # 只选择文件名中不含 '_mask' 的图片（原始图片）
        images = [f for f in os.listdir(mask_dir)
                  if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
                  and '_mask' not in f]
        if not images:
            # 如果没有原始图片，则允许使用已有的蒙版图片（但不会再生成新蒙版）
            images = [f for f in os.listdir(mask_dir)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
            if not images:
                raise FileNotFoundError("mask目录无图片")
            # 注意：返回的可能是蒙版图片，后续 preprocess_mask_image 会直接加载，不会再次生成
        return os.path.join(mask_dir, random.choice(images))

    def _get_random_shape(self):
        return random.choice(SHAPE_FUNCTIONS)

    # preview_generator.py - 在 WordCloudGenerator 类中

    def generate_with_character(self, char, output_name, **kwargs):
        """
        使用指定的单个字符作为蒙版形状生成词云（支持任意字符：汉字、英文字母、数字、符号等）。
        如果字符不被当前字体支持，则抛出 ValueError。
        """
        import numpy as np
        from wordcloud import WordCloud
        from PIL import Image, ImageDraw, ImageFont

        # 确保有 cmap 缓存
        if not hasattr(self, 'cmap') or self.cmap is None:
            from core.font_parser import get_best_cmap
            from core.utils import open_font_safe
            font = open_font_safe(self.font_path)
            self.cmap = get_best_cmap(font)
            font.close()

        # 检查字符是否被字体支持
        if ord(char) not in self.cmap:
            raise ValueError(f"字符 '{char}' 不被当前字体支持")

        # 生成字符蒙版图片（白底黑色字符）
        size = kwargs.get('size', 800)
        # 使用灰度模式 'L'，背景白色（255）
        img = Image.new('L', (size, size), 255)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(self.font_path, int(size * 0.8))
        except:
            font = ImageFont.load_default()

        # 计算文字居中位置
        bbox = draw.textbbox((0, 0), char, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2 - bbox[0]
        y = (size - text_height) // 2 - bbox[1]
        draw.text((x, y), char, font=font, fill=0)  # 黑色

        # 转换为 numpy 数组，黑色区域为 0（填充），白色区域为 255（不填充）
        mask_array = np.array(img)

        wc_params = {
            'font_path': self.font_path,
            'mask': mask_array,
            'background_color': kwargs.get('background_color', 'white'),
            'max_words': kwargs.get('max_words', 200),
            'width': kwargs.get('width', size),
            'height': kwargs.get('height', size),
            'repeat': True,
        }
        if 'outline_width' in kwargs and kwargs['outline_width'] > 0:
            wc_params['contour_width'] = kwargs['outline_width']
            wc_params['contour_color'] = kwargs.get('outline_color', 'black')
        wc_params.update(kwargs.get('wc_params', {}))

        wc = WordCloud(**wc_params).generate(self.processed_text)
        wc.to_file(output_name)
        print(f"字符蒙版词云已生成: {output_name} (字符: {char})")

    def generate_with_shape(self, shape_func=None, shape_name=None, **kwargs):
        if shape_func is None:
            shape_name, shape_func = self._get_random_shape()
        elif shape_name is None:
            shape_name = "custom_shape"
        mask_array = shape_func(size=kwargs.get('size', 800))
        output_name = kwargs.get('output_name', f"wordcloud_{shape_name}.png")
        wc_params = {
            'font_path': self.font_path,
            'mask': mask_array,
            'background_color': 'white',
            'max_words': kwargs.get('max_words', 200),
            'width': kwargs.get('width', 800),
            'height': kwargs.get('height', 800),
            'repeat': True
        }
        if 'outline_width' in kwargs and kwargs['outline_width'] > 0:
            wc_params['contour_width'] = kwargs['outline_width']
            wc_params['contour_color'] = kwargs.get('outline_color', 'black')
        wc_params.update(kwargs.get('wc_params', {}))
        wc = WordCloud(**wc_params).generate(self.processed_text)
        self._save_only(wc, output_name)

    def generate_with_icon(self, icon_name, output_name, **kwargs):
        """
        兼容旧接口：根据图标名称（简单名称，如 'heart'）查找图片并生成图标词云
        """
        # 查找图标文件
        icon_path = None
        for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            candidate = ICON_MASKS_DIR / f"{icon_name}{ext}"
            if candidate.exists():
                icon_path = str(candidate)
                break
        if not icon_path:
            raise FileNotFoundError(f"未找到图标图片: {icon_name} 在 {ICON_MASKS_DIR}")
        self.generate_with_icon_mask(icon_path=icon_path, output_name=output_name, **kwargs)

    # 在 WordCloudGenerator 类中
    def generate_with_icon_mask(self, icon_path, output_name, **kwargs):
        """
        使用 wordcloud + repeat 生成图标词云。
        icon_path: 图标蒙版图片路径（要求白底黑色实心图案）
        """
        import numpy as np
        from wordcloud import WordCloud

        # 生成蒙版数组（复用 preprocess_mask_image 函数）
        mask_array = preprocess_mask_image(icon_path, size=kwargs.get('size', 800))

        # 检查蒙版中黑色（填充）像素数量
        black_pixels = np.sum(mask_array == 0)
        if black_pixels == 0:
            raise ValueError("蒙版中无可填充区域（全白），请确保图标图片为白底黑色实心图案")

        # 构建 WordCloud 参数
        wc_params = {
            'font_path': self.font_path,
            'mask': mask_array,
            'background_color': kwargs.get('background_color', 'white'),
            'max_words': kwargs.get('max_words', 200),
            'width': kwargs.get('width', 800),
            'height': kwargs.get('height', 800),
            'repeat': True,  # 关键：允许重复文本填满轮廓
        }

        # 轮廓（可选）
        if 'outline_width' in kwargs and kwargs['outline_width'] > 0:
            wc_params['contour_width'] = kwargs['outline_width']
            wc_params['contour_color'] = kwargs.get('outline_color', 'black')

        # 合并额外参数（如 wc_params 覆盖）
        wc_params.update(kwargs.get('wc_params', {}))

        # 生成词云
        wc = WordCloud(**wc_params).generate(self.processed_text)

        # 保存图片
        wc.to_file(output_name)
        print(f"图标词云已生成: {output_name}")

    def generate_with_image(self, image_path=None, **kwargs):
        if image_path is None:
            image_path = self._get_random_mask_image()
        mask_array = preprocess_mask_image(
            image_path,
            size=kwargs.get('size', 800),
            delete_original=True  # 添加此参数，根据你的需求决定是否删除原始图片
        )
        # 后续代码不变，直接使用 mask_array
        if 'output_name' not in kwargs:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            kwargs['output_name'] = f"image_{base_name}.png"
        output_name = kwargs.get('output_name')
        wc_params = {
            'font_path': self.font_path,
            'mask': mask_array,
            'background_color': 'white',
            'max_words': kwargs.get('max_words', 200),
            'width': kwargs.get('width', 800),
            'height': kwargs.get('height', 800),
            'repeat': True,
        }
        if 'outline_width' in kwargs and kwargs['outline_width'] > 0:
            wc_params['contour_width'] = kwargs['outline_width']
            wc_params['contour_color'] = kwargs.get('outline_color', 'black')
        wc_params.update(kwargs.get('wc_params', {}))
        wc = WordCloud(**wc_params).generate(self.processed_text)
        self._save_only(wc, output_name)

    def generate_random(self, output_name=None, output_prefix="random", **kwargs):
        modes = ['shape', 'icon', 'image', 'character']  # 包含图标模式
        chosen_mode = random.choice(modes)
        if output_name is not None:
            kwargs['output_name'] = output_name

        if chosen_mode == 'shape':
            shape_name, shape_func = self._get_random_shape()
            if output_name is None and 'output_name' not in kwargs:
                kwargs['output_name'] = f"{output_prefix}_{shape_name}.png"
            self.generate_with_shape(shape_func=shape_func, shape_name=shape_name, **kwargs)
        elif chosen_mode == 'icon':
            icon_path = self._get_random_icon_path()
            if icon_path is None:
                # 降级
                shape_name, shape_func = self._get_random_shape()
                if 'output_name' not in kwargs:
                    kwargs['output_name'] = f"{output_prefix}_{shape_name}_fallback.png"
                self.generate_with_shape(shape_func=shape_func, shape_name=shape_name, **kwargs)
            else:
                # 确保 output_name 只从 kwargs 中取一次
                out_name = kwargs.pop('output_name', None)
                if out_name is None:
                    out_name = f"{output_prefix}_icon.png"
                self.generate_with_icon_mask(icon_path=icon_path, output_name=out_name, **kwargs)
        elif chosen_mode == 'image':
            try:
                image_path = self._get_random_mask_image()
                if output_name is None and 'output_name' not in kwargs:
                    kwargs['output_name'] = f"{output_prefix}_mask.png"
                self.generate_with_image(image_path=image_path, **kwargs)
            except FileNotFoundError:
                shape_name, shape_func = self._get_random_shape()
                if output_name is None and 'output_name' not in kwargs:
                    kwargs['output_name'] = f"{output_prefix}_{shape_name}_fallback.png"
                self.generate_with_shape(shape_func=shape_func, shape_name=shape_name, **kwargs)
        else:  # character
            # 随机选择字符，最多尝试5次
            selected_char = None
            for _ in range(5):
                candidate = random.choice(PRESET_CHARS)
                # 检查该字符是否被字体支持（需要获取当前字体的 cmap）
                # 注意：这里需要用到 self.font 的 cmap，但 WordCloudGenerator 没有直接保存 font 对象
                # 临时获取 cmap 的方法：重新打开字体？效率低。更好的方法是在初始化时缓存 cmap。
                # 为了简单，我们可以利用 generate_with_character 内部会处理不支持字符（显示方框），但降级需要提前知道。
                # 因此我们这里不检查，直接使用，如果生成后效果不好（全是方框）用户会看到，但这不是降级。
                # 根据需求，如果字体不支持该字符，应该降级到形状模式。所以需要提前检查。
                # 我们可以在 WordCloudGenerator 初始化时保存 cmap，以便快速检查。
                # 但为了保持代码简单，我们采用以下方式：调用 generate_with_character，如果结果图片中全是方框（需要解析图片？复杂），不现实。
                # 因此我们改用：在 generate_with_character 中，如果过滤后所有字符都是 □，则抛出异常，上层捕获并降级。
                # 我们修改 generate_with_character 来支持这个机制。
                # 这里先保留原逻辑，稍后修改 generate_with_character。
                selected_char = candidate
                break
            if selected_char is None:
                selected_char = '福'  # 最终后备
            # 尝试生成，如果失败（字符不被支持导致抛出异常），则降级为形状模式
            try:
                if output_name is None and 'output_name' not in kwargs:
                    kwargs['output_name'] = f"{output_prefix}_{selected_char}.png"
                self.generate_with_character(char=selected_char, **kwargs)
            except ValueError as e:
                # 如果因为字符不被支持而失败，降级为形状模式
                print(f"字符 '{selected_char}' 不被字体支持，降级为形状模式")
                shape_name, shape_func = self._get_random_shape()
                if output_name is None and 'output_name' not in kwargs:
                    kwargs['output_name'] = f"{output_prefix}_{shape_name}_fallback.png"
                self.generate_with_shape(shape_func=shape_func, shape_name=shape_name, **kwargs)


def generate_font_title_preview(font_path: str, output_path: str, display_name: str):
    from PIL import Image, ImageDraw, ImageFont

    font_size = 18
    try:
        pil_font = ImageFont.truetype(font_path, font_size)
    except:
        pil_font = ImageFont.load_default()

    # 测量文字尺寸
    temp_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(temp_img)
    bbox = draw.textbbox((0, 0), display_name, font=pil_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x_offset = -bbox[0]
    y_offset = -bbox[1]

    # 创建透明背景
    img = Image.new('RGBA', (text_width, text_height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.text((x_offset, y_offset), display_name, fill=(0,0,0,255), font=pil_font)

    img.save(output_path)
    print(f"小尺寸字体名预览图已生成: {output_path}")


# ========== 对外预览生成函数 ==========
def generate_preview(font_path: str, output_path: str, font_name: str):
    """
    生成词云预览图（仅词云，无额外文字信息）
    """
    # 为避免循环导入，在函数内部导入所需模块
    from core.font_parser import get_best_cmap, get_supported_scripts
    from core.utils import open_font_safe

    font = open_font_safe(font_path)
    try:
        cmap = get_best_cmap(font)
        scripts = get_supported_scripts(font, cmap)
        text_source = " ".join([script["sample"] for script in scripts])
        if not text_source:
            text_source = "字体预览"
        wc_gen = WordCloudGenerator(text_source, font_path)
        wc_gen.generate_random(output_name=output_path, size=350, max_words=200)
        print(f"词云预览图已生成: {output_path}")
    finally:
        font.close()


def generate_chars_preview(font_path: str, output_path: str, font_name: str):
    """
    生成竖排诗歌预览图：固定12列（标题 + 作者 + 10句内容），从左到右排列。
    简繁使用《临江仙》，日文使用俳句・短歌集，韩文使用翻译版，英文使用《The Road Not Taken》。
    """
    from core.font_parser import get_best_cmap, get_supported_languages
    from core.utils import open_font_safe
    from PIL import Image, ImageDraw, ImageFont

    # ========== 高清参数 ==========
    CHAR_SIZE = 42
    LINE_SPACING = 12
    COLUMN_SPACING = 60
    MARGIN_TOP = 60
    MARGIN_BOTTOM = 60
    MARGIN_LEFT = 60
    MARGIN_RIGHT = 60
    TARGET_WIDTH = 1200
    NUM_COLUMNS = 12           # 标题 + 作者 + 10句内容
    # =============================

    font = open_font_safe(font_path)
    try:
        cmap = get_best_cmap(font)
        supported_langs = get_supported_languages(font)
        priority = ['简', '繁', '日', '韩', '英']
        selected_lang = None
        for lang in priority:
            if lang in supported_langs:
                selected_lang = lang
                break
        if not selected_lang:
            selected_lang = '英'

        poem = POEMS.get(selected_lang, POEMS['英'])
        title = poem['title']
        author = poem['author']
        lines = poem['lines'][:10]   # 取前10句
        columns = [title, author] + lines   # 共12列

        # 过滤不支持的字符（保留换行符，但每句没有换行）
        def filter_text(text, cmap):
            result = []
            for ch in text:
                if ch == '\n':
                    result.append('\n')
                elif ord(ch) in cmap:
                    result.append(ch)
                else:
                    result.append('□')
            return ''.join(result)

        filtered_columns = []
        for col in columns:
            filtered_col = filter_text(col, cmap)
            if filtered_col.replace('□', '').strip() == '' and col.strip() != '':
                filtered_col = '□' * len(col)   # 全方框占位
            filtered_columns.append(filtered_col)

        # 如果所有列都无效，降级为英文
        if all(c.replace('□', '').strip() == '' for c in filtered_columns):
            poem = POEMS['英']
            title = poem['title']
            author = poem['author']
            lines = poem['lines'][:10]
            filtered_columns = [title, author] + lines

        # 加载字体
        try:
            pil_font = ImageFont.truetype(font_path, CHAR_SIZE)
        except:
            pil_font = ImageFont.load_default()

        # 计算图片高度（取所有列中最大字符数）
        max_chars = max(len(col) for col in filtered_columns)
        content_height = max_chars * (CHAR_SIZE + LINE_SPACING) - LINE_SPACING
        img_height = content_height + MARGIN_TOP + MARGIN_BOTTOM
        img_height = max(img_height, 600)

        # 计算图片宽度（固定12列）
        total_width = MARGIN_LEFT + MARGIN_RIGHT + NUM_COLUMNS * (CHAR_SIZE + COLUMN_SPACING)
        img_width = max(total_width, TARGET_WIDTH)

        img = Image.new('RGB', (img_width, img_height), color=(245, 247, 250))
        draw = ImageDraw.Draw(img)

        for col_idx, line in enumerate(filtered_columns):
            x = MARGIN_LEFT + col_idx * (CHAR_SIZE + COLUMN_SPACING)
            y = MARGIN_TOP
            for ch in line:
                draw.text((x, y), ch, fill=(0, 0, 0), font=pil_font)
                y += CHAR_SIZE + LINE_SPACING

        img.save(output_path)
        print(f"竖排预览图已生成: {output_path} (12列, 宽度{img_width}px, 高度{img_height}px)")
    finally:
        font.close()


def generate_lang_preview(font_path: str, output_path: str, lang_code: str):
    import random
    from core.font_parser import get_best_cmap
    from core.utils import open_font_safe
    from PIL import Image, ImageDraw, ImageFont
    from config import POEMS, PREVIEW_WIDTH

    # 详情页预览图参数
    CHAR_SIZE = 42
    LINE_SPACING = 12
    COLUMN_SPACING = 60
    MARGIN_TOP = 60
    MARGIN_BOTTOM = 60
    MARGIN_LEFT = 120
    MARGIN_RIGHT = 60
    TARGET_WIDTH = PREVIEW_WIDTH   # 通常为 1200
    NUM_COLUMNS = 12
    FIXED_HEIGHT = 800

    # 获取诗词
    poems_list = POEMS.get(lang_code, POEMS.get('英', []))
    if not poems_list:
        poems_list = POEMS.get('英', [])
    poem = random.choice(poems_list) if poems_list else {'title': 'No Poem', 'author': 'Unknown', 'lines': ['']*10}
    title = poem['title']
    author = poem['author']
    lines = poem['lines'][:10]
    columns = [title, author] + lines

    font = open_font_safe(font_path)
    try:
        cmap = get_best_cmap(font)

        def filter_text(text, cmap):
            result = []
            for ch in text:
                if ch == '\n':
                    result.append('\n')
                elif ord(ch) in cmap:
                    result.append(ch)
                else:
                    result.append('□')
            return ''.join(result)

        filtered_columns = []
        for col in columns:
            filtered_col = filter_text(col, cmap)
            if filtered_col.replace('□', '').strip() == '' and col.strip() != '':
                filtered_col = '□' * len(col)
            filtered_columns.append(filtered_col)

        if all(c.replace('□', '').strip() == '' for c in filtered_columns):
            default_poem = POEMS.get('英', [{}])[0]
            title = default_poem.get('title', '')
            author = default_poem.get('author', '')
            lines = default_poem.get('lines', [''])[:10]
            columns = [title, author] + lines
            filtered_columns = [filter_text(col, cmap) for col in columns]

        try:
            pil_font = ImageFont.truetype(font_path, CHAR_SIZE)
        except:
            pil_font = ImageFont.load_default()

        # 计算垂直居中偏移（所有语言通用）
        max_chars = max(len(col) for col in filtered_columns)
        content_height = max_chars * (CHAR_SIZE + LINE_SPACING) - LINE_SPACING
        y_offset = max((FIXED_HEIGHT - content_height) // 2, 20)

        if lang_code == '英':
            # 英文横排：宽度根据最长行计算
            # 先创建临时图片用于测量
            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            max_line_width = 0
            for line in filtered_columns:
                bbox = temp_draw.textbbox((0, 0), line, font=pil_font)
                width = bbox[2] - bbox[0]
                if width > max_line_width:
                    max_line_width = width
            img_width = max(max_line_width + MARGIN_LEFT + MARGIN_RIGHT, TARGET_WIDTH)
            line_height = CHAR_SIZE + LINE_SPACING
            total_lines = len(filtered_columns)
            content_height = total_lines * line_height
            y_offset = max((FIXED_HEIGHT - content_height) // 2, 20)

            img = Image.new('RGB', (img_width, FIXED_HEIGHT), color=(245, 247, 250))
            draw = ImageDraw.Draw(img)
            y = y_offset
            for line in filtered_columns:
                bbox = draw.textbbox((0, 0), line, font=pil_font)
                line_width = bbox[2] - bbox[0]
                x = (img_width - line_width) // 2
                draw.text((x, y), line, fill=(0, 0, 0), font=pil_font)
                y += line_height
        else:
            # 竖排：宽度固定基于列数
            content_width = MARGIN_LEFT + MARGIN_RIGHT + NUM_COLUMNS * (CHAR_SIZE + COLUMN_SPACING)
            img_width = max(content_width, TARGET_WIDTH)
            offset_x = (img_width - content_width) // 2
            img = Image.new('RGB', (img_width, FIXED_HEIGHT), color=(245, 247, 250))
            draw = ImageDraw.Draw(img)
            for col_idx, line in enumerate(filtered_columns):
                x = offset_x + MARGIN_LEFT + col_idx * (CHAR_SIZE + COLUMN_SPACING)
                y = y_offset
                for ch in line:
                    draw.text((x, y), ch, fill=(0, 0, 0), font=pil_font)
                    y += CHAR_SIZE + LINE_SPACING

        img.save(output_path)
        print(f"生成语言 {lang_code} 预览图: {output_path} (宽度{img_width}px, 高度{FIXED_HEIGHT}px)")
    finally:
        font.close()

SHAPE_FUNCTIONS_DICT = {name: func for name, func in SHAPE_FUNCTIONS}