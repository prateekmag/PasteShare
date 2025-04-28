"""
Branch management utilities for PetrolPro
"""
import os
import json

def get_branch_data(branch_id=None):
    """
    Get information about a specific branch or all branches
    
    Args:
        branch_id (str, optional): The branch ID to get information for. If None, returns all branches.
        
    Returns:
        dict or list: Branch information
    """
    try:
        # Load branches from JSON file if it exists
        branches_file = 'data/branches.json'
        if os.path.exists(branches_file):
            with open(branches_file, 'r') as f:
                branches = json.load(f)
        else:
            # Default branches if file doesn't exist
            branches = [
                {
                    "id": "branch1",
                    "name": "Main Station",
                    "location": "Central Business District",
                    "status": "active"
                }
            ]
            # Create the file with default branches
            os.makedirs(os.path.dirname(branches_file), exist_ok=True)
            with open(branches_file, 'w') as f:
                json.dump(branches, f, indent=2)
    except Exception as e:
        print(f"Error loading branches: {e}")
        # Create an empty list instead of using fallback hardcoded branches
        branches = []
    
    if branch_id:
        for branch in branches:
            if branch["id"] == branch_id:
                return branch
        return None
    
    return branches


def get_branch_filter_param(branch_id):
    """
    Generate database filter parameters for a specific branch
    
    Args:
        branch_id (str): The branch ID to filter by
        
    Returns:
        dict: Filter parameters to add to database queries
    """
    if not branch_id or branch_id == "all":
        # Even when not filtering by a specific branch, only get data from valid branches
        branches = get_branch_data()
        if branches:
            valid_branch_ids = [branch['id'] for branch in branches]
            return {"branch_id_in": valid_branch_ids}
        return {}
    
    # Add specific branch filter
    return {"branch_id": branch_id}


def is_valid_branch(branch_id):
    """
    Check if a branch ID exists in the current list of branches
    
    Args:
        branch_id (str): Branch ID to check
        
    Returns:
        bool: True if branch exists, False otherwise
    """
    if not branch_id or branch_id == "all":
        return True
        
    branches = get_branch_data()
    for branch in branches:
        if branch['id'] == branch_id:
            return True
    return False


def add_branch_info_to_data(data, branch_id):
    """
    Add branch information to data objects
    
    Args:
        data (dict or list): The data to add branch info to
        branch_id (str): The branch ID
        
    Returns:
        dict or list: Data with branch info added
    """
    branch = get_branch_data(branch_id)
    
    if not branch:
        return data
    
    if isinstance(data, list):
        for item in data:
            item["branch"] = branch["name"]
            item["branch_id"] = branch["id"]
    elif isinstance(data, dict):
        data["branch"] = branch["name"]
        data["branch_id"] = branch["id"]
    
    return data


def get_branch_specific_limits(branch_id):
    """
    Get branch-specific operational limits and thresholds
    
    Args:
        branch_id (str): The branch ID
        
    Returns:
        dict: Branch-specific operational limits
    """
    # Default limits
    limits = {
        "low_fuel_threshold": 20,  # Percentage
        "critical_fuel_threshold": 10,  # Percentage
        "max_staff_per_shift": 3,
        "min_staff_per_shift": 1,
        "sales_target_daily": 1000,  # Dollar amount
        "sales_target_monthly": 30000,  # Dollar amount
        "inventory_refresh_days": 7  # Days
    }
    
    # Branch-specific overrides could be defined here
    branch_specific_limits = {
        "branch1": {
            "sales_target_daily": 1200,
            "sales_target_monthly": 40000
        },
        "branch2": {
            "sales_target_daily": 800,
            "sales_target_monthly": 25000
        },
        "branch3": {
            "sales_target_daily": 500,
            "sales_target_monthly": 15000
        }
    }
    
    if branch_id and branch_id in branch_specific_limits:
        limits.update(branch_specific_limits[branch_id])
    
    return limits