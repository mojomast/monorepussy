# Test fixture: code with iteration-order dependencies


def process_items(items):
    """Process items assuming deterministic iteration order."""
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result


def collect_keys(data):
    """Collect keys from a dict assuming order."""
    keys = []
    for key in data.keys():
        keys.append(key)
    return keys


def main():
    """Main entry point for probing."""
    items = [1, -2, 3, -4, 5]
    return process_items(items)
