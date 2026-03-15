import json
import logging
import anthropic
from config import CLAUDE_API_KEY, CANDIDATE_COUNT

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional Korean IT/economy blogger.
Write original blog posts in Korean based on news data.

Rules:
1. Never copy news verbatim (copyright violation)
2. Use news only as background; add your own perspective and insights
3. Include practical information readers can apply in daily life
4. Write SEO-optimized titles (30-50 Korean characters)
5. Use HTML format (Blogger-compatible)
6. Body must be at least 800 Korean characters
7. Structure with subheadings (h2, h3)
8. All output (title, preview, content) must be written in Korean"""

POST_PROMPT_TEMPLATE = """Write {count} blog posts based on the following news. Each post must cover a different topic.

News data:
{news_data}

Respond with JSON only (no other text):
[
  {{
    "id": 1,
    "title": "SEO-optimized Korean title",
    "category": "IT or 경제",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "preview": "2-3 sentence Korean preview",
    "content_html": "<h2>subheading</h2><p>Korean body...</p>"
  }},
  ...
]"""


def _format_news_for_prompt(news_list: list[dict]) -> str:
    lines = []
    for i, news in enumerate(news_list, 1):
        lines.append(f"[{i}] [{news['category']}] {news['title']}")
        if news.get("summary"):
            lines.append(f"    요약: {news['summary'][:200]}")
    return "\n".join(lines)


def write(news_list: list[dict]) -> list[dict]:
    """뉴스 리스트를 받아 Claude API로 블로그 후보 글 3개 작성."""
    logger.info("Claude API로 글 작성 시작")
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    news_text = _format_news_for_prompt(news_list)
    user_prompt = POST_PROMPT_TEMPLATE.format(
        count=CANDIDATE_COUNT,
        news_data=news_text,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text.strip()

    # JSON 파싱
    try:
        # ```json ... ``` 블록이 있으면 제거
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        candidates = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}\n응답: {response_text[:500]}")
        raise

    logger.info(f"글 작성 완료: {len(candidates)}개")
    return candidates
