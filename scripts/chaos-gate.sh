#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export EXPERIMENT=gcp-unavailable
export RUN_ID=${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}
export FLOW_PATH=${FLOW_PATH:-/juegos/}
mkdir -p "evidence/$RUN_ID"
# Journal is kept even when the gate fails.
chaos run --journal-path "evidence/$RUN_ID/journal.json" chaos/gcp-unavailable.json || true
python3 - <<'PYGATE'
import json, os, pathlib, sys
p=pathlib.Path('evidence')/os.environ['RUN_ID']/'comparison.json'
j=p.parent/'journal.json'
result=json.loads(p.read_text()) if p.exists() else {}
journal=json.loads(j.read_text()) if j.exists() else {}
print(json.dumps(result,indent=2))
sys.exit(0 if result.get('gate') is True and journal.get('status')=='completed' and journal.get('steady_states',{}).get('after',{}).get('steady_state_met') is True else 1)
PYGATE
