from db.connection import get_connection

def get_etf_by_ticker(ticker: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT 
                etf_id, 
                ticker, 
                sector, 
                name, 
                mbti_code, 
                description, 
                mbti_vector
            FROM etf 
            WHERE ticker = %s
            """
            cursor.execute(sql, (ticker,))
            result = cursor.fetchone()
            return result
    finally:
        conn.close()
