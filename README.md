 # FirstAid - Ambulance Tracking and Management System

Your Lifeline in Emergencies

FirstAid is a comprehensive ambulance tracking and management system designed to streamline emergency medical services. This platform provides real-time ambulance dispatch, GPS tracking, and efficient resource management for healthcare providers and emergency services across the region.

---

## Executive Summary

FirstAid is an integrated emergency medical services platform that combines real-time GPS tracking with intelligent ambulance dispatch algorithms to ensure rapid response to medical emergencies. The system enables seamless coordination between patients, ambulance operators, hospital administrators, and emergency management personnel.

Whether responding to acute medical emergencies such as cardiac events, strokes, traumatic injuries, or managing routine non-emergency medical transports, FirstAid delivers reliable and professional medical assistance with comprehensive real-time monitoring capabilities.

---

## Core Features and Capabilities

### Real-Time Ambulance Tracking
- GPS-enabled location tracking with continuous position updates
- Real-time speed monitoring and calculation
- Interactive map-based tracking interface
- Historical route documentation and playback
- Multi-ambulance simultaneous tracking

### Ambulance Booking and Dispatch
- Streamlined patient information collection
- Automated ambulance assignment based on proximity and availability
- Priority-based dispatch (Critical, Urgent, Standard)
- Estimated Time of Arrival (ETA) calculation and prediction
- Booking confirmation and status updates

### Hospital Management
- Automated nearest hospital identification based on GPS coordinates
- Hospital service availability filtering
- Distance calculation using Haversine formula
- Hospital contact information and directions
- Integration with hospital management systems

### Administrative Dashboard
- Comprehensive fleet management interface
- Request status monitoring and updates
- Real-time ambulance availability tracking
- Performance analytics and reporting
- Secondary administrator management (main administrator access)
- Historical data archival and retrieval

### Driver and Operator Interface
- Operator authentication and authorization
- Navigation and route guidance
- Patient information display
- Real-time status updates
- Trip documentation and completion

### Reporting and Documentation
- PDF report generation for individual requests
- Patient information and medical history documentation
- Route and distance records
- Timestamp and location logging
- Batch reporting capabilities

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | Python Flask |
| Frontend Interface | HTML5, CSS3, JavaScript |
| Database Management | SQLite |
| Real-Time Communication | Flask-SocketIO, WebSocket Protocol |
| Geolocation Services | Google Maps API, OpenCage Geocoding API |
| Report Generation | ReportLab |
| Authentication | Werkzeug Security Library |
| Server Environment | Python Flask Development Server (Port 5001) |
| Security Protocol | HTTPS with SSL/TLS Encryption |
| Multi-Platform Support | Flutter Framework (iOS, Android, Web, Desktop) |

---

## System Requirements

- Python 3.6 or higher
- Minimum 2GB RAM
- 1GB available disk space
- Stable internet connection for API access
- Modern web browser with JavaScript support

---

## Project Structure

Ambulance-tracker-system/
├── ambulance_tracking_system/
│ ├── android/
│ ├── ios/
│ ├── lib/
│ ├── web/
│ ├── windows/
│ ├── macos/
│ ├── linux/
│ └── pubspec.yaml
├── templates/
│ ├── driver_login.html
│ ├── driver_dashboard.html
│ ├── driver_navigate.html
│ ├── tracking_search.html
│ ├── route_map.html
│ └── tracking_result.html
├── static/
│ ├── css/
│ ├── js/
│ ├── manifest.json
│ ├── images/
│ └── videos/
├── app.py
├── route_map.py
├── users.db
├── requirements.txt
├── README.md
└── .gitignore


---

## Database Schema

### ambulance_requests Table

Maintains records of all ambulance service requests.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment identifier |
| patient_name | TEXT | Full name of patient |
| contact | TEXT | Contact phone number |
| pickup_location | TEXT | Geographic address for ambulance pickup |
| destination | TEXT | Destination hospital or medical facility |
| ambulance_type | TEXT | Classification of required ambulance |
| priority | TEXT | Request priority level |
| status | TEXT | Current request status |
| created_at | TIMESTAMP | Request creation timestamp |
| assigned_ambulance_id | INTEGER | Assigned ambulance identifier |

### ambulance_locations Table

Records real-time ambulance positions and movement data.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment identifier |
| request_id | INTEGER | Foreign key reference to requests |
| ambulance_id | INTEGER | Ambulance identifier |
| latitude | REAL | Geographic latitude coordinate |
| longitude | REAL | Geographic longitude coordinate |
| speed | REAL | Current velocity in kilometers per hour |
| distance_covered | REAL | Distance traveled in kilometers |
| timestamp | TIMESTAMP | Location update timestamp |
| accuracy | REAL | GPS accuracy measurement in meters |

### admins Table

