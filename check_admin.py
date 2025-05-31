from app import create_app, db
from models import User

app = create_app()

with app.app_context():
    admin_user = User.query.filter_by(email='admin@example.com').first()
    if admin_user:
        print(f"Admin user found: {admin_user.username}")
        print(f"Email: {admin_user.email}")
        print(f"Is Admin: {admin_user.is_admin}")
        # Check password - NOTE: This assumes the password was set to 'admin123'
        if admin_user.check_password('admin123'):
            print("Password check: Correct")
        else:
            print("Password check: Incorrect - Password might have been changed or not set correctly.")
    else:
        print("Admin user with email 'admin@example.com' not found.")

