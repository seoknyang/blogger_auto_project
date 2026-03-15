#!/bin/bash
# Oracle Cloud Ubuntu VM 초기 배포 스크립트
# 실행: bash deploy.sh

set -e

PROJECT_DIR="$HOME/blogger_auto_project"
SERVICE_NAME="blogger-auto"

echo "=== 블로그 자동화 봇 배포 시작 ==="

# 1. 시스템 패키지 업데이트
echo "[1/6] 시스템 패키지 업데이트..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv git \
    libfreetype6-dev libjpeg-dev zlib1g-dev fonts-nanum

# 2. 프로젝트 디렉토리 준비
echo "[2/6] 프로젝트 디렉토리 준비..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 3. 가상환경 생성 및 패키지 설치
echo "[3/6] Python 가상환경 및 패키지 설치..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 4. 나눔고딕 폰트 심볼릭 링크 생성
echo "[4/6] 나눔고딕 폰트 연결..."
mkdir -p assets/fonts
NANUM_FONT=$(find /usr/share/fonts -name "NanumGothicBold.ttf" 2>/dev/null | head -1)
if [ -n "$NANUM_FONT" ]; then
    ln -sf "$NANUM_FONT" assets/fonts/NanumGothicBold.ttf
    echo "    폰트 연결됨: $NANUM_FONT"
else
    echo "    경고: NanumGothicBold.ttf를 찾을 수 없음. 기본 폰트를 사용합니다."
fi

# 5. 데이터 디렉토리 생성
echo "[5/6] 데이터 디렉토리 생성..."
mkdir -p data/thumbnails

# 6. systemd 서비스 등록
echo "[6/6] systemd 서비스 등록..."
sudo cp "$PROJECT_DIR/blogger-auto.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo ""
echo "=== 배포 완료 ==="
echo "서비스 상태 확인: sudo systemctl status $SERVICE_NAME"
echo "로그 확인:        sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "⚠️  배포 전 확인 사항:"
echo "   1. .env 파일이 $PROJECT_DIR 에 있어야 합니다"
echo "   2. token.json 이 $PROJECT_DIR 에 있어야 합니다 (로컬에서 setup_auth.py 실행 후 scp로 업로드)"
echo "   3. credentials.json 이 $PROJECT_DIR 에 있어야 합니다"
