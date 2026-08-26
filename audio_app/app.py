import os
import sqlite3
import sys
import uuid

from flask import Flask, g, jsonify, render_template, request

from audio_utils import extract_audio_metadata, infer_extension, transcode_to_wav

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)
from normalise import normalise_phone  # noqa: E402  (Task 1's normalisation, reused as-is)

DB_PATH = os.path.join(REPO_ROOT, "people.db")
AUDIO_DIR = os.path.join("static", "audio")

app = Flask(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audio_submissions (
    submission_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id          INTEGER NOT NULL REFERENCES people(person_id),
    name               TEXT NOT NULL,
    phone               TEXT NOT NULL,
    audio_filename       TEXT NOT NULL,
    original_filename     TEXT,
    content_type         TEXT,
    file_size_bytes       INTEGER,
    duration_sec         REAL,
    sample_rate_hz        INTEGER,
    bitrate_kbps         REAL,
    loudness_dbfs         REAL,
    quality_estimate      TEXT,
    quality_score         REAL,
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(CREATE_TABLE_SQL)
    conn.close()


def resolve_person(conn, name, normalised_phone):
    # Match Task 1's own matching rule: same normalised phone = same person.
    row = conn.execute(
        "SELECT person_id FROM people WHERE phone = ? LIMIT 1", (normalised_phone,)
    ).fetchone()
    if row:
        return row["person_id"], "phone"
    cur = conn.execute(
        "INSERT INTO people (full_name, email, phone, city) VALUES (?, NULL, ?, NULL)",
        (name, normalised_phone),
    )
    return cur.lastrowid, "single_source"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    return render_template("submit.html")


@app.route("/submit", methods=["POST"])
def submit():
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    file_storage = request.files.get("audio")

    if not name:
        return jsonify(status="error", message="Name is required"), 400
    if not phone:
        return jsonify(status="error", message="Phone number is required"), 400
    normalised_phone = normalise_phone(phone)
    if not normalised_phone:
        return jsonify(status="error", message="Phone number needs at least 10 digits"), 400
    if not file_storage or file_storage.filename == "":
        return jsonify(status="error", message="No audio recorded or uploaded"), 400

    token = uuid.uuid4().hex
    raw_ext = infer_extension(file_storage)
    raw_path = os.path.join(AUDIO_DIR, f"{token}_raw{raw_ext}")
    file_storage.save(raw_path)

    try:
        # Extracted from the original upload, before any transcoding, so
        # duration/sample-rate/bitrate/loudness reflect what was actually submitted.
        meta = extract_audio_metadata(raw_path)
    except Exception as exc:
        app.logger.warning("audio metadata extraction failed for %s: %s", raw_path, exc)
        meta = dict(
            duration_sec=None,
            sample_rate_hz=None,
            bitrate_kbps=None,
            loudness_dbfs=None,
            quality_estimate="unknown",
            quality_score=None,
            file_size_bytes=os.path.getsize(raw_path),
        )

    filename = f"{token}.wav"
    path = os.path.join(AUDIO_DIR, filename)
    try:
        transcode_to_wav(raw_path, path)
    except Exception:
        os.remove(raw_path)
        raise
    os.remove(raw_path)

    conn = get_db()
    try:
        with conn:
            person_id, match_key = resolve_person(conn, name, normalised_phone)
            cur = conn.execute(
                """INSERT INTO audio_submissions
                   (person_id, name, phone, audio_filename, original_filename, content_type,
                    file_size_bytes, duration_sec, sample_rate_hz, bitrate_kbps,
                    loudness_dbfs, quality_estimate, quality_score)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    person_id,
                    name,
                    phone,
                    filename,
                    file_storage.filename,
                    file_storage.mimetype,
                    meta["file_size_bytes"],
                    meta["duration_sec"],
                    meta["sample_rate_hz"],
                    meta["bitrate_kbps"],
                    meta["loudness_dbfs"],
                    meta["quality_estimate"],
                    meta["quality_score"],
                ),
            )
            submission_id = cur.lastrowid
            conn.execute(
                "INSERT INTO person_sources (person_id, source_table, source_row_id, match_key) "
                "VALUES (?, 'audio_app', ?, ?)",
                (person_id, submission_id, match_key),
            )
    except Exception:
        os.remove(path)
        raise

    return jsonify(status="ok", submission_id=submission_id, person_id=person_id), 201


@app.route("/submissions")
def submissions():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audio_submissions ORDER BY created_at DESC"
    ).fetchall()
    return render_template("submissions.html", rows=rows)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=8000)
