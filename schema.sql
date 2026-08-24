--this file is a blueprint script to show about the database here--
--Recreating this from csv files mentioned.
CREATE TABLE naukri_applicants (
    row_id INTEGER PRIMARY KEY,
    full_name TEXT, email TEXT, phone_number TEXT, city TEXT,
    expierence TEXT, current_ctc TEXT, app_date TEXT, skills TEXT
);

CREATE TABLE gig_workers (
    row_id INTEGER PRIMARY KEY,
    email TEXT, worker_name TEXT, rate TEXT, location_ TEXT, status_ TEXT, skills_tags TEXT
);

CREATE TABLE cbnexus (
    row_id INTEGER PRIMARY KEY,
    name TEXT, phone TEXT, city TEXT, verified TEXT, projects_completed TEXT
);

-- Canonical identity: one row per real human, after matching.
CREATE TABLE people (
    person_id INTEGER PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    city TEXT,
    category TEXT
);

-- Crosswalk: which raw rows, from which source, resolved to which person.
CREATE TABLE person_sources (
    person_id INTEGER REFERENCES people(person_id),
    source_table TEXT,
    source_row_id INTEGER,
    match_key TEXT,
    PRIMARY KEY (source_table, source_row_id)
);