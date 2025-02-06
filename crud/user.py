from db.connection import get_connection
from schemas.user import UserCreate

def create_user(user_data: UserCreate):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO user (name, age, mbti_code, mbti_vector, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(sql, (
                user_data.name,
                user_data.age,
                user_data.mbti_code,
                user_data.mbti_vector
            ))
            conn.commit()
            return cursor.lastrowid  # 생성된 user_id 반환
    finally:
        conn.close()

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
