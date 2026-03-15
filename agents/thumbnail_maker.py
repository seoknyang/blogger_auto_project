import os
import base64
import logging
import requests
from PIL import Image, ImageDraw, ImageFont
from config import FONT_PATH, THUMBNAILS_DIR, IMGBB_API_KEY

logger = logging.getLogger(__name__)

# 카테고리별 색상 테마
THEMES = {
    "IT": {
        "bg": (30, 64, 175),       # 진한 파란색
        "accent": (96, 165, 250),  # 밝은 파란색
        "text": (255, 255, 255),   # 흰색
        "tag_bg": (96, 165, 250),
        "tag_text": (255, 255, 255),
    },
    "경제": {
        "bg": (6, 95, 70),         # 진한 초록색
        "accent": (52, 211, 153),  # 밝은 초록색
        "text": (255, 255, 255),   # 흰색
        "tag_bg": (52, 211, 153),
        "tag_text": (255, 255, 255),
    },
}
DEFAULT_THEME = THEMES["IT"]

WIDTH, HEIGHT = 1200, 628
PADDING = 60


_FALLBACK_FONTS = [
    FONT_PATH,
    "C:/Windows/Fonts/malgunbd.ttf",   # 맑은 고딕 Bold (Windows 기본)
    "C:/Windows/Fonts/malgun.ttf",     # 맑은 고딕 Regular
    "C:/Windows/Fonts/gulim.ttc",      # 굴림
]


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FALLBACK_FONTS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    logger.warning("한글 폰트를 찾을 수 없음 - 기본 폰트 사용 (한글 깨짐)")
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """텍스트를 max_width에 맞게 줄바꿈."""
    words = text
    lines = []
    # 한글은 글자 단위로 줄바꿈
    current_line = ""
    for char in words:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def create_thumbnail(candidate: dict, output_path: str):
    """후보 글 데이터로 썸네일 이미지 생성."""
    category = candidate.get("category", "IT")
    theme = THEMES.get(category, DEFAULT_THEME)
    title = candidate.get("title", "")

    img = Image.new("RGB", (WIDTH, HEIGHT), color=theme["bg"])
    draw = ImageDraw.Draw(img)

    # 하단 accent 바
    draw.rectangle([(0, HEIGHT - 8), (WIDTH, HEIGHT)], fill=theme["accent"])

    # 좌측 세로 accent 바
    draw.rectangle([(0, 0), (8, HEIGHT)], fill=theme["accent"])

    # 카테고리 태그
    tag_font = _get_font(28)
    tag_text = f"  {category}  "
    tag_bbox = tag_font.getbbox(tag_text)
    tag_w = tag_bbox[2] - tag_bbox[0] + 20
    tag_h = tag_bbox[3] - tag_bbox[1] + 16
    draw.rounded_rectangle(
        [(PADDING + 8, PADDING), (PADDING + 8 + tag_w, PADDING + tag_h)],
        radius=6,
        fill=theme["tag_bg"],
    )
    draw.text((PADDING + 18, PADDING + 8), category, font=tag_font, fill=theme["tag_text"])

    # 제목 텍스트
    title_font = _get_font(52)
    max_text_width = WIDTH - PADDING * 2 - 20
    lines = _wrap_text(title, title_font, max_text_width)
    lines = lines[:4]  # 최대 4줄

    title_y = PADDING + tag_h + 40
    line_height = 68
    for line in lines:
        draw.text((PADDING + 8, title_y), line, font=title_font, fill=theme["text"])
        title_y += line_height

    # 하단 블로그명
    blog_font = _get_font(26)
    blog_text = "Auto Blog"
    draw.text((PADDING + 8, HEIGHT - 60), blog_text, font=blog_font, fill=theme["accent"])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    logger.info(f"썸네일 저장: {output_path}")


def upload_to_imgbb(image_path: str) -> str | None:
    """imgbb에 이미지 업로드 후 공개 URL 반환. 실패 시 None."""
    if not IMGBB_API_KEY:
        logger.warning("IMGBB_API_KEY 없음 - 이미지 업로드 건너뜀")
        return None
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": encoded},
            timeout=30,
        )
        resp.raise_for_status()
        url = resp.json()["data"]["url"]
        logger.info(f"imgbb 업로드 완료: {url}")
        return url
    except Exception as e:
        logger.error(f"imgbb 업로드 실패: {e}")
        return None


def generate_thumbnails(candidates: list[dict]) -> list[dict]:
    """후보 글 목록에 thumbnail_path 추가 후 반환."""
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)
    for candidate in candidates:
        path = os.path.join(THUMBNAILS_DIR, f"candidate_{candidate['id']}.png")
        create_thumbnail(candidate, path)
        candidate["thumbnail_path"] = path
    return candidates
