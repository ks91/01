#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/fetch-robot-session.sh [options] <user@host|host>

Examples:
  ./scripts/fetch-robot-session.sh red@red-hexa.local
  ./scripts/fetch-robot-session.sh --user red red-hexa.local
  ./scripts/fetch-robot-session.sh --remote-root /home/red/01 red@red-hexa.local

Options:
  --user <name>          SSH user when host is given without user@.
  --remote-root <path>   Repository root on the robot. Default: /home/<user>/01
  --dest <path>          Local destination directory. Default: ./robot-sessions/<host>
  --no-logs              Do not fetch logs/.
  --no-notes             Do not fetch robot research note files.
  -h, --help             Show this help.

This script is meant to run on a MacBook or staff laptop. It pulls files from
the Raspberry Pi robot over SSH using rsync.
EOF
}

USER_NAME=""
REMOTE_ROOT=""
DEST_BASE="./robot-sessions"
FETCH_LOGS=1
FETCH_NOTES=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      USER_NAME="${2:?missing value for --user}"
      shift 2
      ;;
    --remote-root)
      REMOTE_ROOT="${2:?missing value for --remote-root}"
      shift 2
      ;;
    --dest)
      DEST_BASE="${2:?missing value for --dest}"
      shift 2
      ;;
    --no-logs)
      FETCH_LOGS=0
      shift
      ;;
    --no-notes)
      FETCH_NOTES=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -ne 1 ]]; then
  echo "Expected exactly one robot host." >&2
  usage >&2
  exit 2
fi

ROBOT="$1"
if [[ "$ROBOT" == *@* ]]; then
  SSH_TARGET="$ROBOT"
  USER_NAME="${ROBOT%@*}"
  HOST_NAME="${ROBOT#*@}"
else
  if [[ -z "$USER_NAME" ]]; then
    echo "When host is given without user@, --user is required." >&2
    exit 2
  fi
  SSH_TARGET="${USER_NAME}@${ROBOT}"
  HOST_NAME="$ROBOT"
fi

if [[ -z "$REMOTE_ROOT" ]]; then
  REMOTE_ROOT="/home/${USER_NAME}/01"
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required." >&2
  exit 127
fi

DEST="${DEST_BASE%/}/${HOST_NAME}"
mkdir -p "$DEST"

fetch_dir_if_exists() {
  local remote_dir="$1"
  local local_dir="$2"
  if ssh "$SSH_TARGET" "test -d '$remote_dir'"; then
    mkdir -p "$local_dir"
    rsync -av --delete "${SSH_TARGET}:${remote_dir%/}/" "${local_dir%/}/"
  else
    echo "skip: remote directory not found: $remote_dir"
  fi
}

fetch_file_if_exists() {
  local remote_file="$1"
  local local_dir="$2"
  if ssh "$SSH_TARGET" "test -f '$remote_file'"; then
    mkdir -p "$local_dir"
    rsync -av "${SSH_TARGET}:${remote_file}" "${local_dir%/}/"
  else
    echo "skip: remote file not found: $remote_file"
  fi
}

echo "robot: ${SSH_TARGET}"
echo "remote root: ${REMOTE_ROOT}"
echo "destination: ${DEST}"

if [[ "$FETCH_LOGS" -eq 1 ]]; then
  fetch_dir_if_exists "${REMOTE_ROOT}/logs" "${DEST}/logs"
fi

if [[ "$FETCH_NOTES" -eq 1 ]]; then
  fetch_file_if_exists "${REMOTE_ROOT}/robot-research-notes.md" "${DEST}"
  fetch_file_if_exists "${REMOTE_ROOT}/robot-session-summary.md" "${DEST}"
  fetch_file_if_exists "${REMOTE_ROOT}/robot-session-notes.md" "${DEST}"
fi

echo "done: ${DEST}"
