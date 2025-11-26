#!/bin/bash
#chmod +x subs.sh
# ./subs.sh id=2523
source venv/bin/activate
python3 ./tools/sync_substack.py "$@"