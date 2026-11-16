#!/usr/bin/env python3
import os,json,urllib.request,uuid

def post(base,path,body):
    req=urllib.request.Request(base.rstrip('/')+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
aws=os.environ['AWS_API_URL'];gcp=os.environ['GCP_API_URL']; suffix=uuid.uuid4().hex[:8]
owner=post(aws,'/owners',{'nombre':'Persona','apellido':'Sintetica','telefono':'3000000000','email':f'test-{suffix}@example.com'})
pet=post(aws,'/pets',{'nombre':'Mascota sintetica','especie':'Perro','raza':'Mestizo','edad':2,'ownerId':int(owner['id'])})
appointment=post(aws,'/appointments',{'fecha':'2026-11-18T15:00:00Z','motivo':'Revision sintetica','petId':str(pet['id'])})
game=post(gcp,'/juegos/',{'nombre':'Juego sintetico '+suffix,'genero':'Aventura','plataforma':'PC','precio':10,'stock':10})
player=post(gcp,'/jugadores/',{'nombre':'Jugador sintetico','correo':f'player-{suffix}@example.com'})
purchase=post(gcp,'/compras/',{'jugador_id':player['id'],'juego_id':game['id'],'cantidad':1})
print(json.dumps({'owner':owner['id'],'pet':pet['id'],'appointment':appointment['id'],'juego':game['id'],'jugador':player['id'],'compra':purchase['id']},indent=2))
