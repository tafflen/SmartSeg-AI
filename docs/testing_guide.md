# Testing guide

## Unit tests

The reward engine is intentionally pure: no database, serial port, or network is required. Tests live in `backend/tests/test_reward_engine.py`.

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
pytest tests/test_reward_engine.py
cd ..
python -m unittest discover ai-engine/tests
```

The reward cases verify metal’s 2× multiplier, plastic’s 1.5× multiplier followed by low-confidence penalty, `OTHER` truncation, and safe missing inputs. The serial test proves retransmitted `EVT` IDs receive a second ACK but only one queued event.

## Integration checklist

1. Start with `SMARTSEG_SIMULATE_MODE=true`; verify `[AI]`, `[BACKEND]`, and `[FRONTEND]` logs appear.
2. Log in to each role dashboard with seeded/test accounts; verify resident, RWA, GCC, and admin pages respect role routing.
3. Confirm simulated events are written locally and appear in `/waste/live` plus the WebSocket live feed.
4. Stop the backend while simulation continues; confirm AI logs bridge retries and the frontend shows its backend-unreachable banner.
5. Restart the backend; confirm queued events replay without duplicate wallet credits, and dashboards receive updates.
6. Set `MOCK_MODE=false` only after verifying Arduino/NFC COM ports; run the ordered hardware path in [end-to-end test plan](end_to_end_test_plan.md).
7. Test registered and unknown NFC cards, a low-confidence classification, reward milestone, redemption, and Arduino unplug/reconnect behavior.

## Demo-day checklist

- Laptop charger connected; external motor and servo supplies charged/verified.
- Arduino and PN532 COM ports written down and set in the launch environment.
- Conveyor moves freely; bins/gate are aligned; IR sensor and raindrop module are dry/clean.
- One registered sample NFC card and one deliberately unregistered card are ready.
- Test account has enough points to demonstrate redemption; admin phone is configured.
- Browser tabs open for resident, RWA, GCC, and admin views; Mock SMS terminal log is visible if Twilio is not used.
- `SMARTSEG_SIMULATE_MODE=true` is prepared as the immediate fallback if hardware or lighting fails.
- Run one full rehearsal following the end-to-end plan before judges arrive.
