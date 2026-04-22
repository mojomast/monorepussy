# Test fixture: code with evaluation-order dependencies


def side_effect_counter():
    """Count calls to demonstrate evaluation order."""
    counter = [0]

    def inc(x):
        counter[0] += 1
        return x

    result = inc(1) + inc(2) + inc(3)
    return counter[0]


def multi_arg_func(a, b, c):
    """Function with multiple args that may depend on eval order."""
    return a + b + c


def main():
    """Main entry point for probing."""
    return side_effect_counter()
