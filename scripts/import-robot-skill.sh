#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
使い方:
  ./scripts/import-robot-skill.sh [-X] <owner/repo|github-url> <skill-name>

例:
  ./scripts/import-robot-skill.sh ks91/robot-skills red-ball-track
  ./scripts/import-robot-skill.sh -X https://github.com/ks91/robot-skills red-ball-track
EOF
}

AUTO=0
while getopts ":Xh" opt; do
  case "$opt" in
    X) AUTO=1 ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "エラー: 不明なオプション -$OPTARG" >&2
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND - 1))

if [ "$#" -ne 2 ]; then
  echo "エラー: 引数が足りません。" >&2
  usage
  exit 1
fi

REPO_INPUT="$1"
SKILL_NAME="$2"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
DEST_BASE="${ROOT_DIR}/software/skills"
DEST_PATH="${DEST_BASE}/${SKILL_NAME}"
CODEX_SKILLS_BASE="${CODEX_HOME:-$HOME/.codex}/skills"

if [ "${DEST_PATH#${ROOT_DIR}/software/skills/}" = "$DEST_PATH" ]; then
  echo "エラー: 保存先の安全チェックに失敗しました。" >&2
  exit 1
fi

if [ "${DEST_PATH#${CODEX_SKILLS_BASE}/}" != "$DEST_PATH" ]; then
  echo "エラー: Codexスキル領域には保存できません。" >&2
  exit 1
fi

if [ -e "$DEST_PATH" ]; then
  echo "エラー: すでに存在します: $DEST_PATH" >&2
  exit 1
fi

normalize_repo_url() {
  local input="$1"
  if [[ "$input" =~ ^https?://github\.com/.+/.+(\.git)?/?$ ]]; then
    echo "$input"
    return 0
  fi
  if [[ "$input" =~ ^[^/]+/[^/]+$ ]]; then
    echo "https://github.com/${input}.git"
    return 0
  fi
  return 1
}

if ! REPO_URL="$(normalize_repo_url "$REPO_INPUT")"; then
  echo "エラー: repo指定は owner/repo か GitHub URL を使ってね。" >&2
  exit 1
fi

if [ "$AUTO" -ne 1 ]; then
  echo "ロボット用スキルを取り込みます。"
  echo "保存先: $DEST_PATH"
  printf "このまま進める？ [Enterで進む / nで中止]: "
  read -r answer
  if [[ "$answer" =~ ^[Nn]$ ]]; then
    echo "中止しました。"
    exit 0
  fi
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

CLONE_DIR="${TMP_DIR}/repo"
git clone --depth 1 "$REPO_URL" "$CLONE_DIR" >/dev/null

SOURCE_PATH=""
if [ -d "${CLONE_DIR}/skills/${SKILL_NAME}" ]; then
  SOURCE_PATH="${CLONE_DIR}/skills/${SKILL_NAME}"
elif [ -d "${CLONE_DIR}/${SKILL_NAME}" ]; then
  SOURCE_PATH="${CLONE_DIR}/${SKILL_NAME}"
fi

if [ -z "$SOURCE_PATH" ]; then
  echo "エラー: スキルが見つかりませんでした: ${SKILL_NAME}" >&2
  echo "確認した場所: ${CLONE_DIR}/skills/${SKILL_NAME}, ${CLONE_DIR}/${SKILL_NAME}" >&2
  exit 1
fi

mkdir -p "$DEST_BASE"
cp -R "$SOURCE_PATH" "$DEST_PATH"

echo "インポート完了: $DEST_PATH"
