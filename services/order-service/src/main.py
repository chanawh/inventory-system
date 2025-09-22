from fastapi import FastAPI, HTTPException, status, Body
from pydantic import BaseModel, Field
from typing import List, Optional
import aiosqlite
import asyncio

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

@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate):
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.execute("INSERT INTO orders (status) VALUES (?)", ("pending",))
        order_id = cursor.lastrowid
        for item in order.items:
            await conn.execute(
                "INSERT INTO order_items (order_id, sku, quantity) VALUES (?, ?, ?)",
                (order_id, item.sku, item.quantity)
            )
        await conn.commit()
    return Order(id=order_id, items=order.items, status="pending")

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