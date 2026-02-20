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
  -y, --full-auto
      Start Codex with `--full-auto` (on-request approvals + workspace-write sandbox).
  -X, --dangerous
      Start Codex with `--dangerously-bypass-approvals-and-sandbox` (no approvals, no sandbox).
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
FULL_AUTO=0
DANGEROUS_MODE=0
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
    -y|--full-auto)
      FULL_AUTO=1
      shift
      ;;
    -X|--dangerous)
      DANGEROUS_MODE=1
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

if [[ "$FULL_AUTO" -eq 1 && "$DANGEROUS_MODE" -eq 1 ]]; then
  echo "Error: --full-auto and --dangerous cannot be used together." >&2
  exit 2
fi

CODEX_BASE_CMD=(codex)
if [[ "$DANGEROUS_MODE" -eq 1 ]]; then
  CODEX_BASE_CMD+=(--dangerously-bypass-approvals-and-sandbox)
elif [[ "$FULL_AUTO" -eq 1 ]]; then
  CODEX_BASE_CMD+=(--full-auto)
fi

CODEX_CMD=("${CODEX_BASE_CMD[@]}" resume --last)
if [[ "$FORCE_NEW" -eq 1 ]]; then
  CODEX_CMD=("${CODEX_BASE_CMD[@]}" --search)
elif [[ "$CHOOSE_RESUME" -eq 1 ]]; then
  CODEX_CMD=("${CODEX_BASE_CMD[@]}" resume)
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
