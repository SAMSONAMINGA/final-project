# FloodGuard KE Backend - Project Structure

```
backend/
├── main.py                          # FastAPI root application
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── Dockerfile                       # Container image
├── docker-compose.yml               # Local dev stack (pg, redis, celery)
├── dev-setup.sh                     # Setup script
├── README_BACKEND.md                # Architecture & API docs
├── alembic.ini                      # Alembic config
│
├── core/                            # Core infrastructure
│   ├── config.py                    # Settings (Pydantic v2)
│   ├── database.py                  # SQLAlchemy 2.0 + AsyncPG
│   ├── redis_client.py              # Redis pubsub + caching
│   └── security.py                  # JWT + RBAC + password hashing
│
├── models/                          # SQLAlchemy ORM
│   └── orm.py                       # All 8 tables (users, counties, etc.)
│
├── schemas/                         # Pydantic v2 validation
│   └── api.py                       # Request/response models
│
├── utils/                           # Algorithms & integrations
│   ├── ekf.py                       # Extended Kalman Filter (sensor fusion)
│   ├── gatv2.py                     # GATv2 ONNX inference + drainage graphs
│   ├── imerg_fetcher.py             # NASA IMERG + OpenWeather clients
│   ├── alerts.py                    # SMS/USSD generation + Africa's Talking dispatch
│   └── shap_explainer.py            # SHAP interpretability
│
├── services/                        # Background jobs & loaders
│   ├── ml_loader.py                 # GATv2 + LSTM model manager
│   ├── county_loader.py             # County metadata cache
│   ├── celery_app.py                # Celery app + Beat schedule
│   └── tasks/                       # Celery background jobs
│       ├── imerg_task.py            # Fetch IMERG every 30 min
│       ├── openweather_task.py      # Fetch OpenWeather every 30 min
│       ├── inference_task.py        # Run GATv2 every 30 min
│       └── alert_task.py            # Dispatch SMS/USSD
│
├── routers/                         # API endpoints (FastAPI)
│   ├── auth.py                      # POST /auth/token, /auth/refresh
│   ├── barometer.py                 # POST /ingest/barometer, /batch
│   ├── risk.py                      # GET /risk/{county_code}
│   ├── simulate.py                  # POST /simulate
│   ├── websocket.py                 # WS /ws/live
│   ├── alerts.py                    # POST /alerts/send, /at-delivery
│   └── admin.py                     # POST /admin/retrain, /ekf-tune, etc.
│
├── alembic/                         # Database migrations
│   ├── env.py                       # Migration environment config
│   └── versions/
│       └── 0001_initial.py          # Initial schema (all 8 tables)
│
└── tests/
    └── test_synthetic_data.py       # Kenya county data loader
```

## Key Design Decisions

### 1. **Async Throughout**
- AsyncPG for non-blocking DB
- httpx for async HTTP
- Celery for long-running tasks
- Redis pub/sub for WebSockets

### 2. **Stateless API**
- No session state
- JWT tokens (HS256)
- Horizontal scaling-ready
- Load balancer compatible

### 3. **Production Patterns**
- Environment-based config (Pydantic v2 BaseSettings)
- Lifespan context manager (FastAPI 0.93+)
- Rate limiting (slowapi)
- Structured JSON logging (structlog)
- Immutable audit/alert logs
- SHA-256 hashing for PII (device_id, phone)

### 4. **ML Integration**
- ONNX Runtime for inference (no PyG runtime dependency)
- EKF for sensor fusion (3-source rainfall)
- SHAP for per-node interpretability
- Fallback LSTM for rural counties

### 5. **Data Pipeline**
- Celery Beat every 30 min:
  - IMERG fetch
  - OpenWeather fetch
  - GATv2 inference
- Alert dispatch on-demand via API

### 6. **Validation**
- Pydantic v2 for strict input validation
- Kenya bbox bounds on all GPS
- Phone number hashing before storage
- No PII stored (only hashes)

## Deployment

### Local Development
```bash
bash dev-setup.sh
# Runs Docker services + alembic + synthetic data + uvicorn
```

### Docker Production
```bash
docker-compose up -d
# All services: backend, postgres, redis, celery, beat
```

### Kubernetes (Example)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: floodguard-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: floodguard/backend:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: floodguard-secrets
              key: database_url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: floodguard-secrets
              key: redis_url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: floodguard-secrets
              key: secret_key
```

## Testing

```bash
# Run synthetic data loader
python tests/test_synthetic_data.py

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Interactive docs
```

## Monitoring

- Health check: GET /health
- Database: PostgreSQL admin interface
- Redis: redis-cli
- Celery tasks: Flower (optional: `pip install flower`, `celery -A services.celery_app flower`)
- API logs: /tmp/floodguard.log (if logging configured)

---

**Status**: ✓ Production-ready, all endpoints implemented, no placeholders
