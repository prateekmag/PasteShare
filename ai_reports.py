import os
import json
from datetime import datetime
from models import AIReport
from openai import OpenAI

# Initialize OpenAI client
openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_report_summary(data, prompt=None):
    """
    Generate an AI summary report using OpenAI.
    
    Args:
        data (dict): The data to summarize
        prompt (str, optional): Additional prompt to guide the AI
        
    Returns:
        dict: Report summary with recommendations
    """
    try:
        # Prepare the data for OpenAI
        data_str = json.dumps(data, indent=2, default=str)
        
        # Create the system message with context
        system_message = """
        You are an expert fuel management system analyst for a petrol station.
        Analyze the provided data and generate a concise summary with actionable recommendations.
        Your response should be formatted as a JSON with two fields:
        1. "summary": A concise analysis of the data
        2. "recommendations": A list of actionable recommendations 
        
        Ensure your response is well-structured, insightful, and directly relates to the data provided.
        """
        
        # Add user prompt if provided
        user_message = f"Here is the data to analyze:\n{data_str}"
        if prompt:
            user_message += f"\n\nAdditional instructions: {prompt}"
        
        # Create the API request
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        
        return {
            "summary": result["summary"],
            "recommendations": result["recommendations"]
        }
        
    except Exception as e:
        # Fallback in case of error
        return {
            "summary": f"Error generating AI report: {str(e)}",
            "recommendations": ["Consider trying again with a different data set or prompt."]
        }

def generate_fuel_consumption_report(data, prompt=None):
    """Generate an AI report specifically for fuel consumption."""
    system_prompt = """
    You are a fuel management expert. Analyze the fuel consumption data provided, focusing on:
    
    1. Patterns of fuel delivery and usage
    2. Discrepancies between fuel received and sold
    3. Potential leakage or theft indicators
    4. Tank utilization and optimal inventory levels
    5. Peak consumption periods
    
    Your recommendations should be practical steps to improve fuel management, reduce losses, and optimize inventory.
    """
    
    # Combine with any user prompt
    combined_prompt = system_prompt
    if prompt:
        combined_prompt += f"\n\nAdditional context: {prompt}"
    
    return generate_report_summary(data, combined_prompt)

def generate_sales_performance_report(data, prompt=None):
    """Generate an AI report specifically for sales performance."""
    system_prompt = """
    You are a sales performance analyst for a petrol station. Analyze the sales data provided, focusing on:
    
    1. Revenue trends by payment method, fuel type, and time period
    2. Attendant performance comparison
    3. Customer purchasing patterns
    4. Opportunities for upselling or cross-selling
    5. Optimal pricing strategies based on sales data
    
    Your recommendations should focus on actionable steps to increase revenue, improve staff performance, and enhance customer experience.
    """
    
    # Combine with any user prompt
    combined_prompt = system_prompt
    if prompt:
        combined_prompt += f"\n\nAdditional context: {prompt}"
    
    return generate_report_summary(data, combined_prompt)

def generate_inventory_management_report(data, prompt=None):
    """Generate an AI report specifically for inventory management."""
    system_prompt = """
    You are an inventory management specialist for a petrol station. Analyze the inventory data provided, focusing on:
    
    1. Current inventory levels compared to capacity
    2. Consumption rates and projected depletion
    3. Optimal reorder points and quantities
    4. Seasonal trends affecting inventory needs
    5. Risk assessment for stockouts or excess inventory
    
    Your recommendations should focus on practical steps to optimize inventory levels, reduce costs, and ensure uninterrupted operations.
    """
    
    # Combine with any user prompt
    combined_prompt = system_prompt
    if prompt:
        combined_prompt += f"\n\nAdditional context: {prompt}"
    
    return generate_report_summary(data, combined_prompt)

def create_ai_report(report_data, report_type, start_date, end_date, prompt=None):
    """
    Create an AI-enhanced report based on the provided data.
    
    Args:
        report_data (dict): The data for the report
        report_type (str): Type of report (fuel_consumption, sales_performance, etc.)
        start_date (datetime): Start date for the report period
        end_date (datetime): End date for the report period
        prompt (str, optional): Additional prompt to guide the AI
        
    Returns:
        AIReport: The generated AI report
    """
    # Generate the appropriate report based on type
    if report_type == "fuel_consumption":
        ai_result = generate_fuel_consumption_report(report_data, prompt)
    elif report_type == "sales_performance":
        ai_result = generate_sales_performance_report(report_data, prompt)
    elif report_type == "inventory_management":
        ai_result = generate_inventory_management_report(report_data, prompt)
    else:
        # Default to a generic report
        ai_result = generate_report_summary(report_data, prompt)
    
    # Create and return the AIReport object
    return AIReport(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        data=report_data,
        generated_at=datetime.now(),
        summary=ai_result["summary"],
        recommendations=ai_result["recommendations"]
    )