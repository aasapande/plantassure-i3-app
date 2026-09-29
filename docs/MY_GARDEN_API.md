# My Garden — API documentation

This covers everything the My Garden epic needs: the four garden endpoints, the two plant
endpoints the garden page reads from, the database tables, and the rules the frontend follows.

- **Live base URL:** `https://plantassure-i3-api.onrender.com/api/v1`
- **Interactive docs (try requests in the browser):** `https://plantassure-i3-api.onrender.com/docs`
- **Local base URL:** `http://localhost:8090/api/v1`
- **Format:** JSON in, JSON out (`Content-Type: application/json`)
- **No login.** Gardens are anonymous. Only a random id, plant ids and a timestamp are stored.

> The free Render server sleeps when unused. The first request after a while can take up to
> ~60 seconds, so use a generous client timeout (the reference app uses 70 s).

---

## 1. Garden endpoints

| Method | Path | Purpose | Needs edit key? |
|---|---|---|---|
| `POST` | `/gardens` | Create a saved garden (“Get a private link”) | No |
| `GET` | `/gardens/{gardenId}` | Read a garden (share link and edit link) | No |
| `PUT` | `/gardens/{gardenId}` | Replace the garden’s plant list (auto-save) | **Yes** |
| `DELETE` | `/gardens/{gardenId}` | Delete the saved garden | **Yes** |

The edit key is sent in a request header:

```
X-Garden-Edit-Token: <editToken>
```

### 1.1 `POST /gardens` — create a garden

Used by **US 4 / AC 4.1** (“Get a private link”).

**Request body**

```json
{ "plantIds": [46, 602, 287] }
```

| Field | Type | Rules |
|---|---|---|
| `plantIds` | array of integers | 0–100 items, each a positive plant id that exists. Duplicates are removed (first position kept). Order is kept. |

**Response `201 Created`**

```json
{
  "gardenId": "e1f80156-ccb1-44c4-9961-89b9904c39ae",
  "plantIds": [46, 602, 287],
  "updatedAt": "2026-09-29T11:55:39",
  "editToken": "q1v6mB0kq7yJ3d1tL0Hn9o0B6zQy1c2w8oYxQbq3m9E"
}
```

- `gardenId` is a random UUID v4.
- `editToken` is returned **only here, once**. The server keeps only its SHA-256 hash and can
  never show it again. The frontend must store it (see section 4).

**Errors:** `422` if a plant id doesn’t exist, is not positive, or there are more than 100.

### 1.2 `GET /gardens/{gardenId}` — read a garden

Used by **US 5** (edit link), **US 6** (share link) and **AC 6.5**.

**Response `200 OK`**

```json
{
  "gardenId": "e1f80156-ccb1-44c4-9961-89b9904c39ae",
  "plantIds": [46, 602, 287],
  "updatedAt": "2026-09-29T11:55:39"
}
```

- Never returns the edit key.
- `plantIds` are in the order the owner added them.

**Errors:** `404 {"detail": "Garden not found."}` when the garden doesn’t exist, was deleted,
was not changed for 90 days, or the id is not a valid UUID v4. The frontend shows
“This garden link is no longer available” (**AC 5.2**).

### 1.3 `PUT /gardens/{gardenId}` — save changes

Used by **AC 4.2** (auto-save), **AC 8.1** (Clear keeps the garden) and copying into a saved
garden (**AC 6.4**). It **replaces** the whole list, it doesn’t add to it.

**Headers:** `X-Garden-Edit-Token: <editToken>`

**Request body:** same as `POST` — `{ "plantIds": [46, 287] }`. An empty list is allowed
(that is what “Clear my garden” sends; the garden and both links stay valid).

**Response `200 OK`:** same shape as `GET`, with a new `updatedAt`. Every successful save resets
the 90-day expiry.

**Errors**

| Code | When | What the frontend does |
|---|---|---|
| `403` | Header missing or wrong key | Stops syncing; list stays in the browser |
| `404` | Garden deleted or expired | Shows “This garden link is no longer available” |
| `422` | Unknown / invalid plant id, or more than 100 | Shows a save error |

### 1.4 `DELETE /gardens/{gardenId}` — delete the saved garden

Used by **AC 8.2**.

**Headers:** `X-Garden-Edit-Token: <editToken>`

**Response:** `204 No Content`. After this, `GET` on the same id returns `404`, so both the
share link and the edit link stop working. The plant list stays in the browser (the frontend
does not clear it).

