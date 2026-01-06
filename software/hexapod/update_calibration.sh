#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SOURCE_FILE="${REPO_ROOT}/../Freenove_Hexapod/Code/Server/point.txt"
DEST_FILE="${SCRIPT_DIR}/point.txt"

if [[ ! -f "${SOURCE_FILE}" ]]; then
  echo "Source calibration file not found: ${SOURCE_FILE}" >&2
  exit 1
fi

cp "${SOURCE_FILE}" "${DEST_FILE}"

echo "Updated calibration: ${DEST_FILE}"
