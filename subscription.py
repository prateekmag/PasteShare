import os
import json
from datetime import datetime, timedelta
from db import get_latest_subscription, get_subscription_types

# Subscription pricing (could be loaded from config/db in future)
SUBSCRIPTION_PRICING = {
    'monthly': 999,  # INR or USD as per your context
    'yearly': 9999
}

def get_subscription_amount(plan_type):
    """Get the amount for a given plan type from the DB subscription_plans table."""
    types = get_subscription_types()
    for t in types:
        if t['plan_type'] == plan_type:
            return float(t['amount'])
    return 0

def get_subscription_data():
    """Load all branch subscriptions from the JSON file."""
    subscriptions_file = 'data/subscriptions.json'
    if os.path.exists(subscriptions_file):
        with open(subscriptions_file, 'r') as f:
            return json.load(f)
    else:
        return []

def save_subscription_data(subscriptions):
    """Save all branch subscriptions to the JSON file."""
    subscriptions_file = 'data/subscriptions.json'
    os.makedirs(os.path.dirname(subscriptions_file), exist_ok=True)
    with open(subscriptions_file, 'w') as f:
        json.dump(subscriptions, f, indent=2, default=str)

def set_branch_subscription(branch_id, plan_type, start_date=None):
    """
    Add or update a subscription for a branch.
    plan_type: 'monthly' or 'yearly'
    start_date: ISO string or None (defaults to today)
    """
    if plan_type not in ['monthly', 'yearly']:
        raise ValueError('plan_type must be "monthly" or "yearly"')
    if not start_date:
        start_date = datetime.now().date().isoformat()
    else:
        start_date = str(start_date)
    if plan_type == 'monthly':
        end_date = (datetime.fromisoformat(start_date) + timedelta(days=30)).date().isoformat()
    else:
        end_date = (datetime.fromisoformat(start_date) + timedelta(days=365)).date().isoformat()
    subscriptions = get_subscription_data()
    # Remove existing subscription for this branch
    subscriptions = [s for s in subscriptions if s['branch_id'] != branch_id]
    subscriptions.append({
        'branch_id': branch_id,
        'plan_type': plan_type,
        'start_date': start_date,
        'end_date': end_date
    })
    save_subscription_data(subscriptions)
    return True

def get_branch_subscription(branch_id):
    """Get the latest subscription for a branch from the DB (with plan info)."""
    return get_latest_subscription(branch_id)

def is_branch_subscription_active(branch_id):
    """Check if a branch has an active subscription."""
    sub = get_branch_subscription(branch_id)
    if not sub:
        return False
    today = datetime.now().date()
    # Ensure start_date and end_date are date objects
    start = sub['start_date']
    end = sub['end_date']
    if isinstance(start, str):
        start = datetime.fromisoformat(start).date()
    if isinstance(end, str):
        end = datetime.fromisoformat(end).date()
    return start <= today <= end
