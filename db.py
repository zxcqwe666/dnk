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
                created_at TEXT NOT NULL
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
    created_at = datetime.utcnow().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders (user_id, username, full_name, payload_json, total, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, full_name, payload_json, total, created_at),
        )
        await db.commit()
        return cursor.lastrowid


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

