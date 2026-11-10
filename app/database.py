
import sqlite3
from pathlib import Path
from datetime import date

DATABASE_PATH = Path(__file__).resolve().parent.parent / "gym_anything.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Not Started',
            deadline TEXT,
            priority TEXT DEFAULT 'Medium'
        )
    """)

    # Migrate existing databases without deleting existing tasks.
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

    connection.commit()
    connection.close()


def create_task(
    title,
    status="Not Started",
    deadline=None,
    priority="Medium"
):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO tasks (title, status, deadline, priority)
        VALUES (?, ?, ?, ?)
        """,
        (title, status, deadline, priority)
    )

    task_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return task_id


def get_all_tasks():
    connection = get_connection()

    tasks = connection.execute(
        """
        SELECT id, title, status, deadline, priority
        FROM tasks
        ORDER BY
            CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
            deadline ASC,
            id ASC
        """
    ).fetchall()

    connection.close()
    return tasks


def get_task_by_id(task_id):
    connection = get_connection()

    task = connection.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    connection.close()
    return task


def update_task(
    task_id,
    title=None,
    status=None,
    deadline=None,
    priority=None
):
    connection = get_connection()

    current = connection.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    if current is None:
        connection.close()
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
    connection.close()
    return True


def delete_task(task_id):
    connection = get_connection()

    cursor = connection.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def get_tasks_with_deadlines():
    connection = get_connection()

    tasks = connection.execute(
        """
        SELECT * FROM tasks
        WHERE deadline IS NOT NULL
        ORDER BY deadline ASC
        """
    ).fetchall()

    connection.close()
    return tasks


def get_overdue_tasks():
    today = date.today().isoformat()

    connection = get_connection()

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

    connection.close()
    return tasks
