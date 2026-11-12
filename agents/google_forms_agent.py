
from playwright.sync_api import sync_playwright

from app.database import get_user_profile, get_user_by_id
from agents.prompt_parser import parse_prompt
from agents.llm_question_understanding import understand_question
from agents.agent_session import request_user_answer, update_session
from verification.verifier import verify_form_results
from agents.agent_session import request_answer_approval
from agents.llm_question_understanding import (
    understand_question,
    generate_answer
)

# --------------------------------------------------
# LOAD LOGGED-IN USER PROFILE
# --------------------------------------------------

def load_profile(user_id):

    user = get_user_by_id(user_id)
    saved_profile = get_user_profile(user_id)

    if not user:
        raise ValueError("User account not found.")

    profile = dict(saved_profile) if saved_profile else {}
    profile["full_name"] = user["full_name"]

    return profile


# --------------------------------------------------
# MATCH FORM QUESTION WITH PROFILE
# --------------------------------------------------

def match_answer(question, profile):
    question_lower = question.lower().strip()

    rules = {
        "full_name": [
            "full name", "your name", "what is your name"
        ],
        "personal_email": [
            "personal email", "personal e-mail", "email address"
        ],
        "work_email": [
            "college email", "university email",
            "institutional email", "work email"
        ],
        "phone": [
            "phone", "mobile number", "contact number"
        ],
        "institution": [
            "college name", "university name",
            "institution name", "name of institution"
        ],
        "department": [
            "department", "branch", "major"
        ],
        "role": [
            "role", "position"
        ],
        "education": [
            "education", "qualification", "degree"
        ],
        "experience": [
            "experience", "work experience"
        ],
        "skills": [
            "skills", "programming languages", "technical skills"
        ],
        "interests": [
            "list your interests", "what are your interests",
            "hobbies", "areas of interest"
        ],
        "languages": [
            "languages known", "which languages",
            "languages you speak"
        ],
        "year_of_study": [
            "year of study",
            "current year",
            "which year",
            "year are you in",
            "study year",
            "academic year"
        ],
        "additional_info": [
            "additional information", "anything else",
            "additional details"
        ]
    }

    for field, keywords in rules.items():
        if any(keyword in question_lower for keyword in keywords):
            answer = profile.get(field)
            if answer:
                return answer
    if any(keyword in question_lower for keyword in [
    "year of study",
    "current year",
    "which year",
    "year are you in",
    "study year",
    "academic year"
]):
        return profile.get("year_of_study") or None
    # Use the LLM only to identify a relevant saved profile field.
    field = understand_question(question, profile)

    if field and field in profile:
        return profile.get(field)

    return None


# --------------------------------------------------
# NORMALIZE ANSWERS
# --------------------------------------------------

def normalize_answer(answer):

    if isinstance(answer, list):
        return ", ".join(map(str, answer))

    return str(answer).strip()


# --------------------------------------------------
# ASK USER TO APPROVE, EDIT OR REJECT
# --------------------------------------------------


def get_approved_answer(question, suggested_answer, user_id):

    suggestion = normalize_answer(suggested_answer)

    print(f"Waiting for approval: {question}")
    print(f"Suggested answer: {suggestion}")

    answer = request_answer_approval(
        question,
        suggestion,
        user_id=user_id
    )

    if not answer:
        return None, "Rejected"

    return answer, "Approved or Edited"


# --------------------------------------------------
# ASK USER FOR MISSING PROFILE INFORMATION
# --------------------------------------------------

def get_missing_answer(question, user_id):

    prompt = (
        "The Google Form contains a question that could not "
        "be answered using your saved profile:\n\n"
        f"{question}\n\n"
        "Please provide your answer.\n"
        "Type SKIP if you want to leave this field empty."
    )

    answer = request_user_answer(
        prompt,
        user_id=user_id
    )

    if not answer:
        return None

    if answer.strip().lower() in ("skip", "reject"):
        return None

    return answer.strip()


# --------------------------------------------------
# INSPECT GOOGLE FORM
# --------------------------------------------------

def inspect_and_match(page, profile):
    print("Questions inspected. Starting form filling...")

    questions = page.locator('[role="listitem"]')

    print("\n===== FORM FIELD INSPECTION =====")

    for i in range(questions.count()):

        question = questions.nth(i)
        question_text = question.inner_text().strip()

        answer = match_answer(question_text, profile)

        print("\nQuestion:", question_text)
        print(
            "Suggested answer:",
            answer if answer is not None else "User input required"
        )

        controls = question.locator(
            'input, textarea, [role="textbox"], '
            '[role="radio"], [role="checkbox"], '
            '[role="listbox"], [role="option"]'
        )

        print("Detected controls:", controls.count())


# --------------------------------------------------
# FILL TEXT FIELDS WITH USER APPROVAL
# --------------------------------------------------


