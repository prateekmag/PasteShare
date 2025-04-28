import os
import secrets
from datetime import datetime
from flask import Blueprint, request, redirect, render_template, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import UserCreate, UserRole, User
import db
from branch_utils import get_branch_data, is_valid_branch

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# User class for Flask-Login
class UserObject:
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.email = user_dict['email']
        self.role = user_dict['role']
        self.branch_id = user_dict['branch_id']
        self.is_active = user_dict['is_active']
        self.created_at = user_dict['created_at']

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.is_active

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def is_admin(self):
        """Admin has full overview access"""
        return self.role == UserRole.ADMIN

    def is_branch_manager(self):
        """Branch manager has branch level access"""
        return self.role == UserRole.SENIOR_MANAGER

    def is_pumpman(self):
        """Pumpman has limited individual access"""
        return self.role == UserRole.PUMPMAN

    def can_manage_users(self):
        """Only admin can manage users"""
        return self.role == UserRole.ADMIN

    def can_access_analytics(self):
        """Admin and branch managers can access analytics"""
        return self.role in [UserRole.ADMIN, UserRole.SENIOR_MANAGER]

    def can_manage_inventory(self):
        """Admin and branch managers can manage inventory"""
        return self.role in [UserRole.ADMIN, UserRole.SENIOR_MANAGER]

    def get_allowed_menu_items(self):
        """Get allowed menu items based on role"""
        if self.role == UserRole.ADMIN:
            return ["dashboard", "users", "branches", "settings", "reports"]
        elif self.role == UserRole.SENIOR_MANAGER:
            return ["dashboard", "reports", "inventory"]
        else:
            return ["dashboard"]

    def can_submit_readings(self):
        """Pumpman can submit readings"""
        return self.role == UserRole.PUMPMAN

    def can_view_reports(self):
        """Admin and branch managers can view reports"""
        return self.role in [UserRole.ADMIN, UserRole.SENIOR_MANAGER]

    def get_accessible_branches(self):
        if self.is_admin():
            return None  # Admin can access all branches
        return [self.branch_id] if self.branch_id else []

    def can_edit_branch_data(self, branch_id):
        if self.is_admin():
            return True
        if self.is_branch_manager() and self.branch_id == branch_id:
            return True
        return False

    def has_full_dashboard_access(self):
        return self.is_admin()

    def has_attendance_access(self):
        return self.is_admin() or self.is_branch_manager() or self.is_pumpman()

    def can_submit_totalizer_readings(self):
        return self.is_pumpman()

    def can_view_reports(self):
        return self.is_admin() or self.is_branch_manager()

    def get_manageable_roles(self):
        """Get the roles this user can manage based on their own role"""
        if self.role == UserRole.ADMIN:
            return [UserRole.ADMIN, UserRole.SENIOR_MANAGER, UserRole.PUMPMAN]
        elif self.role == UserRole.SENIOR_MANAGER:
            # Senior managers can only create pumpman accounts for their branch
            return [UserRole.PUMPMAN]
        else:
            return []

    def can_delete_users(self):
        """Only admin can delete users"""
        return self.role == UserRole.ADMIN

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    user_dict = db.get_user_by_id(int(user_id))
    if not user_dict:
        return None
    return UserObject(user_dict)

