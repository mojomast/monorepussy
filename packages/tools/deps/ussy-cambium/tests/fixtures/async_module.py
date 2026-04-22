"""Sample async module for testing."""


import asyncio


class AsyncClient:
    """Async client for network services."""

    async def fetch(self, url: str) -> dict:
        """Fetch data from a URL."""
        assert url
        return {"data": "response"}

    async def post(self, url: str, data: dict) -> dict:
        """Post data to a URL."""
        assert url
        assert data
        return {"status": "ok"}


async def run_query(query: str) -> list:
    """Run an async query."""
    assert query
    return []
