# Project-Phase-III

Simple CLI calendar app using SQLite + SQLAlchemy.

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

This project defaults to SQLite when no DB URL is provided. To use MySQL, create a MySQL database and user, then provide a SQLAlchemy-compatible URL via the `DATABASE_URL` or `DB_URL` environment variable.

Example URL (using PyMySQL):

```
mysql+pymysql://dbuser:dbpassword@dbhost:3306/dbname
```

Set the environment variable on PowerShell before running:

```powershell
$env:DATABASE_URL = 'mysql+pymysql://dbuser:dbpassword@dbhost:3306/dbname'
python main.py
```

If you prefer to keep using SQLite for quick testing, the default will create `app.db` in the working directory.

Run

```powershell
python main.py
```

Notes

- First create an admin user with `add_user` (you can run `add_user` even while not logged in; the prompt will not block but ideally start by creating an admin).
- `import_canvas` expects a URL that returns JSON in one of these forms:
  - A list of course objects: `[ {"id":..., "name":..., "events":[...]}, ... ]`
  - An object with `courses` key: `{"courses": [ ... ]}`
- Passwords are hashed with SHA256 + random salt stored per-user. For production, replace with a stronger KDF (bcrypt/argon2).
- Deleting a `Course` will cascade-delete related `AcademicEvent` rows; deleting a `User` will cascade-delete their personal `Event` rows.
