import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
from branch_utils import get_branch_data, is_valid_branch
from flask import g, has_app_context

# Database connection string
DATABASE_URL = os.environ.get("postgresql://petrolpro_user:Vw9khY38RQPzVjknEhIHumaqxE9FSPqz@dpg-d07p2bjuibrs73fn52pg-a.oregon-postgres.render.com/petrolpro")

@contextmanager
def test_db_connection():
    """Test database connection and create tables if needed."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                if result:
                    print("Database connection successful")
                    return True
                return False
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return False

@contextmanager
def get_db_connection(allow_no_tenant=False):
    """Context manager for getting a database connection."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        tenant_id = getattr(g, 'tenant_id', None) if has_app_context() else None
        if tenant_id:
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {tenant_id}")
                conn.commit()
        elif not tenant_id and not has_app_context() and allow_no_tenant:
            # Allow connection outside app context for admin tasks
            pass
        yield conn
    finally:
        if conn is not None:
            conn.close()

def dict_cursor(conn):
    """Get a cursor that returns results as dictionaries."""
    return conn.cursor(cursor_factory=RealDictCursor)

def create_tables():
    """Create all necessary tables if they don't exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create users table for authentication
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    full_name VARCHAR(120),
                    password_hash VARCHAR(256) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    branch_id VARCHAR(50),
                    tenant_id VARCHAR(50),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_by INTEGER
                )
            ''')
            # Create fuel_tanks table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS fuel_tanks (
                    id VARCHAR(50) PRIMARY KEY,
                    fuel_type VARCHAR(50) NOT NULL,
                    capacity FLOAT NOT NULL,
                    current_level FLOAT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    branch_id VARCHAR(50)
                )
            ''')

            # Create fuel_entries table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS fuel_entries (
                    id SERIAL PRIMARY KEY,
                    tank_id VARCHAR(50) REFERENCES fuel_tanks(id),
                    shift VARCHAR(20) NOT NULL,
                    litres_received FLOAT NOT NULL,
                    dip_before FLOAT NOT NULL,
                    dip_after FLOAT NOT NULL,
                    attendant VARCHAR(50) NOT NULL,
                    branch_id VARCHAR(50),
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')

            # Create dip_readings table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS dip_readings (
                    id SERIAL PRIMARY KEY,
                    tank_id VARCHAR(50) REFERENCES fuel_tanks(id),
                    dip_reading FLOAT NOT NULL,
                    attendant VARCHAR(50) NOT NULL,
                    shift VARCHAR(20) NOT NULL,
                    branch_id VARCHAR(50),
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')

            # Create attendants table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS attendants (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    employee_id VARCHAR(50) UNIQUE NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'pumpman',
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    branch_id VARCHAR(50),
                    contact_number VARCHAR(50),
                    join_date TIMESTAMP
                )
            ''')

            # Create attendance table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id SERIAL PRIMARY KEY,
                    employee_id VARCHAR(50) REFERENCES attendants(employee_id),
                    check_in TIMESTAMP NOT NULL,
                    check_out TIMESTAMP,
                    shift VARCHAR(20) NOT NULL
                )
            ''')

            # Create staff schedule table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS staff_schedule (
                    id SERIAL PRIMARY KEY,
                    employee_id VARCHAR(50) REFERENCES attendants(employee_id),
                    schedule_date DATE NOT NULL,
                    shift VARCHAR(20) NOT NULL,
                    branch_id VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'scheduled',
                    notes TEXT,
                    created_by VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')

            # Create sales table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS sales (
                    id SERIAL PRIMARY KEY,
                    pump_id VARCHAR(50) NOT NULL,
                    fuel_type VARCHAR(50) NOT NULL,
                    litres_sold FLOAT NOT NULL,
                    unit_price FLOAT NOT NULL,
                    total_amount FLOAT NOT NULL,
                    attendant VARCHAR(50) NOT NULL,
                    vehicle_number VARCHAR(50),
                    payment_method VARCHAR(50) NOT NULL,
                    shift VARCHAR(20) NOT NULL,
                    branch_id VARCHAR(50),
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')

            # Create loyalty_points table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS loyalty_points (
                    id SERIAL PRIMARY KEY,
                    vehicle_number VARCHAR(50) UNIQUE NOT NULL,
                    points INTEGER NOT NULL DEFAULT 0,
                    last_updated TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')

            # Create expenses table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    description TEXT NOT NULL,
                    amount FLOAT NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    employee_id VARCHAR(50) REFERENCES attendants(employee_id),
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')

            # Create reports table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    report_type VARCHAR(50) NOT NULL,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    data JSONB NOT NULL,
                    summary TEXT,
                    recommendations JSONB,
                    generated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')

            # Create purchase_orders table
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

            # Create subscription_plans table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id SERIAL PRIMARY KEY,
                    plan_type VARCHAR(32) UNIQUE NOT NULL,
                    amount NUMERIC(10,2) NOT NULL
                )
            ''')

            # Insert default plans if not present
            cur.execute("SELECT COUNT(*) FROM subscription_plans")
            if cur.fetchone()[0] == 0:
                cur.execute('''
                    INSERT INTO subscription_plans (plan_type, amount) VALUES
                    ('monthly', 999),
                    ('yearly', 9999)
                ''')

            # Create subscriptions table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    branch_id VARCHAR(32) NOT NULL,
                    plan_id INTEGER NOT NULL REFERENCES subscription_plans(id),
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL
                )
            ''')

            # Create product_categories table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS product_categories (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    branch_id VARCHAR(50) NOT NULL
                )
            ''')

            # Create products table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category_id VARCHAR(50) REFERENCES product_categories(id),
                    description TEXT,
                    unit_price DECIMAL(10, 2) NOT NULL,
                    cost_price DECIMAL(10, 2),
                    stock_quantity DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    minimum_stock_level DECIMAL(10, 2),
                    unit_of_measure VARCHAR(50) NOT NULL,
                    is_fuel BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    barcode VARCHAR(100),
                    image_url TEXT,
                    branch_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')

            # Create product stock transaction table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS product_stock_transactions (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(50) REFERENCES products(id),
                    quantity_change DECIMAL(10, 2) NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    reference_id VARCHAR(100),
                    balance_after DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

# =============== User Authentication ===============

def get_user_by_username(username):
    """
    Get a user by username.

    Args:
        username (str): The username to look up

    Returns:
        dict or None: User information or None if user not found
    """
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT * FROM users
                WHERE username = %s
            ''', (username,))

            return cur.fetchone()

def get_user_by_id(user_id):
    """
    Get a user by ID.

    Args:
        user_id (int): The user ID to look up

    Returns:
        dict or None: User information or None if user not found
    """
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT * FROM users
                WHERE id = %s
            ''', (user_id,))

            return cur.fetchone()

def create_user(user, password_hash):
    """
    Create a new user.

    Args:
        user: User object with username, email, full_name, role, branch_id, created_by
        password_hash (str): Hashed password

    Returns:
        int: ID of the newly created user
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO users
                (username, email, full_name, password_hash, role, branch_id, is_active, created_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                user.username,
                user.email,
                user.full_name,
                password_hash,
                user.role,
                user.branch_id,
                user.is_active,
                user.created_at,
                user.created_by
            ))

            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id

