import os
import math
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="templates", static_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "smart_parking_secret_key_2026")

# Database Configuration: Primary MySQL, fallback to SQLite if MySQL is unavailable
MYSQL_URI = os.environ.get("DATABASE_URL", "mysql+pymysql://root:password@localhost/smart_parking")
SQLITE_URI = "sqlite:///smart_parking.db"

app.config["SQLALCHEMY_DATABASE_URI"] = MYSQL_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()

# -------------------------
# Models
# -------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ParkingSlot(db.Model):
    __tablename__ = "parking_slots"
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default="Available")  # "Available" or "Occupied"

class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("parking_slots.id"), nullable=True)
    slot_number = db.Column(db.String(20), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False)
    booking_time = db.Column(db.String(50), nullable=False)
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    exit_time = db.Column(db.DateTime, nullable=True)
    amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="Active")  # "Active" or "Completed"


# -------------------------
# Database Initialization
# -------------------------
def init_db():
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            print("Connected successfully using primary database URI.")
        except Exception as e:
            print(f"Warning: Could not connect to MySQL ({e}). Falling back to SQLite.")
            app.config["SQLALCHEMY_DATABASE_URI"] = SQLITE_URI
            # Recreate engine with SQLite
            db.engine.dispose()
            db.init_app(app)
            db.create_all()
            print("SQLite fallback database initialized at 'smart_parking.db'.")

        # Seed default parking slots if empty
        if ParkingSlot.query.count() == 0:
            default_slots = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"]
            for slot_code in default_slots:
                db.session.add(ParkingSlot(slot_number=slot_code, status="Available"))
            db.session.commit()
            print("Default parking slots (A1-B4) seeded.")

init_db()


# -------------------------
# Helper Context Processor
# -------------------------
@app.context_processor
def inject_user():
    return {
        "current_user_id": session.get("user_id"),
        "current_user_name": session.get("user_name")
    }


# -------------------------
# Static File Routes (Compatibility)
# -------------------------
@app.route("/style.css")
def serve_css():
    return send_from_directory(".", "style.css", mimetype="text/css")

@app.route("/script.js")
def serve_js():
    return send_from_directory(".", "script.js", mimetype="application/javascript")


# -------------------------
# Authentication Routes
# -------------------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please log in.", "error")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("home"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return render_template("login.html", error="Invalid Email or Password")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# -------------------------
# Dashboard & Views
# -------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access your dashboard.", "info")
        return redirect(url_for("home"))

    user_bookings = Booking.query.filter_by(user_id=session["user_id"]).order_by(Booking.id.desc()).all()
    total_slots = ParkingSlot.query.count()
    available_slots = ParkingSlot.query.filter_by(status="Available").count()
    occupied_slots = total_slots - available_slots

    return render_template(
        "dashboard.html",
        name=session.get("user_name"),
        bookings=user_bookings,
        total_slots=total_slots,
        available_slots=available_slots,
        occupied_slots=occupied_slots
    )

@app.route("/parking")
def parking():
    slots = ParkingSlot.query.order_by(ParkingSlot.slot_number.asc()).all()
    total = len(slots)
    available = sum(1 for s in slots if s.status.lower() == "available")
    occupied = total - available

    active_bookings = Booking.query.filter_by(status="Active").order_by(Booking.id.desc()).all()

    return render_template(
        "parking.html",
        slots=slots,
        total=total,
        available=available,
        occupied=occupied,
        active_bookings=active_bookings
    )


