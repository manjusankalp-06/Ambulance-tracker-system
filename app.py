import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
import math
from math import radians, sin, cos, sqrt, atan2
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import requests
import threading
import time
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from functools import wraps
import random
from flask import send_from_directory

app = Flask(__name__)
CORS(app)
load_dotenv()

app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-change-in-production')
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY')
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')
socketio = SocketIO(app)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
UPLOAD_FOLDER = 'uploads'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database initialization
def init_db():
    if not os.path.exists('users.db'):
        print("Database not found. Creating tables...")
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Ambulance Requests Table
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
                route_duration_minutes REAL,
                traffic_delay_minutes REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Ambulance Locations Table (for tracking history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ambulance_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ambulance_id INTEGER,
                latitude REAL,
                longitude REAL,
                timestamp TEXT,
                status TEXT,
                last_updated TEXT,
                FOREIGN KEY (ambulance_id) REFERENCES ambulance_requests(id)
            )
        ''')
        
        # Admins Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # NEW: Drivers Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                current_lat REAL,
                current_lng REAL,
                status TEXT DEFAULT 'Available',
                last_login TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON ambulance_requests(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_driver_phone ON drivers(phone)')
        
        conn.commit()
        conn.close()
        print("Tables created successfully.")
        
    else:
        print("Database already exists.")
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Check if drivers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drivers'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    current_lat REAL,
                    current_lng REAL,
                    status TEXT DEFAULT 'Available',
                    last_login TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_driver_phone ON drivers(phone)')
            print("Created drivers table.")
        
        # Check and update ambulance_requests table columns
        cursor.execute('PRAGMA table_info(ambulance_requests)')
        columns = [column[1] for column in cursor.fetchall()]
        
        # EXISTING COLUMNS
        if 'pickup_lat' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN pickup_lat REAL')
            print("Added pickup_lat column.")
        if 'pickup_lng' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN pickup_lng REAL')
            print("Added pickup_lng column.")
        if 'request_time' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN request_time TEXT')
            print("Added request_time column.")
        if 'estimated_time_minutes' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN estimated_time_minutes INTEGER')
            print("Added estimated_time_minutes column.")
        if 'status' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN status TEXT')
            print("Added status column.")
        
        # NEW COLUMNS FOR DRIVER LOCATION AND ROUTE
        if 'driver_lat' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN driver_lat REAL')
            print("Added driver_lat column.")
        if 'driver_lng' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN driver_lng REAL')
            print("Added driver_lng column.")
        if 'route_distance_km' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN route_distance_km REAL')
            print("Added route_distance_km column.")
        if 'route_duration_minutes' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN route_duration_minutes REAL')
            print("Added route_duration_minutes column.")
        
        #  NEW COLUMN FOR TRAFFIC DELAY
        if 'traffic_delay_minutes' not in columns:
            cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN traffic_delay_minutes REAL')
            print("Added traffic_delay_minutes column.")
        
        conn.commit()
        conn.close()
        print("Database schema updated successfully.")


# Initialize database on startup
init_db()



def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(s):
    return datetime.fromisoformat(s)

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)

# GEOCODING AND DISTANCE FUNCTIONS

def reverse_geocode_for_address(address):
    """Convert address to coordinates using OpenCage"""
    if not OPENCAGE_API_KEY:
        raise ValueError("OPENCAGE_API_KEY is not set in environment variables.")
    
    url = f"https://api.opencagedata.com/geocode/v1/json?q={address}&key={OPENCAGE_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            lat = data['results'][0]['geometry']['lat']
            lng = data['results'][0]['geometry']['lng']
            return lat, lng
        else:
            return None, None
    else:
        print(f"Error: {response.status_code}")
        return None, None

def get_coordinates(location):
    """Get coordinates from address using OpenCage"""
    if not OPENCAGE_API_KEY:
        return None, None
    
    url = f"https://api.opencagedata.com/geocode/v1/json?q={location}&key={OPENCAGE_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            lat = data['results'][0]['geometry']['lat']
            lng = data['results'][0]['geometry']['lng']
            return lat, lng
    return None, None

def reverse_geocode(lat, lng):
    """Convert coordinates to address using OpenCage"""
    if not OPENCAGE_API_KEY:
        return "Unknown Location"
    
    url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lng}&key={OPENCAGE_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            address = data['results'][0]['formatted']
            return address
    return "Unknown Location"

# Haversine formula for distance calculation
def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth radius in kilometers
    
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance

# TRAFFIC-AWARE ROUTING FUNCTIONS

def get_route_via_tomtom(start_lat, start_lng, end_lat, end_lng):
    """
    Get traffic-aware route from TomTom Routing API (FREE - 2,500 requests/day)
    Returns: route coordinates, distance, duration considering LIVE TRAFFIC
    """
    if not TOMTOM_API_KEY:
        print("TomTom API key not found, falling back to OSRM")
        return get_route_via_osrm(start_lat, start_lng, end_lat, end_lng)
    
    try:
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_lat},{start_lng}:{end_lat},{end_lng}/json"
        params = {
            'key': TOMTOM_API_KEY,
            'traffic': 'true',  # Include live traffic
            'travelMode': 'car',
            'routeType': 'fastest',  # Fastest route considering traffic
            'departAt': 'now'  # Current time for traffic data
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'routes' in data and len(data['routes']) > 0:
                route = data['routes'][0]
                summary = route['summary']
                
                # Extract coordinates
                coordinates = []
                for leg in route['legs']:
                    for point in leg['points']:
                        coordinates.append([point['latitude'], point['longitude']])
                
                # Get distance and duration (with traffic)
                distance_km = summary['lengthInMeters'] / 1000
                duration_minutes = summary['travelTimeInSeconds'] / 60
                traffic_delay_seconds = summary.get('trafficDelayInSeconds', 0)
                
                print(f"TomTom route calculated: {distance_km:.2f} km, {duration_minutes:.2f} min (traffic delay: {traffic_delay_seconds/60:.1f} min)")
                
                return {
                    'coordinates': coordinates,
                    'distance_km': round(distance_km, 2),
                    'duration_minutes': round(duration_minutes, 2),
                    'traffic_delay_minutes': round(traffic_delay_seconds / 60, 2),
                    'traffic_aware': True,
                    'success': True
                }
        
        print(f"TomTom API error: {response.status_code}, falling back to OSRM")
        return get_route_via_osrm(start_lat, start_lng, end_lat, end_lng)
    
    except Exception as e:
        print(f"TomTom Error: {e}, falling back to OSRM")
        return get_route_via_osrm(start_lat, start_lng, end_lat, end_lng)

def get_route_via_osrm(start_lat, start_lng, end_lat, end_lng):
    """
    Fallback: Get route from OSRM (no traffic, but free)
    Returns: list of coordinates along the road, actual distance, duration
    """
    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 'Ok' and len(data['routes']) > 0:
                route = data['routes'][0]
                
                # Get coordinates from GeoJSON
                coordinates = [[coord[1], coord[0]] for coord in route['geometry']['coordinates']]
                
                # Distance in meters to km, duration in seconds to minutes
                distance_km = route['distance'] / 1000
                duration_minutes = route['duration'] / 60
                
                print(f"OSRM fallback route: {distance_km:.2f} km, {duration_minutes:.2f} min (no traffic data)")
                
                return {
                    'coordinates': coordinates,
                    'distance_km': round(distance_km, 2),
                    'duration_minutes': round(duration_minutes, 2),
                    'traffic_aware': False,
                    'success': True
                }
        return {'success': False, 'error': 'Unable to get route'}
    except Exception as e:
        print(f"OSRM Error: {e}")
        return {'success': False, 'error': str(e)}


def calculate_route_info(driver_lat, driver_lng, patient_lat, patient_lng, hospital_lat, hospital_lng):
    """
    Calculate optimal route with LIVE TRAFFIC: Driver (A) â†’ Patient (B) â†’ Hospital (H)
    Uses TomTom (free, traffic-aware) with OSRM fallback
    """
    try:
        print(f"\nCalculating route: Driver({driver_lat}, {driver_lng}) â†’ Patient({patient_lat}, {patient_lng}) â†’ Hospital({hospital_lat}, {hospital_lng})")
        
        # Try TomTom first (with live traffic), fallback to OSRM if unavailable
        segment1 = get_route_via_tomtom(driver_lat, driver_lng, patient_lat, patient_lng)
        segment2 = get_route_via_tomtom(patient_lat, patient_lng, hospital_lat, hospital_lng)
        
        if segment1['success'] and segment2['success']:
            total_distance = segment1['distance_km'] + segment2['distance_km']
            total_duration = segment1['duration_minutes'] + segment2['duration_minutes']
            total_traffic_delay = segment1.get('traffic_delay_minutes', 0) + segment2.get('traffic_delay_minutes', 0)
            
            print(f"Total route: {total_distance:.2f} km, {total_duration:.2f} min (traffic delay: {total_traffic_delay:.1f} min)")
            
            route_info = {
                'total_distance_km': round(total_distance, 2),
                'total_duration_minutes': round(total_duration, 2),
                'traffic_delay_minutes': round(total_traffic_delay, 2),
                'traffic_aware': segment1.get('traffic_aware', False) and segment2.get('traffic_aware', False),
                'route_coordinates': segment1['coordinates'] + segment2['coordinates'],
                'segment_1': {
                    'from': 'Driver',
                    'to': 'Patient',
                    'distance_km': segment1['distance_km'],
                    'duration_minutes': segment1['duration_minutes'],
                    'coordinates': segment1['coordinates']
                },
                'segment_2': {
                    'from': 'Patient',
                    'to': 'Hospital',
                    'distance_km': segment2['distance_km'],
                    'duration_minutes': segment2['duration_minutes'],
                    'coordinates': segment2['coordinates']
                }
            }
            return route_info
        else:
            # Fallback to haversine if both APIs fail
            print("Both routing APIs failed, using Haversine fallback")
            distance_to_patient = haversine(driver_lat, driver_lng, patient_lat, patient_lng)
            distance_to_hospital = haversine(patient_lat, patient_lng, hospital_lat, hospital_lng)
            total_distance = distance_to_patient + distance_to_hospital
            
            avg_speed_kmh = 40
            total_duration_minutes = (total_distance / avg_speed_kmh) * 60
            
            return {
                'total_distance_km': round(total_distance, 2),
                'total_duration_minutes': round(total_duration_minutes, 2),
                'traffic_delay_minutes': 0,
                'traffic_aware': False,
                'route_coordinates': [],
                'segment_1': {
                    'from': 'Driver',
                    'to': 'Patient',
                    'distance_km': round(distance_to_patient, 2),
                    'duration_minutes': round((distance_to_patient / avg_speed_kmh) * 60, 2)
                },
                'segment_2': {
                    'from': 'Patient',
                    'to': 'Hospital',
                    'distance_km': round(distance_to_hospital, 2),
                    'duration_minutes': round((distance_to_hospital / avg_speed_kmh) * 60, 2)
                }
            }
    except Exception as e:
        print(f"Route calculation error: {e}")
        distance_to_patient = haversine(driver_lat, driver_lng, patient_lat, patient_lng)
        distance_to_hospital = haversine(patient_lat, patient_lng, hospital_lat, hospital_lng)
        total_distance = distance_to_patient + distance_to_hospital
        
        avg_speed_kmh = 40
        total_duration_minutes = (total_distance / avg_speed_kmh) * 60
        
        return {
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': round(total_duration_minutes, 2),
            'traffic_delay_minutes': 0,
            'traffic_aware': False
        }

def calculate_speed(lat1, lon1, lat2, lon2, time1, time2):
    """Calculate speed between two points"""
    distance_km = haversine(lat1, lon1, lat2, lon2)
    time_diff = (time2 - time1).total_seconds() / 3600  # hours
    
    if time_diff > 0:
        speed_kmh = distance_km / time_diff
        return speed_kmh
    return 0

# DATABASE HELPER FUNCTIONS

def insert_ambulance_request(user_id, patient_name, contact, pickup_location, destination, ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng):
    if destination_lat is None or destination_lng is None:
        flash('Destination coordinates are missing.', 'danger')
        return None
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ambulance_requests 
        (user_id, patient_name, contact, pickup_location, destination, ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, patient_name, contact, pickup_location, destination, ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng))
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    return request_id

# MAIN ROUTES

@app.route('/')
def index():
    return render_template('index.html', title='Home')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        contact = request.form.get('contact')
        destination = request.form.get('destination')
        ambulance_type = request.form.get('ambulance_type', 'Basic')

        # Map pin coordinates (may be blank if not selected)
        pickup_lat = request.form.get('pickup_lat')
        pickup_lng = request.form.get('pickup_lng')
        # Manual text address (optional)
        pickup_location = request.form.get('location')

        # Logic: Prefer map pin, else use geocoding on text address
        if pickup_lat and pickup_lng:
            origin_lat = float(pickup_lat)
            origin_lng = float(pickup_lng)
        else:
            # If no pin, attempt to geocode manual address
            if not pickup_location:
                flash('Please provide a pickup location or select on map.', 'danger')
                return render_template('booking.html', title='Book Ambulance')
            origin_lat, origin_lng = get_coordinates(pickup_location)

        # Get destination coordinates from text
        destination_lat, destination_lng = get_coordinates(destination)

        if origin_lat and destination_lat:
            request_id = insert_ambulance_request(
                None, patient_name, contact, pickup_location, destination,
                ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng
            )

            if request_id:
                flash('Ambulance booking request submitted successfully!', 'success')
                return redirect(url_for('tracking_detail', request_id=request_id))
        else:
            flash('Unable to geocode addresses. Please check the locations or try again.', 'danger')
        
    return render_template('booking.html', title='Book Ambulance')

@app.route('/tracking', methods=['GET', 'POST'])
def tracking_search():
    if request.method == 'POST':
        request_id = request.form.get('request_id')
        if request_id:
            return redirect(url_for('tracking_detail', request_id=request_id))
    return render_template('tracking_search.html', title='Track Ambulance')

@app.route('/tracking/<int:request_id>')
def tracking_detail(request_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ambulance_requests WHERE id = ?', (request_id,))
    request_data = cursor.fetchone()
    conn.close()
    
    if request_data:
        return render_template('tracking_result.html', request=request_data, title='Track Ambulance')
    else:
        flash('Request not found.', 'danger')
        return redirect(url_for('tracking_search'))

# ADMIN ROUTES

@app.route('/admin', methods=['GET'])
def admin_login():
    return render_template('admin_login.html', title='Admin Login')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'admin' and password == '1234':
        session['logged_in'] = True
        session['is_main_admin'] = True
        return redirect(url_for('admin_dashboard'))
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
    admin = cursor.fetchone()
    conn.close()
    
    if admin and check_password_hash(admin[2], password):
        session['logged_in'] = True
        session['is_main_admin'] = False
        return redirect(url_for('admin_dashboard'))
    
    flash('Invalid credentials', 'danger')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Get all requests with driver information using LEFT JOIN
    cursor.execute('''
        SELECT 
            ar.*,
            d.id as driver_id,
            d.name as driver_name,
            d.phone as driver_phone,
            d.current_lat as driver_lat,
            d.current_lng as driver_lng,
            d.status as driver_status
        FROM ambulance_requests ar
        LEFT JOIN drivers d ON ar.user_id = d.id
        ORDER BY ar.id DESC
    ''')
    all_requests = cursor.fetchall()
    conn.close()
    
    #  DEBUG: Print to verify column index
    if all_requests:
        print("=" * 60)
        print("DEBUG: Admin Dashboard Column Info")
        print("=" * 60)
        print(f"Total columns: {len(all_requests[0])}")
        print(f"Sample request ID: {all_requests[0][0]}")
        
        # Print all column values for first request
        for idx, val in enumerate(all_requests[0]):
            print(f"  Index [{idx}]: {val}")
        
        # Check traffic delay column
        if len(all_requests[0]) > 22:
            print(f"\n Traffic delay (index 22): {all_requests[0][22]}")
        else:
            print(f"\n Traffic delay column not found! Only {len(all_requests[0])} columns")
        print("=" * 60)
    
    # Helper function to normalize status values
    def norm(val):
        if not val:
            return "unknown"
        v = str(val).lower().strip().replace("_", " ").replace("-", " ").replace(".", "")
        v = v.strip()
        if v in ["pending", "queue", "waiting", "unknown", ""]:
            return "new"
        if v == "new":
            return "new"
        if v in ["started", "in progress", "on the way", "en route"]:
            return "started"
        if v in ["patient received", "received"]:
            return "patient received"
        if v in ["patient reached", "reached", "completed", "done"]:
            return "patient reached"
        return v
    
    # Filter requests by status (using original column index)
    new_requests = [r for r in all_requests if norm(r[11]) == 'new']
    on_the_way = [r for r in all_requests if norm(r[11]) == 'started']
    patient_received = [r for r in all_requests if norm(r[11]) == 'patient received']
    patient_reached = [r for r in all_requests if norm(r[11]) == 'patient reached']
    
    return render_template(
        'admin_dashboard.html',
        all_requests=all_requests,
        new_requests=new_requests,
        on_the_way=on_the_way,
        patient_received=patient_received,
        patient_reached=patient_reached,
        requests=all_requests,
        title='Admin Dashboard'
    )


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/update_status/<int:req_id>', methods=['POST'])
def update_status(req_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    new_status = request.form.get('status')
    new_status = new_status.strip()
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE ambulance_requests SET status = ? WHERE id = ?', (new_status, req_id))
    conn.commit()
    conn.close()
    flash(f'Status updated to {new_status} for request {req_id}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/update_driver_location/<int:req_id>', methods=['POST'])
def update_driver_location(req_id):
    """Update driver location and calculate TRAFFIC-AWARE route"""
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    driver_lat = request.form.get('driver_lat')
    driver_lng = request.form.get('driver_lng')
    
    if not driver_lat or not driver_lng:
        flash('Please provide driver location', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        driver_lat = float(driver_lat)
        driver_lng = float(driver_lng)
    except ValueError:
        flash('Invalid coordinates', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Get patient and hospital locations
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT origin_lat, origin_lng, destination_lat, destination_lng 
        FROM ambulance_requests WHERE id = ?
    ''', (req_id,))
    result = cursor.fetchone()
    
    if result:
        patient_lat, patient_lng, hospital_lat, hospital_lng = result
        
        # Calculate route info with LIVE TRAFFIC
        route_info = calculate_route_info(
            driver_lat, driver_lng,
            patient_lat, patient_lng,
            hospital_lat, hospital_lng
        )
        
        # Update database
        cursor.execute('''
            UPDATE ambulance_requests 
            SET driver_lat = ?, driver_lng = ?, 
                route_distance_km = ?, route_duration_minutes = ?
            WHERE id = ?
        ''', (driver_lat, driver_lng, 
              route_info['total_distance_km'], 
              route_info['total_duration_minutes'], 
              req_id))
        
        conn.commit()
        conn.close()
        
        traffic_info = f" (Traffic delay: {route_info.get('traffic_delay_minutes', 0):.1f} min)" if route_info.get('traffic_aware') else ""
        flash(f' Driver location updated! Total route: {route_info["total_distance_km"]} km, ETA: {route_info["total_duration_minutes"]:.0f} minutes{traffic_info}', 'success')
    else:
        conn.close()
        flash('Request not found', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/view_route/<int:request_id>')
def view_route(request_id):
    """Display interactive map with driver, patient, and hospital locations"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ambulance_requests WHERE id = ?', (request_id,))
    request_data = cursor.fetchone()
    conn.close()
    
    if request_data:
        # Convert tuple to list to allow modifications
        request_data = list(request_data)
        
        # Define which indices should be numeric (coordinates, distance, duration)
        numeric_indices = [7, 8, 9, 10, 13, 14, 16, 17, 18, 19, 20]
        
        # Replace None values appropriately
        for i in range(len(request_data)):
            if request_data[i] is None:
                if i in numeric_indices:
                    request_data[i] = 0.0  # Numeric fields get 0.0
                else:
                    request_data[i] = 'N/A'  # Text fields get 'N/A'
        
        return render_template('route_map.html', request=request_data, title='Route Map')
    else:
        flash('Request not found.', 'danger')
        return redirect(url_for('admin_dashboard'))



# UTILITY ROUTES

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html', title='Privacy Policy')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('terms_of_service.html', title='Terms of Service')

@app.route('/contact-admin')
def contact_admin():
    return render_template('contact_admin.html')

# API ROUTES

@app.route('/api/ambulance_location/<int:ambulance_id>')
def get_ambulance_location(ambulance_id):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT al.latitude, al.longitude, al.status, ar.patient_name, 
                   ar.pickup_lat, ar.pickup_lng, ar.destination_lat, ar.destination_lng,
                   ar.driver_lat, ar.driver_lng
            FROM ambulance_locations al
            JOIN ambulance_requests ar ON al.ambulance_id = ar.id
            WHERE al.ambulance_id = ?
            ORDER BY al.timestamp DESC LIMIT 1
        ''', (ambulance_id,))
        data = cursor.fetchone()
        conn.close()
        
        if data:
            latitude, longitude, status, patient_name, pickup_lat, pickup_lng, destination_lat, destination_lng, driver_lat, driver_lng = data
            return jsonify({
                'latitude': latitude,
                'longitude': longitude,
                'status': status,
                'patient_name': patient_name,
                'pickup_lat': pickup_lat,
                'pickup_lng': pickup_lng,
                'destination_lat': destination_lat,
                'destination_lng': destination_lng,
                'driver_lat': driver_lat,
                'driver_lng': driver_lng
            })
        else:
            return jsonify({'error': 'No location data available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/download_pdf/<int:req_id>')
def download_pdf(req_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ambulance_requests WHERE id = ?', (req_id,))
    request_data = cursor.fetchone()
    conn.close()
    
    if not request_data:
        flash('Request not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=30,
        alignment=1
    )
    title = Paragraph("Ambulance Request Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Request details
    data = [
        ['Request ID:', str(request_data[0])],
        ['Patient Name:', request_data[2]],
        ['Contact:', request_data[3]],
        ['Pickup Location:', request_data[4]],
        ['Destination:', request_data[5]],
        ['Ambulance Type:', request_data[6]],
        ['Status:', request_data[11]],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment;filename=ambulance_request_{req_id}.pdf'}
    )

# SOCKETIO EVENTS

@socketio.on('update_location')
def handle_location_update(data):
    ambulance_id = data.get('ambulance_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE ambulance_locations 
        SET latitude = ?, longitude = ?, last_updated = ? 
        WHERE ambulance_id = ?
    ''', (latitude, longitude, datetime.now(), ambulance_id))
    conn.commit()
    
    # Calculate distance and ETA
    cursor.execute('SELECT destination_lat, destination_lng FROM ambulance_requests WHERE id = ?', (ambulance_id,))
    destination = cursor.fetchone()
    
    if destination:
        dest_lat, dest_lng = destination
        distance_km = haversine(latitude, longitude, dest_lat, dest_lng)
        
        if distance_km < 0.2:  # Within 200 meters
            cursor.execute('UPDATE ambulance_requests SET status = ? WHERE id = ?', ('Patient Reached', ambulance_id))
            conn.commit()
            emit('status_update', {'ambulance_id': ambulance_id, 'status': 'Patient Reached'}, broadcast=True)
        
        # Calculate ETA (assuming average speed of 60 km/h)
        speed_kmh = 60
        eta_minutes = (distance_km / speed_kmh) * 60
        
        emit('location_update', {
            'ambulance_id': ambulance_id,
            'latitude': latitude,
            'longitude': longitude,
            'distance_km': round(distance_km, 2),
            'eta_minutes': round(eta_minutes, 2)
        }, broadcast=True)
    
    conn.close()

@app.route('/admin/simulate_movement/<int:ambulance_id>')
def simulate_movement(ambulance_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get current request details
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT origin_lat, origin_lng, destination_lat, destination_lng FROM ambulance_requests WHERE id = ?', (ambulance_id,))
    request_data = cursor.fetchone()
    
    if request_data:
        start_lat, start_lng, end_lat, end_lng = request_data
        
        # Simulate 10 points between start and destination
        for i in range(10):
            progress = i / 10
            sim_lat = start_lat + (end_lat - start_lat) * progress + random.uniform(-0.001, 0.001)
            sim_lng = start_lng + (end_lng - start_lng) * progress + random.uniform(-0.001, 0.001)
            
            cursor.execute('''
                INSERT INTO ambulance_locations (ambulance_id, latitude, longitude, timestamp, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (ambulance_id, sim_lat, sim_lng, datetime.now().isoformat(), 'En Route'))
            
            conn.commit()
            time.sleep(2)  # Wait 2 seconds between updates
        
        conn.close()
        flash('Movement simulation completed!', 'success')
    
    return redirect(url_for('admin_dashboard'))


# ============================================
# DRIVER ROUTES (COMPLETE SECTION)
# ============================================

@app.route('/driver/login', methods=['GET', 'POST'])
def driver_login():
    """Driver login with location pinning"""
    if request.method == 'POST':
        driver_name = request.form.get('driver_name')
        driver_phone = request.form.get('driver_phone')
        driver_lat = request.form.get('driver_lat')
        driver_lng = request.form.get('driver_lng')
        
        if driver_name and driver_phone and driver_lat and driver_lng:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            
            # Check if driver exists by phone
            cursor.execute('SELECT id FROM drivers WHERE phone = ?', (driver_phone,))
            existing_driver = cursor.fetchone()
            
            if existing_driver:
                # Update existing driver location and login time
                driver_id = existing_driver[0]
                cursor.execute('''
                    UPDATE drivers 
                    SET name = ?, current_lat = ?, current_lng = ?, 
                        last_login = ?, status = 'Available'
                    WHERE id = ?
                ''', (driver_name, float(driver_lat), float(driver_lng), 
                      datetime.now().isoformat(), driver_id))
            else:
                # Create new driver record
                cursor.execute('''
                    INSERT INTO drivers (name, phone, current_lat, current_lng, last_login, status)
                    VALUES (?, ?, ?, ?, ?, 'Available')
                ''', (driver_name, driver_phone, float(driver_lat), float(driver_lng), 
                      datetime.now().isoformat()))
                driver_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            # Store in session
            session['driver_logged_in'] = True
            session['driver_id'] = driver_id
            session['driver_name'] = driver_name
            session['driver_phone'] = driver_phone
            session['driver_lat'] = float(driver_lat)
            session['driver_lng'] = float(driver_lng)
            
            flash(f'Welcome {driver_name}! Your location has been registered.', 'success')
            return redirect(url_for('driver_dashboard'))
        else:
            flash('Please fill all fields and pin your location', 'danger')
    
    return render_template('driver_login.html', title='Driver Login')


@app.route('/driver/dashboard')
def driver_dashboard():
    """Show all pending/assigned requests for driver - SORTED BY DISTANCE"""
    if not session.get('driver_logged_in'):
        return redirect(url_for('driver_login'))
    
    driver_lat = session.get('driver_lat')
    driver_lng = session.get('driver_lng')
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Get all requests that need drivers
    cursor.execute('''
        SELECT * FROM ambulance_requests 
        WHERE status IN ('Pending', 'Started', 'Patient Received')
        ORDER BY id DESC
    ''')
    available_requests = cursor.fetchall()
    conn.close()
    
    # Calculate distance and sort by nearest
    if driver_lat and driver_lng:
        requests_with_distance = []
        for req in available_requests:
            patient_lat = req[7]  # origin_lat (pickup location)
            patient_lng = req[8]  # origin_lng
            
            if patient_lat and patient_lng:
                # Calculate distance using Haversine
                distance_km = haversine(driver_lat, driver_lng, patient_lat, patient_lng)
                requests_with_distance.append((req, distance_km))
            else:
                requests_with_distance.append((req, 999))  # Unknown distance goes to end
        
        # Sort by distance (nearest first)
        requests_with_distance.sort(key=lambda x: x[1])
        
        # Extract just the request data
        available_requests = [req[0] for req in requests_with_distance]
        distances = [req[1] for req in requests_with_distance]
    else:
        distances = [None] * len(available_requests)
    
    return render_template('driver_dashboard.html', 
                         requests=available_requests,
                         distances=distances,
                         driver_name=session.get('driver_name'),
                         title='Driver Dashboard')

@app.route('/api/driver/initial-location/<int:driver_id>')
def api_get_driver_initial_location(driver_id):
    """Get driver's pinned location (not GPS-tracked location)"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT current_lat, current_lng FROM drivers WHERE id = ?', (driver_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'lat': result[0],
                'lng': result[1],
                'source': 'pinned'  # Indicates this is the pinned location
            })
        else:
            return jsonify({'error': 'Driver not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/driver/accept/<int:request_id>')
def driver_accept_request(request_id):
    if not session.get('driver_logged_in'):
        return redirect(url_for('driver_login'))
    
    driver_id = session.get('driver_id')
    driver_lat = session.get('driver_lat')
    driver_lng = session.get('driver_lng')
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT origin_lat, origin_lng, destination_lat, destination_lng FROM ambulance_requests WHERE id = ?', (request_id,))
    result = cursor.fetchone()
    
    if result:
        patient_lat, patient_lng, hospital_lat, hospital_lng = result
        
        # Calculate route with TRAFFIC
        route_info = calculate_route_info(driver_lat, driver_lng, patient_lat, patient_lng, hospital_lat, hospital_lng)
        
        #  SAVE TRAFFIC DELAY TO DATABASE
        traffic_delay = route_info.get('traffic_delay_minutes', 0)
        
        cursor.execute('''
            UPDATE ambulance_requests 
            SET driver_lat = ?, driver_lng = ?, 
                route_distance_km = ?, route_duration_minutes = ?,
                status = 'Started', user_id = ?
            WHERE id = ?
        ''', (
            driver_lat, driver_lng,
            route_info.get('total_distance_km', 0),
            route_info.get('total_duration_minutes', 0),
            driver_id, request_id
        ))
        
        conn.commit()
        conn.close()
        
        # Flash message with traffic info
        if traffic_delay > 0:
            flash(f'Request accepted! ETA: {route_info["total_duration_minutes"]:.0f} min (âš ï¸ +{traffic_delay:.0f} min traffic delay)', 'warning')
        else:
            flash(f'Request accepted! ETA: {route_info["total_duration_minutes"]:.0f} min (âœ… Clear traffic)', 'success')
        
        return redirect(url_for('driver_navigate', request_id=request_id))


@app.route('/driver/navigate/<int:request_id>')
def driver_navigate(request_id):
    """Live navigation screen with GPS tracking"""
    if not session.get('driver_logged_in'):
        return redirect(url_for('driver_login'))
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ambulance_requests WHERE id = ?', (request_id,))
    request_data = cursor.fetchone()
    conn.close()
    
    if request_data:
        return render_template('driver_navigate.html', 
                             request=request_data,
                             driver_name=session.get('driver_name'),
                             TOMTOM_API_KEY=os.getenv('TOMTOM_API_KEY', '854266e4c8144bf8bab86fac628900e4'),  # Add TomTom key
                             title='Navigate')
    else:
        flash('Request not found', 'danger')
        return redirect(url_for('driver_dashboard'))


@app.route('/driver/update_status/<int:request_id>/<status>')
def driver_update_status(request_id, status):
    """Driver updates trip status (Picked Up / Completed)"""
    if not session.get('driver_logged_in'):
        return jsonify({'error': 'Not logged in'}), 401
    
    # Decode status (handle spaces)
    status = status.replace('%20', ' ')
    
    valid_statuses = ['Patient Received', 'Patient Reached']
    if status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE ambulance_requests SET status = ? WHERE id = ?", (status, request_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'status': status})


@app.route('/driver/logout')
def driver_logout():
    """Driver logout - clear session"""
    session.pop('driver_logged_in', None)
    session.pop('driver_name', None)
    session.pop('driver_phone', None)
    session.pop('driver_lat', None)
    session.pop('driver_lng', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('driver_login'))


# API for real-time location updates from driver
@app.route('/api/driver/location/<int:request_id>', methods=['POST'])
def api_update_driver_location(request_id):
    """Receive live GPS location from driver's phone"""
    data = request.get_json()
    driver_lat = data.get('lat')
    driver_lng = data.get('lng')
    
    if not driver_lat or not driver_lng:
        return jsonify({'error': 'Missing coordinates'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Get patient and hospital locations
        cursor.execute('''
            SELECT origin_lat, origin_lng, destination_lat, destination_lng, status
            FROM ambulance_requests WHERE id = ?
        ''', (request_id,))
        result = cursor.fetchone()
        
        if result:
            patient_lat, patient_lng, hospital_lat, hospital_lng, status = result
            
            # Calculate route based on current phase
            if status == 'Started':
                # Phase 1: Driver â†’ Patient
                route_info = calculate_route_info(
                    driver_lat, driver_lng,
                    patient_lat, patient_lng,
                    hospital_lat, hospital_lng
                )
                eta_to_patient = route_info['segment_1']['duration_minutes']
                
                # Auto-update status if very close to patient (within 100m)
                distance_to_patient = haversine(driver_lat, driver_lng, patient_lat, patient_lng)
                if distance_to_patient < 0.1:  # 100 meters
                    cursor.execute("UPDATE ambulance_requests SET status = 'Patient Received' WHERE id = ?", (request_id,))
                
                response_data = {
                    'phase': 'to_patient',
                    'eta_minutes': round(eta_to_patient, 1),
                    'distance_km': route_info['segment_1']['distance_km'],
                    'traffic_delay': route_info.get('traffic_delay_minutes', 0)
                }
            
            elif status == 'Patient Received':
                # Phase 2: Patient location â†’ Hospital
                route_info = calculate_route_info(
                    driver_lat, driver_lng,
                    patient_lat, patient_lng,
                    hospital_lat, hospital_lng
                )
                eta_to_hospital = route_info['segment_2']['duration_minutes']
                
                # Auto-complete if very close to hospital (within 100m)
                distance_to_hospital = haversine(driver_lat, driver_lng, hospital_lat, hospital_lng)
                if distance_to_hospital < 0.1:
                    cursor.execute("UPDATE ambulance_requests SET status = 'Patient Reached' WHERE id = ?", (request_id,))
                
                response_data = {
                    'phase': 'to_hospital',
                    'eta_minutes': round(eta_to_hospital, 1),
                    'distance_km': route_info['segment_2']['distance_km'],
                    'traffic_delay': route_info.get('traffic_delay_minutes', 0)
                }
            else:
                response_data = {'phase': 'completed'}
            
            # Update driver location in database
            cursor.execute('''
                UPDATE ambulance_requests
                SET driver_lat = ?, driver_lng = ?,
                    route_distance_km = ?, route_duration_minutes = ?
                WHERE id = ?
            ''', (driver_lat, driver_lng,
                  route_info.get('total_distance_km', 0),
                  route_info.get('total_duration_minutes', 0),
                  request_id))
            
            # Also log to ambulance_locations table for history
            cursor.execute('''
                INSERT INTO ambulance_locations (ambulance_id, latitude, longitude, timestamp, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (request_id, driver_lat, driver_lng, datetime.now().isoformat(), status))
            
            conn.commit()
            conn.close()
            
            return jsonify(response_data)
        else:
            conn.close()
            return jsonify({'error': 'Request not found'}), 404
            
    except Exception as e:
        print(f"Error updating driver location: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

# RUN APPLICATION


if __name__ == '__main__':
    print("=" * 70)
    print(" FastAid Ambulance Tracking System")
    print("=" * 70)
    print()
    print(" Server is running on:")
    print(f"   Main Website:      http://127.0.0.1:5001")
    print(f"   Driver Login:      http://127.0.0.1:5001/driver/login")
    print(f"   Admin Dashboard:   http://127.0.0.1:5001/admin")
    print(f"   Book Ambulance:    http://127.0.0.1:5001/booking")
    print()
    print(f"   Network Access:    http://192.168.1.102:5001")
    print()
    print("=" * 70)
    print("Press CTRL+C to stop the server")
    print("=" * 70)
    print()
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)


