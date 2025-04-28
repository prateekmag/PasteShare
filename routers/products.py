"""
Product Management API endpoints
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

import db
from branch_utils import get_branch_filter_param

# Create blueprint
products_bp = Blueprint('products', __name__, url_prefix='/api/products')

# Product Categories routes
@products_bp.route('/categories', methods=['GET'])
def get_product_categories():
    """Get all product categories or filter by branch_id"""
    try:
        branch_id = request.args.get('branch_id')
        categories = db.get_product_categories(branch_id)
        return jsonify(categories)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/categories', methods=['POST'])
def add_product_category():
    """Add a new product category (with option for all branches)"""
    try:
        category_data = request.json
        required_fields = ['id', 'name']
        
        # Validate required fields
        for field in required_fields:
            if field not in category_data or not category_data[field]:
                return jsonify({
                    "status": "error", 
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Check if this is an all-branches operation
        apply_to_all_branches = category_data.get('apply_to_all_branches', False)
        
        if apply_to_all_branches:
            # Import branch utilities
            from branch_utils import get_branch_data
            
            # Get all branches
            branches = get_branch_data()
            if not branches or not isinstance(branches, list):
                return jsonify({
                    "status": "error", 
                    "message": "No branches found to add category to"
                }), 400
                
            # Create categories for all branches
            added_categories = []
            
            for branch in branches:
                if isinstance(branch, dict) and 'id' in branch:
                    # Create unique category ID for this branch
                    branch_specific_id = f"{category_data['id']}_{branch['id']}"
                    
                    # Create category object for this branch
                    category = {
                        "id": branch_specific_id,
                        "name": category_data['name'],
                        "description": category_data.get('description'),
                        "branch_id": branch['id']
                    }
                    
                    try:
                        # Add category to database
                        new_category_id = db.add_product_category(category)
                        category["db_id"] = new_category_id
                        added_categories.append(category)
                    except Exception as branch_error:
                        print(f"Error adding category to branch {branch['id']}: {str(branch_error)}")
                        # Continue with other branches even if one fails
            
            if not added_categories:
                return jsonify({
                    "status": "error", 
                    "message": "Failed to add category to any branch"
                }), 500
                
            return jsonify({
                "status": "success",
                "message": f"Category added to {len(added_categories)} branches",
                "categories": added_categories
            }), 201
        else:
            # Traditional single-branch operation
            if 'branch_id' not in category_data or not category_data['branch_id']:
                return jsonify({
                    "status": "error", 
                    "message": "Missing required field: branch_id"
                }), 400
            
            # Create category object
            category = {
                "id": category_data['id'],
                "name": category_data['name'],
                "description": category_data.get('description'),
                "branch_id": category_data['branch_id']
            }
            
            # Add category to database
            new_category_id = db.add_product_category(category)
            category["db_id"] = new_category_id
            return jsonify(category), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/categories/<category_id>', methods=['GET'])
def get_product_category(category_id):
    """Get a specific product category by ID"""
    try:
        categories = db.get_product_categories()
        category = next((c for c in categories if c['id'] == category_id), None)
        
        if not category:
            return jsonify({"status": "error", "message": "Category not found"}), 404
            
        return jsonify(category)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/categories/<category_id>', methods=['PATCH'])
def update_product_category(category_id):
    """Update a product category"""
    try:
        updates = request.json
        updated_category = db.update_product_category(category_id, updates)
        
        if not updated_category:
            return jsonify({"status": "error", "message": "Category not found"}), 404
            
        return jsonify(updated_category)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/categories/<category_id>', methods=['DELETE'])
def delete_product_category(category_id):
    """Delete a product category"""
    try:
        result = db.delete_product_category(category_id)
        
        if not result:
            return jsonify({"status": "error", "message": "Category not found or could not be deleted"}), 404
            
        return jsonify({"status": "success", "message": "Category deleted successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Products routes
@products_bp.route('/products', methods=['GET'])
def get_products():
    """Get all products with optional filtering"""
    try:
        branch_id = request.args.get('branch_id')
        category_id = request.args.get('category_id')
        
        is_active = None
        if 'is_active' in request.args:
            is_active = request.args.get('is_active').lower() == 'true'
            
        search = request.args.get('search')
        
        products = db.get_products(branch_id, category_id, is_active, search)
        return jsonify(products)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/products/low-stock', methods=['GET'])
def get_low_stock_products():
    """Get products with stock levels below minimum threshold"""
    try:
        branch_id = request.args.get('branch_id')
        low_stock_products = db.get_low_stock_products(branch_id)
        return jsonify(low_stock_products)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/products', methods=['POST'])
def add_product():
    """Add a new product (with option for all branches)"""
    try:
        product_data = request.json
        required_fields = ['id', 'name', 'unit_price', 'unit_of_measure']
        
        # Validate basic required fields
        for field in required_fields:
            if field not in product_data or product_data[field] is None:
                return jsonify({
                    "status": "error", 
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Check if this is an all-branches operation
        apply_to_all_branches = product_data.get('apply_to_all_branches', False)
        
        if apply_to_all_branches:
            # Import branch utilities
            from branch_utils import get_branch_data
            
            # Validate category information for all-branch operation
            if 'category_base_id' not in product_data:
                return jsonify({
                    "status": "error", 
                    "message": "For all-branch products, category_base_id is required"
                }), 400
                
            # Get all branches
            branches = get_branch_data()
            if not branches or not isinstance(branches, list):
                return jsonify({
                    "status": "error", 
                    "message": "No branches found to add product to"
                }), 400
                
            # Create products for all branches
            added_products = []
            
            for branch in branches:
                if isinstance(branch, dict) and 'id' in branch:
                    # Create unique product ID for this branch
                    branch_specific_id = f"{product_data['id']}_{branch['id']}"
                    
                    # Create branch-specific category ID
                    branch_specific_category_id = f"{product_data['category_base_id']}_{branch['id']}"
                    
                    # Create product object for this branch
                    product = {
                        "id": branch_specific_id,
                        "name": product_data['name'],
                        "category_id": branch_specific_category_id,
                        "description": product_data.get('description'),
                        "unit_price": float(product_data['unit_price']),
                        "cost_price": float(product_data['cost_price']) if product_data.get('cost_price') is not None else None,
                        "stock_quantity": float(product_data.get('stock_quantity', 0)),
                        "minimum_stock_level": float(product_data['minimum_stock_level']) if product_data.get('minimum_stock_level') is not None else None,
                        "unit_of_measure": product_data['unit_of_measure'],
                        "is_fuel": bool(product_data.get('is_fuel', False)),
                        "is_active": bool(product_data.get('is_active', True)),
                        "barcode": product_data.get('barcode'),
                        "image_url": product_data.get('image_url'),
                        "branch_id": branch['id']
                    }
                    
                    try:
                        # Add product to database
                        new_product_id = db.add_product(product)
                        product["db_id"] = new_product_id
                        added_products.append(product)
                    except Exception as branch_error:
                        print(f"Error adding product to branch {branch['id']}: {str(branch_error)}")
                        # Continue with other branches even if one fails
            
            if not added_products:
                return jsonify({
                    "status": "error", 
                    "message": "Failed to add product to any branch"
                }), 500
                
            return jsonify({
                "status": "success",
                "message": f"Product added to {len(added_products)} branches",
                "products": added_products
            }), 201
        else:
            # Traditional single-branch operation
            # Additional required fields for single branch
            single_branch_fields = ['category_id', 'branch_id']
            
            # Validate single branch required fields
            for field in single_branch_fields:
                if field not in product_data or product_data[field] is None:
                    return jsonify({
                        "status": "error", 
                        "message": f"Missing required field for single branch operation: {field}"
                    }), 400
            
            # Create product object
            product = {
                "id": product_data['id'],
                "name": product_data['name'],
                "category_id": product_data['category_id'],
                "description": product_data.get('description'),
                "unit_price": float(product_data['unit_price']),
                "cost_price": float(product_data['cost_price']) if product_data.get('cost_price') is not None else None,
                "stock_quantity": float(product_data.get('stock_quantity', 0)),
                "minimum_stock_level": float(product_data['minimum_stock_level']) if product_data.get('minimum_stock_level') is not None else None,
                "unit_of_measure": product_data['unit_of_measure'],
                "is_fuel": bool(product_data.get('is_fuel', False)),
                "is_active": bool(product_data.get('is_active', True)),
                "barcode": product_data.get('barcode'),
                "image_url": product_data.get('image_url'),
                "branch_id": product_data['branch_id']
            }
            
            # Add product to database
            new_product_id = db.add_product(product)
            product["db_id"] = new_product_id
            return jsonify(product), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/products/<product_id>', methods=['GET'])
def get_product_by_id(product_id):
    """Get a specific product by ID"""
    try:
        product = db.get_product_by_id(product_id)
        
        if not product:
            return jsonify({"status": "error", "message": "Product not found"}), 404
            
        return jsonify(product)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/products/<product_id>', methods=['PATCH'])
def update_product(product_id):
    """Update a product"""
    try:
        updates = request.json
        
        # Convert numeric fields
        if 'unit_price' in updates:
            updates['unit_price'] = float(updates['unit_price'])
        if 'cost_price' in updates:
            updates['cost_price'] = float(updates['cost_price']) if updates['cost_price'] is not None else None
        if 'stock_quantity' in updates:
            updates['stock_quantity'] = float(updates['stock_quantity'])
        if 'minimum_stock_level' in updates:
            updates['minimum_stock_level'] = float(updates['minimum_stock_level']) if updates['minimum_stock_level'] is not None else None
        
        # Convert boolean fields
        if 'is_fuel' in updates:
            updates['is_fuel'] = bool(updates['is_fuel'])
        if 'is_active' in updates:
            updates['is_active'] = bool(updates['is_active'])
        
        # Update product
        updated_product = db.update_product(product_id, updates)
        
        if not updated_product:
            return jsonify({"status": "error", "message": "Product not found"}), 404
            
        return jsonify(updated_product)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product"""
    try:
        result = db.delete_product(product_id)
        
        if not result:
            return jsonify({"status": "error", "message": "Product not found or could not be deleted"}), 404
            
        return jsonify({"status": "success", "message": "Product deleted successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/products/<product_id>/stock', methods=['POST'])
def update_product_stock(product_id):
    """Update product stock quantity"""
    try:
        data = request.json
        required_fields = ['quantity_change', 'transaction_type']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error", 
                    "message": f"Missing required field: {field}"
                }), 400
                
        quantity_change = float(data['quantity_change'])
        transaction_type = data['transaction_type']
        reference = data.get('reference')
        
        # Update stock
        updated_product = db.update_product_stock(
            product_id=product_id,
            quantity_change=quantity_change,
            transaction_type=transaction_type,
            reference=reference
        )
        
        if not updated_product:
            return jsonify({"status": "error", "message": "Product not found"}), 404
            
        return jsonify(updated_product)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500