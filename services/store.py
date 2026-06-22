from datetime import datetime
from decimal import Decimal

from database import execute_query, get_connection

PAYMENT_METHODS = ("Cash", "Card", "Mobile", "Loyalty Points")
SALE_STATUSES = ("Pending", "Confirmed", "Processing", "Ready", "Completed", "Cancelled")


def get_available_products():
  return execute_query(
    """
    SELECT p.id, p.name, p.price, p.stock_quantity, c.name AS category
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.stock_quantity > 0
    ORDER BY c.name, p.name
    """,
    fetch=True,
  ) or []


def get_all_products():
  return execute_query(
    """
    SELECT p.id, p.name, p.price, p.stock_quantity, p.category_id, c.name AS category
    FROM products p
    JOIN categories c ON p.category_id = c.id
    ORDER BY p.name
    """,
    fetch=True,
  ) or []


def get_product(product_id):
  return execute_query(
    """
    SELECT p.id, p.name, p.price, p.stock_quantity, p.category_id, c.name AS category
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.id = %s
    """,
    (product_id,),
    fetch_one=True,
  )


def get_categories():
  return execute_query(
    "SELECT id, name FROM categories ORDER BY name",
    fetch=True,
  ) or []


def get_cart_products(cart):
  if not cart:
    return []

  product_ids = list(cart.keys())
  placeholders = ", ".join(["%s"] * len(product_ids))
  products = execute_query(
    f"""
    SELECT id, name, price, stock_quantity
    FROM products
    WHERE id IN ({placeholders})
    """,
    tuple(int(pid) for pid in product_ids),
    fetch=True,
  ) or []

  items = []
  for product in products:
    pid = str(product["id"])
    quantity = int(cart.get(pid, 0))
    if quantity <= 0:
      continue
    price = Decimal(str(product["price"]))
    items.append({
      "product_id": product["id"],
      "name": product["name"],
      "price": price,
      "stock_quantity": product["stock_quantity"],
      "quantity": quantity,
      "subtotal": price * quantity,
    })
  return items


def create_purchase(customer_id, cart_items, payment_method):
  if payment_method not in PAYMENT_METHODS:
    raise ValueError("Invalid payment method.")

  if not cart_items:
    raise ValueError("Your cart is empty.")

  conn = get_connection()
  cursor = conn.cursor(dictionary=True)
  try:
    product_ids = [item["product_id"] for item in cart_items]
    placeholders = ", ".join(["%s"] * len(product_ids))
    cursor.execute(
      f"SELECT id, name, price, stock_quantity FROM products WHERE id IN ({placeholders})",
      tuple(product_ids),
    )
    products = {row["id"]: row for row in cursor.fetchall()}

    line_items = []
    total_amount = Decimal("0")
    for item in cart_items:
      product = products.get(item["product_id"])
      if not product:
        raise ValueError("One or more products are no longer available.")
      quantity = int(item["quantity"])
      if quantity <= 0:
        continue
      if product["stock_quantity"] < quantity:
        raise ValueError(f"Not enough stock for {product['name']}.")

      unit_price = Decimal(str(product["price"]))
      subtotal = unit_price * quantity
      total_amount += subtotal
      line_items.append({
        "product_id": product["id"],
        "quantity": quantity,
        "unit_price": unit_price,
        "subtotal": subtotal,
      })

    if not line_items:
      raise ValueError("Your cart is empty.")

    cursor.execute(
      """
      INSERT INTO sales (customer_id, sale_date, total_amount, payment_method, status)
      VALUES (%s, %s, %s, %s, 'Pending')
      """,
      (customer_id, datetime.now(), float(total_amount), payment_method),
    )
    sale_id = cursor.lastrowid

    for line in line_items:
      cursor.execute(
        """
        INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
          sale_id,
          line["product_id"],
          line["quantity"],
          float(line["unit_price"]),
          float(line["subtotal"]),
        ),
      )
      cursor.execute(
        "UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s",
        (line["quantity"], line["product_id"]),
      )

    conn.commit()
    return sale_id
  except Exception:
    conn.rollback()
    raise
  finally:
    cursor.close()
    conn.close()


def get_customer_purchases(customer_id):
  return execute_query(
    """
    SELECT id, sale_date, total_amount, payment_method, status
    FROM sales
    WHERE customer_id = %s
    ORDER BY sale_date DESC
    """,
    (customer_id,),
    fetch=True,
  ) or []


def get_purchase_detail(sale_id, customer_id=None):
  if customer_id is not None:
    sale = execute_query(
      """
      SELECT s.id, s.sale_date, s.total_amount, s.payment_method, s.status,
             CONCAT(c.first_name, ' ', c.last_name) AS customer_name
      FROM sales s
      JOIN customers c ON s.customer_id = c.id
      WHERE s.id = %s AND s.customer_id = %s
      """,
      (sale_id, customer_id),
      fetch_one=True,
    )
  else:
    sale = execute_query(
      """
      SELECT s.id, s.sale_date, s.total_amount, s.payment_method, s.status,
             s.customer_id,
             CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
             c.email AS customer_email
      FROM sales s
      JOIN customers c ON s.customer_id = c.id
      WHERE s.id = %s
      """,
      (sale_id,),
      fetch_one=True,
    )

  if not sale:
    return None

  items = execute_query(
    """
    SELECT si.quantity, si.unit_price, si.subtotal, p.name AS product_name
    FROM sale_items si
    JOIN products p ON si.product_id = p.id
    WHERE si.sale_id = %s
    """,
    (sale_id,),
    fetch=True,
  ) or []
  sale["line_items"] = items
  return sale


def get_all_purchases():
  return execute_query(
    """
    SELECT s.id, s.sale_date, s.total_amount, s.payment_method, s.status,
           CONCAT(c.first_name, ' ', c.last_name) AS customer_name
    FROM sales s
    JOIN customers c ON s.customer_id = c.id
    ORDER BY s.sale_date DESC
    """,
    fetch=True,
  ) or []


def create_product(name, category_id, price, stock_quantity):
  return execute_query(
    """
    INSERT INTO products (name, category_id, price, stock_quantity)
    VALUES (%s, %s, %s, %s)
    """,
    (name, category_id, price, stock_quantity),
  )


def update_product(product_id, name, category_id, price, stock_quantity):
  execute_query(
    """
    UPDATE products
    SET name = %s, category_id = %s, price = %s, stock_quantity = %s
    WHERE id = %s
    """,
    (name, category_id, price, stock_quantity, product_id),
  )


def delete_product(product_id):
  linked = execute_query(
    "SELECT id FROM sale_items WHERE product_id = %s LIMIT 1",
    (product_id,),
    fetch_one=True,
  )
  if linked:
    raise ValueError("Cannot delete a product that has been purchased. Set stock to 0 instead.")
  execute_query("DELETE FROM products WHERE id = %s", (product_id,))


def update_purchase_status(sale_id, status):
  if status not in SALE_STATUSES:
    raise ValueError("Invalid purchase status.")
  execute_query(
    "UPDATE sales SET status = %s WHERE id = %s",
    (status, sale_id),
  )
