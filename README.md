# GeoAttendance

A smart attendance system using photo EXIF metadata (GPS coordinates and timestamp) to validate employee physical presence within an authorized geofence radius.

## Features

- **EXIF Verification**: Extracts `DateTimeOriginal` and `GPSInfo` directly from the uploaded photo metadata.
- **Geofence Validation**: Uses the Haversine distance formula to verify whether the photo was taken within the designated office perimeter.
- **Timestamp & Anti-Spoofing Checks**:
  - Validates that the photo was captured on today's date (rejects reused/archived photos).
  - Flags submissions captured after 9:00 AM as **LATE**.
  - Rejects future dates and missing/incomplete GPS metadata.
- **Employee Portal**: Clean, modern web interface for employees to check in with real-time feedback.
- **Manager & Admin Dashboard**:
  - Secure role-based authentication (`admin` and `manager`).
  - Attendance logs with status, timestamp, reason, and photo preview.
  - Interactive interface to update office location coordinates and radius on the fly.
  - Option to set office location using browser geolocation.

---

## Project Structure

```text
├── app.py                 # Flask application and REST endpoints
├── attendance_core.py     # EXIF extraction, GPS conversion & geofence validation
├── test_core.py           # Core logic testing script
├── requirements.txt       # Project dependencies
├── templates/             # HTML templates (Tailwind CSS)
│   ├── index.html         # Employee attendance portal
│   ├── admin_login.html   # Admin & manager login
│   ├── admin_dashboard.html # Attendance logs and location settings
│   └── login.html         # Portal login template
├── uploads/               # Stored employee photo uploads
└── attendance _stat/      # Sample verification images
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### 2. Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/Ify4west/GeoAttendance.git
cd GeoAttendance
python -m venv .venv
```

Activate the virtual environment:
- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python app.py
```

The application runs on `http://127.0.0.1:5001`.

### 4. Admin Credentials

- **Admin**: Username: `admin` / Password: `admin123`
- **Manager**: Username: `manager` / Password: `manager123`

---

## Running Verification Tests

To verify the core attendance logic against sample images:

```bash
python test_core.py
