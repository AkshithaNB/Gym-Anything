
from functools import wraps

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from app.database import (
    create_user,
    get_user_by_email,
    get_user_profile,
    update_user_profile
)

auth = Blueprint("auth", __name__)


def login_required(view):
    """Protect routes that require an authenticated user."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped_view


@auth.route("/register", methods=["GET", "POST"])
def register():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "GET":
        return render_template("register.html")

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not full_name or not email or not password:
        return render_template(
            "register.html",
            error="All fields are required."
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must contain at least 8 characters."
        )

    if password != confirm_password:
        return render_template(
            "register.html",
            error="Passwords do not match."
        )

    if get_user_by_email(email):
        return render_template(
            "register.html",
            error="An account with this email already exists."
        )

    password_hash = generate_password_hash(password)

    try:
        user_id = create_user(
            full_name,
            email,
            password_hash
        )

        session.clear()
        session["user_id"] = user_id
        session["user_name"] = full_name

        # New users complete their profile first.
        return redirect(url_for("auth.profile"))

    except Exception as error:
        print("Registration error:", error)

        return render_template(
            "register.html",
            error="Account creation failed. Please try again."
        )


@auth.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)

    if not user or not check_password_hash(
        user["password_hash"],
        password
    ):
        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]

    return redirect(url_for("home"))


@auth.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    user_id = session["user_id"]

    if request.method == "POST":

        allowed_fields = [
            "personal_email",
            "work_email",
            "phone",
            "institution",
            "department",
            "role",
            "education",
            "experience",
            "skills",
            "interests",
            "languages",
            "additional_info"
        ]

        profile_data = {
            field: request.form.get(field, "").strip()
            for field in allowed_fields
        }

        try:
            update_user_profile(user_id, **profile_data)

            return redirect(url_for("home"))

        except Exception as error:
            print("Profile update error:", error)

            profile = get_user_profile(user_id) or {}

            return render_template(
                "profile.html",
                profile=profile,
                error="Could not save your profile. Please try again."
            )

    profile_data = get_user_profile(user_id) or {}

    return render_template(
        "profile.html",
        profile=profile_data
    )


@auth.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("auth.login"))
