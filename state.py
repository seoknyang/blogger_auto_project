import json
import os
from datetime import date
from config import CANDIDATES_FILE, DATA_DIR


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_candidates(candidates: list[dict], news_list: list[dict] | None = None, trending: list[str] | None = None):
    """후보 글을 파일에 저장. 글 작성에 필요한 뉴스와 트렌딩 키워드도 함께 저장."""
    _ensure_data_dir()
    data = {
        "date": str(date.today()),
        "candidates": candidates,
        "selected": None,
        "news_list": news_list or [],
        "trending": trending or [],
    }
    with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_candidates() -> dict | None:
    """저장된 후보 글 로드. 없거나 날짜가 다르면 None 반환."""
    if not os.path.exists(CANDIDATES_FILE):
        return None
    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("date") != str(date.today()):
        return None
    return data


def get_candidate(candidate_id: int) -> dict | None:
    """ID(1~3)로 특정 후보 글 반환."""
    data = load_candidates()
    if not data:
        return None
    for c in data["candidates"]:
        if c["id"] == candidate_id:
            return c
    return None


def mark_selected(candidate_id: int):
    """선택된 후보 ID 기록."""
    if not os.path.exists(CANDIDATES_FILE):
        return
    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["selected"] = candidate_id
    with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_news_and_trending() -> tuple[list[dict], list[str]]:
    """저장된 뉴스 목록과 트렌딩 키워드 반환."""
    data = load_candidates()
    if not data:
        return [], []
    return data.get("news_list", []), data.get("trending", [])


def clear_candidates():
    """발행 완료 후 후보 파일 삭제."""
    if os.path.exists(CANDIDATES_FILE):
        os.remove(CANDIDATES_FILE)
