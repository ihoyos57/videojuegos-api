"""Chaos Toolkit extension. No persistent fault state. Results are never pre-filled."""
import json, os, pathlib, subprocess, time, urllib.request, urllib.error, uuid
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT/'evidence'/os.getenv('RUN_ID', time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()))
OUT.mkdir(parents=True,exist_ok=True)

def get(url):
    with urllib.request.urlopen(url,timeout=8) as r:
        return json.load(r)

def preflight():
    try:
        body=get(os.environ['BASE_URL'].rstrip('/')+os.environ['FLOW_PATH'])
        return body.get('integration',{}).get('status')=='ok' and body.get('data') is not None
    except Exception:
        return False

def rollback():
    # No global fault switch is changed; stopping the injector removes all fault headers.
    # Outstanding requests have a 6s server dependency budget. Verify after it expires.
    time.sleep(7)
    result=preflight()
    (OUT/'recovery.json').write_text(json.dumps({'time':time.time(),'healthy':result}))
    return result

def publish(round_name, points, active):
    target=os.getenv('PUSHGATEWAY_URL')
    if not target: return
    durations=[p[1] for p in points if p[0]=='flow_ms']
    errors=[p[1] for p in points if p[0]=='local_error']
    complete=[p[1] for p in points if p[0]=='integration_complete']
    p95=sorted(durations)[min(len(durations)-1,int(len(durations)*.95))] if durations else 0
    lines={'chaos_injection_active':int(active),'chaos_flow_p95_ms':p95,
        'chaos_local_error_ratio':sum(errors)/len(errors) if errors else 0,
        'chaos_complete_ratio':sum(complete)/len(complete) if complete else 0}
    data=''.join(f'{k} {v}\n' for k,v in lines.items()).encode()
    try:
        url=target.rstrip('/')+'/metrics/job/chaos/experiment/'+os.environ['EXPERIMENT']+'/round/'+round_name
        urllib.request.urlopen(urllib.request.Request(url,data=data,method='PUT'),timeout=2).close()
    except Exception:
        # Evidence files remain authoritative if optional monitoring is offline.
        pass

def run_load(name, fault, mode):
    env=os.environ.copy(); summary=OUT/(name+'.json'); stream=OUT/(name+'.ndjson')
    env.update(ROUND=name,FAULT=fault,MODE=mode,SUMMARY_FILE=str(summary))
    start=time.time(); points=[]; observed=[]; offset=0; aborted=None
    with (OUT/(name+'.log')).open('w') as log:
        process=subprocess.Popen(['k6','run','--out','json='+str(stream),str(ROOT/'load/profile.js')],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                time.sleep(1)
                if stream.exists():
                    with stream.open() as f:
                        f.seek(offset)
                        while True:
                            pos=f.tell(); line=f.readline()
                            if not line: break
                            try: item=json.loads(line)
                            except json.JSONDecodeError: f.seek(pos); break
                            if item.get('type')=='Point' and item.get('metric') in ['flow_ms','local_error','integration_complete']:
                                points.append((item['metric'],item['data']['value']))
                        offset=f.tell()
                publish(name,points,bool(fault))
                # Abort on independent no-fault control traffic. Expected baseline failure is not an abort.
                if int(time.time()-start)%5==0 and not preflight():
                    aborted='unaffected_control_flow_failed'; process.terminate(); break
                if time.time()-start>115:
                    aborted='maximum_duration_exceeded'; process.terminate(); break
            process.wait(timeout=12)
        finally:
            if process.poll() is None:
                process.kill(); process.wait()
            publish(name,points,False)
    meta={'start':start,'end':time.time(),'fault':fault,'mode':mode,'exitCode':process.returncode,'abort':aborted}
    (OUT/(name+'-window.json')).write_text(json.dumps(meta,indent=2))
    if aborted or process.returncode or not summary.exists():
        raise RuntimeError(f'{name}: aborted/failed; inspect {OUT}')
    raw=json.loads(summary.read_text())['metrics']
    return {'p95_ms':raw['flow_ms']['values']['p(95)'],
        'local_error':raw['local_error']['values']['rate'],
        'complete':raw['integration_complete']['values']['rate'],
        'requests':raw['http_reqs']['values']['count']}

def run_suite(fault):
    if os.getenv('CHAOS_WINDOW_ACK')!='yes':
        raise RuntimeError('Set CHAOS_WINDOW_ACK=yes only within the agreed window on group infrastructure')
    if len(os.getenv('CHAOS_TOKEN',''))<32: raise RuntimeError('Missing shared CHAOS_TOKEN')
    result={'experiment':os.environ['EXPERIMENT'],'fault':fault,'measured':{},'gate':False}
    try:
        # Prove rollback/no-fault control before first injection.
        if not rollback(): raise RuntimeError('Initial recovery/control check failed')
        result['measured']['steady']=run_load('steady','','protected')
        steady=result['measured']['steady']
        if steady['complete']<.99 or steady['local_error']>.01 or steady['p95_ms']>=1500:
            raise RuntimeError('Measured steady state outside proposed thresholds; diagnose before injecting')
        result['measured']['round0']=run_load('round0',fault,'baseline')
        if not rollback(): raise RuntimeError('Recovery after round0 failed')
        result['measured']['round1']=run_load('round1',fault,'protected')
        before=result['measured']['round0']; after=result['measured']['round1']
        key='p95_ms' if fault=='latency' else 'local_error'
        threshold=1500 if fault=='latency' else .01
        result.update(metric=key,threshold=threshold,before=before[key],after=after[key],
            variation_percent=(after[key]-before[key])/before[key]*100 if before[key] else None)
        result['hypothesis_refuted_round0']=before[key]>=threshold if key=='p95_ms' else before[key]>threshold
        after_passes = after[key] < threshold if key == 'p95_ms' else after[key] <= threshold
        result['gate']=result['hypothesis_refuted_round0'] and after_passes and after['local_error']<=.01
    except Exception as exc:
        result['error']=str(exc)
    finally:
        result['recovered']=rollback()
        result['gate']=bool(result['gate'] and result['recovered'])
        (OUT/'comparison.json').write_text(json.dumps(result,indent=2))
        subprocess.run(['python3',str(ROOT/'scripts/report-v4.py'),str(OUT)],check=False)
    return result['gate']

def gate_passed():
    p=OUT/'comparison.json'
    return p.exists() and json.loads(p.read_text()).get('gate') is True
