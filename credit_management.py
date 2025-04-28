from datetime import datetime
from db import get_db_connection, dict_cursor
from models import CreditCustomer, CreditTransaction

def create_credit_tables():
    """Create credit_customers and credit_transactions tables if they don't exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create credit_customers table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS credit_customers (
                    id SERIAL PRIMARY KEY,
                    customer_id VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    customer_type VARCHAR(20) NOT NULL,
                    contact_person VARCHAR(100),
                    phone_number VARCHAR(20) NOT NULL,
                    whatsapp_number VARCHAR(20),
                    email VARCHAR(100),
                    address TEXT,
                    credit_limit FLOAT NOT NULL DEFAULT 0,
                    current_balance FLOAT NOT NULL DEFAULT 0,
                    last_payment_date TIMESTAMP,
                    branch_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    credit_days INTEGER DEFAULT 30
                )
            ''')
            
            # Create credit_transactions table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS credit_transactions (
                    id SERIAL PRIMARY KEY,
                    customer_id VARCHAR(50) NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    amount FLOAT NOT NULL,
                    sale_id INTEGER,
                    reference_number VARCHAR(50),
                    payment_method VARCHAR(50),
                    notes TEXT,
                    branch_id VARCHAR(50) NOT NULL,
                    recorded_by VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    balance_after FLOAT NOT NULL
                )
            ''')
            conn.commit()

def add_credit_customer(customer):
    """Add a new credit customer to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Set default credit days based on customer type
            credit_days = getattr(customer, 'credit_days', 30)
            if customer.customer_type == 'government':
                # Government customers usually have longer credit periods
                credit_days = getattr(customer, 'credit_days', 60)
                
            cur.execute('''
                INSERT INTO credit_customers (
                    customer_id, name, customer_type, contact_person, phone_number,
                    whatsapp_number, email, address, credit_limit, current_balance,
                    last_payment_date, branch_id, timestamp, status, credit_days
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                customer.customer_id,
                customer.name,
                customer.customer_type,
                customer.contact_person,
                customer.phone_number,
                customer.whatsapp_number,
                customer.email,
                customer.address,
                customer.credit_limit,
                customer.current_balance,
                customer.last_payment_date,
                customer.branch_id,
                customer.timestamp,
                customer.status,
                credit_days
            ))
            result = cur.fetchone()
            customer_id = result[0] if result else None
            conn.commit()
            return customer_id

def update_credit_customer(customer_id, updates):
    """Update credit customer information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Build update query dynamically based on provided fields
            query_parts = []
            params = []
            
            for key, value in updates.items():
                if key in [
                    'name', 'customer_type', 'contact_person', 'phone_number',
                    'whatsapp_number', 'email', 'address', 'credit_limit',
                    'status', 'credit_days'
                ]:
                    query_parts.append(f"{key} = %s")
                    params.append(value)
            
            if not query_parts:
                return False
                
            query = f"UPDATE credit_customers SET {', '.join(query_parts)} WHERE customer_id = %s"
            params.append(customer_id)
            
            cur.execute(query, params)
            updated = cur.rowcount > 0
            conn.commit()
            return updated

def get_credit_customers(customer_id=None, customer_type=None, status='active', branch_id=None, limit=100, offset=0):
    """
    Get credit customers with optional filtering.
    
    Args:
        customer_id (str, optional): Filter by customer ID
        customer_type (str, optional): Filter by customer type (e.g., 'general', 'government')
        status (str, optional): Filter by status (e.g., 'active', 'inactive')
        branch_id (str, optional): Filter by branch ID
        limit (int): Maximum number of records to return
        offset (int): Pagination offset
        
    Returns:
        List or dict: Credit customer data
    """
    from branch_utils import get_branch_data, is_valid_branch
    
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM credit_customers WHERE 1=1"
            params = []
            
            if customer_id:
                query += " AND customer_id = %s"
                params.append(customer_id)
            
            if customer_type:
                query += " AND customer_type = %s"
                params.append(customer_type)
                
            if status:
                query += " AND status = %s"
                params.append(status)
                
            # Filter by branch
            if branch_id and branch_id != "all":
                # Check if this is a valid branch first
                if is_valid_branch(branch_id):
                    query += " AND branch_id = %s"
                    params.append(branch_id)
                else:
                    # Return empty result for invalid branch ID
                    return [] if not customer_id else None
            else:
                # When not filtering by specific branch, only show data from valid branches
                branches = get_branch_data()
                if branches:
                    branch_ids = [branch["id"] for branch in branches]
                    placeholders = ", ".join(["%s"] * len(branch_ids))
                    query += f" AND (branch_id IS NULL OR branch_id IN ({placeholders}))"
                    params.extend(branch_ids)
            
            query += " ORDER BY name LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            
            if customer_id:
                return cur.fetchone()
            else:
                return cur.fetchall()

def record_credit_transaction(transaction, current_balance=None):
    """
    Record a credit transaction (purchase or payment).
    
    Args:
        transaction: CreditTransaction object
        current_balance: Current balance before transaction (if None, fetched from DB)
        
    Returns:
        id: Transaction ID
        balance_after: New balance after transaction
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get current balance if not provided
            if current_balance is None:
                cur.execute("SELECT current_balance FROM credit_customers WHERE customer_id = %s", 
                           (transaction.customer_id,))
                result = cur.fetchone()
                if not result:
                    raise ValueError(f"Customer with ID {transaction.customer_id} not found")
                current_balance = result[0]
            
            # Calculate new balance
            if transaction.transaction_type == 'purchase':
                balance_after = current_balance + transaction.amount
            elif transaction.transaction_type == 'payment':
                balance_after = current_balance - transaction.amount
            else:
                raise ValueError(f"Invalid transaction type: {transaction.transaction_type}")
            
            # Insert transaction
            cur.execute('''
                INSERT INTO credit_transactions (
                    customer_id, transaction_type, amount, sale_id, reference_number,
                    payment_method, notes, branch_id, recorded_by, timestamp, balance_after
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                transaction.customer_id,
                transaction.transaction_type,
                transaction.amount,
                transaction.sale_id,
                transaction.reference_number,
                transaction.payment_method,
                transaction.notes,
                transaction.branch_id,
                transaction.recorded_by,
                transaction.timestamp,
                balance_after
            ))
            
            result = cur.fetchone()
            transaction_id = result[0] if result else None
            
            # Update customer balance
            cur.execute('''
                UPDATE credit_customers 
                SET current_balance = %s, 
                    last_payment_date = CASE WHEN %s = 'payment' THEN %s ELSE last_payment_date END
                WHERE customer_id = %s
            ''', (
                balance_after,
                transaction.transaction_type,
                transaction.timestamp if transaction.transaction_type == 'payment' else None,
                transaction.customer_id
            ))
            
            conn.commit()
            return transaction_id, balance_after

