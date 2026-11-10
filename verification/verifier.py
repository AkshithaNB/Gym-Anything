
import json
from pathlib import Path
from datetime import datetime

from app.database import get_all_tasks

BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "evidence"


def save_evidence(result):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    evidence_file = EVIDENCE_DIR / "verification_log.json"

    with open(evidence_file, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    print("Evidence saved:", evidence_file)


def verify_task(task_title, expected_status="Completed"):
    print("\n--- INDEPENDENT VERIFIER STARTED ---")

    tasks = get_all_tasks()

    matching_tasks = [
        task for task in tasks
        if task[1] == task_title
    ]

    actual_status = matching_tasks[-1][2] if matching_tasks else None

    verification_status = (
        "PASSED" if actual_status == expected_status else "FAILED"
    )

    result = {
        "agent": "Independent Verifier",
        "task": task_title,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "verification_status": verification_status,
        "timestamp": datetime.now().isoformat()
    }

    save_evidence(result)

    print("Verification:", verification_status)

    return result


def verify_form_results(results):
    print("\n--- GOOGLE FORM VERIFICATION STARTED ---")

    verified_fields = []
    failed_fields = []

    for item in results:
        expected = item.get("answer")
        actual = item.get("actual_value")

        if (
            item.get("status") == "Verified"
            and expected is not None
            and expected == actual
        ):
            verified_fields.append(item)
        else:
            failed_fields.append(item)

    total_fields = len(results)

    verification_status = (
        "PASSED"
        if total_fields > 0 and len(verified_fields) == total_fields
        else "FAILED"
    )

    report = {
        "agent": "Independent Verifier",
        "task": "Google Form Completion",
        "total_fields": total_fields,
        "verified_fields": len(verified_fields),
        "failed_fields": len(failed_fields),
        "verification_status": verification_status,
        "timestamp": datetime.now().isoformat()
    }

    save_evidence(report)

    print("Total fields:", total_fields)
    print("Verified fields:", len(verified_fields))
    print("Failed fields:", len(failed_fields))
    print("Verification:", verification_status)

    return report


if __name__ == "__main__":
    verify_task(
        "Complete Gym-Anything implementation",
        "Completed"
    )
