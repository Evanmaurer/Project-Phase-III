"""
Raw MySQL implementation using PyMySQL. This file replaces the previouss raw SQL queries against a
MySQL database. Provide DB connection information via `DATABASE_URL`
(e.g. `mysql+pymysql://user:pass@host:3306/dbname`) or via `DB_HOST`,
`DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT` environment variables.
"""

import os
import uuid
import hashlib
import requests
from datetime import datetime
from typing import Optional
import pymysql
from urllib.parse import urlparse


def gen_id() -> str:
	return str(uuid.uuid4())


def hash_password(password: str, salt: str) -> str:
	return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def parse_database_url(db_url: str):
	"""Parse a SQLAlchemy-style URL like mysql+pymysql://user:pass@host:3306/dbname"""
	p = urlparse(db_url)
	return {
		"user": p.username,
		"password": p.password,
		"host": p.hostname,
		"port": p.port or 3306,
		"db": p.path.lstrip("/"),
	}


def get_mysql_conn():
	# Prefer full URL
	db_url = os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
	cfg = None
	if db_url:
		if not db_url.startswith("mysql"):
			print("DATABASE_URL provided but not a MySQL URL. Provide a MySQL URL like mysql+pymysql://user:pass@host:3306/dbname")
			raise SystemExit(1)
		cfg = parse_database_url(db_url)
	else:
		host = os.environ.get("DB_HOST")
		if not host:
			print("No MySQL configuration found. Set DATABASE_URL or DB_HOST/DB_USER/DB_PASS/DB_NAME/DB_PORT.")
			raise SystemExit(1)
		cfg = {
			"user": os.environ.get("DB_USER", "root"),
			"password": os.environ.get("DB_PASS", ""),
			"host": host,
			"port": int(os.environ.get("DB_PORT", "3306")),
			"db": os.environ.get("DB_NAME", "appdb"),
		}
	conn = pymysql.connect(host=cfg["host"], user=cfg["user"], password=cfg["password"], database=cfg["db"], port=cfg["port"], cursorclass=pymysql.cursors.DictCursor, autocommit=False)
	return conn


def init_db(conn):
	with conn.cursor() as cur:
		cur.execute("""
		CREATE TABLE IF NOT EXISTS users (
			id VARCHAR(36) PRIMARY KEY,
			username VARCHAR(255) UNIQUE NOT NULL,
			password_hash VARCHAR(128) NOT NULL,
			salt VARCHAR(36) NOT NULL,
			is_admin TINYINT(1) DEFAULT 0
		) ENGINE=InnoDB;
		""")
		cur.execute("""
		CREATE TABLE IF NOT EXISTS courses (
			id VARCHAR(36) PRIMARY KEY,
			canvas_id VARCHAR(255) UNIQUE NOT NULL,
			name VARCHAR(255) NOT NULL
		) ENGINE=InnoDB;
		""")
		cur.execute("""
		CREATE TABLE IF NOT EXISTS academic_events (
			id VARCHAR(36) PRIMARY KEY,
			course_id VARCHAR(36),
			title VARCHAR(255) NOT NULL,
			start_dt DATETIME NULL,
			end_dt DATETIME NULL,
			FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
		) ENGINE=InnoDB;
		""")
		cur.execute("""
		CREATE TABLE IF NOT EXISTS events (
			id VARCHAR(36) PRIMARY KEY,
			owner_id VARCHAR(36) NOT NULL,
			title VARCHAR(255) NOT NULL,
			start_dt DATETIME NULL,
			end_dt DATETIME NULL,
			status VARCHAR(64) NULL,
			priority VARCHAR(64) NULL,
			FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
		) ENGINE=InnoDB;
		""")
	conn.commit()


def login(conn) -> Optional[dict]:
	username = input("Username: ").strip()
	password = input("Password: ")
	with conn.cursor() as cur:
		cur.execute("SELECT * FROM users WHERE username=%s", (username,))
		user = cur.fetchone()
	if not user:
		print("Incorrect username and password")
		return None
	if hash_password(password, user["salt"]) == user["password_hash"]:
		print("Logged in")
		# convert is_admin
		user["is_admin"] = bool(user.get("is_admin"))
		return user
	else:
		print("Incorrect username and password")
		return None