def delete_user(user_id):
    """Delete a user from the database"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

def update_user(user_id, updates):
    """
    Update user information.

    Args:
        user_id (int): The ID of the user to update
        updates (dict): Dictionary of field-value pairs to update

    Returns:
        bool: True if update was successful, False otherwise
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            update_fields = []
            update_values = []

            for key, value in updates.items():
                update_fields.append(f"{key} = %s")
                update_values.append(value)

            if not update_fields:
                return False

            update_values.append(user_id)

            query = f'''
                UPDATE users
                SET {", ".join(update_fields)}
                WHERE id = %s
            '''

            cur.execute(query, update_values)
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def get_users(role=None, branch_id=None, is_active=True):
    """
    Get all users with optional filtering.

    Args:
        role (str, optional): Filter by role (admin, manager, senior_manager, pumpman, tanker_driver)
        branch_id (str, optional): Filter by branch ID
        is_active (bool, optional): Filter by active status

    Returns:
        list: List of user dictionaries
    """
    from branch_utils import get_branch_data, is_valid_branch

    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.role, u.branch_id, 
                       u.is_active, u.created_at, u.created_by, c.username as created_by_username
                FROM users u
                LEFT JOIN users c ON u.created_by = c.id
                WHERE 1=1
            """
            params = []

            if role:
                query += " AND u.role = %s"
                params.append(role)

            if is_active is not None:
                query += " AND u.is_active = %s"
                params.append(is_active)

            # Filter by branch
            if branch_id and branch_id != "all":
                # Check if this is a valid branch first
                if is_valid_branch(branch_id):
                    query += " AND u.branch_id = %s"
                    params.append(branch_id)
                else:
                    # Return empty result for invalid branch ID
                    return []

            query += " ORDER BY u.username"

            cur.execute(query, params)
            return cur.fetchall()

# =============== Fuel Management ===============

def save_fuel_entry(fuel_entry):
    """Save a new fuel entry to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO fuel_entries 
                (tank_id, shift, litres_received, dip_before, dip_after, attendant, branch_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                fuel_entry.tank_id,
                fuel_entry.shift,
                fuel_entry.litres_received,
                fuel_entry.dip_before,
                fuel_entry.dip_after,
                fuel_entry.attendant,
                fuel_entry.branch_id,
                fuel_entry.timestamp
            ))
            entry_id = cur.fetchone()[0]
            conn.commit()
            return entry_id

def get_fuel_entries(tank_id=None, branch_id=None, limit=100, offset=0):
    """
    Get fuel entries with optional filtering by tank ID and branch ID.

    Args:
        tank_id (str, optional): Filter by tank ID
        branch_id (str, optional): Filter by branch ID
        limit (int): Maximum number of records to return
        offset (int): Pagination offset

    Returns:
        List: Fuel entries matching the filters
    """
    from branch_utils import get_branch_data, is_valid_branch

    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM fuel_entries WHERE 1=1"
            params = []

            if tank_id:
                query += " AND tank_id = %s"
                params.append(tank_id)

            # Filter by branch
            if branch_id and branch_id != "all":
                # Check if this is a valid branch first
                if is_valid_branch(branch_id):
                    query += " AND branch_id = %s"
                    params.append(branch_id)
                else:
                    # Return empty result for invalid branch ID
                    return []
            else:
                # When not filtering by specific branch, only show data from valid branches
                branches = get_branch_data()
                if branches:
                    branch_ids = [branch["id"] for branch in branches]
                    placeholders = ", ".join(["%s"] * len(branch_ids))
                    query += f" AND (branch_id IS NULL OR branch_id IN ({placeholders}))"
                    params.extend(branch_ids)

            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cur.execute(query, params)
            return cur.fetchall()

def save_dip_reading(dip):
    """Save a dip reading to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO dip_readings 
                (tank_id, dip_reading, attendant, shift, branch_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                dip.tank_id,
                dip.dip_reading,
                dip.attendant,
                dip.shift,
                dip.branch_id,
                dip.timestamp
            ))
            dip_id = cur.fetchone()[0]
            conn.commit()
            return dip_id

def get_dip_readings(tank_id=None, branch_id=None, limit=100, offset=0):
    """
    Get dip readings with optional filtering by tank ID and branch ID.

    Args:
        tank_id (str, optional): Filter by tank ID
        branch_id (str, optional): Filter by branch ID
        limit (int): Maximum number of records to return
        offset (int): Pagination offset

    Returns:
        List: Dip readings matching the filters
    """
    from branch_utils import get_branch_data, is_valid_branch

    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM dip_readings WHERE 1=1"
            params = []

            if tank_id:
                query += " AND tank_id = %s"
                params.append(tank_id)

            # Filter by branch
            if branch_id and branch_id != "all":
                # Check if this is a valid branch first
                if is_valid_branch(branch_id):
                    query += " AND branch_id = %s"
                    params.append(branch_id)
                else:
                    # Return empty result for invalid branch ID
                    return []
            else:
                # When not filtering by specific branch, only show data from valid branches
                branches = get_branch_data()
                if branches:
                    branch_ids = [branch["id"] for branch in branches]
                    placeholders = ", ".join(["%s"] * len(branch_ids))
                    query += f" AND (branch_id IS NULL OR branch_id IN ({placeholders}))"
                    params.extend(branch_ids)

            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cur.execute(query, params)
            return cur.fetchall()

def add_tank(tank):
    """Add a new tank to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO fuel_tanks 
                (id, fuel_type, capacity, current_level, status, branch_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                tank.id,
                tank.fuel_type,
                tank.capacity,
                tank.current_level,
                tank.status,
                tank.branch_id
            ))
            tank_id = cur.fetchone()[0]
            conn.commit()
            return tank_id

