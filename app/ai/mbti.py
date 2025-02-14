from app.ai.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, client
from app.ai.ai import euclid_etfs, fetch_revision_by_portfolio
import pandas as pd
import numpy as np
import pymysql
import json

#0.사용자 정보 가져오기 (mbti_vector와 mbti_code)
def fetch_user_info(user_id):
    """user 테이블에서 mbti_vector와 mbti_code를 불러와 반환"""
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = "SELECT mbti_vector, mbti_code FROM user WHERE user_id = %s"
    df = pd.read_sql(query, connection, params=[user_id])
    connection.close()

    if df.empty:
        return {"mbti_vector": np.zeros(4), "mbti_code": ""}

    vector_str = df.iloc[0]["mbti_vector"]
    mbti_vector = np.fromstring(vector_str.strip("[]"), sep=',')
    mbti_code = df.iloc[0]["mbti_code"]
    return {"mbti_vector": mbti_vector, "mbti_code": mbti_code}

#1. mbti_code로 최초 포트폴리오 강제
def fetch_default_portfolio(mbti_code):
    """
    mbti 테이블에서 해당 성향코드의 기본 ETF 포트폴리오 구성을 가져옵니다.
    반환값은 etf1~etf5와 allocation1~allocation5를 포함하는 Series입니다.
    """
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = """
        SELECT etf1, etf2, etf3, etf4, etf5, 
               allocation1, allocation2, allocation3, allocation4, allocation5 
        FROM mbti 
        WHERE mbti_code = %s
    """
    df = pd.read_sql(query, connection, params=[mbti_code])
    connection.close()

    if df.empty:
        return None
    return df.iloc[0]


#1. u_id로 mbti벡터 찾기
def fetch_user_target_vector(user_id):
    """user 테이블에서 mbti_vector를 불러와 NumPy 배열로 변환"""
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = "SELECT mbti_vector FROM user WHERE user_id = %s"
    target_data = pd.read_sql(query, connection, params=[user_id])
    connection.close()

    if target_data.empty:
        return np.zeros(4)
    vector_str = target_data.iloc[0]["mbti_vector"]
    return np.fromstring(vector_str.strip("[]"), sep=',')

#2. 티커와 etf_mbti 반환
def fetch_etf_mbti():
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = "SELECT ticker,mbti_vector FROM etf"
    etf_data = pd.read_sql(query, connection)
    connection.close()

    etf_data["mbti_vector"] = etf_data["mbti_vector"].apply(
        lambda x: np.fromstring(x.strip("[]"), sep=',') if x else np.zeros(4)
    )
    return etf_data
#3. 성향지향 추천
def recommend_etfs_adjusted_for_user(user_id, etf_data, portfolio_id, alpha=0.7, top_n=4):
    """
    1. 유저 테이블에서 MBTI 벡터와 MBTI 코드를 가져옵니다.
    2. portfolio_id로 revision 데이터를 조회하여 etfs 필드를 가져옵니다.
       - etfs 필드가 비어있으면, fetch_default_portfolio를 통해 기본 포트폴리오를 가져옵니다.
    3. 기본 포트폴리오에 속한 ETF들의 벡터로 가중평균 벡터를 계산한 후,
       유저 MBTI 벡터와 결합하여 adjusted_vector를 도출합니다.
    4. euclid_etfs 함수를 사용해 adjusted_vector 기준으로 ETF들의 유클리드 거리를 계산하고,
       상위 top_n개의 티커 리스트를 반환합니다.

    매개변수:
      user_id (int): 사용자 ID.
      etf_data (DataFrame): ETF 데이터 (ticker, mbti_vector 컬럼 포함).
      portfolio_id: 포트폴리오 ID.
      alpha (float): 사용자 벡터에 부여할 가중치 (0~1, 기본값 0.7).
      top_n (int): 추천할 ETF 수 (기본값 4).

    반환:
      list: 추천 ETF 티커 리스트.
    """
    # 1. 사용자 정보 가져오기 (mbti_vector와 mbti_code)
    user_info = fetch_user_info(user_id)
    user_vector = user_info["mbti_vector"]
    user_mbti_code = user_info["mbti_code"]

    # 2. portfolio_id로 revision 데이터 조회
    revision_data = fetch_revision_by_portfolio(portfolio_id)

    # 3. revision 데이터에서 etfs 필드를 추출 (JSON 형태로 파싱)
    default_portfolio = {}
    if revision_data and revision_data.get("etfs"):
        try:
            default_portfolio = revision_data["etfs"]
            if isinstance(default_portfolio, str):
                default_portfolio = json.loads(default_portfolio)
        except Exception as e:
            default_portfolio = {}

    # 4. etfs 필드가 비어있다면, 기본 포트폴리오를 user_mbti_code를 사용해 가져옵니다.
    if not default_portfolio or default_portfolio == {}:
        default_pf_series = fetch_default_portfolio(user_mbti_code)
        if default_pf_series is None:
            print("기본 포트폴리오 정보를 가져올 수 없습니다.")
            return []
        default_portfolio = {
            "etfs": [
                {"ticker": default_pf_series["etf1"], "allocation": default_pf_series["allocation1"]},
                {"ticker": default_pf_series["etf2"], "allocation": default_pf_series["allocation2"]},
                {"ticker": default_pf_series["etf3"], "allocation": default_pf_series["allocation3"]},
                {"ticker": default_pf_series["etf4"], "allocation": default_pf_series["allocation4"]},
                {"ticker": default_pf_series["etf5"], "allocation": default_pf_series["allocation5"]},
            ]
        }

    # 5. 기본 포트폴리오의 ETF 벡터로 가중평균 벡터 계산 (allocation 총합은 100)
    total_alloc = 0
    weighted_sum = np.zeros_like(user_vector)
    for etf in default_portfolio["etfs"]:
        ticker = etf["ticker"]
        allocation = etf["allocation"]
        total_alloc += allocation
        etf_row = etf_data[etf_data["ticker"] == ticker]
        if not etf_row.empty:
            etf_vector = etf_row.iloc[0]["mbti_vector"]
        else:
            etf_vector = np.zeros_like(user_vector)
        weighted_sum += allocation * etf_vector
    default_weighted_vector = weighted_sum / total_alloc if total_alloc != 0 else np.zeros_like(user_vector)

    # 6. adjusted_vector: 유저 벡터와 기본 포트폴리오 가중평균 벡터의 가중합
    adjusted_vector = alpha * user_vector + (1 - alpha) * default_weighted_vector

    # 7. 유클리드 거리를 계산해 추천 ETF 도출 (euclid_etfs 함수 사용)
    # euclid_etfs 함수는 target_vector와 etf_data, top_n (예: 4)를 인자로 받습니다.
    recommendations_df = euclid_etfs(adjusted_vector, etf_data, top_n)

    return recommendations_df["ticker"].tolist()


if __name__ == "__main__":
    user_id = input("사용자 ID를 입력하세요: ")
    portfolio_id = input("포트폴리오 ID를 입력하세요: ")
    try:
        user_id = int(user_id)
    except ValueError:
        print("유효한 사용자 ID를 입력해주세요.")
        exit(1)

    etf_data = fetch_etf_mbti()

    rec_tickers = recommend_etfs_adjusted_for_user(user_id, etf_data, portfolio_id)
    print("추천 ETF 티커 리스트:", rec_tickers)