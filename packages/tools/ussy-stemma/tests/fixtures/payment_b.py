def process_payment(order):
    validate_order(order)
    charge = calc(order)
    if charge > 0:
        apply_fees(charge)
        charge = adjust_for_region(charge)
    receipt = generate(charge)
    log.info(f"Processed: {receipt.id}")
    return Receipt(receipt)
