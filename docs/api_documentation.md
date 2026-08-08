# API documentation

Base URL: `http://localhost:8000`. Protected REST requests use `Authorization: Bearer <JWT>`. Interactive OpenAPI documentation is available at `/docs` when the backend runs.

## System and authentication

| Method | Path | Auth / role | Request body | Response |
| --- | --- | --- | --- | --- |
| GET | `/health` | None | — | `{status, database}` |
| POST | `/auth/register` | None (prototype bootstrap) | `{username, password, role, resident_id?}`; `resident_id` is required only for resident accounts | `{access_token, token_type}` |
| POST | `/auth/login` | None | `{username, password}` | `{access_token, token_type:"bearer"}`; JWT includes `sub` and `role` |

## Resident API

| Method | Path | Auth / role | Request / query | Response |
| --- | --- | --- | --- | --- |
| GET | `/resident/me` | JWT resident | — | Resident profile `{id,name,nfc_uid,phone,wallet_balance,created_at}` |
| GET | `/resident/history` | JWT resident | `offset=0`, `limit=20` | Array of waste events |
| GET | `/resident/wallet` | JWT resident | — | `{resident_id,points,redeemable_value,currency:"INR"}` |
| GET | `/resident/transactions` | JWT resident | `offset=0`, `limit=50` | Array `{id,resident_id,type:"earn"\|"redeem",points,timestamp,note}` |
| POST | `/resident/redeem` | JWT resident | `{points}` | `{status:"REDEEMED",redeemed_points,wallet_balance}`; HTTP 400 `INSUFFICIENT_BALANCE` if needed |

## RWA and GCC analytics

| Method | Path | Auth / role | Request / query | Response |
| --- | --- | --- | --- | --- |
| GET | `/rwa/dashboard-summary` | JWT rwa | — | Society totals: `by_category`, `today_by_category`, `week_by_category`, resident counts |
| GET | `/rwa/residents` | JWT rwa | `offset`, `limit` | Resident rows with `event_count` and `earned_points` |
| GET | `/rwa/waste-events` | JWT rwa | `category`, `resident_id`, `from_timestamp`, `to_timestamp`, `offset`, `limit` | Filtered waste-event array |
| GET | `/gcc/analytics` | JWT gcc | — | `{scope:"single_society",societies:[{society_id,resident_count,event_count,total_weight_grams,by_category}]}` |
| GET | `/gcc/compliance-report` | JWT gcc | — | Confidence proxy report: correctly segregated, uncertain, percentage |

## NFC API

| Method | Path | Auth / role | Request / query | Response |
| --- | --- | --- | --- | --- |
| POST | `/nfc/scan` | JWT resident/rwa/gcc/admin | `{nfc_uid}` | Registered: `{resident_id,name,status:"REGISTERED"}`; unknown: `{resident_id:0,name:"Guest",status:"UNREGISTERED_CARD"}` |
| GET | `/nfc/last-seen` | JWT admin | — | `{nfc_uid}`; current process memory value for the admin registration screen |
| POST | `/nfc/register` | JWT admin | `{nfc_uid,resident_id}` | `{resident_id,name,status:"REGISTERED"}` |

## Waste and live feed

| Method | Path | Auth / role | Request / query | Response |
| --- | --- | --- | --- | --- |
| POST | `/waste/event` | JWT resident/rwa/gcc/admin | `{client_event_uuid,resident_id,category,confidence_score?,weight_grams?,reward_points?,timestamp?}` | Stored/idempotently replayed waste event. Backend computes reward points and broadcasts the event. Resident JWTs may submit only their own ID. |
| GET | `/waste/live` | JWT resident/rwa/gcc/admin | `limit=20` | Most recent events; resident role receives only its own events |
| WebSocket | `/ws/live-feed` | No auth in prototype | Open socket; client may send keep-alive text | Server pushes waste-event JSON after backend ingestion. Production should add JWT socket auth. |

## Admin API

| Method | Path | Auth / role | Request / query | Response |
| --- | --- | --- | --- | --- |
| POST | `/admin/residents` | JWT admin | `{name,nfc_uid,phone?}` | Created resident profile |
| GET | `/admin/residents` | JWT admin | `offset=0`, `limit=100` | Resident profile array |
| PUT | `/admin/residents/{resident_id}` | JWT admin | Any of `{name,nfc_uid,phone}` | Updated resident profile |
| DELETE | `/admin/residents/{resident_id}` | JWT admin | — | HTTP 204; HTTP 409 if events prevent deletion |
| GET | `/admin/sync-queue` | JWT admin | — | Firebase queue rows `{id,waste_event_id,status,retry_count,last_attempt}` |
| POST | `/admin/sync/firebase` | JWT admin | — | `{status,synced,failed}`; reports disabled/unavailable safely when cloud configuration is absent |

### Waste-event response shape

All waste-event list/create responses have: `{id,client_event_uuid,resident_id,category,confidence_score,weight_grams,reward_points,timestamp,synced_to_firebase}`.
