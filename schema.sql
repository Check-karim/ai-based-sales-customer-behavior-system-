-- Deluxe Supermarket - AI Sales & Customer Behavior System
-- MySQL Database Schema

CREATE DATABASE IF NOT EXISTS deluxe_supermarket;
USE deluxe_supermarket;

-- Admin users table
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product categories
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    loyalty_tier ENUM('Bronze', 'Silver', 'Gold', 'Platinum') DEFAULT 'Bronze',
    registration_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Registered user accounts (linked to customers)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    customer_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Sales transactions
CREATE TABLE IF NOT EXISTS sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    sale_date DATETIME NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    payment_method ENUM('Cash', 'Card', 'Mobile', 'Loyalty Points') DEFAULT 'Card',
    status ENUM('Pending', 'Confirmed', 'Processing', 'Ready', 'Completed', 'Cancelled') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Sale line items
CREATE TABLE IF NOT EXISTS sale_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Customer behavior insights (AI-generated)
CREATE TABLE IF NOT EXISTS behavior_insights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    insight_type VARCHAR(50) NOT NULL,
    insight_value VARCHAR(255) NOT NULL,
    confidence_score DECIMAL(5, 2) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_sales_customer ON sales(customer_id);
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sale_items_product ON sale_items(product_id);
CREATE INDEX idx_customers_loyalty ON customers(loyalty_tier);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Admin user is created by init_db.py with username: admin, password: admin

-- Seed categories
INSERT INTO categories (name, description) VALUES
('Fresh Produce', 'Fruits, vegetables, and organic items'),
('Dairy & Eggs', 'Milk, cheese, yogurt, and eggs'),
('Meat & Seafood', 'Fresh and frozen meat and fish'),
('Bakery', 'Bread, pastries, and cakes'),
('Beverages', 'Soft drinks, juices, and water'),
('Snacks', 'Chips, cookies, and confectionery'),
('Household', 'Cleaning supplies and home essentials'),
('Personal Care', 'Health and beauty products')
ON DUPLICATE KEY UPDATE name = name;

-- Seed products
INSERT INTO products (name, category_id, price, stock_quantity) VALUES
('Organic Bananas (1kg)', 1, 2.49, 150),
('Fresh Strawberries (500g)', 1, 4.99, 80),
('Whole Milk 1L', 2, 1.89, 200),
('Cheddar Cheese 400g', 2, 5.49, 120),
('Free Range Eggs (12)', 2, 3.99, 90),
('Chicken Breast 1kg', 3, 8.99, 60),
('Atlantic Salmon Fillet 500g', 3, 12.99, 45),
('Sourdough Bread', 4, 3.49, 70),
('Chocolate Croissant', 4, 2.29, 100),
('Orange Juice 1L', 5, 2.99, 180),
('Sparkling Water 6-pack', 5, 4.49, 150),
('Potato Chips Family Size', 6, 3.99, 200),
('Dark Chocolate Bar', 6, 2.79, 175),
('Laundry Detergent 2L', 7, 9.99, 85),
('Dish Soap 750ml', 7, 3.49, 110),
('Shampoo 400ml', 8, 6.99, 95),
('Toothpaste 100ml', 8, 3.29, 130)
ON DUPLICATE KEY UPDATE name = name;

-- Seed customers
INSERT INTO customers (first_name, last_name, email, phone, loyalty_tier, registration_date) VALUES
('Alice', 'Johnson', 'alice.j@email.com', '555-0101', 'Gold', '2023-01-15'),
('Bob', 'Smith', 'bob.smith@email.com', '555-0102', 'Silver', '2023-03-22'),
('Carol', 'Williams', 'carol.w@email.com', '555-0103', 'Platinum', '2022-06-10'),
('David', 'Brown', 'david.b@email.com', '555-0104', 'Bronze', '2024-01-05'),
('Emma', 'Davis', 'emma.d@email.com', '555-0105', 'Gold', '2023-08-18'),
('Frank', 'Miller', 'frank.m@email.com', '555-0106', 'Silver', '2023-11-30'),
('Grace', 'Wilson', 'grace.w@email.com', '555-0107', 'Bronze', '2024-02-14'),
('Henry', 'Taylor', 'henry.t@email.com', '555-0108', 'Platinum', '2022-09-25'),
('Ivy', 'Anderson', 'ivy.a@email.com', '555-0109', 'Gold', '2023-05-07'),
('Jack', 'Thomas', 'jack.t@email.com', '555-0110', 'Silver', '2023-12-01')
ON DUPLICATE KEY UPDATE email = email;

