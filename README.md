# Assignment Submission

Three tasks: merge messy people data from 3 CSVs into one clean database
(Task 1), stand up a Supabase copy of that data for an n8n workflow
(Task 2), and a small audio collection app (Task 3).

## Setup

### Task 1 — merge/dedup pipeline

```bash
python3 script1.py     # rebuilds people.db, loads the 3 CSVs into raw tables
python3 match.py       # matches across sources, writes people + person_sources
```

### Task 2 — Supabase datasource

Run `schema.sql` then `ALTER TABLE people ADD COLUMN category TEXT;` in the
Supabase SQL editor, then run `supabase_migration.sql` to load the deduped
people rows. `sample_data/new_upload_demo.csv` is test data for checking
incremental matching still works.

### Task 3 — audio collection app

```bash
cd audio_app
brew install ffmpeg              # needed for audio metadata extraction
pip3 install -r requirements.txt
python3 app.py
```

Open `http://localhost:8000/` to submit a recording, `http://localhost:8000/submissions`
to view the list. (Runs on port 8000, not Flask's default 5000 — macOS's
AirPlay Receiver uses port 5000, see stuck log below.)

Submissions are matched against Task 1's `people` table by phone number and
saved into the same `people.db` — see [documentation/check_task1_db.txt](documentation/check_task1_db.txt)
for how to verify that yourself.

## Data issues report (Task 1)

- 102 raw rows across the 3 CSVs → 60 unique people after matching.
- No single ID field is common across all 3 sources, so matching is done
  on normalised email OR normalised phone (whichever a given source has).
- Bad rows handled during ingestion:
  - `gig_workers`: 1 fully blank row, and 1 shifted/malformed row (email
    field doesn't contain "@") — both skipped.
  - `cbnexus`: 1 repeated header row embedded mid-file (name == "Name") —
    skipped.
  - `naukri_applicants`: no bad rows, loaded as-is.
- 27 people were duplicated across 2-3 sources and correctly merged into
  one record each.
- Known limitation: a person appearing ONLY in `gig_workers` and `cbnexus`
  (no `naukri_applicants` row) can't be matched, since those two sources
  share no common field (`cbnexus` has no email, `gig_workers` has no
  phone). Left as separate records rather than force-merged on name alone
  (example: Manish Bhatia).

## Stuck log

**1. A recording would submit fine, but pressing play just said "Error."**
Nothing crashed — the file uploaded, saved, and showed up in the list with
its extracted duration/sample rate, but the audio player refused to play
it. I debug it. It ran `file` on the actual saved
file and found the bytes were "ISO Media, MP4 Base Media v5" even though
the file had been saved with a `.webm` extension — the browser had
actually recorded MP4/AAC audio (a format some browsers, like Safari,
use instead of WebM), but the app's code defaulted to labeling anything
that wasn't Ogg as `.webm`. So the server was telling the browser
"this is a webm file" while serving actual MP4 bytes, and the browser
correctly refused to play the mismatch. The fix that got picked wasn't to
just correct that one label — it was to stop trusting whatever format the
browser claims at all, and instead convert every submission to one fixed
format (WAV) on the server before saving it, so playback never depends on
guessing right.

**2. Whether the audio app should write into Task 1's database or its own.**
I first asked for the app's database to be completely separate from
Task 1's `people.db`, since I didn't want the audio app to touch the
existing pipeline at all. I built it that way — its own
`audio_app.db` file, no connection to `people`. Later I changed my mind
and asked for submissions to actually be saved into Task 1's database
instead.  rewrote it to write into `people.db` directly,
reusing the same phone-matching function (`normalise_phone`) Task 1
already uses for its own matching, so a submission either links to an
existing person or creates a new one the same way Task 1's pipeline does.
I verified this by submitting a test recording with an existing
person's phone number and confirming with `sqlite3` that it linked to
their real `person_id` in `people.db`, then a second test with a new
phone number and confirming a new person got created the same way.

**3. The app wouldn't load at `http://localhost:5000/` — just a bare 403.**
No error in the Flask logs at all, which was confusing since the server
said it was running. Claude Code checked the raw response headers with
`curl -v` and found `Server: AirTunes/870.14.1` in the reply — the
request wasn't even reaching Flask. Turned out macOS's AirPlay Receiver
listens on port 5000 by default and was intercepting the connection
first. Moved the app to port 8000 instead of trying to free up port 5000.
