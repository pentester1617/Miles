from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from . import db
from .models import User, Follow, Block, Conversation, Message, Notification, Report

main_bp = Blueprint("main", __name__)

def blocked_either(a, b):
    return Block.query.filter(or_(
        and_(Block.blocker_id == a, Block.blocked_id == b),
        and_(Block.blocker_id == b, Block.blocked_id == a)
    )).first() is not None

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return render_template("index.html")

@main_bp.route("/home")
@login_required
def home():
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template("home.html", unread=unread)

@main_bp.route("/discover")
@login_required
def discover():
    q = request.args.get("q", "").strip().lower()
    users = []
    if q:
        users = User.query.filter(
            User.username.ilike(f"%{q}%"),
            User.id != current_user.id,
            User.is_active_account.is_(True)
        ).order_by(User.username).limit(30).all()
    return render_template("discover.html", users=users, q=q)

@main_bp.route("/u/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username.lower(), is_active_account=True).first_or_404()
    following = Follow.query.filter_by(follower_id=current_user.id, following_id=user.id).first() is not None
    followers = Follow.query.filter_by(following_id=user.id).count()
    following_count = Follow.query.filter_by(follower_id=user.id).count()
    return render_template("profile.html", user=user, following=following,
                           followers=followers, following_count=following_count,
                           blocked=blocked_either(current_user.id, user.id))

@main_bp.post("/u/<username>/follow")
@login_required
def follow(username):
    user = User.query.filter_by(username=username.lower(), is_active_account=True).first_or_404()
    if user.id == current_user.id or blocked_either(current_user.id, user.id):
        abort(403)
    existing = Follow.query.filter_by(follower_id=current_user.id, following_id=user.id).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Follow(follower_id=current_user.id, following_id=user.id))
        db.session.add(Notification(user_id=user.id, kind="follow",
                                    text=f"@{current_user.username} connected with you.",
                                    link=url_for("main.profile", username=current_user.username)))
    db.session.commit()
    return redirect(url_for("main.profile", username=user.username))

@main_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        bio = request.form.get("bio", "").strip()
        avatar = request.form.get("avatar", "").strip()
        if len(bio) > 280:
            flash("Bio is limited to 280 characters.", "error")
            return render_template("edit_profile.html")
        if len(avatar) > 255:
            flash("Avatar URL is too long.", "error")
            return render_template("edit_profile.html")
        current_user.bio, current_user.avatar = bio, avatar
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("main.profile", username=current_user.username))
    return render_template("edit_profile.html")

@main_bp.route("/message/<username>", methods=["GET", "POST"])
@login_required
def message(username):
    recipient = User.query.filter_by(username=username.lower(), is_active_account=True).first_or_404()
    if recipient.id == current_user.id or blocked_either(current_user.id, recipient.id):
        abort(403)
    a, b = sorted([current_user.id, recipient.id])
    convo = Conversation.query.filter_by(user_a_id=a, user_b_id=b).first()
    if not convo:
        convo = Conversation(user_a_id=a, user_b_id=b)
        db.session.add(convo)
        db.session.flush()
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        anonymous = request.form.get("anonymous") == "1"
        if not body or len(body) > 2000:
            flash("Message must be between 1 and 2000 characters.", "error")
            return redirect(url_for("main.message", username=recipient.username))
        msg = Message(conversation_id=convo.id, sender_id=current_user.id,
                      recipient_id=recipient.id, body=body, is_anonymous=anonymous)
        db.session.add(msg)
        db.session.add(Notification(
            user_id=recipient.id, kind="message",
            text=("You received an anonymous message." if anonymous
                  else f"@{current_user.username} sent you a message."),
            link=url_for("main.message", username=current_user.username)
        ))
        db.session.commit()
        flash("Message sent.", "success")
        return redirect(url_for("main.message", username=recipient.username))
    messages = Message.query.filter_by(conversation_id=convo.id, deleted_at=None)\
        .order_by(Message.created_at.asc()).all()
    for m in messages:
        if m.recipient_id == current_user.id:
            m.is_read = True
    db.session.commit()
    return render_template("message.html", recipient=recipient, messages=messages)

@main_bp.route("/inbox")
@login_required
def inbox():
    convos = Conversation.query.filter(or_(
        Conversation.user_a_id == current_user.id,
        Conversation.user_b_id == current_user.id
    )).order_by(Conversation.created_at.desc()).all()
    items = []
    for c in convos:
        other_id = c.user_b_id if c.user_a_id == current_user.id else c.user_a_id
        other = User.query.get(other_id)
        last = Message.query.filter_by(conversation_id=c.id, deleted_at=None)\
            .order_by(Message.created_at.desc()).first()
        if other and last:
            items.append((other, last))
    return render_template("inbox.html", items=items)

@main_bp.route("/notifications")
@login_required
def notifications():
    notes = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(50).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return render_template("notifications.html", notifications=notes)

@main_bp.post("/block/<username>")
@login_required
def block(username):
    user = User.query.filter_by(username=username.lower()).first_or_404()
    if user.id != current_user.id and not Block.query.filter_by(blocker_id=current_user.id, blocked_id=user.id).first():
        db.session.add(Block(blocker_id=current_user.id, blocked_id=user.id))
        db.session.commit()
        flash(f"@{user.username} is now blocked.", "success")
    return redirect(url_for("main.profile", username=user.username))

@main_bp.post("/unblock/<username>")
@login_required
def unblock(username):
    user = User.query.filter_by(username=username.lower()).first_or_404()
    row = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user.id).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return redirect(url_for("main.profile", username=user.username))

@main_bp.post("/report/user/<username>")
@login_required
def report_user(username):
    user = User.query.filter_by(username=username.lower()).first_or_404()
    if user.id == current_user.id:
        abort(400)
    reason = request.form.get("reason", "Other").strip()[:100]
    details = request.form.get("details", "").strip()[:500]
    db.session.add(Report(reporter_id=current_user.id, reported_user_id=user.id,
                          reason=reason, details=details))
    db.session.commit()
    flash("Report submitted for moderation.", "success")
    return redirect(url_for("main.profile", username=user.username))

@main_bp.post("/report/message/<int:message_id>")
@login_required
def report_message(message_id):
    msg = Message.query.get_or_404(message_id)
    if msg.recipient_id != current_user.id and msg.sender_id != current_user.id:
        abort(403)
    reason = request.form.get("reason", "Other").strip()[:100]
    details = request.form.get("details", "").strip()[:500]
    db.session.add(Report(reporter_id=current_user.id, reported_user_id=msg.sender_id,
                          message_id=msg.id, reason=reason, details=details))
    db.session.commit()
    flash("Message reported.", "success")
    return redirect(url_for("main.inbox"))