def add_user(conn, current_user: Optional[dict] = None):
	if current_user and not current_user.get("is_admin"):
		print("Admin privileges required")
		return
	is_admin = input("Is admin? (y/N): ").lower().startswith("y")
	username = input("New username: ").strip()
	password = input("New password: ")
	salt = gen_id()
	uid = gen_id()
	with conn.cursor() as cur:
		try:
			cur.execute("INSERT INTO users (id, username, password_hash, salt, is_admin) VALUES (%s,%s,%s,%s,%s)", (uid, username, hash_password(password, salt), salt, int(is_admin)))
			conn.commit()
			print(f"Created user {username} (id={uid})")
		except Exception as e:
			conn.rollback()
			print("Failed to create user:", e)


def delete_user(conn, current_user: Optional[dict] = None):
	if current_user and not current_user.get("is_admin"):
		print("Admin privileges required")
		return
	username = input("Username to delete: ").strip()
	with conn.cursor() as cur:
		cur.execute("SELECT id FROM users WHERE username=%s", (username,))
		row = cur.fetchone()
		if not row:
			print("User not found")
			return
		try:
			cur.execute("DELETE FROM users WHERE id=%s", (row["id"],))
			conn.commit()
			print(f"Deleted user {username}")
		except Exception as e:
			conn.rollback()
			print("Failed to delete user:", e)


def modify_user(conn, current_user: Optional[dict] = None):
	if current_user and not current_user.get("is_admin"):
		print("Admin privileges required")
		return
	username = input("Username to modify: ").strip()
	with conn.cursor() as cur:
		cur.execute("SELECT * FROM users WHERE username=%s", (username,))
		user = cur.fetchone()
	if not user:
		print("User not found")
		return
	new_username = input(f"New username (leave blank to keep '{user['username']}'): ").strip()
	change_pw = input("Change password? (y/N): ").lower().startswith("y")
	admin_input = input(f"Is admin? (current={bool(user.get('is_admin'))}) (y/N): ").lower()
	try:
		with conn.cursor() as cur:
			if new_username:
				cur.execute("UPDATE users SET username=%s WHERE id=%s", (new_username, user["id"]))
			if change_pw:
				new_pw = input("New password: ")
				salt = gen_id()
				cur.execute("UPDATE users SET password_hash=%s, salt=%s WHERE id=%s", (hash_password(new_pw, salt), salt, user["id"]))
			if admin_input:
				cur.execute("UPDATE users SET is_admin=%s WHERE id=%s", (int(admin_input.startswith("y")), user["id"]))
			conn.commit()
			print("User updated")
	except Exception as e:
		conn.rollback()
		print("Failed to modify user:", e)


