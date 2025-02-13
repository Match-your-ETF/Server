import pandas as pd
import numpy as np
import openai
import pymysql
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 현재 파일의 두 단계 위에 위치한 .env 파일 경로 설정
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

# 환경변수에서 GPT API 키 등 읽기
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
gpt_api_key = os.getenv('GPT_API_KEY')

# openai 설정
openai.api_key = gpt_api_key
client = openai.OpenAI(api_key=openai.api_key)

# --- DB 함수 정의 ---
#1. user정보 조회
def fetch_user_info(user_id):
    """user 테이블에서 사용자 정보를 모두 조회하고, mbti_vector를 numpy 배열로 변환"""
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
    # mbti_vector 변환
    row["mbti_vector"] = np.fromstring(row["mbti_vector"].strip("[]"), sep=',').tolist()
    return row
#2. p_id로 Rdata 찾기
def fetch_revision_by_portfolio(portfolio_id):
    """
    MySQL에서 특정 portfolio_id에 해당하는 revision 데이터를 조회.
    (포트폴리오와 revision은 1:1 대응 관계)
    """
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = """
        SELECT etfs, market_indicators, user_indicators, ai_feedback
        FROM revision
        WHERE portfolio_id = %s
        ORDER BY revision_id DESC
        LIMIT 1
    """
    revision_data = pd.read_sql(query, connection, params=[portfolio_id])
    connection.close()

    if revision_data.empty:
        return {}
    row = revision_data.iloc[0]
    return {
        "etfs": row["etfs"],
        "market_indicators": row["market_indicators"],
        "user_indicators": row["user_indicators"],
        "ai_feedback": row["ai_feedback"]
    }

#3. u_id로 mbti벡터 찾기
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

#4. etf_data 반환
def fetch_etf_data():
    """MySQL에서 ETF 데이터 로드 (티커와 mbti_vector 포함)"""
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    query = "SELECT ticker,category,trailing_pe,trailing_annual_dividend_yield,three_year_average_return, mbti_vector FROM etf"
    etf_data = pd.read_sql(query, connection)
    connection.close()

    etf_data["mbti_vector"] = etf_data["mbti_vector"].apply(
        lambda x: np.fromstring(x.strip("[]"), sep=',') if x else np.zeros(4)
    )
    return etf_data