**Errors:** `403` wrong/missing key, `404` already gone (the frontend treats this as success).

---

## 2. Plant endpoints used by My Garden

### 2.1 `GET /plants/passports?ids=46,602,287` — details for many plants at once

The garden page calls this once with all its plant ids, to draw the cards, the check-up stats,
the tier bar and the tips. Up to 100 ids; unknown ids are simply left out.

**Response `200 OK`** — an object keyed by plant id (as a string):

```json
{
  "46": {
    "plant_id": 46,
    "scientific_name": "Agapanthus praecox",
    "common_name": "Agapanthus",
    "recommendation": "Reconsider Planting",
    "origin": "introduced",
    "establishment": null,
    "plant_type": "Herb",
    "traits": {
      "growth_form": "herb", "woodiness": "herbaceous", "life_history": "perennial",
      "height_min_m": 1.0, "height_max_m": 1.0
    },
    "flowering": {
      "months": [true, false, false, false, false, false, false, false, false, false, false, true],
      "label": "Dec–Jan",
      "sources": 1,
      "split_pattern": false
    },
    "spread": {
      "resprouting": null, "vegetative_spread": null,
      "dispersal": null, "seedbank_longevity": null
    },
    "wet_soil_tolerance": null,
    "local_records": {
      "vba100_count": 3, "vba100_latest_year": 2009,
      "ala_count": 4, "ala_latest_date": "2025"
    },
    "griis_listed_introduced": true,
    "evidence": {
      "strength": "Strong",
      "available": ["rating", "origin", "local_records", "traits", "flowering", "griis"],
      "missing": []
    },
    "vicflora_url": "https://vicflora.rbg.vic.gov.au/flora/taxon/9af576d9-07e9-4491-84b0-3de71adbe509"
  }
}
```

Key fields for the epic:

| Field | Values | Used for |
|---|---|---|
| `recommendation` | `Reconsider Planting`, `Use Caution`, `Lower Concern`, `Not Assessed` | Risk badge, tier bar (**AC 2.2**), which buttons show (**US 3**) |
| `origin` | `native`, `introduced`, or `null` | “Native to Victoria” stat (**AC 2.1**), Growing tips rule (**AC 3.4**) |
| `flowering.label` | e.g. `"Dec–Jan"`, or `null` | Flowering window “where known” (**AC 3.1**) |
| `spread.*`, `wet_soil_tolerance`, `traits.*` | text or `null` | Plant-specific containment / growing tips (**AC 3.2**) |

There is also `GET /plants/{plantId}/passport`, which returns the same object for one plant
(`404` if the plant doesn’t exist).

### 2.2 `GET /plants/{plantId}/alternatives?limit=3` — swap ideas

Used by the PDF swap ideas (**AC 9.1**). “Find a swap” (**AC 3.3**) just opens the existing
Find a Better Plant page for that plant id. `limit` is 1–20 (default 6).

**Response `200 OK`** (trimmed):

```json
{
  "status": "matched",
  "currentPlant": { "plantId": 46, "commonName": "Agapanthus", "scientificName": "Agapanthus praecox", "...": "..." },
  "alternatives": [
    {
      "plantId": 82,
      "commonName": "Nodding Chocolate-lily",
      "scientificName": "Arthropodium fimbriatum",
      "environmentalConcern": "NOT_ASSESSED",
      "originStatus": "NATIVE",
      "growthForm": "herb",
      "height": "0.09–1 m",
      "matchReasons": ["Same growth form", "Same life-history category", "Same woodiness", "Similar mature height"]
    }
  ]
}
```

`status` is one of `matched`, `no_strict_match_found`, `insufficient_trait_data`,
`not_applicable`. When `alternatives` is empty the PDF prints: “No close match found. Ask a
local indigenous nursery for a native alternative.” Unrated plants are only offered as swaps if
they are native to Victoria.

---

## 3. Database tables

Only these two tables are written by My Garden. No names, emails, IP addresses or other personal
data.

```sql
CREATE TABLE garden (
  garden_id        CHAR(36) NOT NULL,   -- random UUID v4
  updated_at       DATETIME NOT NULL,   -- for the 90-day expiry
  edit_token_hash  CHAR(64) NULL,       -- SHA-256 of the edit key (key never stored)
  PRIMARY KEY (garden_id),
  KEY idx_garden_updated (updated_at)
);

CREATE TABLE garden_plant (
  garden_id  CHAR(36)          NOT NULL,
  plant_id   INT UNSIGNED      NOT NULL,
  position   SMALLINT UNSIGNED NOT NULL,  -- keeps the user's order
  PRIMARY KEY (garden_id, plant_id),      -- no duplicates
  FOREIGN KEY (garden_id) REFERENCES garden (garden_id) ON DELETE CASCADE,
  FOREIGN KEY (plant_id)  REFERENCES plant (plant_id)
);
```

