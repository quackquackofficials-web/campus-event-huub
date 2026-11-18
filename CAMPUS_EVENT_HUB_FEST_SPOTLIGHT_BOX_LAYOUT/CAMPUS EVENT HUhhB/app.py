npm run devfrom flask import (
    Flask, render_template, request, redirect, url_for, flash, session, abort
)
import sqlite3
from datetime import date
from functools import wraps
import os
import uuid

from werkzeug.security import generate_password_hash, check_password_hash

from models import event_model_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB poster limit

DATABASE = "campus_events.db"
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_POSTERS = {"png", "jpg", "jpeg", "gif", "webp"}

# ------------------------------------------------------------------
# FESTS / PROGRAMS
# Events can be added freely under any of these. Edit this list if a
# new fest or program is added in the future.
# ------------------------------------------------------------------
FESTS = {
    "yvidh-tech": {
        "name": "YVIDH Tech Fest", "group": "YVIDH", "icon": "💻",
        "desc": "The technical half of YVIDH: coding, robotics, workshops and more.",
    },
    "yvidh-arts": {
        "name": "YVIDH Arts Fest", "group": "YVIDH", "icon": "🎨",
        "desc": "The arts half of YVIDH: music, dance, drama, design and more.",
    },
    "rapido": {
        "name": "RAPIDO", "group": "Sports", "icon": "🏃",
        "desc": "Sports competition between the students of our college.",
    },
    "spike": {
        "name": "SPIKE", "group": "Sports", "icon": "🏐",
        "desc": "Inter-college sports competition between different colleges.",
    },
    "onam": {
        "name": "Onam Celebration", "group": "Celebrations", "icon": "🌼",
        "desc": "Pookalam, sadya, games and cultural programs.",
    },
    "christmas": {
        "name": "Christmas Celebration", "group": "Celebrations", "icon": "🎄",
        "desc": "Carols, cake, cultural programs and a lot of fun.",
    },
    "dekathon": {
        "name": "Dekathon", "group": "Dekathon", "icon": "⚡",
        "desc": "Our Dekathon event.",
    },
}

FEST_GROUPS = ["YVIDH", "Sports", "Celebrations", "Dekathon"]


# ------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            description TEXT,
            poster TEXT,
            venue TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL
        )
    """)

    # New columns on events (added safely if the table already exists)
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(events)")}
    for column, definition in (
        ("fest", "TEXT"),            # key from FESTS
        ("admin_id", "INTEGER"),     # admin assigned to this event
        ("created_by", "INTEGER"),   # admin who created it
        ("start_time", "TEXT"),       # optional event start time
        ("end_time", "TEXT"),         # optional event end time
    ):
        if column not in existing:
            conn.execute(f"ALTER TABLE events ADD COLUMN {column} {definition}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            semester TEXT NOT NULL,
            year TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            in_charge_of TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            note TEXT,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (event_id, student_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            winner_name TEXT NOT NULL,
            department TEXT
        )
    """)

    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def event_status(item, today=None):
    today = today or date.today()
    start = date.fromisoformat(item["start_date"])
    end = date.fromisoformat(item["end_date"])

    if today < start:
        return "Upcoming"
    elif start <= today <= end:
        return "Ongoing"
    return "Completed"


def current_student_id():
    if session.get("role") == "student":
        return session.get("user_id")
    return None


def load_events(where="", params=(), student_id=None):
    """Events with status, registration count, winners and (optionally)
    whether the given student has registered."""
    conn = get_db()
    rows = conn.execute(f"""
        SELECT e.*,
               a.name AS admin_name,
               (SELECT COUNT(*) FROM registrations r
                 WHERE r.event_id = e.id) AS reg_count
        FROM events e
        LEFT JOIN admins a ON a.id = e.admin_id
        {where}
        ORDER BY e.start_date ASC, e.id ASC
    """, params).fetchall()

    winner_rows = conn.execute(
        "SELECT * FROM winners ORDER BY event_id, position"
    ).fetchall()

    registered = set()
    if student_id:
        registered = {
            r["event_id"] for r in conn.execute(
                "SELECT event_id FROM registrations WHERE student_id = ?",
                (student_id,)
            )
        }
    conn.close()

    winners = {}
    for w in winner_rows:
        winners.setdefault(w["event_id"], []).append(dict(w))

    today = date.today()
    event_list = []

    for row in rows:
        item = dict(row)
        item["status"] = event_status(item, today)
        item["winners"] = winners.get(item["id"], [])
        item["registered"] = item["id"] in registered
        item["fest_info"] = FESTS.get(item.get("fest"))
        # Build the appropriate subclass; event_kind() is polymorphic.
        item = event_model_for(item).as_dict()
        event_list.append(item)

    return event_list


