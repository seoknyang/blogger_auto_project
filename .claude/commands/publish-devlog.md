오늘(현재 날짜)의 blogger_auto_project 작업 기록을 수집하여 seoknyang.github.io 블로그에 발행하세요.

## 1단계: 오늘 작업 내역 수집

아래 명령어들을 실행해서 오늘 한 작업을 파악하세요:

```bash
# 오늘 커밋 목록
git log --since=midnight --until=now --pretty=format:"%h %s" --no-merges

# 오늘 커밋 수 확인
git log --since=midnight --oneline | wc -l

# 변경된 파일 통계 (오늘 커밋 기준)
git diff --stat $(git log --since=midnight --oneline | tail -1 | cut -d' ' -f1)^ HEAD 2>/dev/null || git diff --stat HEAD~1 HEAD

# 상세 변경 내용 (너무 길면 주요 파일만)
git log --since=midnight --patch --no-merges --stat 2>/dev/null | head -200
```

커밋이 없는 경우 unstaged/staged 변경사항도 확인하세요:
```bash
git status
git diff --stat
```

## 2단계: 작업 로그 작성

수집한 정보를 바탕으로 **한국어**로 다음 형식의 포스트를 구성하세요:

**제목**: `YYYY-MM-DD 작업 로그 - [오늘 핵심 작업 한 줄 요약]`
**요약**: 오늘 작업의 핵심을 1-2문장으로 (블로그 목록에 표시됨)
**태그**: `devlog blogger-auto` + 관련 기술 태그

**본문 구조**:
```
## 오늘 작업 요약
(전체 개요를 2-3문장으로)

## 변경 사항
(커밋별 또는 기능별 상세 내용)

## 기술적 메모
(트러블슈팅, 배운 점, 다음에 할 일 등 - 있을 때만)
```

## 3단계: Sanity에 발행

아래 명령어로 발행하세요 (제목/요약/본문을 실제 내용으로 채워서):

```bash
python scripts/publish_devlog.py \
  --title "작성한 제목" \
  --summary "작성한 요약" \
  --tags devlog blogger-auto \
  --body "작성한 본문 전체"
```

SANITY_API_TOKEN이 .env에 없다면 사용자에게 안내하세요:
- 발급 URL: https://www.sanity.io/manage/personal/project/nmfm8fl3/api
- Tokens → Add API token → Editor 권한
- .env에 `SANITY_API_TOKEN=발급받은토큰` 추가

## 4단계: 완료 안내

발행 성공 시 아래 내용을 사용자에게 알려주세요:
- 발행된 포스트 URL: `https://seoknyang.github.io/blog/devlog-YYYY-MM-DD`
- 사이트 반영은 GitHub Actions 빌드 완료 후 (~1-2분)
- 오늘 같은 날짜로 재실행하면 포스트가 업데이트됩니다 (덮어쓰기)
