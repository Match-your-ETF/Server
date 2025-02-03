from db.connection import get_connection

def get_all_etfs():
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT etf_id, ticker, name FROM etf"
            cursor.execute(sql)
            return cursor.fetchall()  # 모든 결과 반환
    finally:
        connection.close()

def get_etf_by_id(etf_id: int):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM etf WHERE etf_id = %s"
            cursor.execute(sql, (etf_id,))
            return cursor.fetchone()  # 단일 결과 반환
    finally:
        connection.close()
