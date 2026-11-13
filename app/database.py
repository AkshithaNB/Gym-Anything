
import sqlite3
from pathlib import Path
from datetime import date


DATABASE_PATH = Path(__file__).resolve().parent.parent / "gym_anything.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    connection = get_connection()

    try:
        # User accounts
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Personal, academic and professional profiles
        connection.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        personal_email TEXT,
        work_email TEXT,
        phone TEXT,
        institution TEXT,
        department TEXT,
        role TEXT,
        education TEXT,
        year_of_study TEXT,
        experience TEXT,
        skills TEXT,
        interests TEXT,
        languages TEXT,
        additional_info TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE
    )
""")
        profile_columns = {
    row["name"]
    for row in connection.execute(
        "PRAGMA table_info(user_profiles)"
    ).fetchall()
}

        if "year_of_study" not in profile_columns:
                        connection.execute(
                            "ALTER TABLE user_profiles ADD COLUMN year_of_study TEXT"
                        )

        # Existing tasks table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Not Started',
                deadline TEXT,
                priority TEXT DEFAULT 'Medium',
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        # Migrate existing databases without deleting tasks.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(tasks)"
            ).fetchall()
        }

        if "deadline" not in columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN deadline TEXT"
            )

        if "priority" not in columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'Medium'"
            )

        if "user_id" not in columns:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
            )

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_user_id
            ON tasks(user_id)
        """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# --------------------------------------------------
# USER ACCOUNT FUNCTIONS
# --------------------------------------------------

