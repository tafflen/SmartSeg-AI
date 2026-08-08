# Frontend

# SmartSeg frontend

React 18 + Vite dashboards for residents, RWAs, and GCC oversight. The UI only calls FastAPI REST and WebSocket endpoints; it never accesses the Arduino, SQLite database, or Firebase credentials directly.

## Run

```powershell
npm install
npm run dev
```

The default API target is `http://localhost:8000`. To target another backend, set `VITE_API_URL` before starting Vite. The live-feed WebSocket target is derived automatically from that URL.

The UI theme is intentionally based on forest green, cream, and terracotta; category colours remain functional for sorting data.
