from app import app, db, User
from werkzeug.security import generate_password_hash
from datetime import datetime
import os

# Check if database file exists
db_path = 'users.db'
if os.path.exists(db_path):
    print(f"Database file exists at: {os.path.abspath(db_path)}")
else:
    print("Database file does not exist, will create new one")

try:
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Creating admin user...")
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')  # Change this password
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists")
            
        # List all users in database
        print("\nCurrent users in database:")
        users = User.query.all()
        for user in users:
            print(f"Username: {user.username}, Email: {user.email}, Role: {user.role}")
            
except Exception as e:
    print(f"Error during database initialization: {str(e)}")
    raise 