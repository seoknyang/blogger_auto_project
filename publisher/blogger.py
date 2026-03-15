import os
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import BLOG_ID

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/blogger"]
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "token.json")
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")


def get_credentials() -> Credentials:
    """
    저장된 token.json에서 인증 정보 로드 및 자동 갱신.

    헤드리스 서버에서는 최초 1회 로컬에서 token.json을 생성한 뒤 업로드해야 합니다.
    token.json에 refresh_token이 있으면 자동으로 갱신됩니다.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            logger.info("토큰 갱신 완료")
        else:
            raise RuntimeError(
                "유효한 token.json이 없습니다. "
                "로컬에서 python setup_auth.py 실행 후 token.json을 서버에 업로드하세요."
            )
    return creds


def publish_post(title: str, content_html: str, labels: list[str] | None = None, is_draft: bool = False, thumbnail_url: str | None = None) -> dict:
    """Blogger에 글 발행."""
    creds = get_credentials()
    service = build("blogger", "v3", credentials=creds)

    if thumbnail_url:
        img_tag = f'<div style="text-align:center;margin-bottom:24px;"><img src="{thumbnail_url}" alt="{title}" style="max-width:100%;height:auto;border-radius:8px;"/></div>\n'
        content_html = img_tag + content_html

    post_body = {
        "title": title,
        "content": content_html,
    }
    if labels:
        post_body["labels"] = labels

    post = service.posts().insert(
        blogId=BLOG_ID,
        body=post_body,
        isDraft=is_draft,
    ).execute()

    logger.info(f"발행 완료: {post.get('url', '')}")
    return post