def create_user(full_name, email, password_hash):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO users (full_name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (full_name.strip(), email.strip().lower(), password_hash)
        )

        user_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO user_profiles (
                user_id, personal_email
            )
            VALUES (?, ?)
            """,
            (user_id, email.strip().lower())
        )

        connection.commit()
        return user_id

    except sqlite3.IntegrityError:
        connection.rollback()
        raise ValueError("An account with this email already exists.")

    finally:
        connection.close()


def get_user_by_email(email):
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email.strip().lower(),)
        ).fetchone()
    finally:
        connection.close()


def get_user_by_id(user_id):
    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT id, full_name, email, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()
    finally:
        connection.close()


# --------------------------------------------------
# USER PROFILE FUNCTIONS
# --------------------------------------------------
PROFILE_FIELDS = [
    "personal_email",
    "work_email",
    "phone",
    "institution",
    "department",
    "role",
    "education",
    "year_of_study",
    "experience",
    "skills",
    "interests",
    "languages",
    "additional_info"
]

def get_user_profile(user_id):
    connection = get_connection()

    try:
        profile = connection.execute(
            """
            SELECT
                users.id,
                users.full_name,
                users.email,
                user_profiles.personal_email,
                user_profiles.work_email,
                user_profiles.phone,
                user_profiles.institution,
                user_profiles.department,
                user_profiles.role,
                user_profiles.education,
                user_profiles.experience,
                user_profiles.skills,
                user_profiles.interests,
                user_profiles.languages,
                user_profiles.additional_info,
                user_profiles.updated_at
            FROM users
            LEFT JOIN user_profiles
                ON users.id = user_profiles.user_id
            WHERE users.id = ?
            """,
            (user_id,)
        ).fetchone()

        return dict(profile) if profile else None

    finally:
        connection.close()



def update_user_profile(user_id, full_name=None, profile_data=None, **profile_fields):
    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if not user:
            raise ValueError("User account not found.")

        if full_name is not None:
            connection.execute(
                """
                UPDATE users
                SET full_name = ?
                WHERE id = ?
                """,
                (full_name.strip(), user_id)
            )

        # Support both dictionary and keyword arguments
        valid_data = {}

        if profile_data:
            valid_data.update(profile_data)

        valid_data.update(profile_fields)

        # Allow only fields defined in PROFILE_FIELDS
        valid_data = {
            key: value
            for key, value in valid_data.items()
            if key in PROFILE_FIELDS
        }

        current = connection.execute(
            """
            SELECT user_id
            FROM user_profiles
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not current:
            connection.execute(
                "INSERT INTO user_profiles (user_id) VALUES (?)",
                (user_id,)
            )

        if valid_data:
            assignments = ", ".join(
                f"{field} = ?" for field in valid_data
            )

            values = list(valid_data.values())

            connection.execute(
                f"""
                UPDATE user_profiles
                SET {assignments},
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                values + [user_id]
            )

        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()



# --------------------------------------------------
# TASK MANAGER FUNCTIONS
# --------------------------------------------------

def create_task(
    title,
    status="Not Started",
    deadline=None,
    priority="Medium",
    user_id=None
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO tasks (
                title, status, deadline, priority, user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, status, deadline, priority, user_id)
        )

        task_id = cursor.lastrowid
        connection.commit()
        return task_id

    finally:
        connection.close()


def get_all_tasks(user_id=None):
    connection = get_connection()

    try:
        if user_id is None:
            query = """
                SELECT id, title, status, deadline, priority, user_id
                FROM tasks
                ORDER BY
                    CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
                    deadline ASC,
                    id ASC
            """
            tasks = connection.execute(query).fetchall()
        else:
            tasks = connection.execute(
                """
                SELECT id, title, status, deadline, priority, user_id
                FROM tasks
                WHERE user_id = ?
                ORDER BY
                    CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
                    deadline ASC,
                    id ASC
                """,
                (user_id,)
            ).fetchall()

        return tasks

    finally:
        connection.close()


def get_task_by_id(task_id, user_id=None):
    connection = get_connection()

    try:
        if user_id is None:
            task = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            ).fetchone()
        else:
            task = connection.execute(
                """
                SELECT *
                FROM tasks
                WHERE id = ? AND user_id = ?
                """,
                (task_id, user_id)
            ).fetchone()

        return task

    finally:
        connection.close()


def update_task(
    task_id,
    title=None,
    status=None,
    deadline=None,
    priority=None,
    user_id=None
):
    connection = get_connection()

    try:
        if user_id is None:
            current = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            ).fetchone()
        else:
            current = connection.execute(
                """
                SELECT *
                FROM tasks
                WHERE id = ? AND user_id = ?
                """,
                (task_id, user_id)
            ).fetchone()

        if current is None:
            return False

        connection.execute(
            """
            UPDATE tasks
            SET title = ?,
                status = ?,
                deadline = ?,
                priority = ?
            WHERE id = ?
            """,
            (
                title if title is not None else current["title"],
                status if status is not None else current["status"],
                deadline if deadline is not None else current["deadline"],
                priority if priority is not None else current["priority"],
                task_id
            )
        )

        connection.commit()
        return True

    finally:
        connection.close()


def delete_task(task_id, user_id=None):
    connection = get_connection()

    try:
        if user_id is None:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,)
            )
        else:
            cursor = connection.execute(
                """
                DELETE FROM tasks
                WHERE id = ? AND user_id = ?
                """,
                (task_id, user_id)
            )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def get_tasks_with_deadlines(user_id=None):
    connection = get_connection()

    try:
        if user_id is None:
            tasks = connection.execute(
                """
                SELECT * FROM tasks
                WHERE deadline IS NOT NULL
                ORDER BY deadline ASC
                """
            ).fetchall()
        else:
            tasks = connection.execute(
                """
                SELECT * FROM tasks
                WHERE deadline IS NOT NULL
                  AND user_id = ?
                ORDER BY deadline ASC
                """,
                (user_id,)
            ).fetchall()

        return tasks

    finally:
        connection.close()


def get_overdue_tasks(user_id=None):
    today = date.today().isoformat()
    connection = get_connection()

    try:
        if user_id is None:
            tasks = connection.execute(
                """
                SELECT * FROM tasks
                WHERE deadline IS NOT NULL
                  AND deadline < ?
                  AND status != 'Completed'
                ORDER BY deadline ASC
                """,
                (today,)
            ).fetchall()
        else:
            tasks = connection.execute(
                """
                SELECT * FROM tasks
                WHERE deadline IS NOT NULL
                  AND deadline < ?
                  AND status != 'Completed'
                  AND user_id = ?
                ORDER BY deadline ASC
                """,
                (today, user_id)
            ).fetchall()

        return tasks

    finally:
        connection.close()
