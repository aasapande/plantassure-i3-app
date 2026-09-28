"""
Iteration 3 Data Processing Pipeline -- Plant Passport, My Garden, Data Insights

Builds on the Iteration 2 pipeline (pipeline_i2_aasavari_final.py), which is
imported unchanged. Everything from Iteration 2 (risk rating, traits,
alternatives, occurrence counts, GRIIS) is kept; this script only adds:

  1. Common-name fill      VicFlora -> VBA100 -> DEECA Advisory List -> ALA
  2. Flowering months      AusTraits flowering_time -> 12 month flags + label
  3. Spread traits         resprouting, vegetative spread, seed dispersal,
                           seed bank longevity (for "Keeping it in your garden")
  4. Wet-soil tolerance    AusTraits plant_tolerance_water_logged_soils
  5. Plant type group      Tree / Shrub / Grass / Herb / Climber / Fern
  6. VicFlora profile link from the VicFlora record id
  7. Evidence strength     Strong / Moderate / Limited (how much verified
                           information exists -- NOT environmental risk)
  8. Tableau export        one row per plant per month (long format)
  9. Validation report     coverage numbers and review lists

Rule carried over from earlier iterations: missing values stay missing.
Nothing is inferred or guessed.

Usage:
    python3 pipeline_i3_aasavari.py /path/to/data
"""
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
import pandas as pd
import pyarrow.parquet as pq
import shapefile  # pyshp

import pipeline_i2_aasavari_final as i2

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = i2.BASE  # same data-directory resolution as Iteration 2
OUTPUT_DIR = Path(os.environ.get("PLANTASSURE_OUTPUT_DIR", str(SCRIPT_DIR / "output")))

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
RISKY = {"Reconsider Planting", "Use Caution"}


def exact_key(name):
    """Full scientific name, lower-cased, for exact joins (keeps subspecies
    and varieties distinct -- used for common names, where a species-level
    name must not be copied onto a different subspecies)."""
    if name is None or pd.isna(name):
        return None
    key = " ".join(str(name).split()).lower()
    return key or None


# Step 1: Common-name fill
# Priority: VicFlora (already in the base table) -> VBA100 -> DEECA -> ALA.
# State/official sources come before ALA, whose vernacular names are
# occasionally odd (e.g. "Coast Coastal Banksia").

def load_vba100_common_names(shp_path):
    sf = shapefile.Reader(shp_path)
    fields = [f[0] for f in sf.fields[1:]]
    idx_sci, idx_comm = fields.index("SCI_NAME"), fields.index("COMM_NAME")
    names = {}
    for rec in sf.iterRecords():
        key = exact_key(rec[idx_sci])
        comm = str(rec[idx_comm] or "").strip()
        if key and comm and key not in names:
            names[key] = comm
    return names


def load_advisory_common_names(path, sheet_name="Advisory list 2022"):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    it = wb[sheet_name].iter_rows(values_only=True)
    header = next(it)
    idx_sci, idx_comm = header.index("Scientific name"), header.index("Common Name")
    names = {}
    for row in it:
        key = exact_key(row[idx_sci])
        comm = str(row[idx_comm] or "").strip()
        if key and comm and key not in names:
            names[key] = comm
    return names


def load_ala_common_names(csv_path):
    df = pd.read_csv(csv_path, usecols=["scientificName", "vernacularName"], dtype=str)
    df = df.dropna()
    df["key"] = df["scientificName"].apply(exact_key)
    # Most frequent vernacular name per species
    return df.groupby("key")["vernacularName"].agg(lambda s: s.mode().iloc[0]).to_dict()


def fill_common_names(df, vba_names, deeca_names, ala_names):
    names, sources = [], []
    for sci, vicflora_name in zip(df["scientific_name"], df["vernacular_name"]):
        key = exact_key(sci)
        for source, value in (
            ("VicFlora", vicflora_name),
            ("VBA", vba_names.get(key)),
            ("DEECA Advisory List", deeca_names.get(key)),
            ("ALA", ala_names.get(key)),
        ):
            if value is not None and not pd.isna(value) and str(value).strip():
                names.append(str(value).strip())
                sources.append(source)
                break
        else:
            names.append(None)
            sources.append(None)
    df["common_name"] = names
    df["common_name_source"] = sources
    return df


