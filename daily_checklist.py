from datetime import datetime
from db import get_db_connection, dict_cursor
from models import DailyChecklist

def create_daily_checklist_table():
    """Create daily_checklist table if it doesn't exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS daily_checklist (
                    id SERIAL PRIMARY KEY,
                    branch_id VARCHAR(50) NOT NULL,
                    completed_by VARCHAR(100) NOT NULL,
                    date TIMESTAMP NOT NULL DEFAULT NOW(),
                    dispenser_test_done BOOLEAN NOT NULL DEFAULT FALSE,
                    pump_cleaning_done BOOLEAN NOT NULL DEFAULT FALSE,
                    bathroom_cleaning_done BOOLEAN NOT NULL DEFAULT FALSE,
                    notes TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')
            conn.commit()

def save_checklist(checklist):
    """Save a new daily checklist to the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO daily_checklist (
                    branch_id, completed_by, date, dispenser_test_done, 
                    pump_cleaning_done, bathroom_cleaning_done, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                checklist.branch_id,
                checklist.completed_by,
                checklist.date,
                checklist.dispenser_test_done,
                checklist.pump_cleaning_done,
                checklist.bathroom_cleaning_done,
                checklist.notes
            ))
            checklist_id = cur.fetchone()[0]
            conn.commit()
            return checklist_id

def get_checklists(branch_id=None, start_date=None, end_date=None, limit=100, offset=0):
    """Get daily checklists with optional filtering."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            query = "SELECT * FROM daily_checklist WHERE 1=1"
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
            
            query += " ORDER BY date DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            return cur.fetchall()

def get_checklist_by_id(checklist_id):
    """Get a specific checklist by ID."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('''
                SELECT * FROM daily_checklist
                WHERE id = %s
            ''', (checklist_id,))
            return cur.fetchone()
            
def get_checklist_by_date(branch_id, date):
    """Get a checklist for a specific branch and date."""
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            # Convert date to start and end of day
            start_date = datetime.combine(date.date(), datetime.min.time())
            end_date = datetime.combine(date.date(), datetime.max.time())
            
            cur.execute('''
                SELECT * FROM daily_checklist
                WHERE branch_id = %s AND date >= %s AND date <= %s
                ORDER BY date DESC LIMIT 1
            ''', (branch_id, start_date, end_date))
            return cur.fetchone()

def update_checklist(checklist_id, updates):
    """Update checklist information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            update_fields = []
            update_values = []
            
            for key, value in updates.items():
                update_fields.append(f"{key} = %s")
                update_values.append(value)
            
            if not update_fields:
                return False
            
            update_values.append(checklist_id)
            
            query = f'''
                UPDATE daily_checklist
                SET {", ".join(update_fields)}
                WHERE id = %s
            '''
            
            cur.execute(query, update_values)
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0

def delete_checklist(checklist_id):
    """Delete a checklist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                DELETE FROM daily_checklist
                WHERE id = %s
            ''', (checklist_id,))
            rows_affected = cur.rowcount
            conn.commit()
            return rows_affected > 0