# Route for login page
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        login_type = request.form.get('login_type')
        remember_me = 'remember_me' in request.form

        # Get user from database
        user_dict = db.get_user_by_username(username)

        # Validate login type matches user role
        if user_dict:
            user_role = user_dict['role']
            valid_login = (
                (login_type == 'admin' and user_role == UserRole.ADMIN) or
                (login_type == 'branch' and user_role == UserRole.SENIOR_MANAGER) or
                (login_type == 'pumpman' and user_role == UserRole.PUMPMAN)
            )
            if not valid_login:
                flash('Invalid login type for this user.', 'danger')
                return render_template('login.html')

        if not user_dict:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        # Check if user is active
        if not user_dict['is_active']:
            flash('This account has been disabled. Please contact an administrator.', 'danger')
            return render_template('login.html')

        # Check password
        if not check_password_hash(user_dict['password_hash'], password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        # Login user
        user = UserObject(user_dict)
        login_user(user, remember=remember_me)

        # Set branch in session
        if user.branch_id and is_valid_branch(user.branch_id):
            session['branch_id'] = user.branch_id

        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')

        return redirect(next_page)

    return render_template('login.html')

# Route for logout
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

# Route for user registration (admin and senior managers)
@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Only admins and senior managers can register new users
    if not current_user.can_manage_users():
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))

    # Determine which branches to show based on user role
    if current_user.is_admin():
        branches = get_branch_data()  # Admin sees all branches
    else:
        # Senior manager only sees their own branch
        branches = [branch for branch in get_branch_data() if branch['id'] == current_user.branch_id]
        if not branches:
            flash('Your account is not properly associated with a branch.', 'danger')
            return redirect(url_for('dashboard'))

    # Get available roles based on user's role
    available_roles = current_user.get_manageable_roles()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        # Determine branch_id based on user role
        if current_user.is_admin():
            branch_id = request.form.get('branch_id') if request.form.get('branch_id') != "all" else None
        else:
            # Senior managers can only create users for their own branch
            branch_id = current_user.branch_id

        # Validate input
        if not username or not email or not full_name or not password or not role:
            flash('All fields are required.', 'danger')
            return render_template('register.html', branches=branches, available_roles=available_roles)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', branches=branches, available_roles=available_roles)

        # Validate role permissions
        if role not in [r.value for r in available_roles]:
            flash('You do not have permission to create a user with this role.', 'danger')
            return render_template('register.html', branches=branches, available_roles=available_roles)

        # Check if username already exists
        if db.get_user_by_username(username):
            flash('Username already exists.', 'danger')
            return render_template('register.html', branches=branches, available_roles=available_roles)

        # Create user
        user = UserCreate(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            branch_id=branch_id,
            is_active=True,
            created_at=datetime.now(),
            created_by=current_user.id,
            password=password,
            tenant_id="default"  # Using default tenant
        )

        # Generate password hash
        password_hash = generate_password_hash(password)

        # Add user to database
        try:
            db.create_user(user, password_hash)
            flash(f'User {username} has been created successfully.', 'success')
            return redirect(url_for('auth.manage_users'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'danger')
            return render_template('register.html', branches=branches, available_roles=available_roles)

    return render_template('register.html', branches=branches, available_roles=available_roles)

# Route for managing users (admin and senior managers)
@auth_bp.route('/users')
@login_required
def manage_users():
    # Only admins and senior managers can manage users
    if not (current_user.is_admin() or current_user.is_branch_manager()):
        flash('Access denied. Insufficient permissions.', 'danger')
        return redirect(url_for('dashboard'))
    if not current_user.can_manage_users():
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))

    # Get users based on role and branch access
    if current_user.is_admin():
        # Admins see all users
        users = db.get_users()
    else:
        # Senior managers only see users for their branch
        users = db.get_users(branch_id=current_user.branch_id)

        # Filter out admin and senior manager users from other branches
        # that a senior manager shouldn't be able to see or manage
        users = [u for u in users if u['role'] != UserRole.ADMIN.value and 
                (u['branch_id'] == current_user.branch_id or not u['branch_id'])]

    # Get branch data for display
    branches = {branch['id']: branch['name'] for branch in get_branch_data()}

    # Pass role information to the template
    user_role = current_user.role
    manageable_roles = current_user.get_manageable_roles()

    return render_template('users.html', 
                         users=users, 
                         branches=branches, 
                         user_role=user_role,
                         manageable_roles=manageable_roles)