# Steps 2-4: extra AusTraits traits (read in one pass over the parquet)

EXTRA_TRAITS = {
    "flowering_time",
    "resprouting_capacity",
    "vegetative_reproduction_ability",
    "dispersal_syndrome",
    "seedbank_longevity_class",
    "plant_tolerance_water_logged_soils",
}

# Plain-language labels for dispersal syndromes (AusTraits trait definitions)
DISPERSAL_LABELS = {
    "anemochory": "wind",
    "zoochory": "animals",
    "endozoochory": "birds and animals eating the fruit",
    "epizoochory": "sticking to animals and clothing",
    "myrmecochory": "ants",
    "hydrochory": "water",
    "barochory": "falling near the parent plant",
}

# Wet-soil tolerance, ordered from least to most tolerant. The highest
# category reported for a species is used. "not_applicable" is ambiguous
# in the source, so it is treated as unknown and listed for review.
WATERLOG_ORDER = [
    ("less_than_1_month", "Copes with short wet spells (under a month)"),
    ("1-6_months", "Copes with waterlogged soil for 1-6 months"),
    ("greater_than_6_months", "Copes with waterlogged soil for over 6 months"),
    ("aquatic", "Grows in water"),
]


def load_extra_traits(parquet_path):
    obs = defaultdict(lambda: defaultdict(list))
    pf = pq.ParquetFile(parquet_path)
    for batch in pf.iter_batches(
        batch_size=300000, columns=["taxon_name", "trait_name", "value", "dataset_id"]
    ):
        taxa = batch.column("taxon_name").to_pylist()
        traits = batch.column("trait_name").to_pylist()
        values = batch.column("value").to_pylist()
        datasets = batch.column("dataset_id").to_pylist()
        for taxon, trait, value, dataset in zip(taxa, traits, values, datasets):
            if trait not in EXTRA_TRAITS or not value:
                continue
            key = i2.normalize_name(taxon)
            if key:
                obs[key][trait].append((str(value), dataset))

    rows = []
    for key, traits in obs.items():
        row = {"match_key": key}
        row.update(resolve_flowering(traits.get("flowering_time", [])))
        row["resprouting"] = mode_value(traits.get("resprouting_capacity", []))
        row["vegetative_spread"] = mode_value(traits.get("vegetative_reproduction_ability", []))
        row["seedbank_longevity"] = mode_value(traits.get("seedbank_longevity_class", []))
        row["dispersal"] = resolve_dispersal(traits.get("dispersal_syndrome", []))
        row.update(resolve_waterlogging(traits.get("plant_tolerance_water_logged_soils", [])))
        rows.append(row)
    return pd.DataFrame(rows)


def mode_value(observations):
    """Most frequent single-token value; multi-value strings are split."""
    tokens = [t for v, _ in observations for t in v.split()]
    if not tokens:
        return None
    return Counter(tokens).most_common(1)[0][0]


def resolve_flowering(observations):
    """Union of months across all valid 12-character y/n records: a month
    counts if any source lists it. Also reports how many datasets agree and
    how many separate flowering blocks the result has (split patterns are
    flagged for manual review)."""
    codes = [v for v, _ in observations if len(v) == 12 and set(v) <= {"y", "n"}]
    out = {f"flowers_{m.lower()}": None for m in MONTHS}
    out.update({"flowering_months": None, "flowering_sources": 0, "flowering_blocks": None})
    if not codes:
        return out
    flags = [any(c[i] == "y" for c in codes) for i in range(12)]
    for m, flag in zip(MONTHS, flags):
        out[f"flowers_{m.lower()}"] = flag
    out["flowering_sources"] = len({ds for v, ds in observations if v in codes})
    out["flowering_blocks"] = count_blocks(flags)
    out["flowering_months"] = months_label(flags)
    return out


def count_blocks(flags):
    """Number of separate runs of flowering months, treating Dec->Jan as
    continuous (a Nov-Feb season is one block)."""
    if all(flags):
        return 1
    if not any(flags):
        return 0
    return sum(1 for i in range(12) if flags[i] and not flags[i - 1])


