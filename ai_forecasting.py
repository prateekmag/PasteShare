"""
AI-powered forecasting module for PetrolPro.
Provides fuel demand forecasting, sales trend prediction, and anomaly detection.
"""

import json
import os
import logging
from datetime import datetime, timedelta
import numpy as np
from openai import OpenAI

# Import database utilities
import db
from totalizer import get_totalizer_readings, get_totalizer_sales

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def predict_fuel_demand(branch_id, product_type, days_ahead=7, historical_days=30, include_weather=False, include_events=False):
    """
    Predict fuel demand for the next X days based on historical data.
    
    Args:
        branch_id (str): Branch ID to generate prediction for
        product_type (str): Type of fuel (e.g., 'petrol', 'diesel')
        days_ahead (int): Number of days to forecast
        historical_days (int): Number of days of historical data to use
        include_weather (bool): Whether to include weather data in prediction
        include_events (bool): Whether to include local events data in prediction
        
    Returns:
        dict: Prediction data including daily forecasts and confidence levels
    """
    try:
        # Get historical sales data
        start_date = datetime.now() - timedelta(days=historical_days)
        end_date = datetime.now()
        
        # Get sales data from totalizer readings
        historical_sales = get_totalizer_sales(
            branch_id=branch_id,
            product_type=product_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # If we don't have enough data, return an appropriate message
        if not historical_sales or len(historical_sales) < 7:  # Need at least a week of data
            return {
                "status": "error",
                "message": "Insufficient historical data for prediction. Need at least 7 days of data.",
                "data": None
            }
        
        # Format data for OpenAI
        formatted_data = []
        for sale in historical_sales:
            date_str = sale.get('date')
            if date_str and isinstance(date_str, str):
                try:
                    formatted_data.append({
                        "date": date_str,
                        "sales_volume": sale.get('sales_volume'),
                        "day_of_week": datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
                    })
                except ValueError:
                    # Skip entries with invalid date format
                    logger.warning(f"Skipping entry with invalid date format: {date_str}")
                    continue
        
        # Additional context for prediction
        context = []
        
        # Add weather data if requested and available
        if include_weather:
            # In a production app, you would fetch actual weather data
            # For now, we'll just note in the prompt that this should be considered
            context.append("Please consider typical weather patterns for the season in your forecast.")
        
        # Add local events data if requested and available
        if include_events:
            # In a production app, you would fetch actual local events data
            # For now, we'll just note in the prompt that this should be considered
            context.append("Please consider typical local events and their impact on fuel demand.")
        
        # Generate prediction using OpenAI
        response = generate_ai_forecast(formatted_data, days_ahead, context)
        
        return {
            "status": "success",
            "message": "Forecast generated successfully",
            "data": response
        }
        
    except Exception as e:
        logger.error(f"Error predicting fuel demand: {str(e)}")
        return {
            "status": "error",
            "message": f"Error generating forecast: {str(e)}",
            "data": None
        }

def detect_sales_anomalies(branch_id, product_type, lookback_days=30, threshold=0.2):
    """
    Detect anomalies in sales data.
    
    Args:
        branch_id (str): Branch ID to check for anomalies
        product_type (str): Type of fuel
        lookback_days (int): Number of days to look back
        threshold (float): Threshold for anomaly detection (0-1)
        
    Returns:
        dict: List of detected anomalies with dates and descriptions
    """
    try:
        # Get historical sales data
        start_date = datetime.now() - timedelta(days=lookback_days)
        end_date = datetime.now()
        
        # Get sales data from totalizer readings
        sales_data = get_totalizer_sales(
            branch_id=branch_id,
            product_type=product_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # If we don't have enough data, return an appropriate message
        if not sales_data or len(sales_data) < 7:  # Need at least a week of data
            return {
                "status": "error",
                "message": "Insufficient data for anomaly detection. Need at least 7 days of data.",
                "data": None
            }
        
        # Format data for OpenAI
        formatted_data = []
        for sale in sales_data:
            date_str = sale.get('date')
            if date_str and isinstance(date_str, str):
                try:
                    formatted_data.append({
                        "date": date_str,
                        "sales_volume": sale.get('sales_volume'),
                        "day_of_week": datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
                    })
                except ValueError:
                    # Skip entries with invalid date format
                    logger.warning(f"Skipping entry with invalid date format: {date_str}")
                    continue
        
        # Analyze data for anomalies using OpenAI
        response = detect_ai_anomalies(formatted_data, threshold)
        
        return {
            "status": "success",
            "message": "Anomaly detection completed successfully",
            "data": response
        }
        
    except Exception as e:
        logger.error(f"Error detecting sales anomalies: {str(e)}")
        return {
            "status": "error",
            "message": f"Error detecting anomalies: {str(e)}",
            "data": None
        }
        
def optimize_inventory_levels(branch_id, product_type):
    """
    Optimize inventory levels based on demand forecasts and delivery schedules.
    
    Args:
        branch_id (str): Branch ID to optimize inventory for
        product_type (str): Type of fuel
        
    Returns:
        dict: Optimal reorder points and quantities
    """
    try:
        # Get current inventory levels
        # This would connect to your inventory management system
        # For now, we'll use sample data
        
        # Get demand forecast
        forecast = predict_fuel_demand(branch_id, product_type, days_ahead=14)
        
        if forecast["status"] == "error":
            return forecast
        
        forecast_data = forecast["data"]
        
        # Process forecast for inventory optimization using OpenAI
        response = optimize_ai_inventory(forecast_data, branch_id, product_type)
        
        return {
            "status": "success",
            "message": "Inventory optimization completed successfully",
            "data": response
        }
        
    except Exception as e:
        logger.error(f"Error optimizing inventory levels: {str(e)}")
        return {
            "status": "error",
            "message": f"Error optimizing inventory: {str(e)}",
            "data": None
        }

def generate_ai_forecast(historical_data, days_ahead, context=[]):
    """Use OpenAI to generate a forecast based on historical data."""
    try:
        # Create a prompt for OpenAI
        prompt = f"""
        You are an expert fuel demand forecasting system. Below is the historical sales data for a fuel station:
        
        {json.dumps(historical_data, indent=2)}
        
        Based on this historical data, please forecast fuel demand for the next {days_ahead} days. 
        For each day, provide:
        1. The forecasted sales volume
        2. A confidence score (0-1)
        3. A brief explanation for the forecast
        
        Additional context to consider:
        {' '.join(context)}
        
        Identify any patterns in the data such as:
        - Day of week patterns
        - Weekly cycles
        - Trends over time
        
        Provide your response as a JSON object with this structure:
        {{
            "forecast": [
                {{
                    "date": "YYYY-MM-DD",
                    "sales_volume": float,
                    "confidence": float,
                    "explanation": "string"
                }},
                ...
            ],
            "overall_trend": "string",
            "recommendations": ["string", ...]
        }}
        
        Only respond with the JSON object, no preamble or explanation.
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # Parse and return the response
        forecast_data = json.loads(response.choices[0].message.content)
        return forecast_data
        
    except Exception as e:
        logger.error(f"Error generating AI forecast: {str(e)}")
        raise

def detect_ai_anomalies(sales_data, threshold):
    """Use OpenAI to detect anomalies in sales data."""
    try:
        # Create a prompt for OpenAI
        prompt = f"""
        You are an expert anomaly detection system for fuel station sales. Below is the sales data:
        
        {json.dumps(sales_data, indent=2)}
        
        Please analyze this data and identify any anomalies or unusual patterns.
        An anomaly is defined as a sales volume that deviates significantly from the expected value
        based on historical patterns, weekly cycles, and trends.
        
        The anomaly threshold is {threshold}, meaning that a deviation of more than {threshold*100}% 
        from the expected value should be flagged as an anomaly.
        
        For each anomaly you detect, provide:
        1. The date
        2. The actual sales volume
        3. The expected sales volume range
        4. The percentage deviation
        5. A brief explanation of why it's anomalous
        6. A possible business reason for the anomaly
        
        Provide your response as a JSON object with this structure:
        {{
            "anomalies": [
                {{
                    "date": "YYYY-MM-DD",
                    "actual_volume": float,
                    "expected_volume_range": {{
                        "min": float,
                        "max": float
                    }},
                    "deviation_percentage": float,
                    "explanation": "string",
                    "possible_reason": "string"
                }},
                ...
            ],
            "summary": "string",
            "recommendations": ["string", ...]
        }}
        
        Only respond with the JSON object, no preamble or explanation.
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # Parse and return the response
        anomaly_data = json.loads(response.choices[0].message.content)
        return anomaly_data
        
    except Exception as e:
        logger.error(f"Error detecting AI anomalies: {str(e)}")
        raise

def optimize_ai_inventory(forecast_data, branch_id, product_type):
    """Use OpenAI to optimize inventory levels based on forecast data."""
    try:
        # Get tank capacity information
        # In a real application, this would come from your database
        # For now, we'll use sample data
        tank_capacity = 10000  # liters
        current_level = 6000   # liters
        lead_time = 2          # days for delivery
        
        # Create a prompt for OpenAI
        prompt = f"""
        You are an expert inventory optimization system for a fuel station. 
        
        Tank information:
        - Product type: {product_type}
        - Tank capacity: {tank_capacity} liters
        - Current level: {current_level} liters
        - Lead time for delivery: {lead_time} days
        
        Below is the demand forecast for the next 14 days:
        
        {json.dumps(forecast_data, indent=2)}
        
        Please optimize the inventory management by determining:
        1. The optimal reorder point (in liters)
        2. The optimal order quantity (in liters)
        3. The recommended reorder date
        4. Safety stock level to maintain (in liters)
        
        Consider the following constraints:
        - Deliveries can only happen on weekdays (Monday-Friday)
        - The tank should never go below 10% capacity to prevent pump issues
        - Full tanker deliveries are typically 8,000 liters, but partial deliveries are possible
        
        Provide your response as a JSON object with this structure:
        {{
            "reorder_point": float,
            "order_quantity": float,
            "recommended_reorder_date": "YYYY-MM-DD",
            "safety_stock": float,
            "days_until_reorder_needed": int,
            "explanation": "string",
            "additional_recommendations": ["string", ...]
        }}
        
        Only respond with the JSON object, no preamble or explanation.
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # Parse and return the response
        inventory_data = json.loads(response.choices[0].message.content)
        return inventory_data
        
    except Exception as e:
        logger.error(f"Error optimizing AI inventory: {str(e)}")
        raise