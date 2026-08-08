# SmartSeg roadmap

## Short term — next prototype iteration

1. Replace the simulated weight with an HX711 load cell and calibrate it against known weights.
2. Add glass, paper/cardboard, e-waste, and hazardous-waste categories with explicit safe-bin handling.
3. Add camera placement guides, lighting checks, and a small collection of real on-site test objects to make the demo repeatable.
4. Add authenticated WebSocket access and rate limiting before any public pilot.

## Medium term — society rollout

1. Add `society_id` and tenant-aware roles so the RWA/GCC views aggregate multiple societies safely.
2. Deliver a resident mobile app for wallet redemption, notifications, and collection-day reminders.
3. Add a redemption catalogue and auditable partner settlement workflow instead of demo-only point redemption.
4. Deploy the laptop software as a managed edge appliance with health monitoring and remote update controls.

## Long term — city-scale intelligence

1. Fine-tune a larger vision model on a locally collected Indian household-waste dataset, including packaging and multilingual labels.
2. Use active-learning review queues for low-confidence items and periodically improve the local model.
3. Integrate municipal corporation systems for ward dashboards, compliance reporting, and collection-route planning.
4. Move to encrypted NFC tags or NFC-plus-PIN verification for meaningful resident authentication.
