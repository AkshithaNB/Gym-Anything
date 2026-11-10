

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from agents.prompt_parser import parse_prompt
from agents.llm_question_understanding import understand_question
from agents.agent_session import request_user_answer, update_session
from verification.verifier import verify_form_results


BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_FILE = BASE_DIR / "user_profile" / "profile.json"


def load_profile():
    with open(PROFILE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def match_answer(question, profile):
    question_lower = question.lower().strip()

    # Step 1: Fast rule-based matching
    rules = {
        "full_name": ["full name", "your name"],
        "email": ["email", "email address"],
        "college": ["college", "university", "institution"],
        "department": ["department", "branch", "major"],
        "year_of_study": ["year of study", "current year"],
        "skills": ["skills", "programming languages", "technical skills"],
        "ai_interest": ["interest in ai", "why are you interested in ai"]
    }

    for field, keywords in rules.items():
        if any(keyword in question_lower for keyword in keywords):
            return profile.get(field)

    # Step 2: Use Llama 3 for unfamiliar questions
    field = understand_question(question, profile)

    if field is None:
        return None

    return profile.get(field)


def inspect_and_match(page, profile):
    questions = page.locator('[role="listitem"]')

    print("\n===== FORM FIELD INSPECTION =====")

    for i in range(questions.count()):
        question = questions.nth(i)
        question_text = question.inner_text().strip()

        answer = match_answer(question_text, profile)

        print("\nQuestion:", question_text)
        print(
            "Matched answer:",
            answer if answer is not None else "User input required"
        )

        controls = question.locator(
            'input, textarea, [role="textbox"], '
            '[role="radio"], [role="checkbox"], '
            '[role="listbox"], [role="option"]'
        )

        print("Detected controls:", controls.count())


def fill_text_fields(page, profile):
    questions = page.locator('[role="listitem"]')
    results = []

    print("\n===== FILLING TEXT FIELDS =====")

    for i in range(questions.count()):
        question = questions.nth(i)
        question_text = question.inner_text().strip()

        answer = match_answer(question_text, profile)

        # Ask user when no saved answer is available
        if answer is None:
            print("\n===== NEW QUESTION DETECTED =====")
            print("Question:", question_text)

            answer = request_user_answer(question_text)

            if not answer:
                print("No answer received. Skipping.")

                results.append({
                    "question": question_text,
                    "status": "Needs user input"
                })
                continue

        if isinstance(answer, list):
            answer = ", ".join(answer)

        textbox = question.locator(
            'input[type="text"], textarea'
        )

        # Fill only supported text fields
        if textbox.count() == 1:
            textbox.fill(str(answer))

            actual_value = textbox.input_value()

            if actual_value == str(answer):
                status = "Verified"
                print("Verification SUCCESS:", question_text)
            else:
                status = "Verification FAILED"
                print("Verification FAILED:", question_text)

            results.append({
                "question": question_text,
                "answer": str(answer),
                "actual_value": actual_value,
                "status": status
            })

        else:
            print("Unsupported or ambiguous control:", question_text)

            results.append({
                "question": question_text,
                "answer": str(answer),
                "status": "Unsupported control"
            })

    return results


def execute_agent(form_url, user_prompt):
    if not form_url.startswith("https://docs.google.com/forms/"):
        raise ValueError("Invalid Google Forms URL")

    profile = load_profile()
    profile = parse_prompt(user_prompt, profile)

    print("\n===== AGENT EXECUTION STARTED =====")

    update_session("status", "running")
    update_session("results", [])
    update_session("verification", None)
    update_session("message", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        try:
            page = browser.new_page()

            page.goto(
                form_url,
                wait_until="domcontentloaded"
            )

            page.wait_for_timeout(3000)

            print("Form opened:", page.title())

            # Step 1: Inspect the form
            inspect_and_match(page, profile)

            # Step 2: Fill supported fields
            results = fill_text_fields(page, profile)

            # Step 3: Independently verify results
            verification = verify_form_results(results)

            # Step 4: Prepare final report
            if verification["verification_status"] == "PASSED":
                message = (
                    "Form filled and verified successfully. "
                    "Please review and submit manually."
                )
            else:
                message = (
                    "Some fields could not be verified. "
                    "Please review the form."
                )

            final_report = {
                "title": page.title(),
                "results": results,
                "verification": verification,
                "message": message
            }

            # Step 5: Update dashboard
            update_session("results", results)
            update_session("verification", verification)
            update_session("message", message)
            update_session("status", "completed")

            print("\nForm is ready for human review.")
            print("Review the answers and submit manually if everything is correct.")

                # Keep the browser open until the user closes the form window
            page.wait_for_event("close")



            print("\n===== FINAL AGENT REPORT =====")
            print(message)

            return final_report

        except Exception as error:
            update_session("status", "failed")
            update_session("message", str(error))
            print("Agent error:", error)
            raise

        finally:
            browser.close()


def start_agent():
    print("\n===== GOOGLE FORMS AGENT =====")

    profile = load_profile()

    print("Profile loaded:", profile.get("full_name"))

    form_url = input("\nEnter Google Form URL: ").strip()

    if not form_url.startswith("https://docs.google.com/forms/"):
        print("Invalid Google Forms URL.")
        return

    user_prompt = input("\nEnter task instructions: ")

    report = execute_agent(form_url, user_prompt)

    print("\nFinal report:")
    print(json.dumps(report, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    start_agent()
