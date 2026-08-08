# Backend

# SmartSeg backend

FastAPI REST and WebSocket API for JWT-authenticated resident, RWA, GCC, and admin workflows. It shares `../smartseg.db` with `ai-engine/` and initializes/migrates it from `../database/schema.sql` at startup.

## Run

```powershell
pip install -r requirements.txt
uvicorn main:app --reload
```

Run these commands from this `backend/` directory. The health check is `GET /health`; interactive API documentation is at `/docs`.

Set a unique `SMARTSEG_JWT_SECRET` before deployment. Firebase sync is off unless `SMARTSEG_SYNC_ENABLED=true` and `SMARTSEG_FIREBASE_CREDENTIALS` points to a service-account JSON file.
