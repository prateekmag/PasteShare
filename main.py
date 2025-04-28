import os
from dotenv import load_dotenv
load_dotenv()
import requests
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session
from flask_cors import CORS
import logging
import sys
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, timedelta, date
import db
from db import create_tables
import purchase_orders
from suppliers import create_suppliers_table, add_supplier, get_suppliers, set_supplier_status, delete_supplier

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "petrolpro-secret")

# Enable CORS
CORS(app)

# Import blueprints and auth module
from routes import fuel_bp, sales_bp, staff_bp, reports_bp, purchase_bp, checklist_bp, totalizer_bp, credit_bp
from routers.products import products_bp
from routers.branch import branch_bp
from auth import auth_bp, login_manager, create_default_admin
from ai_routes import ai_bp

# Configure Flask-Login
login_manager.init_app(app)

# Register blueprints
app.register_blueprint(fuel_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(purchase_bp)
app.register_blueprint(checklist_bp)
app.register_blueprint(totalizer_bp)
app.register_blueprint(credit_bp)
app.register_blueprint(products_bp)
app.register_blueprint(branch_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(ai_bp, url_prefix='/ai')

# Root endpoint - redirect to dashboard if logged in, otherwise to login page
@app.route("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('auth.login'))

# Documentation endpoint
@app.route("/api/docs")
def api_docs():
    return jsonify({
        "title": "PetrolPro API Documentation",
        "description": "API for managing petrol station operations",
        "base_url": f"{request.url_root}api",
        "endpoints": {
            "fuel": [
                {"method": "POST", "path": "/api/fuel/entries", "description": "Add a new fuel entry"},
                {"method": "GET", "path": "/api/fuel/entries", "description": "Get fuel entries"},
                {"method": "POST", "path": "/api/fuel/dips", "description": "Add a new dip reading"},
                {"method": "GET", "path": "/api/fuel/dips", "description": "Get dip readings"},
                {"method": "POST", "path": "/api/fuel/tanks", "description": "Add a new tank"},
                {"method": "GET", "path": "/api/fuel/tanks", "description": "Get all tanks"},
                {"method": "GET", "path": "/api/fuel/tanks/{tank_id}", "description": "Get a specific tank"},
                {"method": "PATCH", "path": "/api/fuel/tanks/{tank_id}", "description": "Update a tank"}
            ],
            "sales": [
                {"method": "POST", "path": "/api/sales/sales", "description": "Record a new sale"},
                {"method": "GET", "path": "/api/sales/sales", "description": "Get sales with filtering"},
                {"method": "GET", "path": "/api/sales/sales/today", "description": "Get sales for today"},
                {"method": "GET", "path": "/api/sales/sales/summary", "description": "Get sales summary"},
                {"method": "GET", "path": "/api/sales/loyalty/{vehicle_number}", "description": "Get loyalty points"}
            ],
            "staff": [
                {"method": "POST", "path": "/api/staff/attendants", "description": "Add a new attendant"},
                {"method": "GET", "path": "/api/staff/attendants", "description": "Get all attendants"},
                {"method": "GET", "path": "/api/staff/attendants/{employee_id}", "description": "Get a specific attendant"},
                {"method": "PATCH", "path": "/api/staff/attendants/{employee_id}", "description": "Update an attendant"},
                {"method": "POST", "path": "/api/staff/attendance/check-in", "description": "Record check-in"},
                {"method": "POST", "path": "/api/staff/attendance/check-out/{attendance_id}", "description": "Record check-out"},
                {"method": "GET", "path": "/api/staff/attendance", "description": "Get attendance records"},
                {"method": "GET", "path": "/api/staff/attendance/today", "description": "Get today's attendance"},
                {"method": "POST", "path": "/api/staff/expenses", "description": "Record an expense"},
                {"method": "GET", "path": "/api/staff/expenses", "description": "Get expense records"}
            ],
            "reports": [
                {"method": "POST", "path": "/api/reports/fuel-consumption", "description": "Generate fuel report"},
                {"method": "POST", "path": "/api/reports/sales", "description": "Generate sales report"},
                {"method": "POST", "path": "/api/reports/inventory", "description": "Generate inventory report"},
                {"method": "POST", "path": "/api/reports/ai/fuel-consumption", "description": "AI fuel report"},
                {"method": "POST", "path": "/api/reports/ai/sales", "description": "AI sales report"},
                {"method": "POST", "path": "/api/reports/ai/inventory", "description": "AI inventory report"},
                {"method": "GET", "path": "/api/reports", "description": "Get all reports"},
                {"method": "GET", "path": "/api/reports/{report_id}", "description": "Get a specific report"}
            ],
            "purchase": [
                {"method": "POST", "path": "/api/purchase/orders", "description": "Create a purchase order"},
                {"method": "GET", "path": "/api/purchase/orders", "description": "Get purchase orders"},
                {"method": "GET", "path": "/api/purchase/orders/{order_id}", "description": "Get specific purchase order"},
                {"method": "PATCH", "path": "/api/purchase/orders/{order_id}", "description": "Update a purchase order"},
                {"method": "POST", "path": "/api/purchase/orders/{order_id}/approve", "description": "Approve purchase order"},
                {"method": "POST", "path": "/api/purchase/orders/{order_id}/reject", "description": "Reject purchase order"},
                {"method": "POST", "path": "/api/purchase/orders/{order_id}/payment", "description": "Update payment status"},
                {"method": "POST", "path": "/api/purchase/orders/{order_id}/complete", "description": "Complete purchase order"}
            ],
            "products": [
                {"method": "GET", "path": "/api/products/categories", "description": "Get product categories"},
                {"method": "POST", "path": "/api/products/categories", "description": "Add a new product category"},
                {"method": "GET", "path": "/api/products/categories/{category_id}", "description": "Get a specific category"},
                {"method": "PATCH", "path": "/api/products/categories/{category_id}", "description": "Update a category"},
                {"method": "DELETE", "path": "/api/products/categories/{category_id}", "description": "Delete a category"},
                {"method": "GET", "path": "/api/products/products", "description": "Get products with filtering"},
                {"method": "POST", "path": "/api/products/products", "description": "Add a new product"},
                {"method": "GET", "path": "/api/products/products/{product_id}", "description": "Get a specific product"},
                {"method": "PATCH", "path": "/api/products/products/{product_id}", "description": "Update a product"},
                {"method": "DELETE", "path": "/api/products/products/{product_id}", "description": "Delete a product"},
                {"method": "POST", "path": "/api/products/products/{product_id}/stock", "description": "Update product stock"},
                {"method": "GET", "path": "/api/products/products/low-stock", "description": "Get low stock products"}
            ],
            "branch": [
                {"method": "GET", "path": "/api/branch/branches", "description": "Get all branches"},
                {"method": "POST", "path": "/api/branch/branches", "description": "Add a new branch"},
                {"method": "GET", "path": "/api/branch/branches/{branch_id}", "description": "Get a specific branch"},
                {"method": "PATCH", "path": "/api/branch/branches/{branch_id}", "description": "Update a branch"},
                {"method": "DELETE", "path": "/api/branch/branches/{branch_id}", "description": "Delete a branch"}
            ]
        }
    })

# Initialize database tables
@app.route('/api/initialize', methods=['GET'])
def initialize():
    create_tables()
    db.create_product_tables()  # Ensure product tables are created
    return jsonify({"status": "success", "message": "Database tables created"})

# Web Interface Routes
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

from db import get_fuel_types, get_attendants, get_tanks
@app.route("/fuel", methods=["GET"])
@login_required
def fuel_management():
    fuel_types = get_fuel_types()
    selected_branch = request.args.get('branch_id') or getattr(current_user, 'branch_id', None)
    attendants = get_attendants(active_only=True, branch_id=selected_branch)
    tanks = get_tanks(branch_id=selected_branch)
    branches = [
        {"id": "SMBNC", "name": "SUNDARAM MAHADEO (B. CHARIALI)"},
        {"id": "SMST", "name": "SUNDARAM MAHADEO (SOOTEA)"},
        {"id": "SMGH", "name": "SUNDARAM MAHADEO (GOHPUR)"},
    ]
    return render_template("fuel.html", fuel_types=fuel_types, attendants=attendants, branches=branches, selected_branch=selected_branch, tanks=tanks)

@app.route("/sales")
@login_required
def sales_management():
    return render_template("sales.html")

# Credit Management routes
@app.route("/credit-customers")
@login_required
def credit_customers_view():
    return render_template("credit_customers.html")

@app.route("/credit-customers/add", methods=["GET", "POST"])
@login_required
def add_credit_customer_view():
    if request.method == "POST":
        try:
            # Format customer data
            customer_data = {
                "customer_id": request.form.get("customer_id"),
                "name": request.form.get("name"),
                "customer_type": request.form.get("customer_type"),
                "contact_person": request.form.get("contact_person", ""),
                "phone_number": request.form.get("phone_number"),
                "whatsapp_number": request.form.get("whatsapp_number", ""),
                "email": request.form.get("email", ""),
                "address": request.form.get("address", ""),
                "credit_limit": float(request.form.get("credit_limit", 0)),
                "branch_id": request.form.get("branch_id")
            }

            # Send request to the API
            response = requests.post(f"{request.url_root}api/credit/customers", json=customer_data)

            if response.status_code == 201:
                flash("Credit customer added successfully", "success")
                return redirect(url_for("credit_customers_view"))
            else:
                resp_data = response.json()
                flash(f"Error: {resp_data.get('message', 'Failed to add customer')}", "danger")

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template("add_credit_customer.html")

@app.route("/profile")
@login_required
def profile_view():
    return render_template("profile.html")

@app.route("/credit-customers/<customer_id>")
@login_required
def view_credit_customer(customer_id):
    try:
        response = requests.get(f"{request.url_root}api/credit/customers/{customer_id}/history")
        if response.status_code == 200:
            history = response.json()
            return render_template("view_credit_customer.html", history=history)
        else:
            flash("Customer not found", "warning")
            return redirect(url_for("credit_customers_view"))
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("credit_customers_view"))

@app.route("/credit-customers/<customer_id>/add-transaction", methods=["GET", "POST"])
@login_required
def add_credit_transaction_view(customer_id):
    if request.method == "POST":
        try:
            # Format transaction data
            transaction_data = {
                "customer_id": customer_id,
                "transaction_type": request.form.get("transaction_type"),
                "amount": float(request.form.get("amount", 0)),
                "payment_method": request.form.get("payment_method", ""),
                "reference_number": request.form.get("reference_number", ""),
                "notes": request.form.get("notes", ""),
                "branch_id": request.form.get("branch_id"),
                "recorded_by": request.form.get("recorded_by")
            }

            # Send request to the API
            response = requests.post(f"{request.url_root}api/credit/transactions", json=transaction_data)

            if response.status_code == 201:
                resp_data = response.json()
                flash(f"{transaction_data['transaction_type'].capitalize()} recorded successfully. New balance: {resp_data.get('new_balance', 0)}", "success")
                return redirect(url_for("view_credit_customer", customer_id=customer_id))
            else:
                resp_data = response.json()
                flash(f"Error: {resp_data.get('message', 'Failed to record transaction')}", "danger")

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    # Get customer details
    try:
        response = requests.get(f"{request.url_root}api/credit/customers?customer_id={customer_id}")
        if response.status_code == 200:
            customers = response.json()
            if customers and isinstance(customers, list):
                customer = customers[0]
            else:
                customer = customers
            return render_template("add_credit_transaction.html", customer=customer)
        else:
            flash("Customer not found", "warning")
            return redirect(url_for("credit_customers_view"))
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("credit_customers_view"))

@app.route("/credit-customers/due-payments")
@login_required
def due_payments_view():
    return render_template("due_payments.html")

@app.route("/staff")
@login_required
def staff_management():
    return render_template("staff.html")

@app.route("/attendance")
@login_required
def attendance_tracking():
    return render_template("attendance.html")

@app.route("/reports")
@login_required
def reports_view():
    return render_template("reports.html")

@app.route("/expenses", methods=['GET', 'POST'])
@login_required
def expenses_view():
    from flask import g
    g.tenant_id = getattr(current_user, 'branch_id', None)
    if current_user.role == 'admin':
        managers = db.get_users(role='manager', is_active=True)
        staff = db.get_attendants(active_only=True)
        employees = []
        for emp in managers:
            employees.append({
                'username': emp.get('username'),
                'full_name': emp.get('full_name') or emp.get('username'),
                'is_active': emp.get('is_active', True),
                'role': emp.get('role', 'manager'),
                'branch_id': emp.get('branch_id')
            })
        for att in staff:
            employees.append({
                'username': att.get('username') or att.get('employee_id') or att.get('id'),
                'full_name': att.get('full_name') or att.get('name') or att.get('username') or att.get('employee_id') or att.get('id'),
                'is_active': att.get('is_active', att.get('active', True)),
                'role': att.get('role', 'pumpman'),
                'branch_id': att.get('branch_id')
            })
        reports = db.get_reports(limit=20)
    elif current_user.role == 'manager':
        managers = db.get_users(role='manager', branch_id=g.tenant_id, is_active=True)
        staff = db.get_attendants(active_only=True, branch_id=g.tenant_id)
        employees = []
        for emp in managers:
            employees.append({
                'username': emp.get('username'),
                'full_name': emp.get('full_name') or emp.get('username'),
                'is_active': emp.get('is_active', True),
                'role': emp.get('role', 'manager'),
                'branch_id': emp.get('branch_id')
            })
        for att in staff:
            employees.append({
                'username': att.get('username') or att.get('employee_id') or att.get('id'),
                'full_name': att.get('full_name') or att.get('name') or att.get('username') or att.get('employee_id') or att.get('id'),
                'is_active': att.get('is_active', att.get('active', True)),
                'role': att.get('role', 'pumpman'),
                'branch_id': att.get('branch_id')
            })
        reports = db.get_reports(limit=20)
    else:
        employees = []
        reports = []
    return render_template("expenses.html", employees=employees, reports=reports)

@app.route("/admin")
@login_required
def admin_dashboard():
    # Only admin users can access admin dashboard
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("admin.html")

@app.route("/api/branches", methods=['GET'])
@login_required
def api_get_branches():
    branches = db.get_branches()
    return jsonify(branches)

@app.route("/api/branches", methods=['POST'])
@login_required
def api_create_branch():
    data = request.get_json()
    db.create_branch(
        id=data['id'],
        name=data['name'],
        address=data.get('address'),
        phone=data.get('phone'),
        email=data.get('email'),
        is_active=data.get('is_active', True)
    )
    return jsonify({'status': 'success'})

@app.route("/api/branches/<branch_id>", methods=['PUT'])
@login_required
def api_update_branch(branch_id):
    data = request.get_json()
    db.update_branch(
        branch_id,
        name=data.get('name'),
        address=data.get('address'),
        phone=data.get('phone'),
        email=data.get('email'),
        is_active=data.get('is_active')
    )
    return jsonify({'status': 'success'})

@app.route("/api/branches/<branch_id>", methods=['DELETE'])
@login_required
def api_delete_branch(branch_id):
    db.delete_branch(branch_id)
    return jsonify({'status': 'success'})

@app.route("/purchase-orders")
@login_required
def purchase_orders_view():
    return render_template("purchase_orders.html")

@app.route("/purchase-orders/create", methods=["GET", "POST"])
@login_required
def create_purchase_order_view():
    if request.method == "POST":
        try:
            # Calculate total amount
            quantity = float(request.form.get("quantity", 0))
            unit_price = float(request.form.get("unit_price", 0))
            total_amount = quantity * unit_price

            # Format order data
            order_data = {
                "branch_id": request.form.get("branch_id"),
                "product_type": request.form.get("product_type"),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_amount": total_amount,
                "requested_by": request.form.get("requested_by"),
                "supplier": request.form.get("supplier", ""),
                "expected_delivery_date": request.form.get("expected_delivery_date", ""),
                "notes": request.form.get("notes", "")
            }

            # Send request to the API
            response = requests.post(f"{request.url_root}api/purchase/orders", json=order_data)

            if response.status_code == 201:
                flash("Purchase order created successfully", "success")
                return redirect(url_for("purchase_orders_view"))
            else:
                resp_data = response.json()
                flash(f"Error: {resp_data.get('message', 'Failed to create purchase order')}", "danger")

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    suppliers = get_suppliers(active_only=True)
    # Load branches from JSON for branch dropdown
    with open('data/branches.json') as f:
        branches = json.load(f)
    # Only show the logged-in user for 'requested_by'
    requested_by_user = {'username': current_user.username, 'full_name': getattr(current_user, 'full_name', current_user.username)}
    return render_template('create_purchase_order.html', suppliers=suppliers, branches=branches, requested_by_user=requested_by_user)

@app.route("/purchase-orders/<int:order_id>")
@login_required
def view_purchase_order(order_id):
    try:
        response = requests.get(f"{request.url_root}api/purchase/orders/{order_id}")
        if response.status_code == 200:
            order = response.json()
            return render_template("view_purchase_order.html", order=order)
        else:
            flash("Purchase order not found", "warning")
            return redirect(url_for("purchase_orders_view"))
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("purchase_orders_view"))

