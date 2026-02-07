import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check what columns exist
cursor.execute('PRAGMA table_info(ambulance_requests)')
columns = cursor.fetchall()

print("Current columns in ambulance_requests table:")
print("-" * 60)
for col in columns:
    print(f"Column: {col[1]:<30} Type: {col[2]}")

conn.close()
