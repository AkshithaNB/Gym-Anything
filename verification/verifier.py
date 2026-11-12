
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


def normalize_value(value):
    """Convert values into a consistent format for comparison."""

    if value is None:
        return None

    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)

    return " ".join(str(value).strip().split()).casefold()


def verify_task(task_title, expected_status="Completed"):
    print("\n--- INDEPENDENT VERIFIER STARTED ---")

    tasks = get_all_tasks()

    matching_tasks = [
        task for task in tasks
        if task[1] == task_title
    ]

    actual_status = matching_tasks[-1][2] if matching_tasks else None

    verification_status = (
        "PASSED"
        if actual_status == expected_status
        else "FAILED"
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
    field_details = []

    for item in results:

        question = item.get("question", "Unknown question")
        expected = item.get("answer")
        actual = item.get("actual_value")

        expected_normalized = normalize_value(expected)
        actual_normalized = normalize_value(actual)

        is_verified = (
            item.get("status") == "Verified"
            and expected_normalized is not None
            and actual_normalized is not None
            and expected_normalized == actual_normalized
        )

        if is_verified:
            verified_fields.append(item)
            field_status = "PASSED"
        else:
            failed_fields.append(item)
            field_status = "FAILED"

        field_details.append({
            "question": question,
            "expected_answer": expected,
            "actual_answer": actual,
            "field_status": field_status,
            "original_status": item.get("status"),
            "reason": (
                "Values match"
                if is_verified
                else "Missing answer, missing actual value, "
                     "status not Verified, or values do not match"
            )
        })

    total_fields = len(results)

    verification_status = (
        "PASSED"
        if total_fields > 0
        and len(verified_fields) == total_fields
        else "FAILED"
    )

    report = {
        "agent": "Independent Verifier",
        "task": "Google Form Completion",
        "total_fields": total_fields,
        "verified_fields": len(verified_fields),
        "failed_fields": len(failed_fields),
        "verification_status": verification_status,
        "field_details": field_details,
        "timestamp": datetime.now().isoformat()
    }

    save_evidence(report)

    print("\nVerification Summary")
    print("--------------------")
    print("Total fields:", total_fields)
    print("Verified fields:", len(verified_fields))
    print("Failed fields:", len(failed_fields))
    print("Verification:", verification_status)

    for field in field_details:
        print(
            f"\nQuestion: {field['question']}"
            f"\nExpected: {field['expected_answer']}"
            f"\nActual: {field['actual_answer']}"
            f"\nStatus: {field['field_status']}"
            f"\nReason: {field['reason']}"
        )

    return report


if __name__ == "__main__":
    verify_task(
        "Complete Gym-Anything implementation",
        "Completed"
    )
