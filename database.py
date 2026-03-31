import aiosqlite
from datetime import datetime, timezone

DB_PATH = "businesses.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id     TEXT UNIQUE,
                name         TEXT NOT NULL,
                category     TEXT,
                address      TEXT,
                phone        TEXT,
                rating       REAL,
                review_count INTEGER,
                website      TEXT,
                lat          REAL,
                lon          REAL,
                first_seen   TEXT,
                last_seen    TEXT
            )
        """)
        await db.commit()


async def upsert_business(b: dict):
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO businesses
                (place_id, name, category, address, phone, rating, review_count, website, lat, lon, first_seen, last_seen)
            VALUES
                (:place_id, :name, :category, :address, :phone, :rating, :review_count, :website, :lat, :lon, :first_seen, :last_seen)
            ON CONFLICT(place_id) DO UPDATE SET
                last_seen    = excluded.last_seen,
                rating       = excluded.rating,
                review_count = excluded.review_count,
                phone        = COALESCE(excluded.phone, businesses.phone),
                website      = COALESCE(excluded.website, businesses.website)
        """, {**b, "first_seen": now, "last_seen": now})
        await db.commit()


async def get_all_businesses() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM businesses ORDER BY last_seen DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
