
import os
import re
import threading
from functools import wraps

from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    jsonify,
    session
)

from app.database import (
    initialize_database,
    create_task,
    get_all_tasks,
    update_task,
    delete_task,
    get_tasks_with_deadlines,
    get_overdue_tasks,
    get_task_by_id
)

from agents.google_forms_agent import execute_agent
from agents.execution_agent import execute_task
from agents.shopping_execution_agent import execute_shopping_task
from agents.environment_selector import classify_environment

from agents.agent_session import (
    get_session,
    update_session,
    submit_user_answer,
    reset_session,
    submit_answer_approval
)
from app.auth import auth, login_required


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.secret_key = os.environ.get(
    "GYM_ANYTHING_SECRET_KEY",
    "development-only-change-this-secret"
)

app.register_blueprint(auth)

initialize_database()


ENVIRONMENT_NAMES = {
    "task_manager": "Task Manager",
    "google_forms": "Google Forms",
    "shopping": "Shopping"
}


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("user_id"):
            return redirect(url_for("auth.login"))

        return function(*args, **kwargs)

    return wrapper


def current_user_id():
    user_id = session.get("user_id")

    if user_id is None:
        raise ValueError("Please log in first.")

    return int(user_id)


# --------------------------------------------------
# GOOGLE FORMS URL EXTRACTION
# --------------------------------------------------

def extract_form_url(prompt):

    match = re.search(
        r"https://docs\.google\.com/forms/[^\s]+",
        prompt
    )

    return match.group(0).rstrip(".,)") if match else ""


# --------------------------------------------------
# AGENT SESSION MANAGEMENT
# --------------------------------------------------


def start_agent(environment, prompt, website_url="", user_id=None):

    if user_id is None:
        raise ValueError("User ID is required to start an agent.")

    reset_session(user_id=user_id)

    update_session("status", "running", user_id=user_id)
    update_session("environment", environment, user_id=user_id)
    update_session(
        "title",
        ENVIRONMENT_NAMES.get(environment, environment),
        user_id=user_id
    )
    update_session(
        "message",
        "Agent execution started.",
        user_id=user_id
    )

    thread = threading.Thread(
        target=run_agent_background,
        args=(environment, prompt, website_url, user_id),
        daemon=True
    )

    thread.start()


def run_agent_background(environment, prompt, website_url="", user_id=None):

    try:

        if user_id is None:
            raise ValueError("User ID is required.")

        if environment == "task_manager":

            result = execute_task(prompt, user_id=user_id)

            update_session(
                "results",
                result.get("results", []),
                user_id=user_id
            )

            update_session(
                "verification",
                result.get("verification"),
                user_id=user_id
            )

            if result.get("status") == "SUCCESS":

                update_session(
                    "message",
                    result.get(
                        "message",
                        "Task Manager operation completed."
                    ),
                    user_id=user_id
                )

                update_session("status", "completed", user_id=user_id)

            else:

                update_session(
                    "error",
                    result.get("error", "Task Manager operation failed."),
                    user_id=user_id
                )

                update_session("status", "failed", user_id=user_id)


        elif environment == "google_forms":

            website_url = website_url or extract_form_url(prompt)

            if not website_url or not website_url.startswith(
                "https://docs.google.com/forms/"
            ):
                raise ValueError("Please provide a valid Google Forms URL.")

            result = execute_agent(
                website_url,
                prompt,
                user_id=user_id
            )

            update_session(
                "results",
                result.get("results", []),
                user_id=user_id
            )

            update_session(
                "title",
                result.get("title", "Google Forms"),
                user_id=user_id
            )

            if result.get("verification") is not None:
                update_session(
                    "verification",
                    result["verification"],
                    user_id=user_id
                )

            if result.get("message"):
                update_session(
                    "message",
                    result["message"],
                    user_id=user_id
                )

            if result.get("error"):

                update_session(
                    "error",
                    result["error"],
                    user_id=user_id
                )

                update_session("status", "failed", user_id=user_id)

            else:

                update_session("status", "completed", user_id=user_id)


        elif environment == "shopping":

            # Shopping cart isolation will be implemented separately.
            result = execute_shopping_task(prompt)

            update_session(
                "results",
                [{
                    "question": "Shopping task",
                    "status": result.get("status", "FAILED")
                }],
                user_id=user_id
            )

            update_session(
                "verification",
                result.get("verification"),
                user_id=user_id
            )

            if result.get("status") == "SUCCESS":

                update_session(
                    "message",
                    "Product selection and independent cart verification completed.",
                    user_id=user_id
                )

                update_session("status", "completed", user_id=user_id)

            else:

                update_session(
                    "error",
                    result.get("error", "Shopping failed."),
                    user_id=user_id
                )

                update_session("status", "failed", user_id=user_id)


        else:

            raise ValueError("Unknown environment.")


    except Exception as error:

        print("Agent error:", error)

        update_session("error", str(error), user_id=user_id)
        update_session(
            "message",
            "The agent could not complete the task.",
            user_id=user_id
        )
        update_session("status", "failed", user_id=user_id)



