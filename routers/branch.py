"""
Branch Management API endpoints
"""
import json
import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from branch_utils import get_branch_data, add_branch_info_to_data

# Create blueprint
branch_bp = Blueprint('branch', __name__, url_prefix='/api/branch')

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Branch routes
@branch_bp.route('/branches', methods=['GET'])
def get_branches():
    """Get all branches or a specific branch by ID"""
    try:
        branch_id = request.args.get('branch_id')
        branches = get_branch_data(branch_id)
        logging.info(f"Fetched branches: {branches}")
        return jsonify(branches)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@branch_bp.route('/branches', methods=['POST'])
def add_branch():
    """Add a new branch"""
    try:
        branch_data = request.json
        required_fields = ['id', 'name', 'location']
        
        # Validate required fields
        for field in required_fields:
            if field not in branch_data or not branch_data[field]:
                return jsonify({
                    "status": "error", 
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Get existing branches
        branches = get_branch_data()
        
        # Ensure branches is a list
        if branches is None:
            branches = []
        
        # Check if branch ID already exists
        branch_exists = False
        if branches:
            for branch in branches:
                if isinstance(branch, dict) and 'id' in branch and branch['id'] == branch_data['id']:
                    branch_exists = True
                    break
        
        if branch_exists:
            return jsonify({
                "status": "error", 
                "message": f"Branch ID '{branch_data['id']}' already exists"
            }), 400
            
        # Add new branch to existing branches
        branches.append(branch_data)
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Save updated branches
        with open('data/branches.json', 'w') as f:
            json.dump(branches, f, indent=2)
            
        return jsonify(branch_data), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@branch_bp.route('/branches/<branch_id>', methods=['PATCH'])
def update_branch(branch_id):
    """Update a branch"""
    try:
        updates = request.json
        branches = get_branch_data()
        
        # Ensure branches is a list
        if branches is None or not isinstance(branches, list):
            return jsonify({"status": "error", "message": "No branches found"}), 404
        
        # Find branch to update
        branch_idx = None
        for idx, branch in enumerate(branches):
            if isinstance(branch, dict) and 'id' in branch and branch['id'] == branch_id:
                branch_idx = idx
                break
                
        if branch_idx is None:
            return jsonify({"status": "error", "message": "Branch not found"}), 404
            
        # Update branch fields
        for key, value in updates.items():
            branches[branch_idx][key] = value
            
        # Add updated_at timestamp
        branches[branch_idx]['updated_at'] = datetime.now().isoformat()
        
        # Save updated branches
        with open('data/branches.json', 'w') as f:
            json.dump(branches, f, indent=2)
            
        return jsonify(branches[branch_idx])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@branch_bp.route('/branches/<branch_id>', methods=['DELETE'])
def delete_branch(branch_id):
    """Delete a branch and its related data"""
    try:
        from db import get_db_connection, dict_cursor
        
        branches = get_branch_data()
        
        # Ensure branches is a list
        if branches is None or not isinstance(branches, list):
            return jsonify({"status": "error", "message": "No branches found"}), 404
        
        # Find branch to delete
        branch_idx = None
        for idx, branch in enumerate(branches):
            if isinstance(branch, dict) and 'id' in branch and branch['id'] == branch_id:
                branch_idx = idx
                break
                
        if branch_idx is None:
            return jsonify({"status": "error", "message": "Branch not found"}), 404
            
        # Get branch before removal for reference in cleanup
        deleted_branch = branches[branch_idx]
        
        # Remove branch from branches list
        branches.pop(branch_idx)
        
        # Save updated branches
        with open('data/branches.json', 'w') as f:
            json.dump(branches, f, indent=2)
        
        # Clean up related data
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # List of tables to check for branch_id column
                    branch_related_tables = [
                        'sales', 'dip_readings', 'fuel_entries', 'attendance',
                        'expenses', 'credit_customers', 'credit_transactions',
                        'daily_checklist', 'staff_schedules', 'products'
                    ]
                    
                    # Check each table and clean up records if branch_id column exists
                    for table in branch_related_tables:
                        try:
                            # Check if table exists and has branch_id column
                            cursor.execute(f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = '{table}' 
                                AND column_name = 'branch_id'
                            """)
                            if cursor.fetchone():
                                # Check if table has status column
                                cursor.execute(f"""
                                    SELECT column_name 
                                    FROM information_schema.columns 
                                    WHERE table_name = '{table}' 
                                    AND column_name = 'status'
                                """)
                                has_status = cursor.fetchone() is not None
                                
                                # Set branch_id to NULL for records from deleted branch
                                if has_status:
                                    cursor.execute(f"""
                                        UPDATE {table} 
                                        SET branch_id = NULL, status = 'archived'
                                        WHERE branch_id = %s
                                    """, (branch_id,))
                                else:
                                    cursor.execute(f"""
                                        UPDATE {table} 
                                        SET branch_id = NULL
                                        WHERE branch_id = %s
                                    """, (branch_id,))
                        except Exception as table_error:
                            # Log error but continue with deletion
                            print(f"Warning: Error cleaning up table {table}: {table_error}")
                    
                    conn.commit()
        except Exception as db_error:
            print(f"Warning: Error during data cleanup after branch deletion: {db_error}")
            # Continue with deletion even if cleanup fails
            
        return jsonify({
            "status": "success", 
            "message": f"Branch '{deleted_branch['name']}' deleted successfully and related data archived"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500