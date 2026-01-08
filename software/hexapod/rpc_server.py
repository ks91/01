"""UNIX-socket RPC bridge exposing HexapodDevice to external processes."""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socketserver
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Dict

from .hexapod import HexapodDevice

_DEFAULT_SOCKET = "/tmp/hexapod-rpc.sock"


class HexapodRPCRequestHandler(socketserver.StreamRequestHandler):
    """Handles newline-delimited JSON RPC calls from clients."""

    server: "HexapodRPCServer"

    def handle(self) -> None:
        while True:
            raw = self.rfile.readline()
            if not raw:
                break
            raw = raw.strip()
            if not raw:
                continue
            try:
                message = json.loads(raw)
            except json.JSONDecodeError as exc:
                self.server.logger.warning("Invalid JSON payload: %s", exc)
                self._send(self.server.error_response(None, f"Invalid JSON: {exc}"))
                continue
            response = self.server.dispatch(message)
            self._send(response)

    def _send(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        self.wfile.write(data)
        self.wfile.flush()


class HexapodRPCServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    """Threaded UNIX-socket server that proxies method calls to HexapodDevice."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, socket_path: str, *, chmod: int | None = None, logger: logging.Logger | None = None) -> None:
        self.socket_path = Path(socket_path)
        if self.socket_path.exists():
            self.socket_path.unlink()
        self.logger = logger or logging.getLogger("hexapod.rpc")
        self.device = HexapodDevice()
        self.lock = threading.RLock()
        super().__init__(str(self.socket_path), HexapodRPCRequestHandler)
        if chmod is not None:
            os.chmod(self.socket_path, chmod)

    def dispatch(self, message: Dict[str, Any]) -> Dict[str, Any]:
        req_id = message.get("id")
        method = message.get("method")
        args = message.get("args", [])
        kwargs = message.get("kwargs", {})
        if method is None:
            return self.error_response(req_id, "Missing 'method'")
        if not isinstance(args, list):
            return self.error_response(req_id, "'args' must be a list")
        if not isinstance(kwargs, dict):
            return self.error_response(req_id, "'kwargs' must be a dict")

        if method == "ping":
            return self.ok_response(req_id, {"pong": time.time()})
        if method == "status":
            return self.ok_response(
                req_id,
                {
                    "connected": bool(getattr(self.device, "connected", False)),
                    "socket": str(self.socket_path),
                },
            )
        if method == "shutdown":
            threading.Thread(target=self._shutdown_after_response, daemon=True).start()
            return self.ok_response(req_id, "shutting down")

        func = getattr(self.device, method, None)
        if func is None or not callable(func):
            return self.error_response(req_id, f"Unknown method: {method}")

        try:
            with self.lock:
                result = func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - hardware specific
            self.logger.exception("Error while executing %s", method)
            return self.error_response(req_id, f"{type(exc).__name__}: {exc}")

        return self.ok_response(req_id, _serialize(result))

    def _shutdown_after_response(self) -> None:
        time.sleep(0.1)
        self.shutdown()

    def server_close(self) -> None:
        try:
            with self.lock:
                try:
                    self.device.ball_stop()
                except Exception:  # pragma: no cover - best effort cleanup
                    pass
                try:
                    self.device.disconnect()
                except Exception:
                    pass
        finally:
            super().server_close()
            if self.socket_path.exists():
                self.socket_path.unlink()

    def ok_response(self, req_id: Any, result: Any) -> Dict[str, Any]:
        return {"id": req_id, "ok": True, "result": result}

    def error_response(self, req_id: Any, message: str) -> Dict[str, Any]:
        return {"id": req_id, "ok": False, "error": message}


def _serialize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Mapping):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialize(item) for item in value]
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            pass
    return repr(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hexapod UNIX socket RPC bridge")
    parser.add_argument("--socket", default=_DEFAULT_SOCKET, help="UNIX domain socket path")
    parser.add_argument(
        "--chmod",
        type=lambda val: int(val, 8),
        default=None,
        help="Optional chmod value (octal) applied to the socket file",
    )
    parser.add_argument(
        "--auto-connect",
        action="store_true",
        help="Automatically call hexapod.connect() once the server starts",
    )
    parser.add_argument(
        "--log",
        default=None,
        help="Optional log file path. Defaults to stderr when omitted",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    return parser.parse_args()


def configure_logging(log_file: str | None, level: str) -> None:
    logging_args: Dict[str, Any] = {
        "level": getattr(logging, level.upper(), logging.INFO),
        "format": "%(asctime)s [%(levelname)s] %(message)s",
    }
    if log_file:
        logging_args["filename"] = log_file
    logging.basicConfig(**logging_args)


def install_signal_handlers(server: HexapodRPCServer) -> None:
    def handle(signum, _frame):  # pragma: no cover - signal handling
        server.logger.info("Received signal %s, shutting down", signum)
        server.shutdown()

    signal.signal(signal.SIGTERM, handle)
    signal.signal(signal.SIGINT, handle)


def main() -> None:
    args = parse_args()
    configure_logging(args.log, args.log_level)
    server = HexapodRPCServer(args.socket, chmod=args.chmod)
    install_signal_handlers(server)
    if args.auto_connect:
        try:
            server.device.connect()
        except Exception as exc:  # pragma: no cover - hardware specific
            server.logger.error("Auto-connect failed: %s", exc)
    server.logger.info("Hexapod RPC server listening on %s", args.socket)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
