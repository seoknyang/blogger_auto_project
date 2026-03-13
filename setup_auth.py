"""
최초 1회 실행하여 Blogger OAuth 토큰을 생성합니다.
로컬 PC에서 실행 후 생성된 token.json을 Oracle Cloud 서버에 업로드하세요.

실행: python setup_auth.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ["https://www.googleapis.com/auth/blogger"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"오류: {CREDENTIALS_FILE} 파일이 없습니다.")
        print("Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 다운로드하세요.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=3000)

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"\n✅ 인증 완료! {TOKEN_FILE} 생성됨")
    print("이 파일을 Oracle Cloud 서버의 프로젝트 디렉토리에 업로드하세요:")
    print(f"  scp {TOKEN_FILE} ubuntu@<서버IP>:~/blogger_auto_project/")


if __name__ == "__main__":
    main()
