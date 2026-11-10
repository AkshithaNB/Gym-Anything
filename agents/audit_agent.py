
import json
import sqlite3
from pathlib import Path
from datetime import datetime

from app.database import get_connection, get_all_tasks


BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "evidence"


def audit_environment():

    print("\n--- AUDIT AGENT STARTED ---")

    checks = {}

    # Check 1: Database accessibility
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        checks["database_accessible"] = True
        checks["tasks_table_exists"] = "tasks" in tables

        connection.close()

    except Exception as error:
        checks["database_accessible"] = False
        checks["tasks_table_exists"] = False
        print("Database error:", error)

    # Check 2: Validate task records
    try:
        tasks = get_all_tasks()

        invalid_tasks = [
            task for task in tasks
            if not task[1] or not task[2]
        ]

        checks["tasks_valid"] = len(invalid_tasks) == 0
        checks["total_tasks"] = len(tasks)

    except Exception as error:
        checks["tasks_valid"] = False
        checks["total_tasks"] = 0
        print("Task validation error:", error)

    # Check 3: Creation evidence
    creation_log = EVIDENCE_DIR / "creation_log.json"

    checks["creation_evidence_exists"] = creation_log.exists()

    # Overall audit result
    audit_passed = all([
        checks.get("database_accessible", False),
        checks.get("tasks_table_exists", False),
        checks.get("tasks_valid", False),
        checks.get("creation_evidence_exists", False)
    ])

    result = {
        "agent": "Audit Agent",
        "status": "PASSED" if audit_passed else "FAILED",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }

    # Save audit evidence
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    with open(EVIDENCE_DIR / "audit_log.json", "w") as file:
        json.dump(result, file, indent=4)

    print("\n--- AUDIT RESULTS ---")

    for check, value in checks.items():
        print(f"{check}: {value}")

    print("\nFinal Audit Status:",
          result["status"])

    return result


if __name__ == "__main__":
    audit_environment()