def get_credit_transactions(customer_id=None, transaction_type=None, branch_id=None, 
                          start_date=None, end_date=None, limit=100, offset=0):
    """
    Get credit transactions with optional filtering.
    
    Args:
        customer_id (str, optional): Filter by customer ID
        transaction_type (str, optional): Filter by transaction type (e.g., 'purchase', 'payment')
        branch_id (str, optional): Filter by branch ID
        start_date (datetime, optional): Filter transactions after this date
        end_date (datetime, optional): Filter transactions before this date
        limit (int): Maximum number of records to return
        offset (int): Pagination offset
        
    Returns:
        List: Credit transaction data
    """
    from branch_utils import get_branch_data, is_valid_branch
    
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM credit_transactions WHERE 1=1"
            params = []
            
            if customer_id:
                query += " AND customer_id = %s"
                params.append(customer_id)
            
            if transaction_type:
                query += " AND transaction_type = %s"
                params.append(transaction_type)
            
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

def get_customer_transaction_history(customer_id, limit=50):
    """
    Get transaction history for a specific customer.

    Args:
        customer_id (str): The ID of the customer
        limit (int): Maximum number of transactions to retrieve
        
    Returns:
        dict or None: Customer information and transaction history, or None if customer not found
    """
    from branch_utils import is_valid_branch
    
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Get customer info
            cur.execute("SELECT * FROM credit_customers WHERE customer_id = %s", (customer_id,))
            customer = cur.fetchone()
            
            # Check if the customer exists and belongs to a valid branch
            if not customer:
                return None
            
            # Verify branch is valid if customer has a branch_id
            if customer.get('branch_id') and not is_valid_branch(customer['branch_id']):
                return None
            
            # Get transactions from valid branches
            from branch_utils import get_branch_data
            branches = get_branch_data()
            
            if branches:
                # Create a list of valid branch IDs
                branch_ids = [branch["id"] for branch in branches]
                placeholders = ", ".join(["%s"] * len(branch_ids))
                
                # Query that includes branch validation
                query = f'''
                    SELECT * FROM credit_transactions 
                    WHERE customer_id = %s 
                    AND (branch_id IS NULL OR branch_id IN ({placeholders}))
                    ORDER BY timestamp DESC 
                    LIMIT %s
                '''
                params = [customer_id]
                params.extend(branch_ids)
                params.append(limit)
                
                cur.execute(query, params)
            else:
                # If no branches defined, just get transactions without branch filter
                cur.execute('''
                    SELECT * FROM credit_transactions 
                    WHERE customer_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                ''', (customer_id, limit))
            
            transactions = cur.fetchall()
            
            return {
                "customer": customer,
                "transactions": transactions
            }

