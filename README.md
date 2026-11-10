# Weye AI — Hotel Reservation Agent

Independent project. The existing `saledream/weyea` repository is untouched.

## Phase 1: Reservation API

FastAPI + SQLAlchemy + PostgreSQL. Demo hotel inventory uses ETB prices.

### Start locally

```sh
docker compose up --build
```

Visit http://localhost:8000/docs for interactive API documentation.

### API endpoints

- `GET /health`
- `POST /availability`: check_in, check_out, guests
- `POST /reservations`: stay details, room_type_id, guest_name, idempotency_key
- `GET /reservations/{reference}`

### Development status

This is a prototype, not a production booking system. Before live deployment, implement authentication, multi-hotel isolation, Alembic migrations, transactional inventory locking, booking holds, tax and cancellation rules, and automated tests. The booking endpoint currently checks availability but is **not concurrency-safe** under simultaneous booking requests.

### Next phases

1. Harden booking engine and add tests.
2. React/Vite browser interface and LiveKit voice agent.
3. Hotel dashboard and human escalation.
4. SIP telephony and hotel PMS integration.

## Browser voice demonstration

Run `docker compose up --build`, then visit **http://localhost:8000/demo**.

The demo supports browser speech recognition/synthesis where available, text entry, date selection, room lookup, and reservation confirmation. It is a **limited push-to-talk demo**, not the planned LiveKit streaming voice agent. Speech recognition browser support varies and may use browser-vendor cloud services. The backend currently seeds one demonstration hotel and is not safe for public deployment. Do not enter real guest personal information.

PostgreSQL row locking now serializes competing reservations for the same room type when using the Docker database; SQLite remains unsuitable for concurrent booking validation. This is not a substitute for production hardening and tests.

## LiveKit real-time voice (experimental integration)

The new React frontend and Python LiveKit agent are committed, but have **not yet been executed end-to-end**. You need a LiveKit Cloud project with Inference access. Follow [LiveKit setup](https://docs.livekit.io/agents/start/voice-ai/) to obtain a project URL and API credentials.

1. Copy `voice-agent/.env.example` to a local `.env` at the repository root and replace the three LiveKit values. **Never commit this file.**
2. Run `docker compose up --build` for PostgreSQL, FastAPI and React.
3. In a second terminal, run `docker compose --profile voice up --build voice-agent` to start the Python agent.
4. Open **http://localhost:5173** and allow microphone access. The agent should join automatically when a room is created.

The FastAPI development token endpoint is unauthenticated and is intended for localhost testing **only**. Protect it with authentication, rate limiting, origin restrictions, and deployment controls before exposing any service publicly. Do not use real guest information.

If your LiveKit project requires explicit dispatch rather than automatic dispatch, adjust the agent registration and room dispatch configuration before testing. Model identifiers and billing depend on your LiveKit project and may need adjustment.

The earlier browser-speech fallback remains at http://localhost:8000/demo.
