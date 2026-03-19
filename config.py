import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
BLOG_ID = os.getenv("BLOG_ID", "2714213792568384338")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 구글 뉴스 RSS URL (카테고리별 폴백)
GOOGLE_NEWS_IT_URL = "https://news.google.com/rss/search?q=IT+기술+인공지능&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_ECONOMY_URL = "https://news.google.com/rss/search?q=경제+금융+주식&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_ELECTRONICS_URL = "https://news.google.com/rss/search?q=노트북+스마트폰+태블릿+전자기기&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_LIFE_URL = "https://news.google.com/rss/search?q=생활+문화+건강+트렌드&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_LIFE_INFO_URL = "https://news.google.com/rss/search?q=자취+이사+청약+행정+신청방법+절차&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_WORLD_URL = "https://news.google.com/rss/search?q=세계+국제+외교+미국+유럽&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_SOCIETY_URL = "https://news.google.com/rss/search?q=사회+정책+교육+환경&hl=ko&gl=KR&ceid=KR:ko"

# 네이버 뉴스 RSS URL (카테고리별)
NAVER_NEWS_IT_URL = "https://rss.news.naver.com/main/rss/home.naver?sectionId=105"
NAVER_NEWS_ECONOMY_URL = "https://rss.news.naver.com/main/rss/home.naver?sectionId=101"
NAVER_NEWS_SOCIETY_URL = "https://rss.news.naver.com/main/rss/home.naver?sectionId=102"
NAVER_NEWS_LIFE_URL = "https://rss.news.naver.com/main/rss/home.naver?sectionId=103"
NAVER_NEWS_WORLD_URL = "https://rss.news.naver.com/main/rss/home.naver?sectionId=104"

NEWS_PER_CATEGORY = 15  # 카테고리별 수집 뉴스 수 (소스당 8개씩)
CANDIDATE_COUNT = 4     # 하루 총 후보 글 수

# 요일별 카테고리 스케줄 (0=월, 1=화, ..., 6=일)
# 각 항목: (카테고리명, 후보수) — 합계는 항상 CANDIDATE_COUNT(4)
CATEGORY_SCHEDULE = {
    0: [("전자기기", 2), ("경제", 2)],                           # 월
    1: [("전자기기", 1), ("생활정보", 1), ("경제", 2)],          # 화
    2: [("전자기기", 2), ("세계", 1), ("경제", 1)],             # 수
    3: [("전자기기", 2), ("생활정보", 1), ("사회", 1)],          # 목
    4: [("전자기기", 1), ("생활문화", 1), ("생활정보", 1), ("세계", 1)],  # 금
    5: [("전자기기", 1), ("생활정보", 1), ("경제", 2)],          # 토
    6: [("전자기기", 2), ("생활문화", 1), ("경제", 1)],          # 일
}

# 파일 경로
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
PUBLISHED_TOPICS_FILE = os.path.join(os.path.dirname(__file__), "published_topics.json")
THUMBNAILS_DIR = os.path.join(DATA_DIR, "thumbnails")
FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "NanumGothicBold.ttf")
