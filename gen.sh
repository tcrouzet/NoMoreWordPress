#!/bin/bash
#chmod +x gen.sh
source venv/bin/activate
export PYTHONPYCACHEPREFIX=_temp
python3 ./tools/gen.py