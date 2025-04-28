from datetime import datetime
from db import get_db_connection, dict_cursor
from models import TotalizerReading, ShiftSales

def create_totalizer_tables():
    """Create totalizer_readings and shift_sales tables if they don't exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create totalizer_readings table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS totalizer_readings (
                    id SERIAL PRIMARY KEY,
                    pump_id VARCHAR(50) NOT NULL,
                    nozzle_id VARCHAR(50) NOT NULL,
                    product_type VARCHAR(50) NOT NULL,
                    reading_type VARCHAR(20) NOT NULL,
                    reading_value FLOAT NOT NULL,
                    totalizer_image_url TEXT,
                    pumpman_id VARCHAR(50) NOT NULL,
                    shift VARCHAR(20) NOT NULL,
                    branch_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')
            
            # Create shift_sales table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS shift_sales (
                    id SERIAL PRIMARY KEY,
                    pump_id VARCHAR(50) NOT NULL,
                    nozzle_id VARCHAR(50) NOT NULL,
                    product_type VARCHAR(50) NOT NULL,
                    opening_reading FLOAT NOT NULL,
                    closing_reading FLOAT NOT NULL,
                    pumpman_id VARCHAR(50) NOT NULL,
                    shift VARCHAR(20) NOT NULL,
                    branch_id VARCHAR(50) NOT NULL,
                    amount FLOAT NOT NULL,
                    units_sold FLOAT NOT NULL,
                    date TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')
            conn.commit()

def save_totalizer_reading(reading):
    """Save a new totalizer reading to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO totalizer_readings (
                    pump_id, nozzle_id, product_type, reading_type, reading_value,
                    totalizer_image_url, pumpman_id, shift, branch_id, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                reading.pump_id,
                reading.nozzle_id,
                reading.product_type,
                reading.reading_type,
                reading.reading_value,
                reading.totalizer_image_url,
                reading.pumpman_id,
                reading.shift,
                reading.branch_id,
                reading.timestamp
            ))
            reading_id = cur.fetchone()[0]
            conn.commit()
            return reading_id

def get_totalizer_readings(
    pump_id=None, 
    nozzle_id=None, 
    pumpman_id=None, 
    reading_type=None,
    branch_id=None,
    shift=None,
    start_date=None, 
    end_date=None, 
    limit=100, 
    offset=0
):
    """Get totalizer readings with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM totalizer_readings WHERE 1=1"
            params = []
            
            if pump_id:
                query += " AND pump_id = %s"
                params.append(pump_id)
            
            if nozzle_id:
                query += " AND nozzle_id = %s"
                params.append(nozzle_id)
            
            if pumpman_id:
                query += " AND pumpman_id = %s"
                params.append(pumpman_id)
            
            if reading_type:
                query += " AND reading_type = %s"
                params.append(reading_type)
                
            if branch_id:
                query += " AND branch_id = %s"
                params.append(branch_id)
                
            if shift:
                query += " AND shift = %s"
                params.append(shift)
            
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            return cur.fetchall()

def get_latest_opening_reading(pump_id, nozzle_id, branch_id, shift=None, date=None):
    """Get the latest opening reading for a specific pump/nozzle combination."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = """
                SELECT * FROM totalizer_readings 
                WHERE pump_id = %s 
                AND nozzle_id = %s 
                AND branch_id = %s 
                AND reading_type = 'opening'
            """
            params = [pump_id, nozzle_id, branch_id]
            
            if shift:
                query += " AND shift = %s"
                params.append(shift)
            
            if date:
                # Get readings from the specific date
                start_date = datetime.combine(date.date(), datetime.min.time())
                end_date = datetime.combine(date.date(), datetime.max.time())
                
                query += " AND timestamp >= %s AND timestamp <= %s"
                params.extend([start_date, end_date])
            
            query += " ORDER BY timestamp DESC LIMIT 1"
            
            cur.execute(query, params)
            return cur.fetchone()

def save_shift_sales(sales):
    """Save shift sales data to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO shift_sales (
                    pump_id, nozzle_id, product_type, opening_reading, closing_reading,
                    pumpman_id, shift, branch_id, amount, units_sold, date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                sales.pump_id,
                sales.nozzle_id,
                sales.product_type,
                sales.opening_reading,
                sales.closing_reading,
                sales.pumpman_id,
                sales.shift,
                sales.branch_id,
                sales.amount,
                sales.units_sold,
                sales.date
            ))
            sales_id = cur.fetchone()[0]
            conn.commit()
            return sales_id

