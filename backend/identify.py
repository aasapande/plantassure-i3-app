"""
Photo identification via the Pl@ntNet API (https://my.plantnet.org).

- The API key lives in backend/.env as PLANTNET_API_KEY. Without it, the
  endpoint answers 503 "not set up" instead of failing.
- Photos are re-saved as plain JPEG before sending, which drops all hidden
  metadata (including GPS location). Photos are never stored or logged here.
- Pl@ntNet suggestions are matched to PlantAssure's own plant records; only
  matched plants can be confirmed and opened (AI never supplies plant facts).
"""
import io
import os

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from db import cursor

router = APIRouter()

PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SIDE_PX = 1600
MIN_SCORE = 0.05  # below this, a suggestion is too unreliable to show
MAX_MATCHES = 5
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def clean_jpeg(data: bytes) -> bytes:
    """Re-encode as JPEG without metadata (EXIF/GPS), resized to a sensible size."""
    try:
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image)  # keep the photo upright once EXIF is gone
        image = image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="This file isn’t a readable image.") from None
    image.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=90)  # no exif= argument, so no metadata is written
    return out.getvalue()


def call_plantnet(jpeg: bytes, api_key: str) -> dict | None:
    """Returns Pl@ntNet's JSON, or None when it finds no plant (HTTP 404)."""
    try:
        response = httpx.post(
            PLANTNET_URL,
            params={"api-key": api_key, "nb-results": 10, "lang": "en"},
            files={"images": ("photo.jpg", jpeg, "image/jpeg")},
            data={"organs": "auto"},
            timeout=30,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="The identification service couldn’t be reached.") from None
    if response.status_code == 404:
        return None
    if response.status_code == 429:
        raise HTTPException(status_code=503, detail="Today’s identification limit has been reached. Try again tomorrow.")
    if response.status_code in (401, 403):
        raise HTTPException(status_code=503, detail="Photo identification isn’t set up correctly.")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="The identification service couldn’t process this photo.")
    return response.json()


def match_to_plants(names: list[str]) -> dict[str, dict]:
    """Maps Pl@ntNet species names (binomials) to PlantAssure plants by exact
    scientific name. Anything else is shown as unavailable, never guessed."""
    if not names:
        return {}
    marks = ",".join(["%s"] * len(names))
    with cursor() as cur:
        cur.execute(
            f"SELECT plant_id, scientific_name, common_name FROM plant WHERE scientific_name IN ({marks})", names
        )
        found = {r["scientific_name"]: r for r in cur.fetchall()}
    return found


@router.post("/api/v1/plants/identify")
async def identify(image: UploadFile = File(...)):
    api_key = os.environ.get("PLANTNET_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Photo identification isn’t set up yet.")
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Please upload a JPEG, PNG or WebP photo.")
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Photos must be 10 MB or smaller.")

    result = call_plantnet(clean_jpeg(data), api_key)
    suggestions = [
        r for r in (result or {}).get("results", []) if r.get("score", 0) >= MIN_SCORE
    ][:MAX_MATCHES]
    if not suggestions:
        return {"status": "NO_CONFIDENT_MATCH", "matches": []}

    names = [s["species"]["scientificNameWithoutAuthor"] for s in suggestions]
    known = match_to_plants(names)
    matches = []
    for suggestion, name in zip(suggestions, names):
        plant = known.get(name)
        common = suggestion["species"].get("commonNames") or []
        matches.append({
            "scientificName": name,
            "commonName": plant["common_name"] if plant and plant["common_name"] else (common[0] if common else None),
            "identificationConfidence": round(float(suggestion["score"]), 4),
            "plantId": plant["plant_id"] if plant else None,
            "plantAssureMatch": plant is not None,
        })
    return {"status": "MATCHES_FOUND", "matches": matches}