@app.route("/api/purchase-orders")
@login_required
def get_purchase_orders():
    try:
        branch_id = request.args.get('branch_id')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        # Get purchase orders from the database
        orders = purchase_orders.get_purchase_orders(branch_id, status, limit, offset)
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/purchase-orders/<int:order_id>/approve", methods=["POST"])
@login_required
def approve_purchase_order_view(order_id):
    try:
        data = {
            "approved_by": current_user.id  # Use the logged-in user's id
        }

        response = requests.post(f"{request.url_root}api/purchase/orders/{order_id}/approve", json=data)

        if response.status_code == 200:
            flash("Purchase order approved successfully", "success")
        else:
            resp_data = response.json()
            flash(f"Error: {resp_data.get('message', 'Failed to approve purchase order')}", "danger")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("view_purchase_order", order_id=order_id))

@app.route("/purchase-orders/<int:order_id>/reject", methods=["POST"])
@login_required
def reject_purchase_order_view(order_id):
    try:
        data = {
            "approved_by": request.form.get("approved_by"),
            "reason": request.form.get("reason", "")
        }

        response = requests.post(f"{request.url_root}api/purchase/orders/{order_id}/reject", json=data)

        if response.status_code == 200:
            flash("Purchase order rejected successfully", "success")
        else:
            resp_data = response.json()
            flash(f"Error: {resp_data.get('message', 'Failed to reject purchase order')}", "danger")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("view_purchase_order", order_id=order_id))

