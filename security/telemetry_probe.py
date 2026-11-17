#!/usr/bin/env python3
"""Probe own GCP decoy path only; never disables cluster logging or probes other paths."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from secrets import token_hex

def iso(): return datetime.now(timezone.utc).isoformat()
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True)
    p.add_argument('--honeytoken-path',required=True,help='Must equal deployed SECURITY_HONEYTOKEN_PATH')
    p.add_argument('--out',required=True)
    p.add_argument('--allow-owned-target',action='store_true')
    args=p.parse_args()
    u=urlsplit(args.url)
    if not args.allow_owned_target: p.error('acknowledge authorized owned service')
    if u.scheme!='https' and u.hostname not in ('localhost','127.0.0.1'):p.error('remote endpoint must use HTTPS')
    if not args.honeytoken_path.startswith('/.well-known/') or '?' in args.honeytoken_path:
        p.error('decoy path must be /.well-known/... and must not have a query')
    trace=token_hex(16)
    url=args.url.rstrip('/')+args.honeytoken_path
    started=iso()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'X-Trace-Id':trace}),timeout=10) as response:
            status=response.status
            response.read(3000)
    except urllib.error.HTTPError as error:
        status=error.code
        error.read(3000)
    record={'experiment':'telemetry','case':'positive_honeytoken','sentAt':started,
            'receivedAt':iso(),'traceId':trace,'status':status,'expectedStatus':404,
            'pass':status==404,'source':'remote_http'}
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(record,ensure_ascii=False)+'\n',encoding='utf-8')
    print('HTTP',status,'traceId',trace,'evidence:',dest)
    if status!=404:raise SystemExit('honeytoken endpoint expected 404; check deployed env configuration')
    print('HTTP probe done; collect GKE log event security_event with matching traceId for positive proof')
if __name__=='__main__': main()
