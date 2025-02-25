import pandas as pd
import numpy as np
import pymysql
import json
from app.ai.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, client

# 사용자 정보 조회 함수
def fetch_user_info(user_id):
    """
    user 테이블에서 사용자 정보를 조회하고, mbti_vector를 numpy 배열로 변환.
    """
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = "SELECT * FROM user WHERE user_id = %s"
    user_data = pd.read_sql(query, connection, params=[user_id])
    connection.close()
    if user_data.empty:
        return {}
    row = user_data.iloc[0].to_dict()
    row["mbti_vector"] = np.fromstring(row["mbti_vector"].strip("[]"), sep=',').tolist()
    return row

# ETF 데이터 조회 함수
def fetch_etf_data():
    """
    MySQL에서 ETF 데이터를 로드 (티커 및 mbti_vector 포함)
    """
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = "SELECT ticker, category, trailing_pe, trailing_annual_dividend_yield, three_year_average_return, mbti_vector FROM etf"
    etf_data = pd.read_sql(query, connection)
    connection.close()
    etf_data["mbti_vector"] = etf_data["mbti_vector"].apply(
        lambda x: np.fromstring(x.strip("[]"), sep=',') if x else np.zeros(4)
    )
    return etf_data

# MBTI 추천 ETF 조회 함수
def fetch_mbti_recommendation(mbti_code):
    """
    mbti 테이블에서 해당 mbti_code에 따른 추천 ETF 목록 조회.
    """
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = """
        SELECT etf1, etf2, etf3, etf4, etf5
        FROM mbti
        WHERE mbti_code = %s
    """
    df = pd.read_sql(query, connection, params=[mbti_code])
    connection.close()
    if df.empty:
        return []
    row = df.iloc[0]
    recommended = [row[col] for col in ["etf1", "etf2", "etf3", "etf4", "etf5"] if pd.notnull(row[col])]
    return recommended

# 유클리드 거리 기반 ETF 추천 함수
def euclid_etfs(target_vector, etf_data, nums=5, mode="target"):
    """
    유저의 target_vector와 etf_data의 mbti_vector 간의 유클리드 거리를 계산하여,
    가장 유사한 ETF를 상위 nums개 추천.
    """
    def euclidean_distance(vec):
        return np.linalg.norm(vec - target_vector)
    etf_data = etf_data.copy()
    etf_data["distance"] = etf_data["mbti_vector"].apply(euclidean_distance)
    recommended = etf_data.sort_values(by="distance").head(nums)
    return recommended

# AI 기반 ETF 추천 함수
def ai_recommend_etfs(user_info, etf_data, market_conditions, mbti_recommendation):
    prompt = f"""
    You are a financial strategist AI.
    Based on the investor's profile:
      - Age: {user_info.get('age')}
      - Investment Period (months): {user_info.get('investment_period')}
      - Investment Amount: {user_info.get('investment_amount')}
      - Investment Goal: {user_info.get('investment_goal')}
      - Rebalancing Frequency (months): {user_info.get('rebalancing_frequency')}
      - Investment Style: {user_info.get('mbti_vector')}
    and current market conditions: {json.dumps(market_conditions)},
    as well as MBTI recommendations: {mbti_recommendation},
    please recommend a list of 3 ETFs from the following options: {etf_data['ticker'].tolist()}.
    Consider diversification, risk management, and growth potential.
    Return your response strictly as a plain list of tickers, like this:
    [VOO, QQQ, ARKK]
    Do NOT return JSON or any other format.
    Do NOT include explanations, just the plain list.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a financial strategist AI."},
            {"role": "user", "content": prompt}
        ]
    )
    print("AI recommend_etfs response:", response)
    content = response.choices[0].message.content.strip()
    if not content:
        print("AI recommendation response is empty, returning default empty list.")
        return []
    try:
        print("AI recommendation raw output:", content)
        return content  # 반환값은 단순 티커 리스트 문자열
    except Exception as e:
        print("Error parsing AI recommendation:", e)
        return []
