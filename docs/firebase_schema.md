# Firestore mirror schema

Firestore is a cloud mirror for synchronization and dashboards; the SQLite database remains the immediate source of truth during operation.

## Collections

### `residents/{residentId}`

```json
{
  "name": "Resident name",
  "nfc_uid": "NFC-UID",
  "phone": "+91...",
  "wallet_balance": 0,
  "created_at": "server timestamp / ISO-8601"
}
```

`residentId` is the SQLite `residents.id` serialized as a stable document ID. NFC UID lookups happen locally; Firestore rules should restrict access to authorized backend service accounts and appropriate user roles.

### `waste_events/{eventId}`

```json
{
  "resident_id": 1,
  "category": "PLASTIC",
  "confidence_score": 0.93,
  "weight_grams": 120.0,
  "reward_points": 5,
  "timestamp": "ISO-8601"
}
```

`eventId` is the stable SQLite `waste_events.id`, making retries idempotent upserts rather than duplicate cloud events.

### `analytics_daily/{YYYY-MM-DD}`

```json
{
  "date": "2026-08-08",
  "event_count": 0,
  "total_weight_grams": 0.0,
  "category_totals": {
    "PLASTIC": 0.0,
    "ORGANIC": 0.0,
    "METAL": 0.0,
    "OTHER": 0.0
  },
  "updated_at": "server timestamp / ISO-8601"
}
```

Daily analytics are derived summaries. The future sync worker updates them transactionally or recomputes them from successfully synced `waste_events`; they are never the sole record of a disposal.

## Local-first synchronization strategy

1. On a completed cycle, write `waste_events` and its pending `sync_queue` row in one SQLite transaction. The event is usable locally immediately.
2. A background backend worker checks connectivity and claims pending/failed queue rows.
3. It upserts the matching resident (as needed) and waste event by stable local ID, then updates the daily analytics document.
4. Only after all cloud writes succeed does it set `waste_events.synced_to_firebase = 1` and mark the queue item `synced`.
5. On failure, it increments `retry_count`, records `last_attempt`, and leaves the local event intact for backoff retry after connectivity returns.

This prevents network outages from blocking waste segregation or losing resident rewards.
