import os
from getpass import getpass
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    username = input("Admin username: ").strip().lower()
    password = getpass("Admin password (8+ chars): ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)
    user.role = "admin"
    user.is_active_account = True
    user.set_password(password)
    db.session.commit()
    print(f"Admin account ready: @{username}")