def can_manage_event(event):
    """Only the admin assigned to an event (or the admin who created it)
    can edit its details, see registrations and declare winners."""
    if session.get("role") != "admin":
        return False
    admin_id = session.get("user_id")
    return admin_id in (event.get("admin_id"), event.get("created_by"))


def get_managed_event(event_id):
    events = load_events("WHERE e.id = ?", (event_id,))
    if not events:
        abort(404)
    event = events[0]
    if not can_manage_event(event):
        abort(403)
    return event


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("Please login to continue.", "error")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


def save_poster(file):
    """Saves an uploaded poster and returns its file name (or None)."""
    if not file or not file.filename:
        return None

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_POSTERS:
        raise ValueError("Poster must be a PNG, JPG, GIF or WEBP image.")

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, name))
    return name


def delete_poster(name):
    if not name:
        return
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, name))
    except OSError:
        pass


def fest_summaries(events):
    summary = []
    for slug, info in FESTS.items():
        in_fest = [e for e in events if e.get("fest") == slug]
        summary.append({
            "slug": slug,
            "total": len(in_fest),
            "live": sum(1 for e in in_fest if e["status"] == "Ongoing"),
            **info,
        })
    return summary


@app.context_processor
def inject_globals():
    return {"FESTS": FESTS, "FEST_GROUPS": FEST_GROUPS}


@app.errorhandler(403)
def forbidden(_error):
    flash("You don't have permission to do that.", "error")
    return redirect(url_for("home"))


@app.errorhandler(404)
def not_found(_error):
    flash("That page could not be found.", "error")
    return redirect(url_for("home"))


# ------------------------------------------------------------------
# PUBLIC PAGES
# ------------------------------------------------------------------
@app.route("/")
def home():
    event_list = load_events(student_id=current_student_id())

    return render_template(
        "index.html",
        events=event_list,
        fests=fest_summaries(event_list)
    )


@app.route("/fest/<slug>")
def fest_page(slug):
    fest = FESTS.get(slug)
    if not fest:
        abort(404)

    event_list = load_events(
        "WHERE e.fest = ?", (slug,), student_id=current_student_id()
    )

    return render_template(
        "fest.html",
        fest=fest,
        slug=slug,
        events=event_list
    )


@app.route("/event/<int:event_id>")
def event_detail(event_id):
    events = load_events(
        "WHERE e.id = ?", (event_id,), student_id=current_student_id()
    )
    if not events:
        abort(404)

    event = events[0]
    return render_template(
        "event_detail.html",
        event=event,
        can_manage=can_manage_event(event)
    )


