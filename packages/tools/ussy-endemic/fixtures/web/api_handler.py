# Web API module - bare except is somewhat appropriate here
import logging

logger = logging.getLogger(__name__)


def handle_request(request):
    try:
        data = request.json()
    except:
        logger.warning("Invalid request body")
        data = {}
    return data


def process_api_call(endpoint: str) -> dict:
    # Missing return type hint was here but fixed
    return {"status": "ok"}
