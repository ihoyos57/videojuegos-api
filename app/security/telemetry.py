"""Structured security telemetry and heartbeat for independent log-based watchdogs.
The watchdog must run OUTSIDE this process; this module cannot detect its own death.
"""
import asyncio
from datetime import datetime, timezone
import json
import os

def emit(event: str, **fields):
    print(json.dumps({'event': event, 'cloud': 'gcp',
                      'timestamp': datetime.now(timezone.utc).isoformat(),
                      **fields}, ensure_ascii=False, separators=(',', ':')), flush=True)

async def heartbeat_loop():
    while True:
        if os.getenv('SECURITY_HEARTBEAT_ENABLED', 'false').lower() == 'true' and \
           os.getenv('SECURITY_HEARTBEAT_PAUSED', 'false').lower() != 'true':
            emit('security_heartbeat', service='videojuegos-api', signal='log_export',
                 pod=os.getenv('HOSTNAME', 'local'))
        await asyncio.sleep(5)
