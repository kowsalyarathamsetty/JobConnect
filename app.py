import sqlite3
from contextlib import closing
from pathlib import Path
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)
DATABASE = Path(__file__).with_name("jobs.db")
JOB_FIELDS = ("title", "company", "location", "salary", "description")

def init_db() -> None:
    # FIXED: Order correct chesa - title, company, location, description, salary
    sample_jobs = [
        ("Python Developer", "Infosys", "Hyderabad", "Build and maintain Python apps.", "8 LPA"),
        ("Data Analyst", "Deloitte", "Bangalore", "Turn data into insights.", "10 LPA"),
        ("Frontend Dev", "TCS", "Chennai", "Create responsive web experiences.", "6 LPA"),
    ]

    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                salary TEXT NOT NULL
            )
            """
        )
        job_count = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        if job_count == 0:
            connection.executemany(
                """
                INSERT INTO jobs (title, company, location, description, salary)
                VALUES (?, ?, ?, ?, ?)
                """,
                sample_jobs,
            )
            print("Sample jobs inserted!")
        connection.commit()

def search_jobs(keyword: str = "", location: str = ""):
    conditions = []
    parameters = []
    if keyword:
        conditions.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        keyword_pattern = f"%{keyword}%"
        parameters.extend((keyword_pattern, keyword_pattern, keyword_pattern))
    if location:
        conditions.append("location LIKE ?")
        parameters.append(f"%{location}%")
    query = "SELECT id, title, company, location, description, salary FROM jobs"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.row_factory = sqlite3.Row
        jobs = connection.execute(query, parameters).fetchall()
    return jobs

def validated_job_fields(values):
    fields = {field: values.get(field, "") for field in JOB_FIELDS}
    if not all(isinstance(value, str) and value.strip() for value in fields.values()):
        return None
    return {field: value.strip() for field, value in fields.items()}

def insert_job(fields) -> int:
    with closing(sqlite3.connect(DATABASE)) as connection:
        cursor = connection.execute(
            "INSERT INTO jobs (title, company, location, description, salary) VALUES (?, ?, ?, ?, ?)",
            (fields["title"], fields["company"], fields["location"], fields["description"], fields["salary"]),
        )
        connection.commit()
        return cursor.lastrowid

@app.route("/")
def home():
    keyword = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    jobs = search_jobs(keyword, location)
    return render_template("index.html", jobs=jobs, keyword=keyword, location=location, total_jobs=len(search_jobs()))

@app.route("/add", methods=["GET", "POST"])
def add_job():
    if request.method == "POST":
        fields = validated_job_fields(request.form)
        if fields is None:
            return render_template("add.html", error="Please complete every field.", form_data=request.form), 400
        insert_job(fields)
        return redirect(url_for("home"))
    return render_template("add.html", form_data={})

@app.route("/jobs/<int:job_id>")
def job_detail(job_id: int):
    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.row_factory = sqlite3.Row
        job = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job is None: abort(404)
    return render_template("job.html", job=job)

@app.route("/api/jobs", methods=["GET", "POST"])
def jobs_api():
    if request.method == "GET":
        jobs = search_jobs(request.args.get("q", "").strip(), request.args.get("location", "").strip())
        return jsonify([dict(job) for job in jobs])
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict): return jsonify({"error": "JSON object required"}), 400
    fields = validated_job_fields(payload)
    if fields is None: return jsonify({"error": "All fields required"}), 400
    job_id = insert_job(fields)
    return jsonify({"id": job_id, **fields}), 201

if __name__ == "__main__":
    init_db()
    print(" * JobConnect Running on http://127.0.0.1:5000/")
    # FIXED: Connection Refused fix
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)