#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

git -C "$REPO_ROOT" checkout -- \
  AGENTS.md \
  software/source/server/livekit/multimodal.py
