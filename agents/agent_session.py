
import threading

session = {
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

session_lock = threading.Lock()
answer_event = threading.Event()


def update_session(key, value):
    with session_lock:
        session[key] = value


def get_session():
    with session_lock:
        return session.copy()


def reset_session():
    with session_lock:
        session.update({
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
        })

    answer_event.clear()


def request_user_answer(question):
    update_session("current_question", question)
    update_session("user_answer", "")
    update_session("status", "waiting_for_user")

    answer_event.clear()

    print("Waiting for dashboard response:", question)

    answer_event.wait()

    with session_lock:
        answer = session["user_answer"]
        session["current_question"] = ""
        session["status"] = "running"

    return answer


def submit_user_answer(answer):
    update_session("user_answer", answer)
    answer_event.set()
