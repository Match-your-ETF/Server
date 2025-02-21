import pandas as pd
import numpy as np
import pymysql
import datetime
import json
import decimal
# from pathlib import Path
from app.ai.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, client

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

#7. 유클리드 거리 기반 추천함수
def euclid_etfs(target_vector, etf_data, nums=5, mode="target"):
    """
    유저의 target_vector와 etf_data의 mbti_vector 간의 유클리드 거리를 계산하여,
    가장 유사한 ETF를 상위 5개 추천합니다.

    이 함수는 최초 컨텍스트-포트폴리오 생성 시, 이니셜_레커맨드_etfs로 사용됩니다.
    """
    def euclidean_distance(vec):
        return np.linalg.norm(vec - target_vector)

    etf_data = etf_data.copy()
    etf_data["distance"] = etf_data["mbti_vector"].apply(euclidean_distance)
    recommended = etf_data.sort_values(by="distance").head(nums)
    return recommended

#8. 비중 조정 함수
def normalize_allocation(allocation_list):
    """
    주어진 allocation_list의 각 항목의 allocation이 전체 100이 되도록 정규화합니다.
    예시: [{"etf": "VOO", "allocation": 38}, {"etf": "QQQ", "allocation": 42}, {"etf": "ARKK", "allocation": 20}]
    """
    #print('::얼로케이션::',allocation_list,':::디버그::') #얼로케이션 함수에서 etf키를 ticker로 고쳐보기
    total = sum(item["allocation"] for item in allocation_list)
    if total == 0:
        return allocation_list
    return [{"ticker": item["ticker"], "allocation": round(item["allocation"] / total * 100, 2)}
            for item in allocation_list]

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

#AI2. 피드백 생성 함수
def generate_feedback(portfolio_id, user_id):
    """
    portfolio_id와 user_id를 받아 해당 포트폴리오의 revision 데이터를 기반으로 AI 피드백을 생성하고,
    재조정된 ETF 비중 정보와 함께, 현재 사용자가 보유한 ETF 정보(current_etfs)를 인자로 전달하여
    추천이 이를 반영하도록 합니다.
    """
    # 사용자 정보 조회
    user_info = fetch_user_info(user_id)
    if not user_info:
        return "사용자 정보를 찾을 수 없습니다.", []

    # 포트폴리오 최신 revision 조회
    revision_data = fetch_revision_by_portfolio(portfolio_id)
    if not revision_data:
        return "포트폴리오 데이터가 없습니다.", []
    etf_data = fetch_etf_data()

    portfolio_pc_vector = get_portfolio_pc_vector(revision_data)
    target_vector = np.array(user_info.get("mbti_vector"))
    preference_etfs = euclid_etfs(target_vector, etf_data)

    market_conditions = revision_data.get("market_indicators",
                                          {"interest_rate": 1.50, "inflation_rate": 1.00, "exchange_rate": 1300.0})
    mbti_recommendation = fetch_mbti_recommendation(user_info.get("mbti_code"))

    # AI 기반 추가 ETF 추천 (여기서는 단순히 텍스트로 된 ETF 리스트를 반환)
    ai_etf_recommendation = ai_recommend_etfs(user_info, etf_data, market_conditions, mbti_recommendation)
    if not ai_etf_recommendation:
        return json.dumps({"error": "AI 추천 ETF를 생성할 수 없습니다."}, ensure_ascii=False)

    # 기존 revision 데이터의 ETF 정보는 "current_etfs"로 전달
    current_etfs = revision_data.get("etfs", {})
    if isinstance(current_etfs, dict):
        current_etfs = current_etfs.get("etfs", [])

    # 기존 revision ETF와 AI 추천 ETF를 합산하여 전체 포트폴리오의 비중을 재조정
    rebalanced_allocation = get_allocation_with_revision_rebalance(
        recommended_etfs=ai_etf_recommendation,
        revision_etfs=revision_data.get("etfs", {})
    )

    # analyze_portfolio 함수에 전달할 payload 구성
    function_payload = {
        "portfolio_pc_vector": portfolio_pc_vector.tolist(),
        "target_pc_vector": target_vector.tolist(),
        "preference_etfs": preference_etfs[["ticker"]].to_dict(orient="list"),
        "mbti_recommendation_etfs": mbti_recommendation,
        "current_etfs": current_etfs,  # 현재 사용자가 보유한 ETF 정보 추가
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
    Your role is to provide personalized, actionable advice based on the Korean investor's portfolio data, market conditions, and profile details.

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
                "description": "Analyze ETF portfolio data and generate feedback including ETF recommendations, considering the user's profile, market conditions, MBTI based suggestions, and current ETF holdings.",
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
                        "current_etfs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ticker": {"type": "string"},
                                    "allocation": {"type": "number"}
                                },
                                "required": ["ticker", "allocation"]
                            },
                            "description": "List of ETFs currently held by the user from revision data."
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
    feedback_text = message.content
    if not feedback_text:
        if "function_call" in message and "arguments" in message["function_call"]:
            try:
                func_args = json.loads(message["function_call"]["arguments"])
                feedback_text = func_args.get("feedback", "피드백 정보가 제공되지 않았습니다.")
            except Exception as e:
                print("function_call arguments 파싱 에러:", e)
                feedback_text = "피드백 정보를 파싱할 수 없습니다."
        else:
            feedback_text = "피드백 정보가 제공되지 않았습니다."
        # TODO: 리비전 데이터 - etfs, market_indicators, user_indicators 및 ai_feedback 업데이트
        update_revision_data(
            portfolio_id,
            rebalanced_allocation,
            market_conditions,
            user_info,
            feedback_text
        )
    return feedback_text, rebalanced_allocation

