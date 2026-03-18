import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.news_collector import collect, fetch_trending_keywords
from agents.content_writer import plan_candidates
from agents.pm_agent import send_candidates
import state

logger = logging.getLogger(__name__)


async def run_daily_pipeline():
    """매일 09:00 KST 실행되는 자동화 파이프라인."""
    logger.info("=== 일일 파이프라인 시작 ===")
    try:
        # 1. 트렌딩 키워드 수집 → 트렌딩 기반 뉴스 수집
        logger.info("[1/3] 트렌딩 키워드 수집 중...")
        trending = fetch_trending_keywords()

        logger.info("[1/3] 트렌딩 키워드 기반 뉴스 수집 중...")
        news_list = collect(trending=trending)
        if not news_list:
            logger.error("뉴스 수집 실패 - 파이프라인 중단")
            return

        # 2. 후보 제목/키워드/미리보기만 선정 (본문 미작성)
        logger.info("[2/3] 후보 선정 중 (제목/키워드만)...")
        candidates = plan_candidates(news_list, trending=trending)
        if not candidates:
            logger.error("후보 선정 실패 - 파이프라인 중단")
            return

        # 3. 상태 저장 (뉴스+트렌딩 포함) + 텔레그램 발송
        logger.info("[3/3] 텔레그램 발송 중...")
        state.save_candidates(candidates, news_list=news_list, trending=trending)
        await send_candidates(candidates)

        logger.info("=== 파이프라인 완료 ===")

    except Exception as e:
        logger.exception(f"파이프라인 오류: {e}")


def create_scheduler() -> AsyncIOScheduler:
    """매일 09:00 KST에 파이프라인을 실행하는 스케줄러 생성."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=15, minute=0, timezone="Asia/Seoul"),
        id="daily_pipeline",
        name="일일 블로그 자동화",
        replace_existing=True,
    )
    return scheduler