-- Seed sales (sample transactions over past 90 days)
INSERT INTO sales (customer_id, sale_date, total_amount, payment_method, status) VALUES
(1, '2025-03-15 10:30:00', 45.67, 'Card', 'Completed'),
(2, '2025-03-16 14:20:00', 23.45, 'Cash', 'Completed'),
(3, '2025-03-17 09:15:00', 89.99, 'Card', 'Completed'),
(1, '2025-03-20 11:00:00', 32.10, 'Mobile', 'Completed'),
(4, '2025-03-22 16:45:00', 15.80, 'Cash', 'Completed'),
(5, '2025-03-25 08:30:00', 67.50, 'Card', 'Completed'),
(6, '2025-03-28 13:10:00', 28.90, 'Card', 'Completed'),
(3, '2025-04-01 10:00:00', 112.30, 'Loyalty Points', 'Completed'),
(7, '2025-04-05 17:20:00', 19.45, 'Cash', 'Completed'),
(8, '2025-04-08 09:45:00', 156.78, 'Card', 'Completed'),
(2, '2025-04-10 12:30:00', 34.20, 'Mobile', 'Completed'),
(9, '2025-04-12 15:00:00', 52.60, 'Card', 'Completed'),
(1, '2025-04-15 10:15:00', 41.30, 'Card', 'Completed'),
(10, '2025-04-18 11:40:00', 27.85, 'Cash', 'Completed'),
(5, '2025-04-22 14:55:00', 78.40, 'Card', 'Completed'),
(3, '2025-04-25 09:30:00', 95.20, 'Card', 'Completed'),
(4, '2025-05-01 16:10:00', 22.15, 'Cash', 'Completed'),
(6, '2025-05-05 10:20:00', 38.70, 'Mobile', 'Completed'),
(8, '2025-05-08 13:45:00', 134.50, 'Loyalty Points', 'Completed'),
(9, '2025-05-12 08:50:00', 49.90, 'Card', 'Completed'),
(1, '2025-05-15 11:30:00', 55.60, 'Card', 'Completed'),
(2, '2025-05-18 15:15:00', 31.25, 'Cash', 'Completed'),
(7, '2025-05-22 10:00:00', 18.90, 'Cash', 'Completed'),
(10, '2025-05-25 14:30:00', 42.80, 'Card', 'Completed'),
(5, '2025-05-28 09:20:00', 71.35, 'Card', 'Completed'),
(3, '2025-06-01 11:45:00', 88.45, 'Card', 'Completed'),
(8, '2025-06-05 16:00:00', 145.20, 'Card', 'Completed'),
(4, '2025-06-08 12:10:00', 26.50, 'Mobile', 'Completed'),
(6, '2025-06-10 10:35:00', 35.80, 'Card', 'Completed'),
(9, '2025-06-12 13:20:00', 58.40, 'Card', 'Completed'),
(1, '2025-06-15 09:50:00', 48.75, 'Card', 'Completed'),
(2, '2025-06-16 14:40:00', 29.60, 'Cash', 'Completed');

