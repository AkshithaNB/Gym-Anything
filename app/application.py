
from flask import (
    Flask, render_template, render_template_string,
    request, redirect, url_for, jsonify
)

from app.database import (
    initialize_database, create_task, get_all_tasks,
    update_task, delete_task, get_tasks_with_deadlines,
    get_overdue_tasks, get_task_by_id
)

from agents.google_forms_agent import execute_agent
from agents.execution_agent import execute_task
from agents.shopping_execution_agent import execute_shopping_task
from agents.environment_selector import classify_environment

from agents.agent_session import (
    get_session, update_session, submit_user_answer, reset_session
)

import threading
import re

app = Flask(__name__)
initialize_database()

ENVIRONMENT_NAMES = {
    "task_manager": "Task Manager",
    "google_forms": "Google Forms",
    "shopping": "Shopping"
}


def extract_form_url(prompt):
    match = re.search(
        r"https://docs\.google\.com/forms/[^\s]+",
        prompt
    )
    return match.group(0).rstrip(".,)") if match else ""


def start_agent(environment, prompt, website_url=""):
    reset_session()
    update_session("status", "running")
    update_session("environment", environment)
    update_session("title", ENVIRONMENT_NAMES.get(environment, environment))
    update_session("message", "Agent execution started.")

    thread = threading.Thread(
        target=run_agent_background,
        args=(environment, prompt, website_url),
        daemon=True
    )
    thread.start()


def run_agent_background(environment, prompt, website_url=""):
    try:
        if environment == "task_manager":
            result = execute_task(prompt)

            update_session("results", result.get("results", []))
            update_session("verification", result.get("verification"))

            if result.get("status") == "SUCCESS":
                update_session("message", result.get("message", "Task Manager operation completed."))
                update_session("status", "completed")
            else:
                update_session("error", result.get("error", "Task Manager operation failed."))
                update_session("status", "failed")

        elif environment == "google_forms":
            website_url = website_url or extract_form_url(prompt)

            if not website_url or not website_url.startswith(
                "https://docs.google.com/forms/"
            ):
                raise ValueError("Please provide a valid Google Forms URL.")

            result = execute_agent(website_url, prompt)

            update_session("results", result.get("results", []))
            update_session("title", result.get("title", "Google Forms"))

            if result.get("verification") is not None:
                update_session("verification", result["verification"])

            if result.get("message"):
                update_session("message", result["message"])

            if result.get("error"):
                update_session("error", result["error"])
                update_session("status", "failed")
            else:
                update_session("status", "completed")

        elif environment == "shopping":
            result = execute_shopping_task(prompt)

            update_session("results", [{
                "question": "Shopping task",
                "status": result.get("status", "FAILED")
            }])

            update_session("verification", result.get("verification"))

            if result.get("status") == "SUCCESS":
                update_session(
                    "message",
                    "Product selection and independent cart verification completed."
                )
                update_session("status", "completed")
            else:
                update_session("error", result.get("error", "Shopping failed."))
                update_session("status", "failed")

        else:
            raise ValueError("Unknown environment.")

    except Exception as error:
        print("Agent error:", error)
        update_session("error", str(error))
        update_session("message", "The agent could not complete the task.")
        update_session("status", "failed")


@app.route("/")
def home():
    return render_template("index.html")


# Internal Task Manager interface used by the agent.
@app.route("/internal/task-manager")
def internal_task_manager():
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
                <input type="date" name="deadline" value="{{ task['deadline'] or '' }}">
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
    """, tasks=get_all_tasks())


@app.route("/internal/add-task", methods=["POST"])
def internal_add_task():
    title = request.form.get("title", "").strip()
    deadline = request.form.get("deadline") or None
    priority = request.form.get("priority", "Medium")

    if not title:
        return "Task title is required.", 400

    if deadline and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
        return "Invalid deadline.", 400

    create_task(title, deadline=deadline, priority=priority)
    return redirect(url_for("internal_task_manager"))


@app.route("/internal/update-task/<int:task_id>", methods=["POST"])
def internal_update_task(task_id):
    status = request.form.get("status")
    deadline = request.form.get("deadline") or None
    priority = request.form.get("priority")

    if status not in ("Not Started", "In Progress", "Completed"):
        return "Invalid status.", 400

    if priority not in ("Low", "Medium", "High"):
        return "Invalid priority.", 400

    if not get_task_by_id(task_id):
        return "Task not found.", 404

    connection = get_task_by_id(task_id)

    update_task(
        task_id,
        status=status,
        deadline=deadline if deadline is not None else connection["deadline"],
        priority=priority
    )

    return redirect(url_for("internal_task_manager"))


@app.route("/internal/delete-task/<int:task_id>", methods=["POST"])
def internal_delete_task(task_id):
    delete_task(task_id)
    return redirect(url_for("internal_task_manager"))


@app.route("/internal/tasks")
def internal_tasks_api():
    tasks = [dict(task) for task in get_all_tasks()]
    return jsonify(tasks)


@app.route("/run_agent", methods=["POST"])
def run_agent():
    prompt = request.form.get("prompt", "").strip()
    website_url = request.form.get("website_url", "").strip()

    if not prompt:
        return "Please enter your instructions.", 400

    current = get_session()

    if current["status"] in ("running", "waiting_for_user", "needs_environment"):
        return "An agent task is already running or awaiting input.", 409

    classification = classify_environment(prompt)
    environment = classification["environment"]

    if environment == "ambiguous":
        reset_session()
        update_session("status", "needs_environment")
        update_session("classification", classification)
        update_session("pending_prompt", prompt)
        update_session("pending_website_url", website_url)
        update_session("environment_options", [
            {"value": "task_manager", "label": "Task Manager"},
            {"value": "google_forms", "label": "Google Forms"},
            {"value": "shopping", "label": "Shopping"}
        ])
        update_session("message", "Please select the environment.")
        return redirect(url_for("home"))

    start_agent(environment, prompt, website_url)
    return redirect(url_for("home"))


@app.route("/select_environment", methods=["POST"])
def select_environment():
    environment = request.form.get("environment", "").strip()

    if environment not in ENVIRONMENT_NAMES:
        return "Invalid environment.", 400

    current = get_session()

    if current["status"] != "needs_environment":
        return "No environment selection is pending.", 409

    prompt = current.get("pending_prompt", "")
    website_url = current.get("pending_website_url", "")

    if not prompt:
        return "Original prompt could not be recovered.", 400

    start_agent(environment, prompt, website_url)
    return redirect(url_for("home"))


@app.route("/agent_status")
def agent_status():
    return jsonify(get_session())


@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    answer = request.form.get("answer", "").strip()

    if not answer:
        return "Please enter an answer.", 400

    if get_session()["status"] != "waiting_for_user":
        return "Agent is not waiting for an answer.", 409

    submit_user_answer(answer)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, threaded=True, use_reloader=False)
