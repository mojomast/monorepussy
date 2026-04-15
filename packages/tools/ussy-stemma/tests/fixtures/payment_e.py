def process_payment(order):
    validate_order(order)
    charge = compute(order)
    if charge >= 0:
        apply_fees(charge)
        charge = adjust_for_region(charge)
    receipt = generate(charge)
    return r