def update_tank(tank_id, updates):
    """Update tank information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            update_fields = []
            update_values = []

            for key, value in updates.items():
                update_fields.append(f"{key} = %s")
                update_values.append(value)

            if not update_fields:
                return False

            update_values.append(tank_id)

            query = f'''
                UPDATE fuel_tanks
                SET {", ".join(update_fields)}
                WHERE id = %s
            '''

            cur.execute(query, update_values)
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def get_tanks(tank_id=None, branch_id=None):
    """
    Get all tanks or a specific tank by ID.

    Args:
        tank_id (str, optional): Filter by tank ID
        branch_id (str, optional): Filter by branch ID

    Returns:
        List or dict: Tank data
    """
    from branch_utils import get_branch_data, is_valid_branch

    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            if tank_id:
                cur.execute('''
                    SELECT * FROM fuel_tanks
                    WHERE id = %s
                ''', (tank_id,))
                return cur.fetchone()
            else:
                query = "SELECT * FROM fuel_tanks WHERE 1=1"
                params = []

                # Filter by branch
                if branch_id and branch_id != "all":
                    # Check if this is a valid branch first
                    if is_valid_branch(branch_id):
                        query += " AND branch_id = %s"
                        params.append(branch_id)
                    else:
                        # Return empty result for invalid branch ID
                        return []
                else:
                    # When not filtering by specific branch, only show data from valid branches
                    branches = get_branch_data()
                    if branches:
                        branch_ids = [branch["id"] for branch in branches]
                        placeholders = ", ".join(["%s"] * len(branch_ids))
                        query += f" AND (branch_id IS NULL OR branch_id IN ({placeholders}))"
                        params.extend(branch_ids)

                query += " ORDER BY id"

                cur.execute(query, params)
                return cur.fetchall()

# =============== Sales Management ===============

def save_sale(sale):
    """Save a new sales entry to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            total_amount = sale.litres_sold * sale.unit_price

            cur.execute('''
                INSERT INTO sales 
                (pump_id, fuel_type, litres_sold, unit_price, total_amount, 
                attendant, vehicle_number, payment_method, shift, branch_id, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                sale.pump_id,
                sale.fuel_type,
                sale.litres_sold,
                sale.unit_price,
                total_amount,
                sale.attendant,
                sale.vehicle_number,
                sale.payment_method,
                sale.shift,
                sale.branch_id,
                sale.timestamp
            ))
            sale_id = cur.fetchone()[0]

            # Update or create loyalty points if vehicle number provided
            if sale.vehicle_number:
                # Check if the vehicle has loyalty record
                cur.execute('''
                    SELECT id, points FROM loyalty_points
                    WHERE vehicle_number = %s
                ''', (sale.vehicle_number,))

                loyalty = cur.fetchone()

                if loyalty:
                    # Update existing loyalty record
                    points_to_add = int(sale.litres_sold)  # 1 point per liter
                    cur.execute('''
                        UPDATE loyalty_points
                        SET points = points + %s, last_updated = NOW()
                        WHERE vehicle_number = %s
                    ''', (points_to_add, sale.vehicle_number))
                else:
                    # Create new loyalty record
                    points = int(sale.litres_sold)  # 1 point per liter
                    cur.execute('''
                        INSERT INTO loyalty_points
                        (vehicle_number, points, last_updated)
                        VALUES (%s, %s, NOW())
                    ''', (sale.vehicle_number, points))

            conn.commit()
            return sale_id

def get_sales(start_date=None, end_date=None, attendant=None, branch_id=None, limit=100, offset=0):
    """
    Get sales entries with optional filtering.

    Args:
        start_date: Filter sales after this date
        end_date: Filter sales before this date
        attendant: Filter by attendant name
        branch_id: Filter by branch ID (if None, shows data from all valid branches)
        limit: Maximum number of records to return
        offset: Pagination offset

    Returns:
        List of sales entries matching the filters
    """
    from branch_utils import get_branch_data, is_valid_branch

    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM sales WHERE 1=1"
            params = []

            # Add date filters
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)

            if attendant:
                query += " AND attendant = %s"
                params.append(attendant)

            # Filter by branch
            if branch_id and branch_id != "all":
                # Check if this is a valid branch first
                if is_valid_branch(branch_id):
                    query += " AND branch_id = %s"
                    params.append(branch_id)
                else:
                    # Return empty result for invalid branch ID
                    return []
            else:
                # When not filtering by specific branch, only show data from valid branches
                branches = get_branch_data()
                if branches:
                    branch_ids = [branch["id"] for branch in branches]
                    placeholders = ", ".join(["%s"] * len(branch_ids))
                    query += f" AND (branch_id IS NULL OR branch_id IN ({placeholders}))"
                    params.extend(branch_ids)

            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cur.execute(query, params)
            return cur.fetchall()

def get_loyalty_points(vehicle_number):
    """Get loyalty points for a specific vehicle."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT * FROM loyalty_points
                WHERE vehicle_number = %s
            ''', (vehicle_number,))

            result = cur.fetchone()

            if not result:
                return {
                    "vehicle_number": vehicle_number,
                    "points": 0,
                    "last_updated": None
                }

            return result

# =============== Staff Management ===============

def add_attendant(attendant):
    """Add a new attendant to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO attendants 
                (name, employee_id, role, active, branch_id, contact_number, join_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                attendant.name,
                attendant.employee_id,
                attendant.role,
                attendant.active,
                attendant.branch_id,
                attendant.contact_number,
                attendant.join_date
            ))
            attendant_id = cur.fetchone()[0]
            conn.commit()
            return attendant_id

def update_attendant(employee_id, updates):
    """Update attendant information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            update_fields = []
            update_values = []

            for key, value in updates.items():
                update_fields.append(f"{key} = %s")
                update_values.append(value)

            if not update_fields:
                return False

            update_values.append(employee_id)

            query = f'''
                UPDATE attendants
                SET {", ".join(update_fields)}
                WHERE employee_id = %s
            '''

            cur.execute(query, update_values)
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def get_attendants(employee_id=None, active_only=True, branch_id=None):
    """
    Get all attendants or a specific attendant by ID.

    Args:
        employee_id (str, optional): Filter by employee ID
        active_only (bool): If True, only return active attendants
        branch_id (str, optional): Filter by branch ID

    Returns:
        List or dict: Attendant data
    """
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            if employee_id:
                # Get specific attendant
                cur.execute('''
                    SELECT * FROM attendants
                    WHERE employee_id = %s
                ''', (employee_id,))
                return cur.fetchone()
            else:
                # Build query for multiple attendants
                query = "SELECT * FROM attendants WHERE 1=1"
                params = []

                # Filter for active attendants if requested
                if active_only:
                    query += " AND active = TRUE"

                # Filter by branch
                if branch_id and branch_id != "all":
                    # Check if this is a valid branch first
                    if is_valid_branch(branch_id):
                        query += " AND branch_id = %s"
                        params.append(branch_id)
                    else:
                        # Return empty result for invalid branch ID
                        return []
                else:
                    # When not filtering by specific branch, only show data from valid branches
                    branches = get_branch_data()
                    if branches:
                        branch_ids = [branch["id"] for branch in branches]
                        placeholders = ", ".join(["%s"] * len(branch_ids))
                        query += f" AND (branch_id IS NULL OR branch_id IN ({placeholders}))"
                        params.extend(branch_ids)

                query += " ORDER BY name"

                cur.execute(query, params)
                attendants = cur.fetchall()

                # Map attendant fields to match user dict structure for dropdown rendering
                attendants_fixed = []
                for att in attendants:
                    attendants_fixed.append({
                        "username": att.get("employee_id"),
                        "full_name": att.get("name"),
                        "is_active": att.get("active", True),
                        "role": att.get("role", "pumpman"),
                        "branch_id": att.get("branch_id"),
                    })
                return attendants_fixed

def record_attendance(attendance):
    """Record attendance (check-in) for an employee."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO attendance 
                (employee_id, check_in, shift)
                VALUES (%s, %s, %s)
                RETURNING id
            ''', (
                attendance.employee_id,
                attendance.check_in,
                attendance.shift
            ))
            attendance_id = cur.fetchone()[0]
            conn.commit()
            return attendance_id

def update_attendance(attendance_id, check_out):
    """Update attendance with check-out time."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE attendance
                SET check_out = %s
                WHERE id = %s
            ''', (check_out, attendance_id))
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def get_attendance(employee_id=None, start_date=None, end_date=None):
    """Get attendance records with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM attendance WHERE 1=1"
            params = []

            if employee_id:
                query += " AND employee_id = %s"
                params.append(employee_id)

            if start_date:
                query += " AND check_in >= %s"
                params.append(start_date)

            if end_date:
                query += " AND check_in <= %s"
                params.append(end_date)

            query += " ORDER BY check_in DESC"

            cur.execute(query, params)
            return cur.fetchall()

# =============== Staff Scheduling ===============

def create_staff_schedule(schedule):
    """Create a new staff schedule entry."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            notes = schedule.get('notes', None)
            cur.execute('''
                INSERT INTO staff_schedule 
                (employee_id, schedule_date, shift, branch_id, status, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                schedule['employee_id'],
                schedule['schedule_date'],
                schedule['shift'],
                schedule['branch_id'],
                schedule['status'],
                notes,
                schedule['created_by']
            ))
            schedule_id = cur.fetchone()[0]
            conn.commit()
            return schedule_id

