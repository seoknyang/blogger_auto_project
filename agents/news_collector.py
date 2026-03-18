import re
import feedparser
import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus
from config import (
    GOOGLE_NEWS_IT_URL, GOOGLE_NEWS_ECONOMY_URL, GOOGLE_NEWS_ELECTRONICS_URL,
    GOOGLE_NEWS_LIFE_URL, GOOGLE_NEWS_WORLD_URL, GOOGLE_NEWS_SOCIETY_URL,
    NAVER_NEWS_IT_URL, NAVER_NEWS_ECONOMY_URL, NAVER_NEWS_SOCIETY_URL,
    NAVER_NEWS_LIFE_URL, NAVER_NEWS_WORLD_URL,
    NEWS_PER_CATEGORY, CATEGORY_SCHEDULE,
)

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
_LIFE_HINTS = {
    "음식", "맛집", "레시피", "건강", "다이어트", "운동", "여행", "패션",
    "뷰티", "육아", "결혼", "인테리어", "반려동물", "취미", "문화", "영화",
    "드라마", "음악", "공연", "전시", "책", "독서", "카페", "라이프스타일",
}
_WORLD_HINTS = {
    "미국", "중국", "일본", "유럽", "러시아", "북한", "외교", "국제",
    "UN", "NATO", "G7", "G20", "전쟁", "분쟁", "제재", "조약",
    "트럼프", "바이든", "시진핑", "푸틴", "글로벌", "세계",
}
_SOCIETY_HINTS = {
    "사회", "정치", "정부", "국회", "대통령", "여당", "야당", "법원",
    "검찰", "경찰", "사건", "사고", "재난", "환경", "기후", "교육",
    "복지", "고용", "취업", "인구", "저출생", "고령화", "의료", "병원",
}

# 카테고리별 소스 정의: (구글폴백URL, 네이버RSS URL or None)
_SOURCES = {
    "IT":       (GOOGLE_NEWS_IT_URL,          NAVER_NEWS_IT_URL),
    "전자기기": (GOOGLE_NEWS_ELECTRONICS_URL, None),
    "경제":     (GOOGLE_NEWS_ECONOMY_URL,     NAVER_NEWS_ECONOMY_URL),
    "생활문화": (GOOGLE_NEWS_LIFE_URL,        NAVER_NEWS_LIFE_URL),
    "세계":     (GOOGLE_NEWS_WORLD_URL,       NAVER_NEWS_WORLD_URL),
    "사회":     (GOOGLE_NEWS_SOCIETY_URL,     NAVER_NEWS_SOCIETY_URL),
}

# 트렌딩 분류용 힌트 맵
_HINTS_MAP = {
    "IT":       _IT_HINTS,
    "전자기기": _ELECTRONICS_HINTS,
    "경제":     _ECONOMY_HINTS,
    "생활문화": _LIFE_HINTS,
    "세계":     _WORLD_HINTS,
    "사회":     _SOCIETY_HINTS,
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


def _categorize_trending(keywords: list[str], categories: list[str]) -> dict[str, list[str]]:
    """트렌딩 키워드를 오늘의 활성 카테고리 버킷으로 분류."""
    buckets: dict[str, list[str]] = {cat: [] for cat in categories}
    # 분류 우선순위: 전자기기 → IT → 나머지
    priority = ["전자기기", "IT"] + [c for c in categories if c not in ("전자기기", "IT")]
    for kw in keywords:
        kw_upper = kw.upper()
        for cat in priority:
            if cat not in buckets:
                continue
            hints = _HINTS_MAP.get(cat, set())
            if any(hint.upper() in kw_upper for hint in hints):
                buckets[cat].append(kw)
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


def get_today_schedule() -> list[tuple[str, int]]:
    """오늘 요일에 맞는 카테고리 스케줄 반환. [(카테고리, 후보수), ...]"""
    from datetime import date
    return CATEGORY_SCHEDULE[date.today().weekday()]


def collect(trending: list[str] | None = None) -> list[dict]:
    """오늘 스케줄 카테고리 뉴스 수집. 구글 + 네이버 RSS 병합."""
    schedule = get_today_schedule()
    categories = [cat for cat, _ in schedule]
    logger.info(f"뉴스 수집 시작 — 오늘 카테고리: {categories}")

    buckets = _categorize_trending(trending, categories) if trending else {cat: [] for cat in categories}
    if trending:
        logger.info(f"트렌딩 분류 → " + ", ".join(f"{c}: {buckets[c][:2]}" for c in categories))

    per_source = max(8, NEWS_PER_CATEGORY // 2)

    def _fetch(category: str) -> list[dict]:
        results = []
        google_fallback, naver_url = _SOURCES.get(category, (None, None))

        # 네이버 RSS
        if naver_url:
            naver_items = _parse_feed(naver_url, category, per_source)
            logger.info(f"  [{category}] 네이버 RSS: {len(naver_items)}개")
            results.extend(naver_items)

        # 구글 RSS (트렌딩 키워드 있으면 동적, 없으면 폴백)
        kws = buckets.get(category, [])
        if kws:
            query = " OR ".join(kws[:3])
            google_url = _build_rss_url(query)
            logger.info(f"  [{category}] 구글 트렌딩 쿼리: {query}")
        else:
            google_url = google_fallback
            logger.info(f"  [{category}] 구글 폴백 URL 사용")

        if google_url:
            google_items = _parse_feed(google_url, category, per_source)
            logger.info(f"  [{category}] 구글 RSS: {len(google_items)}개")
            results.extend(google_items)

        return results

    all_news = []
    counts = {}
    for category in categories:
        items = _fetch(category)
        counts[category] = len(items)
        all_news.extend(items)

    all_news = _deduplicate(all_news)
    count_str = ", ".join(f"{c} {n}개" for c, n in counts.items())
    logger.info(f"수집 완료: {count_str} → 중복 제거 후 {len(all_news)}개")
    return all_news
