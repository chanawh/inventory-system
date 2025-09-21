import os
import pytest
from fastapi.testclient import TestClient
from src.main import app, init_db, DATABASE

client = TestClient(app)
API_KEY = os.environ.get("INVENTORY_API_KEY", "testkey")

def api_headers():
    return {"X-API-Key": API_KEY}

def print_inventory_state(label="Inventory State"):
    resp = client.get("/inventory", headers=api_headers())
    data = resp.json()
    print(f"\n--- {label} ---")
    print("{:10} | {:10} | {:8}".format("SKU", "Location", "Quantity"))
    print("-" * 32)
    if not data:
        print("{:10} | {:10} | {:8}".format("(no items)", "", ""))
    else:
        for item in data:
            print("{:10} | {:10} | {:8}".format(item['sku'], item['location'], item['quantity']))
    print("-" * 32)

@pytest.fixture(autouse=True)
def reset_db_and_show_inventory(request):
    print_inventory_state(f"Inventory BEFORE resetting for test: {request.node.name}")
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    init_db()
    yield
    print_inventory_state(f"Inventory AFTER test: {request.node.name}")

# --- Test /inventory (list & filter, pagination, offset) ---

@pytest.fixture
def seed_inventory():
    items = [
        {"sku": "SKU_A", "location": "loc1", "quantity": 10},
        {"sku": "SKU_B", "location": "loc2", "quantity": 20},
        {"sku": "SKU_C", "location": "loc1", "quantity": 5},
        {"sku": "SKU_A", "location": "loc2", "quantity": 3},
    ]
    for item in items:
        client.post(
            f"/inventory/{item['sku']}/adjust",
            json=item,
            headers=api_headers()
        )

@pytest.mark.parametrize(
    "query,expected_count,field_checks",
    [
        ("?limit=2", 2, {}),
        ("?limit=2&offset=2", 2, {}),
        ("?sku=SKU_A", 2, {"sku": "SKU_A"}),
        ("?location=loc1", 2, {"location": "loc1"}),
        ("?min_quantity=10", 2, {"quantity_min": 10}),
        ("?max_quantity=10", 3, {"quantity_max": 10}),
        ("?sku=SKU_A&location=loc2", 1, {"sku": "SKU_A", "location": "loc2"}),
        ("?limit=1&offset=3", 1, {}),
    ]
)
def test_inventory_list_parametrized(seed_inventory, query, expected_count, field_checks):
    resp = client.get(f"/inventory{query}", headers=api_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == expected_count
    for r in data:
        if "sku" in field_checks:
            assert r["sku"] == field_checks["sku"]
        if "location" in field_checks:
            assert r["location"] == field_checks["location"]
        if "quantity_min" in field_checks:
            assert r["quantity"] >= field_checks["quantity_min"]
        if "quantity_max" in field_checks:
            assert r["quantity"] <= field_checks["quantity_max"]

def test_list_inventory_empty():
    resp = client.get("/inventory", headers=api_headers())
    assert resp.status_code == 200
    assert resp.json() == []

# --- Test /inventory/{sku} (lookup by SKU) ---

def test_get_inventory_by_sku(seed_inventory):
    resp = client.get("/inventory/SKU_A", headers=api_headers())
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {"loc1", "loc2"}

def test_get_inventory_by_sku_not_found():
    resp = client.get("/inventory/NOT_EXIST", headers=api_headers())
    assert resp.status_code == 404

# --- Test /inventory/{sku}/adjust (add/remove) ---

def test_adjust_inventory_add_new():
    body = {"sku": "SKU_ADD", "location": "locA", "quantity": 5}
    resp = client.post("/inventory/SKU_ADD/adjust", json=body, headers=api_headers())
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 5

def test_adjust_inventory_remove_valid():
    body = {"sku": "SKU_X", "location": "locX", "quantity": 7}
    client.post("/inventory/SKU_X/adjust", json=body, headers=api_headers())
    resp = client.post("/inventory/SKU_X/adjust", json={"sku": "SKU_X", "location": "locX", "quantity": -4}, headers=api_headers())
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 3

def test_adjust_inventory_insufficient_stock():
    body = {"sku": "SKU_Y", "location": "locY", "quantity": 2}
    client.post("/inventory/SKU_Y/adjust", json=body, headers=api_headers())
    resp = client.post("/inventory/SKU_Y/adjust", json={"sku": "SKU_Y", "location": "locY", "quantity": -5}, headers=api_headers())
    assert resp.status_code == 400
    assert "Insufficient stock" in resp.json()["detail"]

# --- Test Batch Adjust ---

def test_batch_adjust_inventory():
    batch = [
        {"sku": "BATCH1", "location": "loc1", "quantity": 10},
        {"sku": "BATCH1", "location": "loc1", "quantity": -3},
        {"sku": "BATCH2", "location": "loc2", "quantity": -1},
        {"sku": "BATCH3", "location": "loc3", "quantity": 0},
    ]
    resp = client.post("/inventory/batch_adjust", json=batch, headers=api_headers())
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 4
    assert results[0]["success"] is True
    assert results[1]["success"] is True
    assert results[2]["success"] is False
    assert results[3]["success"] is True

# --- Test Delete ---

def test_delete_sku(seed_inventory):
    resp = client.delete("/inventory/SKU_B", headers=api_headers())
    assert resp.status_code == 200
    resp2 = client.get("/inventory?sku=SKU_B", headers=api_headers())
    assert resp2.json() == []

def test_delete_sku_not_found():
    resp = client.delete("/inventory/DOES_NOT_EXIST", headers=api_headers())
    assert resp.status_code == 404

def test_delete_sku_location(seed_inventory):
    resp = client.delete("/inventory/SKU_A/loc1", headers=api_headers())
    assert resp.status_code == 200
    resp2 = client.get("/inventory/SKU_A", headers=api_headers())
    assert "loc1" not in resp2.json()

def test_delete_sku_location_not_found():
    resp = client.delete("/inventory/FOO/loc999", headers=api_headers())
    assert resp.status_code == 404