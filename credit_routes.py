from flask import Blueprint, request, jsonify
from datetime import datetime
import credit_management
from models import CreditCustomer, CreditTransaction, CreditCustomerInDB, CreditTransactionInDB

credit_bp = Blueprint('credit', __name__, url_prefix='/api/credit')

@credit_bp.route('/customers', methods=['POST'])
def add_credit_customer():
    """Add a new credit customer."""
    try:
        # Validate customer data
        data = request.get_json()
        customer = CreditCustomer(**data)
        customer_id = credit_management.add_credit_customer(customer)
        
        return jsonify({
            "status": "success",
            "message": "Credit customer added successfully",
            "customer_id": customer_id
        }), 201
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@credit_bp.route('/customers', methods=['GET'])
def get_credit_customers():
    """Get credit customers with optional filtering."""
    try:
        customer_id = request.args.get('customer_id')
        customer_type = request.args.get('customer_type')
        status = request.args.get('status', 'active')
        branch_id = request.args.get('branch_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        customers = credit_management.get_credit_customers(
            customer_id, customer_type, status, branch_id, limit, offset
        )
        
        return jsonify(customers)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@credit_bp.route('/customers/<customer_id>', methods=['PATCH'])
def update_credit_customer(customer_id):
    """Update credit customer information."""
    try:
        data = request.get_json()
        updated = credit_management.update_credit_customer(customer_id, data)
        
        if updated:
            return jsonify({
                "status": "success",
                "message": "Customer updated successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Customer not found or no valid fields to update"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@credit_bp.route('/transactions', methods=['POST'])
def add_credit_transaction():
    """Record a new credit transaction (purchase or payment)."""
    try:
        # Validate transaction data
        data = request.get_json()
        transaction = CreditTransaction(**data)
        
        transaction_id, new_balance = credit_management.record_credit_transaction(transaction)
        
        return jsonify({
            "status": "success",
            "message": f"{transaction.transaction_type.capitalize()} recorded successfully",
            "transaction_id": transaction_id,
            "new_balance": new_balance
        }), 201
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@credit_bp.route('/transactions', methods=['GET'])
def get_credit_transactions():
    """Get credit transactions with optional filtering."""
    try:
        customer_id = request.args.get('customer_id')
        transaction_type = request.args.get('transaction_type')
        branch_id = request.args.get('branch_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Parse dates if provided
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        transactions = credit_management.get_credit_transactions(
            customer_id, transaction_type, branch_id, start_date, end_date, limit, offset
        )
        
        return jsonify(transactions)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@credit_bp.route('/customers/<customer_id>/history', methods=['GET'])
def get_customer_history(customer_id):
    """Get transaction history for a specific customer."""
    try:
        limit = int(request.args.get('limit', 50))
        
        history = credit_management.get_customer_transaction_history(customer_id, limit)
        
        if history:
            return jsonify(history)
        else:
            return jsonify({
                "status": "error",
                "message": "Customer not found"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@credit_bp.route('/due-payments', methods=['GET'])
def get_due_payments():
    """Get customers with overdue payments."""
    try:
        branch_id = request.args.get('branch_id')
        days_overdue = int(request.args.get('days_overdue', 30))
        min_amount = float(request.args.get('min_amount', 1000))
        
        # Convert min_amount to int to match function parameter type
        min_amount_int = int(min_amount)
        customers = credit_management.get_due_payments(branch_id, days_overdue, min_amount_int)
        
        return jsonify(customers)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@credit_bp.route('/customers/<customer_id>/eligibility', methods=['GET'])
def check_credit_eligibility(customer_id):
    """Check if a customer is eligible for credit."""
    try:
        eligibility = credit_management.check_credit_eligibility(customer_id)
        return jsonify(eligibility)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@credit_bp.route('/summary', methods=['GET'])
def get_credit_summary():
    """Get credit summary statistics grouped by customer type."""
    try:
        branch_id = request.args.get('branch_id')
        
        summary = credit_management.get_credit_summary_by_type(branch_id)
        
        return jsonify(summary)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500