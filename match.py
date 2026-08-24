import sqlite3
from collections import defaultdict

from normalise import normalise_city, normalise_email, normalise_phone

conn = sqlite3.connect("people.db")
conn.row_factory = sqlite3.Row


def load_records(conn):
    records = {}

    for row in conn.execute(
        "SELECT row_id, full_name, email, phone_number, city FROM naukri_applicants"
    ):
        key = ("naukri_applicants", row["row_id"])
        records[key] = {
            "name": row["full_name"],
            "email": normalise_email(row["email"]),
            "phone": normalise_phone(row["phone_number"]),
            "city": normalise_city(row["city"]),
        }

    for row in conn.execute(
        "SELECT row_id, worker_name, email, location_ FROM gig_workers"
    ):
        key = ("gig_workers", row["row_id"])
        records[key] = {
            "name": row["worker_name"],
            "email": normalise_email(row["email"]),
            "phone": None,  # gig_workers has no phone column
            "city": normalise_city(row["location_"]),
        }

    for row in conn.execute(
        "SELECT row_id, name, phone, city FROM cbnexus"
    ):
        key = ("cbnexus", row["row_id"])
        records[key] = {
            "name": row["name"],
            "email": None,  # cbnexus has no email column
            "phone": normalise_phone(row["phone"]),
            "city": normalise_city(row["city"]),
        }

    return records


# --- union-find ---

def find(parent, x):
    if parent[x] != x:
        parent[x] = find(parent, parent[x])
    return parent[x]


def union(parent, x, y):
    root_x, root_y = find(parent, x), find(parent, y)
    if root_x != root_y:
        parent[root_x] = root_y


def build_clusters(records):
    parent = {key: key for key in records}

    email_to_rows = defaultdict(list)
    phone_to_rows = defaultdict(list)
    for key, rec in records.items():
        if rec["email"]:
            email_to_rows[rec["email"]].append(key)
        if rec["phone"]:
            phone_to_rows[rec["phone"]].append(key)

    for rows in email_to_rows.values():
        for other in rows[1:]:
            union(parent, rows[0], other)

    for rows in phone_to_rows.values():
        for other in rows[1:]:
            union(parent, rows[0], other)

    clusters = defaultdict(list)
    for key in records:
        root = find(parent, key)
        clusters[root].append(key)

    return clusters


# Which source wins when two matched records disagree on a field.
# naukri_applicants is richest (has both email and phone), so it goes first.
SOURCE_PRIORITY = ["naukri_applicants", "gig_workers", "cbnexus"]


def materialize(conn, records, clusters):
    conn.execute("DELETE FROM person_sources")
    conn.execute("DELETE FROM people")

    for members in clusters.values():
        # highest-priority source first, so the loop below picks its values first
        members_sorted = sorted(members, key=lambda m: SOURCE_PRIORITY.index(m[0]))

        full_name = email = phone = city = None
        for m in members_sorted:
            rec = records[m]
            full_name = full_name or rec["name"]
            email = email or rec["email"]
            phone = phone or rec["phone"]
            city = city or rec["city"]

        cur = conn.execute(
            "INSERT INTO people (full_name, email, phone, city) VALUES (?, ?, ?, ?)",
            (full_name, email, phone, city),
        )
        person_id = cur.lastrowid

        match_key = "email_or_phone" if len(members) > 1 else "single_source"
        for source_table, row_id in members:
            conn.execute(
                "INSERT INTO person_sources (person_id, source_table, source_row_id, match_key) "
                "VALUES (?, ?, ?, ?)",
                (person_id, source_table, row_id, match_key),
            )

    conn.commit()


if __name__ == "__main__":
    records = load_records(conn)
    clusters = build_clusters(records)

    multi_row_clusters = {root: members for root, members in clusters.items() if len(members) > 1}

    print(f"total raw rows: {len(records)}")
    print(f"total clusters (= unique people found): {len(clusters)}")
    print(f"clusters with more than 1 row: {len(multi_row_clusters)}")

    print("\n-- sample multi-row clusters --")
    for root, members in list(multi_row_clusters.items())[:10]:
        names = [records[m]["name"] for m in members]
        print(f"{names} -> {members}")

    materialize(conn, records, clusters)
    people_count = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    links_count = conn.execute("SELECT COUNT(*) FROM person_sources").fetchone()[0]
    print(f"\nmaterialized: {people_count} rows in people, {links_count} rows in person_sources")
