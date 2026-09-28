# PlantAssure — Iteration 3 (standalone app)

A separate, self-contained version of PlantAssure for Iteration 3. It does not
use or change the team's code or servers.

| Folder | What it is |
|---|---|
| `pipeline/` | Iteration 3 data pipeline (builds on the Iteration 2 pipeline) and its output |
| `backend/` | FastAPI + MySQL API: plants, Plant Passport, swaps, insights, My Garden |
| `frontend/` | Vue 3 + Vuetify site |

## Features
- **Plant Passport** — what we know / don't know, evidence strength, growing tips for safe plants, containment tips for risky plants
- **My Garden** — garden check-up, swap or contain each risky plant, print, and a **private link** (random UUID) to open the garden on any device
- **Data insights** — three charts calculated in MySQL
- **Safer swaps** — suggestions come from the pipeline's strict four-trait match and are never rated risky
- **Photo identification** — via the [Pl@ntNet API](https://my.plantnet.org); suggestions are matched to PlantAssure's own plant records before the user can confirm one

## Privacy
Gardens store only a random id, plant ids and a timestamp — no names, emails or
other personal information. Gardens unchanged for 90 days are deleted. The API
runs with `--no-access-log` so client IP addresses are not logged.

## Database (MySQL 8)
Tables: `plant`, `plant_flowering`, `plant_local_records`, `plant_evidence`,
`plant_alternative`, `garden`, `garden_plant` — see `backend/db/schema.sql`.

## Deploy
See [DEPLOY.md](DEPLOY.md) — Render (website + API) and Aiven (MySQL).

## Run locally
1. Start MySQL (private instance, port 3307):
   `/opt/anaconda3/bin/mysqld --defaults-file=backend/db/my.cnf`
2. Load data (first time, or after re-running the pipeline):
   ```
   cd backend
   .venv/bin/python build_data.py   # pipeline output -> data/plants.json
   .venv/bin/python load_data.py    # data/plants.json -> MySQL
   ```
3. API: `cd backend && .venv/bin/uvicorn main:app --port 8090 --no-access-log`
4. Site: `cd frontend && npx vite --port 5177` → http://localhost:5177

Database credentials live in `backend/.env` (not committed).

### Photo identification (Pl@ntNet)
1. Create a free account at https://my.plantnet.org and copy your API key (free tier: 500 identifications a day).
2. Add this line to `backend/.env`: `PLANTNET_API_KEY=your-key-here`
3. Restart the API.

Without a key, the photo page shows "Photo identification isn’t set up yet." Photos are
re-saved without metadata (including GPS) in the browser and again on the server, are
never stored, and are sent to Pl@ntNet, which may keep them. Attribution to Pl@ntNet is
shown on the page, as its terms require.

## Tests
`cd backend && .venv/bin/python -m pytest` — runs against a separate `plantassure_i3_test` database.
