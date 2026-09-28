"""API tests. They run against a separate database (plantassure_i3_test),
which is dropped and reloaded from data/plants.json first."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import load_data
import main

TEST_DB = "plantassure_i3_test"
GORSE, SNOWY_RIVER_WATTLE, GOLD_DUST_WATTLE = "Ulex europaeus", "Acacia boormanii", "Acacia acinacea"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    load_data.load(TEST_DB)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("DB_NAME", TEST_DB)
    with TestClient(main.app) as c:
        yield c


def plant_id(client, name):
    items = client.get("/api/v1/plants/search", params={"q": name}).json()["items"]
    return next(i["plantId"] for i in items if i["scientificName"] == name)


# ------------------------------------------------------------- plant data

def test_search_finds_common_and_scientific_names(client):
    names = {i["scientificName"] for i in client.get("/api/v1/plants/search", params={"q": "gorse"}).json()["items"]}
    assert GORSE in names


def test_filled_common_name_is_served(client):
    body = client.get(f"/api/v1/plants/{plant_id(client, SNOWY_RIVER_WATTLE)}/assessment").json()
    assert body["plant"]["commonName"] == "Snowy River Wattle"
    assert body["recommendation"]["level"] == "USE_CAUTION"


def test_catalogue_only_lists_rated_plants(client):
    body = client.get("/api/v1/plants", params={"size": 100}).json()
    assert body["totalElements"] == 325
    assert all(i["environmentalConcern"] != "NOT_ASSESSED" for i in body["items"])


def test_catalogue_filters(client):
    body = client.get("/api/v1/plants", params={"environmentalConcern": "LOWER", "originStatus": "NATIVE", "size": 100}).json()
    assert body["totalElements"] > 0
    assert all(i["environmentalConcern"] == "LOWER" and i["originStatus"] == "NATIVE" for i in body["items"])


def test_passport_matches_pipeline(client):
    p = client.get(f"/api/v1/plants/{plant_id(client, GORSE)}/passport").json()
    assert p["flowering"]["label"] == "Sep–Nov"
    assert p["flowering"]["months"][8:11] == [True, True, True]
    assert p["evidence"]["strength"] == "Strong"


def test_swaps_are_never_rated_risky(client):
    body = client.get(f"/api/v1/plants/{plant_id(client, GORSE)}/alternatives").json()
    assert body["status"] == "matched" and body["alternatives"]
    assert all(a["environmentalConcern"] in ("LOWER", "NOT_ASSESSED") for a in body["alternatives"])


def test_compare_two_plants(client):
    ids = f"{plant_id(client, GORSE)},{plant_id(client, GOLD_DUST_WATTLE)}"
    assert len(client.get("/api/v1/plants/compare", params={"plantIds": ids}).json()["plants"]) == 2


def test_insights_numbers(client):
    body = client.get("/api/v1/insights").json()
    assert body["flowering"]["total"] == 232
    assert body["origin"]["introduced"] == 268 and body["origin"]["native"] == 24


# ------------------------------------------------------------- gardens

def test_garden_round_trip(client):
    a, b = plant_id(client, GORSE), plant_id(client, GOLD_DUST_WATTLE)
    created = client.post("/api/v1/gardens", json={"plantIds": [a, b, a]})
    assert created.status_code == 201
    garden = created.json()
    assert set(garden) == {"gardenId", "plantIds", "updatedAt"}
    assert garden["plantIds"] == [a, b]  # duplicates removed
    gid = garden["gardenId"]
    assert client.put(f"/api/v1/gardens/{gid}", json={"plantIds": [b]}).json()["plantIds"] == [b]
    assert client.get(f"/api/v1/gardens/{gid}").json()["plantIds"] == [b]
    assert client.delete(f"/api/v1/gardens/{gid}").status_code == 204
    assert client.get(f"/api/v1/gardens/{gid}").status_code == 404


def test_each_garden_gets_a_different_random_id(client):
    ids = {client.post("/api/v1/gardens", json={"plantIds": []}).json()["gardenId"] for _ in range(5)}
    assert len(ids) == 5


@pytest.mark.parametrize("bad_id", ["1", "abc", "00000000-0000-0000-0000-000000000000"])
def test_guessable_or_invalid_ids_are_not_found(client, bad_id):
    assert client.get(f"/api/v1/gardens/{bad_id}").status_code == 404


def test_rejects_invalid_or_too_many_plants(client):
    assert client.post("/api/v1/gardens", json={"plantIds": list(range(1, 102))}).status_code == 422
    assert client.post("/api/v1/gardens", json={"plantIds": [0]}).status_code == 422
    assert client.post("/api/v1/gardens", json={"plantIds": [999999]}).status_code == 422


def test_gardens_expire_after_90_days(client, monkeypatch):
    gid = client.post("/api/v1/gardens", json={"plantIds": [1]}).json()["gardenId"]
    later = main.now() + timedelta(days=91)
    monkeypatch.setattr(main, "now", lambda: later)
    assert client.get(f"/api/v1/gardens/{gid}").status_code == 404
    assert main.delete_expired_gardens() >= 1


def test_update_resets_the_90_day_clock(client, monkeypatch):
    gid = client.post("/api/v1/gardens", json={"plantIds": [1]}).json()["gardenId"]
    start = main.now()
    monkeypatch.setattr(main, "now", lambda: start + timedelta(days=80))
    client.put(f"/api/v1/gardens/{gid}", json={"plantIds": [1, 2]})
    monkeypatch.setattr(main, "now", lambda: start + timedelta(days=150))
    assert client.get(f"/api/v1/gardens/{gid}").status_code == 200


def test_garden_tables_hold_no_personal_data(client):
    from db import cursor
    with cursor(TEST_DB) as cur:
        cur.execute("SHOW COLUMNS FROM garden")
        garden_cols = [r["Field"] for r in cur.fetchall()]
        cur.execute("SHOW COLUMNS FROM garden_plant")
        plant_cols = [r["Field"] for r in cur.fetchall()]
    assert garden_cols == ["garden_id", "updated_at"]
    assert plant_cols == ["garden_id", "plant_id", "position"]


# ------------------------------------------------------------- photos

def test_photos_come_with_a_credit(client):
    body = client.get(f"/api/v1/plants/{plant_id(client, GORSE)}/assessment").json()
    plant = body["plant"]
    assert plant["imageUrl"].startswith("https://inaturalist-open-data.s3.amazonaws.com/")
    assert plant["imageCredit"].startswith("Photo: ") and "via iNaturalist" in plant["imageCredit"]


def test_catalogue_items_include_photos(client):
    items = client.get("/api/v1/plants", params={"size": 50}).json()["items"]
    with_photo = [i for i in items if i["imageUrl"]]
    assert with_photo and all(i["imageCredit"] for i in with_photo)


def test_adding_photos_to_an_existing_database_is_safe(client):
    from db import cursor
    with cursor(TEST_DB) as cur:
        cur.execute("DELETE FROM plant_image")
    gid = client.post("/api/v1/gardens", json={"plantIds": [1]}).json()["gardenId"]
    assert load_data.ensure_images(TEST_DB) is True  # table was empty: photos added
    assert load_data.ensure_images(TEST_DB) is False  # second run: nothing changes
    assert client.get(f"/api/v1/gardens/{gid}").status_code == 200  # gardens untouched


def test_unrated_swaps_are_always_native(client):
    from db import cursor
    with cursor(TEST_DB) as cur:
        cur.execute("SELECT DISTINCT plant_id FROM plant_alternative")
        risky_ids = [r["plant_id"] for r in cur.fetchall()]
        cur.execute("SELECT plant_id, origin FROM plant")
        origin = {r["plant_id"]: r["origin"] for r in cur.fetchall()}
    for pid in risky_ids:
        for alt in client.get(f"/api/v1/plants/{pid}/alternatives").json()["alternatives"]:
            if alt["environmentalConcern"] == "NOT_ASSESSED":
                assert origin[alt["plantId"]] == "native"
