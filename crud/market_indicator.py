from db.connection import get_connection

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