def run_agent_background(environment, prompt, website_url, user_id):

    try:

        # ------------------------------------------
        # TASK MANAGER
        # ------------------------------------------

        if environment == "task_manager":

            result = execute_task(
                prompt,
                user_id=user_id
            )

            update_session(
                "results",
                result.get("results", []),
                user_id=user_id
            )

            update_session(
                "verification",
                result.get("verification"),
                user_id=user_id
            )

            if result.get("status") == "SUCCESS":

                update_session(
                    "message",
                    result.get(
                        "message",
                        "Task Manager operation completed."
                    ),
                    user_id=user_id
                )

                update_session(
                    "status",
                    "completed",
                    user_id=user_id
                )

            else:

                update_session(
                    "error",
                    result.get(
                        "error",
                        "Task Manager operation failed."
                    ),
                    user_id=user_id
                )

                update_session(
                    "status",
                    "failed",
                    user_id=user_id
                )

        # ------------------------------------------
        # GOOGLE FORMS
        # ------------------------------------------

        elif environment == "google_forms":

            website_url = website_url or extract_form_url(prompt)
            print("DEBUG website_url:", repr(website_url))
            print("DEBUG website_url type:", type(website_url))
            print("DEBUG prompt type:", type(prompt))
            print("DEBUG user_id:", repr(user_id))

            if not website_url or not website_url.startswith(
                "https://docs.google.com/forms/"
            ):

                raise ValueError(
                    "Please provide a valid Google Forms URL."
                )

            # Pass the authenticated user's ID.
            result = execute_agent(
                website_url,
                prompt,
                user_id
            )

            update_session(
                "results",
                result.get("results", []),
                user_id=user_id
            )

            update_session(
                "title",
                result.get("title", "Google Forms"),
                user_id=user_id
            )

            if result.get("verification") is not None:

                update_session(
                    "verification",
                    result["verification"],
                    user_id=user_id
                )

            if result.get("message"):

                update_session(
                    "message",
                    result["message"],
                    user_id=user_id
                )

            if result.get("error"):

                update_session(
                    "error",
                    result["error"],
                    user_id=user_id
                )

                update_session(
                    "status",
                    "failed",
                    user_id=user_id
                )

            else:

                update_session(
                    "status",
                    "completed",
                    user_id=user_id
                )

        # ------------------------------------------
        # SHOPPING
        # ------------------------------------------

        elif environment == "shopping":

            result = execute_shopping_task(prompt)

            update_session(
                "results",
                [{
                    "question": "Shopping task",
                    "status": result.get("status", "FAILED")
                }],
                user_id=user_id
            )

            update_session(
                "verification",
                result.get("verification"),
                user_id=user_id
            )

            if result.get("status") == "SUCCESS":

                update_session(
                    "message",
                    "Product selection and independent cart verification completed.",
                    user_id=user_id
                )

                update_session(
                    "status",
                    "completed",
                    user_id=user_id
                )

            else:

                update_session(
                    "error",
                    result.get("error", "Shopping failed."),
                    user_id=user_id
                )

                update_session(
                    "status",
                    "failed",
                    user_id=user_id
                )

        else:

            raise ValueError("Unknown environment.")

    except Exception as error:

        print("Agent error:", error)

        update_session(
            "error",
            str(error),
            user_id=user_id
        )

        update_session(
            "message",
            "The agent could not complete the task.",
            user_id=user_id
        )

        update_session(
            "status",
            "failed",
            user_id=user_id
        )


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------


