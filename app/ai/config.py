import os
from pathlib import Path
from dotenv import load_dotenv
import openai

# .env 파일 경로 설정 (필요에 따라 수정)
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

# 환경변수 로드
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
GPT_API_KEY = os.getenv('GPT_API_KEY')

# OpenAI 설정
openai.api_key = GPT_API_KEY
