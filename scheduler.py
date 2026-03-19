import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.news_collector import fetch_trending_keywords, fetch_news_for_keyword
from agents.content_writer import plan_candidates_from_trending
from agents.pm_agent import send_candidates
import state
from state import load_published_topics

logger = logging.getLogger(__name__)


async def run_daily_pipeline():
    """매일 10:30 KST 실행되는 자동화 파이프라인."""
    logger.info("=== 일일 파이프라인 시작 ===")
    try:
        # 1. 구글 트렌드 지난 24시간 인기 검색어 수집
        logger.info("[1/2] 구글 트렌드 실시간 인기 검색어 수집 중...")
        trending = fetch_trending_keywords()
        if not trending:
            logger.error("트렌딩 키워드 수집 실패 - 파이프라인 중단")
            return
        logger.info(f"  수집된 키워드: {', '.join(trending[:5])}...")

        # 2. 트렌딩 키워드에서 바로 블로그 후보 선정 (카테고리 제한 없음)
        logger.info("[2/2] 트렌딩 기반 블로그 후보 선정 중...")
        prior_topics = load_published_topics(days=30)
        if prior_topics:
            logger.info(f"  최근 30일 발행 이력 {len(prior_topics)}개 제외 적용")
        candidates = plan_candidates_from_trending(trending, prior_topics=prior_topics, count=4)
        if not candidates:
            logger.error("후보 선정 실패 - 파이프라인 중단")
            return

        # 3. 후보별 키워드로 실제 뉴스 검색 (그라운딩)
        logger.info("[3/4] 후보별 뉴스 검색 중 (그라운딩)...")
        for candidate in candidates:
            keyword = candidate.get("keywords", [candidate.get("title", "")])[0]
            candidate["news_list"] = fetch_news_for_keyword(keyword, limit=10)

        # 4. 상태 저장 + 텔레그램 발송
        logger.info("[4/4] 텔레그램 발송 중...")
        state.save_candidates(candidates, news_list=[], trending=trending)
        await send_candidates(candidates)

        logger.info("=== 파이프라인 완료 ===")

    except Exception as e:
        logger.exception(f"파이프라인 오류: {e}")


def create_scheduler() -> AsyncIOScheduler:
    """매일 10:30 KST에 파이프라인을 실행하는 스케줄러 생성."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=10, minute=0, timezone="Asia/Seoul"),
        id="daily_pipeline",
        name="일일 블로그 자동화",
        replace_existing=True,
    )
    return scheduler
