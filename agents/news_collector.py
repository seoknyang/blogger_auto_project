import re
import feedparser
import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus
from config import GOOGLE_NEWS_IT_URL, GOOGLE_NEWS_ECONOMY_URL, GOOGLE_NEWS_ELECTRONICS_URL, NEWS_PER_CATEGORY

logger = logging.getLogger(__name__)

# 카테고리별 분류 힌트 키워드
_IT_HINTS = {
    "AI", "인공지능", "ChatGPT", "챗GPT", "GPT", "딥러닝", "머신러닝", "클라우드",
    "앱", "소프트웨어", "SW", "플랫폼", "데이터", "사이버", "해킹", "보안", "코딩",
    "구글", "애플", "메타", "마이크로소프트", "MS", "네이버", "카카오", "넥슨",
    "스타트업", "반도체", "칩", "파운드리", "삼성전자", "SK하이닉스", "엔비디아",
    "오픈AI", "OpenAI", "딥시크", "DeepSeek", "로봇", "자율주행", "드론", "클로드",
    "제미나이", "개발자",
}
_ELECTRONICS_HINTS = {
    "스마트폰", "노트북", "태블릿", "갤럭시", "아이폰", "iPhone", "iPad",
    "이어폰", "에어팟", "AirPods", "맥북", "MacBook", "픽셀", "Pixel",
    "TV", "모니터", "카메라", "게이밍", "PS5", "Xbox", "닌텐도",
    "전자기기", "가전", "웨어러블", "스마트워치", "워치", "충전기",
}
_ECONOMY_HINTS = {
    "주식", "코스피", "코스닥", "금리", "환율", "달러", "원화", "부동산",
    "물가", "인플레", "금융", "은행", "증시", "펀드", "ETF", "채권",
    "경제", "GDP", "수출", "무역", "관세", "세금", "예산", "재정",
    "코인", "비트코인", "암호화폐", "Fed", "연준", "한국은행", "나스닥",
    "s&p500",
}

# 카테고리별 폴백 쿼리 (트렌딩 매칭 실패 시)
_FALLBACK = {
    "IT": GOOGLE_NEWS_IT_URL,
    "전자기기": GOOGLE_NEWS_ELECTRONICS_URL,
    "경제": GOOGLE_NEWS_ECONOMY_URL,
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


def _build_rss_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=ko&gl=KR&ceid=KR:ko"


def _categorize_trending(keywords: list[str]) -> dict[str, list[str]]:
    """트렌딩 키워드를 IT/전자기기/경제 버킷으로 분류."""
    buckets: dict[str, list[str]] = {"IT": [], "전자기기": [], "경제": []}
    for kw in keywords:
        kw_upper = kw.upper()
        matched = False
        for hint in _ELECTRONICS_HINTS:
            if hint.upper() in kw_upper:
                buckets["전자기기"].append(kw)
                matched = True
                break
        if not matched:
            for hint in _IT_HINTS:
                if hint.upper() in kw_upper:
                    buckets["IT"].append(kw)
                    matched = True
                    break
        if not matched:
            for hint in _ECONOMY_HINTS:
                if hint.upper() in kw_upper:
                    buckets["경제"].append(kw)
                    break
    return buckets


def fetch_trending_keywords(limit: int = 20) -> list[str]:
    """Google Trends 한국 일별 트렌딩 키워드 반환."""
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
    try:
        feed = feedparser.parse(url)
        keywords = [entry.get("title", "").strip() for entry in feed.entries[:limit]]
        keywords = [k for k in keywords if k]
        logger.info(f"트렌딩 키워드 {len(keywords)}개 수집: {', '.join(keywords[:5])}...")
        return keywords
    except Exception as e:
        logger.warning(f"트렌딩 키워드 수집 실패: {e}")
        return []


def collect(trending: list[str] | None = None) -> list[dict]:
    """IT/전자기기/경제 뉴스 수집. 트렌딩 키워드가 있으면 동적 URL로 검색."""
    logger.info("뉴스 수집 시작")

    if trending:
        buckets = _categorize_trending(trending)
        logger.info(
            f"트렌딩 분류 → IT: {buckets['IT'][:3]}, "
            f"전자기기: {buckets['전자기기'][:3]}, 경제: {buckets['경제'][:3]}"
        )
    else:
        buckets = {"IT": [], "전자기기": [], "경제": []}

    def _fetch(category: str) -> list[dict]:
        kws = buckets.get(category, [])
        if kws:
            # 상위 3개 키워드로 OR 쿼리
            query = " OR ".join(kws[:3])
            url = _build_rss_url(query)
            logger.info(f"  [{category}] 트렌딩 쿼리: {query}")
        else:
            url = _FALLBACK[category]
            logger.info(f"  [{category}] 폴백 URL 사용")
        return _parse_feed(url, category, NEWS_PER_CATEGORY)

    it_news = _fetch("IT")
    electronics_news = _fetch("전자기기")
    economy_news = _fetch("경제")

    all_news = it_news + electronics_news + economy_news
    all_news = _deduplicate(all_news)

    logger.info(
        f"수집 완료: IT {len(it_news)}개, 전자기기 {len(electronics_news)}개, "
        f"경제 {len(economy_news)}개 → 중복 제거 후 {len(all_news)}개"
    )
    return all_news
