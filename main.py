import asyncio
import logging
import signal
import sys

from scheduler import create_scheduler, run_daily_pipeline
from bot.telegram_bot import build_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
# getUpdates 폴링 로그 제거
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def main():
    logger.info("블로그 자동화 봇 시작")

    # 텔레그램 봇 초기화
    app = build_application()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # 즉시 테스트 실행 (--test 옵션)
    if "--test" in sys.argv:
        logger.info("테스트 모드: 파이프라인 즉시 실행")
        await run_daily_pipeline()

    # 스케줄러 시작
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("스케줄러 시작 (매일 09:00 KST)")

    # 종료 시그널 처리
    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("종료 시그널 수신")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows는 add_signal_handler 미지원
            pass

    logger.info("봇 실행 중... (Ctrl+C로 종료)")
    await stop_event.wait()

    # 정리
    scheduler.shutdown()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("봇 종료 완료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt - 종료")
