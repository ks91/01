#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$BASE_DIR/logs"
TODAY_LOCAL="$(date +%Y%m%d)"
LOG_FILE="$LOG_DIR/codex-log-${TODAY_LOCAL}.txt"

usage() {
  cat <<'EOF'
Usage: ./logdex.sh [options]

Options:
  --new
      Ignore saved contexts and always start with `codex --search`.
  --resume
      Open Codex's built-in session picker (`codex resume`).
  -h, --help
      Show this help.
EOF
}

is_running_under_script() {
  local pid ppid comm
  pid="$$"

  while :; do
    ppid="$(ps -o ppid= -p "$pid" | tr -d '[:space:]')"
    if [[ -z "$ppid" || "$ppid" == "0" ]]; then
      return 1
    fi

    comm="$(ps -o comm= -p "$ppid" | awk '{print $1}')"
    if [[ "$comm" == "script" ]]; then
      return 0
    fi

    pid="$ppid"
  done
}

mkdir -p "$LOG_DIR"

FORCE_NEW=0
CHOOSE_RESUME=0
while (($# > 0)); do
  case "$1" in
    --new)
      FORCE_NEW=1
      shift
      ;;
    --resume)
      CHOOSE_RESUME=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$FORCE_NEW" -eq 1 && "$CHOOSE_RESUME" -eq 1 ]]; then
  echo "Error: --new and --resume cannot be used together." >&2
  exit 2
fi

CODEX_CMD=(codex resume --last)
if [[ "$FORCE_NEW" -eq 1 ]]; then
  CODEX_CMD=(codex --search)
elif [[ "$CHOOSE_RESUME" -eq 1 ]]; then
  CODEX_CMD=(codex resume)
fi

if is_running_under_script; then
  exec "${CODEX_CMD[@]}"
fi

RUN_START_LOCAL="$(date '+%Y-%m-%d %H:%M:%S %z')"
{
  printf '\n===== logdex start: %s =====\n' "$RUN_START_LOCAL"
} >> "$LOG_FILE"

SCRIPT_OPTS=(-q -a)
SCRIPT_HELP="$(script -h 2>&1 || true)"

if printf '%s' "$SCRIPT_HELP" | grep -Eq -- '(^|[[:space:]])-F([,[:space:]]|$)'; then
  SCRIPT_OPTS+=(-F)
elif printf '%s' "$SCRIPT_HELP" | grep -Eq -- '(^|[[:space:]])-f([,[:space:]]|$)'; then
  SCRIPT_OPTS+=(-f)
fi

if printf '%s' "$SCRIPT_HELP" | grep -Eq -- '(^|[[:space:]])-c,|--command([[:space:]]|=)'; then
  CODEX_CMD_STRING="$(printf '%q ' "${CODEX_CMD[@]}")"
  CODEX_CMD_STRING="${CODEX_CMD_STRING% }"
  exec script "${SCRIPT_OPTS[@]}" "$LOG_FILE" -c "exec $CODEX_CMD_STRING"
else
  exec script "${SCRIPT_OPTS[@]}" "$LOG_FILE" "${CODEX_CMD[@]}"
fi
