import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.news_collector import collect
from agents.content_writer import write
from agents.thumbnail_maker import generate_thumbnails
from agents.pm_agent import send_candidates
import state

logger = logging.getLogger(__name__)


async def run_daily_pipeline():
    """매일 09:00 KST 실행되는 자동화 파이프라인."""
    logger.info("=== 일일 파이프라인 시작 ===")
    try:
        # 1. 뉴스 수집
        logger.info("[1/4] 뉴스 수집 중...")
        news_list = collect()
        if not news_list:
            logger.error("뉴스 수집 실패 - 파이프라인 중단")
            return

        # 2. Claude API로 글 작성
        logger.info("[2/4] 글 작성 중...")
        candidates = write(news_list)
        if not candidates:
            logger.error("글 작성 실패 - 파이프라인 중단")
            return

        # 3. 썸네일 생성
        logger.info("[3/4] 썸네일 생성 중...")
        candidates = generate_thumbnails(candidates)

        # 4. 상태 저장 + 텔레그램 발송
        logger.info("[4/4] 텔레그램 발송 중...")
        state.save_candidates(candidates)
        await send_candidates(candidates)

        logger.info("=== 파이프라인 완료 ===")

    except Exception as e:
        logger.exception(f"파이프라인 오류: {e}")


def create_scheduler() -> AsyncIOScheduler:
    """매일 09:00 KST에 파이프라인을 실행하는 스케줄러 생성."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
        id="daily_pipeline",
        name="일일 블로그 자동화",
        replace_existing=True,
    )
    return scheduler
