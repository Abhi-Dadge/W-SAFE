from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from functools import wraps
# from openai import OpenAI
import os

app = Flask(__name__)
app.secret_key = "women_safety_secret"
print("DEBUG API KEY:", os.getenv("OPENAI_API_KEY"))

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# ADMIN (SUPERUSER)
# =========================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@app.route("/ai-chat")
def ai_chat():
    if session.get("role") != "user":
        return redirect("/login")
    return render_template("ai_chat.html")

@app.route("/ai-reply", methods=["POST"])
def ai_reply():
    return jsonify({"reply": "AI is temporarily unavailable."})

# =========================
# DATABASE CONNECTION
# =========================
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            phone TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            contact_name TEXT,
            contact_phone TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sos_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            latitude TEXT,
            longitude TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn

# =========================
# ADMIN PROTECTION DECORATOR
# =========================
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect("/admin-login")
        return f(*args, **kwargs)
    return wrapper

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return render_template("index.html")

# =========================
# USER LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = "user"
            return redirect("/dashboard")

        return "Invalid login details ❌"

    return render_template("login.html")

# =========================
# USER REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (name,email,password,phone) VALUES (?,?,?,?)",
            (
                request.form["name"],
                request.form["email"],
                request.form["password"],
                request.form["phone"]
            )
        )
        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template("register.html")

# =========================
# USER DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if session.get("role") != "user":
        return redirect("/login")

    return render_template("dashboard.html", name=session["name"])

# =========================
# USER PAGES
# =========================
@app.route("/helplines")
def helplines():
    if session.get("role") != "user":
        return redirect("/")
    return render_template("helplines.html")

@app.route("/laws")
def laws():
    if session.get("role") != "user":
        return redirect("/")
    return render_template("laws.html")

@app.route("/self_defense")
def self_defense():
    if session.get("role") != "user":
        return redirect("/")
    return render_template("self_defense.html")

# =========================
# CONTACTS
# =========================
@app.route("/contacts", methods=["GET", "POST"])
def contacts():
    if session.get("role") != "user":
        return redirect("/")

    conn = get_db_connection()

    if request.method == "POST":
        conn.execute(
            "INSERT INTO emergency_contacts (user_id, contact_name, contact_phone) VALUES (?,?,?)",
            (session["user_id"], request.form["name"], request.form["phone"])
        )
        conn.commit()

    contacts = conn.execute(
        "SELECT * FROM emergency_contacts WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()

    conn.close()
    return render_template("add_contact.html", contacts=contacts)

# =========================
# SOS BUTTON (USER)
# =========================
@app.route("/sos", methods=["POST"])
def sos():
    if session.get("role") != "user":
        return "Unauthorized", 401

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO sos_logs (user_id, latitude, longitude) VALUES (?,?,?)",
        (session["user_id"], request.form["latitude"], request.form["longitude"])
    )
    conn.commit()
    conn.close()

    return "SOS SENT"

# SOS SUCCESS PAGE

@app.route("/sos_success")
def sos_success():
    return render_template(
        "sos_success.html",
        lat=request.args.get("lat"),
        lon=request.args.get("lon")
    )

# ADMIN LOGIN

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            return redirect("/admin-dashboard")

        return "Invalid Admin Credentials ❌"

    return render_template("admin_login.html")

# ADMIN DASHBOARD

@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():
    conn = get_db_connection()

    # All SOS logs
    logs = conn.execute("""
        SELECT sos_logs.id, sos_logs.latitude, sos_logs.longitude,
               sos_logs.timestamp, users.name
        FROM sos_logs
        LEFT JOIN users ON sos_logs.user_id = users.id
        ORDER BY sos_logs.timestamp DESC
    """).fetchall()

    # Total registered users
    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    # Live SOS (last 10 minutes)
    live_sos = conn.execute("""
        SELECT COUNT(*) FROM sos_logs
        WHERE timestamp >= datetime('now', '-10 minutes')
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        logs=logs,
        total_users=total_users,
        live_sos=live_sos
    )



# DELETE SOS (ADMIN)

@app.route("/admin/delete_sos/<int:sos_id>")
@admin_required
def delete_sos(sos_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM sos_logs WHERE id=?", (sos_id,))
    conn.commit()
    conn.close()
    return redirect("/admin-dashboard")

 # LOGOUT
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/police")
def police():
    if session.get("role") != "user":
        return redirect("/login")
    return render_template("police.html")

@app.route("/hospital")
def hospital():
    if session.get("role") != "user":
        return redirect("/")
    return render_template("hospital.html")

@app.route("/ai-help")
def ai_help():
    if session.get("role") != "user":
        return redirect("/login")
    return render_template("ai_help.html")


# RUN

if __name__ == "__main__":
    app.run()
