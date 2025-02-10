FROM python:3.11

WORKDIR /Server
ENV ENV="prod"

# 종속성 설치
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 컨테이너 실행 시 FastAPI 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
