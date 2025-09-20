from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List
import sqlite3

app = FastAPI()

DATABASE = "inventory.db"

class Stock(BaseModel):
    sku: str
    location: str
    quantity: int

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS inventory (sku TEXT, location TEXT, quantity INTEGER, PRIMARY KEY(sku, location))"
    )
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/inventory", response_model=List[Dict])
def list_inventory(
    limit: int = Query(100, ge=1, le=1000, description="Max number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
):
    """
    List all inventory entries as a list of dicts, with pagination.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "SELECT sku, location, quantity FROM inventory LIMIT ? OFFSET ?",
        (limit, offset)
    )
    rows = c.fetchall()
    conn.close()
    return [{"sku": row[0], "location": row[1], "quantity": row[2]} for row in rows]

@app.get("/inventory/{sku}")
def get_inventory(sku: str):
    """
    Get all locations and quantities for a given SKU.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT location, quantity FROM inventory WHERE sku=?", (sku,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail="SKU not found")
    return {row[0]: row[1] for row in rows}

@app.post("/inventory/{sku}/adjust")
def adjust_inventory(sku: str, stock: Stock):
    """
    Adjust inventory for a SKU/location by a quantity amount (positive or negative).
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "SELECT quantity FROM inventory WHERE sku=? AND location=?", (sku, stock.location)
    )
    row = c.fetchone()
    if row:
        new_quantity = row[0] + stock.quantity
        if new_quantity < 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Insufficient stock")
        c.execute(
            "UPDATE inventory SET quantity=? WHERE sku=? AND location=?",
            (new_quantity, sku, stock.location),
        )
    else:
        if stock.quantity < 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Insufficient stock")
        c.execute(
            "INSERT INTO inventory (sku, location, quantity) VALUES (?, ?, ?)",
            (sku, stock.location, stock.quantity),
        )
    conn.commit()
    conn.close()
    # Placeholder: publish inventory change event here
    return {"sku": sku, "location": stock.location, "quantity": stock.quantity}

@app.delete("/inventory/{sku}")
def delete_sku(sku: str):
    """
    Delete all inventory entries for a specific SKU.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE sku=?", (sku,))
    changes = conn.total_changes
    conn.commit()
    conn.close()
    if changes == 0:
        raise HTTPException(status_code=404, detail="SKU not found")
    return {"detail": f"Deleted all locations for SKU {sku}."}

@app.delete("/inventory/{sku}/{location}")
def delete_sku_location(sku: str, location: str):
    """
    Delete inventory for a SKU at a specific location.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE sku=? AND location=?", (sku, location))
    changes = conn.total_changes
    conn.commit()
    conn.close()
    if changes == 0:
        raise HTTPException(status_code=404, detail="SKU/location not found")
    return {"detail": f"Deleted {sku} at {location}."}