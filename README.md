# Project-Phase-III

Simple CLI calendar app using MySQL (raw PyMySQL driver).

Setup

1. Create a virtual environment and activate it (Windows PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

Database (MySQL)

This project uses MySQL via the `pymysql` driver. Provide connection information using either a single `DATABASE_URL` (recommended) or individual environment variables.

- Example `DATABASE_URL`:

```
mysql+pymysql://dbuser:dbpassword@dbhost:3306/dbname
```

- Or set individual variables (PowerShell):

```powershell
$env:DB_HOST='dbhost'
$env:DB_USER='dbuser'
$env:DB_PASS='dbpassword'
$env:DB_NAME='dbname'
$env:DB_PORT='3306'
```

Run the CLI

```powershell
python main.py
```

The app will connect to the DB and create the schema automatically if tables are missing.

Canvas import

Use the `import_canvas` command inside the CLI. The importer accepts JSON in either of these shapes:
- `{ "courses": [ ... ] }`
- `[ ... ]` (a list of course objects)

Each course object may include `id` (stored as `Course_code`), `name` (-> `title`), `department`, and an `events` or `assignments` array. The importer creates base `events` rows and `academic_events` subtype rows for course events.

Database schema (summary)

The current schema follows the ER diagram you provided. Key tables and columns:
- `users` (User_ID, username, password_hash, salt, is_admin)
- `courses` (Course_ID, Course_code, title, department)
- `sections` (Section_ID, Course_ID, term_code, section_number, instructor_name)
- `source_integration` (Source_ID, provider, status)
- `calendars` (Cal_ID, name, visibility, color, User_ID)
- `events` (Event_ID, title, start_dt, end_dt, status, priority, User_ID, Course_ID, Section_ID, Source_ID, Cal_ID)
- `academic_events` (Event_ID, due_dt, academic_type) — FK -> `events(Event_ID)` (ON DELETE CASCADE)
- `personal_events` (Event_ID, privacy) — FK -> `events(Event_ID)` (ON DELETE CASCADE)
- `reminders` (Reminder_ID, Event_ID, offset_minutes, method) — FK -> `events(Event_ID)` (ON DELETE CASCADE)
- `tags` (Tag_ID, name) and `event_tags` (Event_ID, Tag_ID)

Notes & recommendations

- Passwords are currently hashed with SHA-256 + per-user salt (keeps compatibility). For production, switch to `bcrypt` or `argon2` — I can update the code and `requirements.txt` for you.
- The code uses `ON DELETE CASCADE` for subtype and reminder tables, and `ON DELETE SET NULL` for optional relationships (so deleting a user or course won't cascade-delete unrelated data unintentionally).
- If you have existing data in the old schema, ask me to generate a migration script — I can create a one-off script to map old tables/columns into the new schema.

Next steps I can help with

- Replace SHA-256 hashing with `bcrypt` and update `requirements.txt`.
- Add a one-time migration script to move data from the previous schema to the new schema.
- Add example seed data or unit tests to exercise the main flows.

If you want one of those, tell me which and I'll implement it.