@app.route("/purchase-orders/<int:order_id>/payment", methods=["POST"])
@login_required
def update_payment_status_view(order_id):
    try:
        data = {
            "payment_status": request.form.get("payment_status"),
            "payment_amount": float(request.form.get("payment_amount", 0)),
            "payment_reference": request.form.get("payment_reference", "")
        }

        response = requests.post(f"{request.url_root}api/purchase/orders/{order_id}/payment", json=data)

        if response.status_code == 200:
            flash("Payment status updated successfully", "success")
        else:
            resp_data = response.json()
            flash(f"Error: {resp_data.get('message', 'Failed to update payment status')}", "danger")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("view_purchase_order", order_id=order_id))

@app.route("/purchase-orders/<int:order_id>/complete", methods=["POST"])
@login_required
def complete_purchase_order_view(order_id):
    try:
        response = requests.post(f"{request.url_root}api/purchase/orders/{order_id}/complete")

        if response.status_code == 200:
            flash("Purchase order marked as completed", "success")
        else:
            resp_data = response.json()
            flash(f"Error: {resp_data.get('message', 'Failed to complete purchase order')}", "danger")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("view_purchase_order", order_id=order_id))

@app.route("/add-tank", methods=["GET", "POST"])
@login_required
def add_tank_view():
    if request.method == "POST":
        tank_data = {
            "id": request.form.get("id"),
            "fuel_type": request.form.get("fuel_type"),
            "capacity": float(request.form.get("capacity")),
            "current_level": float(request.form.get("current_level")),
            "status": request.form.get("status"),
            "branch_id": request.form.get("branch_id")
        }
        response = requests.post(f"{request.url_root}api/fuel/tanks", json=tank_data)
        if response.json().get("status") == "success":
            flash("Tank added successfully", "success")
            return redirect(url_for("fuel_management"))
        else:
            flash(f"Error: {response.json().get('message')}", "danger")
    return render_template("add_tank.html")

