from app.db.connection import get_connection
from app.schemas.portfolio import PortfolioCreate
import json

def create_portfolio(portfolio_data: PortfolioCreate):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO portfolio (user_id, name, content, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            """
            cursor.execute(sql, (
                portfolio_data.userId,
                portfolio_data.name,
                json.dumps(portfolio_data.content)  # JSON 데이터 저장
            ))
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()

def get_portfolio_by_id(portfolio_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT 
                portfolio_id AS portfolioId,
                user_id AS userId,
                name,
                content,
                created_at AS createdAt,
                updated_at AS updatedAt
            FROM portfolio
            WHERE portfolio_id = %s
            """
            cursor.execute(sql, (portfolio_id,))
            result = cursor.fetchone()
            if result:
                result["content"] = json.loads(result["content"])  # JSON 데이터 변환
            return result
    finally:
        conn.close()

def get_portfolios_by_user(user_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT 
                portfolio_id AS portfolioId,
                user_id AS userId,
                name,
                content,
                created_at AS createdAt,
                updated_at AS updatedAt
            FROM portfolio
            WHERE user_id = %s
            """
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            for row in results:
                row["content"] = json.loads(row["content"])  # JSON 데이터 변환
            return results
    finally:
        conn.close()
