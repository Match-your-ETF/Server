import json
import datetime
import decimal
import numpy as np
import pandas as pd
import pymysql
from app.ai.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, client

# revision 데이터를 조회하는 함수
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

# revision 데이터를 기반으로 PCA 벡터 계산
def get_portfolio_pc_vector(revision_data):
    """
    revision_data의 etfs 필드를 기반으로 포트폴리오의 PCA 벡터를 계산.
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

# 할당 리스트를 전체 100%로 정규화하는 함수
def normalize_allocation(allocation_list):
    """
    주어진 allocation_list의 각 항목의 allocation이 전체 100이 되도록 정규화합니다.
    예시: [{"ticker": "VOO", "allocation": 38}, {"ticker": "QQQ", "allocation": 42}, {"ticker": "ARKK", "allocation": 20}]
    """
    total = sum(item["allocation"] for item in allocation_list)
    if total == 0:
        return allocation_list
    return [{"ticker": item["ticker"], "allocation": round(item["allocation"] / total * 100, 2)}
            for item in allocation_list]

# JSON 직렬화 헬퍼 함수
def json_serial(obj):
    """JSON 직렬화가 불가능한 타입을 변환하는 함수"""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (np.float32, np.float64, np.float16, np.int32, np.int64)):
        return float(obj)
    raise TypeError("Type not serializable")

# AI를 호출하여 ETF 리스트의 할당비율을 생성하는 함수
def get_allocation_for_etfs(etfs):
    """
    AI에게 ETF 리스트를 전달하여, 각 ETF에 대한 추천 비중을 산출합니다.
    전체 할당이 100%가 되도록 배분하며, 결과는 반드시 [{"ticker": "VOO", "allocation": 40}, ...] 형태로 반환.
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

    # 코드 블록 제거 처리
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

# 기존 revision의 ETF와 AI 추천 ETF를 합산하여 전체 비중 재조정
def get_allocation_with_revision_rebalance(recommended_etfs, revision_etfs, existing_weight_ratio=0.7):
    """
    기존 revision의 ETF 할당과 AI 추천 ETF 리스트를 기반으로 전체 비중을 재조정하는 함수.
    """
    # revision_etfs가 문자열이면 JSON 파싱
    if isinstance(revision_etfs, str):
        try:
            revision_etfs = json.loads(revision_etfs)
        except Exception as e:
            print("기존 revision etfs 파싱 실패:", e)
            revision_etfs = {}

    # 기존 ETF 할당 정보를 딕셔너리로 추출
    existing_allocations = {}
    if revision_etfs and "etfs" in revision_etfs:
        for item in revision_etfs["etfs"]:
            ticker = item.get("ticker")
            allocation = item.get("allocation", 0)
            if ticker:
                existing_allocations[ticker] = allocation

    # 추천 ETF 중 기존에 없는 신규 ETF 도출
    new_etfs = [etf for etf in recommended_etfs if etf not in existing_allocations]

    # 기존 ETF의 전체 할당 합을 지정된 비율로 조정
    total_existing = sum(existing_allocations.values())
    rebalanced_existing = []
    if total_existing > 0:
        for ticker, alloc in existing_allocations.items():
            new_alloc = round(alloc / total_existing * (existing_weight_ratio * 100), 2)
            rebalanced_existing.append({"ticker": ticker, "allocation": new_alloc})

    # 신규 ETF에 대해서는 AI 추천 비중을 받아 전체에서 (1 - existing_weight_ratio)% 할당
    rebalanced_new = []
    if new_etfs:
        new_allocations = get_allocation_for_etfs(new_etfs)
        total_new_alloc = sum(item["allocation"] for item in new_allocations) if new_allocations else 0
        if total_new_alloc > 0:
            for item in new_allocations:
                new_alloc = round(item["allocation"] / total_new_alloc * ((1 - existing_weight_ratio) * 100), 2)
                rebalanced_new.append({"ticker": item["ticker"], "allocation": new_alloc})

    # 기존 ETF와 신규 ETF 병합
    merged_allocations = rebalanced_existing + rebalanced_new
    print(merged_allocations, "디버그용")
    total = sum(item["allocation"] for item in merged_allocations)
    if total != 100:
        merged_allocations = normalize_allocation(merged_allocations)
    return merged_allocations

