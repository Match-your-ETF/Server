from app.db.connection import get_connection
import json

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

        # mbti 테이블에서 ETF 배분 정보 조회
        cursor.execute("SELECT etf1, allocation1, etf2, allocation2, etf3, allocation3, etf4, allocation4, etf5, allocation5 FROM mbti WHERE mbti_code = %s", (mbti_code,))
        mbti_data = cursor.fetchone()

        if not mbti_data:
            return None  # MBTI 데이터가 없으면 None 반환

        return mbti_data

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