#AI3. 신규 ETF 비중 함수
def get_allocation_for_etfs(etfs):
    """
    AI에게 ETF 리스트를 전달하여, 각 ETF에 대한 추천 비중을 산출합니다.
    입력된 ETF 리스트에 대해 전체 할당이 100%가 되도록 배분하며,
    결과는 반드시 [{"ticker": "VOO", "allocation": 40}, ...] 형태의 JSON 배열로만 반환되어야 합니다.
    """
    prompt = f"""
    You are a financial portfolio optimizer.
    Given the following ETFs: {etfs},
    please allocate them into a portfolio so that the total allocation sums to exactly 100%.
    Ensure you consider diversification and risk management.

    Return only a JSON array where each element is an object with exactly two keys:
      "ticker": a string representing the ETF ticker,
      "allocation": a number representing the percentage allocation.
    For example:
    [
        {{"ticker": "VOO", "allocation": 40}},
        {{"ticker": "QQQ", "allocation": 35}},
        {{"ticker": "ARKK", "allocation": 25}}
    ]
    Do not include any explanations or additional text.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a financial portfolio optimizer."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content.strip()

    # Markdown 코드 블록 제거 (예: ```json ... ```)
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        recommended_allocation = json.loads(content)
        total_allocation = sum(item["allocation"] for item in recommended_allocation)

        if total_allocation != 100:
            print("Warning: AI allocation sum is not 100%. Adjusting...")
            recommended_allocation = normalize_allocation(recommended_allocation)

        return recommended_allocation
    except Exception as e:
        print("Error parsing AI allocation recommendation:", e)
        return []

#AI4. 병합 ETF 비중함수
def get_allocation_with_revision_rebalance(recommended_etfs, revision_etfs, existing_weight_ratio=0.7):
    """
    기존 revision의 ETF 할당과 AI 추천 ETF 리스트를 기반으로 전체 비중을 재조정하는 함수.

    매개변수:
      recommended_etfs (list): AI 추천 ETF 티커 리스트 (예: ["VOO", "QQQ", "ARKK"]).
      revision_etfs (str 또는 dict): 기존 revision의 ETF 정보.
          형식은 {"etfs": [{"ticker": "SPY", "allocation": 40}, ...]}.
      existing_weight_ratio (float): 전체 포트폴리오에서 기존 ETF에 할당할 비율 (0과 1 사이).
         기본값은 0.7 (70%).

    반환:
      전체 포트폴리오 ETF 비중 리스트 (예: [{"ticker": "VOO", "allocation": 35}, {"ticker": "QQQ", "allocation": 25}, {"ticker": "ARKK", "allocation": 40}]).
    """
    # revision_etfs가 문자열이면 JSON 파싱
    if isinstance(revision_etfs, str):
        try:
            revision_etfs = json.loads(revision_etfs)
        except Exception as e:
            print("기존 revision etfs 파싱 실패:", e)
            revision_etfs = {}

    # 기존 ETF 할당 정보를 딕셔너리로 추출 (ticker: allocation)
    existing_allocations = {}
    if revision_etfs and "etfs" in revision_etfs:
        for item in revision_etfs["etfs"]:
            ticker = item.get("ticker")
            allocation = item.get("allocation", 0)
            if ticker:
                existing_allocations[ticker] = allocation

    # 추천 ETF 리스트 중 기존에 없는 신규 ETF 도출
    new_etfs = [etf for etf in recommended_etfs if etf not in existing_allocations]

    # 기존 ETF의 전체 할당 합이 이미 100에 가깝다고 가정하고, 이를 지정된 비율 (예: 70%)로 낮춥니다.
    total_existing = sum(existing_allocations.values())
    rebalanced_existing = []
    if total_existing > 0:
        for ticker, alloc in existing_allocations.items():
            new_alloc = round(alloc / total_existing * (existing_weight_ratio * 100), 2)
            rebalanced_existing.append({"ticker": ticker, "allocation": new_alloc})

    # 신규 ETF에 대해서는 AI 추천 비중을 받되, 전체에서 (1 - existing_weight_ratio)%를 할당합니다.
    rebalanced_new = []
    if new_etfs:
        new_allocations = get_allocation_for_etfs(new_etfs)
        total_new_alloc = sum(item["allocation"] for item in new_allocations) if new_allocations else 0
        if total_new_alloc > 0:
            for item in new_allocations:
                new_alloc = round(item["allocation"] / total_new_alloc * ((1 - existing_weight_ratio) * 100), 2)
                rebalanced_new.append({"ticker": item["ticker"], "allocation": new_alloc})

    # 기존 ETF와 신규 ETF 비중을 병합
    merged_allocations = rebalanced_existing + rebalanced_new
    print(merged_allocations,"디버그용") #todo : 병합계산식 디버그 필요
    # 전체 합이 100이 되도록 정규화
    total = sum(item["allocation"] for item in merged_allocations)
    if total != 100:
        merged_allocations = normalize_allocation(merged_allocations)

    return merged_allocations

#제이슨 직렬화처리
def json_serial(obj):
    """JSON 직렬화가 불가능한 타입을 변환하는 함수"""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (np.float32, np.float64, np.float16, np.int32, np.int64)):
        return float(obj)
    raise TypeError("Type not serializable")
#AI5. 리비전 데이터 업데이트 함수
def update_revision_data(portfolio_id, merged_allocations, market_indicators, user_indicators, ai_feedback):
    """포트폴리오 리비전 데이터를 업데이트하는 함수"""
    print(':::update_revision_data 함수가 호출되었습니다.:::')

    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = connection.cursor()

        # 최신 revision_id 조회
        cursor.execute(
            "SELECT revision_id FROM revision WHERE portfolio_id = %s ORDER BY revision_id DESC LIMIT 1",
            (portfolio_id,)
        )
        result = cursor.fetchone()

        if result:
            revision_id = result[0]

            # None 또는 빈 값 처리
            if not ai_feedback or ai_feedback in ["", "null", "None"]:
                ai_feedback_json = json.dumps({"feedback": "AI 피드백 데이터 없음"}, ensure_ascii=False)
            elif isinstance(ai_feedback, (dict, list)):
                ai_feedback_json = json.dumps(ai_feedback, ensure_ascii=False, default=json_serial)
            else:
                ai_feedback_json = json.dumps({"feedback": str(ai_feedback)}, ensure_ascii=False)

            # JSON 직렬화 (불가능한 타입 변환 포함)
            etfs_json = json.dumps({"etfs": merged_allocations}, ensure_ascii=False, default=json_serial)
            market_indicators_json = json.dumps(market_indicators, ensure_ascii=False, default=json_serial)
            user_indicators_json = json.dumps(user_indicators, ensure_ascii=False, default=json_serial)

            # MySQL JSON 칼럼이 빈 문자열을 허용하지 않으면 NULL로 변환
            if ai_feedback_json == '""':
                ai_feedback_json = 'null'

            query = """
                UPDATE revision
                SET etfs = %s,
                    market_indicators = %s,
                    user_indicators = %s,
                    ai_feedback = %s
                WHERE portfolio_id = %s AND revision_id = %s
            """
            cursor.execute(query, (
                etfs_json,
                market_indicators_json,
                user_indicators_json,
                ai_feedback_json,
                portfolio_id,
                revision_id
            ))
            connection.commit()

        else:
            print("해당 portfolio_id에 대한 revision 데이터 없음.")

        cursor.close()
        connection.close()

    except Exception as e:
        print("Error updating revision data:", e)
# --- 실행 테스트 ---
if __name__ == "__main__":
    portfolio_id = "102"  # 예시: 유저1의 첫 포트폴리오
    user_id = "1"
    feedback_text, allocation_info = generate_feedback(portfolio_id, user_id)
    print("AI 투자 피드백:")
    print(feedback_text)
    print("\n재조정된 포트폴리오 비중 정보:")
    print(allocation_info)
