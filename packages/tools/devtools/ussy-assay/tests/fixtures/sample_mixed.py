"""Sample file with heavily mixed concerns — low grade ore."""

import logging

logger = logging.getLogger(__name__)


def process_order(order_id: int, user: dict, items: list) -> dict:
    """Process a customer order with validation, logging, and error handling."""
    # Validate inputs
    if not order_id:
        raise ValueError("Order ID is required")
    if not user:
        raise ValueError("User is required")
    if not isinstance(items, list):
        raise TypeError("Items must be a list")

    logger.debug(f"Processing order {order_id}")

    # Compute total
    total = 0
    for item in items:
        total += item.get("price", 0) * item.get("quantity", 1)

    # Apply regional tax
    region = user.get("region", "US")
    if region == "EU":
        tax_rate = 0.21
    elif region == "UK":
        tax_rate = 0.20
    else:
        tax_rate = 0.07

    tax = total * tax_rate

    # Save to database
    try:
        db.session.add({"order_id": order_id, "total": total, "tax": tax})
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to save order {order_id}: {e}")
        raise

    logger.info(f"Order {order_id} processed: total={total}, tax={tax}")

    # TODO: handle expired tokens
    # HACK: bypass for admin users

    return {"order_id": order_id, "total": total, "tax": tax, "region": region}
