import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

ALTER_SQL = '''\
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(120),
    ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50),
    ADD COLUMN IF NOT EXISTS created_by INTEGER;
'''

def main():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(ALTER_SQL)
            conn.commit()
            print("users table altered successfully.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