# DB의 revision 데이터를 업데이트하는 함수
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
            # ai_feedback 처리
            if not ai_feedback or ai_feedback in ["", "null", "None"]:
                ai_feedback_json = json.dumps({"feedback": "AI 피드백 데이터 없음"}, ensure_ascii=False)
            elif isinstance(ai_feedback, (dict, list)):
                ai_feedback_json = json.dumps(ai_feedback, ensure_ascii=False, default=json_serial)
            else:
                ai_feedback_json = json.dumps({"feedback": str(ai_feedback)}, ensure_ascii=False)

            etfs_json = json.dumps({"etfs": merged_allocations}, ensure_ascii=False, default=json_serial)
            market_indicators_json = json.dumps(market_indicators, ensure_ascii=False, default=json_serial)
            user_indicators_json = json.dumps(user_indicators, ensure_ascii=False, default=json_serial)

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
            print('R데이터 쿼리 실행.')
            cursor.execute(query, (
                etfs_json,
                market_indicators_json,
                user_indicators_json,
                ai_feedback_json,
                portfolio_id,
                revision_id
            ))
            connection.commit()
            print('R데이터 커밋이 완료되었습니다.')
        else:
            print("해당 portfolio_id에 대한 revision 데이터 없음.")
        cursor.close()
        connection.close()
    except Exception as e:
        print("Error updating revision data:", e)

# revision 데이터를 기반으로 AI 피드백을 생성하고 DB를 업데이트하는 함수
def generate_feedback(portfolio_id, user_id, market_data="default"):
    """
    portfolio_id와 user_id를 받아 해당 포트폴리오의 revision 데이터를 기반으로 AI 피드백을 생성하고,
    재조정된 ETF 비중 정보와 함께 현재 사용자가 보유한 ETF 정보를 반영하여 추천합니다.
    """
    from app.ai.ai import fetch_user_info, fetch_etf_data, fetch_mbti_recommendation, ai_recommend_etfs, euclid_etfs

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

    market_conditions = market_data
    print(f"사용할 시장 지표: {market_conditions}")

    mbti_recommendation = fetch_mbti_recommendation(user_info.get("mbti_code"))
    ai_etf_recommendation = ai_recommend_etfs(user_info, etf_data, market_conditions, mbti_recommendation)
    if not ai_etf_recommendation:
        return json.dumps({"error": "AI 추천 ETF를 생성할 수 없습니다."}, ensure_ascii=False)

    current_etfs = revision_data.get("etfs", {})
    if isinstance(current_etfs, dict):
        current_etfs = current_etfs.get("etfs", [])

    rebalanced_allocation = get_allocation_with_revision_rebalance(
        recommended_etfs=ai_etf_recommendation,
        revision_etfs=revision_data.get("etfs", {})
    )

    function_payload = {
        "portfolio_pc_vector": portfolio_pc_vector.tolist(),
        "target_pc_vector": target_vector.tolist(),
        "preference_etfs": preference_etfs[["ticker"]].to_dict(orient="list"),
        "mbti_recommendation_etfs": mbti_recommendation,
        "current_etfs": current_etfs,
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
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        # todo : 펑션콜을 의무로 태우면서도 user 프롬프트 안에 있는 내용대로 최종응답이 와야한다.
        # (펑션 페이로드에 있는 인자들을 json형태의 포맷으로 반드시 전달해야함. 펑션을 안타는경우 종종있음)
        messages=[
            {"role": "system", "content": "당신은 투자 분석 전문가입니다. 모든 요청에 대해 반드시 analyze_portfolio 펑션을 호출하여야 합니다."},
            {"role": "user", "content": prompt},
            {"role": "assistant",
             "function_call": {"name": "analyze_portfolio", "arguments": json.dumps(function_payload)}}
        ],
        functions=[
            {
                "name": "analyze_portfolio",
                "description": "Analyze ETF portfolio data and generate feedback including ETF recommendations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_pc_vector": {"type": "array", "items": {"type": "number"}},
                        "target_pc_vector": {"type": "array", "items": {"type": "number"}},
                        "preference_etfs": {"type": "object", "properties": {"ticker": {"type": "array", "items": {"type": "string"}}}},
                        "ai_recommendation_etfs": {"type": "array", "items": {"type": "string"}},
                        "mbti_recommendation_etfs": {"type": "array", "items": {"type": "string"}},
                        "current_etfs": {"type": "array", "items": {"type": "object", "properties": {"ticker": {"type": "string"}, "allocation": {"type": "number"}}, "required": ["ticker", "allocation"]}},
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
                        "market_conditions": {"type": "object", "properties": {"interest_rate": {"type": "number"}, "inflation_rate": {"type": "number"}, "exchange_rate": {"type": "number"}}}
                    },
                    "required": ["portfolio_pc_vector", "target_pc_vector", "preference_etfs", "user_info", "market_conditions"]
                }
            }
        ],
        function_call="auto"
    )
    message = response.choices[0].message
    if "function_call" in message:
        print("펑션콜이 호출되었습니다:", message["function_call"])
    else:
        print("펑션콜이 호출되지 않았습니다.")
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
            feedback_text = "피드백 생성에 실패했습니다."
    update_revision_data(
        portfolio_id,
        rebalanced_allocation,
        market_conditions,
        user_info,
        feedback_text
    )
    return feedback_text, rebalanced_allocation
