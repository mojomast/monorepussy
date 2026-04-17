# Test fixture: code with state aliasing issues


def modify_copies():
    """Modify a list copy — but what if copy is removed?"""
    original = [1, 2, 3]
    copy = original.copy()
    copy.append(4)
    return original


def shared_state():
    """Variables that might share state."""
    data = {"a": 1}
    backup = dict(data)
    data["b"] = 2
    return backup


def main():
    """Main entry point for probing."""
    return modify_copies()
