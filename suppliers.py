from datetime import datetime
from db import get_db_connection, dict_cursor

class Supplier:
    def __init__(self, name, contact, address, status='active', created_at=None):
        self.name = name
        self.contact = contact
        self.address = address
        self.status = status
        self.created_at = created_at or datetime.now()

    def as_dict(self):
        return {
            'name': self.name,
            'contact': self.contact,
            'address': self.address,
            'status': self.status,
            'created_at': self.created_at
        }

def create_suppliers_table():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS suppliers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    contact VARCHAR(100),
                    address TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''')
            conn.commit()

def add_supplier(name, contact, address):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO suppliers (name, contact, address, status)
                VALUES (%s, %s, %s, 'active') RETURNING id
            ''', (name, contact, address))
            supplier_id = cur.fetchone()[0]
            conn.commit()
            return supplier_id

def set_supplier_status(supplier_id, status):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE suppliers SET status=%s WHERE id=%s
            ''', (status, supplier_id))
            conn.commit()

def delete_supplier(supplier_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM suppliers WHERE id=%s', (supplier_id,))
            conn.commit()

def get_suppliers(active_only=False):
    with get_db_connection() as conn:
        with dict_cursor(conn) as cur:
            if active_only:
                cur.execute('SELECT * FROM suppliers WHERE status = %s', ('active',))
            else:
                cur.execute('SELECT * FROM suppliers')
            return cur.fetchall()