# Totalizer readings views
@app.route("/totalizer")
@login_required
def totalizer_view():
    return render_template("totalizer.html")

@app.route("/totalizer/readings/add", methods=["GET", "POST"])
@login_required
def add_totalizer_reading_view():
    if request.method == "POST":
        try:
            reading_data = {
                "pump_id": request.form.get("pump_id"),
                "nozzle_id": request.form.get("nozzle_id"),
                "product_type": request.form.get("product_type"),
                "reading_type": request.form.get("reading_type"),
                "reading_value": float(request.form.get("reading_value", 0)),
                "pumpman_id": request.form.get("pumpman_id"),
                "shift": request.form.get("shift"),
                "branch_id": request.form.get("branch_id"),
                "totalizer_image_url": request.form.get("totalizer_image_url", "")
            }

            # Send request to the API
            response = requests.post(f"{request.url_root}api/totalizer/readings", json=reading_data)

            if response.status_code == 201:
                if reading_data["reading_type"] == "closing":
                    flash("Closing reading recorded and sales calculated successfully", "success")
                else:
                    flash("Opening reading recorded successfully", "success")
                return redirect(url_for("totalizer_view"))
            else:
                resp_data = response.json()
                flash(f"Error: {resp_data.get('message', 'Failed to record reading')}", "danger")

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template("add_totalizer_reading.html")