def get_shift_sales(
    pump_id=None, 
    nozzle_id=None, 
    pumpman_id=None,
    product_type=None,
    branch_id=None,
    shift=None,
    start_date=None, 
    end_date=None, 
    limit=100, 
    offset=0
):
    """Get shift sales with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM shift_sales WHERE 1=1"
            params = []
            
            if pump_id:
                query += " AND pump_id = %s"
                params.append(pump_id)
            
            if nozzle_id:
                query += " AND nozzle_id = %s"
                params.append(nozzle_id)
            
            if pumpman_id:
                query += " AND pumpman_id = %s"
                params.append(pumpman_id)
                
            if product_type:
                query += " AND product_type = %s"
                params.append(product_type)
                
            if branch_id:
                query += " AND branch_id = %s"
                params.append(branch_id)
                
            if shift:
                query += " AND shift = %s"
                params.append(shift)
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            query += " ORDER BY date DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            return cur.fetchall()

def get_sales_summary_by_product(branch_id=None, start_date=None, end_date=None):
    """Get sales summary grouped by product type."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = """
                SELECT 
                    product_type,
                    SUM(units_sold) as total_units,
                    SUM(amount) as total_amount,
                    COUNT(*) as transaction_count
                FROM shift_sales
                WHERE 1=1
            """
            params = []
            
            if branch_id:
                query += " AND branch_id = %s"
                params.append(branch_id)
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            query += " GROUP BY product_type ORDER BY total_amount DESC"
            
            cur.execute(query, params)
            return cur.fetchall()

def get_sales_summary_by_pumpman(branch_id=None, start_date=None, end_date=None):
    """Get sales summary grouped by pumpman."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = """
                SELECT 
                    pumpman_id,
                    SUM(units_sold) as total_units,
                    SUM(amount) as total_amount,
                    COUNT(*) as transaction_count
                FROM shift_sales
                WHERE 1=1
            """
            params = []
            
            if branch_id:
                query += " AND branch_id = %s"
                params.append(branch_id)
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            query += " GROUP BY pumpman_id ORDER BY total_amount DESC"
            
            cur.execute(query, params)
            return cur.fetchall()
            
def get_totalizer_sales(branch_id=None, product_type=None, start_date=None, end_date=None, limit=100, offset=0):
    """
    Get aggregated daily sales data from totalizer readings.
    
    Args:
        branch_id (str, optional): Filter by branch ID
        product_type (str, optional): Filter by product type (e.g., 'petrol', 'diesel')
        start_date (datetime, optional): Filter sales after this date
        end_date (datetime, optional): Filter sales before this date
        limit (int): Maximum number of records to return
        offset (int): Pagination offset
        
    Returns:
        list: Daily sales data with dates, sales volumes, and totals
    """
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Start with the most detailed query we have: shift_sales
            query = """
                SELECT 
                    DATE(date) as date,
                    product_type,
                    SUM(units_sold) as sales_volume,
                    SUM(amount) as total_amount,
                    branch_id
                FROM shift_sales
                WHERE 1=1
            """
            params = []
            
            if branch_id:
                query += " AND branch_id = %s"
                params.append(branch_id)
                
            if product_type:
                query += " AND product_type = %s"
                params.append(product_type)
            
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            
            # Group by day and product type
            query += " GROUP BY DATE(date), product_type, branch_id ORDER BY date DESC"
            
            # Add limit and offset
            if limit:
                query += " LIMIT %s"
                params.append(limit)
                
            if offset:
                query += " OFFSET %s"
                params.append(offset)
            
            cur.execute(query, params)
            results = cur.fetchall()
            
            # Convert date objects to string format for easier JSON handling
            for row in results:
                if isinstance(row['date'], datetime):
                    row['date'] = row['date'].strftime('%Y-%m-%d')
                    
            return results

def calculate_and_save_shift_sales(closing_reading):
    """
    Calculate and save shift sales based on closing reading.
    
    This function:
    1. Finds the corresponding opening reading
    2. Calculates unit sales and amount
    3. Saves the shift sales record
    4. Returns the saved sales record ID
    
    Args:
        closing_reading: TotalizerReading object with reading_type='closing'
        
    Returns:
        int: ID of the saved shift sales record, or None if opening reading not found
    """
    if closing_reading.reading_type != 'closing':
        raise ValueError("This function requires a closing reading")
    
    # Find matching opening reading
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Get the opening reading from the same day, pump, nozzle, shift and pumpman
            closing_date = closing_reading.timestamp.date()
            start_date = datetime.combine(closing_date, datetime.min.time())
            end_date = datetime.combine(closing_date, datetime.max.time())
            
            cur.execute("""
                SELECT * FROM totalizer_readings 
                WHERE pump_id = %s 
                AND nozzle_id = %s 
                AND branch_id = %s
                AND pumpman_id = %s
                AND shift = %s
                AND reading_type = 'opening'
                AND timestamp >= %s 
                AND timestamp <= %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (
                closing_reading.pump_id,
                closing_reading.nozzle_id,
                closing_reading.branch_id,
                closing_reading.pumpman_id,
                closing_reading.shift,
                start_date,
                end_date
            ))
            
            opening_reading = cur.fetchone()
            
            if not opening_reading:
                return None
            
            # Calculate sales
            units_sold = closing_reading.reading_value - opening_reading['reading_value']
            
            # If units_sold is negative, it might be due to totalizer reset or error
            if units_sold < 0:
                units_sold = closing_reading.reading_value  # Assume totalizer reset
            
            # Get current fuel price to calculate amount
            # This could be fetched from a prices table, but for now we'll use a fixed rate
            # This should be replaced with actual pricing logic
            # Here assuming product_price is stored in a dictionary or fetched from database
            product_prices = {
                'Petrol': 107.00,  # ₹107 per liter for Petrol
                'Diesel': 94.50,   # ₹94.50 per liter for Diesel
                'Premium Petrol': 113.00,  # ₹113 per liter for Premium Petrol
                'Premium Diesel': 99.00    # ₹99 per liter for Premium Diesel
            }
            
            price_per_unit = product_prices.get(closing_reading.product_type, 100.0)  # Default to ₹100 if not found
            amount = units_sold * price_per_unit
            
            # Create ShiftSales object
            from models import ShiftSales
            sales = ShiftSales(
                pump_id=closing_reading.pump_id,
                nozzle_id=closing_reading.nozzle_id,
                product_type=closing_reading.product_type,
                opening_reading=opening_reading['reading_value'],
                closing_reading=closing_reading.reading_value,
                pumpman_id=closing_reading.pumpman_id,
                shift=closing_reading.shift,
                branch_id=closing_reading.branch_id,
                amount=amount,
                units_sold=units_sold,
                date=closing_reading.timestamp
            )
            
            # Save to database
            return save_shift_sales(sales)