def update_staff_schedule(schedule_id, updates):
    """Update staff schedule information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            update_fields = []
            update_values = []

            for key, value in updates.items():
                update_fields.append(f"{key} = %s")
                update_values.append(value)

            if not update_fields:
                return False

            update_values.append(schedule_id)

            query = f'''
                UPDATE staff_schedule
                SET {", ".join(update_fields)}
                WHERE id = %s
            '''

            cur.execute(query, update_values)
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def delete_staff_schedule(schedule_id):
    """Delete a staff schedule entry."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                DELETE FROM staff_schedule
                WHERE id = %s
            ''', (schedule_id,))
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def get_staff_schedules(employee_id=None, start_date=None, end_date=None, branch_id=None):
    """
    Get staff schedules with optional filtering.

    Args:
        employee_id (str, optional): Filter by employee ID
        start_date (date, optional): Filter schedules from this date
        end_date (date, optional): Filter schedules until this date
        branch_id (str, optional): Filter by branch ID

    Returns:
        List: Staff schedule entries matching the filters
    """
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = """
                SELECT ss.*, a.name, a.role
                FROM staff_schedule ss 
                JOIN attendants a ON ss.employee_id = a.employee_id
                WHERE 1=1
            """
            params = []

            if employee_id:
                query += " AND ss.employee_id = %s"
                params.append(employee_id)

            if start_date:
                query += " AND ss.schedule_date >= %s"
                params.append(start_date)

            if end_date:
                query += " AND ss.schedule_date <= %s"
                params.append(end_date)

            # Filter by branch
            if branch_id and branch_id != "all":
                # Check if this is a valid branch first
                if is_valid_branch(branch_id):
                    query += " AND ss.branch_id = %s"
                    params.append(branch_id)
                else:
                    # Return empty result for invalid branch ID
                    return []
            else:
                # When not filtering by specific branch, only show data from valid branches
                branches = get_branch_data()
                if branches:
                    branch_ids = [branch["id"] for branch in branches]
                    placeholders = ", ".join(["%s"] * len(branch_ids))
                    query += f" AND (ss.branch_id IS NULL OR ss.branch_id IN ({placeholders}))"
                    params.extend(branch_ids)

            query += " ORDER BY ss.schedule_date, ss.shift"

            cur.execute(query, params)
            return cur.fetchall()

def generate_automatic_schedule(start_date, end_date, branch_id, created_by):
    """
    Generate an automatic schedule for staff based on their roles.

    The algorithm assigns:
    - At least 1 senior manager per day (morning shift preferred)
    - At least 1 manager per shift
    - Pumpmen distributed across shifts based on total count

    Returns the IDs of created schedule entries.
    """
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Get all active staff members
            cur.execute('''
                SELECT * FROM attendants 
                WHERE active = TRUE 
                ORDER BY 
                    CASE role 
                        WHEN 'senior_manager' THEN 1 
                        WHEN 'manager' THEN 2 
                        ELSE 3 
                    END
            ''')
            staff = cur.fetchall()

            # Group staff by role
            senior_managers = [s for s in staff if s['role'] == 'senior_manager']
            managers = [s for s in staff if s['role'] == 'manager']
            pumpmen = [s for s in staff if s['role'] == 'pumpman']

            # Setup shifts
            shifts = ['morning', 'afternoon', 'night']

            # Calculate date range
            from datetime import datetime, timedelta
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            date_range = [(start + timedelta(days=x)) for x in range((end - start).days + 1)]

            # Schedule IDs created
            schedule_ids = []

            # For each day in the range
            for schedule_date in date_range:
                # Assign senior managers (at least 1 per day, preferably morning)
                sm_index = len(schedule_ids) % len(senior_managers) if senior_managers else None
                if sm_index is not None:
                    sm = senior_managers[sm_index]
                    schedule_id = create_staff_schedule({
                        'employee_id': sm['employee_id'],
                        'schedule_date': schedule_date,
                        'shift': 'morning',
                        'branch_id': branch_id,
                        'status': 'scheduled',
                        'notes': 'Auto-generated - Senior Manager',
                        'created_by': created_by
                    })
                    schedule_ids.append(schedule_id)

                # Assign managers (at least 1 per shift)
                for shift_index, shift in enumerate(shifts):
                    # Skip morning if we already assigned a senior manager
                    if shift == 'morning' and sm_index is not None:
                        continue

                    if managers:
                        manager_index = (len(schedule_ids) + shift_index) % len(managers)
                        manager = managers[manager_index]
                        schedule_id = create_staff_schedule({
                            'employee_id': manager['employee_id'],
                            'schedule_date': schedule_date,
                            'shift': shift,
                            'branch_id': branch_id,
                            'status': 'scheduled',
                            'notes': f'Auto-generated - Manager ({shift} shift)',
                            'created_by': created_by
                        })
                        schedule_ids.append(schedule_id)

                # Distribute pumpmen across shifts based on count
                pumpmen_per_shift = max(1, len(pumpmen) // 3)  # At least 1 per shift

                for shift in shifts:
                    for i in range(pumpmen_per_shift):
                        if pumpmen:
                            pumpman_index = (len(schedule_ids) + i) % len(pumpmen)
                            pumpman = pumpmen[pumpman_index]
                            schedule_id = create_staff_schedule({
                                'employee_id': pumpman['employee_id'],
                                'schedule_date': schedule_date,
                                'shift': shift,
                                'branch_id': branch_id,
                                'status': 'scheduled',
                                'notes': f'Auto-generated - Pumpman ({shift} shift)',
                                'created_by': created_by
                            })
                            schedule_ids.append(schedule_id)

            conn.commit()
            return schedule_ids

def save_expense(expense):
    """Save a new expense to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO expenses 
                (description, amount, category, employee_id, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                expense.description,
                expense.amount,
                expense.category,
                expense.employee_id,
                expense.timestamp
            ))
            expense_id = cur.fetchone()[0]
            conn.commit()
            return expense_id

def get_expenses(start_date=None, end_date=None, category=None, employee_id=None):
    """Get expenses with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM expenses WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)

            if category:
                query += " AND category = %s"
                params.append(category)

            if employee_id:
                query += " AND employee_id = %s"
                params.append(employee_id)

            query += " ORDER BY timestamp DESC"

            cur.execute(query, params)
            return cur.fetchall()

# =============== Reports ===============

def save_report(report):
    """Save a report to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if it's an AI report
            if hasattr(report, 'summary') and hasattr(report, 'recommendations'):
                cur.execute('''
                    INSERT INTO reports 
                    (report_type, start_date, end_date, data, summary, recommendations, generated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    report.report_type,
                    report.start_date,
                    report.end_date,
                    psycopg2.extras.Json(report.data),
                    report.summary,
                    psycopg2.extras.Json(report.recommendations if report.recommendations else []),
                    report.generated_at
                ))
            else:
                cur.execute('''
                    INSERT INTO reports 
                    (report_type, start_date, end_date, data, generated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    report.report_type,
                    report.start_date,
                    report.end_date,
                    psycopg2.extras.Json(report.data),
                    report.generated_at
                ))

            report_id = cur.fetchone()[0]
            conn.commit()
            return report_id

def get_reports(report_type=None, limit=10):
    """Get reports with optional filtering by report type."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            if report_type:
                cur.execute('''
                    SELECT * FROM reports
                    WHERE report_type = %s
                    ORDER BY generated_at DESC
                    LIMIT %s
                ''', (report_type, limit))
            else:
                cur.execute('''
                    SELECT * FROM reports
                    ORDER BY generated_at DESC
                    LIMIT %s
                ''', (limit,))

            return cur.fetchall()

def get_report_by_id(report_id):
    """Get a specific report by ID."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT * FROM reports
                WHERE id = %s
            ''', (report_id,))

            return cur.fetchone()

