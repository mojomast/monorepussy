# Test fixture: code with timing/atomicity assumptions


def accumulate():
    """Accumulate values — assumes atomic read-modify-write."""
    total = 0
    for i in range(100):
        total += i
    return total


def main():
    """Main entry point for probing."""
    return accumulate()
