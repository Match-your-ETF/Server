import pymysql
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 DB 설정 불러오기
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT")),
    "cursorclass": pymysql.cursors.DictCursor  # 결과를 딕셔너리 형태로 반환
}

# DB 연결 함수
def get_connection():
    return pymysql.connect(**DB_CONFIG)