-- Seed sale items
INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 2, 2.49, 4.98), (1, 3, 3, 1.89, 5.67), (1, 6, 2, 8.99, 17.98), (1, 8, 2, 3.49, 6.98), (1, 10, 3, 2.99, 8.97),
(2, 12, 2, 3.99, 7.98), (2, 13, 3, 2.79, 8.37), (2, 10, 2, 2.99, 5.98),
(3, 7, 3, 12.99, 38.97), (3, 5, 2, 3.99, 7.98), (3, 4, 4, 5.49, 21.96), (3, 16, 2, 6.99, 13.98),
(4, 2, 2, 4.99, 9.98), (4, 9, 4, 2.29, 9.16), (4, 11, 3, 4.49, 13.47),
(5, 1, 3, 2.49, 7.47), (5, 17, 2, 3.29, 6.58),
(6, 6, 3, 8.99, 26.97), (6, 14, 2, 9.99, 19.98), (6, 15, 3, 3.49, 10.47),
(7, 8, 3, 3.49, 10.47), (7, 12, 2, 3.99, 7.98), (7, 10, 3, 2.99, 8.97),
(8, 7, 4, 12.99, 51.96), (8, 4, 5, 5.49, 27.45), (8, 16, 3, 6.99, 20.97),
(9, 1, 4, 2.49, 9.96), (9, 3, 3, 1.89, 5.67),
(10, 7, 5, 12.99, 64.95), (10, 5, 4, 3.99, 15.96), (10, 14, 4, 9.99, 39.96),
(11, 6, 2, 8.99, 17.98), (11, 8, 2, 3.49, 6.98), (11, 13, 3, 2.79, 8.37),
(12, 4, 3, 5.49, 16.47), (12, 6, 2, 8.99, 17.98), (12, 10, 3, 2.99, 8.97),
(13, 2, 3, 4.99, 14.97), (13, 9, 5, 2.29, 11.45), (13, 11, 3, 4.49, 13.47),
(14, 12, 3, 3.99, 11.97), (14, 15, 3, 3.49, 10.47),
(15, 7, 2, 12.99, 25.98), (15, 14, 3, 9.99, 29.97), (15, 16, 2, 6.99, 13.98),
(16, 6, 4, 8.99, 35.96), (16, 4, 6, 5.49, 32.94), (16, 5, 4, 3.99, 15.96),
(17, 1, 5, 2.49, 12.45), (17, 3, 4, 1.89, 7.56),
(18, 8, 4, 3.49, 13.96), (18, 12, 3, 3.99, 11.97), (18, 17, 3, 3.29, 9.87),
(19, 7, 6, 12.99, 77.94), (19, 4, 5, 5.49, 27.45), (19, 14, 2, 9.99, 19.98),
(20, 6, 3, 8.99, 26.97), (20, 10, 4, 2.99, 11.96), (20, 13, 4, 2.79, 11.16),
(21, 2, 4, 4.99, 19.96), (21, 9, 6, 2.29, 13.74), (21, 11, 4, 4.49, 17.96),
(22, 12, 4, 3.99, 15.96), (22, 15, 3, 3.49, 10.47),
(23, 1, 4, 2.49, 9.96), (23, 17, 2, 3.29, 6.58),
(24, 6, 2, 8.99, 17.98), (24, 8, 3, 3.49, 10.47), (24, 16, 2, 6.99, 13.98),
(25, 7, 3, 12.99, 38.97), (25, 5, 3, 3.99, 11.97), (25, 14, 2, 9.99, 19.98),
(26, 4, 5, 5.49, 27.45), (26, 6, 4, 8.99, 35.96), (26, 16, 3, 6.99, 20.97),
(27, 7, 5, 12.99, 64.95), (27, 4, 6, 5.49, 32.94), (27, 5, 5, 3.99, 19.95),
(28, 3, 5, 1.89, 9.45), (28, 12, 3, 3.99, 11.97),
(29, 8, 4, 3.49, 13.96), (29, 13, 4, 2.79, 11.16), (29, 10, 3, 2.99, 8.97),
(30, 6, 3, 8.99, 26.97), (30, 2, 3, 4.99, 14.97), (30, 11, 3, 4.49, 13.47),
(31, 7, 2, 12.99, 25.98), (31, 4, 3, 5.49, 16.47), (31, 9, 3, 2.29, 6.87),
(32, 12, 4, 3.99, 15.96), (32, 15, 3, 3.49, 10.47);
