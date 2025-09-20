from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, RootModel
from typing import Dict, List, Optional
import sqlite3

app = FastAPI(
    title="Inventory Service API",
    description="API for tracking inventory by SKU and location, with filtering, pagination, and adjustment capabilities.",
    version="1.1.0",
)

DATABASE = "inventory.db"

class Stock(BaseModel):
    sku: str
    location: str
    quantity: int

class InventoryItem(BaseModel):
    sku: str
    location: str
    quantity: int

class InventoryByLocation(RootModel[Dict[str, int]]):
    pass

class MessageResponse(BaseModel):
    detail: str

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

@app.get(
    "/inventory",
    response_model=List[InventoryItem],
    tags=["Inventory"],
    description="List all inventory entries, with optional filtering by SKU, location, quantity range, and pagination."
)
def list_inventory(
    sku: Optional[str] = Query(None, description="Filter by SKU"),
    location: Optional[str] = Query(None, description="Filter by location"),
    min_quantity: Optional[int] = Query(None, ge=0, description="Minimum quantity"),
    max_quantity: Optional[int] = Query(None, ge=0, description="Maximum quantity"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
):
    """
    List all inventory entries as a list of dicts, with filtering and pagination.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Build WHERE clause dynamically
    where = []
    params = []

    if sku:
        where.append("sku=?")
        params.append(sku)
    if location:
        where.append("location=?")
        params.append(location)
    if min_quantity is not None:
        where.append("quantity>=?")
        params.append(min_quantity)
    if max_quantity is not None:
        where.append("quantity<=?")
        params.append(max_quantity)

    where_clause = " WHERE " + " AND ".join(where) if where else ""
    sql = f"SELECT sku, location, quantity FROM inventory{where_clause} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(sql, tuple(params))
    rows = c.fetchall()
    conn.close()
    return [InventoryItem(sku=row[0], location=row[1], quantity=row[2]) for row in rows]

@app.get(
    "/inventory/{sku}",
    response_model=InventoryByLocation,
    tags=["Inventory"],
    description="Get all locations and quantities for a given SKU."
)
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

@app.post(
    "/inventory/{sku}/adjust",
    response_model=InventoryItem,
    tags=["Inventory Adjustment"],
    description="Adjust inventory for a SKU/location by a quantity amount (positive or negative)."
)
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
        returned_quantity = new_quantity
    else:
        if stock.quantity < 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Insufficient stock")
        c.execute(
            "INSERT INTO inventory (sku, location, quantity) VALUES (?, ?, ?)",
            (sku, stock.location, stock.quantity),
        )
        returned_quantity = stock.quantity
    conn.commit()
    conn.close()
    # Placeholder: publish inventory change event here
    return InventoryItem(sku=sku, location=stock.location, quantity=returned_quantity)

@app.delete(
    "/inventory/{sku}",
    response_model=MessageResponse,
    tags=["Inventory"],
    description="Delete all inventory entries for a specific SKU."
)
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
    return MessageResponse(detail=f"Deleted all locations for SKU {sku}.")

@app.delete(
    "/inventory/{sku}/{location}",
    response_model=MessageResponse,
    tags=["Inventory"],
    description="Delete inventory for a SKU at a specific location."
)
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
    return MessageResponse(detail=f"Deleted {sku} at {location}.")