from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import db
import ai_reports
import purchase_orders
import json
from models import (
    FuelEntry, FuelDip, Tank, SaleEntry, 
    Attendant, Attendance, Expense, 
    ReportRequest, AIReportRequest, PurchaseOrder
)

# Create blueprints for different API sections
fuel_bp = Blueprint('fuel', __name__, url_prefix='/api/fuel')
sales_bp = Blueprint('sales', __name__, url_prefix='/api/sales')
staff_bp = Blueprint('staff', __name__, url_prefix='/api/staff')
reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')
purchase_bp = Blueprint('purchase', __name__, url_prefix='/api/purchase')
checklist_bp = Blueprint('checklist', __name__, url_prefix='/api/checklist')
totalizer_bp = Blueprint('totalizer', __name__, url_prefix='/api/totalizer')
credit_bp = Blueprint('credit', __name__, url_prefix='/api/credit')

# Helper function to parse date parameters
def parse_date(date_str):
    """Parse a date string in ISO format to a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None

# Helper function to validate request data
def validate_model(data, model_class):
    """Validate request data against a model class."""
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"Validation error: {str(e)}")

# ============= Fuel Management Routes =============

@fuel_bp.route('/entries', methods=['POST'])
def add_fuel_entry():
    """Add a new fuel entry record."""
    try:
        data = request.json
        # Validate the data against the FuelEntry model
        from models import FuelEntry
        fuel_entry = validate_model(data, FuelEntry)

        # Save to database
        entry_id = db.save_fuel_entry(fuel_entry)

        # Update tank level
        tank = db.get_tanks(fuel_entry.tank_id)
        if tank:
            new_level = tank["current_level"] + fuel_entry.litres_received
            db.update_tank(fuel_entry.tank_id, {"current_level": new_level})

        return jsonify({
            "status": "success",
            "message": "Fuel entry recorded successfully",
            "id": entry_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@fuel_bp.route('/entries', methods=['GET'])
def get_fuel_entries():
    """Get fuel entries with optional filtering by tank ID."""
    try:
        tank_id = request.args.get('tank_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        entries = db.get_fuel_entries(tank_id, limit, offset)
        return jsonify(entries), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@fuel_bp.route('/dips', methods=['POST'])
def add_dip_reading():
    """Add a new dip reading record."""
    try:
        data = request.json
        # Validate the data against the FuelDip model
        from models import FuelDip
        dip = validate_model(data, FuelDip)

        # Save to database
        dip_id = db.save_dip_reading(dip)

        # Update tank level based on dip reading
        db.update_tank(dip.tank_id, {"current_level": dip.dip_reading})

        return jsonify({
            "status": "success",
            "message": "Dip reading recorded successfully",
            "id": dip_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@fuel_bp.route('/dips', methods=['GET'])
def get_dip_readings():
    """Get dip readings with optional filtering by tank ID."""
    try:
        tank_id = request.args.get('tank_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        readings = db.get_dip_readings(tank_id, limit, offset)
        return jsonify(readings), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@fuel_bp.route('/tanks', methods=['POST'])
def add_tank():
    """Add a new tank to the system."""
    try:
        data = request.json
        # Validate the data against the Tank model
        from models import Tank
        tank = validate_model(data, Tank)

        # Check if tank already exists
        existing_tank = db.get_tanks(tank.id)
        if existing_tank:
            return jsonify({
                "status": "error", 
                "message": f"Tank with ID {tank.id} already exists"
            }), 400

        # Save to database
        tank_id = db.add_tank(tank)

        return jsonify({
            "status": "success",
            "message": f"Tank {tank.id} added successfully",
            "id": tank_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@fuel_bp.route('/tanks', methods=['GET'])
def get_all_tanks():
    """Get all tanks in the system."""
    try:
        tanks = db.get_tanks()
        return jsonify(tanks), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@fuel_bp.route('/tanks/<tank_id>', methods=['GET'])
def get_tank(tank_id):
    """Get a specific tank by ID."""
    try:
        tank = db.get_tanks(tank_id)
        if not tank:
            return jsonify({
                "status": "error", 
                "message": f"Tank with ID {tank_id} not found"
            }), 404
        return jsonify(tank), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@fuel_bp.route('/tanks/<tank_id>', methods=['PATCH'])
def update_tank_details(tank_id):
    """Update details for a specific tank."""
    try:
        data = request.json
        allowed_fields = {"fuel_type", "capacity", "current_level", "status"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return jsonify({
                "status": "error", 
                "message": "No valid fields to update"
            }), 400

        # Check if tank exists
        tank = db.get_tanks(tank_id)
        if not tank:
            return jsonify({
                "status": "error", 
                "message": f"Tank with ID {tank_id} not found"
            }), 404

        # Update the tank
        success = db.update_tank(tank_id, update_data)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Tank {tank_id} updated successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to update tank"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============= Sales Management Routes =============

@sales_bp.route('/sales', methods=['POST'])
def add_sale():
    """Record a new fuel sale."""
    try:
        data = request.json
        # Validate the data against the SaleEntry model
        from models import SaleEntry
        sale = validate_model(data, SaleEntry)

        # Save to database
        sale_id = db.save_sale(sale)

        return jsonify({
            "status": "success",
            "message": "Sale recorded successfully",
            "id": sale_id,
            "total_amount": sale.litres_sold * sale.unit_price
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@sales_bp.route('/sales', methods=['GET'])
def get_sales():
    """Get sales records with optional filtering."""
    try:
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))
        attendant = request.args.get('attendant')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        sales = db.get_sales(start_date, end_date, attendant, limit, offset)
        return jsonify(sales), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@sales_bp.route('/sales/today', methods=['GET'])
def get_today_sales():
    """Get sales records for today."""
    try:
        attendant = request.args.get('attendant')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        sales = db.get_sales(today, tomorrow, attendant)
        return jsonify(sales), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@sales_bp.route('/sales/summary', methods=['GET'])
def get_sales_summary():
    """Get a summary of sales for a specified period."""
    try:
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))

        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        sales = db.get_sales(start_date, end_date)

        # Calculate summary statistics
        total_amount = sum(sale["total_amount"] for sale in sales)
        total_volume = sum(sale["litres_sold"] for sale in sales)
        transaction_count = len(sales)

        # Get sales by payment method
        payment_methods = db.get_sales_by_payment_method(start_date, end_date)

        # Get sales by attendant
        attendant_sales = db.get_sales_by_attendant(start_date, end_date)

        # Get daily sales totals
        daily_sales = db.get_daily_sales(start_date, end_date)

        return jsonify({
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "totals": {
                "sales_amount": total_amount,
                "fuel_volume": total_volume,
                "transaction_count": transaction_count
            },
            "payment_methods": payment_methods,
            "attendant_performance": attendant_sales,
            "daily_totals": daily_sales
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@sales_bp.route('/loyalty/<vehicle_number>', methods=['GET'])
def get_loyalty_points(vehicle_number):
    """Get loyalty points for a specific vehicle."""
    try:
        loyalty = db.get_loyalty_points(vehicle_number)
        return jsonify(loyalty), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============= Staff Management Routes =============

@staff_bp.route('/attendants', methods=['POST'])
def add_attendant():
    """Add a new attendant to the system."""
    try:
        data = request.json
        # Validate the data against the Attendant model
        from models import Attendant
        attendant = validate_model(data, Attendant)

        # Check if attendant already exists
        existing_attendant = db.get_attendants(attendant.employee_id)
        if existing_attendant:
            return jsonify({
                "status": "error", 
                "message": f"Attendant with employee ID {attendant.employee_id} already exists"
            }), 400

        # Save to database
        attendant_id = db.add_attendant(attendant)

        return jsonify({
            "status": "success",
            "message": f"Attendant {attendant.name} added successfully",
            "id": attendant_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/attendants', methods=['GET'])
def get_all_attendants():
    """Get all attendants in the system."""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        attendants = db.get_attendants(active_only=active_only)
        return jsonify(attendants), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/attendants/<employee_id>', methods=['GET'])
def get_attendant(employee_id):
    """Get a specific attendant by employee ID."""
    try:
        attendant = db.get_attendants(employee_id)
        if not attendant:
            return jsonify({
                "status": "error", 
                "message": f"Attendant with employee ID {employee_id} not found"
            }), 404
        return jsonify(attendant), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/attendants/<employee_id>', methods=['PATCH'])
def update_attendant_details(employee_id):
    """Update details for a specific attendant."""
    try:
        data = request.json
        allowed_fields = {"name", "role", "active"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return jsonify({
                "status": "error", 
                "message": "No valid fields to update"
            }), 400

        # Check if attendant exists
        attendant = db.get_attendants(employee_id)
        if not attendant:
            return jsonify({
                "status": "error", 
                "message": f"Attendant with employee ID {employee_id} not found"
            }), 404

        # Update the attendant
        success = db.update_attendant(employee_id, update_data)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Attendant {employee_id} updated successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to update attendant"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/attendance/check-in', methods=['POST'])
def check_in():
    """Record check-in for an attendant."""
    try:
        data = request.json
        # Validate the data against the Attendance model
        from models import Attendance
        attendance = validate_model(data, Attendance)

        # Validate that the employee exists and is active
        attendant = db.get_attendants(attendance.employee_id)
        if not attendant:
            return jsonify({
                "status": "error", 
                "message": f"Attendant with employee ID {attendance.employee_id} not found"
            }), 404

        if not attendant.get("active", False):
            return jsonify({
                "status": "error", 
                "message": f"Attendant with employee ID {attendance.employee_id} is inactive"
            }), 400

        # Set check-in time to now if not provided
        if not attendance.check_in:
            attendance.check_in = datetime.now()

        # Record attendance
        attendance_id = db.record_attendance(attendance)

        return jsonify({
            "status": "success",
            "message": f"Check-in recorded for {attendant.get('name')}",
            "id": attendance_id,
            "check_in_time": attendance.check_in.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/attendance/check-out/<int:attendance_id>', methods=['POST'])
def check_out(attendance_id):
    """Record check-out for an existing attendance record."""
    try:
        # Update attendance with check-out time
        success = db.update_attendance(attendance_id, datetime.now())

        if not success:
            return jsonify({
                "status": "error", 
                "message": f"Attendance record with ID {attendance_id} not found"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Check-out recorded successfully",
            "check_out_time": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/attendance', methods=['GET'])
def get_attendance_records():
    """Get attendance records with optional filtering."""
    try:
        employee_id = request.args.get('employee_id')
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))

        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        attendance_records = db.get_attendance(employee_id, start_date, end_date)
        return jsonify(attendance_records), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/attendance/today', methods=['GET'])
def get_today_attendance():
    """Get attendance records for today."""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        attendance_records = db.get_attendance(start_date=today, end_date=tomorrow)
        return jsonify(attendance_records), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# =============== STAFF SCHEDULING API ===============

@staff_bp.route('/schedule', methods=['GET'])
def get_schedules():
    """Get staff schedules with optional filtering."""
    employee_id = request.args.get('employee_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    branch_id = request.args.get('branch_id')

    try:
        schedules = db.get_staff_schedules(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_id
        )
        return jsonify(schedules)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@staff_bp.route('/schedule', methods=['POST'])
def create_schedule():
    """Create a new staff schedule entry."""
    data = request.json

    try:
        # Validate required fields
        required_fields = ['employee_id', 'schedule_date', 'shift', 'branch_id', 'created_by']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Set default status if not provided
        if 'status' not in data:
            data['status'] = 'scheduled'

        schedule_id = db.create_staff_schedule(data)
        return jsonify({
            'status': 'success',
            'message': 'Schedule created',
            'id': schedule_id
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@staff_bp.route('/schedule/<int:schedule_id>', methods=['PATCH'])
def update_schedule(schedule_id):
    """Update a staff schedule entry."""
    data = request.json

    try:
        success = db.update_staff_schedule(schedule_id, data)
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Schedule updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Schedule not found or no changes made'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@staff_bp.route('/schedule/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete a staff schedule entry."""
    try:
        success = db.delete_staff_schedule(schedule_id)
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Schedule deleted'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Schedule not found'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@staff_bp.route('/schedule/generate', methods=['POST'])
def generate_schedule():
    """Generate an automatic schedule for staff."""
    data = request.json

    try:
        # Validate required fields
        required_fields = ['start_date', 'end_date', 'branch_id', 'created_by']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        schedule_ids = db.generate_automatic_schedule(
            data['start_date'],
            data['end_date'],
            data['branch_id'],
            data['created_by']
        )

        return jsonify({
            'status': 'success',
            'message': f'Generated {len(schedule_ids)} schedule entries',
            'schedule_ids': schedule_ids
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@staff_bp.route('/expenses', methods=['POST'])
def add_expense():
    """Record a new expense."""
    try:
        data = request.json
        # Validate the data against the Expense model
        from models import Expense
        expense = validate_model(data, Expense)

        # Validate that the employee exists
        attendant = db.get_attendants(expense.employee_id)
        if not attendant:
            return jsonify({
                "status": "error", 
                "message": f"Attendant with employee ID {expense.employee_id} not found"
            }), 404

        # Set timestamp to now if not provided
        if not expense.timestamp:
            expense.timestamp = datetime.now()

        # Save the expense
        expense_id = db.save_expense(expense)

        return jsonify({
            "status": "success",
            "message": "Expense recorded successfully",
            "id": expense_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@staff_bp.route('/expenses', methods=['GET'])
def get_expenses():
    """Get expense records with optional filtering."""
    try:
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))
        category = request.args.get('category')
        employee_id = request.args.get('employee_id')

        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        expenses = db.get_expenses(start_date, end_date, category, employee_id)
        return jsonify(expenses), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============= Reports Routes =============

@reports_bp.route('/fuel-consumption', methods=['POST'])
def generate_fuel_consumption_report():
    """Generate a fuel consumption report for a specific period."""
    try:
        data = request.json
        # Parse request data
        from models import ReportRequest

        # Default dates if not provided
        start_date = parse_date(data.get('start_date'))
        end_date = parse_date(data.get('end_date'))

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Create report request object
        report_request = ReportRequest(
            report_type="fuel_consumption",
            start_date=start_date,
            end_date=end_date,
            tanks=data.get('tanks', [])
        )

        # Get fuel consumption data
        tank_id = report_request.tanks[0] if report_request.tanks else None
        fuel_data = db.get_fuel_consumption(report_request.start_date, report_request.end_date, tank_id=tank_id)

        # Create report object
        from models import Report
        report = Report(
            report_type="fuel_consumption",
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            data=fuel_data,
            generated_at=datetime.now()
        )

        # Save report
        report_id = db.save_report(report)

        # Return report with ID
        return jsonify({
            "status": "success",
            "message": "Fuel consumption report generated successfully",
            "report_id": report_id,
            "report": {
                "type": report.report_type,
                "period": {
                    "start_date": report.start_date.isoformat(),
                    "end_date": report.end_date.isoformat()
                },
                "data": report.data,
                "generated_at": report.generated_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@reports_bp.route('/sales', methods=['POST'])
def generate_sales_report():
    """Generate a sales report for a specific period."""
    try:
        data = request.json
        # Parse request data
        from models import ReportRequest

        # Default dates if not provided
        start_date = parse_date(data.get('start_date'))
        end_date = parse_date(data.get('end_date'))

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Create report request object
        report_request = ReportRequest(
            report_type="sales_performance",
            start_date=start_date,
            end_date=end_date
        )

        # Get sales summary data
        sales_data = {
            "payment_methods": db.get_sales_by_payment_method(start_date, end_date),
            "attendant_performance": db.get_sales_by_attendant(start_date, end_date),
            "daily_sales": db.get_daily_sales(start_date, end_date)
        }

        # Create report object
        from models import Report
        report = Report(
            report_type="sales_performance",
            start_date=start_date,
            end_date=end_date,
            data=sales_data,
            generated_at=datetime.now()
        )

        # Save report
        report_id = db.save_report(report)

        # Return report with ID
        return jsonify({
            "status": "success",
            "message": "Sales report generated successfully",
            "report_id": report_id,
            "report": {
                "type": report.report_type,
                "period": {
                    "start_date": report.start_date.isoformat(),
                    "end_date": report.end_date.isoformat()
                },
                "data": report.data,
                "generated_at": report.generated_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@reports_bp.route('/inventory', methods=['POST'])
def generate_inventory_report():
    """Generate an inventory report showing current tank levels and statistics."""
    try:
        data = request.json
        # Parse request data
        from models import ReportRequest

        # Default dates if not provided
        start_date = parse_date(data.get('start_date'))
        end_date = parse_date(data.get('end_date'))

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Create report request object
        report_request = ReportRequest(
            report_type="inventory_management",
            start_date=start_date,
            end_date=end_date
        )

        # Get tanks data
        tanks = db.get_tanks()

        # Get fuel consumption history for context
        fuel_consumption = db.get_fuel_consumption(start_date, end_date)

        # Combine data for the report
        inventory_data = {
            "current_inventory": tanks,
            "consumption_history": fuel_consumption
        }

        # Create report object
        from models import Report
        report = Report(
            report_type="inventory_management",
            start_date=start_date,
            end_date=end_date,
            data=inventory_data,
            generated_at=datetime.now()
        )

        # Save report
        report_id = db.save_report(report)

        # Return report with ID
        return jsonify({
            "status": "success",
            "message": "Inventory report generated successfully",
            "report_id": report_id,
            "report": {
                "type": report.report_type,
                "period": {
                    "start_date": report.start_date.isoformat(),
                    "end_date": report.end_date.isoformat()
                },
                "data": report.data,
                "generated_at": report.generated_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@reports_bp.route('/ai/fuel-consumption', methods=['POST'])
def generate_ai_fuel_consumption_report():
    """Generate an AI-enhanced fuel consumption report."""
    try:
        data = request.json
        # Parse request data
        from models import AIReportRequest

        # Default dates if not provided
        start_date = parse_date(data.get('start_date'))
        end_date = parse_date(data.get('end_date'))

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Create report request object
        report_request = AIReportRequest(
            report_type="fuel_consumption",
            start_date=start_date,
            end_date=end_date,
            tanks=data.get('tanks', []),
            prompt=data.get('prompt')
        )

        # Get fuel consumption data
        tank_id = report_request.tanks[0] if report_request.tanks else None
        fuel_data = db.get_fuel_consumption(start_date, end_date, tank_id=tank_id)

        # Create AI report
        ai_report = ai_reports.create_ai_report(
            fuel_data,
            "fuel_consumption",
            start_date,
            end_date,
            report_request.prompt
        )

        # Save report
        report_id = db.save_report(ai_report)

        # Return report with ID
        return jsonify({
            "status": "success",
            "message": "AI fuel consumption report generated successfully",
            "report_id": report_id,
            "report": {
                "type": ai_report.report_type,
                "period": {
                    "start_date": ai_report.start_date.isoformat(),
                    "end_date": ai_report.end_date.isoformat()
                },
                "summary": ai_report.summary,
                "recommendations": ai_report.recommendations,
                "data": ai_report.data,
                "generated_at": ai_report.generated_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@reports_bp.route('/ai/sales', methods=['POST'])
def generate_ai_sales_report():
    """Generate an AI-enhanced sales performance report."""
    try:
        data = request.json
        # Parse request data
        from models import AIReportRequest

        # Default dates if not provided
        start_date = parse_date(data.get('start_date'))
        end_date = parse_date(data.get('end_date'))

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Create report request object
        report_request = AIReportRequest(
            report_type="sales_performance",
            start_date=start_date,
            end_date=end_date,
            prompt=data.get('prompt')
        )

        # Get sales summary data
        sales_data = {
            "payment_methods": db.get_sales_by_payment_method(start_date, end_date),
            "attendant_performance": db.get_sales_by_attendant(start_date, end_date),
            "daily_sales": db.get_daily_sales(start_date, end_date)
        }

        # Create AI report
        ai_report = ai_reports.create_ai_report(
            sales_data,
            "sales_performance",
            start_date,
            end_date,
            report_request.prompt
        )

        # Save report
        report_id = db.save_report(ai_report)

        # Return report with ID
        return jsonify({
            "status": "success",
            "message": "AI sales report generated successfully",
            "report_id": report_id,
            "report": {
                "type": ai_report.report_type,
                "period": {
                    "start_date": ai_report.start_date.isoformat(),
                    "end_date": ai_report.end_date.isoformat()
                },
                "summary": ai_report.summary,
                "recommendations": ai_report.recommendations,
                "data": ai_report.data,
                "generated_at": ai_report.generated_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@reports_bp.route('/ai/inventory', methods=['POST'])
def generate_ai_inventory_report():
    """Generate an AI-enhanced inventory management report."""
    try:
        data = request.json
        # Parse request data
        from models import AIReportRequest

        # Default dates if not provided
        start_date = parse_date(data.get('start_date'))
        end_date = parse_date(data.get('end_date'))

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Create report request object
        report_request = AIReportRequest(
            report_type="inventory_management",
            start_date=start_date,
            end_date=end_date,
            prompt=data.get('prompt')
        )

        # Get tanks data
        tanks = db.get_tanks()

        # Get fuel consumption history for context
        fuel_consumption = db.get_fuel_consumption(start_date, end_date)

        # Combine data for the report
        inventory_data = {
            "current_inventory": tanks,
            "consumption_history": fuel_consumption
        }

        # Create AI report
        ai_report = ai_reports.create_ai_report(
            inventory_data,
            "inventory_management",
            start_date,
            end_date,
            report_request.prompt
        )

        # Save report
        report_id = db.save_report(ai_report)

        # Return report with ID
        return jsonify({
            "status": "success",
            "message": "AI inventory report generated successfully",
            "report_id": report_id,
            "report": {
                "type": ai_report.report_type,
                "period": {
                    "start_date": ai_report.start_date.isoformat(),
                    "end_date": ai_report.end_date.isoformat()
                },
                "summary": ai_report.summary,
                "recommendations": ai_report.recommendations,
                "data": ai_report.data,
                "generated_at": ai_report.generated_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@reports_bp.route('', methods=['GET'])
def get_reports():
    """Get previously generated reports."""
    try:
        report_type = request.args.get('report_type')
        limit = int(request.args.get('limit', 10))

        reports = db.get_reports(report_type, limit)
        return jsonify(reports), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@reports_bp.route('/<int:report_id>', methods=['GET'])
def get_report_by_id(report_id):
    """Get a specific report by ID."""
    try:
        report = db.get_report_by_id(report_id)
        if not report:
            return jsonify({
                "status": "error", 
                "message": f"Report with ID {report_id} not found"
            }), 404
        return jsonify(report), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============= Purchase Order Routes =============

@purchase_bp.route('/orders', methods=['POST'])
def create_purchase_order():
    """Create a new purchase order request."""
    try:
        data = request.json
        # Validate the data against the PurchaseOrder model
        order = validate_model(data, PurchaseOrder)

        # Save to database
        order_id = purchase_orders.save_purchase_order(order)

        return jsonify({
            "status": "success",
            "message": "Purchase order created successfully",
            "id": order_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@purchase_bp.route('/orders', methods=['GET'])
def get_purchase_orders():
    """Get purchase orders with optional filtering."""
    try:
        branch_id = request.args.get('branch_id')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        orders = purchase_orders.get_purchase_orders(branch_id, status, limit, offset)
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@purchase_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_purchase_order(order_id):
    """Get details of a specific purchase order."""
    try:
        order = purchase_orders.get_purchase_order_by_id(order_id)
        if not order:
            return jsonify({
                "status": "error", 
                "message": f"Purchase order with ID {order_id} not found"
            }), 404
        return jsonify(order), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@purchase_bp.route('/orders/<int:order_id>', methods=['PATCH'])
def update_purchase_order(order_id):
    """Update a purchase order."""
    try:
        data = request.json
        allowed_fields = {
            "product_type", "quantity", "unit_price", "total_amount", 
            "supplier", "expected_delivery_date", "notes"
        }
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return jsonify({
                "status": "error", 
                "message": "No valid fields to update"
            }), 400

        # Update the purchase order
        success = purchase_orders.update_purchase_order(order_id, update_data)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Purchase order {order_id} updated successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to update purchase order or order not found"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@purchase_bp.route('/orders/<int:order_id>/approve', methods=['POST'])
def approve_purchase_order(order_id):
    """Approve a purchase order request."""
    try:
        data = request.json
        approved_by = data.get('approved_by')

        if not approved_by:
            return jsonify({
                "status": "error", 
                "message": "Approved by is required"
            }), 400

        # Get optional updates
        allowed_fields = {
            "product_type", "quantity", "unit_price", "total_amount", 
            "supplier", "expected_delivery_date", "notes"
        }
        updates = {k: v for k, v in data.items() if k in allowed_fields}

        # Approve the purchase order
        success = purchase_orders.approve_purchase_order(order_id, approved_by, updates)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Purchase order {order_id} approved successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to approve purchase order or order not found"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@purchase_bp.route('/orders/<int:order_id>/reject', methods=['POST'])
def reject_purchase_order(order_id):
    """Reject a purchase order request."""
    try:
        data = request.json
        approved_by = data.get('approved_by')
        reason = data.get('reason')

        if not approved_by:
            return jsonify({
                "status": "error", 
                "message": "Approved by is required"
            }), 400

        # Reject the purchase order
        success = purchase_orders.reject_purchase_order(order_id, approved_by, reason)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Purchase order {order_id} rejected successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to reject purchase order or order not found"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@purchase_bp.route('/orders/<int:order_id>/payment', methods=['POST'])
def update_payment_status(order_id):
    """Update the payment status of a purchase order."""
    try:
        data = request.json
        payment_status = data.get('payment_status')
        payment_amount = data.get('payment_amount')
        payment_reference = data.get('payment_reference')

        if not payment_status:
            return jsonify({
                "status": "error", 
                "message": "Payment status is required"
            }), 400

        # Update payment status
        success = purchase_orders.update_payment_status(
            order_id, payment_status, payment_amount, payment_reference
        )

        if success:
            return jsonify({
                "status": "success",
                "message": f"Payment status updated to '{payment_status}' successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to update payment status or order not found"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@purchase_bp.route('/orders/<int:order_id>/complete', methods=['POST'])
def complete_purchase_order(order_id):
    """Mark a purchase order as completed."""
    try:
        # Complete the purchase order
        success = purchase_orders.complete_purchase_order(order_id)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Purchase order {order_id} marked as completed"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to complete purchase order or order not found"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============= Totalizer Readings Routes =============

@totalizer_bp.route('/readings', methods=['POST'])
def add_totalizer_reading():
    """Add a new totalizer reading record."""
    try:
        data = request.json
        # Validate the data against the TotalizerReading model
        from models import TotalizerReading
        import totalizer

        reading = validate_model(data, TotalizerReading)

        # Save to database
        reading_id = totalizer.save_totalizer_reading(reading)

        # If this is a closing reading, calculate and save the sales data
        if reading.reading_type == 'closing':
            sales_id = totalizer.calculate_and_save_shift_sales(reading)

            return jsonify({
                "status": "success",
                "message": "Closing reading recorded and sales calculated successfully",
                "reading_id": reading_id,
                "sales_id": sales_id
            }), 201
        else:
            return jsonify({
                "status": "success",
                "message": "Opening reading recorded successfully",
                "id": reading_id
            }), 201

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@totalizer_bp.route('/readings', methods=['GET'])
def get_totalizer_readings():
    """Get totalizer readings with optional filtering."""
    try:
        import totalizer

        pump_id = request.args.get('pump_id')
        nozzle_id = request.args.get('nozzle_id')
        pumpman_id = request.args.get('pumpman_id')
        reading_type = request.args.get('reading_type')
        branch_id = request.args.get('branch_id')
        shift = request.args.get('shift')
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        readings = totalizer.get_totalizer_readings(
            pump_id, nozzle_id, pumpman_id, reading_type, 
            branch_id, shift, start_date, end_date, limit, offset
        )
        return jsonify(readings), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@totalizer_bp.route('/sales', methods=['GET'])
def get_shift_sales():
    """Get shift sales with optional filtering."""
    try:
        import totalizer

        pump_id = request.args.get('pump_id')
        nozzle_id = request.args.get('nozzle_id')
        pumpman_id = request.args.get('pumpman_id')
        product_type = request.args.get('product_type')
        branch_id = request.args.get('branch_id')
        shift = request.args.get('shift')
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        sales = totalizer.get_shift_sales(
            pump_id, nozzle_id, pumpman_id, product_type, 
            branch_id, shift, start_date, end_date, limit, offset
        )
        return jsonify(sales), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@totalizer_bp.route('/sales/summary/product', methods=['GET'])
def get_sales_summary_by_product():
    """Get sales summary grouped by product type."""
    try:
        import totalizer

        branch_id = request.args.get('branch_id')
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))

        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        summary = totalizer.get_sales_summary_by_product(branch_id, start_date, end_date)
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@totalizer_bp.route('/sales/summary/pumpman', methods=['GET'])
def get_sales_summary_by_pumpman():
    """Get sales summary grouped by pumpman."""
    try:
        import totalizer

        branch_id = request.args.get('branch_id')
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))

        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        summary = totalizer.get_sales_summary_by_pumpman(branch_id, start_date, end_date)
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============= Daily Checklist Routes =============

@checklist_bp.route('/checklists', methods=['POST'])
def add_daily_checklist():
    """Add a new daily checklist entry."""
    try:
        data = request.json
        # Validate the data against the DailyChecklist model
        from models import DailyChecklist
        checklist = validate_model(data, DailyChecklist)

        import daily_checklist
        # Save to database
        checklist_id = daily_checklist.save_checklist(checklist)

        return jsonify({
            "status": "success",
            "message": "Daily checklist recorded successfully",
            "id": checklist_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@checklist_bp.route('/checklists', methods=['GET'])
def get_daily_checklists():
    """Get daily checklists with optional filtering."""
    try:
        branch_id = request.args.get('branch_id')
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        import daily_checklist
        checklists = daily_checklist.get_checklists(branch_id, start_date, end_date, limit, offset)
        return jsonify(checklists), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@checklist_bp.route('/checklists/<int:checklist_id>', methods=['GET'])
def get_checklist(checklist_id):
    """Get a specific checklist by ID."""
    try:
        import daily_checklist
        checklist = daily_checklist.get_checklist_by_id(checklist_id)
        if not checklist:
            return jsonify({
                "status": "error", 
                "message": f"Checklist with ID {checklist_id} not found"
            }), 404
        return jsonify(checklist), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@checklist_bp.route('/checklists/today', methods=['GET'])
def get_today_checklist():
    """Get today's checklist for a specific branch."""
    try:
        branch_id = request.args.get('branch_id')
        if not branch_id:
            return jsonify({
                "status": "error", 
                "message": "Branch ID is required"
            }), 400

        import daily_checklist
        today = datetime.now()
        checklist = daily_checklist.get_checklist_by_date(branch_id, today)

        # If no checklist exists for today, return an empty response
        if not checklist:
            return jsonify({
                "status": "info",
                "message": "No checklist found for today",
                "data": None
            }), 200

        return jsonify(checklist), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@checklist_bp.route('/checklists/<int:checklist_id>', methods=['PATCH'])
def update_checklist(checklist_id):
    """Update a checklist."""
    try:
        data = request.json
        allowed_fields = {
            "dispenser_test_done", "pump_cleaning_done", 
            "bathroom_cleaning_done", "notes"
        }
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return jsonify({
                "status": "error", 
                "message": "No valid fields to update"
            }), 400

        import daily_checklist
        # Check if checklist exists
        checklist = daily_checklist.get_checklist_by_id(checklist_id)
        if not checklist:
            return jsonify({
                "status": "error", 
                "message": f"Checklist with ID {checklist_id} not found"
            }), 404

        # Update the checklist
        success = daily_checklist.update_checklist(checklist_id, update_data)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Checklist updated successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to update checklist"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@checklist_bp.route('/checklists/<int:checklist_id>', methods=['DELETE'])
def delete_checklist(checklist_id):
    """Delete a checklist."""
    try:
        import daily_checklist
        # Check if checklist exists
        checklist = daily_checklist.get_checklist_by_id(checklist_id)
        if not checklist:
            return jsonify({
                "status": "error", 
                "message": f"Checklist with ID {checklist_id} not found"
            }), 404

        # Delete the checklist
        success = daily_checklist.delete_checklist(checklist_id)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Checklist deleted successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to delete checklist"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============= Credit Management Routes =============

@credit_bp.route('/customers', methods=['POST'])
def add_credit_customer():
    """Add a new credit customer."""
    try:
        data = request.json
        # Validate the data against the CreditCustomer model
        from models import CreditCustomer
        import credit_management

        customer = validate_model(data, CreditCustomer)

        # Check if customer already exists
        existing_customer = credit_management.get_credit_customers(customer.customer_id)
        if existing_customer:
            return jsonify({
                "status": "error", 
                "message": f"Customer with ID {customer.customer_id} already exists"
            }), 400

        # Save to database
        customer_id = credit_management.add_credit_customer(customer)

        return jsonify({
            "status": "success",
            "message": f"Credit customer {customer.name} added successfully",
            "id": customer_id
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@credit_bp.route('/customers', methods=['GET'])
def get_credit_customers():
    """Get credit customers with optional filtering."""
    try:
        import credit_management

        customer_id = request.args.get('customer_id')
        customer_type = request.args.get('customer_type')
        status = request.args.get('status', 'active')
        branch_id = request.args.get('branch_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        customers = credit_management.get_credit_customers(
            customer_id, customer_type, status, branch_id, limit, offset
        )

        if customer_id and not customers:
            return jsonify({
                "status": "error", 
                "message": f"Customer with ID {customer_id} not found"
            }), 404

        return jsonify(customers), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@credit_bp.route('/customers/<customer_id>', methods=['PATCH'])
def update_credit_customer(customer_id):
    """Update credit customer information."""
    try:
        import credit_management
        data = request.json

        # Check if customer exists
        customer = credit_management.get_credit_customers(customer_id)
        if not customer:
            return jsonify({
                "status": "error", 
                "message": f"Customer with ID {customer_id} not found"
            }), 404

        # Update customer
        success = credit_management.update_credit_customer(customer_id, data)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Customer {customer_id} updated successfully"
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to update customer"
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@credit_bp.route('/transactions', methods=['POST'])
def add_credit_transaction():
    """Record a new credit transaction (purchase or payment)."""
    try:
        data = request.json
        # Validate the data against the CreditTransaction model
        from models import CreditTransaction
        import credit_management

        transaction = validate_model(data, CreditTransaction)

        # Check if customer exists
        customer = credit_management.get_credit_customers(transaction.customer_id)
        if not customer:
            return jsonify({
                "status": "error", 
                "message": f"Customer with ID {transaction.customer_id} not found"
            }), 404

        # Check if customer is active
        if customer['status'] != 'active':
            return jsonify({
                "status": "error", 
                "message": f"Customer with ID {transaction.customer_id} is not active"
            }), 400

        # Record transaction
        transaction_id, new_balance = credit_management.record_credit_transaction(transaction)

        return jsonify({
            "status": "success",
            "message": f"{transaction.transaction_type.capitalize()} recorded successfully",
            "id": transaction_id,
            "new_balance": new_balance
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@credit_bp.route('/transactions', methods=['GET'])
def get_credit_transactions():
    """Get credit transactions with optional filtering."""
    try:
        import credit_management

        customer_id = request.args.get('customer_id')
        transaction_type = request.args.get('transaction_type')
        branch_id = request.args.get('branch_id')
        start_date = parse_date(request.args.get('start_date'))
        end_date = parse_date(request.args.get('end_date'))
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        transactions = credit_management.get_credit_transactions(
            customer_id, transaction_type, branch_id, start_date, end_date, limit, offset
        )

        return jsonify(transactions), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@credit_bp.route('/customers/<customer_id>/history', methods=['GET'])
def get_customer_history(customer_id):
    """Get transaction history for a specific customer."""
    try:
        import credit_management

        limit = int(request.args.get('limit', 50))

        history = credit_management.get_customer_transaction_history(customer_id, limit)

        if not history:
            return jsonify({
                "status": "error", 
                "message": f"Customer with ID {customer_id} not found"
            }), 404

        return jsonify(history), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@credit_bp.route('/due-payments', methods=['GET'])
def get_due_payments():
    """Get customers with overdue payments."""
    try:
        import credit_management

        branch_id = request.args.get('branch_id')
        days_overdue = int(request.args.get('days_overdue', 30))
        min_amount = float(request.args.get('min_amount', 1000))

        overdue_customers = credit_management.get_due_payments(branch_id, days_overdue, min_amount)

        return jsonify(overdue_customers), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@credit_bp.route('/summary', methods=['GET'])
def get_credit_summary():
    """Get credit summary statistics grouped by customer type."""
    try:
        import credit_management

        branch_id = request.args.get('branch_id')

        summary = credit_management.get_credit_summary_by_type(branch_id)

        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500