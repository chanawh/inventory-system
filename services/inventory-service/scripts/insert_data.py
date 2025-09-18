import requests

BASE_URL = "http://127.0.0.1:8000"

# Data to insert
inventory_updates = [
    # SKU001
    ("sku001", "warehouse_a", 100),
    ("sku001", "warehouse_b", 50),
    ("sku001", "store_1", 20),
    # SKU002
    ("sku002", "warehouse_a", 150),
    ("sku002", "store_1", 30),
    ("sku002", "store_2", 75),
]

for sku, location, quantity in inventory_updates:
    try:
        url = f"{BASE_URL}/inventory/{sku}/adjust"
        payload = {
            "sku": sku,
            "location": location,
            "quantity": quantity
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        print(f"Inserted: {payload}")
    except requests.exceptions.RequestException as e:
        print(f"Error inserting data: {e}")

print("Data insertion complete.")
