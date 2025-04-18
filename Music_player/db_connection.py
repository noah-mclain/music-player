import mysql.connector
from mysql.connector import pooling

# Connect to the database
try:
    pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name='mypool',
        pool_size=5,
        host='localhost',
        user='root',
        password='Namo!CS3003',
        database='music_player_db'
    )
    print("Database connection pool created successfully")
except mysql.connector.Error as e:
    print(f"Error creating connection pool: {e}")

class DBConnection:
    def __enter__(self):
        try:
            self.conn = pool.get_connection()
            print("Got connection from pool")
            return self.conn
        except mysql.connector.Error as e:
            print(f"Error getting connection from pool: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'conn'):
            self.conn.close()
            print("Connection returned to pool")

# Usage in the data operations file
def get_db_connection():
    return DBConnection()

# Test the connection
def test_connection():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                print("Tables in the database:")
                print("\n".join(table[0] for table in tables))
    except mysql.connector.Error as e:
        print(f"Error testing connection: {e}")

# Call this function when your application starts
test_connection()