def months_label(flags):
    if all(flags):
        return "All year"
    if not any(flags):
        return None
    # Start labelling from a month that begins a block, so Dec-Feb stays together
    start = next(i for i in range(12) if flags[i] and not flags[i - 1])
    parts, i = [], start
    for _ in range(12):
        if flags[i % 12] and not flags[(i - 1) % 12]:
            j = i
            while flags[(j + 1) % 12] and (j + 1) % 12 != i % 12:
                j += 1
            first, last = MONTHS[i % 12], MONTHS[j % 12]
            parts.append(first if first == last else f"{first}–{last}")
        i += 1
    return ", ".join(parts)


def resolve_dispersal(observations):
    tokens = [t for v, _ in observations for t in v.split() if t in DISPERSAL_LABELS]
    if not tokens:
        return None
    ranked = [t for t, _ in Counter(tokens).most_common(2)]
    return " / ".join(DISPERSAL_LABELS[t] for t in ranked)


def resolve_waterlogging(observations):
    tokens = {t for v, _ in observations for t in v.split()}
    best = None
    for code, label in WATERLOG_ORDER:
        if code in tokens:
            best = label
    needs_review = bool(observations) and best is None  # only "not_applicable"
    return {"wet_soil_tolerance": best, "wet_soil_needs_review": needs_review}


# Step 5: Plant type group (for charts and general planting guidance)

def plant_type_group(growth_form):
    if growth_form is None or pd.isna(growth_form):
        return None
    gf = str(growth_form)
    if "climber" in gf:
        return "Climber"
    if "tree" in gf:
        return "Tree"
    if "shrub" in gf:
        return "Shrub"
    if "graminoid" in gf or "tussock" in gf:
        return "Grass"
    if "fern" in gf:
        return "Fern"
    return "Herb"


# Step 7: Evidence strength -- how much verified information exists.
# Five core evidence types; GRIIS counts only for introduced plants
# (it also lists Victorian natives introduced elsewhere in Australia).

EVIDENCE_TYPES = ["rating", "origin", "local_records", "traits", "flowering"]
# Strong = all five types (so a Not Assessed plant can never be Strong);
# a looser 4-of-5 rule marked 797 of 880 plants Strong and did not separate
# plants. Change here if the team decides otherwise.
STRONG_MIN, MODERATE_MIN = 5, 3


def evidence_for(row):
    available = []
    if row["recommendation"] != "Not Assessed":
        available.append("rating")
    if row["establishment_means"] not in (None, "Not available") and not pd.isna(row["establishment_means"]):
        available.append("origin")
    if (row["vba100_record_count"] or 0) + (row["ala_record_count"] or 0) > 0:
        available.append("local_records")
    if row["growth_form"] is not None and not pd.isna(row["growth_form"]):
        available.append("traits")
    if row.get("flowering_months") is not None and not pd.isna(row.get("flowering_months")):
        available.append("flowering")
    missing = [e for e in EVIDENCE_TYPES if e not in available]
    if str(row["establishment_means"]).lower() == "introduced" and bool(row["griis_listed"]):
        available.append("griis")
    core = len([e for e in available if e in EVIDENCE_TYPES])
    strength = "Strong" if core >= STRONG_MIN else "Moderate" if core >= MODERATE_MIN else "Limited"
    return available, missing, strength


