import mysql.connector
from app import DB_CONFIG

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def init_db():
    """Initializes the database schema and sample data."""
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL, -- Store hashed passwords
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.fetchall()

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN user_id INT, ADD FOREIGN KEY (user_id) REFERENCES users(id)")
        cursor.fetchall()
        print("Added user_id column to orders table.")
    except mysql.connector.Error as e:
        if e.errno == 1060: 
             pass 
        else:
             print(f"Error adding user_id column: {e}")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            image VARCHAR(255),
            category VARCHAR(100)
        )
    ''')
    cursor.fetchall()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id VARCHAR(50) UNIQUE,
            customer_name VARCHAR(255),
            customer_email VARCHAR(255),
            customer_phone VARCHAR(20),
            customer_address TEXT,
            total_amount DECIMAL(10, 2),
            payment_method VARCHAR(50),
            status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            -- user_id INT, -- Uncomment if adding user_id later and modifying the ALTER TABLE above
            -- FOREIGN KEY (user_id) REFERENCES users(id) -- Uncomment if adding user_id later
        )
    ''')
    cursor.fetchall()

    # Create order_items table if it doesn't exist (your existing code)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id VARCHAR(50),
            product_id INT,
            quantity INT,
            price DECIMAL(10, 2),
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')
    cursor.fetchall()

    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    if count == 0:
        sample_products = [
            ('Smartphone X', 'Latest smartphone with advanced features', 1299.99, 'Phone.jpg', 'Electronics'),
            ('Apple Pro', 'High-performance laptop for professionals', 4599.99, 'laptop.jpg', 'Electronics'),
            ('Wireless Headphones', 'Noise-cancelling wireless headphones', 599.99, 'headphones.jpg', 'Electronics'),
            ('Watch', 'Fitness tracking smartwatch', 249.99, 'watch.jpg', 'Electronics'),
            ('Bluetooth Speaker', 'Portable waterproof speaker', 999.99, 'Speakers.jpg', 'Electronics'),
            ('Camera Kit', 'Professional photography kit', 899.99, 'camera.jpg', 'Electronics')
        ]
        cursor.executemany('''
            INSERT INTO products (name, description, price, image, category)
            VALUES (%s, %s, %s, %s, %s)
        ''', sample_products)
        conn.commit()
        print("Sample products inserted.")

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized.")