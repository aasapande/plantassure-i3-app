# PlantAssure — My Garden API Documentation

Version 1.0 · Iteration 3 · Epic: My Garden (US 1–9)

- **Base path:** `/api/v1`
- **Format:** JSON (`Content-Type: application/json`)
- **Authentication:** none. Gardens are anonymous. Changing or deleting a garden needs the
  garden's private edit key in a request header (see below).
- **Plant ids** are `species_data.id`.
- **Working reference:** the same endpoints are live at
  https://plantassure-i3-api.onrender.com/docs (interactive; first load can take ~60 s).
  That prototype uses different plant ids and returns errors as `{ "detail": … }` with 422 for
  bad plant lists; this document uses our backend's ids and error format.

---

## Summary

| # | Method | Endpoint | Purpose | Edit key |
|---|---|---|---|---|
| 1 | `POST` | `/api/v1/gardens` | Create a saved garden | No |
| 2 | `GET` | `/api/v1/gardens/{gardenId}` | Get a garden | No |
| 3 | `PUT` | `/api/v1/gardens/{gardenId}` | Replace a garden's plant list | **Yes** |
| 4 | `DELETE` | `/api/v1/gardens/{gardenId}` | Delete a garden | **Yes** |
| 5 | `GET` | `/api/v1/plants/passports?ids=…` | Plant details for many plants | No |
| 6 | `GET` | `/api/v1/plants/{plantId}/passport` | Plant details for one plant | No |
| — | `GET` | `/api/v1/plants/{plantId}/alternatives` | Swap ideas (**existing endpoint, unchanged**) | No |

### Edit key header

```
X-Garden-Edit-Token: <editToken>
```

Required for `PUT` and `DELETE`. `GET` never needs it, which is what makes the share link
view-only.

### Error format

All errors use the existing `ErrorResponse`:

```json
{
  "code": "GARDEN_NOT_FOUND",
  "message": "This garden link is no longer available.",
  "path": "/api/v1/gardens/e1f80156-ccb1-44c4-9961-89b9904c39ae"
}
```

| HTTP | `code` | `message` | When |
|---|---|---|---|
| 400 | `INVALID_GARDEN_PLANTS` | plantIds must contain up to 100 existing plant IDs. | Bad `plantIds` |
| 400 | `INVALID_REQUEST` | ids must be numbers. | Bad `ids` on endpoint 5 |
| 403 | `GARDEN_EDIT_FORBIDDEN` | You can view this garden but not change it. | Edit key missing or wrong |
| 404 | `GARDEN_NOT_FOUND` | This garden link is no longer available. | Garden missing, deleted, expired, or id not a UUID v4 |
| 404 | `PLANT_NOT_FOUND` | Plant not found. | Endpoint 6, unknown plant |

---

## 1. Create a garden

`POST /api/v1/gardens`

Called when the user clicks **“Get a private link”** (AC 4.1).

**Request body**

