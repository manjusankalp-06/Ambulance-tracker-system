import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ambulance_requests'")
if not cursor.fetchone():
    print("Table doesn't exist. Creating it...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ambulance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            patient_name TEXT,
            contact TEXT,
            pickup_location TEXT,
            destination TEXT,
            ambulance_type TEXT,
            origin_lat REAL NOT NULL,
            origin_lng REAL NOT NULL,
            destination_lat REAL,
            destination_lng REAL,
            status TEXT DEFAULT 'Pending',
            estimated_arrival_time TEXT,
            estimated_completion_time TEXT,
            pickup_lat REAL,
            pickup_lng REAL,
            request_time TEXT,
            estimated_time_minutes INTEGER,
            driver_lat REAL,
            driver_lng REAL,
            route_distance_km REAL,
            route_duration_minutes REAL
        )
    ''')
    print("✓ Table created successfully!")
else:
    print("✓ Table exists")

conn.commit()
conn.close()
print("✓ Database fixed!")