def fill_text_fields(page, profile, user_id):
    results = []

    open_ended_phrases = [
        "why are you interested",
        "why do you want",
        "describe yourself",
        "tell us about yourself",
        "what motivates you",
        "how do you",
        "explain why",
        "what interests you",
        "describe your"
    ]

    questions = page.get_by_role("listitem")

    print("Total question containers:", questions.count())

    for i in range(questions.count()):
        item = questions.nth(i)
        question_text = item.inner_text().strip()

        textbox = item.locator(
            'input[type="text"], textarea, input[type="email"], input[type="number"]'
        )

        if textbox.count() != 1:
            print("Skipping unsupported question:", question_text)
            continue

        print("Processing question:", question_text)

        is_open_ended = any(
            phrase in question_text.lower()
            for phrase in open_ended_phrases
        )

        answer = None
        decision = ""

        if is_open_ended:
            suggested_answer = generate_answer(
                question_text,
                profile
            )

            if suggested_answer:
                answer, decision = get_approved_answer(
                    question_text,
                    suggested_answer,
                    user_id
                )

                if not answer:
                    results.append({
                        "question": question_text,
                        "answer": "",
                        "actual_value": None,
                        "status": "Rejected",
                        "decision": decision
                    })
                    continue
            else:
                answer = get_missing_answer(
                    question_text,
                    user_id
                )
                decision = "User Provided"

        else:
            answer = match_answer(
                question_text,
                profile
            )

            if answer:
                decision = "Profile Auto-filled"
            else:
                answer = get_missing_answer(
                    question_text,
                    user_id
                )
                decision = "User Provided"

        if not answer:
            results.append({
                "question": question_text,
                "answer": "",
                "actual_value": None,
                "status": "Skipped",
                "decision": decision
            })
            continue

        answer = normalize_answer(answer)

        textbox.fill(answer)

        actual_value = textbox.input_value().strip()

        if actual_value == answer.strip():
            status = "Verified"
        else:
            status = "Verification Failed"

        result = {
            "question": question_text,
            "answer": answer,
            "actual_value": actual_value,
            "status": status,
            "decision": decision
        }

        results.append(result)

        update_session(
            "results",
            results,
            user_id=user_id
        )

        print(f"Question: {question_text}")
        print(f"Expected: {answer}")
        print(f"Actual: {actual_value}")
        print(f"Status: {status}")

    return results

# --------------------------------------------------
# MAIN GOOGLE FORMS AGENT
# --------------------------------------------------

def execute_agent(form_url, user_prompt, user_id):

    if not form_url.startswith(
        "https://docs.google.com/forms/"
    ):
        raise ValueError("Invalid Google Forms URL")

    if user_id is None:
        raise ValueError("A logged-in user ID is required.")

    # Retrieve this user's profile only.
    profile = load_profile(user_id)

    profile = parse_prompt(user_prompt, profile)

    print("\n===== GOOGLE FORMS AGENT STARTED =====")
    print("User ID:", user_id)
    print("Profile loaded for:", profile.get("full_name"))

    update_session(
        "status", "running", user_id=user_id
    )

    update_session(
        "results", [], user_id=user_id
    )

    update_session(
        "verification", None, user_id=user_id
    )

    update_session(
        "message", "Opening Google Form.", user_id=user_id
    )

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

            # Step 1: Inspect questions.
            inspect_and_match(page, profile)

            # Step 2: Ask the user to approve answers.
            results = fill_text_fields(
                page,
                profile,
                user_id
            )

            # Step 3: Independently verify filled fields.
            verification = verify_form_results(results)
            print("\n===== DEBUG VERIFICATION =====")
            for item in results:
                print(item)

            print("\n===== VERIFIER REPORT =====")
            print(verification)

            # Step 4: Prepare report.
            verified_count = sum(
                1 for result in results
                if result.get("status") == "Verified"
            )

            rejected_count = sum(
                1 for result in results
                if result.get("status") == "Rejected by user"
            )

            message = (
                f"Form processing completed. "
                f"Verified fields: {verified_count}. "
                f"Rejected fields: {rejected_count}. "
                "Please review the form and submit manually."
            )

            final_report = {
                "title": page.title(),
                "results": results,
                "verification": verification,
                "message": message
            }

            # Step 5: Update this user's session.
            update_session(
                "results",
                results,
                user_id=user_id
            )

            update_session(
                "verification",
                verification,
                user_id=user_id
            )

            update_session(
                "message",
                message,
                user_id=user_id
            )

            update_session(
                "status",
                "completed",
                user_id=user_id
            )

            print("\n===== FINAL AGENT REPORT =====")
            print(message)

            print(
                "\nReview the answers and submit the form manually."
            )

            # Never automatically submit the form.
            page.wait_for_event("close")

            return final_report

        except Exception as error:

            update_session(
                "status",
                "failed",
                user_id=user_id
            )

            update_session(
                "message",
                str(error),
                user_id=user_id
            )

            print("Google Forms Agent error:", error)

            raise

        finally:

            browser.close()


if __name__ == "__main__":

    print(
        "Google Forms Agent must be started "
        "through the authenticated Gym-Anything dashboard."
    )