# =============== Data Analysis ===============

def get_fuel_consumption(start_date, end_date, tank_id=None):
    """Get fuel consumption statistics for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Get fuel received
            if tank_id:
                cur.execute('''
                    SELECT 
                        tank_id,
                        SUM(litres_received) as total_received,
                        COUNT(*) as delivery_count
                    FROM fuel_entries
                    WHERE timestamp BETWEEN %s AND %s
                    AND tank_id = %s
                    GROUP BY tank_id
                ''', (start_date, end_date, tank_id))
            else:
                cur.execute('''
                    SELECT 
                        tank_id,
                        SUM(litres_received) as total_received,
                        COUNT(*) as delivery_count
                    FROM fuel_entries
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY tank_id
                ''', (start_date, end_date))

            fuel_received = cur.fetchall()

            # Get fuel sold
            if tank_id:
                # Get fuel type for the specific tank
                cur.execute('''
                    SELECT fuel_type FROM fuel_tanks
                    WHERE id = %s
                ''', (tank_id,))

                tank_info = cur.fetchone()
                if tank_info:
                    fuel_type = tank_info['fuel_type']

                    cur.execute('''
                        SELECT 
                            fuel_type,
                            SUM(litres_sold) as total_sold,
                            COUNT(*) as transaction_count,
                            SUM(total_amount) as total_sales
                        FROM sales
                        WHERE timestamp BETWEEN %s AND %s
                        AND fuel_type = %s
                        GROUP BY fuel_type
                    ''', (start_date, end_date, fuel_type))
                else:
                    # Tank not found
                    fuel_sold = []
            else:
                cur.execute('''
                    SELECT 
                        fuel_type,
                        SUM(litres_sold) as total_sold,
                        COUNT(*) as transaction_count,
                        SUM(total_amount) as total_sales
                    FROM sales
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY fuel_type
                ''', (start_date, end_date))

            fuel_sold = cur.fetchall()

            # Get current tank levels
            if tank_id:
                cur.execute('''
                    SELECT id, fuel_type, current_level, capacity
                    FROM fuel_tanks
                    WHERE id = %s
                ''', (tank_id,))
            else:
                cur.execute('''
                    SELECT id, fuel_type, current_level, capacity
                    FROM fuel_tanks
                ''')

            current_levels = cur.fetchall()

            # Combine results
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "fuel_received": fuel_received,
                "fuel_sold": fuel_sold,
                "current_levels": current_levels
            }

def get_sales_by_payment_method(start_date, end_date):
    """Get sales statistics by payment method for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Handle both timestamp and date objects
            if isinstance(start_date, datetime):
                start_date_str = start_date.isoformat()
            else:
                start_date_str = start_date

            if isinstance(end_date, datetime):
                end_date_str = end_date.isoformat()
            else:
                end_date_str = end_date

            # For debugging
            print(f"Querying sales by payment method from {start_date_str} to {end_date_str}")

            cur.execute('''
                SELECT 
                    payment_method,
                    SUM(litres_sold) as total_volume,
                    COUNT(*) as transaction_count,
                    SUM(total_amount) as total_sales
                FROM sales
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY payment_method
                ORDER BY total_sales DESC
            ''', (start_date, end_date))

            result = cur.fetchall()
            print(f"Found {len(result)} payment method groups")
            return result

def get_sales_by_attendant(start_date, end_date):
    """Get sales statistics by attendant for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Handle both timestamp and date objects
            if isinstance(start_date, datetime):
                start_date_str = start_date.isoformat()
            else:
                start_date_str = start_date

            if isinstance(end_date, datetime):
                end_date_str = end_date.isoformat()
            else:
                end_date_str = end_date

            # For debugging
            print(f"Querying sales by attendant from {start_date_str} to {end_date_str}")

            cur.execute('''
                SELECT 
                    s.attendant,
                    a.name as attendant_name,
                    SUM(s.litres_sold) as total_volume,
                    COUNT(*) as transaction_count,
                    SUM(s.total_amount) as total_sales
                FROM sales s
                LEFT JOIN attendants a ON s.attendant = a.employee_id
                WHERE s.timestamp BETWEEN %s AND %s
                GROUP BY s.attendant, a.name
                ORDER BY total_sales DESC
            ''', (start_date, end_date))

            result = cur.fetchall()
            print(f"Found {len(result)} attendant groups")
            return result

def get_daily_sales(start_date, end_date):
    """Get daily sales totals for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Handle both timestamp and date objects
            if isinstance(start_date, datetime):
                start_date_str = start_date.isoformat()
            else:
                start_date_str = start_date

            if isinstance(end_date, datetime):
                end_date_str = end_date.isoformat()
            else:
                end_date_str = end_date

            # For debugging
            print(f"Querying daily sales from {start_date_str} to {end_date_str}")

            cur.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    SUM(litres_sold) as total_volume,
                    COUNT(*) as transaction_count,
                    SUM(total_amount) as total_sales
                FROM sales
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (start_date, end_date))

            result = cur.fetchall()
            print(f"Found {len(result)} daily sales records")
            return result


# Product Management Functions
def create_product_tables():
    """Create products and product_categories tables if they don't exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create product categories table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS product_categories (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    branch_id VARCHAR(50) NOT NULL
                )
            ''')

            # Create products table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category_id VARCHAR(50) REFERENCES product_categories(id),
                    description TEXT,
                    unit_price DECIMAL(10, 2) NOT NULL,
                    cost_price DECIMAL(10, 2),
                    stock_quantity DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    minimum_stock_level DECIMAL(10, 2),
                    unit_of_measure VARCHAR(50) NOT NULL,
                    is_fuel BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    barcode VARCHAR(100),
                    image_url TEXT,
                    branch_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')

            # Create product stock transaction table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS product_stock_transactions (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(50) REFERENCES products(id),
                    quantity_change DECIMAL(10, 2) NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    reference_id VARCHAR(100),
                    balance_after DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

def add_product_category(category):
    """Add a new product category to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO product_categories (id, name, description, branch_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (
                category['id'],
                category['name'],
                category.get('description'),
                category['branch_id']
            ))

            conn.commit()
            result = cur.fetchone()
            return result[0] if result else None

def update_product_category(category_id, updates):
    """Update product category information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE product_categories
                SET name = %s, description = %s
                WHERE id = %s
                RETURNING id
            ''', (
                updates.get('name'),
                updates.get('description'),
                category_id
            ))

            conn.commit()
            return cur.rowcount > 0

def delete_product_category(category_id):
    """Delete a product category."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # First check if category has products
            cur.execute("SELECT COUNT(*) FROM products WHERE category_id = %s", (category_id,))
            count = cur.fetchone()[0]

            if count > 0:
                return False  # Cannot delete category with products

            cur.execute("DELETE FROM product_categories WHERE id = %s", (category_id,))
            conn.commit()

            return cur.rowcount > 0

