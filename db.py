import json
import os
from datetime import datetime
from typing import Any, Dict

import aiosqlite


DB_PATH = os.path.join(os.path.dirname(__file__), "dnk.sqlite3")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                payload_json TEXT NOT NULL,
                total INTEGER NOT NULL,
                status TEXT DEFAULT 'new',
                tracking_number TEXT,
                manager_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS order_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                shoe_size TEXT,
                clothing_size TEXT,
                city TEXT,
                delivery TEXT,
                phone TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def save_order(
    user_id: int,
    username: str | None,
    full_name: str | None,
    payload: Dict[str, Any],
) -> int:
    total = int(payload.get("total", 0))
    payload_json = json.dumps(payload, ensure_ascii=False)
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders (user_id, username, full_name, payload_json, total, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, full_name, payload_json, total, now, now),
        )
        await db.commit()
        order_id = cursor.lastrowid
        
        # Добавляем запись в историю статусов
        await db.execute(
            """
            INSERT INTO order_status_history (order_id, old_status, new_status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, None, 'new', now),
        )
        await db.commit()
        
        return order_id


async def update_order_status(
    order_id: int, 
    new_status: str, 
    comment: str = None,
    tracking_number: str = None,
    manager_notes: str = None
) -> bool:
    """Обновляет статус заказа и записывает в историю"""
    now = datetime.utcnow().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем текущий статус
        cursor = await db.execute(
            "SELECT status FROM orders WHERE id = ?", (order_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return False
        
        old_status = row[0]
        
        # Обновляем заказ
        update_fields = ["status = ?", "updated_at = ?"]
        update_values = [new_status, now]
        
        if tracking_number:
            update_fields.append("tracking_number = ?")
            update_values.append(tracking_number)
            
        if manager_notes:
            update_fields.append("manager_notes = ?")
            update_values.append(manager_notes)
        
        update_values.append(order_id)
        
        await db.execute(
            f"UPDATE orders SET {', '.join(update_fields)} WHERE id = ?",
            update_values,
        )
        
        # Добавляем в историю
        await db.execute(
            """
            INSERT INTO order_status_history (order_id, old_status, new_status, comment, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, old_status, new_status, comment, now),
        )
        
        await db.commit()
        return True


async def get_order_status_history(order_id: int) -> list[dict[str, Any]]:
    """Получает историю изменений статуса заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT old_status, new_status, comment, created_at
            FROM order_status_history
            WHERE order_id = ?
            ORDER BY created_at ASC
            """,
            (order_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def fetch_orders_by_status(status: str, limit: int = 50) -> list[dict[str, Any]]:
    """Получает заказы по статусу"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, username, full_name, total, status, tracking_number, created_at, updated_at
            FROM orders
            WHERE status = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (status, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def fetch_last_orders(limit: int = 10) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, username, full_name, total, created_at
            FROM orders
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def fetch_user_orders(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, total, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def fetch_order_by_id(order_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, username, full_name, total, payload_json, created_at
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def save_user_profile(
    user_id: int,
    username: str | None,
    full_name: str | None,
    profile: Dict[str, Any],
) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (
                user_id, username, full_name,
                shoe_size, clothing_size, city, delivery, phone,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                shoe_size=excluded.shoe_size,
                clothing_size=excluded.clothing_size,
                city=excluded.city,
                delivery=excluded.delivery,
                phone=excluded.phone,
                updated_at=excluded.updated_at
            """,
            (
                user_id,
                username,
                full_name,
                profile.get("shoe_size"),
                profile.get("clothing_size"),
                profile.get("city"),
                profile.get("delivery"),
                profile.get("phone"),
                now,
                now,
            ),
        )
        await db.commit()

