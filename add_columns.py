import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Add new columns
try:
    cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN driver_lat REAL')
    print("✓ Added driver_lat column.")
except Exception as e:
    print(f"driver_lat: {e}")

try:
    cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN driver_lng REAL')
    print("✓ Added driver_lng column.")
except Exception as e:
    print(f"driver_lng: {e}")

try:
    cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN route_distance_km REAL')
    print("✓ Added route_distance_km column.")
except Exception as e:
    print(f"route_distance_km: {e}")

try:
    cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN route_duration_minutes REAL')
    print("✓ Added route_duration_minutes column.")
except Exception as e:
    print(f"route_duration_minutes: {e}")

conn.commit()
conn.close()

print("\n✓ Database updated successfully!")