def get_product_categories(branch_id=None):
    """Get all product categories or filter by branch ID."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM product_categories"
            params = []

            if branch_id and branch_id != 'all':
                query += " WHERE branch_id = %s"
                params.append(branch_id)

            query += " ORDER BY name"

            cur.execute(query, params)
            return cur.fetchall()

def add_product(product):
    """Add a new product to the database."""
    from datetime import datetime

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO products (
                    id, name, category_id, description, unit_price, cost_price,
                    stock_quantity, minimum_stock_level, unit_of_measure, is_fuel,
                    is_active, barcode, image_url, branch_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                product['id'],
                product['name'],
                product['category_id'],
                product.get('description'),
                product['unit_price'],
                product.get('cost_price'),
                product.get('stock_quantity', 0),
                product.get('minimum_stock_level'),
                product['unit_of_measure'],
                product.get('is_fuel', False),
                product.get('is_active', True),
                product.get('barcode'),
                product.get('image_url'),
                product['branch_id'],
                datetime.now()
            ))

            conn.commit()
            result = cur.fetchone()
            return result[0] if result else None

def update_product(product_id, updates):
    """Update product information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            set_clauses = []
            params = []

            # Build dynamic SET clause
            fields = [
                'name', 'category_id', 'description', 'unit_price', 'cost_price',
                'stock_quantity', 'minimum_stock_level', 'unit_of_measure', 'is_fuel',
                'is_active', 'barcode', 'image_url'
            ]

            for field in fields:
                if field in updates:
                    set_clauses.append(f"{field} = %s")
                    params.append(updates[field])

            # Add updated_at
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")

            # Build query
            query = f'''
                UPDATE products
                SET {', '.join(set_clauses)}
                WHERE id = %s
                RETURNING id
            '''

            # Add product_id as last parameter
            params.append(product_id)

            cur.execute(query, params)
            conn.commit()

            return cur.rowcount > 0

def delete_product(product_id):
    """Delete a product."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()

            return cur.rowcount > 0

def get_products(branch_id=None, category_id=None, is_active=None, search=None):
    """Get products with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = '''
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN product_categories c ON p.category_id = c.id
                WHERE 1=1
            '''

            params = []

            if branch_id and branch_id != 'all':
                query += " AND p.branch_id = %s"
                params.append(branch_id)

            if category_id:
                query += " AND p.category_id = %s"
                params.append(category_id)

            if is_active is not None:
                query += " AND p.is_active = %s"
                params.append(is_active)

            if search:
                query += " AND (p.name ILIKE %s OR p.description ILIKE %s OR p.barcode = %s)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search])

            query += " ORDER BY p.name"

            cur.execute(query, params)
            return cur.fetchall()

def get_product_by_id(product_id):
    """Get a specific product by ID."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN product_categories c ON p.category_id = c.id
                WHERE p.id = %s
            ''', (product_id,))

            return cur.fetchone()

def get_low_stock_products(branch_id=None):
    """Get products with stock levels below their minimum threshold."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = '''
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN product_categories c ON p.category_id = c.id
                WHERE p.minimum_stock_level IS NOT NULL
                AND p.stock_quantity < p.minimum_stock_level
                AND p.is_active = TRUE
            '''

            params = []

            if branch_id and branch_id != 'all':
                query += " AND p.branch_id = %s"
                params.append(branch_id)

            query += " ORDER BY (p.stock_quantity / p.minimum_stock_level) ASC"

            cur.execute(query, params)
            return cur.fetchall()

def update_product_stock(product_id, quantity_change, transaction_type, reference=None):
    """
    Update product stock quantity.

    Args:
        product_id: ID of the product
        quantity_change: Amount to add/remove (positive for additions, negative for reductions)
        transaction_type: Type of transaction (e.g., 'purchase', 'sale', 'adjustment')
        reference: Optional reference ID (e.g., sale ID, purchase order ID)

    Returns:
        dict: Updated product information
    """
    with get_db_connection() as conn:
        conn.autocommit = False
        try:
            with dict_cursor(conn) as cur:
                # Update product stock
                cur.execute('''
                    UPDATE products
                    SET stock_quantity = stock_quantity + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                ''', (quantity_change, product_id))

                updated_product = cur.fetchone()

                if not updated_product:
                    conn.rollback()
                    return None

                # Record stock transaction
                cur.execute('''
                    INSERT INTO product_stock_transactions (
                        product_id, quantity_change, transaction_type, 
                        reference_id, balance_after
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    product_id,
                    quantity_change,
                    transaction_type,
                    reference,
                    updated_product['stock_quantity']
                ))

                conn.commit()
                return updated_product

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.autocommit = True

def get_fuel_consumption(start_date, end_date, tank_id=None):
    """Get fuel consumption statistics for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Get fuel received
            if tank_id:
                cur.execute('''
                    SELECT 
                        tank_id,
                        SUM(litres_received) as total_received,
                        COUNT(*) as delivery_count
                    FROM fuel_entries
                    WHERE timestamp BETWEEN %s AND %s
                    AND tank_id = %s
                    GROUP BY tank_id
                ''', (start_date, end_date, tank_id))
            else:
                cur.execute('''
                    SELECT 
                        tank_id,
                        SUM(litres_received) as total_received,
                        COUNT(*) as delivery_count
                    FROM fuel_entries
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY tank_id
                ''', (start_date, end_date))

            fuel_received = cur.fetchall()

            # Get fuel sold
            if tank_id:
                # Get fuel type for the specific tank
                cur.execute('''
                    SELECT fuel_type FROM fuel_tanks
                    WHERE id = %s
                ''', (tank_id,))

                tank_info = cur.fetchone()
                if tank_info:
                    fuel_type = tank_info['fuel_type']

                    cur.execute('''
                        SELECT 
                            fuel_type,
                            SUM(litres_sold) as total_sold,
                            COUNT(*) as transaction_count,
                            SUM(total_amount) as total_sales
                        FROM sales
                        WHERE timestamp BETWEEN %s AND %s
                        AND fuel_type = %s
                        GROUP BY fuel_type
                    ''', (start_date, end_date, fuel_type))
                else:
                    # Tank not found
                    fuel_sold = []
            else:
                cur.execute('''
                    SELECT 
                        fuel_type,
                        SUM(litres_sold) as total_sold,
                        COUNT(*) as transaction_count,
                        SUM(total_amount) as total_sales
                    FROM sales
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY fuel_type
                ''', (start_date, end_date))

            fuel_sold = cur.fetchall()

            # Get current tank levels
            if tank_id:
                cur.execute('''
                    SELECT id, fuel_type, current_level, capacity
                    FROM fuel_tanks
                    WHERE id = %s
                ''', (tank_id,))
            else:
                cur.execute('''
                    SELECT id, fuel_type, current_level, capacity
                    FROM fuel_tanks
                ''')

            current_levels = cur.fetchall()

            # Combine results
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "fuel_received": fuel_received,
                "fuel_sold": fuel_sold,
                "current_levels": current_levels
            }

def get_sales_by_payment_method(start_date, end_date):
    """Get sales statistics by payment method for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Handle both timestamp and date objects
            if isinstance(start_date, datetime):
                start_date_str = start_date.isoformat()
            else:
                start_date_str = start_date

            if isinstance(end_date, datetime):
                end_date_str = end_date.isoformat()
            else:
                end_date_str = end_date

            # For debugging
            print(f"Querying sales by payment method from {start_date_str} to {end_date_str}")

            cur.execute('''
                SELECT 
                    payment_method,
                    SUM(litres_sold) as total_volume,
                    COUNT(*) as transaction_count,
                    SUM(total_amount) as total_sales
                FROM sales
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY payment_method
                ORDER BY total_sales DESC
            ''', (start_date, end_date))

            result = cur.fetchall()
            print(f"Found {len(result)} payment method groups")
            return result

