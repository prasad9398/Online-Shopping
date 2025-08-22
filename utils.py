import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

SMTP_SERVER = "smtp.gmail.com" 
SMTP_PORT = 587
EMAIL_ADDRESS = "kolusuprasad2000@gmail.com" 
EMAIL_PASSWORD = "pibh lmdj ceux laau"  

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