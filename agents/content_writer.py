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

# 카테고리별 추가 작성 지침
_CATEGORY_EXTRA = {
    "전자기기": (
        "ELECTRONICS STRATEGY (MUST apply for 전자기기 category):\n"
        "Do NOT write about 멀티탭 — readers are not interested. Focus on consumer electronics and devices.\n"
        "- Always include a dedicated price comparison section: list at least 3 models with exact Korean market prices (원화).\n"
        "- Provide 가성비 verdict: which model wins per budget tier (예: 30만원 이하, 50만원대, 100만원 이상).\n"
        "- MANDATORY IMAGE RULE — NO EXCEPTIONS: For EVERY product model introduced under an <h3> heading, "
        "place [PRODUCT_IMAGE: 정확한브랜드+모델명] IMMEDIATELY after the </h3> closing tag (before any <p>). "
        "Use the exact brand + model name. Examples:\n"
        "  <h3>✅ 삼성 갤럭시북4 엣지</h3>[PRODUCT_IMAGE: 삼성 갤럭시북4 엣지]<p>설명...</p>\n"
        "  <h3>✅ LG 그램 16 2024</h3>[PRODUCT_IMAGE: LG 그램 16 2024]<p>설명...</p>\n"
        "  <h3>✅ 애플 맥북 에어 M3</h3>[PRODUCT_IMAGE: 애플 맥북 에어 M3]<p>설명...</p>\n"
        "- When comparing 2+ products, MUST include an HTML spec comparison table in this exact format"
        " (use single quotes for all HTML attributes — double quotes break JSON):\n"
        "  <table style='width:100%;border-collapse:collapse;margin:16px 0;'>\n"
        "    <thead><tr style='background:#1a73e8;color:#fff;'>\n"
        "      <th style='padding:8px 12px;text-align:left;'>항목</th>\n"
        "      <th style='padding:8px 12px;text-align:center;'>제품A명</th>\n"
        "      <th style='padding:8px 12px;text-align:center;'>제품B명</th>\n"
        "    </tr></thead>\n"
        "    <tbody>\n"
        "      <tr style='border-bottom:1px solid #e0e0e0;'>\n"
        "        <td style='padding:8px 12px;font-weight:bold;'>가격</td>\n"
        "        <td style='padding:8px 12px;text-align:center;'>XXX원</td>\n"
        "        <td style='padding:8px 12px;text-align:center;'>XXX원</td>\n"
        "      </tr>\n"
        "    </tbody>\n"
        "  </table>\n"
        "  Include rows for: 가격, 주요 스펙(CPU/RAM/저장공간 등), 배터리/디스플레이, 장점, 단점\n"
        "- Include a '이런 분께 추천' section mapping user types (대학생, 직장인, 크리에이터, 게이머 등) to specific models with one-line reasons.\n"
        "- Where relevant, mention major Korean retailers (쿠팡, 네이버쇼핑, 다나와) and note if any deals or seasonal sales apply.\n"
        "- Avoid pure news recap — the value is in the structured price/spec comparison, not the event itself."
    ),
    "생활정보": (
        "LIFE INFO STRATEGY (MUST apply for 생활정보 category):\n"
        "Look at 'Trending keywords in Korea right now'. From that full list, pick the keyword(s) most relevant "
        "to practical daily life that Korean readers would find genuinely helpful RIGHT NOW. "
        "Scope is broad — any daily life domain: 건강/의료, 행정절차, 취업/이직/직장생활, 금융 상식, "
        "생활 꿀팁, 요리/레시피, 여행 준비, 법률 상식, 육아/교육, 계절 생활정보, 부동산/이사, 복지 혜택 등.\n"
        "IMPORTANT: Do NOT write a news article. Write a PRACTICAL GUIDE based on what people are searching for:\n"
        "- Procedure/process topic → numbered steps (1단계, 2단계...)\n"
        "- Checklist topic → categorized checklist items\n"
        "- Tips topic → concrete tips with real examples\n"
        "- Always include: 준비물/필요서류, 주의사항, 예상 비용/시간, 유용한 사이트/앱(정부24, 건강보험공단 등)\n"
        "- Use warning callout for cautions: "
        "<div style='background:#fff3cd;border-left:4px solid #ffc107;padding:12px 16px;margin:12px 0;border-radius:4px;'>⚠️ 주의</div>\n"
        "- End with a quick-reference summary table or checklist.\n"
        "- Avoid vague general advice — every point must be actionable and specific."
    ),
}


