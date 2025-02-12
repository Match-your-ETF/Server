from app.db.connection import get_connection
import json
from fastapi import HTTPException
from app.schemas.portfolio import *
import decimal


def convert_decimal_to_float(data):
    """딕셔너리 내부의 Decimal 값을 float으로 변환"""
    if isinstance(data, decimal.Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: convert_decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_decimal_to_float(i) for i in data]
    return data


def create_portfolio_with_context(user_id: int, mbti_code: str):
    """
    1. context 생성 후 ID 가져오기
    2. portfolio 생성
    3. revision 생성
    4. mbti 테이블에서 ETF 데이터 조회 후 리턴
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # context 테이블에 새로운 행 추가
        cursor.execute("INSERT INTO context (user_id, name) VALUES (%s, %s)", (user_id, "New Context"))
        conn.commit()

        # 새 context_id 가져오기
        cursor.execute("SELECT LAST_INSERT_ID()")
        context_id = cursor.fetchone()["LAST_INSERT_ID()"]

        # portfolio 테이블에 추가
        cursor.execute("INSERT INTO portfolio (context_id) VALUES (%s)", (context_id,))
        conn.commit()

        # 새 portfolio_id 가져오기
        cursor.execute("SELECT LAST_INSERT_ID()")
        portfolio_id = cursor.fetchone()["LAST_INSERT_ID()"]

        # revision 테이블에 추가 (JSON 필드는 빈 JSON)
        cursor.execute(
            "INSERT INTO revision (portfolio_id, etfs, market_indicators, user_indicators, ai_feedback) VALUES (%s, %s, %s, %s, %s)",
            (portfolio_id, '{}', '{}', '{}', '{}')
        )
        conn.commit()

        cursor.execute("SELECT LAST_INSERT_ID()")
        revision_id = cursor.fetchone()["LAST_INSERT_ID()"]

        # mbti 테이블에서 ETF 배분 정보 조회
        cursor.execute(
            """
            SELECT etf1, allocation1, etf2, allocation2, etf3, allocation3, etf4, allocation4, etf5, allocation5 
            FROM mbti 
            WHERE mbti_code = %s
            """,
            (mbti_code,)
        )
        mbti_data = cursor.fetchone()

        if not mbti_data:
            mbti_data = {
                "etf1": None, "allocation1": None,
                "etf2": None, "allocation2": None,
                "etf3": None, "allocation3": None,
                "etf4": None, "allocation4": None,
                "etf5": None, "allocation5": None
            }

        return PortfolioResponse(
            context_id=context_id,
            portfolio_id=portfolio_id,
            revision_id=revision_id,
            **mbti_data
        )

    except Exception as e:
        conn.rollback()
        print(f"DB 에러: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def get_portfolio_logs(context_id: int):
    """ 특정 context_id에 속한 모든 포트폴리오의 revision 로그 조회 """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # context_id에 해당하는 portfolio_id 목록 조회
        query = "SELECT portfolio_id FROM portfolio WHERE context_id = %s"
        cursor.execute(query, (context_id,))
        portfolio_ids = [row["portfolio_id"] for row in cursor.fetchall()]

        if not portfolio_ids:
            print(f"No portfolios found for context_id={context_id}")
            return []

        print(f"Found portfolio_ids: {portfolio_ids}")

        # 해당 portfolio_id들의 revision 로그 조회
        query = f"""
            SELECT portfolio_id, revision_id, etfs, market_indicators, user_indicators, ai_feedback
            FROM revision
            WHERE portfolio_id IN ({','.join(['%s'] * len(portfolio_ids))})
            ORDER BY revision_id DESC
        """
        cursor.execute(query, portfolio_ids)
        logs = cursor.fetchall()

        print(f"Fetched logs: {logs}")

        if not logs:
            return []

        # JSON 변환 후 반환
        result = []
        for log in logs:
            result.append({
                "portfolio_id": log["portfolio_id"],
                "revision_id": log["revision_id"],
                "etfs": json.loads(log["etfs"]),
                "market_indicators": json.loads(log["market_indicators"]),
                "user_indicators": json.loads(log["user_indicators"]),
                "ai_feedback": json.loads(log["ai_feedback"]),
            })

        return result

    except Exception as e:
        print(f"DB 조회 오류: {e}")
        return []

    finally:
        cursor.close()
        conn.close()


def update_custom_portfolio(portfolio_id: int, data: CustomPortfolioRequest):
    """ 사용자가 직접 설정한 포트폴리오 정보를 업데이트 """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 사용자 정보 업데이트 (investment_period, investment_goal, investment_amount, rebalancing_frequency)
        if data.investment_period or data.investment_goal or data.investment_amount or data.rebalancing_frequency:
            query = """
                UPDATE user 
                SET investment_period = %s, investment_goal = %s, investment_amount = %s, rebalancing_frequency = %s
                WHERE user_id = %s
            """
            cursor.execute(query, (
                data.investment_period,
                data.investment_goal,
                data.investment_amount,
                data.rebalancing_frequency,
                data.user_id
            ))
            conn.commit()

        # 선택한 market_indicator 데이터 가져오기 (옵션)
        market_indicators = None
        if data.market_indicator_name:
            query = "SELECT interest_rate, inflation_rate, exchange_rate FROM market_indicator WHERE name = %s"
            cursor.execute(query, (data.market_indicator_name,))
            market_indicator_data = cursor.fetchone()

            if market_indicator_data:
                market_indicator_data = convert_decimal_to_float(market_indicator_data)
                market_indicators = json.dumps(market_indicator_data, ensure_ascii=False)

        # user_indicators 데이터 구성 (user 업데이트 정보 + market_indicator 선택 정보)
        user_indicators = json.dumps({
            "investment_period": data.investment_period,
            "investment_goal": data.investment_goal,
            "investment_amount": data.investment_amount,
            "rebalancing_frequency": data.rebalancing_frequency,
            "market_indicator_name": data.market_indicator_name
        })

        # 최신 revision 찾기 (해당 portfolio의 가장 최신 revision_id)
        query = """
            SELECT revision_id FROM revision 
            WHERE portfolio_id = %s 
            ORDER BY revision_id DESC LIMIT 1
        """
        cursor.execute(query, (portfolio_id,))
        latest_revision = cursor.fetchone()

        if not latest_revision:
            print(f"No revisions found for portfolio_id={portfolio_id}")
            return False

        revision_id = latest_revision["revision_id"]

        # revision 테이블 업데이트 (필수: etfs, 옵션: market_indicators, user_indicators)
        query = """
            UPDATE revision 
            SET etfs = %s, market_indicators = %s, user_indicators = %s 
            WHERE revision_id = %s
        """
        cursor.execute(query, (
            json.dumps(data.etfs, ensure_ascii=False),  # etfs 값 그대로 저장
            market_indicators if market_indicators else "{}",  # market_indicators (선택)
            user_indicators,  # user_indicators (user 정보 + market_indicator 선택 정보)
            revision_id
        ))
        conn.commit()

        return True

    except Exception as e:
        conn.rollback()
        print(f"DB 업데이트 오류: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def decision_investment(context_id: int) -> DecisionInvestmentResponse:
    """ 주어진 context_id를 유지하면서 새로운 portfolio와 revision을 생성 """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 새로운 portfolio 생성
        cursor.execute("INSERT INTO portfolio (context_id, created_at, updated_at) VALUES (%s, NOW(), NOW())",
                       (context_id,))
        conn.commit()

        # 새로 생성된 portfolio_id 가져오기
        cursor.execute("SELECT LAST_INSERT_ID()")
        portfolio_id = cursor.fetchone()["LAST_INSERT_ID()"]

        # 새로운 revision 생성
        cursor.execute(
            """
            INSERT INTO revision (portfolio_id, etfs, market_indicators, user_indicators, ai_feedback, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """,
            (portfolio_id, '{}', '{}', '{}', '{}')
        )
        conn.commit()

        # 새로 생성된 revision_id 가져오기
        cursor.execute("SELECT LAST_INSERT_ID()")
        revision_id = cursor.fetchone()["LAST_INSERT_ID()"]

        # 반환할 응답 생성
        return DecisionInvestmentResponse(portfolio_id=portfolio_id, revision_id=revision_id)

    except Exception as e:
        conn.rollback()
        print(f"[Error] Failed to create investment decision: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        cursor.close()
        conn.close()