#5. mbti기반 추천코드
def fetch_mbti_recommendation(mbti_code):
    """
    mbti 테이블에서 해당 mbti_code에 따른 추천 ETF 목록을 조회.
    (NULL 값은 제외)
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
#6. 리비전 벡터 계산
def get_portfolio_pc_vector(revision_data):
    """
    , etf_data 는 잠시 생략
    revision_data의 etfs 필드를 기반으로 포트폴리오의 PCA 벡터를 계산.
    revision_data["etfs"]는 ETF 목록 정보가 포함된 JSON 문자열임.
    (예시: 각 ETF의 allocation의 평균을 4차원 벡터로 확장)
    """
    if not revision_data.get("etfs"):
        return np.zeros(4)
    try:
        etf_info = revision_data["etfs"]
        if isinstance(etf_info, str):
            etf_info = json.loads(etf_info)
        allocations = [etf.get("allocation", 0) for etf in etf_info.get("etfs", [])]
    except Exception as e:
        print("JSON 파싱 에러:", e)
        return np.zeros(4)

    mean_alloc = np.mean(allocations) if allocations else 0
    return np.array([mean_alloc] * 4)

#7. etf들 추천함수
def recommend_etfs(target_vector, etf_data, mode="target"):
    """
    유저의 target_vector와 etf_data의 mbti_vector 간의 유클리드 거리를 계산하여,
    가장 유사한 ETF를 상위 5개 추천합니다.

    이 함수는 최초 컨텍스트-포트폴리오 생성 시, 이니셜_레커맨드_etfs로 사용됩니다.
    """
    def euclidean_distance(vec):
        return np.linalg.norm(vec - target_vector)

    etf_data = etf_data.copy()
    etf_data["distance"] = etf_data["mbti_vector"].apply(euclidean_distance)
    recommended = etf_data.sort_values(by="distance").head(5)
    return recommended


# --- 인공지능 함수 ---
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

    Return your response **strictly as a plain list of tickers**, like this:
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

    content = response.choices[0].message.content.strip()
    if not content:
        print("AI recommendation response is empty, returning default empty list.")
        return []
    try:
        print(content)
        gpt_recommendation = content
        return gpt_recommendation
    except Exception as e:
        print("Error parsing AI recommendation:", e)
        return []


def generate_feedback(portfolio_id, user_id):
    """
    portfolio_id와 user_id를 받아 해당 포트폴리오의 revision 데이터를 기반으로 AI 피드백을 생성.
    사용자 정보, 시장 지표, MBTI 추천, 그리고 두 방식의 ETF 추천 정보를 종합하여
    AI 투자 피드백을 생성합니다.
    피드백 생성 후, 필요시 새 revision 기록을 생성하는 흐름으로 확장할 수 있습니다.
    """

    # 사용자 정보 조회
    user_info = fetch_user_info(user_id)
    if not user_info:
        return "사용자 정보를 찾을 수 없습니다.", []

    # 포트폴리오 최신 revision 조회
    revision_data = fetch_revision_by_portfolio(portfolio_id)
    if not revision_data:
        return "포트폴리오 데이터가 없습니다.", []
    # ETF 데이터 조회
    etf_data = fetch_etf_data()

    # 포트폴리오의 PCA 벡터 계산
    portfolio_pc_vector = get_portfolio_pc_vector(revision_data)
    # 성향 기반 추천 ETF (유클리드 거리 기준)
    target_vector = np.array(user_info.get("mbti_vector"))
    preference_etfs = recommend_etfs(target_vector, etf_data)

    # 시장 지표: revision 데이터에 저장된 market_indicators 활용 (없으면 기본값)
    market_conditions = revision_data.get("market_indicators",
                                          {"interest_rate": 1.50, "inflation_rate": 1.00, "exchange_rate": 1300.0})

    # MBTI 추천 ETF: mbti 테이블에서 조회
    mbti_recommendation = fetch_mbti_recommendation(user_info.get("mbti_code"))

    # AI 기반 추가 ETF 추천
    ai_etf_recommendation = ai_recommend_etfs(user_info, etf_data, market_conditions, mbti_recommendation)

    # 함수 호출에 전달할 payload 구성 (티커 정보만 사용)
    function_payload = {
        "portfolio_pc_vector": portfolio_pc_vector.tolist(),
        "target_pc_vector": target_vector.tolist(),
        "preference_etfs": preference_etfs[["ticker"]].to_dict(orient="list"),
        "mbti_recommendation_etfs": mbti_recommendation,
        "user_info": {
            "name": user_info.get("name"),
            "age": user_info.get("age"),
            "investment_period": user_info.get("investment_period"),
            "investment_amount": user_info.get("investment_amount"),
            "investment_goal": user_info.get("investment_goal"),
            "rebalancing_frequency": user_info.get("rebalancing_frequency")
        },
        "market_conditions": market_conditions
    }

    prompt = """
    You are WISE (Wealth Investment Strategic Expert), an AI investment advisor specializing in ETF portfolio analysis and optimization.
    Your role is to provide personalized, actionable advice based on the investor's portfolio data, market conditions, and profile details.

    Please analyze the following aspects:
    1. Overall asset allocation strategy
    2. Risk-return balance
    3. Market condition alignment
    4. Goal compatibility

    Respond in the following format:
    1. 포트폴리오 평가 (2-3줄)
    2. 강점 (글머리 기호로 2-3개)
    3. 위험 요소 (글머리 기호로 1-2개)
    4. 조언 (단기/장기)
    5. 추천 ETF
 
    포트폴리오 평가 및 투자 피드백은 자유로운 텍스트 형식으로 작성해 주세요.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 투자 분석 전문가입니다."},
            {"role": "user", "content": prompt},
            {"role": "assistant",
             "function_call": {"name": "analyze_portfolio", "arguments": json.dumps(function_payload)}}
        ],
        functions=[
            {
                "name": "analyze_portfolio",
                "description": "Analyze ETF portfolio data and generate feedback including ETF recommendations, considering user profile, market conditions, and MBTI based suggestions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_pc_vector": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "The PCA vector of the user's current portfolio."
                        },
                        "target_pc_vector": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "The target PCA vector representing the investor's ideal style."
                        },
                        "preference_etfs": {
                            "type": "object",
                            "properties": {
                                "ticker": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "description": "List of ETF tickers recommended based on similarity."
                        },
                        "ai_recommendation_etfs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Additional ETF recommendations based on AI strategic analysis."
                        },
                        "mbti_recommendation_etfs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "ETF tickers recommended based on the user's MBTI profile."
                        },
                        "user_info": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "age": {"type": "number"},
                                "investment_period": {"type": "number"},
                                "investment_amount": {"type": "number"},
                                "investment_goal": {"type": "string"},
                                "rebalancing_frequency": {"type": "number"}
                            }
                        },
                        "market_conditions": {
                            "type": "object",
                            "properties": {
                                "interest_rate": {"type": "number"},
                                "inflation_rate": {"type": "number"},
                                "exchange_rate": {"type": "number"}
                            }
                        }
                    },
                    "required": ["portfolio_pc_vector", "target_pc_vector", "preference_etfs", "user_info",
                                 "market_conditions"]
                }
            }
        ]
    )

    message = response.choices[0].message
    # 최종 피드백 텍스트 반환 (message.content에 피드백이 포함되어 있습니다)
    feedback_text = message.content
    return feedback_text, ai_etf_recommendation


# --- 실행 테스트 ---
if __name__ == "__main__":
    # 예시: portfolio_id 1 (유저1의 첫 포트폴리오), user_id 1
    portfolio_id = "1"
    user_id = "1"
    feedback, ai_etfs = generate_feedback(portfolio_id, user_id)
    print("AI 투자 피드백:")
    print(feedback)
    print("\nAI 추천 ETF 리스트:")
    print(ai_etfs)
