import feedparser
import logging
from datetime import datetime, timezone
from config import GOOGLE_NEWS_IT_URL, GOOGLE_NEWS_ECONOMY_URL, NEWS_PER_CATEGORY

logger = logging.getLogger(__name__)


def _parse_feed(url: str, category: str, limit: int) -> list[dict]:
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:limit]:
        summary = entry.get("summary", "")
        # feedparser가 가져오는 summary에 HTML 태그 제거
        import re
        summary = re.sub(r"<[^>]+>", "", summary).strip()

        results.append({
            "title": entry.get("title", "").strip(),
            "summary": summary[:500],
            "link": entry.get("link", ""),
            "category": category,
            "published": entry.get("published", str(datetime.now(timezone.utc))),
        })
    return results


def _deduplicate(news_list: list[dict]) -> list[dict]:
    """제목 앞 20자 기준으로 중복 제거."""
    seen = set()
    unique = []
    for item in news_list:
        key = item["title"][:20]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def collect() -> list[dict]:
    """IT/경제 뉴스 수집 후 합쳐서 반환."""
    logger.info("뉴스 수집 시작")
    it_news = _parse_feed(GOOGLE_NEWS_IT_URL, "IT", NEWS_PER_CATEGORY)
    economy_news = _parse_feed(GOOGLE_NEWS_ECONOMY_URL, "경제", NEWS_PER_CATEGORY)

    all_news = it_news + economy_news
    all_news = _deduplicate(all_news)

    logger.info(f"수집 완료: IT {len(it_news)}개, 경제 {len(economy_news)}개 → 중복 제거 후 {len(all_news)}개")
    return all_news