def get_sales_by_attendant(start_date, end_date):
    """Get sales statistics by attendant for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Handle both timestamp and date objects
            if isinstance(start_date, datetime):
                start_date_str = start_date.isoformat()
            else:
                start_date_str = start_date

            if isinstance(end_date, datetime):
                end_date_str = end_date.isoformat()
            else:
                end_date_str = end_date

            # For debugging
            print(f"Querying sales by attendant from {start_date_str} to {end_date_str}")

            cur.execute('''
                SELECT 
                    s.attendant,
                    a.name as attendant_name,
                    SUM(s.litres_sold) as total_volume,
                    COUNT(*) as transaction_count,
                    SUM(s.total_amount) as total_sales
                FROM sales s
                LEFT JOIN attendants a ON s.attendant = a.employee_id
                WHERE s.timestamp BETWEEN %s AND %s
                GROUP BY s.attendant, a.name
                ORDER BY total_sales DESC
            ''', (start_date, end_date))

            result = cur.fetchall()
            print(f"Found {len(result)} attendant groups")
            return result

def get_daily_sales(start_date, end_date):
    """Get daily sales totals for a specific period."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Handle both timestamp and date objects
            if isinstance(start_date, datetime):
                start_date_str = start_date.isoformat()
            else:
                start_date_str = start_date

            if isinstance(end_date, datetime):
                end_date_str = end_date.isoformat()
            else:
                end_date_str = end_date

            # For debugging
            print(f"Querying daily sales from {start_date_str} to {end_date_str}")

            cur.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    SUM(litres_sold) as total_volume,
                    COUNT(*) as transaction_count,
                    SUM(total_amount) as total_sales
                FROM sales
                WHERE timestamp BETWEEN %s AND %s
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (start_date, end_date))

            result = cur.fetchall()
            print(f"Found {len(result)} daily sales records")
            return result


# Product Management Functions
def create_product_tables():
    """Create products and product_categories tables if they don't exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create product categories table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS product_categories (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    branch_id VARCHAR(50) NOT NULL
                )
            ''')

            # Create products table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category_id VARCHAR(50) REFERENCES product_categories(id),
                    description TEXT,
                    unit_price DECIMAL(10, 2) NOT NULL,
                    cost_price DECIMAL(10, 2),
                    stock_quantity DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    minimum_stock_level DECIMAL(10, 2),
                    unit_of_measure VARCHAR(50) NOT NULL,
                    is_fuel BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    barcode VARCHAR(100),
                    image_url TEXT,
                    branch_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')

            # Create product stock transaction table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS product_stock_transactions (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(50) REFERENCES products(id),
                    quantity_change DECIMAL(10, 2) NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    reference_id VARCHAR(100),
                    balance_after DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

def add_product_category(category):
    """Add a new product category to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO product_categories (id, name, description, branch_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (
                category['id'],
                category['name'],
                category.get('description'),
                category['branch_id']
            ))

            conn.commit()
            result = cur.fetchone()
            return result[0] if result else None

def update_product_category(category_id, updates):
    """Update product category information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE product_categories
                SET name = %s, description = %s
                WHERE id = %s
                RETURNING id
            ''', (
                updates.get('name'),
                updates.get('description'),
                category_id
            ))

            conn.commit()
            return cur.rowcount > 0

def delete_product_category(category_id):
    """Delete a product category."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # First check if category has products
            cur.execute("SELECT COUNT(*) FROM products WHERE category_id = %s", (category_id,))
            count = cur.fetchone()[0]

            if count > 0:
                return False  # Cannot delete category with products

            cur.execute("DELETE FROM product_categories WHERE id = %s", (category_id,))
            conn.commit()

            return cur.rowcount > 0

def get_product_categories(branch_id=None):
    """Get all product categories or filter by branch ID."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM product_categories"
            params = []

            if branch_id and branch_id != 'all':
                query += " WHERE branch_id = %s"
                params.append(branch_id)

            query += " ORDER BY name"

            cur.execute(query, params)
            return cur.fetchall()

def add_product(product):
    """Add a new product to the database."""
    from datetime import datetime

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO products (
                    id, name, category_id, description, unit_price, cost_price,
                    stock_quantity, minimum_stock_level, unit_of_measure, is_fuel,
                    is_active, barcode, image_url, branch_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                product['id'],
                product['name'],
                product['category_id'],
                product.get('description'),
                product['unit_price'],
                product.get('cost_price'),
                product.get('stock_quantity', 0),
                product.get('minimum_stock_level'),
                product['unit_of_measure'],
                product.get('is_fuel', False),
                product.get('is_active', True),
                product.get('barcode'),
                product.get('image_url'),
                product['branch_id'],
                datetime.now()
            ))

            conn.commit()
            result = cur.fetchone()
            return result[0] if result else None

def update_product(product_id, updates):
    """Update product information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            set_clauses = []
            params = []

            # Build dynamic SET clause
            fields = [
                'name', 'category_id', 'description', 'unit_price', 'cost_price',
                'stock_quantity', 'minimum_stock_level', 'unit_of_measure', 'is_fuel',
                'is_active', 'barcode', 'image_url'
            ]

            for field in fields:
                if field in updates:
                    set_clauses.append(f"{field} = %s")
                    params.append(updates[field])

            # Add updated_at
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")

            # Build query
            query = f'''
                UPDATE products
                SET {', '.join(set_clauses)}
                WHERE id = %s
                RETURNING id
            '''

            # Add product_id as last parameter
            params.append(product_id)

            cur.execute(query, params)
            conn.commit()

            return cur.rowcount > 0

def delete_product(product_id):
    """Delete a product."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            conn.commit()

            return cur.rowcount > 0

def get_products(branch_id=None, category_id=None, is_active=None, search=None):
    """Get products with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = '''
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN product_categories c ON p.category_id = c.id
                WHERE 1=1
            '''

            params = []

            if branch_id and branch_id != 'all':
                query += " AND p.branch_id = %s"
                params.append(branch_id)

            if category_id:
                query += " AND p.category_id = %s"
                params.append(category_id)

            if is_active is not None:
                query += " AND p.is_active = %s"
                params.append(is_active)

            if search:
                query += " AND (p.name ILIKE %s OR p.description ILIKE %s OR p.barcode = %s)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search])

            query += " ORDER BY p.name"

            cur.execute(query, params)
            return cur.fetchall()