**Expiry:** once an hour the server runs
`DELETE FROM garden WHERE updated_at < NOW() - INTERVAL 90 DAY`. Reads also treat anything older
than 90 days as not found, so an expired garden is never returned even between clean-ups.

---

## 4. Rules the frontend follows

These aren’t API calls, but the acceptance criteria depend on them.

**Browser storage (US 1).** The garden lives in `localStorage` under
`plantassure.garden.v2`:

```json
{ "plants": [{ "plantId": 46, "scientificName": "Agapanthus praecox", "commonName": "Agapanthus" }],
  "gardenId": "e1f8…", "editToken": "q1v6…" }
```

Adding a plant needs no API call. The server is only involved after “Get a private link”.

**The two links (US 4, 6, 7).**

| Link | Format | Who can do what |
|---|---|---|
| Share link | `/garden/{gardenId}` | Anyone can view. No edit key. |
| Private edit link | `/garden/{gardenId}#edit={editToken}` | Can view, change and delete. |

- The key is after `#`, so browsers never send it to any server or put it in server logs.
- When an edit link is opened, the page reads the key, saves it in `localStorage`, then removes
  the `#edit=…` part from the address bar (**AC 7.2**).
- Opening an edit link on another device replaces that browser’s list with the saved garden
  (**AC 5.1**).
- Opening a share link without a key shows the read-only view (**US 6**). The one exception: if
  that browser already owns the garden, it shows the owner view. Test US 6 in a private window.

**Auto-save (AC 4.2).** When the list changes and a saved garden exists, wait ~600 ms, then send
`PUT` with the full list. Status shows “Saving…” then “Saved”.

**Copy to my garden (AC 6.3–6.6).** Pure frontend: add each shared plant to the local list,
skipping ones already there. No request touches the shared garden. If the viewer has their own
saved garden, the normal auto-save `PUT` sends their updated list to **their** garden only.

**Which buttons each plant shows (US 3).**

| `recommendation` | `origin` | Buttons |
|---|---|---|
| Reconsider Planting / Use Caution | any | “Find a swap” + “How to keep it contained” |
| Lower Concern | any | “Growing tips” |
| Not Assessed | `native` | “Growing tips” |
| Not Assessed | not native | none |

“Need attention” (**AC 2.1**) = count of Reconsider Planting + Use Caution.

**Containment steps (AC 3.2).** Plant-specific lines are built from `spread.*`,
`wet_soil_tolerance` and `traits`, followed by the general “For any risky plant” checklist:

1. Bag seed heads and put them in the rubbish bin, not green waste
2. Never dump clippings near bushland, parks or creeks
3. Check nearby for seedlings and pull them out early

(The reference wording is in `frontend/src/utils/passportPresentation.ts`.)

**Print / PDF (US 9).** Uses the browser’s print dialog (`window.print()`). Print CSS hides the
link panel and buttons, and shows every plant’s tips (even collapsed ones) plus a “Swap ideas:”
line with up to 3 names from `/alternatives?limit=3` for each risky plant.

---

## 5. Error format

All errors are JSON:

```json
{ "detail": "You can view this garden but not change it." }
```

Validation errors (`422`) use FastAPI’s standard format, where `detail` is a list describing
each invalid field.

## 6. Quick test with curl

```bash
BASE=https://plantassure-i3-api.onrender.com/api/v1

# Create (save editToken from the response)
curl -s -X POST $BASE/gardens -H 'Content-Type: application/json' -d '{"plantIds":[46,287]}'

# Read (share link)
curl -s $BASE/gardens/<gardenId>

# Update: without key -> 403, with key -> 200
curl -s -X PUT $BASE/gardens/<gardenId> -H 'Content-Type: application/json' -d '{"plantIds":[46]}'
curl -s -X PUT $BASE/gardens/<gardenId> -H 'Content-Type: application/json' \
     -H 'X-Garden-Edit-Token: <editToken>' -d '{"plantIds":[46]}'

# Delete -> 204, then GET -> 404
curl -s -X DELETE $BASE/gardens/<gardenId> -H 'X-Garden-Edit-Token: <editToken>'
```
