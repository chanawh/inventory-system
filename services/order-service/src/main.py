import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List
import aiosqlite
import httpx

DATABASE = "orders.db"

INVENTORY_URL = os.environ.get("INVENTORY_SERVICE_URL", "http://localhost:8000")
INVENTORY_API_KEY = os.environ.get("INVENTORY_API_KEY", "testkey")

app = FastAPI(
    title="Order Service API",
    description="API for placing and managing customer orders.",
    version="0.2.0",
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

async def init_db():
    async with aiosqlite.connect(DATABASE) as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT)"
        )
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS order_items (order_id INTEGER, sku TEXT, quantity INTEGER)"
        )
        await conn.commit()

@app.on_event("startup")
async def startup():
    await init_db()

async def reserve_inventory(items: List[OrderItem]) -> None:
    url = f"{INVENTORY_URL}/inventory/batch_adjust"
    headers = {"X-API-Key": INVENTORY_API_KEY}
    # Always try to decrement from 'warehouse_a' (can be improved for multiple locations)
    payload = [
        {"sku": item.sku, "location": "warehouse_a", "quantity": -item.quantity}
        for item in items
    ]
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=5.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Inventory service did not respond as expected.")
        results = resp.json()
        # Find any failures
        failed = [r for r in results if not r.get("success")]
        if failed:
            reasons = ", ".join(
                f"{r['sku']}@{r['location']}: {r.get('error', 'error')}" for r in failed
            )
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient inventory: {reasons}"
            )

@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate):
    # 1. Reserve inventory first!
    await reserve_inventory(order.items)
    # 2. If successful, create order in DB
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.execute("INSERT INTO orders (status) VALUES (?)", ("confirmed",))
        order_id = cursor.lastrowid
        for item in order.items:
            await conn.execute(
                "INSERT INTO order_items (order_id, sku, quantity) VALUES (?, ?, ?)",
                (order_id, item.sku, item.quantity)
            )
        await conn.commit()
    return Order(id=order_id, items=order.items, status="confirmed")

@app.get("/orders", response_model=List[Order])
async def list_orders():
    orders = []
    async with aiosqlite.connect(DATABASE) as conn:
        async with conn.execute("SELECT id, status FROM orders") as cursor:
            order_rows = await cursor.fetchall()
            for order_id, status in order_rows:
                async with conn.execute("SELECT sku, quantity FROM order_items WHERE order_id=?", (order_id,)) as items_cursor:
                    items_rows = await items_cursor.fetchall()
                    items = [OrderItem(sku=sku, quantity=quantity) for sku, quantity in items_rows]
                orders.append(Order(id=order_id, items=items, status=status))
    return orders

@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: int):
    async with aiosqlite.connect(DATABASE) as conn:
        async with conn.execute("SELECT status FROM orders WHERE id=?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Order not found")
            status = row[0]
        async with conn.execute("SELECT sku, quantity FROM order_items WHERE order_id=?", (order_id,)) as items_cursor:
            items_rows = await items_cursor.fetchall()
            items = [OrderItem(sku=sku, quantity=quantity) for sku, quantity in items_rows]
    return Order(id=order_id, items=items, status=status)