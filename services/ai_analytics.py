import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from database import execute_query


def get_sales_summary():
  return execute_query(
    """
    SELECT
      COUNT(*) AS total_transactions,
      COALESCE(SUM(total_amount), 0) AS total_revenue,
      COALESCE(AVG(total_amount), 0) AS avg_transaction,
      COUNT(DISTINCT customer_id) AS unique_customers
    FROM sales
    """,
    fetch_one=True,
  )


def get_monthly_sales():
  return execute_query(
    """
    SELECT
      DATE_FORMAT(sale_date, '%Y-%m') AS month,
      COUNT(*) AS transactions,
      SUM(total_amount) AS revenue
    FROM sales
    GROUP BY DATE_FORMAT(sale_date, '%Y-%m')
    ORDER BY month
    """,
    fetch=True,
  )


def get_top_products(limit=10):
  return execute_query(
    """
    SELECT
      p.name AS product_name,
      c.name AS category,
      SUM(si.quantity) AS units_sold,
      SUM(si.subtotal) AS revenue
    FROM sale_items si
    JOIN products p ON si.product_id = p.id
    JOIN categories c ON p.category_id = c.id
    GROUP BY p.id, p.name, c.name
    ORDER BY revenue DESC
    LIMIT %s
    """,
    (limit,),
    fetch=True,
  )


def get_customer_rfm_data():
  return execute_query(
    """
    SELECT
      c.id,
      CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
      c.loyalty_tier,
      DATEDIFF(CURDATE(), MAX(s.sale_date)) AS recency_days,
      COUNT(s.id) AS frequency,
      COALESCE(SUM(s.total_amount), 0) AS monetary
    FROM customers c
    LEFT JOIN sales s ON c.id = s.customer_id
    GROUP BY c.id, c.first_name, c.last_name, c.loyalty_tier
    """,
    fetch=True,
  )


def segment_customers_rfm():
  customers = get_customer_rfm_data()
  if not customers or len(customers) < 2:
    return customers or []

  features = []
  for c in customers:
    recency = max(c["recency_days"] or 365, 1)
    features.append([
      1 / recency,
      c["frequency"] or 0,
      float(c["monetary"] or 0),
    ])

  scaler = StandardScaler()
  scaled = scaler.fit_transform(features)

  n_clusters = min(4, len(customers))
  kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
  labels = kmeans.fit_predict(scaled)

  segment_names = ["At Risk", "Occasional", "Loyal", "Champion"]
  for i, customer in enumerate(customers):
    cluster = labels[i]
    customer["segment"] = segment_names[cluster % len(segment_names)]
    customer["ai_score"] = round(float(scaled[i].mean()) * 50 + 50, 1)

  return customers


def predict_churn_risk():
  customers = get_customer_rfm_data()
  results = []

  for c in customers:
    recency = c["recency_days"] or 365
    frequency = c["frequency"] or 0
    monetary = float(c["monetary"] or 0)

    recency_score = max(0, 100 - recency)
    frequency_score = min(100, frequency * 15)
    monetary_score = min(100, monetary / 5)

    churn_probability = round(
      100 - (recency_score * 0.4 + frequency_score * 0.3 + monetary_score * 0.3),
      1,
    )
    churn_probability = max(0, min(100, churn_probability))

    if churn_probability >= 70:
      risk_level = "High"
    elif churn_probability >= 40:
      risk_level = "Medium"
    else:
      risk_level = "Low"

    results.append({
      "customer_id": c["id"],
      "customer_name": c["customer_name"],
      "loyalty_tier": c["loyalty_tier"],
      "recency_days": recency,
      "frequency": frequency,
      "monetary": monetary,
      "churn_probability": churn_probability,
      "risk_level": risk_level,
    })

  return sorted(results, key=lambda x: x["churn_probability"], reverse=True)


def get_purchase_patterns():
  return execute_query(
    """
    SELECT
      c.name AS category,
      COUNT(si.id) AS purchase_count,
      SUM(si.subtotal) AS category_revenue,
      AVG(si.quantity) AS avg_quantity
    FROM sale_items si
    JOIN products p ON si.product_id = p.id
    JOIN categories c ON p.category_id = c.id
    GROUP BY c.id, c.name
    ORDER BY category_revenue DESC
    """,
    fetch=True,
  )


def get_payment_method_distribution():
  return execute_query(
    """
    SELECT
      payment_method,
      COUNT(*) AS count,
      SUM(total_amount) AS total
    FROM sales
    GROUP BY payment_method
    ORDER BY count DESC
    """,
    fetch=True,
  )


def get_loyalty_tier_analysis():
  return execute_query(
    """
    SELECT
      c.loyalty_tier,
      COUNT(DISTINCT c.id) AS customer_count,
      COALESCE(SUM(s.total_amount), 0) AS total_spent,
      COALESCE(AVG(s.total_amount), 0) AS avg_spent
    FROM customers c
    LEFT JOIN sales s ON c.id = s.customer_id
    GROUP BY c.loyalty_tier
    ORDER BY total_spent DESC
    """,
    fetch=True,
  )


def generate_behavior_insights():
  segments = segment_customers_rfm()
  churn = predict_churn_risk()
  patterns = get_purchase_patterns()

  insights = []

  for seg in segments:
    insights.append({
      "customer_id": seg["id"],
      "customer_name": seg["customer_name"],
      "type": "Segment",
      "value": seg["segment"],
      "confidence": seg.get("ai_score", 75),
    })

  for c in churn[:5]:
    if c["risk_level"] == "High":
      insights.append({
        "customer_id": c["customer_id"],
        "customer_name": c["customer_name"],
        "type": "Churn Risk",
        "value": f"{c['churn_probability']}% - {c['risk_level']}",
        "confidence": 100 - c["churn_probability"],
      })

  if patterns:
    top_category = patterns[0]
    insights.append({
      "customer_id": 0,
      "customer_name": "All Customers",
      "type": "Trend",
      "value": f"Top category: {top_category['category']} (${float(top_category['category_revenue']):.2f})",
      "confidence": 92.5,
    })

  return insights


def get_sales_forecast(days=30):
  monthly = get_monthly_sales()
  if len(monthly) < 2:
    avg_revenue = float(monthly[0]["revenue"]) if monthly else 0
    return {"forecast_revenue": avg_revenue, "growth_rate": 0, "confidence": 60}

  revenues = [float(m["revenue"]) for m in monthly]
  growth_rates = []
  for i in range(1, len(revenues)):
    if revenues[i - 1] > 0:
      growth_rates.append((revenues[i] - revenues[i - 1]) / revenues[i - 1])

  avg_growth = np.mean(growth_rates) if growth_rates else 0
  forecast = revenues[-1] * (1 + avg_growth)

  return {
    "forecast_revenue": round(forecast, 2),
    "growth_rate": round(avg_growth * 100, 1),
    "confidence": min(95, 70 + len(monthly) * 5),
    "historical": monthly,
  }


def get_full_dashboard_data():
  return {
    "summary": get_sales_summary(),
    "monthly_sales": get_monthly_sales(),
    "top_products": get_top_products(),
    "customer_segments": segment_customers_rfm(),
    "churn_risk": predict_churn_risk(),
    "purchase_patterns": get_purchase_patterns(),
    "payment_methods": get_payment_method_distribution(),
    "loyalty_analysis": get_loyalty_tier_analysis(),
    "behavior_insights": generate_behavior_insights(),
    "forecast": get_sales_forecast(),
  }
