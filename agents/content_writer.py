import json
import logging
import anthropic
from config import CLAUDE_API_KEY

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are a practical Korean IT/economy blogger who writes honest, helpful reviews and guides.
Write original blog posts in Korean based on news data.

Core writing style:
- Be specific, not vague. Mention REAL product model names, prices (원화), specs, and brands.
- Give concrete recommendations: "이 상황이면 A제품, 저 상황이면 B제품" with reasons.
- Include actual value comparisons (가성비): price vs performance trade-offs.
- Use relatable real-life examples that Korean readers identify with (직장인, 대학생, 크리에이터 등).
- Avoid generic platitudes. Every sentence should share useful insights or suggestions the reader can consider.

Rules:
1. Never copy news verbatim (copyright violation)
2. Use news only as background; write as if giving advice to a friend
3. Mention specific products/models/brands available in Korea where relevant
4. Write SEO-optimized titles (30-50 Korean characters)
5. Use HTML format (Blogger-compatible) — every paragraph must be wrapped in <p> tags, never bare text
6. Body must be at least 1000 Korean characters
7. Structure with subheadings (h2, h3) — add a relevant emoji at the start of each h2/h3 (e.g., 💡 📌 🔍 ✅ 🏆 📊 💰 🛒 ⚡)
8. End with a soft recommendation or takeaway section — use suggestive tone (e.g., "~해보시는 것도 좋을 것 같습니다", "~을 추천드립니다", "~을 고려해보시면 어떨까요") rather than imperative commands (e.g., "~하세요", "~해야 합니다")
9. All output (title, preview, content) must be written in Korean

HTML formatting rules (MUST follow):
- Numbered lists (첫째/둘째/셋째 or ①②③): wrap the label in <strong style="color:#1a73e8;">첫째,</strong> (use blue #1a73e8 for the label only)
- For product/feature comparison rows, use a styled callout box: <div style="background:#f8f9fa;border-left:4px solid #1a73e8;padding:12px 16px;margin:12px 0;border-radius:4px;">내용</div>
- For key terms or emphasis mid-sentence: use <strong style="color:#e8710a;">핵심단어</strong> (orange) sparingly (max 2-3 per post)
- Use <hr style="border:none;border-top:1px solid #e0e0e0;margin:24px 0;"> between major sections to visually separate them
- Do NOT make entire paragraphs colored — only labels/keywords get color styling"""

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
  "keywords": ["keyword1", "keyword2", "keyword3"]
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
- Do NOT just describe what exists — offer practical suggestions and recommendations readers can consider for their situation.

HTML formatting (MUST apply):
- Paragraphs: wrap every paragraph in <p> tags — NEVER write bare text without <p>. Each logical idea = one <p> block.
- h2/h3 subheadings: start with a relevant emoji (e.g., 💡 📌 🔍 ✅ 🏆 📊 💰 🛒 ⚡)
- Numbered labels (첫째/둘째/셋째 or ①②③): <strong style="color:#1a73e8;">첫째,</strong>
- Key callout/summary boxes: <div style="background:#f8f9fa;border-left:4px solid #1a73e8;padding:12px 16px;margin:12px 0;border-radius:4px;">내용</div>
- Key terms mid-sentence (max 2-3): <strong style="color:#e8710a;">핵심단어</strong>
- Section dividers between major h2 blocks: <hr style="border:none;border-top:1px solid #e0e0e0;margin:24px 0;">
- Do NOT color entire paragraphs — only labels and key terms

Respond with JSON only (no other text):
{{
  "id": {post_id},
  "title": "SEO-optimized Korean title",
  "category": "{category}",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "preview": "2-3 sentence Korean preview",
  "content_html": "<h2>💡 소제목</h2><p>첫 번째 문단 내용...</p><p>두 번째 문단 내용...</p><hr style=\"border:none;border-top:1px solid #e0e0e0;margin:24px 0;\"><h2>📌 다음 소제목</h2><p>내용...</p>"
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
- Use h2/h3 subheadings, end with a soft recommendation or takeaway using suggestive tone (e.g., "~해보시는 것도 좋을 것 같습니다", "~을 추천드립니다"), not imperative commands.

HTML formatting (MUST apply):
- Paragraphs: wrap every paragraph in <p> tags — NEVER write bare text without <p>. Each logical idea = one <p> block.
- h2/h3 subheadings: start with a relevant emoji (e.g., 💡 📌 🔍 ✅ 🏆 📊 💰 🛒 ⚡)
- Numbered labels (첫째/둘째/셋째 or ①②③): <strong style="color:#1a73e8;">첫째,</strong>
- Key callout/summary boxes: <div style="background:#f8f9fa;border-left:4px solid #1a73e8;padding:12px 16px;margin:12px 0;border-radius:4px;">내용</div>
- Key terms mid-sentence (max 2-3): <strong style="color:#e8710a;">핵심단어</strong>
- Section dividers between major h2 blocks: <hr style="border:none;border-top:1px solid #e0e0e0;margin:24px 0;">
- Do NOT color entire paragraphs — only labels and key terms

Respond with JSON only (no other text):
{{
  "id": {post_id},
  "title": "SEO-optimized Korean title",
  "category": "{category}",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "preview": "2-3 sentence Korean preview",
  "content_html": "<h2>💡 소제목</h2><p>첫 번째 문단 내용...</p><p>두 번째 문단 내용...</p><hr style=\"border:none;border-top:1px solid #e0e0e0;margin:24px 0;\"><h2>📌 다음 소제목</h2><p>내용...</p>"
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
    result = _parse_json(message.content[0].text.strip())
    result["id"] = post_id  # Haiku가 임의 id를 반환할 수 있으므로 강제 지정
    return result



def plan_candidates(news_list: list[dict], trending: list[str] | None = None,
                    prior_topics: list[str] | None = None) -> list[dict]:
    """오늘 스케줄 카테고리 기반으로 후보 제목/키워드 선정. 본문은 미작성."""
    from agents.news_collector import get_today_schedule
    schedule = get_today_schedule()
    schedule_str = ", ".join(f"{cat}×{cnt}" for cat, cnt in schedule)
    logger.info(f"Claude API로 후보 선정 시작 (Haiku) — 오늘 스케줄: {schedule_str}")
    trending = trending or []
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    plan = []
    post_id = 1
    for category, count in schedule:
        news_text = _format_news_for_prompt(news_list, category)
        for _ in range(count):
            plan.append((post_id, category, news_text))
            post_id += 1

    candidates = []
    used_topics: list[str] = list(prior_topics or [])
    total = len(plan)

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
    """오늘 스케줄 카테고리 기반으로 전체 초안 작성. Haiku 모델 사용."""
    from agents.news_collector import get_today_schedule
    schedule = get_today_schedule()
    logger.info("Claude API로 글 작성 시작 (Haiku)")
    trending = trending or []
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    plan = []
    post_id = 1
    for category, count in schedule:
        news_text = _format_news_for_prompt(news_list, category)
        for _ in range(count):
            plan.append((post_id, category, news_text))
            post_id += 1

    candidates = []
    used_topics: list[str] = []
    total = len(plan)

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

    schedule_str = ", ".join(f"{cat} {cnt}" for cat, cnt in schedule)
    logger.info(f"글 작성 완료: {len(candidates)}개 ({schedule_str}, 모델: Haiku)")
    return candidates