@app.route("/totalizer/sales")
@login_required
def totalizer_sales_view():
    return render_template("totalizer_sales.html")

# Products Management routes
@app.route("/products")
@login_required
def products_view():
    return render_template("products.html")

# Daily checklist views
@app.route("/daily-checklist")
@login_required
def daily_checklist_view():
    return render_template("daily_checklist.html")

@app.route("/daily-checklist/add", methods=["GET", "POST"])
@login_required
def add_daily_checklist_view():
    if request.method == "POST":
        try:
            checklist_data = {
                "branch_id": request.form.get("branch_id"),
                "completed_by": request.form.get("completed_by"),
                "dispenser_test_done": request.form.get("dispenser_test_done") == "on",
                "pump_cleaning_done": request.form.get("pump_cleaning_done") == "on",
                "bathroom_cleaning_done": request.form.get("bathroom_cleaning_done") == "on",
                "notes": request.form.get("notes", "")
            }

            # Send request to the API
            response = requests.post(f"{request.url_root}api/checklist/checklists", json=checklist_data)

            if response.status_code == 201:
                flash("Daily checklist recorded successfully", "success")
                return redirect(url_for("daily_checklist_view"))
            else:
                resp_data = response.json()
                flash(f"Error: {resp_data.get('message', 'Failed to record checklist')}", "danger")

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    # Fetch list of branches for dropdown
    from branch_utils import get_branch_data
    branches = get_branch_data()
    return render_template("add_daily_checklist.html", branches=branches)

