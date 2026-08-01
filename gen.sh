#!/bin/bash
#chmod +x gen.sh
project_venv="$PWD/venv"
if [[ "${VIRTUAL_ENV:-}" != "$project_venv" ]]; then
    source "$project_venv/bin/activate"
fi

export PYTHONPYCACHEPREFIX=_temp

if [[ -z "${1:-}" ]]; then
    echo "Usage: ./gen.sh <site>"
    exit 1
fi

python3 ./tools/gen.py "$1"
