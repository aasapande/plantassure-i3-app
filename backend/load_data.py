"""
Creates the tables (db/schema.sql) and loads data/plants.json into MySQL.

    python3 build_data.py      # pipeline output -> data/plants.json
    python3 load_data.py       # data/plants.json -> MySQL

Re-running drops and reloads everything, including gardens.
"""
import json
import re
import sys
from pathlib import Path

from db import cursor

HERE = Path(__file__).resolve().parent
ORIGINS = {"native", "introduced", "uncertain"}


def year(value) -> int | None:
    text = str(value or "")[:4]
    return int(text) if text.isdigit() else None


def run_schema(cur) -> None:
    # Strip "--" comments first: they may contain semicolons.
    text = re.sub(r"--[^\n]*", "", (HERE / "db" / "schema.sql").read_text(encoding="utf-8"))
    for statement in text.split(";"):
        if statement.strip():
            cur.execute(statement)


def load(database: str | None = None) -> dict:
    plants = json.loads((HERE / "data" / "plants.json").read_text(encoding="utf-8"))
    with cursor(database) as cur:
        run_schema(cur)
        cur.executemany(
            """INSERT INTO plant (plant_id, scientific_name, common_name, common_name_source, family, origin,
                 establishment, risk_rating, recommendation, plant_type, growth_form, woodiness, life_history,
                 height_min_m, height_max_m, flowering_label, flowering_sources, flowering_split, resprouting,
                 vegetative_spread, dispersal, seedbank_longevity, wet_soil_tolerance, griis_listed_introduced,
                 evidence_strength, alternatives_status, vicflora_url)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [
                (
                    p["id"], p["scientific_name"], p["common_name"], p["common_name_source"], p["family"],
                    p["origin"] if p["origin"] in ORIGINS else None,
                    None if p["establishment"] in (None, "Not available") else p["establishment"],
                    p["risk_rating"], p["recommendation"], p["plant_type"],
                    p["traits"]["growth_form"], p["traits"]["woodiness"], p["traits"]["life_history"],
                    p["traits"]["height_min_m"], p["traits"]["height_max_m"],
                    p["flowering"]["label"], p["flowering"]["sources"], p["flowering"]["split_pattern"],
                    p["spread"]["resprouting"], p["spread"]["vegetative_spread"], p["spread"]["dispersal"],
                    p["spread"]["seedbank_longevity"], p["wet_soil_tolerance"], p["griis_listed_introduced"],
                    p["evidence"]["strength"], p["alternatives"]["status"], p["vicflora_url"],
                )
                for p in plants
            ],
        )
        cur.executemany(
            "INSERT INTO plant_flowering (plant_id, month) VALUES (%s,%s)",
            [
                (p["id"], i + 1)
                for p in plants
                for i, flowers in enumerate(p["flowering"]["months"] or [])
                if flowers
            ],
        )
        cur.executemany(
            """INSERT INTO plant_local_records (plant_id, vba100_count, vba100_latest_year, ala_count, ala_latest_year)
               VALUES (%s,%s,%s,%s,%s)""",
            [
                (
                    p["id"], p["local_records"]["vba100_count"], year(p["local_records"]["vba100_latest_year"]),
                    p["local_records"]["ala_count"], year(p["local_records"]["ala_latest_date"]),
                )
                for p in plants
            ],
        )
        cur.executemany(
            "INSERT INTO plant_evidence (plant_id, evidence_type) VALUES (%s,%s)",
            [(p["id"], e) for p in plants for e in p["evidence"]["available"]],
        )
        cur.executemany(
            "INSERT INTO plant_alternative (plant_id, alternative_id, rank_order) VALUES (%s,%s,%s)",
            [(p["id"], alt, rank + 1) for p in plants for rank, alt in enumerate(p["alternatives"]["ids"])],
        )
        counts = {}
        for table in ["plant", "plant_flowering", "plant_local_records", "plant_evidence", "plant_alternative"]:
            cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
            counts[table] = cur.fetchone()["n"]
    return counts


if __name__ == "__main__":
    print(load(sys.argv[1] if len(sys.argv) > 1 else None))
