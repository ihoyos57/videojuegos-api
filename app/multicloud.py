"""Live cross-cloud composition; faults affect only authenticated test requests."""
import asyncio
import hmac
import json
import os
import random
import re
import secrets
import time
import httpx
from starlette.responses import JSONResponse, Response

def authorized(request):
    token = os.getenv("CHAOS_TOKEN", "")
    try:
        until = float(request.headers.get("x-chaos-until", "0"))
    except ValueError:
        return False
    return (os.getenv("CHAOS_ENABLED") == "true" and len(token) >= 32
            and hmac.compare_digest(token.encode(), request.headers.get("x-chaos-token", "").encode())
            and time.time()*1000 < until <= time.time()*1000+300000)

def install(app):
    @app.middleware("http")
    async def composition(request, call_next):
        start = time.monotonic()
        parent = request.headers.get("traceparent", "")
        trace_id = parent.split('-')[1] if re.fullmatch(r'00-[a-f0-9]{32}-[a-f0-9]{16}-01', parent) else secrets.token_hex(16)
        span_id = secrets.token_hex(8)
        traceparent = f"00-{trace_id}-{span_id}-01"
        active = authorized(request)
        fault = request.headers.get("x-chaos-fault", "") if active else ""
        protected = not (active and request.headers.get("x-resilience-mode") == "baseline")
        response = await call_next(request)
        if request.method == 'GET' and response.status_code == 200 and re.fullmatch(r'/(?:api/v[23]/)?(juegos|jugadores|compras)(/\d+)?/?', request.url.path):
            body = b''.join([chunk async for chunk in response.body_iterator])
            local = json.loads(body)
            pet, reason = None, None
            dep_start = time.monotonic()
            try:
                url = os.getenv('PEER_API_URL', '').rstrip('/')
                if not url:
                    raise ValueError('peer_not_configured')
                headers = {'traceparent':traceparent}
                if fault == 'unavailable':
                    headers.update({'x-chaos-token':os.environ['CHAOS_TOKEN'],
                        'x-chaos-until':request.headers['x-chaos-until'], 'x-chaos-fault':'unavailable'})
                async def fetch():
                    async with httpx.AsyncClient(trust_env=False, timeout=0.8 if protected else 6.0) as client:
                        remote = await client.get(url+'/pets/raw', headers=headers)
                        remote.raise_for_status()
                        values = remote.json()
                        if not isinstance(values, list) or not values:
                            raise ValueError('peer_empty')
                        return random.choice(values)
                pet = await asyncio.wait_for(fetch(), timeout=0.8 if protected else 6.0)
            except Exception as exc:
                reason = 'timeout' if isinstance(exc, (TimeoutError,httpx.TimeoutException)) else type(exc).__name__
            print(json.dumps({'event':'dependency_span','cloud':'gcp','traceId':trace_id,
                'spanId':secrets.token_hex(8),'parentSpanId':span_id,'peer':'aws',
                'durationMs':(time.monotonic()-dep_start)*1000,'fault':fault,
                'mode':'protected' if protected else 'baseline','status':reason or 'ok'}), flush=True)
            response = JSONResponse({'data':local,'mascota':pet,
                'integration':{'status':'degraded' if reason else 'ok','reason':reason,'live':True},
                'traceId':trace_id},status_code=502 if reason and not protected else 200)
        response.headers['X-App-Version'] = os.getenv('APP_VERSION', '4.0.0')
        response.headers['X-Trace-Id'] = trace_id
        response.headers['traceparent'] = traceparent
        response.headers['Cache-Control'] = 'no-store'
        print(json.dumps({'event':'server_span','cloud':'gcp','traceId':trace_id,'spanId':span_id,
            'parentSpanId':parent.split('-')[2] if re.fullmatch(r'00-[a-f0-9]{32}-[a-f0-9]{16}-01',parent) else None,
            'path':request.url.path,'status':response.status_code,'durationMs':(time.monotonic()-start)*1000}),flush=True)
        return response
