from datetime import datetime
from db import get_db_connection, dict_cursor
from models import PurchaseOrder

def create_purchase_orders_table():
    """Create purchase_orders table if it doesn't exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id SERIAL PRIMARY KEY,
                    branch_id VARCHAR(50) NOT NULL,
                    product_type VARCHAR(50) NOT NULL,
                    quantity FLOAT NOT NULL,
                    unit_price FLOAT NOT NULL,
                    total_amount FLOAT NOT NULL,
                    requested_by VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    payment_amount FLOAT DEFAULT 0,
                    payment_reference VARCHAR(100),
                    supplier VARCHAR(100),
                    expected_delivery_date TIMESTAMP,
                    notes TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    approved_by VARCHAR(50),
                    approved_at TIMESTAMP
                )
            ''')
            conn.commit()

def save_purchase_order(purchase_order):
    """Save a new purchase order to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO purchase_orders (
                    branch_id, product_type, quantity, unit_price, total_amount, 
                    requested_by, status, payment_status, payment_amount, 
                    payment_reference, supplier, expected_delivery_date, notes, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                purchase_order.branch_id,
                purchase_order.product_type,
                purchase_order.quantity,
                purchase_order.unit_price,
                purchase_order.total_amount,
                purchase_order.requested_by,
                purchase_order.status,
                purchase_order.payment_status,
                purchase_order.payment_amount,
                purchase_order.payment_reference,
                purchase_order.supplier,
                purchase_order.expected_delivery_date,
                purchase_order.notes,
                purchase_order.timestamp or datetime.now()
            ))
            order_id = cur.fetchone()[0]
            conn.commit()
            return order_id

def update_purchase_order(order_id, updates):
    """Update purchase order information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            update_fields = []
            update_values = []
            
            for key, value in updates.items():
                update_fields.append(f"{key} = %s")
                update_values.append(value)
            
            if not update_fields:
                return False
            
            update_values.append(order_id)
            
            query = f'''
                UPDATE purchase_orders
                SET {", ".join(update_fields)}
                WHERE id = %s
            '''
            
            cur.execute(query, update_values)
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def get_purchase_orders(branch_id=None, status=None, limit=100, offset=0):
    """Get purchase orders with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM purchase_orders WHERE 1=1"
            params = []
            
            if branch_id:
                query += " AND branch_id = %s"
                params.append(branch_id)
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            return cur.fetchall()

def get_purchase_order_by_id(order_id):
    """Get a specific purchase order by ID."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT * FROM purchase_orders
                WHERE id = %s
            ''', (order_id,))
            return cur.fetchone()

def get_purchase_orders_by_product(product_type, start_date=None, end_date=None):
    """Get purchase orders for a specific product type and date range."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM purchase_orders WHERE product_type = %s"
            params = [product_type]
            
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC"
            
            cur.execute(query, params)
            return cur.fetchall()

def approve_purchase_order(order_id, approved_by, updates=None):
    """Approve a purchase order."""
    if updates is None:
        updates = {}
    
    updates.update({
        'status': 'approved',
        'approved_by': approved_by,
        'approved_at': datetime.now()
    })
    
    return update_purchase_order(order_id, updates)

def reject_purchase_order(order_id, approved_by, reason=None):
    """Reject a purchase order."""
    updates = {
        'status': 'rejected',
        'approved_by': approved_by,
        'approved_at': datetime.now()
    }
    
    if reason:
        updates['notes'] = reason
    
    return update_purchase_order(order_id, updates)

def update_payment_status(order_id, payment_status, payment_amount=None, payment_reference=None):
    """Update the payment status of a purchase order."""
    updates = {'payment_status': payment_status}
    
    if payment_amount is not None:
        updates['payment_amount'] = payment_amount
    
    if payment_reference:
        updates['payment_reference'] = payment_reference
    
    return update_purchase_order(order_id, updates)

def complete_purchase_order(order_id):
    """Mark a purchase order as completed."""
    return update_purchase_order(order_id, {'status': 'completed'})