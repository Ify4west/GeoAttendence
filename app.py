from datetime import datetime
from functools import wraps
import os
import sqlite3
import time

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask.helpers import secure_filename

from attendance_core import process_attendance


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

UPLOAD_FOLDER = "uploads"
DATABASE_PATH = "attendance.db"
DEFAULT_LOCATION = {
    "location_name": "Default Location",
    "latitude": 12.924078,
    "longitude": 77.560282,
    "radius_meters": 300,
}
ADMIN_USERS = {
    "admin": {
        "password": os.environ.get("ADMIN_PASSWORD", "admin123"),
        "role": "admin",
    },
    "manager": {
        "password": os.environ.get("MANAGER_PASSWORD", "manager123"),
        "role": "manager",
    },
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                employee_name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                checked_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance_location (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                location_name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                radius_meters REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO attendance_location (
                id,
                location_name,
                latitude,
                longitude,
                radius_meters,
                updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_LOCATION["location_name"],
                DEFAULT_LOCATION["latitude"],
                DEFAULT_LOCATION["longitude"],
                DEFAULT_LOCATION["radius_meters"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )


def get_current_attendance_location():
    with get_db_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM attendance_location
            WHERE id = 1
            """
        ).fetchone()


def update_attendance_location(location_name, latitude, longitude, radius_meters):
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE attendance_location
            SET location_name = ?,
                latitude = ?,
                longitude = ?,
                radius_meters = ?,
                updated_at = ?
            WHERE id = 1
            """,
            (
                location_name,
                latitude,
                longitude,
                radius_meters,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )


def validate_location_form(form):
    location_name = form.get("location_name", "").strip() or "Attendance Location"

    try:
        latitude = float(form.get("latitude", ""))
        longitude = float(form.get("longitude", ""))
        radius_meters = float(form.get("radius_meters", ""))
    except ValueError:
        return None, "Latitude, longitude, and radius must be valid numbers"

    if not -90 <= latitude <= 90:
        return None, "Latitude must be between -90 and 90"

    if not -180 <= longitude <= 180:
        return None, "Longitude must be between -180 and 180"

    if radius_meters <= 0:
        return None, "Radius must be a positive number"

    return {
        "location_name": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "radius_meters": radius_meters,
    }, None


def record_attendance(employee_id, employee_name, original_filename, stored_filename, status, reason):
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO attendance_logs (
                employee_id,
                employee_name,
                original_filename,
                stored_filename,
                status,
                reason,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employee_id,
                employee_name,
                original_filename,
                stored_filename,
                status,
                reason,
                checked_at,
            ),
        )


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") not in {"admin", "manager"}:
            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapped_view


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html", location=get_current_attendance_location())


@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    if "image" not in request.files:
        return jsonify({"status": "REJECTED", "reason": "No file part"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"status": "REJECTED", "reason": "No selected file"}), 400

    employee_id = request.form.get("employee_id", "").strip()
    employee_name = request.form.get("employee_name", "").strip()

    if not employee_id or not employee_name:
        return jsonify({"status": "REJECTED", "reason": "Employee name and ID are required"}), 400

    filename = f"{int(time.time())}_{secure_filename(file.filename)}"
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)
    location = get_current_attendance_location()

    try:
        status, reason = process_attendance(
            save_path,
            location["latitude"],
            location["longitude"],
            location["radius_meters"],
        )
    except Exception as exc:
        status = "REJECTED"
        reason = f"Could not process image: {exc}"

    record_attendance(
        employee_id=employee_id,
        employee_name=employee_name,
        original_filename=file.filename,
        stored_filename=filename,
        status=status,
        reason=reason,
    )

    return jsonify({
        "status": status,
        "reason": reason
    })


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = ADMIN_USERS.get(username)

        if user and password == user["password"]:
            session["username"] = username
            session["role"] = user["role"]
            return redirect(url_for("admin_dashboard"))

        error = "Invalid admin or manager credentials"

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin", methods=["GET"])
@admin_required
def admin_dashboard():
    with get_db_connection() as conn:
        records = conn.execute(
            """
            SELECT *
            FROM attendance_logs
            ORDER BY checked_at DESC, id DESC
            """
        ).fetchall()

        summary = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) AS present_count,
                SUM(CASE WHEN status = 'LATE' THEN 1 ELSE 0 END) AS late_count,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_count
            FROM attendance_logs
            """
        ).fetchone()

    return render_template(
        "admin_dashboard.html",
        records=records,
        summary=summary,
        location=get_current_attendance_location(),
        location_error=request.args.get("location_error"),
        location_success=request.args.get("location_success"),
        username=session.get("username"),
        role=session.get("role"),
    )


@app.route("/admin/location", methods=["POST"])
@admin_required
def admin_update_location():
    location, error = validate_location_form(request.form)

    if error:
        return redirect(url_for("admin_dashboard", location_error=error))

    update_attendance_location(
        location["location_name"],
        location["latitude"],
        location["longitude"],
        location["radius_meters"],
    )

    return redirect(url_for("admin_dashboard", location_success="Attendance location updated"))


@app.route("/admin/photos/<filename>", methods=["GET"])
@admin_required
def admin_photo(filename):
    safe_filename = secure_filename(filename)
    if safe_filename != filename:
        abort(404)

    return send_from_directory(UPLOAD_FOLDER, safe_filename)


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
