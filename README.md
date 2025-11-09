# semantic-service

Ultra-fast attribute conversion service (physical <-> logical) with CRUD/search,
backed by Postgres and Redis, exposed via FastAPI. Designed for heavy concurrent traffic.

## Quickstart (Local)

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
