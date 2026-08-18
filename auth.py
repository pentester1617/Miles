from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from flask_limiter.util import get_remote_address
from . import db, limiter
from .models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not (3 <= len(username) <= 30) or not username.replace("_", "").isalnum():
            flash("Username must be 3–30 characters using letters, numbers, or underscores.", "error")
            return render_template("signup.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("signup.html")
        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
            return render_template("signup.html")
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("main.edit_profile"))
    return render_template("signup.html")

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if not user or not user.is_active_account or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")
        login_user(user)
        return redirect(url_for("main.home"))
    return render_template("login.html")

@auth_bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))
