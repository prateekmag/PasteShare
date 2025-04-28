from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import db
from models import Attendant, AttendantInDB, Attendance, AttendanceInDB, Expense

router = APIRouter(prefix="/staff", tags=["Staff Management"])

@router.post("/attendants", response_model=AttendantInDB)
async def add_attendant(attendant: Attendant):
    """
    Add a new attendant to the system.
    """
    try:
        # Check if attendant already exists
        existing_attendant = db.get_attendants(attendant.employee_id)
        if existing_attendant:
            raise HTTPException(
                status_code=400, 
                detail=f"Attendant with employee ID {attendant.employee_id} already exists"
            )
        
        # Save the attendant to the database
        attendant_id = db.add_attendant(attendant)
        
        # Return the saved attendant with its ID
        return {**attendant.dict(), "id": attendant_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attendants", response_model=List[AttendantInDB])
async def get_all_attendants(active_only: bool = True):
    """
    Get all attendants in the system.
    
    - active_only: If True, only return active attendants
    """
    try:
        attendants = db.get_attendants(active_only=active_only)
        return attendants
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attendants/{employee_id}", response_model=AttendantInDB)
async def get_attendant(employee_id: str):
    """
    Get a specific attendant by employee ID.
    """
    try:
        attendant = db.get_attendants(employee_id)
        if not attendant:
            raise HTTPException(
                status_code=404, 
                detail=f"Attendant with employee ID {employee_id} not found"
            )
        return attendant
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/attendants/{employee_id}", response_model=AttendantInDB)
async def update_attendant_details(employee_id: str, updates: Dict[str, Any]):
    """
    Update details for a specific attendant.
    
    Allowed fields to update: name, role, active
    """
    try:
        # Check if attendant exists
        attendant = db.get_attendants(employee_id)
        if not attendant:
            raise HTTPException(
                status_code=404, 
                detail=f"Attendant with employee ID {employee_id} not found"
            )
        
        # Validate update fields
        allowed_fields = {"name", "role", "active"}
        update_data = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(
                status_code=400, 
                detail="No valid fields to update"
            )
        
        # Update the attendant
        success = db.update_attendant(employee_id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to update attendant"
            )
        
        # Get the updated attendant
        updated_attendant = db.get_attendants(employee_id)
        return updated_attendant
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/attendance/check-in", response_model=AttendanceInDB)
async def check_in(attendance: Attendance):
    """
    Record check-in for an attendant.
    """
    try:
        # Validate that the employee exists and is active
        attendant = db.get_attendants(attendance.employee_id)
        if not attendant:
            raise HTTPException(
                status_code=404, 
                detail=f"Attendant with employee ID {attendance.employee_id} not found"
            )
        
        if not attendant.get("active", False):
            raise HTTPException(
                status_code=400, 
                detail=f"Attendant with employee ID {attendance.employee_id} is inactive"
            )
        
        # Set check-in time to now if not provided
        if not attendance.check_in:
            attendance.check_in = datetime.now()
        
        # Record attendance
        attendance_id = db.record_attendance(attendance)
        
        # Return the recorded attendance with its ID
        return {**attendance.dict(), "id": attendance_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/attendance/check-out/{attendance_id}", response_model=Dict[str, Any])
async def check_out(attendance_id: int):
    """
    Record check-out for an existing attendance record.
    """
    try:
        # Update attendance with check-out time
        check_out_time = datetime.now()
        success = db.update_attendance(attendance_id, check_out_time)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Attendance record with ID {attendance_id} not found"
            )
        
        return {
            "status": "success",
            "message": "Check-out recorded successfully",
            "check_out_time": check_out_time.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attendance", response_model=List[AttendanceInDB])
async def get_attendance_records(
    employee_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get attendance records with optional filtering.
    
    - employee_id: Filter by employee ID
    - start_date: Filter records on or after this date
    - end_date: Filter records on or before this date
    """
    try:
        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        attendance_records = db.get_attendance(employee_id, start_date, end_date)
        return attendance_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/attendance/today", response_model=List[AttendanceInDB])
async def get_today_attendance():
    """
    Get attendance records for today.
    """
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        attendance_records = db.get_attendance(start_date=today, end_date=tomorrow)
        return attendance_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/expenses", response_model=Dict[str, Any])
async def add_expense(expense: Expense):
    """
    Record a new expense.
    """
    try:
        # Validate that the employee exists
        attendant = db.get_attendants(expense.employee_id)
        if not attendant:
            raise HTTPException(
                status_code=404, 
                detail=f"Attendant with employee ID {expense.employee_id} not found"
            )
        
        # Set timestamp to now if not provided
        if not expense.timestamp:
            expense.timestamp = datetime.now()
        
        # Save the expense
        expense_id = db.save_expense(expense)
        
        # Return the saved expense with its ID
        return {**expense.dict(), "id": expense_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/expenses", response_model=List[Dict[str, Any]])
async def get_expenses(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category: Optional[str] = None,
    employee_id: Optional[str] = None
):
    """
    Get expense records with optional filtering.
    
    - start_date: Filter expenses on or after this date
    - end_date: Filter expenses on or before this date
    - category: Filter by expense category
    - employee_id: Filter by employee who recorded the expense
    """
    try:
        # Set default date range to last 30 days if not provided
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
            
        expenses = db.get_expenses(start_date, end_date, category, employee_id)
        return expenses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))