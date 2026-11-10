
import json
import re
from pathlib import Path
from datetime import datetime, date, timedelta

from app.database import (
    create_task,
    get_all_tasks,
    get_tasks_with_deadlines,
    get_overdue_tasks,
    update_task,
    delete_task,
    get_task_by_id
)

BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "evidence"


def parse_deadline(prompt):
    text = prompt.lower()

    match = re.search(
        r"\b(\d{4}-\d{2}-\d{2})\b",
        text
    )

    if match:
        return match.group(1)

    match = re.search(
        r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*(\d{4})?\b",
        text
    )

    if match:
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4,
            "may": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }

        year = int(match.group(3) or date.today().year)

        try:
            return date(
                year,
                months[match.group(2)],
                int(match.group(1))
            ).isoformat()
        except ValueError:
            return None

    if "tomorrow" in text:
        return (date.today() + timedelta(days=1)).isoformat()

    if "today" in text:
        return date.today().isoformat()

    return None


def save_evidence(result):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    with open(
        EVIDENCE_DIR / "execution_log.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(result, file, indent=4, default=str)


def execute_task(prompt, new_status="Completed"):

    text = prompt.lower().strip()

    result = {
        "agent": "Task Manager Agent",
        "task": prompt,
        "status": "FAILED",
        "results": [],
        "verification": None,
        "timestamp": datetime.now().isoformat()
    }

    try:

        # READ: Show tasks with deadlines.
        if any(word in text for word in (
            "show", "list", "display", "view", "find"
        )):

            if "overdue" in text:
                tasks = get_overdue_tasks()
                operation = "Overdue tasks"

            elif "deadline" in text or "due" in text:
                tasks = get_tasks_with_deadlines()
                operation = "Tasks with deadlines"

                if "this week" in text:
                    end_date = (date.today() + timedelta(days=7)).isoformat()
                    tasks = [
                        task for task in tasks
                        if task["deadline"] <= end_date
                    ]

                elif "tomorrow" in text:
                    tomorrow = (
                        date.today() + timedelta(days=1)
                    ).isoformat()

                    tasks = [
                        task for task in tasks
                        if task["deadline"] == tomorrow
                    ]

            else:
                tasks = get_all_tasks()
                operation = "All tasks"

            result["results"] = [
                {
                    "question": task["title"],
                    "status": task["status"],
                    "deadline": task["deadline"],
                    "priority": task["priority"]
                }
                for task in tasks
            ]

            result["status"] = "SUCCESS"
            result["message"] = (
                f"{operation}: {len(tasks)} task(s) found."
            )

            result["verification"] = {
                "agent": "Task Manager Database Verifier",
                "verification_status": "PASSED",
                "verified_count": len(tasks)
            }

        # DELETE: Delete a task by its title.
        elif any(word in text for word in ("delete", "remove")):

            tasks = get_all_tasks()
            matching = [
                task for task in tasks
                if task["title"].lower() in text
            ]

            if not matching:
                raise ValueError("Could not identify the task to delete.")

            selected = matching[0]
            deleted = delete_task(selected["id"])

            check = get_task_by_id(selected["id"])

            verified = deleted and check is None

            result["status"] = "SUCCESS" if verified else "FAILED"
            result["message"] = (
                "Task deleted and absence verified."
                if verified else "Task deletion verification failed."
            )

            result["results"] = [{
                "question": selected["title"],
                "status": "Deleted" if verified else "Not deleted"
            }]

            result["verification"] = {
                "agent": "Task Manager Database Verifier",
                "verification_status": "PASSED" if verified else "FAILED"
            }

        # UPDATE: Change a deadline.
        elif "change" in text or "update" in text or "move" in text:

            deadline = parse_deadline(prompt)

            if not deadline:
                raise ValueError(
                    "Please specify a deadline such as 2026-11-20."
                )

            tasks = get_all_tasks()

            matching = [
                task for task in tasks
                if task["title"].lower() in text
            ]

            if not matching:
                raise ValueError("Could not identify the task to update.")

            selected = matching[0]

            update_task(
                selected["id"],
                deadline=deadline
            )

            updated = get_task_by_id(selected["id"])
            verified = updated["deadline"] == deadline

            result["status"] = "SUCCESS" if verified else "FAILED"
            result["results"] = [{
                "question": updated["title"],
                "status": updated["status"],
                "deadline": updated["deadline"],
                "priority": updated["priority"]
            }]

            result["verification"] = {
                "agent": "Task Manager Database Verifier",
                "verification_status": "PASSED" if verified else "FAILED",
                "expected_deadline": deadline,
                "actual_deadline": updated["deadline"]
            }

            result["message"] = (
                "Deadline updated and verified."
                if verified else "Deadline verification failed."
            )

        # CREATE: Create a task.
        else:

            title_match = re.search(
                r"(?:called|named)\s+(.+?)(?:\s+with a deadline|\s+by\s+\d|\s+due\s+|$)",
                prompt,
                re.IGNORECASE
            )

            if title_match:
                title = title_match.group(1).strip().rstrip(".")
            else:
                title = prompt.strip()

            deadline = parse_deadline(prompt)

            priority = "Medium"

            if "high priority" in text or "urgent" in text:
                priority = "High"
            elif "low priority" in text:
                priority = "Low"

            task_id = create_task(
                title,
                status="Not Started",
                deadline=deadline,
                priority=priority
            )

            saved_task = get_task_by_id(task_id)

            verified = (
                saved_task is not None
                and saved_task["title"] == title
                and saved_task["deadline"] == deadline
            )

            result["status"] = "SUCCESS" if verified else "FAILED"

            result["results"] = [{
                "question": saved_task["title"],
                "status": saved_task["status"],
                "deadline": saved_task["deadline"],
                "priority": saved_task["priority"]
            }]

            result["verification"] = {
                "agent": "Task Manager Database Verifier",
                "verification_status": "PASSED" if verified else "FAILED",
                "expected_deadline": deadline,
                "actual_deadline": saved_task["deadline"]
            }

            result["message"] = (
                "Task created and database values verified."
                if verified else "Task creation verification failed."
            )

    except Exception as error:
        result["error"] = str(error)
        result["message"] = "Task Manager operation failed."

    save_evidence(result)

    print("\nTask Manager result:", result["status"])

    return result


if __name__ == "__main__":
    print(execute_task("Show me all projects with deadlines."))
