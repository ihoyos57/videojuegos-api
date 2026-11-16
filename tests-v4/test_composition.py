import os, tempfile, threading, json, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
os.environ['CHAOS_ENABLED']='true'
os.environ['CHAOS_TOKEN']='t'*40
from fastapi.testclient import TestClient
from app.main import app
class Peer(BaseHTTPRequestHandler):
    calls=0
    value='Mascota 1'
    def do_GET(self):
        Peer.calls+=1
        self.send_response(503 if self.headers.get('x-chaos-fault')=='unavailable' else 200)
        self.send_header('Content-Type','application/json'); self.end_headers()
        self.wfile.write(json.dumps([{'id':1,'nombre':Peer.value}]).encode())
    def log_message(self,*args):pass

def test_live_and_resilience():
    peer=ThreadingHTTPServer(('127.0.0.1',0),Peer)
    thread=threading.Thread(target=peer.serve_forever,daemon=True);thread.start()
    os.environ['PEER_API_URL']=f'http://127.0.0.1:{peer.server_port}'
    try:
        with TestClient(app) as c:
            game=c.post('/juegos/',json={'nombre':'Juego sintético','genero':'Arcade','plataforma':'PC','precio':1,'stock':4})
            assert game.status_code==200
            id=game.json()['id']
            for path in ['/juegos/',f'/juegos/{id}','/jugadores/','/compras/','/api/v3/juegos/']:
                r=c.get(path);assert r.status_code==200
                assert r.json()['mascota']['id']==1
                assert r.headers['x-trace-id']==r.json()['traceId']
            Peer.value='Cambio en tiempo real';assert c.get('/juegos/').json()['mascota']['nombre']==Peer.value
            n=Peer.calls;assert isinstance(c.get('/juegos/raw').json(),list);assert Peer.calls==n
            assert c.get('/juegos/999999').status_code==404
            h={'x-chaos-token':os.environ['CHAOS_TOKEN'],'x-chaos-until':str(time.time()*1000+15000),'x-chaos-fault':'unavailable'}
            r=c.get('/juegos/',headers=h);assert r.status_code==200;assert r.json()['mascota'] is None;assert r.json()['integration']['status']=='degraded'
            h['x-resilience-mode']='baseline';assert c.get('/juegos/',headers=h).status_code==502
            h['x-chaos-token']='wrong';assert c.get('/juegos/',headers=h).json()['integration']['status']=='ok'
            assert c.get('/health/live').status_code==200
            assert c.get('/health/ready').status_code==200
    finally:peer.shutdown();peer.server_close()
