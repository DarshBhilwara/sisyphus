#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == hardware ]]; then
  exec bash "$ROOT/scripts/hardware.sh"
fi
ENV_FILE="${SETUP_ENV_FILE:-$ROOT/setup.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Copy setup.env.example to setup.env and edit it." >&2
  exit 2
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
exec python3 "$ROOT/scripts/setup.py" "${1:-render}"
