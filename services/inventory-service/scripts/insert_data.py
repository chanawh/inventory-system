import requests

BASE_URL = "http://127.0.0.1:8000"

def list_inventory():
    url = f"{BASE_URL}/inventory"
    response = requests.get(url)
    if response.status_code == 404:
        print("The /inventory endpoint was not found. Is the FastAPI server running the correct code?")
        return []
    response.raise_for_status()
    return response.json()

def get_inventory(sku):
    url = f"{BASE_URL}/inventory/{sku}"
    response = requests.get(url)
    if response.status_code == 404:
        print(f"SKU {sku} not found.")
        return None
    response.raise_for_status()
    return response.json()

def adjust_inventory(sku, location, quantity):
    url = f"{BASE_URL}/inventory/{sku}/adjust"
    payload = {
        "sku": sku,
        "location": location,
        "quantity": quantity
    }
    response = requests.post(url, json=payload)
    if response.status_code == 400:
        print(f"Insufficient stock for {sku} at {location}.")
        return None
    response.raise_for_status()
    return response.json()

def delete_sku(sku):
    url = f"{BASE_URL}/inventory/{sku}"
    response = requests.delete(url)
    if response.status_code == 404:
        print(f"SKU {sku} not found for deletion.")
        return None
    response.raise_for_status()
    return response.json()

def delete_sku_location(sku, location):
    url = f"{BASE_URL}/inventory/{sku}/{location}"
    response = requests.delete(url)
    if response.status_code == 404:
        print(f"SKU {sku} at {location} not found for deletion.")
        return None
    response.raise_for_status()
    return response.json()
    
def reset_inventory():
    url = f"{BASE_URL}/inventory"
    response = requests.get(url)
    if response.status_code == 404:
        print("The /inventory endpoint was not found.")
        return
    response.raise_for_status()
    all_inventory = response.json()
    for entry in all_inventory:
        sku = entry["sku"]
        location = entry["location"]
        delete_url = f"{BASE_URL}/inventory/{sku}/{location}"
        del_resp = requests.delete(delete_url)
        if del_resp.status_code == 404:
            print(f"SKU {sku} at {location} not found for deletion.")
        else:
            print(f"Deleted {sku} at {location}.")

if __name__ == "__main__":
    # Example data to insert
    inventory_updates = [
        # SKU001
        ("SKU001", "warehouse_a", 100),
        ("SKU001", "warehouse_b", 50),
        ("SKU001", "store1", 20),
        # SKU002
        ("SKU002", "warehouse_a", 150),
        ("SKU002", "store1", 30),
        ("SKU002", "store2", 75),
    ]
    
    print("Resetting inventory...")
    reset_inventory()

    print("Adjusting inventory...")
    for sku, location, quantity in inventory_updates:
        result = adjust_inventory(sku, location, quantity)
        if result:
            print(f"Adjusted: {result}")

    print("\nListing all inventory:")
    all_inventory = list_inventory()
    for entry in all_inventory:
        print(entry)

    print("\nGetting inventory for SKU001:")
    sku1 = get_inventory("SKU001")
    print(sku1)

    print("\nDeleting SKU002 at store2:")
    del_result = delete_sku_location("SKU002", "store2")
    print(del_result)

    print("\nDeleting all locations for SKU002:")
    del_result = delete_sku("SKU002")
    print(del_result)

    print("\nFinal inventory:")
    all_inventory = list_inventory()
    for entry in all_inventory:
        print(entry)