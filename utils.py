import json
import random
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

class TestCasesSampler:
    """
    A class to sample test cases from a list of test cases.
    """
    def __init__(self, test_cases_json: str, sample_size_per_test: int):
        with open(test_cases_json, 'r', encoding = "utf-8") as file:
            self.test_cases = json.load(file)
        self.sample_size_per_test = sample_size_per_test

        self.total_test_types = len(self.test_cases.keys())

        self.total_test_pairs = sum(len(cases) for cases in self.test_cases.values())

    def sample_test_cases(self):
        """
        Sample test cases from the loaded test cases.
        
        Returns:
            dict: A dictionary with sampled test cases
        """
        sampled_cases = []
        
        for _, system_pairs in self.test_cases.items():
            for cases in system_pairs:
                if len(cases) <= self.sample_size_per_test:
                    sampled_cases.extend(cases)
                else:
                    sampled_cases.extend(random.sample(cases, self.sample_size_per_test))
        
        return sampled_cases
