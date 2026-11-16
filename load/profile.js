import http from 'k6/http';
import {sleep} from 'k6';
import {Rate, Trend} from 'k6/metrics';
const localError = new Rate('local_error');
const complete = new Rate('integration_complete');
const e2e = new Trend('flow_ms', true);
export const options = {
  stages:[{duration:'15s',target:5},{duration:'60s',target:5},{duration:'15s',target:0}],
  gracefulRampDown:'8s', gracefulStop:'8s',
  tags:{round:__ENV.ROUND,experiment:__ENV.EXPERIMENT},
  thresholds: __ENV.MODE==='baseline' ? {} : {local_error:[{threshold:'rate<0.50',abortOnFail:true,delayAbortEval:'10s'}]},
};
export default function () {
  const headers = {};
  if (__ENV.FAULT) {
    headers['X-Chaos-Token']=__ENV.CHAOS_TOKEN;
    headers['X-Chaos-Until']=String(Date.now()+15000);
    headers['X-Chaos-Fault']=__ENV.FAULT;
    headers['X-Resilience-Mode']=__ENV.MODE;
  }
  // 32 hex digits with per-request entropy; propagated by both APIs.
  const trace=Array.from({length:32},()=>Math.floor(Math.random()*16).toString(16)).join('');
  headers.traceparent='00-'+trace+'-1234567890abcdef-01';
  const res=http.get(__ENV.BASE_URL.replace(/\/$/,'')+__ENV.FLOW_PATH,{headers,timeout:'8s'});
  let body={}; try {body=res.json();} catch (_) {}
  localError.add(!(res.status===200 && body.data!==undefined));
  complete.add(res.status===200 && body.integration && body.integration.status==='ok');
  e2e.add(res.timings.duration);
  // Samples of IDs only; never log credentials or request headers.
  if (__ITER===0) console.log(JSON.stringify({traceId:body.traceId,round:__ENV.ROUND,status:res.status}));
  sleep(0.2);
}
export function handleSummary(data) {
  return {[__ENV.SUMMARY_FILE]:JSON.stringify(data,null,2)};
}
