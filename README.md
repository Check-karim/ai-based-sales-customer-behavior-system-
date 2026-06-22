# Deluxe Supermarket - AI Sales & Customer Behavior System

An AI-powered admin dashboard for **Deluxe Supermarket** that analyzes sales data and customer behavior, with PDF and Excel report downloads.

## Features

- **Admin authentication** with predefined credentials
- **Sales dashboard** with revenue, transactions, and customer metrics
- **AI analytics** powered by scikit-learn:
  - Customer segmentation (RFM + K-Means clustering)
  - Churn risk prediction
  - Purchase pattern analysis
  - Sales forecasting
  - Behavior insights generation
- **Report downloads** in PDF and Excel formats
- **MySQL database** with sample supermarket data

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, Flask |
| Database | MySQL |
| AI/ML | scikit-learn, NumPy |
| Reports | openpyxl (Excel), ReportLab (PDF) |
| Frontend | HTML, CSS (Jinja2 templates) |

## Prerequisites

- Python 3.10+
- MySQL Server 8.0+
- pip (Python package manager)

## Installation

### 1. Clone or navigate to the project

```bash
cd "ai based sales behavior"
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the example environment file and edit your MySQL credentials:

```bash
copy .env.example .env
```

Edit `.env`:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=deluxe_supermarket
SECRET_KEY=your-secret-key
```

### 5. Initialize the database

Make sure MySQL is running, then:

```bash
python init_db.py
```

This creates the `deluxe_supermarket` database, loads the schema, seeds sample data, and creates the admin user.

Alternatively, import the SQL file manually:

```bash
mysql -u root -p < schema.sql
python init_db.py
```

## Running the Application

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

## User Pages

| Page | URL | Description |
|------|-----|-------------|
| Homepage | `/` | Welcome page with featured products |
| About Us | `/about` | Store story, mission, and values |
| Register | `/register` | Create a customer account |
| Login | `/login` | Sign in as a customer |
| My Account | `/profile` | View account details and purchase history |

## Admin Login

| Field | Value |
|-------|-------|
| URL | `/admin/login` |
| Username | `admin` |
| Password | `admin` |

## Project Structure

```
ai based sales behavior/
├── app.py                  # Flask application entry point
├── config.py               # Configuration settings
├── database.py             # MySQL connection helpers
├── init_db.py              # Database initialization script
├── schema.sql              # MySQL schema and seed data
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── services/
│   ├── ai_analytics.py     # AI/ML analytics engine
│   └── reports.py          # PDF and Excel report generators
├── templates/
│   ├── base.html           # Base layout with navigation
│   ├── home.html           # Public homepage
│   ├── about.html          # About us page
│   ├── register.html       # Customer registration
│   ├── user_login.html     # Customer login
│   ├── profile.html        # Customer account page
│   ├── admin_login.html    # Admin login page
│   ├── dashboard.html      # Admin analytics dashboard
│   └── reports.html        # Admin report downloads
└── static/
    └── css/
        └── style.css       # Application styles
```

## Dashboard Sections

- **Sales Summary** — Total revenue, transactions, average order value
- **AI Sales Forecast** — Predicted revenue with growth rate and confidence
- **Top Products** — Best-selling items by revenue
- **Customer Segments** — AI-driven RFM segmentation (Champion, Loyal, Occasional, At Risk)
- **Churn Risk** — Customers at risk of leaving with probability scores
- **Purchase Patterns** — Category-level buying trends
- **Payment Methods** — Distribution of payment types
- **Loyalty Tier Analysis** — Spending by Bronze/Silver/Gold/Platinum tiers
- **AI Behavior Insights** — Actionable customer behavior recommendations

## Report Downloads

From the **Reports** page, admins can download:

- **Excel (.xlsx)** — Multi-sheet workbook with all analytics data
- **PDF** — Formatted executive summary report

## Database Schema

| Table | Description |
|-------|-------------|
| `admins` | Admin user accounts |
| `categories` | Product categories |
| `products` | Supermarket products |
| `customers` | Customer profiles with loyalty tiers |
| `users` | Registered customer accounts |
| `sales` | Transaction records |
| `sale_items` | Individual line items per sale |
| `behavior_insights` | Stored AI-generated insights |

## License

This project is for educational and demonstration purposes.
