"""
Migration script to add plan_id to subscriptions, backfill from plan_type, and drop old columns.
Run this ONCE after deploying the new subscription schema.
"""
import psycopg2
import os

def migrate():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    # 1. Add plan_id column if not exists
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='subscriptions' AND column_name='plan_id'
            ) THEN
                ALTER TABLE subscriptions ADD COLUMN plan_id INTEGER;
            END IF;
        END$$;
    """)
    # 2. Backfill plan_id using plan_type
    cur.execute("""
        UPDATE subscriptions s
        SET plan_id = p.id
        FROM subscription_plans p
        WHERE s.plan_type = p.plan_type AND s.plan_id IS NULL;
    """)
    # 3. Set plan_id NOT NULL and add FK constraint
    cur.execute("""
        ALTER TABLE subscriptions ALTER COLUMN plan_id SET NOT NULL;
    """)
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_plan') THEN
                ALTER TABLE subscriptions ADD CONSTRAINT fk_plan FOREIGN KEY (plan_id) REFERENCES subscription_plans(id);
            END IF;
        END$$;
    """)
    # 4. Drop old columns
    cur.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='subscriptions' AND column_name='plan_type'
            ) THEN
                ALTER TABLE subscriptions DROP COLUMN plan_type;
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='subscriptions' AND column_name='amount'
            ) THEN
                ALTER TABLE subscriptions DROP COLUMN amount;
            END IF;
        END$$;
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete. 'plan_id' added, backfilled, and old columns dropped.")

if __name__ == "__main__":
    migrate()