```json
{ "plantIds": [3, 7, 120] }
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `plantIds` | array of integers | No (missing = `[]`) | Max 100 items. Each must be a positive, existing `species_data.id`. Duplicates are removed, keeping the first position. Order is kept. |

**Response — `201 Created`**

```json
{
  "gardenId": "e1f80156-ccb1-44c4-9961-89b9904c39ae",
  "plantIds": [3, 7, 120],
  "updatedAt": "2026-09-29T11:55:39",
  "editToken": "q1v6mB0kq7yJ3d1tL0Hn9o0B6zQy1c2w8oYxQbq3m9E"
}
```

| Field | Type | Notes |
|---|---|---|
| `gardenId` | string (UUID v4) | Created by the server with a secure random generator |
| `plantIds` | array of integers | After removing duplicates |
| `updatedAt` | string | UTC, ISO-8601, seconds precision |
| `editToken` | string | 32 random bytes, URL-safe Base64 (43 chars). **Returned only in this response.** The server stores only its SHA-256 hash. |

**Errors:** `400 INVALID_GARDEN_PLANTS`

---

## 2. Get a garden

`GET /api/v1/gardens/{gardenId}`

Used when opening the share link or the edit link (US 5, US 6).

| Path parameter | Type | Notes |
|---|---|---|
| `gardenId` | string | Must be a UUID v4. Anything else returns 404. |

**Response — `200 OK`**

```json
{
  "gardenId": "e1f80156-ccb1-44c4-9961-89b9904c39ae",
  "plantIds": [3, 7, 120],
  "updatedAt": "2026-09-29T11:55:39"
}
```

- Never includes `editToken`.
- `plantIds` are in the order the owner added them.

**Errors:** `404 GARDEN_NOT_FOUND` (also returned for gardens not changed for 90 days, even if
not yet deleted)

---

## 3. Update a garden

`PUT /api/v1/gardens/{gardenId}`

Auto-save after any change (AC 4.2), and **“Clear my garden”** (AC 8.1). **Replaces** the whole
list; it does not add to it.

**Headers:** `X-Garden-Edit-Token: <editToken>` (required)

**Request body**

```json
{ "plantIds": [3, 120] }
```

Same rules as endpoint 1. An empty list `[]` is allowed: the garden and both links stay valid.

**Response — `200 OK`:** same as endpoint 2, with a new `updatedAt`. Every successful update
resets the 90-day expiry.

**Errors (checked in this order)**

1. `404 GARDEN_NOT_FOUND`
2. `403 GARDEN_EDIT_FORBIDDEN`
3. `400 INVALID_GARDEN_PLANTS`

---

## 4. Delete a garden

`DELETE /api/v1/gardens/{gardenId}`

**“Delete saved garden”** (AC 8.2).

**Headers:** `X-Garden-Edit-Token: <editToken>` (required)

**Response — `204 No Content`** (no body). Afterwards, endpoints 2–4 return 404 for this id, so
both the share link and the edit link stop working.

**Errors:** `404 GARDEN_NOT_FOUND`, `403 GARDEN_EDIT_FORBIDDEN`

---

## 5. Get plant passports (many)

`GET /api/v1/plants/passports?ids=3,7,120`

The garden page calls this once with all its plant ids to draw the plant cards, the check-up
stats, the risk tier bar and the tips (US 2, US 3, US 9).

| Query parameter | Type | Notes |
|---|---|---|
| `ids` | string | Comma-separated plant ids. Only the first 100 are used. Unknown ids are left out (no error). |

**Response — `200 OK`:** an object keyed by plant id (as a string). Each value is a
[Plant passport](#plant-passport-object).

```json
{
  "3": { "plant_id": 3, "scientific_name": "Acacia baileyana", "...": "..." },
  "7": { "plant_id": 7, "scientific_name": "Acacia dealbata", "...": "..." }
}
```

**Errors:** `400 INVALID_REQUEST` if `ids` contains something that isn't a number.

---

## 6. Get plant passport (one)

`GET /api/v1/plants/{plantId}/passport`

**Response — `200 OK`:** one [Plant passport](#plant-passport-object).

**Errors:** `404 PLANT_NOT_FOUND`

---

## Plant passport object

Field names are **snake_case** (unlike other endpoints) so the existing frontend garden page
works unchanged. In Java: `@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)`.

```json
{
  "plant_id": 3,
  "scientific_name": "Acacia baileyana",
  "common_name": "Cootamundra Wattle",
  "recommendation": "Use Caution",
  "origin": "introduced",
  "establishment": "naturalised",
  "plant_type": "Tree",
  "traits": {
    "growth_form": "shrub tree",
    "woodiness": "woody",
    "life_history": "perennial",
    "height_min_m": 3.0,
    "height_max_m": 10.0
  },
  "flowering": {
    "months": [false, false, false, false, false, true, true, true, true, false, false, false],
    "label": "Jun–Sep",
    "sources": 4,
    "split_pattern": false
  },
  "spread": {
    "resprouting": null,
    "vegetative_spread": null,
    "dispersal": "ants",
    "seedbank_longevity": null
  },
  "wet_soil_tolerance": null,
  "local_records": {
    "vba100_count": 2,
    "vba100_latest_year": 2000,
    "ala_count": 12,
    "ala_latest_date": "2026-04-25"
  },
  "griis_listed_introduced": true,
  "evidence": {
    "strength": "Strong",
    "available": ["rating", "origin", "local_records", "traits", "flowering", "griis"],
    "missing": []
  },
  "vicflora_url": "https://vicflora.rbg.vic.gov.au/flora/taxon/238b3bfd-4a0c-4638-b928-485897ec580d"
}
```

| Field | Type | Values / source | Used for |
|---|---|---|---|
| `plant_id` | integer | `species_data.id` | |
| `scientific_name` | string | `species_data` | Card |
| `common_name` | string / null | Iteration 3 name, else `species_data.vernacular_name` | Card |
| `recommendation` | string | `Reconsider Planting`, `Use Caution`, `Lower Concern`, `Not Assessed`. **Same rule as the assessment page:** Very High/High → Reconsider Planting; Moderately High/Medium → Use Caution; Lower → Lower Concern; otherwise Not Assessed | Risk badge, tier bar, “need attention” (AC 2.1–2.2, 3.1) |
| `origin` | string / null | `native`, `introduced` (lower case) | “Native to Victoria” stat; Growing tips rule (AC 2.1, 3.4) |
| `establishment` | string / null | `species_data.degree_of_establishment` | |
| `plant_type` | string / null | e.g. `Tree`, `Shrub`, `Herb`, `Grass` | Growing tips heading |
| `traits.*` | string / number / null | `species_data` | Tips |
| `flowering.months` | 12 booleans (Jan–Dec) / null | null when no flowering data | |
| `flowering.label` | string / null | e.g. `Jun–Sep` | Flowering window “where known” (AC 3.1) |
| `flowering.sources` | integer | 0–4 | |
| `flowering.split_pattern` | boolean | | |
| `spread.*` | string / null | AusTraits | Plant-specific containment tips (AC 3.2) |
| `wet_soil_tolerance` | string / null | AusTraits | Tips |
| `local_records.*` | integer / string / null | `species_data` VBA and ALA columns | Tips |
| `griis_listed_introduced` | boolean | `species_data.griis_listed` | |
| `evidence.strength` | string | `Strong`, `Moderate`, `Limited` | |
| `evidence.available` / `missing` | array of strings | `rating`, `origin`, `local_records`, `traits`, `flowering`, `griis` | |
| `vicflora_url` | string / null | | |

Data for `common_name`, `plant_type`, `flowering`, `spread`, `wet_soil_tolerance`, `evidence`
and `vicflora_url` comes from the new `species_passport` table (see below).

---

## Swap ideas (existing endpoint)

`GET /api/v1/plants/{plantId}/alternatives?limit=3`

No change needed. The garden page uses it for:

- **“Find a swap”** (AC 3.3): opens the existing Find a Better Plant page for that plant.
- **Print / PDF** (AC 9.1): prints up to 3 alternative names as “Swap ideas”. If the list is
  empty it prints “No close match found. Ask a local indigenous nursery for a native
  alternative.”

---

## Database

```sql
CREATE TABLE garden (
  garden_id        CHAR(36) NOT NULL,   -- UUID v4
  updated_at       DATETIME NOT NULL,   -- UTC, for the 90-day expiry
  edit_token_hash  CHAR(64) NOT NULL,   -- SHA-256 hex of the edit key (key never stored)
  PRIMARY KEY (garden_id),
  KEY idx_garden_updated (updated_at)
);

