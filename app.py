from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime, date

from config import Config
from database import execute_query
from services.ai_analytics import get_full_dashboard_data
from services.reports import generate_excel_report, generate_pdf_report

app = Flask(__name__)
app.config.from_object(Config)


@app.context_processor
def inject_now():
  return {"now": datetime.now()}


def admin_required(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if "admin_id" not in session:
      flash("Please log in as admin to access this page.", "warning")
      return redirect(url_for("admin_login"))
    return f(*args, **kwargs)
  return decorated


def user_required(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if "user_id" not in session:
      flash("Please log in to access your account.", "warning")
      return redirect(url_for("user_login"))
    return f(*args, **kwargs)
  return decorated


def verify_admin(username, password):
  admin = execute_query(
    "SELECT id, username, password_hash, full_name FROM admins WHERE username = %s",
    (username,),
    fetch_one=True,
  )
  if admin and check_password_hash(admin["password_hash"], password):
    return admin
  if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
    return ensure_default_admin()
  return None


def ensure_default_admin():
  existing = execute_query(
    "SELECT id, username, password_hash, full_name FROM admins WHERE username = %s",
    (Config.ADMIN_USERNAME,),
    fetch_one=True,
  )
  if existing:
    return existing

  password_hash = generate_password_hash(Config.ADMIN_PASSWORD)
  admin_id = execute_query(
    "INSERT INTO admins (username, password_hash, full_name) VALUES (%s, %s, %s)",
    (Config.ADMIN_USERNAME, password_hash, "System Administrator"),
  )
  return {
    "id": admin_id,
    "username": Config.ADMIN_USERNAME,
    "full_name": "System Administrator",
  }


def get_user_by_username(username):
  return execute_query(
    """
    SELECT u.id, u.username, u.email, u.password_hash, u.first_name, u.last_name,
           u.phone, u.customer_id, c.loyalty_tier
    FROM users u
    LEFT JOIN customers c ON u.customer_id = c.id
    WHERE u.username = %s
    """,
    (username,),
    fetch_one=True,
  )


def get_user_profile(user_id):
  return execute_query(
    """
    SELECT u.id, u.username, u.email, u.first_name, u.last_name, u.phone,
           u.customer_id, u.created_at, c.loyalty_tier, c.registration_date
    FROM users u
    LEFT JOIN customers c ON u.customer_id = c.id
    WHERE u.id = %s
    """,
    (user_id,),
    fetch_one=True,
  )


# --- Public routes ---

@app.route("/")
def home():
  try:
    featured_products = execute_query(
      """
      SELECT p.name, p.price, c.name AS category
      FROM products p
      JOIN categories c ON p.category_id = c.id
      ORDER BY p.stock_quantity DESC
      LIMIT 6
      """,
      fetch=True,
    ) or []
  except Exception:
    featured_products = []
  return render_template("home.html", featured_products=featured_products)


@app.route("/about")
def about():
  return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
  if "user_id" in session:
    return redirect(url_for("profile"))

  if request.method == "POST":
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    phone = request.form.get("phone", "").strip()

    errors = []
    if not all([username, email, password, first_name, last_name]):
      errors.append("All required fields must be filled in.")
    if len(username) < 3:
      errors.append("Username must be at least 3 characters.")
    if len(password) < 6:
      errors.append("Password must be at least 6 characters.")
    if password != confirm_password:
      errors.append("Passwords do not match.")

    if errors:
      for error in errors:
        flash(error, "danger")
      return render_template("register.html")

    if execute_query("SELECT id FROM users WHERE username = %s", (username,), fetch_one=True):
      flash("Username is already taken.", "danger")
      return render_template("register.html")

    if execute_query("SELECT id FROM users WHERE email = %s", (email,), fetch_one=True):
      flash("Email is already registered.", "danger")
      return render_template("register.html")

    try:
      customer_id = execute_query(
        """
        INSERT INTO customers (first_name, last_name, email, phone, loyalty_tier, registration_date)
        VALUES (%s, %s, %s, %s, 'Bronze', %s)
        """,
        (first_name, last_name, email, phone or None, date.today()),
      )

      password_hash = generate_password_hash(password)
      user_id = execute_query(
        """
        INSERT INTO users (username, email, password_hash, first_name, last_name, phone, customer_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (username, email, password_hash, first_name, last_name, phone or None, customer_id),
      )

      session["user_id"] = user_id
      session["user_name"] = f"{first_name} {last_name}"
      flash("Welcome to Deluxe Supermarket! Your account has been created.", "success")
      return redirect(url_for("profile"))
    except Exception as e:
      flash(f"Registration failed: {e}", "danger")

  return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def user_login():
  if "user_id" in session:
    return redirect(url_for("profile"))

  if request.method == "POST":
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
      session["user_id"] = user["id"]
      session["user_name"] = f"{user['first_name']} {user['last_name']}"
      flash("Welcome back!", "success")
      return redirect(url_for("profile"))

    flash("Invalid username or password.", "danger")

  return render_template("user_login.html")


@app.route("/logout")
def user_logout():
  session.pop("user_id", None)
  session.pop("user_name", None)
  flash("You have been logged out.", "info")
  return redirect(url_for("home"))


@app.route("/profile")
@user_required
def profile():
  user = get_user_profile(session["user_id"])
  purchases = execute_query(
    """
    SELECT sale_date, total_amount, payment_method
    FROM sales
    WHERE customer_id = %s
    ORDER BY sale_date DESC
    LIMIT 10
    """,
    (user["customer_id"],),
    fetch=True,
  ) or []
  return render_template("profile.html", user=user, purchases=purchases)


# --- Admin routes ---

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
  if "admin_id" in session:
    return redirect(url_for("dashboard"))

  if request.method == "POST":
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    admin = verify_admin(username, password)
    if admin:
      session["admin_id"] = admin["id"]
      session["admin_name"] = admin.get("full_name", admin["username"])
      flash("Welcome back, Admin!", "success")
      return redirect(url_for("dashboard"))

    flash("Invalid admin credentials.", "danger")

  return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
  session.pop("admin_id", None)
  session.pop("admin_name", None)
  flash("Admin session ended.", "info")
  return redirect(url_for("home"))


@app.route("/admin/dashboard")
@admin_required
def dashboard():
  try:
    data = get_full_dashboard_data()
  except Exception as e:
    flash(f"Database error: {e}. Please run init_db.py and check your MySQL connection.", "danger")
    data = {
      "summary": {"total_transactions": 0, "total_revenue": 0, "avg_transaction": 0, "unique_customers": 0},
      "monthly_sales": [],
      "top_products": [],
      "customer_segments": [],
      "churn_risk": [],
      "purchase_patterns": [],
      "payment_methods": [],
      "loyalty_analysis": [],
      "behavior_insights": [],
      "forecast": {"forecast_revenue": 0, "growth_rate": 0, "confidence": 0},
    }

  return render_template("dashboard.html", data=data)


@app.route("/admin/reports")
@admin_required
def reports():
  return render_template("reports.html")


@app.route("/admin/download/excel")
@admin_required
def download_excel():
  try:
    buffer = generate_excel_report()
    filename = f"deluxe_supermarket_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
      buffer,
      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      as_attachment=True,
      download_name=filename,
    )
  except Exception as e:
    flash(f"Failed to generate Excel report: {e}", "danger")
    return redirect(url_for("reports"))


@app.route("/admin/download/pdf")
@admin_required
def download_pdf():
  try:
    buffer = generate_pdf_report()
    filename = f"deluxe_supermarket_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(
      buffer,
      mimetype="application/pdf",
      as_attachment=True,
      download_name=filename,
    )
  except Exception as e:
    flash(f"Failed to generate PDF report: {e}", "danger")
    return redirect(url_for("reports"))


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0", port=5000)
