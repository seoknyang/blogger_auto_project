import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import state
from publisher.blogger import publish_post

logger = logging.getLogger(__name__)


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    is_photo = bool(query.message.photo)

    async def edit_msg(text: str, parse_mode: str | None = None):
        if is_photo:
            await query.edit_message_caption(caption=text, parse_mode=parse_mode)
        else:
            await query.edit_message_text(text=text, parse_mode=parse_mode)

    # 본인만 사용 가능하도록 검증
    if query.from_user.id != TELEGRAM_CHAT_ID:
        await edit_msg("권한이 없습니다.")
        return

    data = query.data

    if data == "skip":
        state.clear_candidates()
        await edit_msg("오늘 발행을 건너뜁니다.")
        logger.info("사용자가 오늘 발행 건너뜀")
        return

    if data.startswith("select_"):
        candidate_id = int(data.split("_")[1])
        candidate = state.get_candidate(candidate_id)

        if not candidate:
            await edit_msg("후보를 찾을 수 없습니다. 오늘 후보가 만료되었을 수 있습니다.")
            return

        await edit_msg(f"⏳ {candidate['title']}\n\n발행 중입니다...")

        try:
            post = publish_post(
                title=candidate["title"],
                content_html=candidate["content_html"],
                labels=[candidate.get("category", ""), *candidate.get("keywords", [])],
            )
            post_url = post.get("url", "")
            state.mark_selected(candidate_id)
            state.clear_candidates()

            await edit_msg(
                f"✅ 발행 완료!\n\n*{candidate['title']}*\n\n🔗 {post_url}",
                parse_mode="Markdown",
            )
            logger.info(f"발행 성공: {post_url}")

        except Exception as e:
            logger.error(f"발행 실패: {e}")
            await edit_msg(f"❌ 발행 실패: {e}")


def build_application() -> Application:
    """텔레그램 봇 Application 객체 생성."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(_handle_callback))
    return app
