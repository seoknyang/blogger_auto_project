import logging
from datetime import date
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

MIN_PREVIEW_LENGTH = 20  # 최소 미리보기 글자 수


def _quality_check(candidates: list[dict]) -> list[dict]:
    """최소 품질 기준 미달 후보 필터링."""
    passed = []
    for c in candidates:
        preview_len = len(c.get("preview", ""))
        if preview_len < MIN_PREVIEW_LENGTH:
            logger.warning(f"후보 {c['id']} 품질 미달 (미리보기 {preview_len}자) - 제외")
            continue
        passed.append(c)
    return passed


def _build_message(candidates: list[dict]) -> str:
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"📢 *오늘의 블로그 후보* ({today})\n"]
    for c in candidates:
        lines.append(f"*[{c['id']}번]* {c['category']} | {c['title']}")
        lines.append(f"{c.get('preview', '')}\n")
    lines.append("👇 발행할 글을 선택하세요")
    return "\n".join(lines)


def _build_keyboard(candidates: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"{c['id']}번 선택", callback_data=f"select_{c['id']}")
        for c in candidates
    ]
    skip_btn = InlineKeyboardButton("오늘 건너뜀", callback_data="skip")
    # 2개씩 묶어서 2x2 그리드, 건너뜀 버튼 별도 줄
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([skip_btn])
    return InlineKeyboardMarkup(rows)


async def send_candidates(candidates: list[dict]):
    """PM 에이전트: 품질 검토 후 텔레그램으로 후보 제목 목록 발송."""
    passed = _quality_check(candidates)
    if not passed:
        logger.error("품질 통과 후보 없음")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    message_text = _build_message(passed)
    keyboard = _build_keyboard(passed)

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    logger.info(f"텔레그램 후보 발송 완료: {len(passed)}개")
