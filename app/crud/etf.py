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

def search_etfs(keyword: str, limit: int = 6):
    """ETF 데이터를 LIKE 검색 후 반환"""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT ticker FROM etf
            WHERE ticker LIKE %s 
            LIMIT %s
            """
            cursor.execute(sql, (f"%{keyword}%", limit))
            results = cursor.fetchall()
    except Exception as e:
        print(f"DB 검색 오류: {e}")
        results = []
    finally:
        connection.close()

    return [{"ticker": row["ticker"]} for row in results]
