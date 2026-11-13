
import json
import csv
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "evidence"
RESULTS_DIR = BASE_DIR / "evaluation"


def load_evidence(filename):

    file_path = EVIDENCE_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Evidence file not found: {filename}"
        )

    with open(file_path, "r") as file:
        return json.load(file)


def evaluate_system():

    print("\n--- SYSTEM EVALUATION STARTED ---")

    # Load agent evidence
    creation = load_evidence("creation_log.json")
    audit = load_evidence("audit_log.json")
    execution = load_evidence("execution_log.json")
    verification = load_evidence("verification_log.json")

    # Calculate metrics
    execution_success = (
        execution["status"] == "SUCCESS"
    )

    verification_success = (
        verification["verification_status"] == "PASSED"
    )

    audit_success = (
        audit["status"] == "PASSED"
    )

    creation_success = (
        creation["status"] == "SUCCESS"
    )

    # Convert results into percentages
    metrics = {
        "Creation Success Rate": int(creation_success * 100),
        "Audit Pass Rate": int(audit_success * 100),
        "Execution Success Rate": int(execution_success * 100),
        "Verification Success Rate": int(verification_success * 100)
    }

    overall_success = all([
        creation_success,
        audit_success,
        execution_success,
        verification_success
    ])

    metrics["Overall Success Rate"] = int(
        overall_success * 100
    )

    # Display results
    print("\n--- EVALUATION RESULTS ---")

    for metric, value in metrics.items():
        print(f"{metric}: {value}%")

    # Save results as CSV
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    csv_file = RESULTS_DIR / "results.csv"

    with open(csv_file, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow(["Metric", "Score (%)"])

        for metric, value in metrics.items():
            writer.writerow([metric, value])

    print("\nResults saved to:", csv_file)

    return metrics


if __name__ == "__main__":
    evaluate_system()