# ------------------------------------------------------------------
# AUTH
# ------------------------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role", "student")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Name, email and a password of at least 8 characters are required.", "error")
            return render_template("signup.html")

        conn = get_db()
        try:
            if role == "admin":
                in_charge_of = request.form.get("in_charge_of", "").strip()
                if not department or not in_charge_of:
                    flash("Department and in-charge of event are required.", "error")
                    return render_template("signup.html")

                conn.execute(
                    """INSERT INTO admins
                       (name, department, in_charge_of, email, phone, password_hash)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (name, department, in_charge_of, email, phone,
                     generate_password_hash(password))
                )
            else:
                roll_number = request.form.get("roll_number", "").strip()
                semester = request.form.get("semester", "").strip()
                year = request.form.get("year", "").strip()
                if not (roll_number and department and semester and year):
                    flash("Roll number, department, semester and year are required.", "error")
                    return render_template("signup.html")

                conn.execute(
                    """INSERT INTO students
                       (name, roll_number, department, semester, year,
                        email, phone, password_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, roll_number, department, semester, year,
                     email, phone, generate_password_hash(password))
                )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("An account with this email (or roll number) already exists.", "error")
            return render_template("signup.html")
        finally:
            conn.close()

        flash("Account created! You can login now.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "student")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        table = "admins" if role == "admin" else "students"

        conn = get_db()
        user = conn.execute(
            f"SELECT * FROM {table} WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["role"] = "admin" if role == "admin" else "student"
            session["user_id"] = user["id"]
            session["name"] = user["name"]

            flash(f"Welcome, {user['name']}!", "success")
            if session["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("student_dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


# ------------------------------------------------------------------
# STUDENT
# ------------------------------------------------------------------
@app.route("/student/dashboard")
@role_required("student")
def student_dashboard():
    student_id = session["user_id"]

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    conn.close()

    if not student:
        session.clear()
        return redirect(url_for("login"))

    my_events = load_events(
        "WHERE e.id IN (SELECT event_id FROM registrations WHERE student_id = ?)",
        (student_id,), student_id=student_id
    )

    return render_template(
        "student_dashboard.html",
        student=student,
        events=my_events
    )


@app.route("/event/<int:event_id>/register", methods=["POST"])
@role_required("student")
def register_event(event_id):
    events = load_events("WHERE e.id = ?", (event_id,))
    if not events:
        abort(404)

    event = events[0]
    if event["status"] == "Completed":
        flash("Registration is closed. This event is already completed.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    note = request.form.get("note", "").strip()[:200]

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO registrations (event_id, student_id, note) VALUES (?, ?, ?)",
            (event_id, session["user_id"], note)
        )
        conn.commit()
        flash(f"You are registered for {event['title']}!", "success")
    except sqlite3.IntegrityError:
        flash("You are already registered for this event.", "error")
    finally:
        conn.close()

    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/event/<int:event_id>/unregister", methods=["POST"])
@role_required("student")
def unregister_event(event_id):
    events = load_events("WHERE e.id = ?", (event_id,))
    if not events:
        abort(404)

    if events[0]["status"] == "Completed":
        flash("This event is already completed.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    conn = get_db()
    conn.execute(
        "DELETE FROM registrations WHERE event_id = ? AND student_id = ?",
        (event_id, session["user_id"])
    )
    conn.commit()
    conn.close()

    flash("Your registration has been cancelled.", "success")
    return redirect(url_for("event_detail", event_id=event_id))


# ------------------------------------------------------------------
# ADMIN
# ------------------------------------------------------------------
@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    admin_id = session["user_id"]

    conn = get_db()
    admin = conn.execute(
        "SELECT * FROM admins WHERE id = ?", (admin_id,)
    ).fetchone()
    conn.close()

    if not admin:
        session.clear()
        return redirect(url_for("login"))

    my_events = load_events(
        "WHERE e.admin_id = ? OR e.created_by = ? OR e.admin_id IS NULL", (admin_id, admin_id)
    )

    return render_template(
        "admin_dashboard.html",
        admin=admin,
        events=my_events
    )


def handle_event_form(event):
    conn = get_db()
    admins = conn.execute(
        "SELECT id, name, department FROM admins ORDER BY name"
    ).fetchall()
    conn.close()

    if request.method == "POST":
        form = request.form.to_dict()
        title = form.get("title", "").strip()
        fest = form.get("fest", "")
        description = form.get("description", "").strip()
        venue = form.get("venue", "").strip()
        start_date = form.get("start_date", "")
        end_date = form.get("end_date", "") or start_date
        start_time = form.get("start_time", "").strip()
        end_time = form.get("end_time", "").strip()

        try:
            assigned = int(form.get("admin_id") or session["user_id"])
        except ValueError:
            assigned = session["user_id"]

        errors = []
        if not title:
            errors.append("Event title is required.")
        if fest not in FESTS:
            errors.append("Please choose a fest / program.")
        if not venue:
            errors.append("Venue is required.")
        if assigned not in {a["id"] for a in admins}:
            errors.append("Please choose a valid admin to assign.")

        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            if end < start:
                errors.append("End date cannot be before the start date.")
        except ValueError:
            errors.append("Please enter valid dates.")

        poster = event["poster"] if event else None
        new_poster = None
        if not errors:
            try:
                new_poster = save_poster(request.files.get("poster"))
            except ValueError as error:
                errors.append(str(error))

        if errors:
            for message in errors:
                flash(message, "error")
            return render_template(
                "event_form.html", event=event, form=form, admins=admins
            )

        conn = get_db()
        if event:
            conn.execute(
                """UPDATE events SET title = ?, category = ?, description = ?,
                       poster = ?, venue = ?, start_date = ?, end_date = ?,
                       fest = ?, admin_id = ?, start_time = ?, end_time = ?
                   WHERE id = ?""",
                (title, FESTS[fest]["name"], description,
                 new_poster or poster, venue, start_date, end_date,
                 fest, assigned, start_time or None, end_time or None, event["id"])
            )
            if new_poster:
                delete_poster(poster)
            flash("Event updated.", "success")
            event_id = event["id"]
        else:
            cursor = conn.execute(
                """INSERT INTO events
                   (title, category, description, poster, venue,
                    start_date, end_date, fest, admin_id, created_by,
                    start_time, end_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, FESTS[fest]["name"], description, new_poster, venue,
                 start_date, end_date, fest, assigned, session["user_id"],
                 start_time or None, end_time or None)
            )
            event_id = cursor.lastrowid
            flash("Event added.", "success")
        conn.commit()
        conn.close()

        return redirect(url_for("event_detail", event_id=event_id))

    form = dict(event) if event else {"admin_id": session["user_id"]}
    return render_template("event_form.html", event=event, form=form, admins=admins)


@app.route("/admin/events/<int:event_id>/claim", methods=["POST"])
@role_required("admin")
def claim_event(event_id):
    events = load_events("WHERE e.id = ?", (event_id,))
    if not events:
        abort(404)
    if events[0].get("admin_id") is not None:
        flash("This event has already been assigned to an admin.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    conn.execute(
        "UPDATE events SET admin_id = ? WHERE id = ? AND admin_id IS NULL",
        (session["user_id"], event_id)
    )
    conn.commit()
    conn.close()
    flash("You are now the in-charge admin for this event.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/events/new", methods=["GET", "POST"])
@role_required("admin")
def event_new():
    return handle_event_form(None)


@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def event_edit(event_id):
    return handle_event_form(get_managed_event(event_id))


@app.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@role_required("admin")
def event_delete(event_id):
    event = get_managed_event(event_id)

    conn = get_db()
    conn.execute("DELETE FROM registrations WHERE event_id = ?", (event_id,))
    conn.execute("DELETE FROM winners WHERE event_id = ?", (event_id,))
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

    delete_poster(event["poster"])
    flash("Event deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/events/<int:event_id>/registrations")
@role_required("admin")
def event_registrations(event_id):
    event = get_managed_event(event_id)

    conn = get_db()
    students = conn.execute(
        """SELECT s.name, s.roll_number, s.department, s.semester, s.year,
                  s.email, s.phone, r.note, r.registered_at
           FROM registrations r
           JOIN students s ON s.id = r.student_id
           WHERE r.event_id = ?
           ORDER BY r.registered_at ASC""",
        (event_id,)
    ).fetchall()
    conn.close()

    return render_template(
        "event_registration.html", event=event, students=students
    )


@app.route("/admin/events/<int:event_id>/winners", methods=["GET", "POST"])
@role_required("admin")
def event_winners(event_id):
    event = get_managed_event(event_id)

    if event["status"] == "Upcoming":
        flash("Winners can be declared once the event has started.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        conn = get_db()
        conn.execute("DELETE FROM winners WHERE event_id = ?", (event_id,))

        for position in range(1, 6):
            name = request.form.get(f"winner_name_{position}", "").strip()
            department = request.form.get(f"winner_dept_{position}", "").strip()
            if name:
                conn.execute(
                    """INSERT INTO winners (event_id, position, winner_name, department)
                       VALUES (?, ?, ?, ?)""",
                    (event_id, position, name, department)
                )

        conn.commit()
        conn.close()

        flash("Winners saved.", "success")
        return redirect(url_for("event_detail", event_id=event_id))

    current = {w["position"]: w for w in event["winners"]}
    return render_template("event_winners.html", event=event, current=current)


create_database()

if __name__ == "__main__":
    app.run(debug=True)
    
