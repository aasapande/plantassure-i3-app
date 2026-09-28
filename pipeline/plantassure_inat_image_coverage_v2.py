#!/usr/bin/env python3
"""
PlantAssure iNaturalist Image Coverage Checker — v2

Fixes in v2
-----------
- Accepts exact CURRENT scientific-name matches.
- Accepts exact SYNONYM matches returned by iNaturalist autocomplete.
- Captures iNaturalist preferred common name.
- Records the matched term so synonym cases can be reviewed.
- Still rejects fuzzy/partial matches.
- Checks only reusable photo licences by default: CC0, CC BY, CC BY-SA.
- Falls back from the taxon's default photo to licensed observation photos.
- Saves checkpoints while running.

Example
-------
python3 plantassure_inat_image_coverage_v2.py --input vicflora_monash_2026.csv

Quick test first:
python3 plantassure_inat_image_coverage_v2.py --input vicflora_monash_2026.csv --limit 20

Dependencies
------------
pip install pandas requests
"""

import argparse
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Iterable

import pandas as pd
import requests


API_BASE = "https://api.inaturalist.org/v1"
DEFAULT_LICENSES = "cc0,cc-by,cc-by-sa"

# iNaturalist recommends keeping API use around 60 requests/minute or lower.
REQUEST_DELAY_SECONDS = 1.05
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 4

USER_AGENT = (
    "PlantAssure university prototype - "
    "scientific-name, common-name and image coverage checker"
)


def normalise_name(value: Any) -> str:
    """Case/spacing normalisation only — deliberately no fuzzy matching."""
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).casefold()


def find_scientific_name_column(df: pd.DataFrame) -> str:
    candidates = [
        "scientific_name",
        "scientificName",
        "species_name",
        "species",
        "taxon_name",
        "taxon",
    ]

    for col in candidates:
        if col in df.columns:
            return col

    lower_lookup = {str(c).casefold(): c for c in df.columns}
    for col in candidates:
        if col.casefold() in lower_lookup:
            return lower_lookup[col.casefold()]

    raise ValueError(
        "Could not find a scientific-name column.\n"
        f"Columns found: {list(df.columns)}\n"
        "Rename the column to 'scientific_name' or pass --name-column COLUMN_NAME."
    )


