# Deploying PlantAssure Iteration 3 (Render + Aiven MySQL)

- **Website** → Render static site (free)
- **API** → Render web service (free; sleeps after 15 minutes without visitors — the first visit after that takes about a minute)
- **Database** → Aiven for MySQL, free plan (1 GB, no credit card)

You create the accounts and enter the secrets yourself. Nothing secret is stored in this repo.

---

## Part 1 — Database (Aiven)

1. Sign up at https://aiven.io (free, no credit card).
2. **Create service → MySQL → Free plan.** Pick any region offered and name it e.g. `plantassure-db`. Wait until it shows **Running**.
3. On the service's **Overview** page, note the connection details:
   - **Host**, **Port**, **User** (usually `avnadmin`), **Password**, **Database name** (usually `defaultdb`)
4. Download the **CA certificate** (`ca.pem`) from the same page. You'll paste its contents into Render.

## Part 2 — API and website (Render)

1. Sign up at https://render.com with **GitHub**, and allow Render to access the repo `aasapande/plantassure-i3-app`.
2. **New → Blueprint** → choose `aasapande/plantassure-i3-app`. Render reads `render.yaml` and shows two services: `plantassure-i3-api` and `plantassure-i3-web`.
3. Fill in the values it asks for:

   | Service | Setting | Value |
   |---|---|---|
   | API | `DB_HOST` | Aiven host |
   | API | `DB_PORT` | Aiven port |
   | API | `DB_NAME` | `defaultdb` (or Aiven's database name) |
   | API | `DB_USER` | `avnadmin` (or Aiven's user) |
   | API | `DB_PASSWORD` | Aiven password |
   | API | `DB_SSL_CA_PEM` | Open `ca.pem` in a text editor, copy **everything** (including the BEGIN/END lines) and paste it |
   | API | `PLANTNET_API_KEY` | Your Pl@ntNet API key |
   | API | `FRONTEND_ORIGIN` | Leave empty for now (step 6) |
   | Website | `VITE_API_BASE_URL` | Leave empty for now (step 5) |

4. Click **Apply**. When the API is live, open `https://<your-api-address>/api/v1/health` — you should see `{"status":"ok","plants":880}`. The first start creates the tables and loads the plant data automatically (only when the database is empty — saved gardens are never touched on later deploys).
5. Open the **website** service → **Environment** → set `VITE_API_BASE_URL` to `https://<your-api-address>/api/v1` → **Save**, then **Manual Deploy → Clear build cache & deploy**.
6. Open the **API** service → **Environment** → set `FRONTEND_ORIGIN` to your website address, e.g. `https://plantassure-i3-web.onrender.com` (no slash at the end) → **Save** (it redeploys).
7. Open the website address. That's the link to share.

Use the exact addresses Render shows — if a name is taken, Render adds a suffix.

## Updating later

Push to `main` on GitHub → Render rebuilds automatically.
If the pipeline output changes: run `build_data.py`, commit `backend/data/plants.json`, then empty the `plant` table (or run `python load_data.py` against the Aiven database — note this also clears gardens).

## Privacy notes

- Gardens store only a random id, plant ids and a timestamp. Unchanged gardens are deleted after 90 days.
- The API runs with `--no-access-log`, so it doesn't record visitors' IP addresses. Render's own platform may still log requests — check Render's privacy policy if this matters for your submission.
- Photos are stripped of location data before upload and sent to Pl@ntNet (which may keep them); they are never stored by PlantAssure.