# Route for editing user (admin and senior managers)
@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    # Only admins and senior managers can edit users
    if not current_user.can_manage_users():
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))

    # Get user
    user_dict = db.get_user_by_id(user_id)
    if not user_dict:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.manage_users'))

    # For senior managers, restrict access to only users in their branch and not admins or other senior managers
    if not current_user.is_admin():
        if user_dict['branch_id'] != current_user.branch_id or user_dict['role'] == UserRole.ADMIN.value:
            flash('You do not have permission to edit this user.', 'danger')
            return redirect(url_for('auth.manage_users'))

    # Determine which branches to show based on user role
    if current_user.is_admin():
        branches = get_branch_data()  # Admin sees all branches
    else:
        # Senior manager only sees their own branch
        branches = [branch for branch in get_branch_data() if branch['id'] == current_user.branch_id]

    # Get available roles based on user's role
    available_roles = current_user.get_manageable_roles()

    if request.method == 'POST':
        # Check if user is trying to edit their own role
        if current_user.id == user_id and request.form.get('role') != user_dict['role']:
            flash('You cannot change your own role.', 'danger')
            return redirect(url_for('auth.edit_user', user_id=user_id))

        # Update user data
        updates = {}
        updates['email'] = request.form.get('email')
        updates['full_name'] = request.form.get('full_name')

        # Role updates have permission restrictions
        new_role = request.form.get('role')
        if new_role not in [r.value for r in available_roles] and new_role != user_dict['role']:
            flash('You do not have permission to assign this role.', 'danger')
            return render_template('edit_user.html', 
                               user=user_dict, 
                               branches=branches, 
                               available_roles=available_roles)
        updates['role'] = new_role

        # Branch updates depend on user role
        if current_user.is_admin():
            updates['branch_id'] = request.form.get('branch_id') if request.form.get('branch_id') != "all" else None
        else:
            # Senior managers can only assign users to their own branch
            updates['branch_id'] = current_user.branch_id

        updates['is_active'] = 'is_active' in request.form

        # Update password if provided
        password = request.form.get('password')
        if password:
            confirm_password = request.form.get('confirm_password')
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('edit_user.html', 
                                   user=user_dict, 
                                   branches=branches, 
                                   available_roles=available_roles)
            updates['password_hash'] = generate_password_hash(password)

        # Update user in database
        try:
            if db.update_user(user_id, updates):
                flash('User has been updated successfully.', 'success')
                return redirect(url_for('auth.manage_users'))
            else:
                flash('Error updating user.', 'danger')
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'danger')

        return render_template('edit_user.html', 
                           user=user_dict, 
                           branches=branches, 
                           available_roles=available_roles)

    return render_template('edit_user.html', 
                       user=user_dict, 
                       branches=branches, 
                       available_roles=available_roles)

# Route for deleting user (admin and senior managers)
@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete a user from the system."""
    # Check permissions
    if not current_user.can_delete_users():
        return jsonify({
            "status": "error",
            "message": "You do not have permission to delete users"
        }), 403

    # Prevent self-deletion
    if current_user.id == user_id:
        return jsonify({
            "status": "error",
            "message": "You cannot delete your own account"
        }), 400

    # Delete the user
    try:
        success = db.delete_user(user_id)
        if success:
            return jsonify({
                "status": "success",
                "message": "User deleted successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "User not found or could not be deleted"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error deleting user: {str(e)}"
        }), 500

def initialize_tenant_schema(tenant_id):
    """Initialize clean tables for a new tenant"""
    with db.get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create schema for tenant
            cur.execute(f"""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = %s) THEN
                        EXECUTE 'CREATE SCHEMA ' || quote_ident(%s);
                    END IF;
                END $$;
            """, (tenant_id, tenant_id))
            conn.commit()

            # Set search path to tenant schema
            cur.execute(f"SET search_path TO {tenant_id}")

            # Create all tables for this tenant
            db.create_tables()
            db.create_product_tables()

def create_default_admin(tenant_id=None):
    if tenant_id:
        # Initialize schema and tables for new tenant
        initialize_tenant_schema(tenant_id)

    # Check if any admin user exists for this tenant
    users = db.get_users(role=UserRole.ADMIN.value, tenant_id=tenant_id)

    if not users:
        # Create default admin user
        username = f'admin_{tenant_id}' if tenant_id else 'admin'
        email = f'admin@{tenant_id}.petroltro.com' if tenant_id else 'admin@petroltro.com'
        password = secrets.token_urlsafe(12)  # Generate a random password

        user = UserCreate(
            username=username,
            email=email,
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(),
            password=password
        )

        # Generate password hash
        password_hash = generate_password_hash(password)

        # Add user to database
        try:
            db.create_user(user, password_hash)
            print(f"Default admin user created with username: {username} and password: {password}")
            print("Please change this password immediately after first login!")
        except Exception as e:
            print(f"Error creating default admin: {str(e)}")