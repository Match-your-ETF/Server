from app.db.connection import get_connection

def get_etf_by_ticker(ticker: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT 
                *
            FROM etf 
            WHERE ticker = %s
            """
            cursor.execute(sql, (ticker,))
            result = cursor.fetchone()
            return result
    finally:
        conn.close()
