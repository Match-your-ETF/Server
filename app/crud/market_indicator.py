from app.db.connection import get_connection

def get_market_indicator_by_name(name: str):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT market_indicator_id, name, interest_rate, inflation_rate, exchange_rate, 
                       created_at, updated_at
                FROM market_indicator
                WHERE name = %s
            """
            cursor.execute(sql, (name,))
            market_data = cursor.fetchone()

        if not market_data:
            return None

        # Decimal 값을 float으로 변환
        for key in ["interest_rate", "inflation_rate", "exchange_rate"]:
            if market_data[key] is not None:
                market_data[key] = float(market_data[key])

        return market_data
    finally:
        connection.close()

def get_market_indicators():
    """ market_indicator 테이블의 모든 데이터를 조회 """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT market_indicator_id, name, interest_rate, inflation_rate, exchange_rate, created_at, updated_at
            FROM market_indicator
            ORDER BY market_indicator_id ASC
        """
        cursor.execute(query)
        market_data = cursor.fetchall()

        if not market_data:
            return []

        return market_data

    except Exception as e:
        print(f"DB 조회 오류: {e}")
        return []

    finally:
        cursor.close()
        conn.close()
