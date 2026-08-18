from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import db
from .models import User, Report, Message

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

@admin_bp.get("")
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "active": User.query.filter_by(is_active_account=True).count(),
        "reports": Report.query.filter_by(status="open").count(),
        "messages": Message.query.count(),
    }
    reports = Report.query.order_by(Report.created_at.desc()).limit(50).all()
    return render_template("admin.html", stats=stats, reports=reports)

@admin_bp.post("/users/<int:user_id>/suspend")
@admin_required
def suspend(user_id):
    user = User.query.get_or_404(user_id)
    if user.id != current_user.id:
        user.is_active_account = False
        db.session.commit()
    return redirect(url_for("admin.dashboard"))

@admin_bp.post("/users/<int:user_id>/restore")
@admin_required
def restore(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_account = True
    db.session.commit()
    return redirect(url_for("admin.dashboard"))

@admin_bp.post("/messages/<int:message_id>/delete")
@admin_required
def delete_message(message_id):
    msg = Message.query.get_or_404(message_id)
    msg.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))

@admin_bp.post("/reports/<int:report_id>/resolve")
@admin_required
def resolve_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.status = "resolved"
    report.resolved_at = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for("admin.dashboard"))
