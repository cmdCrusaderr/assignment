#The goal of this file to work on the csv provided
import csv
import os
import sqlite3

DB_PATH = "people.db"

# Rebuild the db fresh each run, so re-running the loader while you iterate
# doesn't hit "table already exists" errors.
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
with open("schema.sql") as f:
    conn.executescript(f.read())


def load_naukri(conn, path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                row["Full Name"], row["Email"], row["Phone"], row["City"],
                row["Experience (Years)"], row["Current CTC"], row["Applied Date"], row["Skills"],
            )
            for row in reader
        ]
    conn.executemany(
        "INSERT INTO naukri_applicants "
        "(full_name, email, phone_number, city, expierence, current_ctc, app_date, skills) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"naukri_applicants: inserted {len(rows)} rows")


def load_gig_workers(conn, path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        skipped = 0
        for row in reader:
            email = (row.get("email_id") or "").strip()
            if not email or "@" not in email:
                # catches the blank row and the shifted/malformed Isha Chopra row
                skipped += 1
                continue
            rows.append((
                email, row["worker_name"], row["rate"], row["location"], row["status"], row["skill_tags"],
            ))
    conn.executemany(
        "INSERT INTO gig_workers "
        "(email, worker_name, rate, location_, status_, skills_tags) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"gig_workers: inserted {len(rows)} rows, skipped {skipped}")


def load_cbnexus(conn, path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        skipped = 0
        for row in reader:
            if row["Name"] == "Name":
                # repeated header row embedded mid-file
                skipped += 1
                continue
            rows.append((
                row["Name"], row["Phone Number"], row["City"], row["Verified"], row["Projects Completed"],
            ))
    conn.executemany(
        "INSERT INTO cbnexus (name, phone, city, verified, projects_completed) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"cbnexus: inserted {len(rows)} rows, skipped {skipped}")


load_naukri(conn, "csv/source1_naukri_applicants.csv")
load_gig_workers(conn, "csv/source2_gig_workers.csv")
load_cbnexus(conn, "csv/source3_cbnexus_contacts.csv")

conn.close()