def get_product_by_id(product_id):
    """Get a specific product by ID."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN product_categories c ON p.category_id = c.id
                WHERE p.id = %s
            ''', (product_id,))

            return cur.fetchone()

def get_low_stock_products(branch_id=None):
    """Get products with stock levels below their minimum threshold."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = '''
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN product_categories c ON p.category_id = c.id
                WHERE p.minimum_stock_level IS NOT NULL
                AND p.stock_quantity < p.minimum_stock_level
                AND p.is_active = TRUE
            '''

            params = []

            if branch_id and branch_id != 'all':
                query += " AND p.branch_id = %s"
                params.append(branch_id)

            query += " ORDER BY (p.stock_quantity / p.minimum_stock_level) ASC"

            cur.execute(query, params)
            return cur.fetchall()

def update_product_stock(product_id, quantity_change, transaction_type, reference=None):
    """
    Update product stock quantity.

    Args:
        product_id: ID of the product
        quantity_change: Amount to add/remove (positive for additions, negative for reductions)
        transaction_type: Type of transaction (e.g., 'purchase', 'sale', 'adjustment')
        reference: Optional reference ID (e.g., sale ID, purchase order ID)

    Returns:
        dict: Updated product information
    """
    with get_db_connection() as conn:
        conn.autocommit = False
        try:
            with dict_cursor(conn) as cur:
                # Update product stock
                cur.execute('''
                    UPDATE products
                    SET stock_quantity = stock_quantity + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                ''', (quantity_change, product_id))

                updated_product = cur.fetchone()

                if not updated_product:
                    conn.rollback()
                    return None

                # Record stock transaction
                cur.execute('''
                    INSERT INTO product_stock_transactions (
                        product_id, quantity_change, transaction_type, 
                        reference_id, balance_after
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    product_id,
                    quantity_change,
                    transaction_type,
                    reference,
                    updated_product['stock_quantity']
                ))

                conn.commit()
                return updated_product

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.autocommit = True

# =============== Fuel Types Table ---
def create_fuel_types_table():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS fuel_types (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL
                );
            ''')
            conn.commit()

def get_fuel_types():
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('SELECT * FROM fuel_types ORDER BY name')
            return cur.fetchall()

def add_fuel_type(name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO fuel_types (name) VALUES (%s) ON CONFLICT DO NOTHING', (name,))
            conn.commit()

def update_fuel_type(type_id, name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE fuel_types SET name=%s WHERE id=%s', (name, type_id))
            conn.commit()

def delete_fuel_type(type_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM fuel_types WHERE id=%s', (type_id,))
            conn.commit()

# =============== Subscription Plan Table Management ---
def create_subscription_plan_table():
    with get_db_connection(allow_no_tenant=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id SERIAL PRIMARY KEY,
                    plan_type VARCHAR(32) UNIQUE NOT NULL,
                    amount NUMERIC(10,2) NOT NULL
                )
            ''')
            # Insert default plans if not present
            cur.execute("SELECT COUNT(*) FROM subscription_plans")
            if cur.fetchone()[0] == 0:
                cur.execute('''
                    INSERT INTO subscription_plans (plan_type, amount) VALUES
                    ('monthly', 999),
                    ('yearly', 9999)
                ''')
            conn.commit()

# --- Update Subscriptions Table ---
def create_subscription_table():
    with get_db_connection(allow_no_tenant=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    branch_id VARCHAR(32) NOT NULL,
                    plan_id INTEGER NOT NULL REFERENCES subscription_plans(id),
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL
                )
            ''')
            conn.commit()

def add_subscription(branch_id, plan_id, start_date, end_date):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO subscriptions (branch_id, plan_id, start_date, end_date)
                VALUES (%s, %s, %s, %s)
            ''', (branch_id, plan_id, start_date, end_date))
            conn.commit()

def get_latest_subscription(branch_id):
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT s.*, p.plan_type, p.amount
                FROM subscriptions s
                JOIN subscription_plans p ON s.plan_id = p.id
                WHERE branch_id = %s
                ORDER BY end_date DESC LIMIT 1
            ''', (branch_id,))
            return cur.fetchone()

def get_subscription_types():
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT * FROM subscription_plans ORDER BY plan_type
            ''')
            return cur.fetchall()

# For overview: get all latest subscriptions per branch with plan info
def get_latest_subscriptions_all():
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT DISTINCT ON (s.branch_id) s.*, p.plan_type, p.amount
                FROM subscriptions s
                JOIN subscription_plans p ON s.plan_id = p.id
                ORDER BY s.branch_id, s.end_date DESC
            ''')
            return cur.fetchall()

# =============== Expense Categories ===============

def create_expense_categories_table():
    """Create the expense_categories table and insert static categories if needed."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS expense_categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(64) UNIQUE NOT NULL,
                    description TEXT
                )
            ''')
            static_categories = [
                ("Maintenance", "All equipment and facility maintenance costs"),
                ("Operational", "Day-to-day operational expenses"),
                ("Administrative", "Office and administrative expenses"),
                ("Utilities", "Water, electricity, internet, etc."),
                ("Taxes", "Government taxes and statutory payments"),
                ("Salaries", "Employee salaries and wages"),
                ("Other", "Miscellaneous expenses")
            ]
            for name, desc in static_categories:
                cur.execute('''
                    INSERT INTO expense_categories (name, description)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO NOTHING
                ''', (name, desc))
            conn.commit()

def get_expense_categories():
    """Fetch all expense categories from the database."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('SELECT * FROM expense_categories ORDER BY name')
            return cur.fetchall()

def reset_subscriptions_table():
    with get_db_connection(allow_no_tenant=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''DROP TABLE IF EXISTS subscriptions CASCADE''')
            conn.commit()
    create_subscription_table()

def add_subscription_plan(plan_type, amount):
    with get_db_connection(allow_no_tenant=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO subscription_plans (plan_type, amount) VALUES (%s, %s) ON CONFLICT (plan_type) DO NOTHING''', (plan_type, amount))
            conn.commit()

def update_subscription_plan(plan_id, plan_type, amount):
    with get_db_connection(allow_no_tenant=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''UPDATE subscription_plans SET plan_type=%s, amount=%s WHERE id=%s''', (plan_type, amount, plan_id))
            conn.commit()

def delete_subscription_plan(plan_id):
    with get_db_connection(allow_no_tenant=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''DELETE FROM subscription_plans WHERE id=%s''', (plan_id,))
            conn.commit()

# =============== Branch Management ---
def create_branch(id, name, address=None, phone=None, email=None, is_active=True):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO branches (id, name, address, phone, email, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (id, name, address, phone, email, is_active))
        conn.commit()

def get_branches(active_only=False):
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = 'SELECT * FROM branches'
            if active_only:
                query += ' WHERE is_active = TRUE'
            cur.execute(query)
            return cur.fetchall()

def update_branch(id, name=None, address=None, phone=None, email=None, is_active=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            updates = []
            params = []
            if name is not None:
                updates.append('name = %s')
                params.append(name)
            if address is not None:
                updates.append('address = %s')
                params.append(address)
            if phone is not None:
                updates.append('phone = %s')
                params.append(phone)
            if email is not None:
                updates.append('email = %s')
                params.append(email)
            if is_active is not None:
                updates.append('is_active = %s')
                params.append(is_active)
            params.append(id)
            if updates:
                cur.execute(f'''UPDATE branches SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s''', params)
        conn.commit()

def delete_branch(id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM branches WHERE id = %s', (id,))
        conn.commit()
