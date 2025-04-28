"""
API routes for AI features in PetrolPro.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required, current_user

import ai_forecasting

# Create blueprint for AI routes
ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/dashboard')
@login_required
def ai_dashboard():
    """
    AI Analytics Dashboard
    """
    from branch_utils import get_branch_data
    
    # Get branch data for the user
    branch_name = "No Branch Assigned"
    if current_user.branch_id:
        branches = get_branch_data()
        for branch in branches:
            if branch.get('id') == current_user.branch_id:
                branch_name = branch.get('name')
                break
    
    return render_template("ai_analytics.html", branch_name=branch_name)

@ai_bp.route('/api/ai/forecast')
@login_required
def forecast_api():
    """
    API endpoint for fuel demand forecasting
    """
    try:
        branch_id = request.args.get('branch_id')
        product_type = request.args.get('product_type', 'petrol')
        days_ahead = int(request.args.get('days_ahead', 7))
        include_weather = request.args.get('include_weather', 'false').lower() == 'true'
        include_events = request.args.get('include_events', 'false').lower() == 'true'
        
        if not branch_id:
            return jsonify({
                "status": "error",
                "message": "Branch ID is required",
                "data": None
            }), 400
            
        # Call the forecasting function
        forecast_data = ai_forecasting.predict_fuel_demand(
            branch_id=branch_id,
            product_type=product_type,
            days_ahead=days_ahead,
            include_weather=include_weather,
            include_events=include_events
        )
        
        return jsonify(forecast_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in forecast API: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error generating forecast: {str(e)}",
            "data": None
        }), 500

@ai_bp.route('/api/ai/anomalies')
@login_required
def anomalies_api():
    """
    API endpoint for detecting sales anomalies
    """
    try:
        branch_id = request.args.get('branch_id')
        product_type = request.args.get('product_type', 'petrol')
        lookback_days = int(request.args.get('lookback_days', 30))
        threshold = float(request.args.get('threshold', 0.2))
        
        if not branch_id:
            return jsonify({
                "status": "error",
                "message": "Branch ID is required",
                "data": None
            }), 400
            
        # Call the anomaly detection function
        anomaly_data = ai_forecasting.detect_sales_anomalies(
            branch_id=branch_id,
            product_type=product_type,
            lookback_days=lookback_days,
            threshold=threshold
        )
        
        return jsonify(anomaly_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in anomalies API: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error detecting anomalies: {str(e)}",
            "data": None
        }), 500

@ai_bp.route('/api/ai/inventory')
@login_required
def inventory_api():
    """
    API endpoint for inventory optimization
    """
    try:
        branch_id = request.args.get('branch_id')
        product_type = request.args.get('product_type', 'petrol')
        
        if not branch_id:
            return jsonify({
                "status": "error",
                "message": "Branch ID is required",
                "data": None
            }), 400
            
        # Call the inventory optimization function
        inventory_data = ai_forecasting.optimize_inventory_levels(
            branch_id=branch_id,
            product_type=product_type
        )
        
        return jsonify(inventory_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in inventory API: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error optimizing inventory: {str(e)}",
            "data": None
        }), 500