import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
#시스템 경로설정 끝
from app.ai.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, client
import pymysql
import pandas as pd
import numpy as np
# --- 유저 자연어 쿼리 임베딩 기반 ETF 추천 함수 ---
#1. 유저쿼리 임베드 벡터화
def get_embedding(text, model="text-embedding-3-small"):
    """
    OpenAI의 text-embedding-3-small 모델을 사용하여 텍스트를 임베딩하는 함수.
    """
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

#2. etf 텍스트 벡터 및 설명데이터 조회
def fetch_etf_text_vectors():
    """ETF 테이블에서 text_vector 컬럼을 조회하여 반환하는 함수"""
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    query = "SELECT ticker, category, long_business_summary, text_vector FROM etf"
    etf_data = pd.read_sql(query, connection)
    connection.close()

    # 문자열 형태의 벡터를 NumPy 배열로 변환
    etf_data["text_vector"] = etf_data["text_vector"].apply(
        lambda x: np.fromstring(x.strip("[]"), sep=',') if x else np.zeros(1536)
    )

    return etf_data
#3. 코사인 유사도 계산함수
def cosine_similarity(vec1, vec2):
    """
    두 벡터 간의 코사인 유사도를 계산하는 함수.
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(vec1, vec2) / (norm1 * norm2)

#4. 요약함수
#4-1. 단순 150자이내 절삭
def truncate_text(text, max_length=150):
    """
    긴 ETF 설명을 적절한 길이로 줄이는 함수 (기본: 150자)
    """
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."  # 문장이 끊기지 않도록 마지막 공백 기준으로 자름
#4-2. gpt 요약함수
def summarize_text(text, category):
    """
    OpenAI GPT 모델을 사용하여 ETF 설명을 투자 관점에서 요약하는 함수.
    카테고리 정보도 포함하여 요약을 보강함.
    """
    prompt = f"""
    당신은 금융 투자 분석가입니다. 아래는 특정 ETF의 섹터 및 사업 설명입니다:

    섹터: {category}
    설명: "{text}"

    해당 ETF의 투자 전략, 주요 투자 대상(산업군), 리스크 수준, 기대 수익률을 포함하여 
    투자자가 이해하기 쉽도록 2~3문장으로 요약해 주세요.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "당신은 금융 데이터 요약 전문가입니다."},
                  {"role": "user", "content": prompt}]
    )

    summary = response.choices[0].message.content.strip()
    return summary
#5. 자연어쿼리 기반 ai 추천함수
def query_recommend_etfs(user_query, top_k=4, use_gpt_summary=True):
    """
    사용자 자연어 쿼리를 임베딩하고, ETF 테이블의 text_vector와 코사인 유사도를 비교하여 상위 ETF 추천.
    추천 결과를 JSON 형식으로 반환.
    """
    # 1. 사용자 쿼리 임베딩
    query_embedding = get_embedding(user_query)

    # 2. ETF 데이터 로드 (text_vector 포함)
    etf_data = fetch_etf_text_vectors()

    # 3. 각 ETF와의 코사인 유사도 계산
    scores = []
    for _, row in etf_data.iterrows():
        etf_vector = row["text_vector"]
        sim = cosine_similarity(query_embedding, etf_vector)
        scores.append((row, sim))

    # 4. 유사도 기준 정렬 후 상위 ETF 추천
    scores.sort(key=lambda x: x[1], reverse=True)
    top_etfs = scores[:top_k]

    # 5. 추천 ETF 포맷팅 (JSON 형식으로 리턴)
    formatted_recommendations = []
    for etf, _ in top_etfs:
        ticker = etf["ticker"]
        category = etf["category"]
        description = etf["long_business_summary"]

        # 설명 요약 (GPT 사용 여부 선택)
        summary = summarize_text(description,category) if use_gpt_summary else truncate_text(description)

        # JSON 형식으로 저장
        formatted_recommendations.append({
            "ticker": ticker,
            "category": category,
            "summary": summary
        })

    return formatted_recommendations


# --- 실행 테스트 ---
if __name__ == "__main__":
    user_query = input("추천받고싶은 내용을 입력하세요: ")
    recommendations = query_recommend_etfs(user_query)
    print(recommendations)
    # print(":::AI의 추천 목록:")
    # for etf in recommendations:
    #     print(f"{etf['ticker']} - {etf['category']}")
