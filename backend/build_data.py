"""
Builds the app's plant data file from the Iteration 3 pipeline output.

    python3 build_data.py /path/to/output_i3.json

Each plant gets a stable id (position in the pipeline output, which follows
VicFlora's alphabetical order). Swap suggestions come from the pipeline's
strict four-trait matching, converted from scientific names to ids.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / "pipeline/output/output_i3.json"


def main(source: Path) -> None:
    rows = json.loads(source.read_text(encoding="utf-8"))
    ids = {row["scientific_name"]: index + 1 for index, row in enumerate(rows)}

    plants = []
    for row in rows:
        alt = row["alternatives"]
        row = dict(row)
        row["id"] = ids[row["scientific_name"]]
        row["alternatives"] = {
            "status": alt["status"],
            "ids": [ids[a["scientific_name"]] for a in alt["alternatives"] if a["scientific_name"] in ids],
        }
        plants.append(row)

    out = HERE / "data" / "plants.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(plants, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(plants)} plants to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE)
