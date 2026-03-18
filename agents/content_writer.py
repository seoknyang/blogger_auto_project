import json
import logging
import anthropic
from config import CLAUDE_API_KEY, IT_COUNT, ELECTRONICS_COUNT, ECONOMY_COUNT

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are a practical Korean IT/economy blogger who writes honest, helpful reviews and guides.
Write original blog posts in Korean based on news data.

Core writing style:
- Be specific, not vague. Mention REAL product model names, prices (원화), specs, and brands.
- Give concrete recommendations: "이 상황이면 A제품, 저 상황이면 B제품" with reasons.
- Include actual value comparisons (가성비): price vs performance trade-offs.
- Use relatable real-life examples that Korean readers identify with (직장인, 대학생, 크리에이터 등).
- Avoid generic platitudes. Every sentence should give the reader actionable information.

Rules:
1. Never copy news verbatim (copyright violation)
2. Use news only as background; write as if giving advice to a friend
3. Mention specific products/models/brands available in Korea where relevant
4. Write SEO-optimized titles (30-50 Korean characters)
5. Use HTML format (Blogger-compatible)
6. Body must be at least 1000 Korean characters
7. Structure with subheadings (h2, h3)
8. End with a clear recommendation or takeaway section
9. All output (title, preview, content) must be written in Korean"""

PLAN_PROMPT_TEMPLATE = """Select the best blog post topic for the {category} category based on the following news.
Prioritize topics overlapping with trending keywords. If no overlap, pick the most interesting topic.

Today's date: {current_date}. Only reference events, products, or trends relevant to this date.

Trending keywords in Korea right now:
{trending}

News data:
{news_data}

Already used topics (do NOT overlap): {used_topics}

Respond with JSON only (no other text):
{{
  "id": {post_id},
  "title": "SEO-optimized Korean title (30-50 characters)",
  "category": "{category}",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "preview": "2-3 sentence Korean preview of what the post will cover"
}}"""

DRAFT_PROMPT_TEMPLATE = """Write blog post #{post_id} about the {category} category based on the following news.
Prioritize topics that overlap with the trending keywords. If no overlap, choose the most interesting topic.

Today's date: {current_date}. Only reference events and products relevant to this date. Do NOT mention dates or years before {current_date}.

Trending keywords in Korea right now:
{trending}

News data:
{news_data}

Already used topics (do NOT overlap): {used_topics}

IMPORTANT content guidelines:
- If the topic involves products (laptops, phones, tablets, etc.): name at least 3 specific models with approximate Korean market prices and key pros/cons of each.
- If the topic is a comparison/recommendation: give a clear verdict per use case (e.g., 대학생 → XX, 직장인 → YY).
- If the topic is IT/economy news: explain the real-world impact on Korean consumers and give practical advice.
- Do NOT just describe what exists — tell readers what to DO with that information.

Respond with JSON only (no other text):
{{
  "id": {post_id},
  "title": "SEO-optimized Korean title",
  "category": "{category}",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "preview": "2-3 sentence Korean preview",
  "content_html": "<h2>subheading</h2><p>Korean body...</p>"
}}"""

WRITE_PROMPT_TEMPLATE = """Write a full blog post for this planned topic.

Today's date: {current_date}. Only reference events and products relevant to this date. Do NOT mention dates before {current_date}.

Topic: {title}
Category: {category}
Keywords: {keywords}

Trending keywords in Korea right now:
{trending}

Reference news (background only, do NOT copy verbatim):
{news_data}

Content guidelines:
- If topic involves products: name at least 3 specific models with Korean market prices and pros/cons.
- If comparison/recommendation: give verdict per use case (대학생, 직장인, 크리에이터 등).
- If IT/economy news: explain real-world impact on Korean consumers with practical advice.
- Body must be at least 1000 Korean characters.
- Use h2/h3 subheadings, end with a clear recommendation or takeaway.

