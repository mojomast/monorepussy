"""Sample file with high business logic content."""

from decimal import Decimal


def calc_tax(subtotal: Decimal, rate: Decimal, region: str = "US") -> Decimal:
    """Calculate tax amount based on subtotal and rate."""
    tax = subtotal * rate
    if region == "EU":
        tax = tax * Decimal("1.02")  # EU rounding adjustment
    return tax


def apply_discount(price: Decimal, discount_pct: Decimal) -> Decimal:
    """Apply a percentage discount to a price."""
    discount_amount = price * (discount_pct / 100)
    return price - discount_amount


def compute_fees(base: Decimal, quantity: int) -> Decimal:
    """Compute total fees with volume discount."""
    unit_fee = base
    if quantity > 100:
        unit_fee = base * Decimal("0.9")
    elif quantity > 50:
        unit_fee = base * Decimal("0.95")
    return unit_fee * quantity
