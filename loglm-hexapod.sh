#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOCKET_PATH="${HEXAPOD_RPC_SOCKET:-/tmp/hexapod-rpc.sock}"
LOGLM_HEXAPOD_DANGEROUS="${LOGLM_HEXAPOD_DANGEROUS:-1}"

if ! command -v loglm >/dev/null 2>&1; then
  echo "loglm command not found. Install loglm outside this repository first." >&2
  exit 127
fi

"${ROOT_DIR}/software/start-hexapod-rpc.sh" start

cd "${ROOT_DIR}"
export HEXAPOD_RPC_SOCKET="${SOCKET_PATH}"
export ACAMP_HEXAPOD_RESEARCH_ASSISTANT=1
if [[ "${LOGLM_HEXAPOD_DANGEROUS}" == "0" ]]; then
  exec loglm "$@"
fi
exec loglm -X "$@"
