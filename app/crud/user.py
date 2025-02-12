from app.db.connection import get_connection

def get_user_by_id(user_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM user WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            return result
    finally:
        conn.close()
