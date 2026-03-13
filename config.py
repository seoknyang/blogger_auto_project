import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
BLOG_ID = os.getenv("BLOG_ID", "2714213792568384338")

# 구글 뉴스 RSS URL
GOOGLE_NEWS_IT_URL = "https://news.google.com/rss/search?q=IT+기술+인공지능&hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_ECONOMY_URL = "https://news.google.com/rss/search?q=경제+금융+주식&hl=ko&gl=KR&ceid=KR:ko"

NEWS_PER_CATEGORY = 15  # 카테고리별 수집 뉴스 수
CANDIDATE_COUNT = 3     # 후보 글 수

# 파일 경로
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
THUMBNAILS_DIR = os.path.join(DATA_DIR, "thumbnails")
FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "NanumGothicBold.ttf")
