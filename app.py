
import os
import sqlite3
import uuid
import secrets

from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    session,
    abort
)

from werkzeug.utils import secure_filename

app = Flask(__name__)

# Admin authentication
app.secret_key = os.environ["ROADWATCH_SECRET_KEY"]
ADMIN_PASSWORD = os.environ["ROADWATCH_ADMIN_PASSWORD"]

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return function(*args, **kwargs)
    return wrapper


UPLOAD_FOLDER = os.path.join(
    app.root_path, "static", "uploads"
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


DATABASE = "roadwatch.db"


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                damage_type TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(reports)")
        }

        if "photo" not in columns:
            conn.execute(
                "ALTER TABLE reports ADD COLUMN photo TEXT"
            )

        columns= {
            row[1]
            for row in conn.execute("PRAGMA table_info(reports)")
        }

        if "latitude" not in columns:
            conn.execute(
                "ALTER TABLE reports ADD COLUMN latitude REAL"
            )

        if "longitude" not in columns:
            conn.execute(
                "ALTER TABLE reports ADD COLUMN longitude REAL"
            )

        # Create table for website usage analytics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)





@app.route("/")
def home():
    return render_template("index.html")



@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        location = request.form.get("location", "").strip()
        damage_type = request.form.get("damage_type", "").strip()
        description = request.form.get("description", "").strip()

        if not location or not damage_type or not description:
            return "Please fill in all required fields.", 400

        photo = request.files.get("photo")
        photo_filename = None

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                return "Only JPG, PNG and WebP images are allowed.", 400

            original = secure_filename(photo.filename)
            extension = original.rsplit(".", 1)[1].lower()

            photo_filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )

            photo.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    photo_filename
                )
            )

        # Get selected map coordinates
        try:
            latitude = float(request.form.get("latitude", ""))
            longitude = float(request.form.get("longitude", ""))

            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError()

        except (ValueError, TypeError):
            return "Please select a valid location on the map.", 400

        
        with sqlite3.connect(DATABASE) as conn:
            conn.execute(
                """
                INSERT INTO reports
                (location, damage_type, description, photo, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    location,
                    damage_type,
                    description,
                    photo_filename,
                    latitude,
                    longitude
                )
            )
        log_event("report_submitted")

        return redirect(url_for("reports"))

    return render_template("report.html")



@app.route("/reports")
def reports():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        saved_reports = conn.execute(
            "SELECT * FROM reports ORDER BY id DESC"
        ).fetchall()

    return render_template(
        "reports.html",
        reports=saved_reports
    )


init_db()

def log_event(event_type):
    allowed_events = {
        "report_submitted",
        "report_searched"
    }

    if event_type not in allowed_events:
        return

    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            "INSERT INTO usage_logs (event_type) VALUES (?)",
            (event_type,)
        )


@app.route("/track", methods=["GET"])
def track_report():
    report_id = request.args.get("report_id", "").strip()
    report = None
    searched = bool(report_id)

    if report_id:
        if not report_id.isdigit() or int(report_id) < 1:
            return "Please enter a valid report ID.", 400
        
        log_event("report_searched")

        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row

            report = conn.execute(
                "SELECT * FROM reports WHERE id = ?",
                (int(report_id),)
            ).fetchone()

    return render_template(
        "track.html",
        report=report,
        report_id=report_id,
        searched=searched
    )
   
# Admin login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")

        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["is_admin"] = True
            session["csrf_token"] = secrets.token_hex(32)
            return redirect(url_for("admin_dashboard"))

        return render_template(
            "admin_login.html",
            error="Incorrect administrator password."
        )

    return render_template("admin_login.html", error=None)


# Admin dashboard
@app.route("/admin")
@admin_required
def admin_dashboard():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        reports = conn.execute(
            "SELECT * FROM reports ORDER BY id DESC"
        ).fetchall()

        # Get website usage statistics
        submission_count = conn.execute(
            """
            SELECT COUNT(*) FROM usage_logs
            WHERE event_type = 'report_submitted'
            """
        ).fetchone()[0]

        search_count = conn.execute(
            """
            SELECT COUNT(*) FROM usage_logs
            WHERE event_type = 'report_searched'
            """
        ).fetchone()[0]

        # Count reports by damage type
        damage_stats = conn.execute("""
            SELECT damage_type, COUNT(*) AS total
            FROM reports
            GROUP BY damage_type
            ORDER BY total DESC
        """).fetchall()



    return render_template(
        "admin.html",
        reports=reports,
        total_reports=len(reports),
        pending_reports=sum(
            1 for r in reports if r["status"] == "Pending"
        ),
        progress_reports=sum(
            1 for r in reports if r["status"] == "In Progress"
        ),
        resolved_reports=sum(
            1 for r in reports if r["status"] == "Resolved"
        ),
                submission_count=submission_count,
        search_count=search_count,
        damage_stats=damage_stats
    )


# Update report status
@app.route("/admin/update/<int:report_id>", methods=["POST"])
@admin_required
def update_status(report_id):
    token = request.form.get("csrf_token", "")

    if not secrets.compare_digest(
        token, session.get("csrf_token", "")
    ):
        abort(403)

    new_status = request.form.get("status", "")

    if new_status not in ("Pending", "In Progress", "Resolved"):
        abort(400)

    with sqlite3.connect(DATABASE) as conn:
        result = conn.execute(
            "UPDATE reports SET status = ? WHERE id = ?",
            (new_status, report_id)
        )

    if result.rowcount == 0:
        abort(404)

    return redirect(url_for("admin_dashboard"))


# Admin logout
@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    token = request.form.get("csrf_token", "")

    if not secrets.compare_digest(
        token, session.get("csrf_token", "")
    ):
        abort(403)

    session.clear()
    return redirect(url_for("admin_login"))
 
if __name__ == "__main__":
    app.run(debug=True)
