#!/usr/bin/env python3
"""
오늘의 작업 로그를 Sanity 블로그(seoknyang.github.io)에 발행합니다.

사용법:
  python scripts/publish_devlog.py --title "제목" --summary "요약" --body "본문"
"""
import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드
load_dotenv(Path(__file__).parent.parent / ".env")

SANITY_PROJECT_ID = "nmfm8fl3"
SANITY_DATASET = "production"
SANITY_API_VERSION = "2024-01-01"
BLOG_BASE_URL = "https://seoknyang.github.io/blog"


def get_sanity_token():
    token = os.getenv("SANITY_API_TOKEN")
    if not token:
        print("❌ SANITY_API_TOKEN 환경변수가 없습니다.")
        print("   .env 파일에 다음을 추가해주세요:")
        print("   SANITY_API_TOKEN=your_token_here")
        print()
        print("   토큰 발급: https://www.sanity.io/manage/personal/project/nmfm8fl3/api")
        print("   → Tokens → Add API token → Editor 권한 선택")
        sys.exit(1)
    return token


def slugify(text):
    """제목을 URL-friendly slug로 변환"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def text_to_portable_text(text):
    """일반 텍스트/마크다운을 Sanity Portable Text 블록으로 변환"""
    blocks = []
    paragraphs = text.split('\n\n')

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 헤더
        if para.startswith('### '):
            blocks.append({
                "_type": "block",
                "style": "h3",
                "markDefs": [],
                "children": [{"_type": "span", "text": para[4:].strip(), "marks": []}]
            })
        elif para.startswith('## '):
            blocks.append({
                "_type": "block",
                "style": "h2",
                "markDefs": [],
                "children": [{"_type": "span", "text": para[3:].strip(), "marks": []}]
            })
        elif para.startswith('# '):
            blocks.append({
                "_type": "block",
                "style": "h1",
                "markDefs": [],
                "children": [{"_type": "span", "text": para[2:].strip(), "marks": []}]
            })
        else:
            # 여러 줄을 하나의 블록으로
            lines = para.split('\n')
            children = []
            for i, line in enumerate(lines):
                if i > 0:
                    children.append({"_type": "span", "text": "\n", "marks": []})
                if line.strip():
                    children.append({"_type": "span", "text": line, "marks": []})

            if children:
                blocks.append({
                    "_type": "block",
                    "style": "normal",
                    "markDefs": [],
                    "children": children
                })

    return blocks


def create_or_update_post(title, summary, body_text, tags=None):
    token = get_sanity_token()

    today = datetime.now().strftime('%Y-%m-%d')
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    doc_id = f"devlog-{today}"
    slug = doc_id

    if tags is None:
        tags = ["devlog", "blogger-auto"]

    body_blocks = text_to_portable_text(body_text)

    mutation = {
        "mutations": [{
            "createOrReplace": {
                "_type": "post",
                "_id": doc_id,
                "title": title,
                "slug": {"_type": "slug", "current": slug},
                "publishedAt": now_iso,
                "tags": tags,
                "summary": summary,
                "body": body_blocks
            }
        }]
    }

    url = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v{SANITY_API_VERSION}/data/mutate/{SANITY_DATASET}"
    data = json.dumps(mutation).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"✅ 발행 완료!")
            print(f"   포스트 ID: {doc_id}")
            print(f"   URL: {BLOG_BASE_URL}/{slug}")
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Sanity API 오류 ({e.code}): {error_body}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='오늘의 작업 로그를 Sanity에 발행')
    parser.add_argument('--title', required=True, help='포스트 제목')
    parser.add_argument('--summary', required=True, help='요약 (1-2줄)')
    parser.add_argument('--body', help='본문 내용 (없으면 stdin에서 읽음)')
    parser.add_argument('--tags', nargs='+', default=['devlog', 'blogger-auto'],
                        help='태그 목록 (기본: devlog blogger-auto)')
    args = parser.parse_args()

    body = args.body if args.body else sys.stdin.read()

    if not body.strip():
        print("❌ 본문이 비어있습니다.")
        sys.exit(1)

    create_or_update_post(args.title, args.summary, body, args.tags)
