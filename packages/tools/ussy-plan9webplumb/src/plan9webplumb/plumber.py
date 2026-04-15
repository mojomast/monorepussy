"""Plumber WebSocket server for Plan9-WebPlumb.

The Plumber is the central WebSocket server that receives messages from
the browser extension, matches them against handler rules, and dispatches
to local handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

try:
    import websockets
    from websockets.server import serve as ws_serve
except ImportError:
    websockets = None  # type: ignore[assignment]
    ws_serve = None  # type: ignore[assignment]

from plan9webplumb.config import Config
from plan9webplumb.handlers import HandlerRegistry
from plan9webplumb.models import PlumbMessage

logger = logging.getLogger(__name__)


class PlumberStats:
    """Runtime statistics for the plumber server."""

    def __init__(self) -> None:
        self.start_time: Optional[str] = None
        self.messages_received: int = 0
        self.messages_dispatched: int = 0
        self.handlers_fired: int = 0
        self.errors: int = 0
        self.connected_clients: int = 0

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "messages_received": self.messages_received,
            "messages_dispatched": self.messages_dispatched,
            "handlers_fired": self.handlers_fired,
            "errors": self.errors,
            "connected_clients": self.connected_clients,
            "uptime_seconds": self._uptime(),
        }

    def _uptime(self) -> float:
        if not self.start_time:
            return 0.0
        start = datetime.fromisoformat(self.start_time)
        now = datetime.now(timezone.utc)
        return (now - start).total_seconds()


class Plumber:
    """The Plumber WebSocket server.

    Receives messages from browser extensions, matches against handler rules,
    and dispatches to local handlers.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self.config.load_server_config()
        self.registry = HandlerRegistry(self.config)
        self.stats = PlumberStats()
        self._server: Optional[object] = None
        self._running = False

    @property
    def host(self) -> str:
        return self.config.host

    @property
    def port(self) -> int:
        return self.config.port

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start the plumber WebSocket server."""
        if websockets is None:
            raise RuntimeError(
                "The 'websockets' package is required to run the plumber server. "
                "Install it with: pip install websockets"
            )

        self.registry.load()
        self.stats.start_time = datetime.now(timezone.utc).isoformat()
        self._running = True

        logger.info("Plumber starting on ws://%s:%d", self.host, self.port)

        async with ws_serve(  # type: ignore[misc]
            self._handle_connection,
            self.host,
            self.port,
        ):
            await asyncio.Future()  # Run forever until cancelled

    async def stop(self) -> None:
        """Stop the plumber server."""
        self._running = False
        logger.info("Plumber stopping")

    async def _handle_connection(self, websocket: object, path: str = "") -> None:
        """Handle a WebSocket connection from a browser extension."""
        self.stats.connected_clients += 1
        remote = getattr(websocket, "remote_address", "unknown")
        logger.info("Client connected: %s", remote)

        try:
            async for raw_message in websocket:  # type: ignore[union-attr]
                await self._process_message(raw_message, websocket)
        except Exception as exc:
            logger.error("Connection error: %s", exc)
            self.stats.errors += 1
        finally:
            self.stats.connected_clients -= 1
            logger.info("Client disconnected: %s", remote)

    async def _process_message(self, raw_message: object, websocket: object) -> None:
        """Process a single incoming message."""
        self.stats.messages_received += 1

        try:
            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode("utf-8")
            data = json.loads(raw_message)
            message = PlumbMessage.from_dict(data)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.error("Invalid message: %s", exc)
            self.stats.errors += 1
            await self._send_response(websocket, {
                "type": "error",
                "error": f"Invalid message format: {exc}",
            })
            return

        logger.info(
            "Received message: type=%s data=%r url=%r",
            message.msg_type.value, message.data[:100], message.url[:100] if message.url else "",
        )

        # Dispatch to handlers
        results = await self.registry.dispatch(message)
        self.stats.messages_dispatched += 1

        dispatched_count = len(results)
        self.stats.handlers_fired += dispatched_count

        # Send response back
        response = {
            "type": "dispatch_result",
            "message_id": message.id,
            "handlers_fired": dispatched_count,
            "results": [r.to_dict() for r in results],
        }
        await self._send_response(websocket, response)

    async def _send_response(self, websocket: object, data: dict) -> None:
        """Send a JSON response back through the WebSocket."""
        try:
            await websocket.send(json.dumps(data))  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("Failed to send response: %s", exc)

    def get_status(self) -> dict:
        """Get current plumber status."""
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "stats": self.stats.to_dict(),
            "handlers_loaded": len(self.registry.handlers),
            "rules_loaded": len(self.registry.rules),
        }


def run_server(config: Optional[Config] = None) -> None:
    """Run the plumber server (blocking)."""
    plumber = Plumber(config)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    try:
        asyncio.run(plumber.start())
    except KeyboardInterrupt:
        logger.info("Plumber stopped by user")
