from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime, date

from config import Config
from database import execute_query
from services.ai_analytics import (
  get_full_dashboard_data,
  get_sales_forecast,
  segment_customers_rfm,
  predict_churn_risk,
  generate_behavior_insights,
  get_top_products,
)
from services.reports import generate_excel_report, generate_pdf_report
from services.store import (
  PAYMENT_METHODS,
  SALE_STATUSES,
  get_available_products,
  get_all_products,
  get_product,
  get_categories,
  get_cart_products,
  create_purchase,
  get_customer_purchases,
  get_purchase_detail,
  get_all_purchases,
  create_product,
  update_product,
  delete_product,
  update_purchase_status,
)

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
  purchases = get_customer_purchases(user["customer_id"])[:5]
  return render_template("profile.html", user=user, purchases=purchases)


# --- User shopping routes ---

def get_cart():
  return session.get("cart", {})


def save_cart(cart):
  session["cart"] = cart


@app.route("/shop")
def shop():
  products = get_available_products()
  return render_template("shop.html", products=products, cart_count=sum(get_cart().values()))


@app.route("/shop/add-to-cart", methods=["POST"])
@user_required
def add_to_cart():
  product_id = request.form.get("product_id", type=int)
  quantity = request.form.get("quantity", type=int, default=1)

  if not product_id or quantity < 1:
    flash("Invalid product or quantity.", "danger")
    return redirect(url_for("shop"))

  product = get_product(product_id)
  if not product or product["stock_quantity"] < 1:
    flash("Product is not available.", "danger")
    return redirect(url_for("shop"))

  cart = get_cart()
  pid = str(product_id)
  current_qty = cart.get(pid, 0)
  new_qty = current_qty + quantity
  if new_qty > product["stock_quantity"]:
    flash(f"Only {product['stock_quantity']} units of {product['name']} available.", "warning")
    new_qty = product["stock_quantity"]

  cart[pid] = new_qty
  save_cart(cart)
  flash(f"Added {product['name']} to your cart.", "success")
  return redirect(url_for("shop"))


@app.route("/cart")
@user_required
def cart():
  cart_items = get_cart_products(get_cart())
  total = sum(item["subtotal"] for item in cart_items)
  return render_template(
    "cart.html",
    cart_items=cart_items,
    total=total,
    payment_methods=PAYMENT_METHODS,
  )


@app.route("/cart/update", methods=["POST"])
@user_required
def update_cart():
  cart = get_cart()
  for key in request.form:
    if key.startswith("qty_"):
      product_id = key[4:]
      quantity = request.form.get(key, type=int, default=0)
      if quantity <= 0:
        cart.pop(product_id, None)
      else:
        product = get_product(int(product_id))
        if product and quantity > product["stock_quantity"]:
          quantity = product["stock_quantity"]
        cart[product_id] = quantity
  save_cart(cart)
  flash("Cart updated.", "info")
  return redirect(url_for("cart"))


@app.route("/cart/checkout", methods=["POST"])
@user_required
def checkout():
  payment_method = request.form.get("payment_method", "Card")
  cart_items = get_cart_products(get_cart())
  if not cart_items:
    flash("Your cart is empty.", "warning")
    return redirect(url_for("shop"))

  user = get_user_profile(session["user_id"])
  try:
    sale_id = create_purchase(
      user["customer_id"],
      [{"product_id": item["product_id"], "quantity": item["quantity"]} for item in cart_items],
      payment_method,
    )
    save_cart({})
    flash(f"Purchase placed successfully! Order #{sale_id}", "success")
    return redirect(url_for("purchase_detail", sale_id=sale_id))
  except ValueError as e:
    flash(str(e), "danger")
    return redirect(url_for("cart"))


@app.route("/purchases")
@user_required
def purchases():
  user = get_user_profile(session["user_id"])
  purchase_list = get_customer_purchases(user["customer_id"])
  return render_template("purchases.html", purchases=purchase_list)


