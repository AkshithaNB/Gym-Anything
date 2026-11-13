
import json
import re
from pathlib import Path
from datetime import datetime
from verification.shopping_verifier import verify_shopping_task

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BASE_DIR / "evidence"

SHOPPING_URL = "http://127.0.0.1:5001"



def parse_shopping_prompt(prompt):
    text = prompt.lower()

    # Search all shoes, including sneakers and sports shoes
    search = "shoes"

    color = ""
    size = ""
    max_price = ""
    sort = "price_low"

    if "black" in text:
        color = "Black"
    elif "white" in text:
        color = "White"

    size_match = re.search(r"size\s*(\d+)", text)
    if size_match:
        size = size_match.group(1)

    price_match = re.search(
        r"(?:under|below|less than)\s*₹?\s*(\d+)",
        text
    )

    if price_match:
        max_price = price_match.group(1)

    if "high to low" in text or "highest price" in text:
        sort = "price_high"

    return {
        "search": search,
        "color": color,
        "size": size,
        "max_price": max_price,
        "sort": sort
    }


def execute_shopping_task(prompt):

    print("\n===== SHOPPING EXECUTION STARTED =====")

    result = {
        "agent": "Shopping Execution Agent",
        "task": prompt,
        "status": "FAILED",
        "timestamp": datetime.now().isoformat()
    }

    try:
        filters = parse_shopping_prompt(prompt)

        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(headless=False)
            page = browser.new_page()

            # Step 1: Open shopping environment
            page.goto(SHOPPING_URL)
            page.wait_for_load_state("networkidle")

            print("Shopping environment opened.")

            # Step 2: Enter search and filters
            page.locator("#search").fill(filters["search"])

            if filters["color"]:
                page.locator("#color").select_option(
                    label=filters["color"]
                )

            if filters["size"]:
                page.locator("#size").select_option(
                    value=filters["size"]
                )

            if filters["max_price"]:
                page.locator("#max_price").fill(
                    filters["max_price"]
                )

            page.locator("#sort").select_option(
                value=filters["sort"]
            )

            page.get_by_role(
                "button",
                name="Apply Filters"
            ).click()

            page.wait_for_timeout(500)

            print("Search and filters applied.")

            # Step 3: Read matching products
            product_cards = page.locator(".product")

            if product_cards.count() == 0:
                raise Exception("No matching products found.")

            matching_products = []

            for i in range(product_cards.count()):
                card = product_cards.nth(i)

                name = card.locator("h3").inner_text()
                price_text = card.locator(".price").inner_text()

                price = int(
                    re.sub(r"[^0-9]", "", price_text)
                )

                matching_products.append({
                    "name": name,
                    "price": price,
                    "index": i
                })

            # Step 4: Select the cheapest product
            selected = min(
                matching_products,
                key=lambda product: product["price"]
            )

            print("Selected product:", selected["name"])
            print("Price:", selected["price"])

            # Step 5: Add selected product to cart
            product_cards.nth(
                selected["index"]
            ).get_by_role(
                "button",
                name="Add to Cart"
            ).click()

            page.wait_for_timeout(500)

            # Step 6: Read cart from the website
            page.reload()
            page.wait_for_load_state("networkidle")

            cart_response = page.request.get(
                SHOPPING_URL + "/api/cart"
            )

            cart = cart_response.json()

            verified = any(
                item["name"] == selected["name"]
                and item["price"] == selected["price"]
                for item in cart
            )

            if not verified:
                raise Exception(
                    "Selected product was not found in cart."
                )

            result.update({
                "status": "SUCCESS",
                "filters": filters,
                "selected_product": selected,
                "cart_verified": True,
                "cart_items": cart
            })

            print("Execution agent cart check PASSED.")

            browser.close()

            # Independent verification
            verification = verify_shopping_task(result)

            result["verification"] = verification

            if verification["verification_status"] != "PASSED":
                result["status"] = "FAILED"
                result["error"] = "Independent verification failed."
            else:
                result["status"] = "SUCCESS"
    except Exception as error:
            result["error"] = str(error)
            print("Shopping execution failed:", error)

    # Step 7: Save execution evidence
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    evidence_file = (
        EVIDENCE_DIR / "shopping_execution_log.json"
    )

    with open(evidence_file, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)

    print("\nShopping result:", result["status"])
    print("Evidence saved:", evidence_file)

    return result


if __name__ == "__main__":

    execute_shopping_task(
        "Find black sneakers under 2000, "
        "size 7, sort by price, and add the cheapest product to cart."
    )

