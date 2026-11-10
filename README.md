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
