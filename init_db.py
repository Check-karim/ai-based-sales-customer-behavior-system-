"""
Initialize the Deluxe Supermarket database and admin user.

Usage:
  python init_db.py
"""

import mysql.connector
from werkzeug.security import generate_password_hash

from config import Config


def run_schema():
  with open("schema.sql", "r", encoding="utf-8") as f:
    sql_content = f.read()

  statements = []
  current = []
  for line in sql_content.split("\n"):
    stripped = line.strip()
    if stripped.startswith("--") or not stripped:
      continue
    current.append(line)
    if stripped.endswith(";"):
      statements.append("\n".join(current))
      current = []

  conn = mysql.connector.connect(
    host=Config.MYSQL_HOST,
    port=Config.MYSQL_PORT,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
  )
  cursor = conn.cursor()

  for statement in statements:
    try:
      cursor.execute(statement)
    except mysql.connector.Error as e:
      if e.errno not in (1050, 1061, 1062):
        print(f"Warning: {e}")

  conn.commit()
  cursor.close()
  conn.close()
  print("Database schema loaded successfully.")


def setup_admin():
  conn = mysql.connector.connect(
    host=Config.MYSQL_HOST,
    port=Config.MYSQL_PORT,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DATABASE,
  )
  cursor = conn.cursor(dictionary=True)

  password_hash = generate_password_hash(Config.ADMIN_PASSWORD)
  cursor.execute("SELECT id FROM admins WHERE username = %s", (Config.ADMIN_USERNAME,))
  existing = cursor.fetchone()

  if existing:
    cursor.execute(
      "UPDATE admins SET password_hash = %s, full_name = %s WHERE username = %s",
      (password_hash, "System Administrator", Config.ADMIN_USERNAME),
    )
    print(f"Admin user '{Config.ADMIN_USERNAME}' password updated.")
  else:
    cursor.execute(
      "INSERT INTO admins (username, password_hash, full_name) VALUES (%s, %s, %s)",
      (Config.ADMIN_USERNAME, password_hash, "System Administrator"),
    )
    print(f"Admin user '{Config.ADMIN_USERNAME}' created.")

  conn.commit()
  cursor.close()
  conn.close()


if __name__ == "__main__":
  print("Initializing Deluxe Supermarket database...")
  run_schema()
  setup_admin()
  print("Done! Run 'python app.py' to start the application.")