def get_due_payments(branch_id=None, days_overdue=30, min_amount=1000):
    """
    Get customers with outstanding balances over the specified amount 
    and no payment in the last X days.
    
    Args:
        branch_id (str, optional): Filter by branch ID
        days_overdue (int): Minimum days since last payment to consider overdue
        min_amount (float): Minimum balance to include in results
        
    Returns:
        List: Credit customers with overdue payments
    """
    from branch_utils import get_branch_data, is_valid_branch
    
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = """
                SELECT c.*, 
                    CASE WHEN c.last_payment_date IS NULL THEN
                        EXTRACT(DAY FROM NOW() - c.timestamp)::INTEGER
                    ELSE
                        EXTRACT(DAY FROM NOW() - c.last_payment_date)::INTEGER
                    END AS days_since_payment
                FROM credit_customers c
                WHERE c.current_balance >= %s
                AND c.status = 'active'
                AND (
                    c.last_payment_date IS NULL OR
                    NOW() - c.last_payment_date > INTERVAL '%s days'
                )
            """
            
            params = [min_amount, days_overdue]
            
            # Filter by branch
            if branch_id and branch_id != "all":
                # Check if this is a valid branch first
                if is_valid_branch(branch_id):
                    query += " AND c.branch_id = %s"
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
                    query += f" AND (c.branch_id IS NULL OR c.branch_id IN ({placeholders}))"
                    params.extend(branch_ids)
                
            query += " ORDER BY days_since_payment DESC, c.current_balance DESC"
            
            cur.execute(query, params)
            return cur.fetchall()

def check_credit_eligibility(customer_id):
    """
    Check if a customer is eligible for credit.
    
    Returns a dictionary with:
    - eligibility: True/False
    - reason: Reason for not being eligible (if applicable)
    - credit_status: Status information about the customer
    """
    from branch_utils import is_valid_branch
    
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Get customer info with days since last payment
            query = """
                SELECT c.*,
                    CASE WHEN c.last_payment_date IS NULL THEN
                        EXTRACT(DAY FROM NOW() - c.timestamp)::INTEGER
                    ELSE
                        EXTRACT(DAY FROM NOW() - c.last_payment_date)::INTEGER
                    END AS days_since_payment
                FROM credit_customers c
                WHERE c.customer_id = %s AND c.status = 'active'
            """
            
            cur.execute(query, (customer_id,))
            customer = cur.fetchone()
            
            if not customer:
                return {
                    "eligibility": False,
                    "reason": "Customer not found or account inactive",
                    "credit_status": None
                }
            
            # Verify branch is valid if customer has a branch_id
            if customer.get('branch_id') and not is_valid_branch(customer['branch_id']):
                return {
                    "eligibility": False,
                    "reason": "Customer belongs to a branch that no longer exists",
                    "credit_status": None
                }
            
            # Check if customer is within credit limit
            available_credit = customer['credit_limit'] - customer['current_balance']
            if available_credit <= 0:
                return {
                    "eligibility": False,
                    "reason": "Credit limit reached",
                    "credit_status": {
                        "current_balance": customer['current_balance'],
                        "credit_limit": customer['credit_limit'],
                        "available_credit": available_credit,
                        "days_since_payment": customer['days_since_payment'],
                        "credit_days": customer['credit_days'],
                        "is_overdue": customer['days_since_payment'] > customer['credit_days']
                    }
                }
            
            # Check if payment is overdue
            if customer['days_since_payment'] > customer['credit_days']:
                return {
                    "eligibility": False,
                    "reason": f"Payment overdue by {customer['days_since_payment'] - customer['credit_days']} days",
                    "credit_status": {
                        "current_balance": customer['current_balance'],
                        "credit_limit": customer['credit_limit'],
                        "available_credit": available_credit,
                        "days_since_payment": customer['days_since_payment'],
                        "credit_days": customer['credit_days'],
                        "is_overdue": True,
                        "days_overdue": customer['days_since_payment'] - customer['credit_days']
                    }
                }
            
            # Customer is eligible
            return {
                "eligibility": True,
                "reason": None,
                "credit_status": {
                    "current_balance": customer['current_balance'],
                    "credit_limit": customer['credit_limit'],
                    "available_credit": available_credit,
                    "days_since_payment": customer['days_since_payment'],
                    "credit_days": customer['credit_days'],
                    "is_overdue": False,
                    "days_remaining": customer['credit_days'] - customer['days_since_payment']
                }
            }

def get_credit_summary_by_type(branch_id=None):
    """
    Get credit summary statistics grouped by customer type.
    
    Args:
        branch_id (str, optional): Filter by branch ID
        
    Returns:
        List: Credit summary data grouped by customer type
    """
    from branch_utils import get_branch_data, is_valid_branch
    
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = """
                SELECT 
                    customer_type,
                    COUNT(*) as customer_count,
                    SUM(current_balance) as total_balance,
                    SUM(credit_limit) as total_limit,
                    AVG(current_balance) as avg_balance,
                    MAX(current_balance) as max_balance
                FROM credit_customers
                WHERE status = 'active'
            """
            
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
                
            query += " GROUP BY customer_type ORDER BY total_balance DESC"
            
            cur.execute(query, params)
            return cur.fetchall()