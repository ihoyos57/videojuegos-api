#!/usr/bin/env python3
"""Compute strictly observed SLI from probe & alarm evidence, not synthetic defaults.
Both inputs are NDJSON. Alert rows MUST contain detectedAt UTC and traceId.
Probe rows MUST contain sentAt/receivedAt UTC, case, traceId, status.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path

def ts(s): return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def score(probes,alerts,positive_cases):
    positives=[p for p in probes if p['case'] in positive_cases]
    negatives=[p for p in probes if p['case'] not in positive_cases]
    detections=[];false_alerts=[];contained=[]
    for p in probes:
        matched=[a for a in alerts if a.get('traceId') and a.get('traceId')==p.get('traceId')]
        for a in matched:
            delta=max(0,ts(a['detectedAt'])-ts(p['sentAt']))
            if p in positives:detections.append({'case':p['case'],'mttdSeconds':delta})
            else:false_alerts.append({'case':p['case'],'delaySeconds':delta})
        if p in positives and p.get('status') in (401,403,404):
            contained.append(max(0,ts(p['receivedAt'])-ts(p['sentAt'])))
    observed=len({x['case'] for x in detections})
    return {'source':'ACTUAL_PROBE_AND_ALERT_EVENTS_ONLY',
        'numberPositiveCases':len(positives),'numberNegativeCases':len(negatives),
        'detectionCoverage':observed/len(positives) if positives else None,
        'falsePositiveRate':len(false_alerts)/len(negatives) if negatives else None,
        'mttdSeconds':sum(x['mttdSeconds'] for x in detections)/len(detections) if detections else None,
        'mttcSeconds':sum(contained)/len(contained) if contained else None,
        'positiveMatchedAlerts':detections,'falseAlarms':false_alerts,
        'warning':'MTTD null without independently timestamped alert data; do not substitute app log time.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--probes',required=True)
    p.add_argument('--alerts',required=True);p.add_argument('--positive-cases',required=True)
    p.add_argument('--out',required=True);args=p.parse_args()
    load=lambda p: [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
    result=score(load(args.probes),load(args.alerts),set(args.positive_cases.split(',')))
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
