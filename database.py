import mysql.connector
from mysql.connector import Error
from config import Config


def get_connection():
  return mysql.connector.connect(
    host=Config.MYSQL_HOST,
    port=Config.MYSQL_PORT,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DATABASE,
  )


def execute_query(query, params=None, fetch=False, fetch_one=False):
  conn = None
  cursor = None
  try:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    if fetch_one:
      return cursor.fetchone()
    if fetch:
      return cursor.fetchall()
    conn.commit()
    return cursor.lastrowid
  except Error as e:
    if conn:
      conn.rollback()
    raise e
  finally:
    if cursor:
      cursor.close()
    if conn:
      conn.close()


def execute_many(query, params_list):
  conn = None
  cursor = None
  try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(query, params_list)
    conn.commit()
  except Error as e:
    if conn:
      conn.rollback()
    raise e
  finally:
    if cursor:
      cursor.close()
    if conn:
      conn.close()
