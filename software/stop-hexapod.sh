#!/usr/bin/env bash
set -euo pipefail

SOCKET_PATH="${HEXAPOD_RPC_SOCKET:-/tmp/hexapod-rpc.sock}"
SYSTEM_PYTHON="${HEXAPOD_SYSTEM_PYTHON:-/usr/bin/python3}"
STANDBY_PID_FILE="${HEXAPOD_STANDBY_PID_FILE:-/tmp/hexapod-standby.pid}"

usage() {
  cat <<'EOF'
Usage: ./stop-hexapod.sh [--keep-servo-power]

Stops the hexapod through the RPC bridge.

Default behavior:
  - stop ball tracking
  - stop movement
  - disable balance
  - return body/head toward neutral
  - turn buzzer off
  - turn servo power off

Options:
  --keep-servo-power   Stop motion but leave servo power on.
EOF
}

KEEP_SERVO_POWER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-servo-power)
      KEEP_SERVO_POWER=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -S "${SOCKET_PATH}" ]]; then
  echo "Hexapod RPC socket not found: ${SOCKET_PATH}" >&2
  echo "Is the RPC bridge running? Try: ./run-hexapod.sh --rpc-status" >&2
  exit 1
fi

if [[ -f "${STANDBY_PID_FILE}" ]]; then
  standby_pid="$(cat "${STANDBY_PID_FILE}" 2>/dev/null || true)"
  if [[ -n "${standby_pid}" ]] && kill -0 "${standby_pid}" >/dev/null 2>&1; then
    kill "${standby_pid}" >/dev/null 2>&1 || true
  fi
  rm -f "${STANDBY_PID_FILE}"
fi

"${SYSTEM_PYTHON}" - "${SOCKET_PATH}" "${KEEP_SERVO_POWER}" <<'PY'
from __future__ import annotations

import json
import socket
import sys
import time

sock_path = sys.argv[1]
keep_servo_power = sys.argv[2] == "1"


def call(method, *args, **kwargs):
    payload = {
        "id": f"stop-hexapod-{method}",
        "method": method,
        "args": list(args),
        "kwargs": kwargs,
    }
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(2.5)
        sock.connect(sock_path)
        sock.sendall(json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n")
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    if not data:
        raise RuntimeError(f"No response for {method}")
    response = json.loads(data.decode("utf-8", errors="replace").split("\n", 1)[0])
    if not response.get("ok", False):
        raise RuntimeError(f"{method}: {response.get('error', 'RPC call failed')}")
    return response.get("result")


steps = [
    ("ball_stop", (), {}),
    ("stop", (), {}),
    ("balance", (False,), {}),
    ("attitude", (0, 0, 0), {}),
    ("position", (0, 0, 0), {}),
    ("head_horizontal", (90,), {}),
    ("head_vertical", (90,), {}),
    ("buzzer_off", (), {}),
]

if not keep_servo_power:
    steps.append(("servopower", (False,), {}))

failures = []
for method, args, kwargs in steps:
    try:
        call(method, *args, **kwargs)
        time.sleep(0.05)
    except Exception as exc:
        failures.append(f"{method}: {exc}")

if failures:
    print("Hexapod stop attempted, but some RPC calls failed:", file=sys.stderr)
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    sys.exit(1)

if keep_servo_power:
    print("Hexapod stopped. Servo power is still on.")
else:
    print("Hexapod stopped. Servo power is off.")
PY
