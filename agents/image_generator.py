import re
import base64
import logging
import requests
import anthropic
from config import IMGBB_API_KEY, CLAUDE_API_KEY, PEXELS_API_KEY

logger = logging.getLogger(__name__)


def _to_english_prompt(korean_topic: str, context: str = "") -> str:
    """Claude Haiku로 한글 주제를 영어 검색 키워드로 변환 (최대 5단어)."""
    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=30,
            messages=[{
                "role": "user",
                "content": (
                    f"Convert this Korean topic to 3-5 English keywords for photo search. "
                    f"Topic: {korean_topic}. Context: {context}. "
                    f"Reply with English keywords only, comma-separated, no explanation."
                ),
            }],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        logger.warning(f"프롬프트 변환 실패: {e}")
        return korean_topic


def _search_pexels(query: str, used_urls: set[str] | None = None) -> tuple[bytes, str] | tuple[None, None]:
    """Pexels에서 쿼리로 사진 검색. 중복 제외. (bytes, url) 반환."""
    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY 없음 - 이미지 검색 건너뜀")
        return None, None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 10, "orientation": "landscape"},
            timeout=30,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            logger.warning(f"Pexels 검색 결과 없음: {query}")
            return None, None

        for photo in photos:
            photo_url = photo["src"]["large2x"]
            if used_urls and photo_url in used_urls:
                continue
            img_resp = requests.get(photo_url, timeout=30)
            img_resp.raise_for_status()
            return img_resp.content, photo_url

        return None, None
    except Exception as e:
        logger.error(f"Pexels 이미지 가져오기 실패: {e}")
        return None, None


def _upload_bytes(image_bytes: bytes) -> str | None:
    """이미지 bytes를 imgbb에 업로드 후 URL 반환."""
    if not IMGBB_API_KEY:
        return None
    try:
        encoded = base64.b64encode(image_bytes).decode()
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": encoded},
            timeout=30,
        )
        resp.raise_for_status()
        url = resp.json()["data"]["url"]
        logger.info(f"이미지 업로드 완료: {url}")
        return url
    except Exception as e:
        logger.error(f"imgbb 업로드 실패: {e}")
        return None


def generate_thumbnail_url(title: str, category: str, keywords: list[str], used_urls: set[str] | None = None) -> str | None:
    """제목 기반 썸네일 이미지 검색 후 imgbb URL 반환."""
    en_keywords = _to_english_prompt(title, context=category)
    logger.info(f"썸네일 이미지 검색 중 (Pexels): {en_keywords}")
    image_bytes, photo_url = _search_pexels(en_keywords, used_urls)
    if not image_bytes:
        return None
    if used_urls is not None and photo_url:
        used_urls.add(photo_url)
    return _upload_bytes(image_bytes)


def inject_content_images(content_html: str, title: str, used_urls: set[str] | None = None) -> str:
    """모든 h2 소제목 뒤에 관련 이미지 삽입 (중복 제외)."""
    if used_urls is None:
        used_urls = set()

    h2_pattern = re.compile(r"(</h2>)", re.IGNORECASE)
    total = len(h2_pattern.findall(content_html))
    if total == 0:
        return content_html

    offset = 0
    result = content_html
    inserted = 0

    for i in range(total):
        m = h2_pattern.search(result, offset)
        if not m:
            break

        h2_start = result.rfind("<h2", 0, m.start())
        section_text = re.sub(r"<[^>]+>", "", result[h2_start:m.end()])[:80]

        en_keywords = _to_english_prompt(section_text, context=title)
        logger.info(f"본문 이미지 [{i+1}/{total}] 검색 중 (Pexels): {en_keywords}")
        image_bytes, photo_url = _search_pexels(en_keywords, used_urls)

        if image_bytes:
            url = _upload_bytes(image_bytes)
            if url:
                used_urls.add(photo_url)
                img_html = (
                    f'\n<div style="text-align:center;margin:24px 0;">'
                    f'<img src="{url}" alt="{section_text.strip()}" '
                    f'style="max-width:100%;height:auto;border-radius:8px;'
                    f'box-shadow:0 2px 8px rgba(0,0,0,0.15);"/>'
                    f"</div>\n"
                )
                insert_pos = m.end()
                result = result[:insert_pos] + img_html + result[insert_pos:]
                offset = insert_pos + len(img_html)
                inserted += 1
                continue

        offset = m.end()

    logger.info(f"본문 이미지 삽입 완료: {inserted}/{total}개")
    return result
