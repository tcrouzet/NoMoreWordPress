#!/bin/bash
#chmod +x subs.sh
# ./subs.sh id=2523
# ./subs.sh path=1999/02/fevrier-1999.md
source venv/bin/activate
python3 ./tools/sync_substack.py "$@"