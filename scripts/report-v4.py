#!/usr/bin/env python3
"""Render measured evidence only. No cloud results are invented."""
import datetime, html, json, math, pathlib, sys
out=pathlib.Path(sys.argv[1]);result=json.loads((out/'comparison.json').read_text())
def esc(x):return html.escape(str(x))
series={}
for name in ['steady','round0','round1']:
    points=[];p=out/(name+'.ndjson'); window=out/(name+'-window.json')
    if not p.exists() or not window.exists():continue
    meta=json.loads(window.read_text()); bins={}
    for line in p.open():
        try:r=json.loads(line)
        except ValueError:continue
        if r.get('type')!='Point' or r.get('metric') not in ['flow_ms','local_error','integration_complete']:continue
        d=r['data'];t=datetime.datetime.fromisoformat(d['time'].replace('Z','+00:00')).timestamp()-meta['start']
        b=bins.setdefault(int(t)//5*5,{'flow_ms':[],'local_error':[],'integration_complete':[]});b[r['metric']].append(d['value'])
    for t,b in sorted(bins.items()):
        v=sorted(b['flow_ms']); points.append({'s':t,'p95':v[min(len(v)-1,int(.95*len(v)))] if v else 0,'error':sum(b['local_error'])/max(1,len(b['local_error']))*100,'complete':sum(b['integration_complete'])/max(1,len(b['integration_complete']))*100})
    series[name]={'meta':meta,'points':points}
rows=''.join('<tr><td>'+esc(k)+'</td>'+''.join('<td>'+esc(round(v[n],3))+'</td>' for n in ['p95_ms','local_error','complete','requests'])+'</tr>' for k,v in result['measured'].items())
charts=''
for metric,title,unit in [('p95','Latencia p95 por intervalos de 5 segundos','ms'),('error','Error del servicio local','%'),('complete','Integración completa en tiempo real','%')]:
    maximum=max([p[metric] for s in series.values() for p in s['points']]+[1]);maximum=maximum*1.1
    svg='<svg viewBox="0 0 960 280" role="img" aria-label="'+title+'"><rect x="55" y="15" width="810" height="220" fill="#fff3dd"/>'
    for i in range(5):
        y=235-i*55;svg+=f'<line x1="55" x2="930" y1="{y}" y2="{y}" stroke="#ddd"/><text x="2" y="{y}" font-size="12">{maximum*i/4:.0f}</text>'
    for name,color in [('steady','#64748b'),('round0','#c2410c'),('round1','#0369a1')]:
        points=series.get(name,{}).get('points',[]); coords=' '.join(f"{55+p['s']*9},{235-p[metric]/maximum*220}" for p in points)
        svg+=f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{coords}"/>'
    svg+='<text x="55" y="265">0 s</text><text x="460" y="265">45 s</text><text x="850" y="265">90 s</text></svg>'
    charts+='<h2>'+title+' ('+unit+')</h2>'+svg
windows=''.join('<li>'+esc(n)+': '+esc(datetime.datetime.fromtimestamp(s['meta']['start'],datetime.timezone.utc).isoformat())+' → '+esc(datetime.datetime.fromtimestamp(s['meta']['end'],datetime.timezone.utc).isoformat())+'</li>' for n,s in series.items())
page='''<!doctype html><html lang="es"><meta charset="utf-8"><title>Experimento de caos medido</title><style>body{max-width:1040px;margin:40px auto;font:16px/1.5 system-ui;color:#172033;padding:0 24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:10px;text-align:left}svg{width:100%}pre{white-space:pre-wrap}h1{font-size:30px}</style>'''
page+='<h1>Experimento '+esc(result['experiment'])+'</h1><p>Puerta de calidad: <b>'+('APROBADA' if result.get('gate') else 'RECHAZADA')+'</b>. Fuente: mediciones k6 de esta ejecución. Compruebe el host y la nube en el journal antes de presentar.</p>'
page+='<table><tr><th>Ronda</th><th>p95 ms</th><th>Error local 0 a 1</th><th>Completa 0 a 1</th><th>Peticiones</th></tr>'+rows+'</table>'
page+='<p>Líneas: gris estado estable, naranja ronda 0, azul ronda 1. Franja amarilla: ventana de solicitudes con fallo (0 a 90 s), sólo en rondas 0 y 1; las solicitudes en curso pueden terminar después. Eje temporal alineado para comparar perfiles idénticos. p95 del cuadro usa todas las muestras, no el promedio de p95 parciales.</p>'+charts+'<h2>Ventanas absolutas UTC</h2><ul>'+windows+'</ul>'
page+='<h2>Conclusión automática y límites</h2><pre>'+esc(json.dumps(result,indent=2,ensure_ascii=False))+'</pre><p>Durante una dependencia caída, la respuesta parcial NO cumple la disponibilidad del flujo completo. El objetivo es conservar datos locales y acotar latencia. Complete el diagnóstico con trazas correlacionadas y capturas reales.</p></html>'
(out/'dashboard.html').write_text(page)
report=f'''# Informe de experimento {result['experiment']}

Ejecución: {out.name}. Resultado de puerta: {result.get('gate')}. Infraestructura y ventana: completar con las cuentas y URLs reales de esta ejecución.

## Estado estable y resultados medidos

```json
{json.dumps(result,indent=2,ensure_ascii=False)}
```

## Método e hipótesis

Perfil fijo 15 s de 0 a 5 VU, 60 s a 5 VU y 15 s de 5 a 0; una solicitud por iteración y pausa 200 ms; mismo fallo y carga antes y después. Métrica AWS p95 <1500 ms; GCP error local <=1%. Inyección sólo por solicitud autenticada, sin escrituras. Ronda 0 desactiva timeout corto y respuesta parcial; ronda 1 activa ambos.

## Diagnóstico de mecanismo y evidencia

Completar con traceId reales y extractos JSON de ambas nubes. AWS: la espera saliente puede dominar p95 sin causar errores HTTP. GCP: un 503 remoto se propaga como 502 sin protección; con ella se conserva data y mascota=null. Ver dashboard.html y los archivos ndjson. Adjuntar captura del tablero y logs del instante exacto. No afirmar verificación en nube usando pruebas locales.

## Reversión y radio de impacto

Sólo GET con token y vencimiento en infraestructura propia. Al parar k6 desaparece la inyección; espera 7 s y verificación del flujo completo. recovery.json contiene el resultado. El control sin fallo aborta si deja de funcionar. Deshabilitar CHAOS_ENABLED después del ejercicio.

## Hallazgos inesperados y backlog

Completar con lo observado, incluyendo si no se refuta la hipótesis. Pendiente según diagnóstico: circuito, bulkhead, telemetría OTel a un backend distribuido, HTTPS de extremo a extremo y autenticación de todas las rutas. No se usan caché ni datos ficticios como fallback.

## Apoyo de IA

ChatGPT propuso la composición viva, el aislamiento por solicitud y la comparación automatizada. Se descartaron caché de entidades y reintentos para mantener el requisito realtime y evitar multiplicar tráfico durante un fallo. Los integrantes deben revisar y explicar los resultados obtenidos.
'''
(out/'informe-experimento.md').write_text(report)
print(out/'dashboard.html')
# Compact four-page draft. Human diagnosis/captures must be completed after cloud execution.
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=sec.bottom_margin=Inches(.75)
for n in ['Normal','Title','Heading 1','Heading 2']:
    doc.styles[n].font.name='Calibri';doc.styles[n].font.color.rgb=RGBColor(0,0,0)
doc.styles['Normal'].font.size=Pt(11)
def para(s):doc.add_paragraph(s)
def heading(s):doc.add_heading(s,1)
doc.add_heading('Informe de experimento de caos',0)
para(result['experiment']+' · Ejecución '+out.name)
para('Borrador basado en mediciones de esta ejecución. Completar identificación de cuentas, diagnóstico y capturas antes de entregar. No presentar una ejecución local como evidencia de nube.')
heading('Estado estable e hipótesis')
para('Perfil fijo de 90 segundos: 15 segundos de subida a 5 usuarios virtuales, 60 constantes y 15 de bajada. Se usa el mismo perfil en estado estable y en ambas rondas. AWS propone p95 menor a 1500 ms bajo 3000 ms de latencia; GCP error local máximo de 1% bajo 503 de mascotas.')
para('Estado estable exigido antes de inyectar: completitud de al menos 99%, error local máximo de 1% y p95 menor a 1500 ms. Los valores realmente medidos aparecen en la siguiente página.')
heading('Método y radio de impacto')
para('Chaos Toolkit ejecuta k6 y un interruptor propio por cabeceras con token y vencimiento. Sólo afecta solicitudes GET sintéticas autorizadas. No modifica bases de datos ni derriba todo el servicio. Ronda 0 conserva límite de seguridad de 6 s y propaga errores; ronda 1 usa timeout de 800 ms y respuesta parcial sin caché.')
doc.add_page_break();heading('Resultados medidos')
t=doc.add_table(rows=1,cols=5);t.style='Table Grid'
for c,v in zip(t.rows[0].cells,['Ronda','p95 ms','Error local','Completa','Peticiones']):c.text=v
for name,v in result['measured'].items():
    cells=t.add_row().cells
    for c,x in zip(cells,[name,f"{v['p95_ms']:.2f}",f"{v['local_error']:.4f}",f"{v['complete']:.4f}",str(v['requests'])]):c.text=x
para('Tasas expresadas de 0 a 1. La completitud mide llegada del objeto remoto y no debe confundirse con disponibilidad local.')
para('Puerta de calidad: '+('aprobada' if result.get('gate') else 'rechazada')+'. Recuperación: '+str(result.get('recovered'))+'.')
para('Métrica objetivo: '+str(result.get('metric','no calculada'))+'. Antes: '+str(result.get('before'))+'. Después: '+str(result.get('after'))+'. Variación porcentual: '+str(result.get('variation_percent'))+'.')
para('Error o aborto: '+str(result.get('error','ninguno registrado')))
heading('Ventanas de observación')
for name,s in series.items():para(name+': '+datetime.datetime.fromtimestamp(s['meta']['start'],datetime.timezone.utc).isoformat()+' a '+datetime.datetime.fromtimestamp(s['meta']['end'],datetime.timezone.utc).isoformat())
para('Adjuntar captura o enlace al dashboard.html de esta ejecución. Las curvas de las dos rondas y la ventana de inyección se encuentran en ese archivo; ndjson conserva todas las muestras.')
doc.add_page_break();heading('Diagnóstico con evidencia')
para('Completar con dos o más traceId reales, extractos de los spans de ambas nubes y la captura del tablero en la ventana del fallo. Explicar el mecanismo causal, no sólo que el gráfico sube.')
para('AWS: la espera saliente domina la latencia sin necesariamente generar errores HTTP. El timeout limita esa espera. Si vence antes de abrir conexión a GCP, no debe esperarse un span remoto para esa solicitud.')
para('GCP: un 503 de mascotas se propaga como 502 al consumidor sin protección. La degradación conserva data local y devuelve mascota=null. La métrica de completitud cae aunque el error local se recupere.')
heading('Hallazgos y conclusión de la hipótesis')
para('Completar: hipótesis refutada o no en ronda 0, aceptada provisionalmente o no en ronda 1, observaciones inesperadas, límites de la medición y posible influencia de la ubicación del generador. Si no hubo refutación inicial, no afirmar mejora demostrada.')
doc.add_page_break();heading('Reversión y cierre')
para('Al detener k6 dejan de emitirse cabeceras de inyección. Las solicitudes en vuelo están limitadas a 6 s; se espera 7 s y se comprueba una consulta completa sin fallos. recovery.json conserva el resultado. Desactivar CHAOS_ENABLED en ambas APIs al terminar la ventana.')
para('Abortos: falla del control sin caos, duración superior a 115 s por ronda o error local de más de 50% durante la ronda protegida después de 10 s. La refutación esperada en la ronda inicial no se confunde con un fallo del control independiente.')
heading('Backlog de resiliencia')
para('Revisar según evidencia: circuit breaker, bulkhead, autenticación general de rutas, HTTPS completo y backend de trazas OTel. No añadir patrones sin explicar qué modo de fallo resuelven. Mantener las comparaciones bajo carga fija.')
heading('Apoyo de inteligencia artificial')
para('ChatGPT propuso la integración viva, timeout y respuesta parcial, el aislamiento por solicitud y la generación de evidencias. Se descartaron caché de entidades y reintentos para respetar realtime y evitar amplificar errores. Los estudiantes deben revisar, ejecutar y explicar las mediciones.')
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            tcPr=cell._tc.get_or_add_tcPr(); borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            tcPr.append(borders)
    for cell in table.rows[0].cells:
        shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E8EDF2');cell._tc.get_or_add_tcPr().append(shade)
for root in [doc._element, doc.styles.element]:
    for border in list(root.iter(qn('w:pBdr'))): border.getparent().remove(border)
doc.save(out/'informe-experimento.docx')