class INatClient:
    def __init__(self, delay: float = REQUEST_DELAY_SECONDS):
        self.delay = max(delay, 1.0)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )
        self._last_request_time = 0.0

    def _wait(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def get(self, endpoint: str, params: Optional[dict] = None) -> Dict[str, Any]:
        url = f"{API_BASE}{endpoint}"
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            self._wait()
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                self._last_request_time = time.time()

                if response.status_code == 429:
                    wait = min(30, 2 ** attempt)
                    print(f"    Rate limit reached. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.RequestException as exc:
                last_error = exc
                wait = min(20, 2 ** attempt)
                if attempt < MAX_RETRIES:
                    print(f"    Request failed ({exc}). Retrying in {wait}s...")
                    time.sleep(wait)

        raise RuntimeError(
            f"iNaturalist request failed after {MAX_RETRIES} attempts: {last_error}"
        )


def _flatten_strings(value: Any) -> Iterable[str]:
    """
    Defensively extract strings from possible all_names response structures.
    This makes the checker tolerant of list/dict/string representations.
    """
    if value is None:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _flatten_strings(v)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from _flatten_strings(v)


def exact_taxon_or_synonym_match(
    client: INatClient,
    scientific_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Resolve a PlantAssure scientific name against iNaturalist.

    SAFE matches accepted:
      1) EXACT_CURRENT_NAME:
         iNaturalist current taxon name == requested scientific name.

      2) EXACT_SYNONYM:
         the autocomplete result says the requested scientific name exactly
         matched a stored taxon name/synonym, while the current iNat name differs.

    Partial/fuzzy matches are rejected.
    """

    data = client.get(
        "/taxa/autocomplete",
        params={
            "q": scientific_name,
            "all_names": "true",
            "per_page": 30,
        },
    )

    target = normalise_name(scientific_name)
    results = data.get("results", [])

    # Pass 1: exact current scientific name always wins.
    for taxon in results:
        current_name = normalise_name(taxon.get("name"))
        if current_name == target:
            out = dict(taxon)
            out["_plantassure_match_type"] = "EXACT_CURRENT_NAME"
            out["_plantassure_matched_name"] = taxon.get("name")
            return out

    # Pass 2: exact synonym / alternate scientific name.
    #
    # matched_term is especially useful because iNaturalist can resolve a
    # historical/synonym scientific name to its current accepted taxon.
    for taxon in results:
        matched_term = taxon.get("matched_term")
        if normalise_name(matched_term) == target:
            out = dict(taxon)
            out["_plantassure_match_type"] = "EXACT_SYNONYM"
            out["_plantassure_matched_name"] = matched_term
            return out

    # Pass 3: if all_names returned explicit names, accept ONLY an exact string.
    # We intentionally inspect only name-like fields and still require exactness.
    for taxon in results:
        candidate_name_fields = []
        for key in ("names", "taxon_names", "common_names"):
            if key in taxon:
                candidate_name_fields.extend(list(_flatten_strings(taxon.get(key))))

        for candidate in candidate_name_fields:
            if normalise_name(candidate) == target:
                out = dict(taxon)
                out["_plantassure_match_type"] = "EXACT_SYNONYM"
                out["_plantassure_matched_name"] = candidate
                return out

    return None


def photo_fields(
    photo: Dict[str, Any],
    source: str,
    observation_id: Optional[int] = None,
) -> Dict[str, Any]:
    photo_id = photo.get("id")
    medium_url = photo.get("medium_url")

    if not medium_url:
        url = photo.get("url")
        if url:
            medium_url = (
                url.replace("/square.", "/medium.")
                   .replace("/small.", "/medium.")
                   .replace("/thumb.", "/medium.")
            )

    return {
        "usable_photo": True,
        "photo_source": source,
        "photo_id": photo_id,
        "photo_url": medium_url or photo.get("url"),
        "photo_license": photo.get("license_code"),
        "photo_attribution": photo.get("attribution"),
        "observation_id": observation_id,
        "observation_url": (
            f"https://www.inaturalist.org/observations/{observation_id}"
            if observation_id
            else None
        ),
        "photo_page_url": (
            f"https://www.inaturalist.org/photos/{photo_id}"
            if photo_id
            else None
        ),
    }


def blank_photo_result() -> Dict[str, Any]:
    return {
        "usable_photo": False,
        "photo_source": None,
        "photo_id": None,
        "photo_url": None,
        "photo_license": None,
        "photo_attribution": None,
        "observation_id": None,
        "observation_url": None,
        "photo_page_url": None,
    }


def default_photo_if_usable(
    taxon: Dict[str, Any],
    accepted_licenses: set,
) -> Optional[Dict[str, Any]]:
    photo = taxon.get("default_photo") or {}
    licence = normalise_name(photo.get("license_code"))

    if photo and licence in accepted_licenses:
        return photo_fields(photo, "taxon_default_photo")

    return None


def observation_photo(
    client: INatClient,
    taxon_id: int,
    accepted_licenses_csv: str,
    accepted_licenses: set,
    research_grade_only: bool,
) -> Optional[Dict[str, Any]]:
    params = {
        "taxon_id": taxon_id,
        "photos": "true",
        "photo_license": accepted_licenses_csv,
        "per_page": 30,
        "order_by": "votes",
        "order": "desc",
    }

    if research_grade_only:
        params["quality_grade"] = "research"

    data = client.get("/observations", params=params)

    for obs in data.get("results", []):
        for photo in obs.get("photos", []):
            licence = normalise_name(photo.get("license_code"))
            if licence in accepted_licenses:
                return photo_fields(
                    photo,
                    source=(
                        "research_grade_observation"
                        if research_grade_only
                        else "licensed_observation"
                    ),
                    observation_id=obs.get("id"),
                )

    return None


def process_one(
    client: INatClient,
    scientific_name: str,
    accepted_licenses_csv: str,
    accepted_licenses: set,
) -> Dict[str, Any]:

    result = {
        "plantassure_scientific_name": scientific_name,
        "safe_inat_match": False,
        "match_type": None,
        "matched_term": None,
        "inat_taxon_id": None,
        "inat_current_scientific_name": None,
        "inat_preferred_common_name": None,
        "inat_rank": None,
        "inat_taxon_url": None,
        "name_differs_from_inat_current": False,
        "inat_default_photo_exists": False,
        "inat_default_photo_license": None,
        "status": None,
        "error": None,
    }
    result.update(blank_photo_result())

    try:
        taxon = exact_taxon_or_synonym_match(client, scientific_name)

        if not taxon:
            result["status"] = "NO_SAFE_EXACT_OR_SYNONYM_MATCH"
            return result

        taxon_id = taxon.get("id")
        current_name = taxon.get("name")
        match_type = taxon.get("_plantassure_match_type")
        matched_name = taxon.get("_plantassure_matched_name") or taxon.get("matched_term")

        result["safe_inat_match"] = True
        result["match_type"] = match_type
        result["matched_term"] = matched_name
        result["inat_taxon_id"] = taxon_id
        result["inat_current_scientific_name"] = current_name
        result["inat_preferred_common_name"] = taxon.get("preferred_common_name")
        result["inat_rank"] = taxon.get("rank")
        result["inat_taxon_url"] = (
            f"https://www.inaturalist.org/taxa/{taxon_id}"
            if taxon_id
            else None
        )
        result["name_differs_from_inat_current"] = (
            normalise_name(current_name) != normalise_name(scientific_name)
        )

        default_photo = taxon.get("default_photo") or {}
        result["inat_default_photo_exists"] = bool(default_photo)
        result["inat_default_photo_license"] = default_photo.get("license_code")

        usable = default_photo_if_usable(taxon, accepted_licenses)
        if usable:
            result.update(usable)
            result["status"] = (
                "USABLE_DEFAULT_PHOTO_SYNONYM_MATCH"
                if match_type == "EXACT_SYNONYM"
                else "USABLE_DEFAULT_PHOTO_CURRENT_NAME_MATCH"
            )
            return result

        if taxon_id is None:
            result["status"] = "MATCHED_BUT_NO_TAXON_ID"
            return result

        # First fallback: licensed Research Grade observation photo.
        usable = observation_photo(
            client,
            taxon_id=taxon_id,
            accepted_licenses_csv=accepted_licenses_csv,
            accepted_licenses=accepted_licenses,
            research_grade_only=True,
        )
        if usable:
            result.update(usable)
            result["status"] = (
                "USABLE_RESEARCH_GRADE_PHOTO_SYNONYM_MATCH"
                if match_type == "EXACT_SYNONYM"
                else "USABLE_RESEARCH_GRADE_PHOTO_CURRENT_NAME_MATCH"
            )
            return result

        # Second fallback: any observation with an accepted photo licence.
        usable = observation_photo(
            client,
            taxon_id=taxon_id,
            accepted_licenses_csv=accepted_licenses_csv,
            accepted_licenses=accepted_licenses,
            research_grade_only=False,
        )
        if usable:
            result.update(usable)
            result["status"] = (
                "USABLE_LICENSED_PHOTO_SYNONYM_MATCH"
                if match_type == "EXACT_SYNONYM"
                else "USABLE_LICENSED_PHOTO_CURRENT_NAME_MATCH"
            )
            return result

        if default_photo:
            result["status"] = "PHOTO_EXISTS_BUT_NO_ACCEPTED_LICENSE_FOUND"
        else:
            result["status"] = "NO_USABLE_PHOTO_FOUND"

        return result

    except Exception as exc:
        result["status"] = "ERROR"
        result["error"] = str(exc)
        return result


def print_summary(results: pd.DataFrame):
    total = len(results)
    if total == 0:
        print("No scientific names were checked.")
        return

    safe_matches = int(results["safe_inat_match"].fillna(False).sum())
    current_matches = int((results["match_type"] == "EXACT_CURRENT_NAME").sum())
    synonym_matches = int((results["match_type"] == "EXACT_SYNONYM").sum())
    usable = int(results["usable_photo"].fillna(False).sum())
    missing = total - usable
    common_names = int(
        results["inat_preferred_common_name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )
    errors = int((results["status"] == "ERROR").sum())

    print("\n" + "=" * 72)
    print("PLANTASSURE × iNATURALIST NAME + IMAGE COVERAGE — v2")
    print("=" * 72)
    print(f"Unique PlantAssure names checked            : {total}")
    print(
        f"Safe iNaturalist matches                    : "
        f"{safe_matches}/{total} ({safe_matches/total*100:.1f}%)"
    )
    print(f"  Exact current-name matches                : {current_matches}")
    print(f"  Exact synonym-name matches                : {synonym_matches}")
    print(
        f"Preferred common names obtained             : "
        f"{common_names}/{total} ({common_names/total*100:.1f}%)"
    )
    print(
        f"Usable licensed photos                      : "
        f"{usable}/{total} ({usable/total*100:.1f}%)"
    )
    print(
        f"Without a usable licensed photo             : "
        f"{missing}/{total} ({missing/total*100:.1f}%)"
    )
    print(f"Errors requiring review                     : {errors}")
    print("=" * 72)

    print("\nMatch-type breakdown:")
    print(results["match_type"].fillna("NO_MATCH").value_counts().to_string())

    print("\nStatus breakdown:")
    print(results["status"].fillna("UNKNOWN").value_counts().to_string())


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Check iNaturalist current-name/synonym matches, preferred common names, "
            "and licensed image coverage for PlantAssure."
        )
    )
    parser.add_argument(
        "--input",
        default="vicflora_monash_2026.csv",
        help="Input CSV (default: vicflora_monash_2026.csv)",
    )
    parser.add_argument(
        "--output",
        default="inat_name_image_coverage_results.csv",
        help="Detailed output CSV",
    )
    parser.add_argument(
        "--name-column",
        default=None,
        help="Scientific-name column; auto-detected if omitted.",
    )
    parser.add_argument(
        "--licenses",
        default=DEFAULT_LICENSES,
        help=(
            "Comma-separated accepted PHOTO licences. "
            "Default: cc0,cc-by,cc-by-sa"
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY_SECONDS,
        help="Seconds between API requests (minimum 1.0; default 1.05)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional test limit, e.g. --limit 20",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path.resolve()}\n"
            "Put the CSV beside this script or pass --input /path/to/file.csv"
        )

    df = pd.read_csv(input_path, low_memory=False)
    name_col = args.name_column or find_scientific_name_column(df)

    names = df[name_col].dropna().astype(str).str.strip()
    names = names[names.ne("")].drop_duplicates().tolist()

    if args.limit is not None:
        names = names[: max(args.limit, 0)]

    accepted_licenses_csv = ",".join(
        x.strip().casefold()
        for x in args.licenses.split(",")
        if x.strip()
    )
    accepted_licenses = set(accepted_licenses_csv.split(","))

    print(f"Using scientific-name column: {name_col}")
    print(f"Scientific names to check: {len(names)}")
    print(f"Accepted photo licences: {', '.join(sorted(accepted_licenses))}")
    print(
        "\nExact current names AND exact synonyms are accepted. "
        "Fuzzy/partial matches are rejected.\n"
    )

    client = INatClient(delay=args.delay)
    rows: List[Dict[str, Any]] = []
    output_path = Path(args.output)

    for idx, name in enumerate(names, start=1):
        print(f"[{idx}/{len(names)}] {name}")

        row = process_one(
            client=client,
            scientific_name=name,
            accepted_licenses_csv=accepted_licenses_csv,
            accepted_licenses=accepted_licenses,
        )
        rows.append(row)

        match_label = row.get("match_type") or "NO MATCH"
        common = row.get("inat_preferred_common_name") or "—"
        photo_marker = "✓ PHOTO" if row.get("usable_photo") else "✗ PHOTO"

        if row.get("match_type") == "EXACT_SYNONYM":
            print(
                f"    ✓ SYNONYM → {row.get('inat_current_scientific_name')} "
                f"| common: {common} | {photo_marker}"
            )
        elif row.get("match_type") == "EXACT_CURRENT_NAME":
            print(
                f"    ✓ CURRENT NAME | common: {common} | {photo_marker}"
            )
        else:
            print(f"    ✗ {row.get('status')}")

        # Checkpoint every 25 names.
        if idx % 25 == 0 or idx == len(names):
            pd.DataFrame(rows).to_csv(output_path, index=False)

    results = pd.DataFrame(rows)
    results.to_csv(output_path, index=False)

    review_path = output_path.with_name(
        output_path.stem + "_missing_or_review.csv"
    )
    review_mask = (
        ~results["safe_inat_match"].fillna(False)
        | ~results["usable_photo"].fillna(False)
        | (results["match_type"] == "EXACT_SYNONYM")
        | (results["status"] == "ERROR")
    )
    results.loc[review_mask].to_csv(review_path, index=False)

    print_summary(results)

    print(f"\nDetailed results saved to:\n  {output_path.resolve()}")
    print(f"\nSynonym/missing/review cases saved to:\n  {review_path.resolve()}")
    print(
        "\nIMPORTANT: Keep photo attribution, licence, and source URLs "
        "with every image used in PlantAssure."
    )


if __name__ == "__main__":
    main()
