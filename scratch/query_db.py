import sqlite3
import os

db_path = os.path.join("backend", "app.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM retention_interventions")
print("Retention interventions count:", cursor.fetchone()[0])
cursor.execute("SELECT * FROM retention_interventions")
print("All interventions:", cursor.fetchall())
conn.close()
