from app.ai.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, client
import pymysql
import pandas as pd
import numpy as np
# --- 유저 자연어 쿼리 임베딩 기반 ETF 추천 함수 ---

def get_embedding(text, model="text-embedding-3-small"):
    """
    OpenAI의 text-embedding-3-small 모델을 사용하여 텍스트를 임베딩하는 함수.
    """
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


def fetch_etf_text_vectors():
    """ETF 테이블에서 text_vector 컬럼을 조회하여 반환하는 함수"""
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    query = "SELECT ticker, category, text_vector FROM etf"
    etf_data = pd.read_sql(query, connection)
    connection.close()

    # 문자열 형태의 벡터를 NumPy 배열로 변환
    etf_data["text_vector"] = etf_data["text_vector"].apply(
        lambda x: np.fromstring(x.strip("[]"), sep=',') if x else np.zeros(1536)
    )

    return etf_data

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


def query_recommend_etfs(user_query, top_k=4):
    """
    사용자 자연어 쿼리를 기반으로 ETF를 추천하는 함수.

    1. GPT의 text-embedding-3-small 모델을 사용해 사용자 쿼리를 임베딩합니다.
    2. DB에 저장된 ETF 데이터(fetch_etf_data 사용)에서 각 ETF의 text_vector와 코사인 유사도를 계산합니다.
    3. 유사도가 높은 순으로 정렬하여 상위 top_k개의 ETF 정보를 반환합니다.

    반환되는 각 ETF 정보는 딕셔너리 형태입니다.
    """
    # 1. 사용자 쿼리 임베딩
    query_embedding = get_embedding(user_query)

    # 2. ETF 데이터 로드
    etf_data = fetch_etf_text_vectors()

    # 3. 각 ETF와의 코사인 유사도 계산
    scores = []
    for idx, row in etf_data.iterrows():
        etf_vector = row["text_vector"]
        sim = cosine_similarity(query_embedding, etf_vector)
        scores.append((row, sim))

    # 4. 유사도 기준 내림차순 정렬 후 상위 ETF 선택
    scores.sort(key=lambda x: x[1], reverse=True)
    top_etfs = [item[0].to_dict() for item in scores[:top_k]]

    return top_etfs

# --- 실행 테스트 ---
if __name__ == "__main__":
    user_query = input("추천받고싶은 내용을 입력하세요: ")
    recommendations = query_recommend_etfs(user_query)
    print(recommendations)
    print(":::AI의 추천 목록:")
    for etf in recommendations:
        print(f"{etf['ticker']} - {etf['category']}")
