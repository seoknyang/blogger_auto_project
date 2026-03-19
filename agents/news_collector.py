import re
import feedparser
import logging
from datetime import datetime, timezone
from config import (
    GOOGLE_NEWS_IT_URL, GOOGLE_NEWS_ECONOMY_URL, GOOGLE_NEWS_ELECTRONICS_URL,
    GOOGLE_NEWS_LIFE_URL, GOOGLE_NEWS_LIFE_INFO_URL, GOOGLE_NEWS_WORLD_URL, GOOGLE_NEWS_SOCIETY_URL,
    NAVER_NEWS_IT_URL, NAVER_NEWS_ECONOMY_URL, NAVER_NEWS_SOCIETY_URL,
    NAVER_NEWS_LIFE_URL, NAVER_NEWS_WORLD_URL,
    NEWS_PER_CATEGORY, CATEGORY_SCHEDULE,
)

logger = logging.getLogger(__name__)

# 카테고리별 소스 정의: (구글RSS URL, 네이버RSS URL or None)
# 트렌딩 키워드는 LLM에 전체 전달 — 힌트 필터 없이 LLM이 주제를 자유롭게 선택
_SOURCES = {
    "IT":       (GOOGLE_NEWS_IT_URL,          NAVER_NEWS_IT_URL),
    "전자기기": (GOOGLE_NEWS_ELECTRONICS_URL, None),
    "경제":     (GOOGLE_NEWS_ECONOMY_URL,     NAVER_NEWS_ECONOMY_URL),
    "생활문화": (GOOGLE_NEWS_LIFE_URL,        NAVER_NEWS_LIFE_URL),
    "세계":     (GOOGLE_NEWS_WORLD_URL,       NAVER_NEWS_WORLD_URL),
    "사회":     (GOOGLE_NEWS_SOCIETY_URL,     NAVER_NEWS_SOCIETY_URL),
    "생활정보": (GOOGLE_NEWS_LIFE_INFO_URL,   NAVER_NEWS_LIFE_URL),
}


def _parse_feed(url: str, category: str, limit: int) -> list[dict]:
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:limit]:
        summary = entry.get("summary", "")
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




def fetch_trending_keywords(limit: int = 20) -> list[str]:
    """Google Trends 한국 일별 트렌딩 키워드 반환."""
    url = "https://trends.google.com/trending/rss?geo=KR"
    try:
        feed = feedparser.parse(url)
        keywords = [entry.get("title", "").strip() for entry in feed.entries[:limit]]
        keywords = [k for k in keywords if k]
        logger.info(f"트렌딩 키워드 {len(keywords)}개 수집: {', '.join(keywords[:5])}...")
        return keywords
    except Exception as e:
        logger.warning(f"트렌딩 키워드 수집 실패: {e}")
        return []


def fetch_news_for_keyword(keyword: str, limit: int = 10) -> list[dict]:
    """특정 키워드로 구글 뉴스 RSS 검색. 후보 그라운딩용."""
    import urllib.parse
    query = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        results = _parse_feed(url, keyword, limit)
        logger.info(f"키워드 뉴스 [{keyword}]: {len(results)}개")
        return results
    except Exception as e:
        logger.warning(f"키워드 뉴스 수집 실패 [{keyword}]: {e}")
        return []


def get_today_schedule() -> list[tuple[str, int]]:
    """오늘 요일에 맞는 카테고리 스케줄 반환. [(카테고리, 후보수), ...]"""
    from datetime import date
    return CATEGORY_SCHEDULE[date.today().weekday()]


def collect(trending: list[str] | None = None) -> list[dict]:
    """오늘 스케줄 카테고리 뉴스 수집. 구글 + 네이버 RSS 병합.
    트렌딩 키워드는 LLM에 전체 전달하므로 수집 단계에서 필터링하지 않음."""
    schedule = get_today_schedule()
    categories = [cat for cat, _ in schedule]
    logger.info(f"뉴스 수집 시작 — 오늘 카테고리: {categories}")

    per_source = max(8, NEWS_PER_CATEGORY // 2)
    all_news = []
    counts = {}

    for category in categories:
        google_url, naver_url = _SOURCES.get(category, (None, None))
        results = []

        if naver_url:
            items = _parse_feed(naver_url, category, per_source)
            logger.info(f"  [{category}] 네이버 RSS: {len(items)}개")
            results.extend(items)

        if google_url:
            items = _parse_feed(google_url, category, per_source)
            logger.info(f"  [{category}] 구글 RSS: {len(items)}개")
            results.extend(items)

        counts[category] = len(results)
        all_news.extend(results)

    all_news = _deduplicate(all_news)
    count_str = ", ".join(f"{c} {n}개" for c, n in counts.items())
    logger.info(f"수집 완료: {count_str} → 중복 제거 후 {len(all_news)}개")
    return all_news
