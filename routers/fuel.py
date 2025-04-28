from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime
import db
from models import FuelEntry, FuelEntryInDB, FuelDip, FuelDipInDB, Tank, TankInDB

router = APIRouter(prefix="/fuel", tags=["Fuel Management"])

@router.post("/entries", response_model=FuelEntryInDB)
async def add_fuel_entry(entry: FuelEntry):
    """
    Add a new fuel entry record.
    
    This endpoint is used when fuel is delivered to a tank.
    """
    try:
        # Save the entry to the database
        entry_id = db.save_fuel_entry(entry)
        
        # Update the tank's current level
        tank = db.get_tanks(entry.tank_id)
        if tank:
            new_level = tank["current_level"] + entry.litres_received
            db.update_tank(entry.tank_id, {"current_level": new_level})
        
        # Return the saved entry with its ID
        return {**entry.dict(), "id": entry_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entries", response_model=List[FuelEntryInDB])
async def get_fuel_entries(
    tank_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get fuel entries with optional filtering by tank ID.
    """
    try:
        entries = db.get_fuel_entries(tank_id, limit, offset)
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dips", response_model=FuelDipInDB)
async def add_dip_reading(dip: FuelDip):
    """
    Add a new dip reading record.
    
    Dip readings are manual measurements of fuel levels in tanks.
    """
    try:
        # Save the dip reading to the database
        dip_id = db.save_dip_reading(dip)
        
        # Update the tank's current level
        db.update_tank(dip.tank_id, {"current_level": dip.dip_reading})
        
        # Return the saved dip reading with its ID
        return {**dip.dict(), "id": dip_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dips", response_model=List[FuelDipInDB])
async def get_dip_readings(
    tank_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get dip readings with optional filtering by tank ID.
    """
    try:
        readings = db.get_dip_readings(tank_id, limit, offset)
        return readings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tanks", response_model=TankInDB)
async def add_tank(tank: Tank):
    """
    Add a new tank to the system.
    """
    try:
        # Check if the tank already exists
        existing_tank = db.get_tanks(tank.id)
        if existing_tank:
            raise HTTPException(
                status_code=400, 
                detail=f"Tank with ID {tank.id} already exists"
            )
        
        # Save the tank to the database
        tank_id = db.add_tank(tank)
        
        # Return the saved tank
        return tank
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tanks", response_model=List[TankInDB])
async def get_all_tanks():
    """
    Get all tanks in the system.
    """
    try:
        tanks = db.get_tanks()
        return tanks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tanks/{tank_id}", response_model=TankInDB)
async def get_tank(tank_id: str):
    """
    Get a specific tank by ID.
    """
    try:
        tank = db.get_tanks(tank_id)
        if not tank:
            raise HTTPException(
                status_code=404, 
                detail=f"Tank with ID {tank_id} not found"
            )
        return tank
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/tanks/{tank_id}", response_model=TankInDB)
async def update_tank_details(tank_id: str, updates: dict):
    """
    Update details for a specific tank.
    
    Allowed fields to update: fuel_type, capacity, current_level, status
    """
    try:
        # Check if the tank exists
        tank = db.get_tanks(tank_id)
        if not tank:
            raise HTTPException(
                status_code=404, 
                detail=f"Tank with ID {tank_id} not found"
            )
        
        # Validate update fields
        allowed_fields = {"fuel_type", "capacity", "current_level", "status"}
        update_data = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(
                status_code=400, 
                detail="No valid fields to update"
            )
        
        # Update the tank
        success = db.update_tank(tank_id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to update tank"
            )
        
        # Get the updated tank
        updated_tank = db.get_tanks(tank_id)
        return updated_tank
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))