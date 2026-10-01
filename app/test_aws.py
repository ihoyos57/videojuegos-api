import asyncio
import httpx

URL = "http://ae7646e6cf2b74912906f40f9a30539d-032ee795ec92fbaf.elb.us-east-2.amazonaws.com/pets"


async def main():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(URL, timeout=10.0)

            print("STATUS:", response.status_code)
            print("RESPUESTA:", response.text[:500])

    except Exception as e:
        print("ERROR:", type(e).__name__)
        print("DETALLE:", str(e))


asyncio.run(main())