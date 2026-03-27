# Troubleshooting

## The dashboard loads but shows no data

- Confirm the backend is running on `http://localhost:8000`.
- Check `GET /api/me` directly. If that fails, the backend is not bootstrapped correctly.
- If you changed `AUTH_MODE`, make sure the expected headers or credentials are present.

## The backend starts but the demo state is missing

- Confirm `SEED_DEMO=true`.
- Confirm `SEED_ON_STARTUP=true`.
- Restart the backend after changing seed-related variables.

## Websocket status shows offline

- The dashboard still works without live fanout, but it will rely on follow-up API reads.
- Confirm Redis is reachable if you want the default live update path.
- Confirm the backend exposes `/ws/dashboard`.

## Frontend dev server fails to start

- Run `cd frontend && npm install`.
- Re-run `cd frontend && npm run build` to catch type or config issues before launching the dev server.

## Smoke test fails unexpectedly

- Re-run `cd backend && venv/bin/python -m src.demo.smoke_runner`.
- If previous manual testing left the demo data in a strange state, restarting with `SEED_ON_STARTUP=true` resets the seeded workspace.
- For targeted pytest execution, use `-o addopts=` to bypass the repo-wide legacy pytest defaults.