Manages administrator authentication and authorization.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment identifier |
| username | TEXT | Administrator username |
| password_hash | TEXT | Cryptographically hashed password |
| email | TEXT | Administrator email address |
| is_main_admin | BOOLEAN | Principal administrator privilege flag |
| created_at | TIMESTAMP | Account creation timestamp |
| last_login | TIMESTAMP | Most recent login timestamp |

### ambulances Table

Maintains fleet inventory and status information.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment identifier |
| ambulance_number | TEXT | Unique registration number |
| type | TEXT | Ambulance classification |
| status | TEXT | Current availability status |
| driver_id | INTEGER | Assigned operator identifier |
| current_latitude | REAL | Current position latitude |
| current_longitude | REAL | Current position longitude |
| fuel_level | REAL | Fuel tank percentage |
| last_maintenance | TIMESTAMP | Previous maintenance date |

---

## System Architecture

Client Layer (Multi-Platform)
|-- Web Browser Interface
|-- Flutter Mobile Application
|-- Progressive Web Application
|
v
Real-Time Communication Layer
|-- HTTP Protocol
|-- WebSocket Protocol
|-- REST API Endpoints
|
v
Flask Application Server (Port 5001)
|-- Request Routing
|-- Business Logic
|-- Session Management
|-- WebSocket Event Handling
|
v
Data Layer
|-- SQLite Database
|-- User Records
|-- Request History
|-- Location Tracking Data
|-- Administrator Accounts
|
v
External Services
|-- Google Maps API
|-- OpenCage Geocoding API
|-- Coordinates and Routing


---

## API Endpoints and Services

### Patient and User Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| / | GET | Home page and landing interface |
| /booking | GET, POST | Ambulance booking form and submission |
| /tracking | GET, POST | Ambulance tracking search interface |
| /track_ambulance | GET | Real-time tracking display |

### Driver and Operator Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /driver_login | GET, POST | Driver authentication |
| /driver_dashboard | GET | Operator dashboard interface |
| /driver_navigate/<req_id> | GET | Navigation and routing interface |
| /update_location | POST | Real-time position update |

### Administrator Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /login | GET, POST | Administrator authentication |
| /admin_dashboard | GET | Administrative management interface |
| /update_status/<req_id> | POST | Request status modification |
| /manage_admins | GET, POST | Secondary administrator management |
| /analytics | GET | Performance analytics and reporting |

### Utility and Support Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /download_pdf/<req_id> | GET | PDF report generation and download |
| /find_nearest_hospitals | GET | Hospital location search service |
| /logout | GET | Session termination |
| /privacy-policy | GET | Privacy policy documentation |
| /terms-of-service | GET | Terms and conditions |

---

## Real-Time Communication Features

### WebSocket Events

The system implements real-time event streaming through WebSocket connections:

- ambulance_update: Real-time position and speed data
- request_status_change: Status modification notifications
- new_request: Incoming ambulance request alerts
- eta_update: Updated arrival time calculations
- driver_arrival: Driver arrival confirmations

### Real-Time Capabilities

- Continuous GPS coordinate transmission
- Instantaneous speed calculation and display
- Live request status notifications
- Dynamic ETA predictions with traffic analysis
- Support for multiple concurrent tracking sessions
- Automatic reconnection on connection interruption

---

## Security Implementation

### Authentication and Authorization

| Security Feature | Implementation Method |
|------------------|----------------------|
| Password Security | Werkzeug cryptographic hashing with salt |
| Session Management | Secure Flask sessions with timeout enforcement |
| Encryption | HTTPS/TLS protocol for all communications |
| Input Validation | Sanitization and validation to prevent injection attacks |
| Access Control | Role-based permission management |
| Data Protection | Encrypted storage of sensitive information |
| CSRF Prevention | Cross-Site Request Forgery token validation |
| Rate Limiting | Request throttling for API endpoints |

### Role-Based Access Control

- Patient: Booking and tracking capabilities
- Driver/Operator: Navigation and status management
- Administrator: Request management and reporting
- Primary Administrator: Full system and personnel management

---

## Installation and Deployment

### Prerequisites

- Python 3.6 or higher
- pip package manager
- Git version control system
- Internet connection for API keys

### Installation Steps

#1. Clone the Repository
git clone https://github.com/manjusankalp-06/Ambulance-tracker-system.git
cd Ambulance-tracker-system

#2. Create Python Virtual Environment
python -m venv venv
source venv/bin/activate
# On Windows: venv\Scripts\activate

#3. Install Dependencies
pip install -r requirements.txt

#4. Configure Environment Variables
#Create .env file in project root directory:
GOOGLE_MAPS_API_KEY=your_api_key_here
OPENCAGE_API_KEY=your_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True

#5. Initialize Database
python app.py

#6. Access Application
Navigate to: https://localhost:5001
