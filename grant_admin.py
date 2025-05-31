from app import create_app, db
from models import User

app = create_app()

with app.app_context():
    # Use double quotes for the email string to avoid issues with single quotes
    admin_user = User.query.filter_by(email="admin@example.com").first()
    if admin_user:
        if not admin_user.is_admin:
            admin_user.is_admin = True
            db.session.commit()
            print(f"Admin permissions granted for user: {admin_user.email}")
        else:
            print(f"User {admin_user.email} already has admin permissions.")
    else:
        print("Admin user with email 'admin@example.com' not found. Cannot grant permissions.")

