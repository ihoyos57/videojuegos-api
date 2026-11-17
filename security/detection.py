"""GCP heartbeat and decoy detection logic for Cloud Logging logs exported as NDJSON."""
import json
from datetime import datetime, timezone
from pathlib import Path

def honeytoken(event: dict) -> bool:
    return event.get('event')=='security_event' and event.get('action')=='honeytoken_touched' and event.get('outcome')=='alert'

def heartbeat_gap(events: list, *, evaluated_at: float, threshold_seconds: float=20.0) -> bool:
    observed=[]
    for event in events:
        if event.get('event')!='security_heartbeat':continue
        try: observed.append(datetime.fromisoformat(event['timestamp'].replace('Z','+00:00')).timestamp())
        except (ValueError,KeyError,TypeError):continue
    return bool(observed) and evaluated_at-max(observed)>threshold_seconds
    # A heartbeat must be observed first; absent-from-start needs separate startup alert.

def test_fixture(path):
    items=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    return bool(items) and all(honeytoken(row)==row['expectedAlert'] for row in items)
