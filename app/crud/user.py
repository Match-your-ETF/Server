from app.db.connection import get_connection
from app.schemas.user import UserLog
from typing import List

def get_user_by_id(user_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT user_id, name, age, investment_period, investment_goal, investment_amount, rebalancing_frequency, mbti_code, mbti_vector FROM user WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            return result
    finally:
        conn.close()

def get_user_logs(user_id: int) -> List[UserLog]:
    """
    특정 사용자의 로그 데이터를 조회하는 함수
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT context_id, name, user_id, created_at, updated_at
            FROM context
            WHERE user_id = %s
            """
            cursor.execute(sql, (user_id,))
            result = cursor.fetchall()
            return [UserLog(**row) for row in result]
    finally:
        connection.close()
