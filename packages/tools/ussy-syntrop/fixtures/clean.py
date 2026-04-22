# Test fixture: clean code with no behavioral assumptions
# Used for negative test cases


def add(a, b):
    """Pure function with no assumptions."""
    return a + b


def main():
    """Main entry point for probing."""
    return add(2, 3)