def run_pipeline_i3():
    base = Path(BASE)
    print(f"Using data directory: {base}")

    print("Iteration 2 pipeline (unchanged) ...")
    i2_output, merged = i2.run_pipeline()
    alternatives = {i2.normalize_name(e["scientific_name"]): e["alternatives"] for e in i2_output}

    print("Step 1: Common-name fill ...")
    vicflora_ids = pd.read_csv(base / "vicflora_monash_2026.csv", dtype=str)[["id", "scientific_name"]]
    shp = base / "order/ll_gda2020/esrishape/lga_polygon/MONASH-0/FLORAFAUNA1/VBA_FLORA100.shp"
    with zipfile.ZipFile(base / "records-2026-09-10.zip") as z:
        z.extract("records-2026-09-10.csv", "/tmp")
    merged = fill_common_names(
        merged,
        load_vba100_common_names(shp),
        load_advisory_common_names(base / "Advisory-list-of-environmental-weeds-in-Victoria_2022.xlsx"),
        load_ala_common_names("/tmp/records-2026-09-10.csv"),
    )

    print("Steps 2-4: Flowering, spread traits, wet-soil tolerance ...")
    extra = load_extra_traits(base / "austraits-7.0.0-flattened.parquet")
    merged = merged.merge(extra, on="match_key", how="left")
    merged["wet_soil_needs_review"] = merged["wet_soil_needs_review"].fillna(False)
    merged["flowering_sources"] = merged["flowering_sources"].fillna(0).astype(int)

    print("Step 5: Plant type group ...")
    merged["plant_type"] = merged["growth_form"].apply(plant_type_group)

    print("Step 6: VicFlora profile links ...")
    merged = merged.merge(vicflora_ids.rename(columns={"id": "vicflora_id"}), on="scientific_name", how="left")
    merged = merged.drop_duplicates(subset="scientific_name")
    merged["vicflora_url"] = merged["vicflora_id"].apply(
        lambda i: f"https://vicflora.rbg.vic.gov.au/flora/taxon/{i}" if isinstance(i, str) else None
    )

    print("Step 7: Evidence strength ...")
    evidence = merged.apply(evidence_for, axis=1, result_type="expand")
    merged["evidence_available"], merged["evidence_missing"], merged["evidence_strength"] = (
        evidence[0], evidence[1], evidence[2]
    )

    output = [build_entry(row, alternatives) for _, row in merged.iterrows()]
    return output, merged


def clean(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "item"):  # numpy scalars
        return value.item()
    return value


def build_entry(row, alternatives):
    month_flags = [clean(row.get(f"flowers_{m.lower()}")) for m in MONTHS]
    return {
        "scientific_name": row["scientific_name"],
        "common_name": clean(row["common_name"]),
        "common_name_source": clean(row["common_name_source"]),
        "family": clean(row["family"]),
        "origin": clean(row["establishment_means"]),
        "establishment": clean(row["degree_of_establishment"]),
        "recommendation": row["recommendation"],
        "risk_rating": clean(row["Risk Rating"]),
        "plant_type": clean(row["plant_type"]),
        "traits": {
            "growth_form": clean(row["growth_form"]),
            "woodiness": clean(row["woodiness"]),
            "life_history": clean(row["life_history"]),
            "height_min_m": clean(row["height_min"]),
            "height_max_m": clean(row["height_max"]),
        },
        "flowering": {
            "months": month_flags if any(f is not None for f in month_flags) else None,
            "label": clean(row["flowering_months"]),
            "sources": int(row["flowering_sources"]),
            "split_pattern": bool(clean(row["flowering_blocks"]) and row["flowering_blocks"] >= 3),
        },
        "spread": {
            "resprouting": clean(row["resprouting"]),
            "vegetative_spread": clean(row["vegetative_spread"]),
            "dispersal": clean(row["dispersal"]),
            "seedbank_longevity": clean(row["seedbank_longevity"]),
        },
        "wet_soil_tolerance": clean(row["wet_soil_tolerance"]),
        "local_records": {
            "vba100_count": int(row["vba100_record_count"]),
            "vba100_latest_year": clean(row["vba100_most_recent_year"]),
            "ala_count": int(row["ala_record_count"]),
            "ala_latest_date": clean(row["ala_most_recent_date"]),
        },
        "griis_listed_introduced": bool(
            str(row["establishment_means"]).lower() == "introduced" and bool(row["griis_listed"])
        ),
        "evidence": {
            "strength": row["evidence_strength"],
            "available": row["evidence_available"],
            "missing": row["evidence_missing"],
        },
        "vicflora_url": clean(row["vicflora_url"]),
        "alternatives": alternatives.get(
            row["match_key"], {"status": "not_applicable_lower_concern_or_not_assessed", "alternatives": []}
        ),
    }


