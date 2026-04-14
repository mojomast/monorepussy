"""Sample main entry point for testing."""


def greet(name: str = "World") -> str:
    """Return a greeting string."""
    return f"Hello, {name}!"


def main() -> None:
    """Main entry point."""
    print(greet())


if __name__ == "__main__":
    main()
