import json
import logging
import anthropic
from config import CLAUDE_API_KEY, CANDIDATE_COUNT

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 IT/경제 전문 블로거입니다.
뉴스 데이터를 참고하여 독창적인 블로그 글을 작성하세요.

규칙:
1. 뉴스 원문을 절대 그대로 복사하지 마세요 (저작권 위반)
2. 뉴스를 배경 정보로만 활용하고, 필자의 관점과 인사이트를 추가하세요
3. 독자가 실생활에서 활용할 수 있는 정보를 포함하세요
4. SEO에 최적화된 제목을 작성하세요 (30~50자)
5. HTML 형식으로 작성하세요 (Blogger 호환)
6. 본문은 최소 800자 이상으로 작성하세요
7. 소제목(h2, h3)을 사용해 구조화하세요"""

POST_PROMPT_TEMPLATE = """다음 뉴스들을 참고하여 블로그 포스트 {count}개를 작성해주세요.
각 포스트는 서로 다른 주제를 다뤄야 합니다.

뉴스 데이터:
{news_data}

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
[
  {{
    "id": 1,
    "title": "SEO 최적화 제목",
    "category": "IT 또는 경제",
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "preview": "미리보기 텍스트 2~3문장",
    "content_html": "<h2>소제목</h2><p>본문...</p>"
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
