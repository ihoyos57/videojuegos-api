import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("trace")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

TRACE_HEADER = "X-Trace-Id"


class TraceIdMiddleware(BaseHTTPMiddleware):
    """
    - Si la peticion YA trae X-Trace-Id (porque viene de un compañero
      que nos esta llamando), lo reutilizamos: asi el mismo id viaja
      entre las nubes.
    - Si no trae nada (porque la peticion empieza aqui, por ejemplo
      alguien probando en Postman), generamos uno nuevo.
    - Lo guardamos en request.state para poder usarlo en los routers,
      lo devolvemos en la respuesta, y lo dejamos en el log.
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get(TRACE_HEADER) or str(uuid.uuid4())
        request.state.trace_id = trace_id

        logger.info(f"[trace_id={trace_id}] {request.method} {request.url.path} - inicio")

        response = await call_next(request)

        response.headers[TRACE_HEADER] = trace_id
        logger.info(
            f"[trace_id={trace_id}] {request.method} {request.url.path} "
            f"- fin status={response.status_code}"
        )
        return response