import re

def is_valid_email(email: str) -> bool:
    """
    Check if a given string is a valid email address.
    
    Args:
        email (str): The email string to validate
        
    Returns:
        bool: True if valid email, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return re.match(pattern, email) is not None
