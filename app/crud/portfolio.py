from app.db.connection import get_connection
from fastapi import HTTPException
import json
import decimal
from app.schemas.portfolio import *

def convert_decimal_to_float(data):
    """딕셔너리 내부의 Decimal 값을 float으로 변환"""
    if isinstance(data, decimal.Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: convert_decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_decimal_to_float(i) for i in data]
    return data

def create_portfolio_with_context(user_id: int, mbti_code: str, mbti_vector: str):
    """
    1. context 생성 후 ID 가져오기
    2. portfolio 생성
    3. revision 생성
    4. mbti 테이블에서 ETF 데이터 조회 후 리턴
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE user SET mbti_vector = %s WHERE user_id = %s",
            (mbti_vector, user_id)
        )
        conn.commit()

        # context 테이블에 새로운 행 추가
        cursor.execute("INSERT INTO context (user_id, name) VALUES (%s, %s)", (user_id, None))
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
            return None

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

def get_portfolio_logs(context_id: int) -> PortfolioLogsResponse:
    """ 특정 context_id에 속한 모든 포트폴리오의 revision 로그 조회 및 context name 포함 """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # context 테이블에서 name 조회
        cursor.execute("SELECT name FROM context WHERE context_id = %s", (context_id,))
        context_row = cursor.fetchone()

        if not context_row:
            raise HTTPException(status_code=404, detail=f"해당 context_id에 대한 포트폴리오 로그 데이터가 없습니다.")

        context_name = context_row.get("name") if context_row else None

        # context_id에 해당하는 portfolio_id 목록 조회
        cursor.execute("SELECT portfolio_id FROM portfolio WHERE context_id = %s", (context_id,))
        rows = cursor.fetchall()
        portfolio_ids = [row["portfolio_id"] if isinstance(row, dict) else row[0] for row in rows]

        if not portfolio_ids:
            return PortfolioLogsResponse(name=context_name, data=[])

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

        # JSON 변환 후 데이터 리스트 생성
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

        return PortfolioLogsResponse(name=context_name, data=result)

    except Exception as e:
        print(f"DB 조회 오류: {e}")  # 기존 코드
        return PortfolioLogsResponse(name=None, data=[])

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
        cursor.execute(
            "INSERT INTO portfolio (context_id, created_at, updated_at) VALUES (%s, NOW(), NOW())",
            (context_id,)
        )
        conn.commit()

        # 새로 생성된 portfolio_id 가져오기
        cursor.execute("SELECT LAST_INSERT_ID()")
        portfolio_id = cursor.fetchone()["LAST_INSERT_ID()"]

        # 새로운 revision 생성
        cursor.execute(
            """
            INSERT INTO revision (portfolio_id, etfs, market_indicators, user_indicators, ai_feedback) 
            VALUES (%s, %s, %s, %s, %s)
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
        return None

    finally:
        cursor.close()
        conn.close()

def decision_portfolio(context_id: int, data: DecisionPortfolioRequest) -> DecisionPortfolioResponse:
    """
    주어진 context_id로 context 테이블의 name을 업데이트하고 변경된 데이터를 반환
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # context_id로 기존 레코드 조회
        cursor.execute(
            "SELECT context_id, name, user_id, created_at, updated_at FROM context WHERE context_id = %s",
            (context_id,)
        )
        existing_context = cursor.fetchone()

        if not existing_context:
            print(f"[Error] Context ID {context_id} not found")
            return None  # 존재하지 않는 경우 None 반환

        # name 업데이트 실행
        cursor.execute(
            "UPDATE context SET name = %s, updated_at = NOW() WHERE context_id = %s",
            (data.name, context_id)
        )
        conn.commit()

        # 업데이트된 행이 있는지 확인
        if cursor.rowcount == 0:
            print(f"[Warning] No rows were updated. Possible duplicate name or already updated.")

        # 업데이트된 데이터 가져오기
        cursor.execute(
            "SELECT context_id, name, user_id, created_at, updated_at FROM context WHERE context_id = %s",
            (context_id,)
        )
        updated_context = cursor.fetchone()

        if updated_context is None:
            print(f"[Error] Failed to retrieve updated context data for context_id={context_id}")
            return None  # SELECT 결과가 None이면 None 반환

        print(f"[Success] Updated Context Data: {updated_context}")

        return DecisionPortfolioResponse(**updated_context)

    except Exception as e:
        conn.rollback()
        print(f"[Error] Failed to update context name: {e}")
        return None

    finally:
        cursor.close()
        conn.close()

def update_portfolio_etfs(portfolio_id: int, data: UpdatePortfolioEtfsRequest):
    """
    주어진 portfolio_id로 revision 테이블의 etfs를 업데이트하고 revision 데이터를 반환
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # revision 찾기
        query = """
            SELECT revision_id FROM revision
            WHERE portfolio_id = %s
        """
        cursor.execute(query, (portfolio_id,))
        latest_revision = cursor.fetchone()

        if not latest_revision:
            print(f"No revisions found for portfolio_id={portfolio_id}")
            return None

        revision_id = latest_revision["revision_id"]

        # revision 테이블 업데이트 (etfs 필드 업데이트)
        query = """
            UPDATE revision
            SET etfs = %s
            WHERE revision_id = %s
        """
        cursor.execute(query, (json.dumps(data.etfs, ensure_ascii=False), revision_id))
        conn.commit()

        # 업데이트된 revision 데이터 가져오기
        query = """
            SELECT portfolio_id, revision_id, etfs, market_indicators, user_indicators, ai_feedback
            FROM revision
            WHERE revision_id = %s
        """
        cursor.execute(query, (revision_id,))
        updated_revision = cursor.fetchone()

        if not updated_revision:
            print(f"Failed to retrieve updated revision for revision_id={revision_id}")
            return None

        # JSON 변환 후 반환
        return {
            "portfolio_id": updated_revision["portfolio_id"],
            "revision_id": updated_revision["revision_id"],
            "etfs": json.loads(updated_revision["etfs"]),
            "market_indicators": json.loads(updated_revision["market_indicators"]),
            "user_indicators": json.loads(updated_revision["user_indicators"]),
            "ai_feedback": json.loads(updated_revision["ai_feedback"]),
        }

    except Exception as e:
        conn.rollback()
        print(f"DB 업데이트 오류: {e}")
        return None

    finally:
        cursor.close()
        conn.close()
