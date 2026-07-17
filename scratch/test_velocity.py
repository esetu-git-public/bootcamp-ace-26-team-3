import sqlite3
import os

db_path = "app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT customer_id, COUNT(*) FROM customers GROUP BY customer_id HAVING COUNT(*) > 1")
print("Duplicate customers:", cursor.fetchall())

cursor.execute("SELECT customer_id, COUNT(*) FROM churn_predictions GROUP BY customer_id HAVING COUNT(*) > 1")
print("Duplicate churn predictions:", cursor.fetchall())

conn.close()
