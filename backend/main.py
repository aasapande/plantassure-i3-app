"""
PlantAssure Iteration 3 -- standalone backend (FastAPI + MySQL).

Plant data comes from the Iteration 3 pipeline (loaded by load_data.py).
Gardens store ONLY a random id, plant ids and a timestamp -- no personal data.

Run:
    .venv/bin/uvicorn main:app --port 8090 --no-access-log
(--no-access-log matters: uvicorn's default access log records client IPs.)
"""
import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from db import cursor
from identify import router as identify_router

API = "/api/v1"
MAX_GARDEN_PLANTS = 100
GARDEN_RETENTION = timedelta(days=90)
CLEANUP_INTERVAL_SECONDS = 3600
CORE_EVIDENCE = ["rating", "origin", "local_records", "traits", "flowering"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CONCERN_BY_RATING = {
    "Very High Risk": "VERY_HIGH",
    "High Risk": "HIGH",
    "Moderately High Risk": "MODERATELY_HIGH",
    "Medium Risk": "MEDIUM",
    "Lower Risk": "LOWER",
}
RATING_BY_CONCERN = {v: k for k, v in CONCERN_BY_RATING.items()}
LEVEL_BY_RECOMMENDATION = {
    "Reconsider Planting": "RECONSIDER_PLANTING",
    "Use Caution": "USE_CAUTION",
    "Lower Concern": "LOWER_CONCERN",
    "Not Assessed": "NOT_ASSESSED",
}
EXPLANATIONS = {
    "Reconsider Planting": "Rated Very High or High risk on the 2022 Advisory List of Environmental Weeds in Victoria.",
    "Use Caution": "Rated Moderately High or Medium risk on the 2022 Advisory List of Environmental Weeds in Victoria.",
    "Lower Concern": "Rated Lower risk on the 2022 Advisory List of Environmental Weeds in Victoria.",
    "Not Assessed": "No exact matching assessment was found in the 2022 Advisory List. This does not mean the plant is free of risk.",
}
PLANT_SQL = """
    SELECT p.*, r.vba100_count, r.vba100_latest_year, r.ala_count, r.ala_latest_year
    FROM plant p JOIN plant_local_records r USING (plant_id)
"""


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- helpers

def concern(row) -> str:
    return CONCERN_BY_RATING.get(row["risk_rating"], "NOT_ASSESSED")


def origin_status(row) -> str | None:
    return row["origin"].upper() if row["origin"] else None


def number(value) -> float | None:
    return None if value is None else float(value)


def height(row) -> str | None:
    lo, hi = number(row["height_min_m"]), number(row["height_max_m"])
    if hi is None:
        return None
    fmt = lambda v: f"{v:g}"
    return f"{fmt(hi)} m" if lo is None or lo == hi else f"{fmt(lo)}–{fmt(hi)} m"


def local_occurrence(row) -> dict:
    count = row["vba100_count"] + row["ala_count"]
    years = [y for y in (row["vba100_latest_year"], row["ala_latest_year"]) if y]
    latest = max(years) if years else None
    return {
        "status": "FOUND" if count else "NOT_FOUND",
        "recordCount": count,
        "latestRecordYear": latest,
        "mostRecentRecordYear": latest,
        "source": "Victorian Biodiversity Atlas + Atlas of Living Australia",
    }


def fetch_plants(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    marks = ",".join(["%s"] * len(ids))
    with cursor() as cur:
        cur.execute(f"{PLANT_SQL} WHERE p.plant_id IN ({marks})", ids)
        return {row["plant_id"]: row for row in cur.fetchall()}


def fetch_plant(plant_id: int) -> dict:
    row = fetch_plants([plant_id]).get(plant_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Plant not found.")
    return row


def summary_item(row) -> dict:
    return {
        "plantId": row["plant_id"],
        "scientificName": row["scientific_name"],
        "commonName": row["common_name"],
        "family": row["family"],
        "imageUrl": None,
    }


def trait_fields(row) -> dict:
    return {
        "growthForm": row["growth_form"],
        "lifeHistory": row["life_history"],
        "woodiness": row["woodiness"],
        "height": height(row),
    }


def passports(ids: list[int]) -> dict[int, dict]:
    rows = fetch_plants(ids)
    if not rows:
        return {}
    marks = ",".join(["%s"] * len(rows))
    months: dict[int, set[int]] = {i: set() for i in rows}
    evidence: dict[int, list[str]] = {i: [] for i in rows}
    with cursor() as cur:
        cur.execute(f"SELECT plant_id, month FROM plant_flowering WHERE plant_id IN ({marks})", list(rows))
        for r in cur.fetchall():
            months[r["plant_id"]].add(r["month"])
        cur.execute(f"SELECT plant_id, evidence_type FROM plant_evidence WHERE plant_id IN ({marks})", list(rows))
        for r in cur.fetchall():
            evidence[r["plant_id"]].append(r["evidence_type"])

    result = {}
    for plant_id, row in rows.items():
        available = evidence[plant_id]
        result[plant_id] = {
            "plant_id": plant_id,
            "scientific_name": row["scientific_name"],
            "common_name": row["common_name"],
            "recommendation": row["recommendation"],
            "origin": row["origin"],
            "establishment": row["establishment"],
            "plant_type": row["plant_type"],
            "traits": {
                "growth_form": row["growth_form"],
                "woodiness": row["woodiness"],
                "life_history": row["life_history"],
                "height_min_m": number(row["height_min_m"]),
                "height_max_m": number(row["height_max_m"]),
            },
            "flowering": {
                "months": [m in months[plant_id] for m in range(1, 13)] if row["flowering_label"] else None,
                "label": row["flowering_label"],
                "sources": row["flowering_sources"],
                "split_pattern": bool(row["flowering_split"]),
            },
            "spread": {
                "resprouting": row["resprouting"],
                "vegetative_spread": row["vegetative_spread"],
                "dispersal": row["dispersal"],
                "seedbank_longevity": row["seedbank_longevity"],
            },
            "wet_soil_tolerance": row["wet_soil_tolerance"],
            "local_records": {
                "vba100_count": row["vba100_count"],
                "vba100_latest_year": row["vba100_latest_year"],
                "ala_count": row["ala_count"],
                "ala_latest_date": str(row["ala_latest_year"]) if row["ala_latest_year"] else None,
            },
            "griis_listed_introduced": bool(row["griis_listed_introduced"]),
            "evidence": {
                "strength": row["evidence_strength"],
                "available": available,
                "missing": [e for e in CORE_EVIDENCE if e not in available],
            },
            "vicflora_url": row["vicflora_url"],
        }
    return result


# ---------------------------------------------------------------- app

def delete_expired_gardens() -> int:
    with cursor() as cur:
        return cur.execute("DELETE FROM garden WHERE updated_at < %s", (now() - GARDEN_RETENTION,))


async def cleanup_loop() -> None:
    while True:
        try:
            delete_expired_gardens()
        except Exception:  # database briefly unavailable: try again next round
            pass
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="PlantAssure Iteration 3 API", lifespan=lifespan)
app.include_router(identify_router)


# ---------------------------------------------------------------- plants

@app.get(f"{API}/plants/search")
def search_plants(q: str = "", limit: int = Query(8, ge=1, le=50)):
    query = q.strip()
    if not query:
        return {"query": query, "items": []}
    like, starts = f"%{query}%", f"{query}%"
    with cursor() as cur:
        cur.execute(
            """SELECT plant_id, scientific_name, common_name, family FROM plant
               WHERE scientific_name LIKE %s OR common_name LIKE %s
               ORDER BY (common_name LIKE %s OR scientific_name LIKE %s) DESC, scientific_name
               LIMIT %s""",
            (like, like, starts, starts, limit),
        )
        return {"query": query, "items": [summary_item(r) for r in cur.fetchall()]}


@app.get(f"{API}/plants")
def catalogue(
    q: str = "",
    environmentalConcern: list[str] = Query(default=[]),
    originStatus: list[str] = Query(default=[]),
    page: int = Query(0, ge=0),
    size: int = Query(12, ge=1, le=100),
    sort: str = "commonName,asc",
):
    where, params = ["p.recommendation <> 'Not Assessed'"], []
    ratings = [RATING_BY_CONCERN[c] for c in environmentalConcern if c in RATING_BY_CONCERN]
    if environmentalConcern:
        where.append(f"p.risk_rating IN ({','.join(['%s'] * len(ratings))})" if ratings else "FALSE")
        params += ratings
    origins = [o.lower() for o in originStatus if o.upper() in {"NATIVE", "INTRODUCED", "UNCERTAIN"}]
    if originStatus:
        where.append(f"p.origin IN ({','.join(['%s'] * len(origins))})" if origins else "FALSE")
        params += origins
    if q.strip():
        where.append("(p.scientific_name LIKE %s OR p.common_name LIKE %s)")
        params += [f"%{q.strip()}%"] * 2
    clause = " AND ".join(where)
    with cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS n FROM plant p WHERE {clause}", params)
        total = cur.fetchone()["n"]
        cur.execute(
            f"""{PLANT_SQL} WHERE {clause}
                ORDER BY p.common_name IS NULL, p.common_name, p.scientific_name
                LIMIT %s OFFSET %s""",
            params + [size, page * size],
        )
        rows = cur.fetchall()
    return {
        "items": [
            {
                **summary_item(r),
                "environmentalConcern": concern(r),
                "originStatus": origin_status(r),
                "growthForm": r["growth_form"],
                "lifeHistory": r["life_history"],
                "height": height(r),
            }
            for r in rows
        ],
        "page": page,
        "size": size,
        "totalElements": total,
        "totalPages": (total + size - 1) // size,
        "sort": sort,
    }


@app.get(f"{API}/plants/compare")
def compare(plantIds: str):
    try:
        ids = [int(x) for x in plantIds.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="plantIds must be numbers.") from None
    if not 2 <= len(ids) <= 3 or len(set(ids)) != len(ids):
        raise HTTPException(status_code=400, detail="Compare two or three different plants.")
    rows = fetch_plants(ids)
    if len(rows) != len(ids):
        raise HTTPException(status_code=404, detail="Plant not found.")
    return {
        "plants": [
            {
                **summary_item(rows[i]),
                "environmentalConcern": concern(rows[i]),
                "legalStatus": "UNAVAILABLE",
                "originStatus": origin_status(rows[i]),
                **trait_fields(rows[i]),
                "localOccurrence": local_occurrence(rows[i]),
            }
            for i in ids
        ]
    }


@app.get(f"{API}/plants/passports")
def passports_for(ids: str = ""):
    try:
        plant_ids = [int(x) for x in ids.split(",") if x.strip()][:MAX_GARDEN_PLANTS]
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be numbers.") from None
    return {str(k): v for k, v in passports(plant_ids).items()}


@app.get(f"{API}/plants/{{plant_id}}/assessment")
def assessment(plant_id: int):
    row = fetch_plant(plant_id)
    establishment = row["establishment"]
    return {
        "plant": summary_item(row),
        "originStatus": origin_status(row),
        "victorianEstablishment": {
            "status": establishment.upper() if establishment else None,
            "label": establishment.capitalize() if establishment else None,
        },
        "localOccurrence": local_occurrence(row),
        "environmentalConcern": {"status": concern(row), "source": "2022 Advisory List of Environmental Weeds in Victoria"},
        "legalStatus": "UNAVAILABLE",
        "recommendation": {
            "level": LEVEL_BY_RECOMMENDATION[row["recommendation"]],
            "displayLabel": row["recommendation"],
            "explanation": EXPLANATIONS[row["recommendation"]],
        },
    }


@app.get(f"{API}/plants/{{plant_id}}/passport")
def passport(plant_id: int):
    result = passports([plant_id]).get(plant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Plant not found.")
    return result


@app.get(f"{API}/plants/{{plant_id}}/alternatives")
def alternatives(plant_id: int, limit: int = Query(6, ge=1, le=20)):
    row = fetch_plant(plant_id)
    status = row["alternatives_status"]
    if status.startswith("not_applicable"):
        status = "not_applicable"
    with cursor() as cur:
        cur.execute(
            "SELECT alternative_id FROM plant_alternative WHERE plant_id = %s ORDER BY rank_order LIMIT %s",
            (plant_id, limit),
        )
        alt_ids = [r["alternative_id"] for r in cur.fetchall()]
    alts = fetch_plants(alt_ids)
    reasons = ["Same growth form", "Same life-history category", "Same woodiness", "Similar mature height"]
    return {
        "status": status,
        "currentPlant": {**summary_item(row), "environmentalConcern": concern(row), **trait_fields(row)},
        "alternatives": [
            {
                **summary_item(alts[i]),
                "environmentalConcern": concern(alts[i]),
                "originStatus": origin_status(alts[i]),
                "legalStatus": "UNAVAILABLE",
                **trait_fields(alts[i]),
                "matchReasons": reasons,
            }
            for i in alt_ids
            if i in alts
        ],
    }


@app.get(f"{API}/insights")
def insights():
    with cursor() as cur:
        cur.execute(
            """SELECT f.month, COUNT(*) AS n FROM plant_flowering f JOIN plant p USING (plant_id)
               WHERE p.recommendation IN ('Reconsider Planting','Use Caution') GROUP BY f.month"""
        )
        by_month = {r["month"]: r["n"] for r in cur.fetchall()}
        cur.execute(
            """SELECT COUNT(*) AS n FROM plant WHERE flowering_label IS NOT NULL
               AND recommendation IN ('Reconsider Planting','Use Caution')"""
        )
        risky_with_flowering = cur.fetchone()["n"]
        cur.execute(
            """SELECT origin, COUNT(*) AS n FROM plant
               WHERE recommendation IN ('Reconsider Planting','Use Caution') GROUP BY origin"""
        )
        origin = {(r["origin"] or "unknown"): r["n"] for r in cur.fetchall()}
        cur.execute(
            """SELECT plant_type, COUNT(*) AS total,
                      SUM(recommendation IN ('Reconsider Planting','Use Caution')) AS risky
               FROM plant WHERE plant_type IS NOT NULL GROUP BY plant_type HAVING COUNT(*) >= 30
               ORDER BY risky / total DESC"""
        )
        types = [
            {"type": r["plant_type"], "total": r["total"], "risky": int(r["risky"]),
             "pct": round(100 * int(r["risky"]) / r["total"])}
            for r in cur.fetchall()
        ]
    return {
        "flowering": {
            "months": MONTHS,
            "counts": [by_month.get(m, 0) for m in range(1, 13)],
            "total": risky_with_flowering,
        },
        "origin": {"introduced": origin.get("introduced", 0), "native": origin.get("native", 0),
                   "total": sum(origin.values())},
        "plantTypes": types,
        "minGroupSize": 30,
    }


# ---------------------------------------------------------------- gardens

class GardenIn(BaseModel):
    plantIds: list[int] = Field(default_factory=list, max_length=MAX_GARDEN_PLANTS)

    @field_validator("plantIds")
    @classmethod
    def positive_unique(cls, ids: list[int]) -> list[int]:
        if any(i <= 0 for i in ids):
            raise ValueError("plantIds must be positive integers.")
        return list(dict.fromkeys(ids))  # drop duplicates, keep order


def parse_garden_id(garden_id: str) -> str:
    """Only real random (version 4) UUIDs are accepted; anything else is a
    404, so gardens cannot be found by guessing ids like 1, 2, 3."""
    try:
        parsed = uuid.UUID(garden_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Garden not found.") from None
    if parsed.version != 4 or str(parsed) != garden_id.lower():
        raise HTTPException(status_code=404, detail="Garden not found.")
    return str(parsed)


def check_plants_exist(cur, ids: list[int]) -> None:
    if not ids:
        return
    cur.execute(f"SELECT COUNT(*) AS n FROM plant WHERE plant_id IN ({','.join(['%s'] * len(ids))})", ids)
    if cur.fetchone()["n"] != len(ids):
        raise HTTPException(status_code=422, detail="Unknown plant id.")


def save_plants(cur, garden_id: str, ids: list[int]) -> None:
    cur.execute("DELETE FROM garden_plant WHERE garden_id = %s", (garden_id,))
    cur.executemany(
        "INSERT INTO garden_plant (garden_id, plant_id, position) VALUES (%s,%s,%s)",
        [(garden_id, pid, pos) for pos, pid in enumerate(ids)],
    )


def load_garden(cur, garden_id: str) -> dict:
    cur.execute("SELECT updated_at FROM garden WHERE garden_id = %s", (garden_id,))
    row = cur.fetchone()
    if row is None or row["updated_at"] < now() - GARDEN_RETENTION:
        raise HTTPException(status_code=404, detail="Garden not found.")
    cur.execute("SELECT plant_id FROM garden_plant WHERE garden_id = %s ORDER BY position", (garden_id,))
    return {
        "gardenId": garden_id,
        "plantIds": [r["plant_id"] for r in cur.fetchall()],
        "updatedAt": row["updated_at"].isoformat(),
    }


@app.post(f"{API}/gardens", status_code=201)
def create_garden(body: GardenIn):
    garden_id = str(uuid.uuid4())
    with cursor() as cur:
        check_plants_exist(cur, body.plantIds)
        cur.execute("INSERT INTO garden (garden_id, updated_at) VALUES (%s, %s)", (garden_id, now()))
        save_plants(cur, garden_id, body.plantIds)
        return load_garden(cur, garden_id)


@app.get(f"{API}/gardens/{{garden_id}}")
def get_garden(garden_id: str):
    with cursor() as cur:
        return load_garden(cur, parse_garden_id(garden_id))


@app.put(f"{API}/gardens/{{garden_id}}")
def update_garden(garden_id: str, body: GardenIn):
    garden_id = parse_garden_id(garden_id)
    with cursor() as cur:
        load_garden(cur, garden_id)  # 404 if missing or expired
        check_plants_exist(cur, body.plantIds)
        cur.execute("UPDATE garden SET updated_at = %s WHERE garden_id = %s", (now(), garden_id))
        save_plants(cur, garden_id, body.plantIds)
        return load_garden(cur, garden_id)


@app.delete(f"{API}/gardens/{{garden_id}}", status_code=204)
def delete_garden(garden_id: str):
    garden_id = parse_garden_id(garden_id)
    with cursor() as cur:
        if not cur.execute("DELETE FROM garden WHERE garden_id = %s", (garden_id,)):
            raise HTTPException(status_code=404, detail="Garden not found.")
    return Response(status_code=204)
