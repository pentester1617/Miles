from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255), default="")
    bio = db.Column(db.String(280), default="")
    role = db.Column(db.String(20), default="user", nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("follower_id", "following_id", name="uq_follow"),)

class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("blocker_id", "blocked_id", name="uq_block"),)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    user_b_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_a_id", "user_b_id", name="uq_conversation"),)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = db.Column(db.String(40), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), default="/inbox")
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    message_id = db.Column(db.Integer, db.ForeignKey("message.id", ondelete="SET NULL"), nullable=True)
    reason = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(500), default="")
    status = db.Column(db.String(20), default="open", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