def add_personal_event(conn, current_user: dict):
	if not current_user:
		print("Must be logged in to add events")
		return
	title = input("Title: ").strip()
	start = input("Start datetime (YYYY-MM-DD HH:MM) or blank: ").strip()
	end = input("End datetime (YYYY-MM-DD HH:MM) or blank: ").strip()
	status = input("Status (optional): ").strip() or None
	priority = input("Priority (optional): ").strip() or None
	def parse_dt(val):
		if not val:
			return None
		try:
			return datetime.strptime(val, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
		except ValueError:
			print("Bad datetime format, storing NULL")
			return None
	eid = gen_id()
	try:
		with conn.cursor() as cur:
			cur.execute("INSERT INTO events (id, owner_id, title, start_dt, end_dt, status, priority) VALUES (%s,%s,%s,%s,%s,%s,%s)", (eid, current_user["id"], title, parse_dt(start), parse_dt(end), status, priority))
			conn.commit()
			print(f"Event created (id={eid})")
	except Exception as e:
		conn.rollback()
		print("Failed to create event:", e)


def delete_event(conn, current_user: Optional[dict] = None):
	eid = input("Event id to delete: ").strip()
	try:
		with conn.cursor() as cur:
			cur.execute("SELECT * FROM events WHERE id=%s", (eid,))
			ev = cur.fetchone()
			if ev:
				if current_user and not current_user.get("is_admin") and ev["owner_id"] != current_user.get("id"):
					print("Cannot delete others' events")
					return
				cur.execute("DELETE FROM events WHERE id=%s", (eid,))
				conn.commit()
				print("Event deleted")
				return
			cur.execute("SELECT * FROM academic_events WHERE id=%s", (eid,))
			ae = cur.fetchone()
			if ae:
				cur.execute("DELETE FROM academic_events WHERE id=%s", (eid,))
				conn.commit()
				print("Academic event deleted")
				return
			print("Event not found")
	except Exception as e:
		conn.rollback()
		print("Failed to delete event:", e)


def import_canvas_data(conn):
	url = input("Canvas API URL (returning courses+events JSON): ").strip()
	token = input("Optional API token (leave blank if none): ").strip()
	headers = {}
	if token:
		headers["Authorization"] = f"Bearer {token}"
	try:
		resp = requests.get(url, headers=headers, timeout=10)
		resp.raise_for_status()
		data = resp.json()
	except Exception as e:
		print("Failed to fetch or parse JSON:", e)
		return

	courses = []
	if isinstance(data, dict) and "courses" in data:
		courses = data["courses"]
	elif isinstance(data, list):
		courses = data
	else:
		print("Unexpected JSON shape; expecting a list or {'courses': [...]}")
		return

	try:
		with conn.cursor() as cur:
			for c in courses:
				canvas_id = str(c.get("id"))
				name = c.get("name") or c.get("course_name") or f"Course {canvas_id}"
				cur.execute("SELECT id FROM courses WHERE canvas_id=%s", (canvas_id,))
				row = cur.fetchone()
				if row:
					course_id = row["id"]
				else:
					course_id = gen_id()
					cur.execute("INSERT INTO courses (id, canvas_id, name) VALUES (%s,%s,%s)", (course_id, canvas_id, name))
					print(f"Added course {name} (canvas_id={canvas_id})")
				events = c.get("events") or c.get("assignments") or []
				for e in events:
					title = e.get("title") or e.get("name") or "Untitled"
					def parse_dt_field(val):
						if not val:
							return None
						for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
							try:
								return datetime.strptime(val, fmt).strftime("%Y-%m-%d %H:%M:%S")
							except Exception:
								continue
						return None
					start_dt = parse_dt_field(e.get("start")) or parse_dt_field(e.get("start_at")) or parse_dt_field(e.get("due_at"))
					end_dt = parse_dt_field(e.get("end")) or parse_dt_field(e.get("end_at"))
					aeid = gen_id()
					cur.execute("INSERT INTO academic_events (id, course_id, title, start_dt, end_dt) VALUES (%s,%s,%s,%s,%s)", (aeid, course_id, title, start_dt, end_dt))
			conn.commit()
	except Exception as e:
		conn.rollback()
		print("Failed to import canvas data:", e)


def list_users(conn):
	with conn.cursor() as cur:
		cur.execute("SELECT id, username, is_admin FROM users")
		for u in cur.fetchall():
			print(f"{u['id']}\t{u['username']}\tadmin={bool(u['is_admin'])}")


def list_events(conn, current_user: Optional[dict] = None):
	print("-- Personal Events --")
	with conn.cursor() as cur:
		if current_user and not current_user.get("is_admin"):
			cur.execute("SELECT * FROM events WHERE owner_id=%s", (current_user["id"],))
		else:
			cur.execute("SELECT * FROM events")
		for e in cur.fetchall():
			print(f"{e['id']}\t{e['title']}\t{e['start_dt']}\t{e['end_dt']}\towner={e['owner_id']}")
		print("-- Academic Events --")
		cur.execute("SELECT * FROM academic_events")
		for ae in cur.fetchall():
			print(f"{ae['id']}\t{ae['title']}\t{ae['start_dt']}\t{ae['end_dt']}\tcourse_id={ae['course_id']}")


def main():
	conn = get_mysql_conn()
	init_db(conn)
	current_user = None
	print("Simple Calendar CLI (MySQL raw driver)")
	while True:
		print("\nOptions: login, logout, add_user, del_user, mod_user, import_canvas, add_event, del_event, list, exit")
		cmd = input("cmd> ").strip().lower()
		if cmd == "login":
			current_user = login(conn)
		elif cmd == "logout":
			current_user = None
			print("Logged out")
		elif cmd == "add_user":
			add_user(conn, current_user)
		elif cmd == "del_user":
			delete_user(conn, current_user)
		elif cmd == "mod_user":
			modify_user(conn, current_user)
		elif cmd == "import_canvas":
			import_canvas_data(conn)
		elif cmd == "add_event":
			add_personal_event(conn, current_user)
		elif cmd == "del_event":
			delete_event(conn, current_user)
		elif cmd == "list":
			list_users(conn)
			list_events(conn, current_user)
		elif cmd == "exit":
			break
		else:
			print("Unknown command")


if __name__ == "__main__":
	main()