def tableau_long_format(merged):
    """One row per plant per month, plus the fields the three Data Insights
    charts need (origin, rating, plant type). Plants without flowering data
    still get 12 rows with flowers = blank, so origin/type charts can use
    every plant."""
    rows = []
    for _, r in merged.iterrows():
        for i, m in enumerate(MONTHS):
            flag = clean(r.get(f"flowers_{m.lower()}"))
            rows.append({
                "scientific_name": r["scientific_name"],
                "common_name": clean(r["common_name"]),
                "recommendation": r["recommendation"],
                "is_risky": r["recommendation"] in RISKY,
                "origin": clean(r["establishment_means"]),
                "plant_type": clean(r["plant_type"]),
                "month_number": i + 1,
                "month": m,
                "flowers": flag,
                "flowering_split_pattern": bool(clean(r["flowering_blocks"]) and r["flowering_blocks"] >= 3),
            })
    return pd.DataFrame(rows)


def validation_report(merged):
    n = len(merged)
    risky = merged["recommendation"].isin(RISKY)
    has_flowering = merged["flowering_months"].notna()

    def pct(part, whole):
        return f"{part} / {whole} ({part / whole:.0%})" if whole else "0"

    lines = [
        "PlantAssure Iteration 3 -- data validation report",
        "=" * 52,
        f"Plants processed: {n}",
        "",
        "Recommendation distribution:",
        *[f"  {k}: {v}" for k, v in merged["recommendation"].value_counts().items()],
        "",
        "Common names:",
        f"  VicFlora only (Iteration 2): {pct(int(merged['vernacular_name'].notna().sum()), n)}",
        f"  After fill (Iteration 3):    {pct(int(merged['common_name'].notna().sum()), n)}",
        *[f"    from {k}: {v}" for k, v in merged["common_name_source"].value_counts().items()],
        "",
        "Coverage (all plants / risky plants):",
    ]
    for label, col in [
        ("Flowering months", "flowering_months"),
        ("Resprouting", "resprouting"),
        ("Vegetative spread", "vegetative_spread"),
        ("Seed dispersal", "dispersal"),
        ("Seed bank longevity", "seedbank_longevity"),
        ("Wet-soil tolerance", "wet_soil_tolerance"),
        ("Plant type group", "plant_type"),
    ]:
        has = merged[col].notna()
        lines.append(f"  {label:<20} {pct(int(has.sum()), n):<18} {pct(int((has & risky).sum()), int(risky.sum()))}")

    lines += [
        "",
        "Evidence strength (how much verified information exists, not risk):",
        *[f"  {k}: {v}" for k, v in merged["evidence_strength"].value_counts().items()],
        "",
        "Evidence strength for Not Assessed plants:",
        *[
            f"  {k}: {v}"
            for k, v in merged.loc[merged["recommendation"] == "Not Assessed", "evidence_strength"]
            .value_counts()
            .items()
        ],
        "",
        "Chart check -- risky plants in flower per month:",
        "  " + "  ".join(
            f"{m} {int((merged.loc[risky & has_flowering, f'flowers_{m.lower()}'] == True).sum())}" for m in MONTHS
        ),
        "",
        "Needs manual review (see review_*.csv):",
        f"  Split flowering patterns (3+ separate blocks): {int((merged['flowering_blocks'] >= 3).sum())}",
        f"  Wet-soil value only 'not_applicable':          {int(merged['wet_soil_needs_review'].sum())}",
        f"  Still no common name:                          {int(merged['common_name'].isna().sum())}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    result, merged_df = run_pipeline_i3()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "output_i3.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    merged_df.to_csv(OUTPUT_DIR / "output_i3.csv", index=False, encoding="utf-8-sig")
    tableau_long_format(merged_df).to_csv(OUTPUT_DIR / "tableau_insights_i3.csv", index=False, encoding="utf-8-sig")

    merged_df.loc[merged_df["flowering_blocks"] >= 3, ["scientific_name", "common_name", "flowering_months", "flowering_sources"]].to_csv(
        OUTPUT_DIR / "review_flowering_split.csv", index=False, encoding="utf-8-sig"
    )
    merged_df.loc[merged_df["common_name"].isna(), ["scientific_name", "recommendation", "establishment_means"]].to_csv(
        OUTPUT_DIR / "review_missing_common_names.csv", index=False, encoding="utf-8-sig"
    )

    report = validation_report(merged_df)
    (OUTPUT_DIR / "validation_report_i3.txt").write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"\nOutputs written to: {OUTPUT_DIR}")
