from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import db
from models import SaleEntry, SaleEntryInDB

router = APIRouter(prefix="/sales", tags=["Sales Management"])

@router.post("/sales", response_model=SaleEntryInDB)
async def add_sale(sale: SaleEntry):
    """
    Record a new fuel sale.
    
    This endpoint is used when fuel is sold to a customer.
    """
    try:
        # Calculate total amount
        total_amount = sale.litres_sold * sale.unit_price
        
        # Save the sale to the database
        sale_id = db.save_sale(sale)
        
        # Return the saved sale with its ID and total amount
        return {**sale.dict(), "id": sale_id, "total_amount": total_amount}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sales", response_model=List[SaleEntryInDB])
async def get_sales(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    attendant: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get sales records with optional filtering.
    
    - start_date: Filter sales on or after this date
    - end_date: Filter sales on or before this date
    - attendant: Filter sales by attendant
    """
    try:
        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        sales = db.get_sales(start_date, end_date, attendant, limit, offset)
        return sales
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sales/today", response_model=List[SaleEntryInDB])
async def get_today_sales(
    attendant: Optional[str] = None
):
    """
    Get sales records for today.
    
    - attendant: Optional filter for a specific attendant
    """
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        sales = db.get_sales(today, tomorrow, attendant)
        return sales
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sales/summary", response_model=Dict[str, Any])
async def get_sales_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get a summary of sales for a specified period.
    
    Returns total sales, volume, and transaction count.
    """
    try:
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
        
        return {
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/loyalty/{vehicle_number}", response_model=Dict[str, Any])
async def get_loyalty_points(vehicle_number: str):
    """
    Get loyalty points for a specific vehicle.
    """
    try:
        loyalty = db.get_loyalty_points(vehicle_number)
        return loyalty
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))