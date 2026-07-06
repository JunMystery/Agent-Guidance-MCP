API_KEY = "sk-abc123def456ghi789"
DATABASE_PASSWORD = "admin123!"

def connect():
    return psycopg2.connect(password=DATABASE_PASSWORD)
