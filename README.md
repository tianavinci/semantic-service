# semantic-service

Ultra-fast attribute conversion service (physical <-> logical) with CRUD/search,
backed by Postgres and Redis, exposed via FastAPI. Designed for heavy concurrent traffic.

## Quickstart (Local)
Build the image

```bash
docker compose -f docker/docker-compose.yml up --build -d
# wait for db to come up
docker ps
# run migration
docker exec -it $(docker ps -qf "ancestor=semantic-service_api") bash -lc "psql $DATABASE_URL -f /app/migrations/001_init.sql"
# if that doesn't resolve, connect to db container:
# docker exec -it semantic-service-db-1 psql -U semantic -d semantic -f /app/migrations/001_init.sql
```

API: http://localhost:8080  
DB:  postgresql://lextr_user:Mygooru1028%24@host.docker.internal:5433/lextr
Redis: redis://localhost:6379/0

### Create sample attributes
```bash
curl -X POST http://localhost:8080/v1/attributes -H 'content-type: application/json' -d '[
 {"namespace":"default","entity":"customer","logical_name":"Customer Name","physical_name":"cust_nm","data_type":"text"},
 {"namespace":"default","entity":"loan","logical_name":"Loan Principal Balance","physical_name":"ln_prin_bal","data_type":"decimal"}
]'
```

### Convert physical -> logical
```bash
curl -X POST http://localhost:8080/v1/convert/physical-to-logical -H 'content-type: application/json' -d '{
 "namespace":"default","entity":"customer","physical_names":["cust_nm","cust_id"]
}'
```

---

## Helm (GKE)
See `helm/semantic-service/`

```bash
helm upgrade --install semantic-service helm/semantic-service   --set image.repository=YOUR_REGISTRY/semantic-service   --set image.tag=latest   --set env.DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@HOST:5433/DB"   --set env.REDIS_URL="redis://redis:6379/0"
```


## LOCAL
set DATABASE_URL=postgresql+asyncpg://lextr_user:Mygooru1028%24@localhost:5433/lextr
set REDIS_URL=redis://localhost:6379/0
uvicorn api.app.main:app --reload --port 8080



## Distributed Dask with Docker Compose
Run the full distributed stack (Postgres, Redis, Dask scheduler, Dask worker(s), API)

Quick start (from project root):

1) Build images and start services:

```bash
# Build and start all services (scheduler + one worker)
docker compose up --build -d
```

2) Scale workers (run more workers):

```bash
# Add 2 more workers (total 3 workers)
docker compose up -d --scale dask-worker=3
```

3) Check logs (scheduler / worker / api):

```bash
docker compose logs -f dask-scheduler
docker compose logs -f dask-worker
docker compose logs -f api
```

4) Open the Dask dashboard:

- Dashboard is exposed on host port 8787 by default. Open http://localhost:8787/ in your browser.
- Alternatively, query the scheduler from a running container:

```bash
docker compose exec api python -c "from api.app.dask_config import DaskConfig; c=DaskConfig().client(); print('dashboard:', c.dashboard_link); c.close()"
```

5) Notes:

- The `api` service is configured with `DASK_MODE=remote` and `DASK_SCHEDULER_ADDRESS=tcp://dask-scheduler:8786` so it will attach to the scheduler in the compose network.
- The `Dockerfile` installs `dask` and `distributed`, so scheduler/worker images use the same build and will have the application deps available.
- Adjust `dask-worker` args (`--nthreads`, `--memory-limit`) for your host capacity.

6) Stopping and cleaning up:

```bash
docker compose down --volumes --remove-orphans
```
