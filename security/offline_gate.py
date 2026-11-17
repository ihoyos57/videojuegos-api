#!/usr/bin/env python3
"""Unit-level rule fixture gate; does not claim live GCP security MTTD."""
import argparse
import json
from pathlib import Path
from datetime import datetime,timezone
from detection import test_fixture,heartbeat_gap
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
ok=test_fixture(Path(__file__).parent/'fixtures/telemetry-positive-negative.jsonl')
record={'source':'OFFLINE_DETECTION_FIXTURES','experiment':'telemetry',
    'timestamp':datetime.now(timezone.utc).isoformat(),
    'positiveAndNegativeCasesPassed':ok,'cloudExperimentExecuted':False,
    'mttdSeconds':None,'mttcSeconds':None,'cloudDetectionCoverage':None,
    'warning':'Unit tests are not a live Cloud Monitoring incident measurement.'}
out=Path(a.out);out.parent.mkdir(exist_ok=True,parents=True);out.write_text(json.dumps(record,indent=2)+'\n')
if not ok:raise SystemExit(1)
