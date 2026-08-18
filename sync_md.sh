#!/bin/bash
# Synchronise et nettoie le dépôt Markdown publié, indépendamment de gen.sh.

project_venv="$PWD/venv"
if [[ "${VIRTUAL_ENV:-}" != "$project_venv" ]]; then
    source "$project_venv/bin/activate"
fi

export PYTHONPYCACHEPREFIX=_temp

if [[ -z "${1:-}" ]]; then
    echo "Usage: ./sync_md.sh <site>"
    exit 1
fi

python3 ./tools/sync_md.py "$1"
