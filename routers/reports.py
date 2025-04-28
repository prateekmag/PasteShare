from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import db
import ai_reports
from models import ReportRequest, AIReportRequest, Report, AIReport

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.post("/fuel-consumption", response_model=Dict[str, Any])
async def generate_fuel_consumption_report(request: ReportRequest):
    """
    Generate a fuel consumption report for a specific period.
    
    This report includes:
    - Fuel received by tank
    - Fuel sold by type
    - Discrepancies and analysis
    """
    try:
        # Set default dates if not provided
        start_date = request.start_date
        end_date = request.end_date
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # Get fuel consumption data
        tank_id = request.tanks[0] if request.tanks else None
        fuel_data = db.get_fuel_consumption(start_date, end_date, tank_id=tank_id)
        
        # Create report object
        report = Report(
            report_type="fuel_consumption",
            start_date=start_date,
            end_date=end_date,
            data=fuel_data,
            generated_at=datetime.now()
        )
        
        # Save report
        report_id = db.save_report(report)
        
        # Return report with ID
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sales", response_model=Dict[str, Any])
async def generate_sales_report(request: ReportRequest):
    """
    Generate a sales report for a specific period.
    
    This report includes:
    - Total sales by fuel type
    - Sales by payment method
    - Sales by attendant
    - Daily sales breakdown
    """
    try:
        # Set default dates if not provided
        start_date = request.start_date
        end_date = request.end_date
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # Get sales summary data
        sales_data = {
            "payment_methods": db.get_sales_by_payment_method(start_date, end_date),
            "attendant_performance": db.get_sales_by_attendant(start_date, end_date),
            "daily_sales": db.get_daily_sales(start_date, end_date)
        }
        
        # Create report object
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
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inventory", response_model=Dict[str, Any])
async def generate_inventory_report(request: ReportRequest):
    """
    Generate an inventory report showing current tank levels and statistics.
    """
    try:
        # Set default dates if not provided
        start_date = request.start_date
        end_date = request.end_date
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
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
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/fuel-consumption", response_model=Dict[str, Any])
async def generate_ai_fuel_consumption_report(request: AIReportRequest):
    """
    Generate an AI-enhanced fuel consumption report.
    
    This report includes AI-generated insights and recommendations.
    """
    try:
        # Set default dates if not provided
        start_date = request.start_date
        end_date = request.end_date
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # Get fuel consumption data
        tank_id = request.tanks[0] if request.tanks else None
        fuel_data = db.get_fuel_consumption(start_date, end_date, tank_id=tank_id)
        
        # Create AI report
        ai_report = ai_reports.create_ai_report(
            fuel_data,
            "fuel_consumption",
            start_date,
            end_date,
            request.prompt
        )
        
        # Save report
        report_id = db.save_report(ai_report)
        
        # Return report with ID
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/sales", response_model=Dict[str, Any])
async def generate_ai_sales_report(request: AIReportRequest):
    """
    Generate an AI-enhanced sales performance report.
    
    This report includes AI-generated insights and recommendations for improving sales.
    """
    try:
        # Set default dates if not provided
        start_date = request.start_date
        end_date = request.end_date
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
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
            request.prompt
        )
        
        # Save report
        report_id = db.save_report(ai_report)
        
        # Return report with ID
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/inventory", response_model=Dict[str, Any])
async def generate_ai_inventory_report(request: AIReportRequest):
    """
    Generate an AI-enhanced inventory management report.
    
    This report includes AI-generated insights and recommendations for inventory optimization.
    """
    try:
        # Set default dates if not provided
        start_date = request.start_date
        end_date = request.end_date
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
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
            request.prompt
        )
        
        # Save report
        report_id = db.save_report(ai_report)
        
        # Return report with ID
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[Dict[str, Any]])
async def get_reports(report_type: Optional[str] = None, limit: int = 10):
    """
    Get previously generated reports.
    
    - report_type: Filter by report type
    - limit: Maximum number of reports to return
    """
    try:
        reports = db.get_reports(report_type, limit)
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}", response_model=Dict[str, Any])
async def get_report_by_id(report_id: int):
    """
    Get a specific report by ID.
    """
    try:
        report = db.get_report_by_id(report_id)
        if not report:
            raise HTTPException(
                status_code=404, 
                detail=f"Report with ID {report_id} not found"
            )
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))