@app.route("/api/daily-checklists")
@login_required
def get_daily_checklists():
    try:
        branch_id = request.args.get('branch_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = datetime.now().isoformat()

        import daily_checklist
        # Parse dates
        from routes import parse_date
        start_date_obj = parse_date(start_date)
        end_date_obj = parse_date(end_date)

        # Get checklists from the database
        checklists = daily_checklist.get_checklists(branch_id, start_date_obj, end_date_obj)
        return jsonify(checklists)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/daily-checklists/today")
@login_required
def get_today_checklist():
    try:
        branch_id = request.args.get('branch_id')
        if not branch_id:
            return jsonify({"error": "Branch ID is required"}), 400

        import daily_checklist
        today = datetime.now()
        checklist = daily_checklist.get_checklist_by_date(branch_id, today)

        if not checklist:
            return jsonify({
                "status": "info",
                "message": "No checklist found for today",
                "data": None
            })

        return jsonify(checklist)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/suppliers')
@login_required
def suppliers_view():
    if not current_user.role == 'admin':
        flash('Only admins can manage suppliers.', 'danger')
        return redirect(url_for('dashboard'))
    suppliers = get_suppliers()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
def add_supplier_view():
    if not current_user.role == 'admin':
        flash('Only admins can add suppliers.', 'danger')
        return redirect(url_for('suppliers_view'))
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        address = request.form['address']
        add_supplier(name, contact, address)
        flash('Supplier added successfully.', 'success')
        return redirect(url_for('suppliers_view'))
    return render_template('add_supplier.html')

@app.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
def edit_supplier_view(supplier_id):
    # Only allow admin and manager to edit
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to edit suppliers.', 'danger')
        return redirect(url_for('suppliers_view'))
    with db.get_db_connection() as conn:
        with db.dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM suppliers WHERE id = %s", (supplier_id,))
            supplier = cur.fetchone()
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for("suppliers_view"))
    if request.method == "POST":
        name = request.form.get("name")
        contact = request.form.get("contact")
        address = request.form.get("address")
        # Validation
        errors = []
        if not name or len(name.strip()) < 3:
            errors.append("Supplier name must be at least 3 characters.")
        if contact and (len(contact) < 7 or not contact.isdigit()):
            errors.append("Contact must be a valid phone number.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("supplier_edit.html", supplier=supplier)
        with db.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE suppliers SET name = %s, contact = %s, address = %s WHERE id = %s
                """, (name, contact, address, supplier_id))
                conn.commit()
        flash("Supplier updated successfully!", "success")
        return redirect(url_for("suppliers_view"))
    return render_template("supplier_edit.html", supplier=supplier)

@app.route('/suppliers/<int:supplier_id>/status/<status>', methods=['POST'])
@login_required
def set_supplier_status_view(supplier_id, status):
    if not current_user.role == 'admin':
        flash('Only admins can change supplier status.', 'danger')
        return redirect(url_for('suppliers_view'))
    set_supplier_status(supplier_id, status)
    flash(f'Supplier status changed to {status}.', 'success')
    return redirect(url_for('suppliers_view'))

@app.route('/suppliers/<int:supplier_id>/delete', methods=['POST'])
@login_required
def delete_supplier_view(supplier_id):
    if not current_user.role == 'admin':
        flash('Only admins can delete suppliers.', 'danger')
        return redirect(url_for('suppliers_view'))
    delete_supplier(supplier_id)
    flash('Supplier deleted.', 'success')
    return redirect(url_for('suppliers_view'))

@app.route('/suppliers/bulk-edit', methods=['GET', 'POST'])
@login_required
def suppliers_bulk_edit_view():
    # Only allow admin/manager
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission for bulk edit.', 'danger')
        return redirect(url_for('suppliers_view'))
    if request.method == 'POST':
        selected = request.form.getlist('selected')
        updates = []
        for sid in selected:
            name = request.form.get(f'name_{sid}')
            contact = request.form.get(f'contact_{sid}')
            address = request.form.get(f'address_{sid}')
            # Validation (reuse)
            if not name or len(name.strip()) < 3:
                flash(f'Supplier name for ID {sid} must be at least 3 characters.', 'danger')
                continue
            if contact and (len(contact) < 7 or not contact.isdigit()):
                flash(f'Contact for ID {sid} must be a valid phone number.', 'danger')
                continue
            updates.append((name, contact, address, sid))
        if updates:
            with db.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany('UPDATE suppliers SET name=%s, contact=%s, address=%s WHERE id=%s', updates)
                    conn.commit()
            flash('Selected suppliers updated.', 'success')
        return redirect(url_for('suppliers_view'))
    # GET: render table
    with db.get_db_connection() as conn:
        with db.dict_cursor(conn) as cur:
            cur.execute('SELECT * FROM suppliers ORDER BY id')
            suppliers = cur.fetchall()
    return render_template('suppliers_bulk_edit.html', suppliers=suppliers)

@app.route('/suppliers/bulk-upload', methods=['GET', 'POST'])
@login_required
def suppliers_bulk_upload_view():
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission for bulk upload.', 'danger')
        return redirect(url_for('suppliers_view'))
    import csv, io
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)
        file = request.files['csv_file']
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(request.url)
        stream = io.StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        updates = []
        for row in reader:
            sid = row.get('id')
            name = row.get('name')
            contact = row.get('contact')
            address = row.get('address')
            if not sid or not name or len(name.strip()) < 3:
                flash(f'Row with ID {sid} has invalid name.', 'danger')
                continue
            if contact and (len(contact) < 7 or not contact.isdigit()):
                flash(f'Row with ID {sid} has invalid contact.', 'danger')
                continue
            updates.append((name, contact, address, sid))
        if updates:
            with db.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany('UPDATE suppliers SET name=%s, contact=%s, address=%s WHERE id=%s', updates)
                    conn.commit()
            flash('Bulk upload successful.', 'success')
        return redirect(url_for('suppliers_view'))
    return render_template('suppliers_bulk_upload.html')

@app.route('/suppliers/bulk-upload/template')
@login_required
def suppliers_bulk_upload_template():
    import csv, io
    with db.get_db_connection() as conn:
        with db.dict_cursor(conn) as cur:
            cur.execute('SELECT * FROM suppliers ORDER BY id')
            suppliers = cur.fetchall()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['id', 'name', 'contact', 'address'])
    writer.writeheader()
    for s in suppliers:
        writer.writerow({'id': s['id'], 'name': s['name'], 'contact': s['contact'], 'address': s['address']})
    output.seek(0)
    from flask import Response
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=suppliers_template.csv'})

# --- Subscription Management ---
from db import (
    add_subscription, get_subscription_types,
    create_fuel_types_table, get_fuel_types, add_fuel_type, update_fuel_type, delete_fuel_type
)

@app.route("/subscription-plans")
@login_required
def subscription_plans_view():
    from db import get_subscription_types
    plans = get_subscription_types()
    return render_template("subscription_plans.html", plans=plans)

@app.route("/branch/<branch_id>/subscription", methods=["GET", "POST"])
@login_required
def branch_subscription_view(branch_id):
    from branch_utils import get_branch_data
    branch = get_branch_data(branch_id)
    if not branch:
        flash("Branch not found", "danger")
        return redirect(url_for("branches_view"))
    msg = None
    plan_types = get_subscription_types()
    if request.method == "POST" and not request.args.get("ajax"):
        plan_type = request.form.get("plan_type")
        # Find plan_id and amount from plan_types
        plan = next((p for p in plan_types if p['plan_type'] == plan_type), None)
        if not plan:
            msg = "Invalid subscription plan."
        else:
            plan_id = plan['id']
            start_date = datetime.now().date()
            if plan_type == 'monthly':
                end_date = start_date + timedelta(days=30)
            else:
                end_date = start_date + timedelta(days=365)
            add_subscription(branch_id, plan_id, start_date, end_date)
            msg = f"Subscription set to {plan_type} for branch {branch['name']}"
    from subscription import get_branch_subscription, is_branch_subscription_active
    subscription = get_branch_subscription(branch_id)
    active = is_branch_subscription_active(branch_id)
    amount = subscription['amount'] if subscription else 0
    # If ajax param, return JSON for table display
    if request.args.get("ajax"):
        from flask import jsonify
        return jsonify({"subscription": subscription, "active": active, "amount": amount})
    return render_template("branch_subscription.html", branch=branch, subscription=subscription, active=active, msg=msg, amount=amount, plan_types=plan_types)

@app.route("/subscriptions")
@login_required
def subscriptions_overview():
    from db import get_latest_subscriptions_all
    from flask import render_template
    subscriptions = get_latest_subscriptions_all()
    today = date.today().isoformat()
    for sub in subscriptions:
        if hasattr(sub['start_date'], 'isoformat'):
            sub['start_date'] = sub['start_date'].isoformat()
        if hasattr(sub['end_date'], 'isoformat'):
            sub['end_date'] = sub['end_date'].isoformat()
    return render_template("subscriptions.html", subscriptions=subscriptions, today=today)

@app.route("/subscription-plans/manage", methods=["GET", "POST"])
@login_required
def subscription_plans_manage():
    if not current_user.is_admin():
        flash('Only admins can manage plans.', 'danger')
        return redirect(url_for('subscription_plans_view'))
    from db import get_subscription_types
    from db import add_subscription_plan, update_subscription_plan, delete_subscription_plan
    msg = None
    if request.method == "POST":
        plan_type = request.form.get('plan_type', '').strip().lower()
        amount = request.form.get('amount')
        if plan_type and amount:
            try:
                add_subscription_plan(plan_type, float(amount))
                msg = f"Plan '{plan_type}' added."
            except Exception as e:
                msg = f"Error: {e}"
    plans = get_subscription_types()
    return render_template("subscription_plans_manage.html", plans=plans, msg=msg)

@app.route("/subscription-plans/edit/<int:plan_id>", methods=["POST"])
@login_required
def subscription_plan_edit(plan_id):
    if not current_user.is_admin():
        flash('Only admins can edit plans.', 'danger')
        return redirect(url_for('subscription_plans_manage'))
    plan_type = request.form.get('plan_type', '').strip().lower()
    amount = request.form.get('amount')
    from db import update_subscription_plan
    if plan_type and amount:
        update_subscription_plan(plan_id, plan_type, float(amount))
        flash(f"Plan updated.", 'success')
    return redirect(url_for('subscription_plans_manage'))

@app.route("/subscription-plans/delete/<int:plan_id>")
@login_required
def subscription_plan_delete(plan_id):
    if not current_user.is_admin():
        flash('Only admins can delete plans.', 'danger')
        return redirect(url_for('subscription_plans_manage'))
    from db import delete_subscription_plan
    delete_subscription_plan(plan_id)
    flash("Plan deleted.", 'success')
    return redirect(url_for('subscription_plans_manage'))

@app.route("/subscription-plans/simple")
@login_required
def subscription_plans_simple():
    if not current_user.is_admin():
        flash('Only admins can manage plans.', 'danger')
        return redirect(url_for('subscription_plans_view'))
    from db import get_subscription_types
    plans = get_subscription_types()
    return render_template("subscription_plans_simple.html", plans=plans)

@app.route("/subscription-plans/simple/add", methods=["GET", "POST"])
@login_required
def subscription_plan_add():
    if not current_user.is_admin():
        flash('Only admins can add plans.', 'danger')
        return redirect(url_for('subscription_plans_simple'))
    from db import add_subscription_plan
    msg = None
    if request.method == "POST":
        plan_type = request.form.get('plan_type', '').strip().lower()
        amount = request.form.get('amount')
        if plan_type and amount:
            try:
                add_subscription_plan(plan_type, float(amount))
                flash(f"Plan '{plan_type}' added.", 'success')
                return redirect(url_for('subscription_plans_simple'))
            except Exception as e:
                msg = f"Error: {e}"
    return render_template("subscription_plan_add.html", msg=msg)

@app.route("/subscription-plans/simple/edit/<int:plan_id>", methods=["GET", "POST"])
@login_required
def subscription_plan_edit_simple(plan_id):
    if not current_user.is_admin():
        flash('Only admins can edit plans.', 'danger')
        return redirect(url_for('subscription_plans_simple'))
    from db import get_subscription_types, update_subscription_plan
    from db import get_db_connection, dict_cursor
    msg = None
    # Get plan
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('SELECT * FROM subscription_plans WHERE id=%s', (plan_id,))
            plan = cur.fetchone()
    if not plan:
        flash('Plan not found.', 'danger')
        return redirect(url_for('subscription_plans_simple'))
    if request.method == "POST":
        plan_type = request.form.get('plan_type', '').strip().lower()
        amount = request.form.get('amount')
        if plan_type and amount:
            update_subscription_plan(plan_id, plan_type, float(amount))
            flash('Plan updated.', 'success')
            return redirect(url_for('subscription_plans_simple'))
    return render_template("subscription_plan_edit.html", plan=plan, msg=msg)

@app.route("/subscription-plans/simple/delete/<int:plan_id>")
@login_required
def subscription_plan_delete_simple(plan_id):
    if not current_user.is_admin():
        flash('Only admins can delete plans.', 'danger')
        return redirect(url_for('subscription_plans_simple'))
    from db import delete_subscription_plan
    delete_subscription_plan(plan_id)
    flash("Plan deleted.", 'success')
    return redirect(url_for('subscription_plans_simple'))

@app.route("/admin/notifications", methods=["GET", "POST"])
@login_required
def admin_notifications():
    if not current_user.is_admin():
        flash('Only admins can send notifications.', 'danger')
        return redirect(url_for('dashboard'))
    msg = None
    if request.method == "POST":
        notif_type = request.form.get('notification_type')
        recipient = request.form.get('recipient')
        subject = request.form.get('subject')
        message = request.form.get('message')
        try:
            if notif_type == 'email':
                # Send email (implement your own send_email function)
                from notifications import send_email
                send_email(recipient, subject or '', message)
                msg = f"Email sent to {recipient}."
            elif notif_type == 'whatsapp':
                # Send WhatsApp (implement your own send_whatsapp function)
                from notifications import send_whatsapp
                send_whatsapp(recipient, message)
                msg = f"WhatsApp message sent to {recipient}."
            elif notif_type == 'sms':
                # Send SMS (implement your own send_sms function)
                from notifications import send_sms
                send_sms(recipient, message)
                msg = f"SMS sent to {recipient}."
            else:
                msg = "Invalid notification type."
        except Exception as e:
            msg = f"Error: {e}"
    return render_template("admin_notifications.html", msg=msg)

@app.route('/fuel-types', methods=['GET', 'POST'])
@login_required
def fuel_types_view():
    create_fuel_types_table()
    if request.method == 'POST':
        type_id = request.form.get('type_id')
        name = request.form.get('name')
        if type_id:
            update_fuel_type(type_id, name)
        else:
            add_fuel_type(name)
        return redirect(url_for('fuel_types_view'))
    fuel_types = get_fuel_types()
    return render_template('fuel_types.html', fuel_types=fuel_types)

@app.route('/fuel-types/delete/<int:type_id>', methods=['POST'])
@login_required
def delete_fuel_type_view(type_id):
    delete_fuel_type(type_id)
    return ('', 204)

from db import get_branches, create_branch, update_branch, delete_branch

# Initialize database when app starts
with app.app_context():
    create_tables()
    db.create_expense_categories_table()
    purchase_orders.create_purchase_orders_table()
    import daily_checklist
    daily_checklist.create_daily_checklist_table()
    import totalizer
    totalizer.create_totalizer_tables()
    import credit_management
    credit_management.create_credit_tables()
    # Create product management tables
    db.create_product_tables()
    create_suppliers_table()

@app.route('/branches')
@login_required
def branches_view():
    return render_template('branches.html')

if __name__ == "__main__":
    import sys
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except Exception:
            pass
    # Test database connection
    if not db.test_db_connection():
        logger.error("Failed to connect to database")
        sys.exit(1)

    # Initialize database tables
    try:
        with app.app_context():
            create_tables()
            db.create_expense_categories_table()
            purchase_orders.create_purchase_orders_table()
            daily_checklist.create_daily_checklist_table()
            totalizer.create_totalizer_tables()
            credit_management.create_credit_tables()
            db.create_product_tables()
            create_suppliers_table()
            logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {str(e)}")
        sys.exit(1)

    app.run(debug=True, port=port)