@app.route("/")
@login_required
def home():
    return render_template("index.html")


# --------------------------------------------------
# INTERNAL TASK MANAGER INTERFACE
# --------------------------------------------------

@app.route("/internal/task-manager")
@login_required
def internal_task_manager():

    user_id = current_user_id()

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Internal Task Manager</title>
        <style>
            body { font-family: Arial; margin: 30px; }
            input, select, button { padding: 10px; margin: 5px; }
            .task { padding: 12px; margin: 10px 0; background: #eee; }
        </style>
    </head>
    <body>

        <h1>Internal Task Manager</h1>

        <h2>Create Task</h2>

        <form action="/internal/add-task" method="POST">
            <input name="title" placeholder="Task title" required>
            <input name="deadline" type="date">

            <select name="priority">
                <option>Low</option>
                <option selected>Medium</option>
                <option>High</option>
            </select>

            <button type="submit">Create Task</button>
        </form>

        <h2>Existing Tasks</h2>

        {% for task in tasks %}
        <div class="task">

            <strong>{{ task["title"] }}</strong>

            <p>Status: {{ task["status"] }}</p>
            <p>Deadline: {{ task["deadline"] or "Not set" }}</p>
            <p>Priority: {{ task["priority"] or "Medium" }}</p>

            <form action="/internal/update-task/{{ task['id'] }}" method="POST">

                <select name="status">
                    <option>Not Started</option>
                    <option>In Progress</option>
                    <option>Completed</option>
                </select>

                <input type="date" name="deadline"
                       value="{{ task['deadline'] or '' }}">

                <select name="priority">
                    <option>Low</option>
                    <option>Medium</option>
                    <option>High</option>
                </select>

                <button type="submit">Update Task</button>

            </form>

            <form action="/internal/delete-task/{{ task['id'] }}" method="POST">
                <button type="submit">Delete Task</button>
            </form>

        </div>
        {% else %}
            <p>No tasks available.</p>
        {% endfor %}

    </body>
    </html>
    """, tasks=get_all_tasks(user_id=user_id))


@app.route("/internal/add-task", methods=["POST"])
@login_required
def internal_add_task():

    user_id = current_user_id()

    title = request.form.get("title", "").strip()
    deadline = request.form.get("deadline") or None
    priority = request.form.get("priority", "Medium")

    if not title:
        return "Task title is required.", 400

    if priority not in ("Low", "Medium", "High"):
        return "Invalid priority.", 400

    if deadline and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
        return "Invalid deadline.", 400

    create_task(
        title,
        deadline=deadline,
        priority=priority,
        user_id=user_id
    )

    return redirect(url_for("internal_task_manager"))


@app.route("/internal/update-task/<int:task_id>", methods=["POST"])
@login_required
def internal_update_task(task_id):

    user_id = current_user_id()

    status = request.form.get("status")
    deadline = request.form.get("deadline") or None
    priority = request.form.get("priority")

    if status not in ("Not Started", "In Progress", "Completed"):
        return "Invalid status.", 400

    if priority not in ("Low", "Medium", "High"):
        return "Invalid priority.", 400

    task = get_task_by_id(task_id, user_id=user_id)

    if not task:
        return "Task not found.", 404

    update_task(
        task_id,
        status=status,
        deadline=deadline if deadline is not None else task["deadline"],
        priority=priority,
        user_id=user_id
    )

    return redirect(url_for("internal_task_manager"))


@app.route("/internal/delete-task/<int:task_id>", methods=["POST"])
@login_required
def internal_delete_task(task_id):

    user_id = current_user_id()

    task = get_task_by_id(task_id, user_id=user_id)

    if not task:
        return "Task not found.", 404

    delete_task(
        task_id,
        user_id=user_id
    )

    return redirect(url_for("internal_task_manager"))


@app.route("/internal/tasks")
@login_required
def internal_tasks_api():

    user_id = current_user_id()

    tasks = [
        dict(task)
        for task in get_all_tasks(user_id=user_id)
    ]

    return jsonify(tasks)


# --------------------------------------------------
# RUN AGENT
# --------------------------------------------------


@app.route("/run_agent", methods=["POST"])
@login_required
def run_agent():

    user_id = session.get("user_id")

    prompt = request.form.get("prompt", "").strip()
    website_url = request.form.get("website_url", "").strip()

    if not prompt:
        return "Please enter your instructions.", 400

    current = get_session(user_id)

    active_statuses = (
        "running",
        "waiting_for_user",
        "waiting_for_approval",
        "needs_environment"
    )

    if current.get("status") in active_statuses:
        return "An agent task is already running or awaiting input.", 409

    classification = classify_environment(prompt)
    environment = classification["environment"]

    if environment == "ambiguous":

        reset_session(user_id=user_id)

        update_session(
            "status", "needs_environment", user_id=user_id
        )

        update_session(
            "classification", classification, user_id=user_id
        )

        update_session(
            "pending_prompt", prompt, user_id=user_id
        )

        update_session(
            "pending_website_url", website_url, user_id=user_id
        )

        update_session(
            "environment_options",
            [
                {"value": "task_manager", "label": "Task Manager"},
                {"value": "google_forms", "label": "Google Forms"},
                {"value": "shopping", "label": "Shopping"}
            ],
            user_id=user_id
        )

        update_session(
            "message",
            "Please select the environment.",
            user_id=user_id
        )

        return redirect(url_for("home"))

    start_agent(
        environment,
        prompt,
        website_url,
        user_id=user_id
    )

    return redirect(url_for("home"))


# --------------------------------------------------
# SELECT ENVIRONMENT
# --------------------------------------------------


@app.route("/select_environment", methods=["POST"])
@login_required
def select_environment():

    user_id = session.get("user_id")

    environment = request.form.get("environment", "").strip()

    if environment not in ENVIRONMENT_NAMES:
        return "Invalid environment.", 400

    current = get_session(user_id)

    if current.get("status") != "needs_environment":
        return "No environment selection is pending.", 409

    prompt = current.get("pending_prompt", "")
    website_url = current.get("pending_website_url", "")

    if not prompt:
        return "Original prompt could not be recovered.", 400

    start_agent(
        environment,
        prompt,
        website_url,
        user_id=user_id
    )

    return redirect(url_for("home"))


@app.route("/agent_status")
@login_required
def agent_status():

    user_id = session.get("user_id")

    return jsonify(get_session(user_id))


@app.route("/submit_answer", methods=["POST"])
@login_required
def submit_answer():

    user_id = session.get("user_id")

    answer = request.form.get("answer", "").strip()

    if not answer:
        return "Please enter an answer.", 400

    current = get_session(user_id)

    if current.get("status") != "waiting_for_user":
        return "Agent is not waiting for an answer.", 409

    success = submit_user_answer(
        answer,
        user_id=user_id
    )

    if not success:
        return "Unable to submit your answer.", 409

    return redirect(url_for("home"))


@app.route("/submit_approval", methods=["POST"])
@login_required
def submit_approval():

    user_id = session.get("user_id")

    data = request.get_json(silent=True) or {}

    decision = data.get("decision", "")
    answer = data.get("answer", "")

    if decision not in ("approve", "edit", "reject"):
        return jsonify({
            "error": "Invalid approval decision."
        }), 400

    if not isinstance(answer, str):
        return jsonify({
            "error": "Answer must be text."
        }), 400

    current = get_session(user_id)

    if current.get("status") != "waiting_for_approval":
        return jsonify({
            "error": "The agent is not waiting for approval."
        }), 409

    success = submit_answer_approval(
        decision,
        answer,
        user_id=user_id
    )

    if not success:
        return jsonify({
            "error": "Unable to submit your approval."
        }), 409

    return jsonify({
        "message": "Your decision was sent to the agent."
    }), 200


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5055,
        debug=False,
        threaded=True,
        use_reloader=False
    )
