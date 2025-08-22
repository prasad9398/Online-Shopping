from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from datetime import datetime, timedelta
import uuid
import qrcode
from io import BytesIO
import base64
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your_very_strong_secret_key_here_change_this' 


DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Prasad@123', 
    'database': 'ecommerce_db'
}

BUSINESS_CONTACT = {
    'phone': '9876543210',
    'business_name': 'Prasad',
    'email': 'prasad@gmail.com' 
}

PAYMENT_CONFIG = {
    'gpay_upi': 'prasad2000-1@okaxis',  
    'phonepe_upi': 'your-business@phonepe',   
    'paytm_upi': 'your-business@paytm',       
    'business_phone': '9876543210',
    'upi_string_template': 'upi://pay?pa={upi_id}&pn={business_name}&mc=0000&tid=XXXX&tr=XXXX&tn=PaymentforOrder&am={amount}&cu=INR'
}

SMTP_SERVER = "smtp.gmail.com" 
SMTP_PORT = 587
EMAIL_ADDRESS = "kolusuprasad2000@gmail.com" 
EMAIL_PASSWORD = "pibh lmdj ceux laau"  

otp_store = {}

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256 with a salt."""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return salt + pwdhash.hex()

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verifies a provided password against the stored hash."""
    salt = stored_password[:32]
    stored_hash = stored_password[32:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return pwdhash.hex() == stored_hash

def send_email(to_email, subject, body):
    """Sends an email using SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, to_email, text)
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def generate_otp(length=6):
    """Generates a numeric OTP of specified length."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])

def init_db():
    """Initializes the database schema and sample data."""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for initialization.")
        return

    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.fetchall()

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
        )
    ''')
    cursor.fetchall()

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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

        conn = get_db_connection()
        if not conn:
             flash('Database connection failed!', 'error')
             return render_template('register.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                flash('Username or email already exists!', 'error')
                return render_template('register.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

            hashed_pw = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, hashed_pw)
            )
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Registration failed: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return render_template('register.html', BUSINESS_CONTACT=BUSINESS_CONTACT)
    return render_template('register.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'] 
        password = request.form['password']

        conn = get_db_connection()
        if not conn:
             flash('Database connection failed!', 'error')
             return render_template('login.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, username, email, password_hash FROM users WHERE username = %s OR email = %s",
                (identifier, identifier)
            )
            user = cursor.fetchone()

            if user and verify_password(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f'Welcome back, {user["username"]}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username/email or password.', 'error')
        except mysql.connector.Error as err:
            flash(f'Login failed: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return render_template('login.html', BUSINESS_CONTACT=BUSINESS_CONTACT)
    return render_template('login.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        if not conn:
             flash('Database connection failed!', 'error')
             return render_template('forgot_password.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                otp = generate_otp()
                expires_at = datetime.now() + timedelta(minutes=10)
                otp_store[email] = {'otp': otp, 'expires': expires_at}

                subject = "Password Reset OTP"
                body = f"Your OTP for password reset is: {otp}. It expires in 10 minutes."
                if send_email(email, subject, body):
                    flash('OTP sent to your email address.', 'info')
                    session['reset_email'] = email
                    return redirect(url_for('reset_password'))
                else:
                    flash('Failed to send OTP email. Please try again.', 'error')
            else:
                flash('If the email exists, an OTP has been sent.', 'info')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return render_template('forgot_password.html', BUSINESS_CONTACT=BUSINESS_CONTACT)
    return render_template('forgot_password.html', BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')
    if not email:
        flash('Invalid request. Please request a new OTP.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        otp = request.form['otp']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('reset_password.html', email=email, BUSINESS_CONTACT=BUSINESS_CONTACT)

        stored_otp_data = otp_store.get(email)
        if not stored_otp_data:
            flash('OTP expired or invalid. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))

        if datetime.now() > stored_otp_data['expires']:
            del otp_store[email]
            flash('OTP expired. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))

        if stored_otp_data['otp'] != otp:
            flash('Invalid OTP.', 'error')
            return render_template('reset_password.html', email=email, BUSINESS_CONTACT=BUSINESS_CONTACT)

        conn = get_db_connection()
        if not conn:
             flash('Database connection failed!', 'error')
             return render_template('reset_password.html', email=email, BUSINESS_CONTACT=BUSINESS_CONTACT)

        cursor = conn.cursor()
        try:
            hashed_pw = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (hashed_pw, email))
            conn.commit()
            del otp_store[email]
            session.pop('reset_email', None)
            flash('Password reset successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Error resetting password: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
        return render_template('reset_password.html', email=email, BUSINESS_CONTACT=BUSINESS_CONTACT)
    return render_template('reset_password.html', email=email, BUSINESS_CONTACT=BUSINESS_CONTACT)


@app.route('/')
def index():
    conn = get_db_connection()
    if not conn:
         flash('Database connection failed!', 'error')
         return render_template('index.html', products=[], BUSINESS_CONTACT=BUSINESS_CONTACT)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', products=products, BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    if not conn:
         flash('Database connection failed!', 'error')
         return render_template('index.html', products=[], BUSINESS_CONTACT=BUSINESS_CONTACT)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if product:
        return render_template('product.html', product=product, BUSINESS_CONTACT=BUSINESS_CONTACT)
    else:
        flash("Product not found.", "error")
        return redirect(url_for('index'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please log in to view your cart.', 'info')
        return redirect(url_for('login'))
    cart_items = session.get('cart', {})
    return render_template('cart.html', cart_items=cart_items, BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = int(request.form['product_id'])
    quantity = int(request.form.get('quantity', 1))
    conn = get_db_connection()
    if not conn:
         flash('Database connection failed!', 'error')
         return redirect(url_for('index')) 
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    if product:
        if 'cart' not in session:
            session['cart'] = {}
        cart = session['cart']
        if str(product_id) in cart:
            cart[str(product_id)]['quantity'] += quantity
        else:
            cart[str(product_id)] = {
                'id': product['id'],
                'name': product['name'],
                'price': float(product['price']),
                'quantity': quantity,
                'image': product['image']
            }
        session['cart'] = cart
        flash(f"{product['name']} added to cart!", "success")
    if 'user_id' not in session:
         flash('Please log in to proceed.', 'info')
         return redirect(url_for('login'))
    return redirect(url_for('cart'))

@app.route('/update_cart', methods=['POST'])
def update_cart():
    cart = session.get('cart', {})
    product_id = request.form['product_id']
    action = request.form['action']

    if product_id in cart:
        if action == 'increase':
            cart[product_id]['quantity'] += 1
        elif action == 'decrease':
            cart[product_id]['quantity'] -= 1
            if cart[product_id]['quantity'] <= 0:
                del cart[product_id]
                flash("Item removed from cart.", "info")
        elif action == 'remove':
            del cart[product_id]
            flash("Item removed from cart.", "info")

    session['cart'] = cart
    return jsonify({'success': True})

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash('Please log in to proceed to checkout.', 'warning')
        return redirect(url_for('login'))
    cart_items = session.get('cart', {})
    if not cart_items:
        flash("Your cart is empty.", "info")
        return redirect(url_for('index')) 
    total = sum(item['price'] * item['quantity'] for item in cart_items.values())
    return render_template('checkout.html', cart_items=cart_items, total=total, BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/process_order', methods=['POST'])
def process_order():
    if 'user_id' not in session:
        flash('Please log in to place an order.', 'warning')
        return redirect(url_for('login'))

    customer_name = request.form['name']
    customer_email = request.form['email']
    customer_phone = request.form['phone']
    customer_address = request.form['address']
    payment_method = request.form['payment_method']
    cart_items = session.get('cart', {})
    if not cart_items:
        flash("Cannot process empty order.", "error")
        return redirect(url_for('index')) 

    total = sum(item['price'] * item['quantity'] for item in cart_items.values())
    order_id = str(uuid.uuid4())
    conn = get_db_connection()
    if not conn:
         flash('Database connection failed!', 'error')
         return redirect(url_for('checkout')) 
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO orders (order_id, customer_name, customer_email, customer_phone, customer_address, total_amount, payment_method, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (order_id, customer_name, customer_email, customer_phone, customer_address, total, payment_method, 'Pending'))
        for item_id, item in cart_items.items():
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            ''', (order_id, item['id'], item['quantity'], item['price']))
        conn.commit()
        flash(f"Order {order_id[:8]} placed successfully!", "success")
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Error processing order: {err}", "error")
        return redirect(url_for('checkout')) 
    finally:
        cursor.close()
        conn.close()
    session['cart'] = {} 
    if payment_method == 'cod':
        return redirect(url_for('order_confirmation', order_id=order_id))
    elif payment_method in ['gpay', 'phonepe', 'paytm', 'upi_qr', 'phone_qr']:
        return redirect(url_for('payment_page', order_id=order_id))
    else:
        return redirect(url_for('checkout'))

