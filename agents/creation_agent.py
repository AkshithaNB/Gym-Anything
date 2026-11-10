
import json
from pathlib import Path
from datetime import datetime

from app.database import (
    initialize_database,
    create_task,
    get_all_tasks
)


# Project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Evidence directory
EVIDENCE_DIR = BASE_DIR / "evidence"


def create_environment():

    print("\n--- CREATION AGENT STARTED ---")

    # Step 1: Initialize database
    initialize_database()

    print("Database initialized successfully.")

    # Step 2: Check existing tasks
    existing_tasks = get_all_tasks()

    # Step 3: Load tasks from JSON if database is empty
    if not existing_tasks:

        task_file = BASE_DIR / "tasks" / "task_definitions.json"

        with open(task_file, "r") as file:
            task_data = json.load(file)

        sample_tasks = task_data["tasks"]

        for task in sample_tasks:
            create_task(task["task_name"])

        print("Tasks loaded from JSON successfully.")

    else:
        print("Existing tasks found. Skipping task creation.")

    # Step 4: Get all tasks
    tasks = get_all_tasks()

    # Step 5: Create evidence directory
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # Step 6: Record creation evidence
    evidence = {
        "agent": "Creation Agent",
        "status": "SUCCESS",
        "total_tasks": len(tasks),
        "timestamp": datetime.now().isoformat()
    }

    evidence_file = EVIDENCE_DIR / "creation_log.json"

    with open(evidence_file, "w") as file:
        json.dump(evidence, file, indent=4)

    print("Environment creation completed.")
    print(f"Total tasks: {len(tasks)}")
    print(f"Evidence saved at: {evidence_file}")

    return evidence


if __name__ == "__main__":
    create_environment()
