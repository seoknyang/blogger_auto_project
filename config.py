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

# 구글 뉴스 RSS URL
GOOGLE_NEWS_IT_URL = "https://news.google.com/rss/search?q=IT+기술+인공지능&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_ECONOMY_URL = "https://news.google.com/rss/search?q=경제+금융+주식&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_ELECTRONICS_URL = "https://news.google.com/rss/search?q=노트북+스마트폰+태블릿+전자기기&hl=ko&gl=KR&ceid=KR:ko"

NEWS_PER_CATEGORY = 15  # 카테고리별 수집 뉴스 수
CANDIDATE_COUNT = 4        # 후보 글 수 (IT 1 + 전자기기 1 + 경제 2)
IT_COUNT = 1
ELECTRONICS_COUNT = 1
ECONOMY_COUNT = 2

# 파일 경로
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
PUBLISHED_TOPICS_FILE = os.path.join(os.path.dirname(__file__), "published_topics.json")
THUMBNAILS_DIR = os.path.join(DATA_DIR, "thumbnails")
FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "NanumGothicBold.ttf")