@app.route('/payment/<order_id>')
def payment_page(order_id):
    conn = get_db_connection()
    if not conn:
         flash('Database connection failed!', 'error')
         return redirect(url_for('index'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM orders WHERE order_id = %s', (order_id,))
    order = cursor.fetchone()
    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))

    payment_details = {
        'gpay': PAYMENT_CONFIG['gpay_upi'],
        'phonepe': PAYMENT_CONFIG['phonepe_upi'],
        'paytm': PAYMENT_CONFIG['paytm_upi'],
        'business_phone': PAYMENT_CONFIG['business_phone'],
        'business_name': BUSINESS_CONTACT['business_name']
    }

    upi_string = None
    qr_code_img = None
    if order['payment_method'] in ['gpay', 'phonepe', 'paytm', 'upi_qr']:
        upi_id = payment_details[order['payment_method']] if order['payment_method'] in payment_details else f"{PAYMENT_CONFIG['business_phone']}@paytm"
        upi_string = PAYMENT_CONFIG['upi_string_template'].format(
            upi_id=upi_id,
            business_name=BUSINESS_CONTACT['business_name'],
            amount=order['total_amount']
        )

        if upi_string:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            qr.add_data(upi_string)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffered = BytesIO()
            img.save(buffered, format="PNG")
            qr_code_img = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return render_template('payment.html',
                         order=order,
                         upi_string=upi_string,
                         qr_code_img=qr_code_img,
                         payment_details=payment_details,
                         BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/confirm_payment/<order_id>')
def confirm_payment(order_id):
    conn = get_db_connection()
    if not conn:
         flash('Database connection failed!', 'error')
         return redirect(url_for('index'))

    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE orders SET status = %s WHERE order_id = %s
        ''', ('Completed', order_id))
        conn.commit()
        flash("Payment confirmed! Order completed.", "success")
    except mysql.connector.Error as err:
        flash(f"Error confirming payment: {err}", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('order_confirmation', order_id=order_id))

@app.route('/order_confirmation/<order_id>')
def order_confirmation(order_id):
    conn = get_db_connection()
    if not conn:
         flash('Database connection failed!', 'error')
         return redirect(url_for('index'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM orders WHERE order_id = %s', (order_id,))
    order = cursor.fetchone()
    cursor.close()
    conn.close()

    if not order:
        flash("Order not found.", "error")
        return redirect(url_for('index'))
    return render_template('confirmation.html', order=order, BUSINESS_CONTACT=BUSINESS_CONTACT)

@app.route('/images/<path:filename>')
def custom_static(filename):
    return app.send_static_file('images/' + filename)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
