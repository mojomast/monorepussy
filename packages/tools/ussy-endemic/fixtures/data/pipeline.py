# Data pipeline module - bare except is inappropriate here
# (errors should be surfaced, not swallowed)


def transform_data(raw_data):
    try:
        result = raw_data.parse()
    except:
        pass  # DANGEROUS: silently swallows data errors
    return result


def validate_record(record):
    try:
        assert record["id"] > 0
    except:
        pass  # Should raise ValidationError instead
