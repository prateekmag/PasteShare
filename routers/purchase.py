from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import PurchaseOrder, PurchaseOrderInDB
import purchase_orders

router = APIRouter()

@router.post("/purchase-orders", response_model=Dict[str, Any])
async def create_purchase_order(order: PurchaseOrder):
    """
    Create a new purchase order request.
    
    This endpoint is used by branch managers to request fuel or product purchases.
    """
    order_id = purchase_orders.save_purchase_order(order)
    return {"id": order_id, "message": "Purchase order created successfully"}

@router.get("/purchase-orders", response_model=List[Dict[str, Any]])
async def get_purchase_orders(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get purchase orders with optional filtering.
    
    - branch_id: Filter by branch ID
    - status: Filter by status (pending, approved, rejected, completed)
    """
    orders = purchase_orders.get_purchase_orders(branch_id, status, limit, offset)
    return orders

@router.get("/purchase-orders/{order_id}", response_model=Dict[str, Any])
async def get_purchase_order(order_id: int):
    """
    Get details of a specific purchase order.
    """
    order = purchase_orders.get_purchase_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return order

@router.put("/purchase-orders/{order_id}", response_model=Dict[str, Any])
async def update_purchase_order(order_id: int, updates: Dict[str, Any]):
    """
    Update a purchase order.
    
    This can be used to update any fields of the purchase order.
    """
    success = purchase_orders.update_purchase_order(order_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Purchase order not found or no valid updates provided")
    return {"message": "Purchase order updated successfully"}

@router.post("/purchase-orders/{order_id}/approve", response_model=Dict[str, Any])
async def approve_purchase_order(order_id: int, approved_by: str, updates: Optional[Dict[str, Any]] = None):
    """
    Approve a purchase order request.
    
    This endpoint is used by admins to approve purchase orders from branches.
    """
    success = purchase_orders.approve_purchase_order(order_id, approved_by, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return {"message": "Purchase order approved successfully"}

@router.post("/purchase-orders/{order_id}/reject", response_model=Dict[str, Any])
async def reject_purchase_order(order_id: int, approved_by: str, reason: Optional[str] = None):
    """
    Reject a purchase order request.
    
    This endpoint is used by admins to reject purchase orders from branches.
    """
    success = purchase_orders.reject_purchase_order(order_id, approved_by, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return {"message": "Purchase order rejected successfully"}

@router.post("/purchase-orders/{order_id}/payment", response_model=Dict[str, Any])
async def update_payment_status(
    order_id: int, 
    payment_status: str,
    payment_amount: Optional[float] = None,
    payment_reference: Optional[str] = None
):
    """
    Update the payment status of a purchase order.
    
    This endpoint is used to track payments for purchase orders.
    """
    success = purchase_orders.update_payment_status(
        order_id, payment_status, payment_amount, payment_reference
    )
    if not success:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return {"message": f"Payment status updated to '{payment_status}' successfully"}

@router.post("/purchase-orders/{order_id}/complete", response_model=Dict[str, Any])
async def complete_purchase_order(order_id: int):
    """
    Mark a purchase order as completed.
    
    This endpoint is used when the ordered products have been received.
    """
    success = purchase_orders.complete_purchase_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return {"message": "Purchase order marked as completed"}