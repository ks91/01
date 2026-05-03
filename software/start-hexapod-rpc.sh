#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOCKET_PATH="${HEXAPOD_RPC_SOCKET:-/tmp/hexapod-rpc.sock}"
LOG_FILE="${HEXAPOD_RPC_LOG:-${SCRIPT_DIR}/hexapod-rpc.log}"
SYSTEM_PYTHON="${HEXAPOD_SYSTEM_PYTHON:-/usr/bin/python3}"
PID_FILE="${HEXAPOD_RPC_PID_FILE:-${SOCKET_PATH}.pid}"
ACTION="start"

usage() {
  cat <<'EOF'
Usage: ./start-hexapod-rpc.sh [start|status|stop|restart]

Starts or manages the Freenove hexapod RPC bridge.

Environment:
  HEXAPOD_RPC_SOCKET       Socket path. Default: /tmp/hexapod-rpc.sock
  HEXAPOD_RPC_LOG          Log file. Default: ./hexapod-rpc.log
  HEXAPOD_SYSTEM_PYTHON    System Python with hardware libraries. Default: /usr/bin/python3
  HEXAPOD_RPC_PID_FILE     PID file. Default: ${HEXAPOD_RPC_SOCKET}.pid
EOF
}

if [[ $# -gt 0 ]]; then
  case "$1" in
    start|status|stop|restart)
      ACTION="$1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown action: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
fi

if [[ $# -gt 0 ]]; then
  echo "Unexpected arguments: $*" >&2
  usage >&2
  exit 2
fi

mkdir -p "$(dirname "${LOG_FILE}")"

rpc_simple_call() {
  local method="$1"
  "${SYSTEM_PYTHON}" - "$SOCKET_PATH" "$method" <<'PY'
import json
import socket
import sys

sock_path = sys.argv[1]
method = sys.argv[2]
payload = {"id": "start-hexapod-rpc", "method": method, "args": [], "kwargs": {}}
try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        sock.connect(sock_path)
        sock.sendall(json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n")
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
except OSError as exc:
    print(exc, file=sys.stderr)
    sys.exit(1)
if not data:
    sys.exit(1)
message = json.loads(data.decode("utf-8", errors="replace").split("\n", 1)[0])
if not message.get("ok", False):
    print(message.get("error", "RPC call failed"), file=sys.stderr)
    sys.exit(1)
if method == "status":
    result = message.get("result", {})
    print(
        f"Hexapod RPC bridge running on {result.get('socket')} "
        f"(connected={result.get('connected')})"
    )
PY
}

is_bridge_alive() {
  if [[ ! -S "${SOCKET_PATH}" ]]; then
    return 1
  fi
  "${SYSTEM_PYTHON}" - "$SOCKET_PATH" <<'PY'
import json
import socket
import sys

sock_path = sys.argv[1]
payload = {"id": "start-hexapod-rpc", "method": "ping", "args": [], "kwargs": {}}
try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        sock.connect(sock_path)
        sock.sendall(json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n")
        data = sock.recv(1024)
except OSError:
    sys.exit(1)
sys.exit(0 if data else 1)
PY
}

read_bridge_pid() {
  if [[ -f "${PID_FILE}" ]]; then
    tr -d '\n' <"${PID_FILE}"
  fi
}

bridge_pid_alive() {
  local pid
  pid="$(read_bridge_pid || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

wait_for_bridge() {
  local attempt=1
  while (( attempt <= 20 )); do
    if is_bridge_alive; then
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done
  return 1
}

start_bridge() {
  if is_bridge_alive; then
    echo "Hexapod RPC bridge already running at ${SOCKET_PATH}."
    return 0
  fi
  if [[ -S "${SOCKET_PATH}" ]]; then
    rm -f "${SOCKET_PATH}"
  fi
  echo "Starting hexapod RPC bridge via ${SYSTEM_PYTHON}..."
  (
    cd "${SCRIPT_DIR}"
    nohup "${SYSTEM_PYTHON}" -m hexapod.rpc_server \
      --socket "${SOCKET_PATH}" \
      --log "${LOG_FILE}" \
      --log-level "INFO" \
      --auto-connect >>"${LOG_FILE}" 2>&1 &
    echo $! >"${PID_FILE}"
  )
  if wait_for_bridge; then
    echo "Hexapod RPC bridge started at ${SOCKET_PATH}."
    return 0
  fi
  if bridge_pid_alive; then
    local pid
    pid="$(read_bridge_pid || true)"
    echo "Hexapod RPC bridge process ${pid} is running, but socket check failed. Check ${LOG_FILE}." >&2
    return 0
  fi
  echo "Failed to start hexapod RPC bridge. Check ${LOG_FILE}." >&2
  exit 1
}

stop_bridge() {
  if ! is_bridge_alive; then
    echo "Hexapod RPC bridge is not running."
    rm -f "${PID_FILE}"
    return 0
  fi
  rpc_simple_call shutdown
  rm -f "${PID_FILE}"
  echo "Hexapod RPC bridge shut down."
}

case "${ACTION}" in
  start)
    start_bridge
    ;;
  status)
    if is_bridge_alive; then
      rpc_simple_call status
    else
      echo "Hexapod RPC bridge is not running."
      exit 1
    fi
    ;;
  stop)
    stop_bridge
    ;;
  restart)
    stop_bridge
    start_bridge
    ;;
esac
