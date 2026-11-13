
from playwright.sync_api import sync_playwright

from app.database import get_user_profile, get_user_by_id
from agents.prompt_parser import parse_prompt
from agents.llm_question_understanding import understand_question
from agents.agent_session import request_user_answer, update_session
from verification.verifier import verify_form_results
from agents.agent_session import request_answer_approval
from agents.llm_question_understanding import (
    understand_question,
    generate_answer,
    solve_academic_mcq
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

    # Never use the database user ID as a USN.
    if any(keyword in question_lower for keyword in [
        "usn", "university seat number",
        "student number", "registration number",
        "registration id", "roll number"
    ]):
        return profile.get("usn") or None

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
            "department", "branch", "major", "section"
        ],
        "role": ["role", "position"],
        "education": ["education", "qualification", "degree"],
        "experience": ["experience", "work experience"],
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
            "year of study", "current year",
            "which year", "year are you in",
            "study year", "academic year"
        ],
        "additional_info": [
            "additional information", "anything else",
            "additional details"
        ]
    }

    for field, keywords in rules.items():
        if any(keyword in question_lower for keyword in keywords):
            return profile.get(field) or None

    # Ask the LLM only to identify an existing profile field.
    try:
        field = understand_question(question, profile)

        invalid_answers = {
            "user input required",
            "needs user input",
            "unknown",
            "none",
            "null",
            ""
        }

        if isinstance(field, str):
            field = field.strip().lower()

            if field in invalid_answers:
                return None

            if field in profile:
                answer = profile.get(field)

                if answer and str(answer).strip().lower() not in invalid_answers:
                    return answer

    except Exception as error:
        print("[PROFILE MATCH ERROR]", error)

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

    print("[USER INPUT] Waiting for dashboard answer:", question)

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

    def normalize(value):
        return " ".join(str(value).strip().lower().split())

    def get_option_text(option):
        text = option.get_attribute("aria-label")

        if not text:
            try:
                text = option.locator("xpath=..").inner_text()
            except Exception:
                text = option.inner_text()

        return text.strip()

    def find_matching_option(answer, options):
        answer_normalized = normalize(answer)

        for option, option_text in options:
            option_normalized = normalize(option_text)

            if answer_normalized == option_normalized:
                return option

        for option, option_text in options:
            option_normalized = normalize(option_text)

            if (
                answer_normalized in option_normalized
                or option_normalized in answer_normalized
            ):
                return option

        return None

    def save_result(question, answer, actual, status, decision):
        result = {
            "question": question,
            "answer": answer,
            "actual_value": actual,
            "status": status,
            "decision": decision
        }

        results.append(result)

        update_session(
            "results",
            results,
            user_id=user_id
        )

        print(
            f"\nQuestion: {question}"
            f"\nExpected: {answer}"
            f"\nActual: {actual}"
            f"\nStatus: {status}"
        )

    questions = page.get_by_role("listitem")

    print("Total question containers:", questions.count())

    for i in range(questions.count()):

        item = questions.nth(i)
        question_text = item.inner_text().strip()

        if not question_text:
            continue

        print("\nProcessing:", question_text)

        # --------------------------------
        # 1. TEXT INPUTS AND TEXTAREAS
        # --------------------------------

        textbox = item.locator(
            'input[type="text"], textarea, '
            'input[type="email"], input[type="number"]'
        )

        if textbox.count() == 1:

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
                        save_result(
                            question_text, "", None,
                            "Rejected", decision
                        )
                        continue

                else:
                    answer = get_missing_answer(
                        question_text, user_id
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
                        question_text, user_id
                    )
                    decision = "User Provided"

            if not answer:
                save_result(
                    question_text, "", None,
                    "Skipped", decision
                )
                continue

            answer = normalize_answer(answer)

            textbox.fill(answer)

            actual = textbox.input_value().strip()

            status = (
                "Verified"
                if normalize(actual) == normalize(answer)
                else "Verification Failed"
            )

            save_result(
                question_text, answer, actual,
                status, decision
            )

            continue

       
        # --------------------------------
        # 2. MULTIPLE CHOICE (RADIO)
        # --------------------------------

        
        radios = item.locator('[role="radio"]')

        if radios.count() > 0:

            options = [
                (radios.nth(j), get_option_text(radios.nth(j)))
                for j in range(radios.count())
            ]

            option_names = [name for _, name in options]

            print("\n[MCQ] Question:", question_text)
            print("[MCQ] Options:", option_names)

            # First check whether this is a personal profile question.
            answer = match_answer(question_text, profile)
            decision = "Profile Auto-filled"

            # Otherwise, ask the AI to solve the academic MCQ.
            if not answer:
                print("[MCQ] Sending question to AI solver...")

                answer = solve_academic_mcq(
                    question_text,
                    option_names
                )

                decision = "AI Academic MCQ"
                print("[MCQ] AI answer:", repr(answer))

            if not answer:
                print("[MCQ] AI could not solve this question.")

                user_question = (
                    question_text
                    + "\nAvailable options: "
                    + ", ".join(option_names)
                )

                answer = get_missing_answer(user_question, user_id)
                decision = "User Provided"

            if not answer:
                save_result(
                    question_text, "", None,
                    "Skipped", decision
                )
                continue

            # Match the answer against the actual radio options.
            answer_normalized = normalize(answer).casefold()

            selected = None

            for option, option_name in options:
                option_normalized = normalize(option_name).casefold()

                if (
                    answer_normalized == option_normalized
                    or (
                        len(answer_normalized) > 10
                        and answer_normalized in option_normalized
                    )
                    or (
                        len(option_normalized) > 10
                        and option_normalized in answer_normalized
                    )
                ):
                    selected = option
                    break

            if selected is None:
                print("[MCQ] No matching radio option found.")

                save_result(
                    question_text,
                    answer,
                    None,
                    "Option Not Found",
                    decision
                )
                continue

            try:
                selected.click()
                selected.page.wait_for_timeout(500)

                actual_value = (
                    get_option_text(selected)
                    if selected.get_attribute("aria-checked") == "true"
                    else None
                )

                status = (
                    "Verified"
                    if actual_value is not None
                    and normalize(actual_value).casefold()
                    == normalize(get_option_text(selected)).casefold()
                    else "Verification Failed"
                )

                print("[MCQ] Selected:", actual_value)
                print("[MCQ] Status:", status)

                save_result(
                    question_text,
                    answer,
                    actual_value,
                    status,
                    decision
                )

            except Exception as e:
                print("[MCQ] Selection error:", str(e))

                save_result(
                    question_text,
                    answer,
                    None,
                    "Selection Failed",
                    decision
                )

            continue


        # --------------------------------
        # 3. CHECKBOXES (MULTIPLE SELECT)
        # --------------------------------

        checkboxes = item.locator('[role="checkbox"]')

        if checkboxes.count() > 0:

            options = [
                (checkboxes.nth(j), get_option_text(checkboxes.nth(j)))
                for j in range(checkboxes.count())
            ]

            option_names = [name for _, name in options]

            answer = match_answer(
                question_text, profile
            )

            decision = "Profile Auto-filled"

            if not answer:

                user_question = (
                    question_text
                    + "\nAvailable options (you may select multiple): "
                    + ", ".join(option_names)
                )

                answer = get_missing_answer(
                    user_question, user_id
                )

                decision = "User Provided"

            if not answer:
                save_result(
                    question_text, "", None,
                    "Skipped", decision
                )
                continue

            if isinstance(answer, str):
                selected_answers = [
                    value.strip()
                    for value in answer.split(",")
                    if value.strip()
                ]
            else:
                selected_answers = list(answer)

            selected_names = []

            for selected_answer in selected_answers:

                selected = find_matching_option(
                    selected_answer, options
                )

                if selected:
                    if selected.get_attribute("aria-checked") != "true":
                        selected.click()

                    selected_names.append(
                        get_option_text(selected)
                    )

            actual = [
                name for option, name in options
                if option.get_attribute("aria-checked") == "true"
            ]

            status = (
                "Verified"
                if (
                    actual
                    and all(
                        normalize(name) in [
                            normalize(x) for x in actual
                        ]
                        for name in selected_names
                    )
                    and len(actual) == len(selected_names)
                )
                else "Verification Failed"
            )

            save_result(
                question_text,
                ", ".join(selected_names),
                ", ".join(actual),
                status,
                decision
            )

            continue

        # --------------------------------
        # 4. DROPDOWN QUESTIONS
        # --------------------------------

        dropdown = item.locator('[role="listbox"]')

        if dropdown.count() > 0:

            dropdown.click()

            page.wait_for_timeout(500)

            options = page.get_by_role("option")

            option_data = [
                (options.nth(j), options.nth(j).inner_text().strip())
                for j in range(options.count())
            ]

            option_names = [
                name for _, name in option_data
            ]

            answer = match_answer(
                question_text, profile
            )

            decision = "Profile Auto-filled"

            if not answer:

                user_question = (
                    question_text
                    + "\nAvailable options: "
                    + ", ".join(option_names)
                )

                answer = get_missing_answer(
                    user_question, user_id
                )

                decision = "User Provided"

            if not answer:
                page.keyboard.press("Escape")

                save_result(
                    question_text, "", None,
                    "Skipped", decision
                )
                continue

            selected = find_matching_option(
                answer, option_data
            )

            if selected:

                selected.click()

                actual = dropdown.get_attribute("aria-label")

                if not actual:
                    actual = dropdown.inner_text().strip()

                status = (
                    "Verified"
                    if normalize(actual) == normalize(
                        get_option_text(selected)
                    )
                    else "Verification Failed"
                )

                save_result(
                    question_text,
                    answer,
                    actual,
                    status,
                    decision
                )

            else:
                page.keyboard.press("Escape")

                save_result(
                    question_text, answer, None,
                    "Option Not Found", decision
                )

            continue

        print("Unsupported question type:", question_text)

        save_result(
            question_text, "", None,
            "Unsupported", "Not Processed"
        )

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