# -------------------------
# Booking & Release APIs
# -------------------------
@app.route("/book/<int:slot_id>", methods=["POST"])
def book_slot(slot_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please log in to book a slot."}), 401

    slot = ParkingSlot.query.get(slot_id)
    if not slot:
        return jsonify({"success": False, "message": "Slot not found."}), 404

    if slot.status != "Available":
        return jsonify({"success": False, "message": "Slot is already occupied."}), 400

    vehicle_number = request.form.get("vehicle_number", "").strip().upper()
    booking_time = request.form.get("booking_time", "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not vehicle_number:
        return jsonify({"success": False, "message": "Vehicle number is required."}), 400

    # Check if vehicle already has an active booking
    existing_veh = Booking.query.filter_by(vehicle_number=vehicle_number, status="Active").first()
    if existing_veh:
        return jsonify({"success": False, "message": f"Vehicle '{vehicle_number}' is already parked in slot {existing_veh.slot_number}."}), 400

    booking = Booking(
        user_id=session["user_id"],
        slot_id=slot.id,
        slot_number=slot.slot_number,
        customer_name=session.get("user_name", "Registered User"),
        vehicle_number=vehicle_number,
        booking_time=booking_time,
        entry_time=datetime.utcnow(),
        status="Active"
    )
    slot.status = "Occupied"

    db.session.add(booking)
    db.session.commit()

    return jsonify({"success": True, "message": "Parking Slot Booked Successfully!", "slot_number": slot.slot_number})


@app.route("/api/slots", methods=["GET"])
@app.route("/get_slots.php", methods=["GET"])
def get_slots():
    slots = ParkingSlot.query.order_by(ParkingSlot.slot_number.asc()).all()
    slots_data = [{"id": s.id, "slot_number": s.slot_number, "status": s.status} for s in slots]

    total = len(slots)
    available = sum(1 for s in slots if s.status.lower() == "available")
    occupied = total - available

    active_bookings = Booking.query.filter_by(status="Active").order_by(Booking.id.desc()).all()
    bookings_data = [
        {
            "id": b.id,
            "slot_number": b.slot_number,
            "customer_name": b.customer_name,
            "vehicle_number": b.vehicle_number,
            "entry_time": b.entry_time.strftime("%Y-%m-%d %H:%M:%S") if b.entry_time else b.booking_time
        }
        for b in active_bookings
    ]

    return jsonify({
        "success": True,
        "slots": slots_data,
        "stats": {
            "total": total,
            "available": available,
            "occupied": occupied
        },
        "active_bookings": bookings_data
    })


@app.route("/api/reserve", methods=["POST"])
@app.route("/reserve.php", methods=["POST"])
def reserve_slot():
    customer_name = request.form.get("customer_name", "").strip()
    vehicle_number = request.form.get("vehicle_number", "").strip().upper()
    slot_number = request.form.get("slot_number", "").strip().upper()

    if not customer_name or not vehicle_number or not slot_number:
        return jsonify({"success": False, "message": "All fields (Name, Vehicle Number, Slot) are required."}), 400

    slot = ParkingSlot.query.filter_by(slot_number=slot_number).first()
    if not slot:
        return jsonify({"success": False, "message": f"Invalid parking slot: {slot_number}"}), 400

    if slot.status.lower() == "occupied":
        return jsonify({"success": False, "message": f"Sorry! Parking slot {slot_number} is already occupied."}), 400

    existing_active = Booking.query.filter_by(vehicle_number=vehicle_number, status="Active").first()
    if existing_active:
        return jsonify({"success": False, "message": f"Vehicle '{vehicle_number}' is already parked in slot {existing_active.slot_number}."}), 400

    user_id = session.get("user_id")
    now_dt = datetime.utcnow()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    booking = Booking(
        user_id=user_id,
        slot_id=slot.id,
        slot_number=slot.slot_number,
        customer_name=customer_name,
        vehicle_number=vehicle_number,
        booking_time=now_str,
        entry_time=now_dt,
        status="Active"
    )
    slot.status = "Occupied"

    db.session.add(booking)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Slot {slot.slot_number} reserved successfully!",
        "slot_number": slot.slot_number,
        "vehicle_number": vehicle_number,
        "customer_name": customer_name,
        "entry_time": now_str
    })


@app.route("/api/release", methods=["POST"])
@app.route("/release.php", methods=["POST"])
def release_slot():
    slot_number = request.form.get("slot_number", "").strip().upper()
    booking_id = request.form.get("booking_id", type=int)

    booking = None
    if booking_id:
        booking = Booking.query.filter_by(id=booking_id, status="Active").first()
    elif slot_number:
        booking = Booking.query.filter_by(slot_number=slot_number, status="Active").first()

    if not booking:
        return jsonify({"success": False, "message": "No active reservation found to release."}), 404

    exit_time = datetime.utcnow()
    entry_time = booking.entry_time or exit_time

    diff = exit_time - entry_time
    total_minutes = max(1, int(diff.total_seconds() / 60))
    hours = math.ceil(total_minutes / 60)
    hourly_rate = 2.00
    calculated_amount = round(hours * hourly_rate, 2)

    booking.exit_time = exit_time
    booking.amount = calculated_amount
    booking.status = "Completed"

    slot = ParkingSlot.query.filter_by(slot_number=booking.slot_number).first()
    if slot:
        slot.status = "Available"

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Vehicle checked out! Slot {booking.slot_number} is now Available.",
        "slot_number": booking.slot_number,
        "customer_name": booking.customer_name,
        "vehicle_number": booking.vehicle_number,
        "duration_minutes": total_minutes,
        "amount": f"{calculated_amount:.2f}",
        "exit_time": exit_time.strftime("%Y-%m-%d %H:%M:%S")
    })


# -------------------------
# Run Application
# -------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
