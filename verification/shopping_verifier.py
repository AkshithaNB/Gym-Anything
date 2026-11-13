
import json
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen

BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "evidence"

SHOPPING_URL = "http://127.0.0.1:5001"


def verify_shopping_task(execution_result):

    print("\n===== INDEPENDENT SHOPPING VERIFIER =====")

    selected = execution_result.get("selected_product")

    verification_status = "FAILED"
    actual_cart = []

    try:
        if not selected:
            raise ValueError("No selected product in execution result.")

        # Independently retrieve the actual shopping cart
        with urlopen(SHOPPING_URL + "/api/cart", timeout=10) as response:
            actual_cart = json.loads(response.read().decode("utf-8"))

        # Compare actual cart with selected product
        matching_items = [
            item for item in actual_cart
            if (
                item.get("name") == selected.get("name")
                and item.get("price") == selected.get("price")
            )
        ]

        if matching_items:
            verification_status = "PASSED"

    except Exception as error:
        print("Verification error:", error)

    report = {
        "agent": "Independent Shopping Verifier",
        "task": execution_result.get("task"),
        "expected_product": selected,
        "actual_cart": actual_cart,
        "verification_status": verification_status,
        "timestamp": datetime.now().isoformat()
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    evidence_file = EVIDENCE_DIR / "shopping_verification_log.json"

    with open(evidence_file, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("Verification:", verification_status)
    print("Evidence saved:", evidence_file)

    return report


if __name__ == "__main__":
    print("Run the shopping execution agent first.")
