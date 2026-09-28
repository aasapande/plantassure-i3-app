"""Photo identification tests. Pl@ntNet is replaced by a fake, so no API key
or internet connection is needed."""
import io

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

import identify
import load_data
import main

TEST_DB = "plantassure_i3_test"


def photo(with_gps: bool = False) -> bytes:
    image = Image.new("RGB", (40, 30), (40, 120, 60))
    out = io.BytesIO()
    if with_gps:
        exif = Image.Exif()
        exif[0x8825] = {1: "S", 2: (37.0, 54.0, 0.0), 3: "E", 4: (145.0, 8.0, 0.0)}  # GPS block
        image.save(out, format="JPEG", exif=exif)
    else:
        image.save(out, format="JPEG")
    return out.getvalue()


def plantnet_result(*species):
    return {"results": [{"score": score, "species": {"scientificNameWithoutAuthor": name, "commonNames": common}}
                        for name, score, common in species]}


@pytest.fixture(scope="module", autouse=True)
def test_database():
    load_data.load(TEST_DB)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("DB_NAME", TEST_DB)
    monkeypatch.setenv("PLANTNET_API_KEY", "test-key")
    with TestClient(main.app) as c:
        yield c


def upload(client, data=None, content_type="image/jpeg"):
    return client.post("/api/v1/plants/identify", files={"image": ("plant.jpg", data or photo(), content_type)})


def test_location_data_is_removed_before_sending():
    original = photo(with_gps=True)
    assert Image.open(io.BytesIO(original)).getexif().get(0x8825)  # GPS present
    cleaned = identify.clean_jpeg(original)
    assert not Image.open(io.BytesIO(cleaned)).getexif()  # no metadata at all


def test_matches_are_linked_to_plantassure_records(client, monkeypatch):
    sent = {}

    def fake(jpeg, key):
        sent["exif"] = Image.open(io.BytesIO(jpeg)).getexif()
        return plantnet_result(("Ulex europaeus", 0.91, ["Gorse"]), ("Rosa rubiginosa", 0.04, []),
                               ("Genista monspessulana", 0.06, ["Montpellier broom"]))

    monkeypatch.setattr(identify, "call_plantnet", fake)
    body = upload(client, photo(with_gps=True)).json()
    assert not sent["exif"]
    assert body["status"] == "MATCHES_FOUND"
    names = [m["scientificName"] for m in body["matches"]]
    assert names == ["Ulex europaeus", "Genista monspessulana"]  # 0.04 is below the threshold
    gorse = body["matches"][0]
    assert gorse["plantAssureMatch"] and isinstance(gorse["plantId"], int)
    assert gorse["identificationConfidence"] == 0.91


def test_species_outside_monash_list_cannot_be_confirmed(client, monkeypatch):
    monkeypatch.setattr(identify, "call_plantnet", lambda j, k: plantnet_result(("Welwitschia mirabilis", 0.8, ["Tree tumbo"])))
    match = upload(client).json()["matches"][0]
    assert match["plantAssureMatch"] is False and match["plantId"] is None
    assert match["commonName"] == "Tree tumbo"


def test_no_plant_found(client, monkeypatch):
    monkeypatch.setattr(identify, "call_plantnet", lambda j, k: None)
    assert upload(client).json() == {"status": "NO_CONFIDENT_MATCH", "matches": []}


def test_not_set_up_without_a_key(client, monkeypatch):
    monkeypatch.setenv("PLANTNET_API_KEY", "")
    r = upload(client)
    assert r.status_code == 503 and "set up" in r.json()["detail"]


def test_daily_limit_message(client, monkeypatch):
    def over_limit(j, k):
        raise HTTPException(status_code=503, detail="Today’s identification limit has been reached. Try again tomorrow.")
    monkeypatch.setattr(identify, "call_plantnet", over_limit)
    r = upload(client)
    assert r.status_code == 503 and "limit" in r.json()["detail"]


def test_rejects_non_images(client):
    assert upload(client, b"not an image", "text/plain").status_code == 400
    assert upload(client, b"not an image", "image/jpeg").status_code == 400
