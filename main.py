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
	db_url='mysql+pymysql://root:Evcat807@DESKTOP-HVDKJP2:3306/project3'
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
		# Users
		cur.execute("""
		CREATE TABLE IF NOT EXISTS users (
			User_ID VARCHAR(36) PRIMARY KEY,
			username VARCHAR(255) UNIQUE NOT NULL,
			password_hash VARCHAR(128) NOT NULL,
			salt VARCHAR(36) NOT NULL,
			is_admin TINYINT(1) DEFAULT 0
		) ENGINE=InnoDB;
		""")

		# Courses
		cur.execute("""
		CREATE TABLE IF NOT EXISTS courses (
			Course_ID VARCHAR(36) PRIMARY KEY,
			Course_code VARCHAR(255) UNIQUE NOT NULL,
			title VARCHAR(255) NOT NULL,
			department VARCHAR(255) NULL
		) ENGINE=InnoDB;
		""")

		# Sections
		cur.execute("""
		CREATE TABLE IF NOT EXISTS sections (
			Section_ID VARCHAR(36) PRIMARY KEY,
			Course_ID VARCHAR(36) NULL,
			term_code VARCHAR(64) NULL,
			section_number VARCHAR(64) NULL,
			instructor_name VARCHAR(255) NULL,
			FOREIGN KEY (Course_ID) REFERENCES courses(Course_ID) ON DELETE SET NULL
		) ENGINE=InnoDB;
		""")

		# Source integration
		cur.execute("""
		CREATE TABLE IF NOT EXISTS source_integration (
			Source_ID VARCHAR(36) PRIMARY KEY,
			provider VARCHAR(255) NULL,
			status VARCHAR(64) NULL
		) ENGINE=InnoDB;
		""")

		# Calendars
		cur.execute("""
		CREATE TABLE IF NOT EXISTS calendars (
			Cal_ID VARCHAR(36) PRIMARY KEY,
			name VARCHAR(255) NOT NULL,
			visibility VARCHAR(64) NULL,
			color VARCHAR(64) NULL,
			User_ID VARCHAR(36) NULL,
			FOREIGN KEY (User_ID) REFERENCES users(User_ID) ON DELETE SET NULL
		) ENGINE=InnoDB;
		""")

		# Events (base)
		cur.execute("""
		CREATE TABLE IF NOT EXISTS events (
			Event_ID VARCHAR(36) PRIMARY KEY,
			title VARCHAR(255) NOT NULL,
			start_dt DATETIME NULL,
			end_dt DATETIME NULL,
			status VARCHAR(64) NULL,
			priority VARCHAR(64) NULL,
			User_ID VARCHAR(36) NULL,
			Course_ID VARCHAR(36) NULL,
			Section_ID VARCHAR(36) NULL,
			Source_ID VARCHAR(36) NULL,
			Cal_ID VARCHAR(36) NULL,
			FOREIGN KEY (User_ID) REFERENCES users(User_ID) ON DELETE SET NULL,
			FOREIGN KEY (Course_ID) REFERENCES courses(Course_ID) ON DELETE SET NULL,
			FOREIGN KEY (Section_ID) REFERENCES sections(Section_ID) ON DELETE SET NULL,
			FOREIGN KEY (Source_ID) REFERENCES source_integration(Source_ID) ON DELETE SET NULL,
			FOREIGN KEY (Cal_ID) REFERENCES calendars(Cal_ID) ON DELETE SET NULL
		) ENGINE=InnoDB;
		""")

		# AcademicEvent (subtype of Event)
		cur.execute("""
		CREATE TABLE IF NOT EXISTS academic_events (
			Event_ID VARCHAR(36) PRIMARY KEY,
			due_dt DATETIME NULL,
			academic_type VARCHAR(128) NULL,
			FOREIGN KEY (Event_ID) REFERENCES events(Event_ID) ON DELETE CASCADE
		) ENGINE=InnoDB;
		""")

		# PersonalEvent (subtype of Event)
		cur.execute("""
		CREATE TABLE IF NOT EXISTS personal_events (
			Event_ID VARCHAR(36) PRIMARY KEY,
			privacy VARCHAR(64) NULL,
			FOREIGN KEY (Event_ID) REFERENCES events(Event_ID) ON DELETE CASCADE
		) ENGINE=InnoDB;
		""")

		# Reminders
		cur.execute("""
		CREATE TABLE IF NOT EXISTS reminders (
			Reminder_ID VARCHAR(36) PRIMARY KEY,
			Event_ID VARCHAR(36) NOT NULL,
			offset_minutes INT NULL,
			method VARCHAR(64) NULL,
			FOREIGN KEY (Event_ID) REFERENCES events(Event_ID) ON DELETE CASCADE
		) ENGINE=InnoDB;
		""")

		# Tags and association
		cur.execute("""
		CREATE TABLE IF NOT EXISTS tags (
			Tag_ID VARCHAR(36) PRIMARY KEY,
			name VARCHAR(255) NOT NULL
		) ENGINE=InnoDB;
		""")

		cur.execute("""
		CREATE TABLE IF NOT EXISTS event_tags (
			Event_ID VARCHAR(36) NOT NULL,
			Tag_ID VARCHAR(36) NOT NULL,
			PRIMARY KEY (Event_ID, Tag_ID),
			FOREIGN KEY (Event_ID) REFERENCES events(Event_ID) ON DELETE CASCADE,
			FOREIGN KEY (Tag_ID) REFERENCES tags(Tag_ID) ON DELETE CASCADE
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
			cur.execute("INSERT INTO users (User_ID, username, password_hash, salt, is_admin) VALUES (%s,%s,%s,%s,%s)", (uid, username, hash_password(password, salt), salt, int(is_admin)))
			conn.commit()
			print(f"Created user {username} (User_ID={uid})")
		except Exception as e:
			conn.rollback()
			print("Failed to create user:", e)


def delete_user(conn, current_user: Optional[dict] = None):
	if current_user and not current_user.get("is_admin"):
		print("Admin privileges required")
		return
	username = input("Username to delete: ").strip()
	with conn.cursor() as cur:
		cur.execute("SELECT User_ID FROM users WHERE username=%s", (username,))
		row = cur.fetchone()
		if not row:
			print("User not found")
			return
		try:
			cur.execute("DELETE FROM users WHERE User_ID=%s", (row["User_ID"],))
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
				cur.execute("UPDATE users SET username=%s WHERE User_ID=%s", (new_username, user["User_ID"]))
			if change_pw:
				new_pw = input("New password: ")
				salt = gen_id()
				cur.execute("UPDATE users SET password_hash=%s, salt=%s WHERE User_ID=%s", (hash_password(new_pw, salt), salt, user["User_ID"]))
			if admin_input:
				cur.execute("UPDATE users SET is_admin=%s WHERE User_ID=%s", (int(admin_input.startswith("y")), user["User_ID"]))
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
			cur.execute(
				"INSERT INTO events (Event_ID, User_ID, title, start_dt, end_dt, status, priority) VALUES (%s,%s,%s,%s,%s,%s,%s)",
				(eid, current_user["User_ID"], title, parse_dt(start), parse_dt(end), status, priority),
			)
			# Also create a PersonalEvent row (subtype) with privacy
			cur.execute("INSERT INTO personal_events (Event_ID, privacy) VALUES (%s,%s)", (eid, None))
			conn.commit()
			print(f"Event created (Event_ID={eid})")
	except Exception as e:
		conn.rollback()
		print("Failed to create event:", e)


def delete_event(conn, current_user: Optional[dict] = None):
	eid = input("Event id to delete: ").strip()
	try:
		with conn.cursor() as cur:
			cur.execute("SELECT * FROM events WHERE Event_ID=%s", (eid,))
			ev = cur.fetchone()
			if ev:
				if current_user and not current_user.get("is_admin") and ev["User_ID"] != current_user.get("User_ID"):
					print("Cannot delete others' events")
					return
				cur.execute("DELETE FROM events WHERE Event_ID=%s", (eid,))
				conn.commit()
				print("Event deleted")
				return
			cur.execute("SELECT * FROM academic_events WHERE Event_ID=%s", (eid,))
			ae = cur.fetchone()
			if ae:
				cur.execute("DELETE FROM academic_events WHERE Event_ID=%s", (eid,))
				conn.commit()
				print("Academic event deleted")
				return
			print("Event not found")
	except Exception as e:
		conn.rollback()
		print("Failed to delete event:", e)


def import_canvas_data(conn):
	print("Canvas API URL format: https://your-canvas-instance.instructure.com/api/v1/courses")
	url = input("Canvas API URL: ").strip()
	token = input("Canvas API token (get from Account > Settings > Approved Integrations): ").strip()
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
				department = c.get("department")
				cur.execute("SELECT Course_ID FROM courses WHERE Course_code=%s", (canvas_id,))
				row = cur.fetchone()
				if row:
					course_id = row["Course_ID"]
				else:
					course_id = gen_id()
					cur.execute("INSERT INTO courses (Course_ID, Course_code, title, department) VALUES (%s,%s,%s,%s)", (course_id, canvas_id, name, department))
					print(f"Added course {name} (Course_code={canvas_id})")
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
					start_dt = parse_dt_field(e.get("start")) or parse_dt_field(e.get("start_at"))
					end_dt = parse_dt_field(e.get("end")) or parse_dt_field(e.get("end_at"))
					# create a base Event, then an AcademicEvent subtype row
					event_id = gen_id()
					cur.execute(
						"INSERT INTO events (Event_ID, title, start_dt, end_dt, status, priority, Course_ID) VALUES (%s,%s,%s,%s,%s,%s,%s)",
						(event_id, title, start_dt, end_dt, None, None, course_id),
					)
					due_dt = parse_dt_field(e.get("due")) or parse_dt_field(e.get("due_at")) or parse_dt_field(e.get("due_dt"))
					academic_type = e.get("academic_type") or e.get("type")
					cur.execute("INSERT INTO academic_events (Event_ID, due_dt, academic_type) VALUES (%s,%s,%s)", (event_id, due_dt, academic_type))
			conn.commit()
	except Exception as e:
		conn.rollback()
		print("Failed to import canvas data:", e)


def list_users(conn):
	with conn.cursor() as cur:
		cur.execute("SELECT User_ID, username, is_admin FROM users")
		for u in cur.fetchall():
			print(f"{u['User_ID']}\t{u['username']}\tadmin={bool(u['is_admin'])}")


def list_events(conn, current_user: Optional[dict] = None):
	print("-- Personal Events --")
	with conn.cursor() as cur:
		if current_user and not current_user.get("is_admin"):
			cur.execute("SELECT * FROM events WHERE User_ID=%s", (current_user["User_ID"],))
		else:
			cur.execute("SELECT * FROM events")
		for e in cur.fetchall():
			print(f"{e['Event_ID']}\t{e['title']}\t{e['start_dt']}\t{e['end_dt']}\towner={e.get('User_ID')}")
		print("-- Academic Events --")
		cur.execute("SELECT ae.Event_ID, ae.due_dt, ae.academic_type, e.title, e.Course_ID FROM academic_events ae JOIN events e ON ae.Event_ID = e.Event_ID")
		for ae in cur.fetchall():
			print(f"{ae['Event_ID']}\t{ae['title'] if 'title' in ae else ''}\t{ae.get('due_dt')}\t{ae.get('academic_type')}\tcourse_id={ae.get('Course_ID')}")


def main():
	print("Canvas API URL format: https://your-canvas-instance.instructure.com/api/v1/courses")
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




