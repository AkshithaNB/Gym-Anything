
import threading


DEFAULT_USER_ID = "default"

INITIAL_SESSION = {
    "status": "idle",
    "current_question": "",
    "user_answer": "",
    "results": [],
    "verification": None,
    "message": "",
    "error": None,
    "title": "",
    "environment": "",
    "classification": None,
    "environment_options": [],
    "pending_prompt": "",
    "pending_website_url": ""
}

# Each user gets an independent session, lock, and answer event.
_sessions = {}
_sessions_lock = threading.Lock()


def _get_user_id(user_id=None):
    """Return a consistent session key."""
    return str(user_id) if user_id is not None else DEFAULT_USER_ID


def _get_user_session(user_id=None):
    """Get or create the session for a particular user."""
    user_id = _get_user_id(user_id)

    with _sessions_lock:
        if user_id not in _sessions:
            _sessions[user_id] = {
                "data": INITIAL_SESSION.copy(),
                "lock": threading.Lock(),
                "answer_event": threading.Event()
            }

        return _sessions[user_id]


def update_session(key, value, user_id=None):
    user_session = _get_user_session(user_id)

    with user_session["lock"]:
        user_session["data"][key] = value


def get_session(user_id=None):
    user_session = _get_user_session(user_id)

    with user_session["lock"]:
        return user_session["data"].copy()


def reset_session(user_id=None):
    user_session = _get_user_session(user_id)

    with user_session["lock"]:
        user_session["data"] = INITIAL_SESSION.copy()

    user_session["answer_event"].clear()


def request_user_answer(question, user_id=None):
    user_session = _get_user_session(user_id)
    event = user_session["answer_event"]

    event.clear()

    with user_session["lock"]:
        user_session["data"]["current_question"] = question
        user_session["data"]["user_answer"] = ""
        user_session["data"]["status"] = "waiting_for_user"

    print(f"Waiting for dashboard response from user {user_id}: {question}")

    # Wait until this specific user submits an answer.
    event.wait()

    with user_session["lock"]:
        answer = user_session["data"]["user_answer"]
        user_session["data"]["current_question"] = ""
        user_session["data"]["status"] = "running"

    return answer

def request_answer_approval(question, suggested_answer, user_id=None):
    user_session = _get_user_session(user_id)
    event = user_session["answer_event"]

    event.clear()

    with user_session["lock"]:
        user_session["data"]["current_question"] = question
        user_session["data"]["suggested_answer"] = suggested_answer
        user_session["data"]["approval_decision"] = ""
        user_session["data"]["approved_answer"] = ""
        user_session["data"]["status"] = "waiting_for_approval"

    print(f"Waiting for approval from user {user_id}: {question}")

    event.wait()

    with user_session["lock"]:
        decision = user_session["data"].get("approval_decision", "")
        answer = user_session["data"].get("approved_answer", "")

        user_session["data"]["current_question"] = ""
        user_session["data"]["suggested_answer"] = ""
        user_session["data"]["approval_decision"] = ""
        user_session["data"]["approved_answer"] = ""
        user_session["data"]["status"] = "running"

    if decision in ("approve", "edit"):
        return answer

    return ""


def submit_answer_approval(decision, answer="", user_id=None):
    if decision not in ("approve", "edit", "reject"):
        return False

    user_session = _get_user_session(user_id)

    with user_session["lock"]:
        if user_session["data"].get("status") != "waiting_for_approval":
            return False

        suggested = user_session["data"].get("suggested_answer", "")

        if decision == "approve":
            answer = suggested

        elif decision == "edit":
            answer = answer.strip()
            if not answer:
                return False

        else:
            answer = ""

        user_session["data"]["approval_decision"] = decision
        user_session["data"]["approved_answer"] = answer

    user_session["answer_event"].set()
    return True



def submit_user_answer(answer, user_id=None):
    user_session = _get_user_session(user_id)

    with user_session["lock"]:
        user_session["data"]["user_answer"] = answer

    user_session["answer_event"].set()

    return True