CREATE TABLE garden_plant (
  garden_id  CHAR(36)          NOT NULL,
  plant_id   BIGINT UNSIGNED   NOT NULL,  -- species_data.id
  position   SMALLINT UNSIGNED NOT NULL,  -- order the user added plants
  PRIMARY KEY (garden_id, plant_id),
  FOREIGN KEY (garden_id) REFERENCES garden (garden_id) ON DELETE CASCADE,
  FOREIGN KEY (plant_id)  REFERENCES species_data (id)
);
```

`species_passport` (Iteration 3 plant data for endpoints 5–6) is created and filled by
`spring-boot/species_passport_i3.sql`: 880 rows, matched to `species_data` by
`scientific_name`.

---

## Rules

| Rule | Detail |
|---|---|
| Garden expiry | Gardens not updated for **90 days** are treated as not found and deleted by an hourly job. |
| Max plants | 100 per garden |
| Edit key check | Compare SHA-256 hashes in constant time (`MessageDigest.isEqual`). |
| Privacy | Store only `garden_id`, `updated_at`, `edit_token_hash` and plant ids. No names, emails or IP addresses. Never log the edit key. |
| CORS | Allow `GET, POST, PUT, DELETE, OPTIONS` and the `X-Garden-Edit-Token` header. |

---

## How the frontend uses the API

| Link | Format | API calls |
|---|---|---|
| Share link (view only) | `/garden/{gardenId}` | `GET` only |
| Private edit link | `/garden/{gardenId}#edit={editToken}` | `GET`, then `PUT`/`DELETE` with the header |

- Adding a plant to the garden (US 1) needs **no API call**. The list is kept in the browser
  until the user clicks “Get a private link” (endpoint 1).
- After that, every change is sent with `PUT` about 0.6 s later.
- “Copy these plants to my garden” (AC 6.3–6.6) makes **no call** to the shared garden.
- The frontend only checks the status codes **403** (stop saving) and **404** (“This garden
  link is no longer available”).

---

## Example requests (curl)

```bash
BASE=http://localhost:8080/api/v1

# 1. Create -> 201 (copy gardenId and editToken from the response)
curl -X POST $BASE/gardens -H 'Content-Type: application/json' -d '{"plantIds":[3,7]}'

# 2. Get -> 200
curl $BASE/gardens/<gardenId>

# 3. Update without key -> 403; with key -> 200
curl -X PUT $BASE/gardens/<gardenId> -H 'Content-Type: application/json' -d '{"plantIds":[3]}'
curl -X PUT $BASE/gardens/<gardenId> -H 'Content-Type: application/json' \
     -H 'X-Garden-Edit-Token: <editToken>' -d '{"plantIds":[3]}'

# 4. Delete -> 204, then Get -> 404
curl -X DELETE $BASE/gardens/<gardenId> -H 'X-Garden-Edit-Token: <editToken>'

# 5. Passports -> 200
curl "$BASE/plants/passports?ids=3,7"
```
