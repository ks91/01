"""Client helpers for talking to the system-Python hexapod RPC server."""
from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import dataclass
from typing import Any, Dict

_DEFAULT_SOCKET = "/tmp/hexapod-rpc.sock"


class HexapodRPCError(RuntimeError):
    """Raised when the RPC server reports an error."""


@dataclass
class _RPCResponse:
    ok: bool
    result: Any
    error: str | None = None


class HexapodRPCClient:
    """Simple JSON-over-UNIX-socket client for the hexapod bridge."""

    def __init__(self, socket_path: str | None = None, timeout: float = 30.0) -> None:
        self.socket_path = socket_path or os.environ.get("HEXAPOD_RPC_SOCKET", _DEFAULT_SOCKET)
        self.timeout = timeout

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        payload = {
            "id": str(uuid.uuid4()),
            "method": method,
            "args": list(args),
            "kwargs": kwargs,
        }
        response = self._request(payload)
        if not response.ok:
            raise HexapodRPCError(response.error or "RPC call failed")
        return response.result

    def ping(self) -> Any:
        """Return the server heartbeat payload."""
        return self.call("ping")

    def status(self) -> Any:
        """Return server health information."""
        return self.call("status")

    def _request(self, payload: Dict[str, Any]) -> _RPCResponse:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)
            sock.sendall(data)
            raw = self._readline(sock)
        if raw is None:
            return _RPCResponse(False, None, "No response from RPC server")
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            return _RPCResponse(False, None, f"Invalid JSON response: {exc}")
        return _RPCResponse(bool(message.get("ok")), message.get("result"), message.get("error"))

    def _readline(self, sock: socket.socket) -> str | None:
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        if not chunks:
            return None
        data = b"".join(chunks)
        line = data.split(b"\n", 1)[0]
        return line.decode("utf-8", errors="replace")


_default_client: HexapodRPCClient | None = None


def _get_default_client() -> HexapodRPCClient:
    global _default_client
    if _default_client is None:
        _default_client = HexapodRPCClient()
    return _default_client


def hexapod_call(method: str, *args: Any, **kwargs: Any) -> Any:
    """Send a single RPC call using a process-wide client instance."""
    client = _get_default_client()
    return client.call(method, *args, **kwargs)