def _inject_product_images(content_html: str) -> str:
    """[PRODUCT_IMAGE: 제품명] 플레이스홀더 교체 + h3 태그 fallback 자동 삽입."""
    import re
    from agents.price_fetcher import fetch_product_image

    seen: set[str] = set()

    def make_img_html(name: str, url: str) -> str:
        return (
            f'<div style="text-align:center;margin:16px 0;">'
            f'<img src="{url}" alt="{name}" '
            f'style="max-width:320px;width:100%;height:auto;border-radius:8px;'
            f'border:1px solid #e0e0e0;box-shadow:0 2px 6px rgba(0,0,0,0.1);"/>'
            f'</div>'
        )

    # 1차: [PRODUCT_IMAGE: X] 플레이스홀더 교체
    pattern = re.compile(r'\[PRODUCT_IMAGE:\s*([^\]]+)\]')

    def replace_placeholder(match: re.Match) -> str:
        name = match.group(1).strip()
        seen.add(name.lower())
        url = fetch_product_image(name)
        if not url:
            logger.warning(f"  제품 이미지 없음: {name}")
            return ""
        logger.info(f"  제품 이미지 교체: {name}")
        return make_img_html(name, url)

    content_html = pattern.sub(replace_placeholder, content_html)

    # 2차 fallback: 이미지 div가 없는 h3 태그 뒤에 자동 삽입
    h3_re = re.compile(r'(<h3[^>]*>)(.*?)(</h3>)', re.DOTALL | re.IGNORECASE)
    already_has_img = re.compile(r'^\s*<div[^>]*text-align\s*:\s*center', re.IGNORECASE)

    parts: list[str] = []
    last_end = 0
    for m in h3_re.finditer(content_html):
        h3_end = m.end()
        inner = m.group(2)
        after = content_html[h3_end:h3_end + 120]
        if already_has_img.match(after):
            continue  # 이미 이미지 있음

        # 이모지·HTML·번호 등 제거하여 제품명 추출
        name = re.sub(r'<[^>]+>', '', inner).strip()
        name = re.sub(r'^[^\uAC00-\uD7A3a-zA-Z0-9]+', '', name).strip()
        if not name or len(name) < 3 or name.lower() in seen:
            continue

        url = fetch_product_image(name)
        if not url:
            continue

        seen.add(name.lower())
        logger.info(f"  h3 fallback 이미지 삽입: {name}")
        parts.append(content_html[last_end:h3_end])
        parts.append(make_img_html(name, url))
        last_end = h3_end

    parts.append(content_html[last_end:])
    return "".join(parts)

PLAN_PROMPT_TEMPLATE = """Select the best blog post topic for the {category} category based on the following news.
Prioritize topics overlapping with trending keywords. If no overlap, pick the most interesting topic.

Today's date: {current_date}. Only reference events, products, or trends relevant to this date.

Trending keywords in Korea right now:
{trending}

News data:
{news_data}

Already used topics (do NOT overlap): {used_topics}

{category_extra}
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

{category_extra}
IMPORTANT content guidelines:
- If the topic involves products (laptops, phones, tablets, etc.): name at least 3 specific models with approximate Korean market prices and key pros/cons of each.
- If the topic is a comparison/recommendation: give a clear verdict per use case (e.g., 대학생 → XX, 직장인 → YY).
- If the topic is economy news: explain the real-world impact on Korean consumers and give practical advice.
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

{price_data}

{category_extra}
Content guidelines:
- If topic involves products: name at least 3 specific models with Korean market prices and pros/cons.
- If comparison/recommendation: give verdict per use case (대학생, 직장인, 크리에이터 등).
- If economy news: explain real-world impact on Korean consumers with practical advice.
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
        category_extra=_CATEGORY_EXTRA.get(category, ""),
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
        category_extra=_CATEGORY_EXTRA.get(category, ""),
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
    category = candidate.get("category", "")
    news_text = _format_news_for_prompt(news_list, category)

    # 전자기기 카테고리: 네이버쇼핑 실시간 가격 조회
    price_data_text = ""
    if category == "전자기기":
        from agents.price_fetcher import fetch_prices, format_price_context
        keywords = candidate.get("keywords", [])
        logger.info(f"  네이버쇼핑 가격 조회: {keywords}")
        price_data = fetch_prices(keywords, display=3)  # noqa: F841
        price_data_text = format_price_context(price_data)
        if price_data_text:
            logger.info("  실시간 가격 데이터 프롬프트 주입 완료")
        else:
            logger.warning("  가격 데이터 없음 — 모델 자체 지식으로 작성")

    user_prompt = WRITE_PROMPT_TEMPLATE.format(
        current_date=current_date,
        post_id=candidate["id"],
        title=candidate["title"],
        category=category,
        keywords=", ".join(candidate.get("keywords", [])),
        news_data=news_text,
        trending=", ".join(trending) if trending else "없음",
        price_data=price_data_text,
        category_extra=_CATEGORY_EXTRA.get(category, ""),
    )
    message = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    result = _parse_json(message.content[0].text.strip())

    # 전자기기: [PRODUCT_IMAGE: 제품명] 플레이스홀더를 실제 이미지로 교체
    if category == "전자기기":
        result["content_html"] = _inject_product_images(result.get("content_html", ""))

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
