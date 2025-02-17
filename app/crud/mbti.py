from app.db.connection import get_connection

def get_mbti_etfs(mbtiCode: str):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    description, etf1, allocation1, etf2, allocation2, etf3, allocation3, 
                       etf4, allocation4, etf5, allocation5
                FROM mbti
                WHERE mbti_code = %s
            """
            cursor.execute(sql, (mbtiCode,))
            mbti_data = cursor.fetchone()
        return mbti_data
    finally:
        connection.close()
