from contextlib import asynccontextmanager
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Literal
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text
from src.db import engine, init_db
from src.matching import postcode_key, name_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title='UK Business Entity Resolution', lifespan=lifespan)
requests = Counter('business_http_requests','HTTP requests',['status'])
latency = Histogram('business_http_seconds','HTTP request duration')
windows: dict[str, deque[float]] = defaultdict(deque)
lock = Lock()

@app.middleware('http')
async def monitor(request: Request, call_next):
    start = monotonic()
    if request.url.path.startswith(('/business','/review')):
        key = request.client.host if request.client else 'unknown'
        with lock:
            if len(windows)>10000 and key not in windows:
                return JSONResponse({'detail':'Rate limit capacity'},status_code=429)
            bucket = windows[key]
            while bucket and bucket[0] <= start-60:
                bucket.popleft()
            if len(bucket)>=6000:
                return JSONResponse({'detail':'Rate limit exceeded'},status_code=429)
            bucket.append(start)
    response = await call_next(request)
    requests.labels(str(response.status_code)).inc()
    latency.observe(monotonic()-start)
    return response

@app.get('/health')
def health():
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    return {'status':'ok'}

@app.get('/metrics')
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get('/business')
def search(name: str = Query(min_length=1,max_length=200), postcode: str = Query(min_length=3,max_length=20)):
    normalized = name_key(name)
    if not normalized:
        raise HTTPException(422, 'Business name is empty after normalization')
    # Escape SQL LIKE metacharacters; only the final percent is a wildcard.
    prefix = normalized.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT fsa_id, company_id, name, postcode, score, status FROM matches WHERE postcode=:p AND normalized_name LIKE :n ESCAPE '!' AND status IN ('auto_match','approved') ORDER BY score DESC LIMIT 50"), {'p':postcode_key(postcode),'n':prefix}).mappings()
        return [dict(row) for row in rows]

@app.get('/review')
def review():
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text("SELECT * FROM matches WHERE status='review' LIMIT 100")).mappings()]

@app.post('/review/{fsa_id}/{company_id}')
def resolve(fsa_id: str, company_id: str, status: Literal['approved','rejected']):
    with engine.begin() as conn:
        result=conn.execute(text("UPDATE matches SET status=:s WHERE fsa_id=:f AND company_id=:c AND status='review'"),{'s':status,'f':fsa_id,'c':company_id})
        if result.rowcount != 1:
            raise HTTPException(404,'Pending match not found')
    return {'status':status}
