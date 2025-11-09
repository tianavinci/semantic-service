from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from api.app.routers import convert, attributes, search
from api.app.config import settings

app = FastAPI(title="semantic-service", default_response_class=ORJSONResponse)

@app.middleware("http")
async def add_version_header(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Semantic-Version"] = settings.semantic_version
    return resp

app.include_router(convert.router)
app.include_router(search.router)
app.include_router(attributes.router)

@app.get("/healthz")
def healthz(): return {"ok": True}
