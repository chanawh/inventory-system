from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
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

@app.get("/inventory/{sku}")
def get_inventory(sku: str):
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
