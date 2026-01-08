#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOCKET_PATH="${HEXAPOD_RPC_SOCKET:-/tmp/hexapod-rpc.sock}"
LOG_FILE="${HEXAPOD_RPC_LOG:-${SCRIPT_DIR}/hexapod-rpc.log}"
SYSTEM_PYTHON="${HEXAPOD_SYSTEM_PYTHON:-/usr/bin/python3}"
POETRY_ARGS=("01" "--server" "livekit" "--qr" "--multimodal")
if [[ $# -gt 0 ]]; then
  POETRY_ARGS=("01" "$@")
fi

BRIDGE_PID=""
cleanup() {
  if [[ -n "${BRIDGE_PID}" ]]; then
    if kill -0 "${BRIDGE_PID}" >/dev/null 2>&1; then
      kill "${BRIDGE_PID}" >/dev/null 2>&1 || true
      wait "${BRIDGE_PID}" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT

start_bridge() {
  if [[ -S "${SOCKET_PATH}" ]]; then
    rm -f "${SOCKET_PATH}"
  fi
  echo "Starting hexapod RPC bridge via ${SYSTEM_PYTHON}..."
  (cd "${SCRIPT_DIR}" && \
    "${SYSTEM_PYTHON}" -m hexapod.rpc_server \
      --socket "${SOCKET_PATH}" \
      --log "${LOG_FILE}" \
      --log-level "INFO" \
      --auto-connect) &
  BRIDGE_PID=$!
  sleep 2
}

start_bridge

cd "${SCRIPT_DIR}"
export HEXAPOD_RPC_SOCKET="${SOCKET_PATH}"
poetry run "${POETRY_ARGS[@]}"
