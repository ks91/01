#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOCKET_PATH="${HEXAPOD_RPC_SOCKET:-/tmp/hexapod-rpc.sock}"
LOGLM_HEXAPOD_DANGEROUS="${LOGLM_HEXAPOD_DANGEROUS:-1}"
STANDBY_PID_FILE="${HEXAPOD_STANDBY_PID_FILE:-/tmp/hexapod-standby.pid}"

if ! command -v loglm >/dev/null 2>&1; then
  echo "loglm command not found. Install loglm outside this repository first." >&2
  exit 127
fi

"${ROOT_DIR}/software/start-hexapod-rpc.sh" start

cleanup() {
  if [[ -f "${STANDBY_PID_FILE}" ]]; then
    local pid
    pid="$(cat "${STANDBY_PID_FILE}" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
    rm -f "${STANDBY_PID_FILE}"
  fi
}
trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"
export HEXAPOD_RPC_SOCKET="${SOCKET_PATH}"
export ACAMP_HEXAPOD_RESEARCH_ASSISTANT=1
"${ROOT_DIR}/software/hexapod-standby.py" >/tmp/hexapod-standby.log 2>&1 &
echo $! >"${STANDBY_PID_FILE}"
if [[ "${LOGLM_HEXAPOD_DANGEROUS}" == "0" ]]; then
  loglm "$@"
else
  loglm -X "$@"
fi