@app.route("/purchases/<int:sale_id>")
@user_required
def purchase_detail(sale_id):
  user = get_user_profile(session["user_id"])
  purchase = get_purchase_detail(sale_id, customer_id=user["customer_id"])
  if not purchase:
    flash("Purchase not found.", "danger")
    return redirect(url_for("purchases"))
  return render_template("purchase_detail.html", purchase=purchase)


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


@app.route("/admin/products")
@admin_required
def admin_products():
  products = get_all_products()
  return render_template("admin_products.html", products=products)


@app.route("/admin/products/add", methods=["GET", "POST"])
@admin_required
def admin_add_product():
  categories = get_categories()
  if request.method == "POST":
    name = request.form.get("name", "").strip()
    category_id = request.form.get("category_id", type=int)
    price = request.form.get("price", type=float)
    stock_quantity = request.form.get("stock_quantity", type=int, default=0)

    if not name or not category_id or price is None or price < 0:
      flash("Please fill in all required fields correctly.", "danger")
      return render_template("admin_product_form.html", product=None, categories=categories)

    create_product(name, category_id, price, max(stock_quantity, 0))
    flash(f"Product '{name}' added successfully.", "success")
    return redirect(url_for("admin_products"))

  return render_template("admin_product_form.html", product=None, categories=categories)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_product(product_id):
  product = get_product(product_id)
  if not product:
    flash("Product not found.", "danger")
    return redirect(url_for("admin_products"))

  categories = get_categories()
  if request.method == "POST":
    name = request.form.get("name", "").strip()
    category_id = request.form.get("category_id", type=int)
    price = request.form.get("price", type=float)
    stock_quantity = request.form.get("stock_quantity", type=int, default=0)

    if not name or not category_id or price is None or price < 0:
      flash("Please fill in all required fields correctly.", "danger")
      return render_template("admin_product_form.html", product=product, categories=categories)

    update_product(product_id, name, category_id, price, max(stock_quantity, 0))
    flash(f"Product '{name}' updated successfully.", "success")
    return redirect(url_for("admin_products"))

  return render_template("admin_product_form.html", product=product, categories=categories)


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def admin_delete_product(product_id):
  product = get_product(product_id)
  if not product:
    flash("Product not found.", "danger")
    return redirect(url_for("admin_products"))

  try:
    delete_product(product_id)
    flash(f"Product '{product['name']}' deleted.", "success")
  except ValueError as e:
    flash(str(e), "danger")
  return redirect(url_for("admin_products"))


@app.route("/admin/purchases")
@admin_required
def admin_purchases():
  purchase_list = get_all_purchases()
  return render_template("admin_purchases.html", purchases=purchase_list)


@app.route("/admin/purchases/<int:sale_id>")
@admin_required
def admin_purchase_detail(sale_id):
  purchase = get_purchase_detail(sale_id)
  if not purchase:
    flash("Purchase not found.", "danger")
    return redirect(url_for("admin_purchases"))
  return render_template(
    "admin_purchase_detail.html",
    purchase=purchase,
    statuses=SALE_STATUSES,
  )


@app.route("/admin/purchases/<int:sale_id>/status", methods=["POST"])
@admin_required
def admin_update_purchase_status(sale_id):
  status = request.form.get("status", "")
  try:
    update_purchase_status(sale_id, status)
    flash(f"Purchase #{sale_id} status updated to {status}.", "success")
  except ValueError as e:
    flash(str(e), "danger")
  return redirect(url_for("admin_purchase_detail", sale_id=sale_id))


@app.route("/admin/predictions")
@admin_required
def admin_predictions():
  try:
    data = {
      "forecast": get_sales_forecast(),
      "segments": segment_customers_rfm(),
      "churn_risk": predict_churn_risk(),
      "insights": generate_behavior_insights(),
      "top_products": get_top_products(10),
    }
  except Exception as e:
    flash(f"Failed to load predictions: {e}", "danger")
    data = {
      "forecast": {"forecast_revenue": 0, "growth_rate": 0, "confidence": 0},
      "segments": [],
      "churn_risk": [],
      "insights": [],
      "top_products": [],
    }
  return render_template("admin_predictions.html", data=data)


if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0", port=5000)
