import re
import logging
import requests
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET

logger = logging.getLogger(__name__)

NAVER_SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_prices(keywords: list[str], display: int = 3) -> dict[str, list[dict]]:
    """키워드별 네이버쇼핑 최저가 상위 결과 반환.

    Returns:
        {keyword: [{"name": str, "lprice": int, "mall": str}, ...]}
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        logger.warning("네이버 쇼핑 API 키 미설정 — 가격 조회 건너뜀")
        return {}

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    result = {}
    for kw in keywords:
        try:
            resp = requests.get(
                NAVER_SHOP_URL,
                headers=headers,
                params={"query": kw, "display": display * 5, "sort": "sim"},
                timeout=5,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            # 악세서리·통신사 공시지원금 등 비정상 가격 필터링 (50,000원 미만)
            filtered = [
                {
                    "name": _strip_html(item.get("title", "")),
                    "lprice": int(item.get("lprice", 0)),
                    "mall": item.get("mallName", ""),
                    "image": item.get("image", ""),
                }
                for item in items
                if int(item.get("lprice", 0)) >= 50_000
            ][:display]
            result[kw] = filtered
            logger.info(f"  가격 조회 [{kw}]: {len(result[kw])}개")
        except Exception as e:
            logger.warning(f"  가격 조회 실패 [{kw}]: {e}")
            result[kw] = []
    return result


def fetch_product_image(product_name: str) -> str | None:
    """제품명으로 네이버쇼핑 대표 이미지 URL 1개 반환."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return None
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    try:
        resp = requests.get(
            NAVER_SHOP_URL,
            headers=headers,
            params={"query": product_name, "display": 5, "sort": "sim"},
            timeout=5,
        )
        resp.raise_for_status()
        for item in resp.json().get("items", []):
            if int(item.get("lprice", 0)) >= 50_000 and item.get("image"):
                return item["image"]
    except Exception as e:
        logger.warning(f"  제품 이미지 조회 실패 [{product_name}]: {e}")
    return None


def format_price_context(price_data: dict[str, list[dict]]) -> str:
    """LLM 프롬프트에 삽입할 가격 데이터 텍스트. 데이터 없으면 빈 문자열 반환."""
    if not any(items for items in price_data.values()):
        return ""
    lines = [
        "[실시간 네이버쇼핑 최저가 (오늘 기준) — 글에 이 수치를 그대로 반영하세요]"
    ]
    for kw, items in price_data.items():
        if not items:
            continue
        lines.append(f"\n▶ {kw}")
        for item in items:
            price_str = f"{item['lprice']:,}원" if item["lprice"] else "가격정보 없음"
            lines.append(f"  - {item['name']} | 최저가 {price_str} ({item['mall']})")
    return "\n".join(lines)
