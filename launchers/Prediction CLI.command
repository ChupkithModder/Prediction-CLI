#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Prediction CLI needs Python 3.10+ from https://www.python.org/downloads/'
  printf '%s' 'Press Return to close: '
  read answer
  exit 1
fi
exec python3 "$HERE/prediction-cli.pyz" "$@"
