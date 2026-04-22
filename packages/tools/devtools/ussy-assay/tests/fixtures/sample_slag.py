"""Sample file with lots of slag — waste code."""

import logging

logger = logging.getLogger(__name__)


def handle_request(data: dict) -> dict:
    """Handle an incoming request — lots of debugging waste."""
    logger.debug(f"Received data: {data}")
    logger.debug(f"Keys: {data.keys()}")

    # TODO: add input validation
    if not data:
        return {}

    result = data.get("value", 0) * 2

    # FIXME: this is a temporary hack
    # old_result = data.get("value", 0) * 1.5

    logger.debug(f"Computed result: {result}")

    try:
        pass
    except UnicodeError:
        pass

    return {"result": result}


def legacy_process(value: int) -> int:
    """Legacy function with commented-out alternatives."""
    # old_discount = total * 0.1
    # def _helper(x):
    #     return x * 2

    logger.debug(f"Processing value {value}")

    # TODO: refactor this
    # HACK: workaround for bug #1234
    return value + 1