Respond with JSON only (no other text):
{{
  "id": {post_id},
  "title": "SEO-optimized Korean title",
  "category": "{category}",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "preview": "2-3 sentence Korean preview",
  "content_html": "<h2>subheading</h2><p>Korean body...</p>"
}}"""


def _format_news_for_prompt(news_list: list[dict], category: str) -> str:
    lines = []
    for i, news in enumerate(
        [n for n in news_list if n["category"] == category], 1
    ):
        published = news.get("published", "")[:10]  # YYYY-MM-DD
        lines.append(f"[{i}] ({published}) {news['title']}")
        if news.get("summary"):
            lines.append(f"    요약: {news['summary']}")
    return "\n".join(lines)


def _escape_control_chars(text: str) -> str:
    """JSON 문자열 값 내부의 literal 제어 문자(개행 등)를 이스케이프."""
    result = []
    in_string = False
    escape_next = False
    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
        elif char == "\\":
            result.append(char)
            escape_next = True
        elif char == '"':
            result.append(char)
            in_string = not in_string
        elif in_string and char == "\n":
            result.append("\\n")
        elif in_string and char == "\r":
            result.append("\\r")
        elif in_string and char == "\t":
            result.append("\\t")
        else:
            result.append(char)
    return "".join(result)


def _parse_json(response_text: str) -> dict:
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()
    response_text = _escape_control_chars(response_text)
    return json.loads(response_text)


def _write_draft(client: anthropic.Anthropic, post_id: int, category: str,
                 news_text: str, used_topics: list[str], trending: list[str]) -> dict:
    """Haiku 모델로 초안 작성."""
    from datetime import date
    current_date = date.today().strftime("%Y-%m-%d")
    user_prompt = DRAFT_PROMPT_TEMPLATE.format(
        current_date=current_date,
        post_id=post_id,
        category=category,
        news_data=news_text,
        used_topics=", ".join(used_topics) if used_topics else "없음",
        trending=", ".join(trending) if trending else "없음",
    )
    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _parse_json(message.content[0].text.strip())


def _plan_candidate(client: anthropic.Anthropic, post_id: int, category: str,
                    news_text: str, used_topics: list[str], trending: list[str]) -> dict:
    """Haiku 모델로 글 제목/키워드/미리보기만 선정 (본문 미작성)."""
    from datetime import date
    current_date = date.today().strftime("%Y-%m-%d")
    user_prompt = PLAN_PROMPT_TEMPLATE.format(
        current_date=current_date,
        post_id=post_id,
        category=category,
        news_data=news_text,
        used_topics=", ".join(used_topics) if used_topics else "없음",
        trending=", ".join(trending) if trending else "없음",
    )
    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _parse_json(message.content[0].text.strip())



def plan_candidates(news_list: list[dict], trending: list[str] | None = None) -> list[dict]:
    """IT 1 + 전자기기 1 + 경제 2 총 4개 후보 제목/키워드/미리보기만 선정. 본문은 미작성."""
    logger.info("Claude API로 후보 선정 시작 (Haiku) - 제목/키워드만")
    trending = trending or []
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    it_news = _format_news_for_prompt(news_list, "IT")
    electronics_news = _format_news_for_prompt(news_list, "전자기기")
    economy_news = _format_news_for_prompt(news_list, "경제")

    plan = (
        [(i + 1, "IT", it_news) for i in range(IT_COUNT)] +
        [(IT_COUNT + i + 1, "전자기기", electronics_news) for i in range(ELECTRONICS_COUNT)] +
        [(IT_COUNT + ELECTRONICS_COUNT + i + 1, "경제", economy_news) for i in range(ECONOMY_COUNT)]
    )

    candidates = []
    used_topics: list[str] = []

    total = IT_COUNT + ELECTRONICS_COUNT + ECONOMY_COUNT
    for post_id, category, news_text in plan:
        logger.info(f"  [{post_id}/{total}] {category} 후보 선정 중...")
        try:
            candidate = _plan_candidate(client, post_id, category, news_text, used_topics, trending)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"후보 {post_id} 선정 실패: {e}")
            continue

        candidates.append(candidate)
        used_topics.append(candidate.get("title", f"post{post_id}"))
        logger.info(f"  완료: {candidate.get('title', '')[:30]}")

    logger.info(f"후보 선정 완료: {len(candidates)}개 (본문 미작성)")
    return candidates


def write_single(candidate: dict, news_list: list[dict], trending: list[str] | None = None) -> dict:
    """선택된 후보 1개의 본문(content_html) 작성. 사용자 선택 후 호출."""
    logger.info(f"글 작성 시작: {candidate.get('title', '')[:30]}")
    trending = trending or []
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    from datetime import date
    current_date = date.today().strftime("%Y-%m-%d")
    category = candidate.get("category", "IT")
    news_text = _format_news_for_prompt(news_list, category)

    user_prompt = WRITE_PROMPT_TEMPLATE.format(
        current_date=current_date,
        post_id=candidate["id"],
        title=candidate["title"],
        category=category,
        keywords=", ".join(candidate.get("keywords", [])),
        news_data=news_text,
        trending=", ".join(trending) if trending else "없음",
    )
    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    result = _parse_json(message.content[0].text.strip())
    logger.info(f"글 작성 완료: {result.get('title', '')[:30]}")
    return result


def write(news_list: list[dict], trending: list[str] | None = None) -> list[dict]:
    """IT 1 + 전자기기 1 + 경제 2 총 4개 후보 작성. Haiku 모델 사용."""
    logger.info("Claude API로 글 작성 시작 (Haiku)")
    trending = trending or []
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    it_news = _format_news_for_prompt(news_list, "IT")
    electronics_news = _format_news_for_prompt(news_list, "전자기기")
    economy_news = _format_news_for_prompt(news_list, "경제")

    plan = (
        [(i + 1, "IT", it_news) for i in range(IT_COUNT)] +
        [(IT_COUNT + i + 1, "전자기기", electronics_news) for i in range(ELECTRONICS_COUNT)] +
        [(IT_COUNT + ELECTRONICS_COUNT + i + 1, "경제", economy_news) for i in range(ECONOMY_COUNT)]
    )

    candidates = []
    used_topics: list[str] = []

    total = IT_COUNT + ELECTRONICS_COUNT + ECONOMY_COUNT
    for post_id, category, news_text in plan:
        logger.info(f"  [{post_id}/{total}] {category} 초안 작성 중 (Haiku)...")
        try:
            draft = _write_draft(client, post_id, category, news_text, used_topics, trending)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"글 {post_id} 초안 실패: {e}")
            continue

        candidates.append(draft)
        used_topics.append(draft.get("title", f"post{post_id}"))
        logger.info(f"  완료: {draft.get('title', '')[:30]}")

    logger.info(f"글 작성 완료: {len(candidates)}개 (IT {IT_COUNT} + 전자기기 {ELECTRONICS_COUNT} + 경제 {ECONOMY_COUNT}, 모델: Haiku)")
    return candidates
