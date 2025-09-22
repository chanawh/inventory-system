# ... (existing imports and code)

from fastapi import FastAPI, HTTPException, status, Body
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3

DATABASE = "orders.db"

app = FastAPI(
    title="Order Service API",
    description="API for placing and managing customer orders.",
    version="0.1.0",
)

class OrderItem(BaseModel):
    sku: str
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItem]

class Order(BaseModel):
    id: int
    items: List[OrderItem]
    status: str

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS order_items (order_id INTEGER, sku TEXT, quantity INTEGER)"
    )
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate):
    # TODO: Call inventory microservice to reserve/deduct stock
    # For now, just store the order
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO orders (status) VALUES (?)", ("pending",))
    order_id = c.lastrowid
    for item in order.items:
        c.execute(
            "INSERT INTO order_items (order_id, sku, quantity) VALUES (?, ?, ?)",
            (order_id, item.sku, item.quantity)
        )
    conn.commit()
    conn.close()
    return Order(id=order_id, items=order.items, status="pending")

# --- New endpoints below ---

@app.get("/orders", response_model=List[Order])
def list_orders():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, status FROM orders")
    orders = []
    for order_id, status in c.fetchall():
        c.execute("SELECT sku, quantity FROM order_items WHERE order_id=?", (order_id,))
        items = [OrderItem(sku=sku, quantity=quantity) for sku, quantity in c.fetchall()]
        orders.append(Order(id=order_id, items=items, status=status))
    conn.close()
    return orders

@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT status FROM orders WHERE id=?", (order_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    status = row[0]
    c.execute("SELECT sku, quantity FROM order_items WHERE order_id=?", (order_id,))
    items = [OrderItem(sku=sku, quantity=quantity) for sku, quantity in c.fetchall()]
    conn.close()
    return Order(id=order_id, items=items, status=status)