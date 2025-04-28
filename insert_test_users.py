import os
from datetime import datetime
from werkzeug.security import generate_password_hash
import db
from models import User
from main import app  # Import the Flask app

# --- CONFIGURE THESE VALUES AS NEEDED ---
admin_branch_id = None  # Admin may not need a branch
branch_id = "branch_001"  # Example branch for manager and pumpman
created_by = 1  # Use an integer user ID, e.g., 1 for system/admin

def get_tenant_id():
    # You may want to fetch this from your config or set a default for testing
    return "tenant_001"

users = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "password": "admin123",
        "role": "admin",
        "branch_id": admin_branch_id,
        "is_active": True,
    },
    {
        "username": "manager",
        "email": "manager@example.com",
        "full_name": "Branch Manager",
        "password": "manager123",
        "role": "branch_manager",
        "branch_id": branch_id,
        "is_active": True,
    },
    {
        "username": "pumpman",
        "email": "pumpman@example.com",
        "full_name": "Pumpman User",
        "password": "pumpman123",
        "role": "pumpman",
        "branch_id": branch_id,
        "is_active": True,
    },
]

def main():
    now = datetime.now()
    tenant_id = get_tenant_id()
    for u in users:
        password_hash = generate_password_hash(u["password"], method="pbkdf2:sha256")
        user_obj = User(
            username=u["username"],
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"],
            branch_id=u["branch_id"],
            tenant_id=tenant_id,
            is_active=u["is_active"],
            created_at=now,
            created_by=created_by
        )
        with app.app_context():
            user_id = db.create_user(user_obj, password_hash)
            print(f"Created user {u['username']} with id {user_id}")

if __name__ == "__main__":
    main()
