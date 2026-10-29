import aiosqlite
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "navbat.db"
ACTIVE_STATUSES = ("waiting", "called")


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        );

        CREATE TABLE IF NOT EXISTS queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            organization_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (service_id) REFERENCES services(id)
        );

        CREATE INDEX IF NOT EXISTS idx_queues_user_status
        ON queues(user_id, status);

        CREATE INDEX IF NOT EXISTS idx_queues_status_created
        ON queues(status, created_at);

        CREATE INDEX IF NOT EXISTS idx_queues_org_status
        ON queues(organization_id, status);
        """)

        cur = await db.execute("SELECT COUNT(*) FROM organizations")
        if (await cur.fetchone())[0] == 0:
            stamp = now_text()
            await db.executemany(
                "INSERT INTO organizations(name, active, created_at) VALUES (?, 1, ?)",
                [("Namuna poliklinikasi", stamp), ("Namuna banki", stamp)],
            )

            cur = await db.execute("SELECT id, name FROM organizations")
            for org_id, org_name in await cur.fetchall():
                defaults = (
                    ["Terapevt qabuli", "Tahlil topshirish", "Kardiolog qabuli"]
                    if "poliklinika" in org_name.lower()
                    else ["Kassa xizmati", "Karta ochish", "Kredit bo‘yicha maslahat"]
                )
                await db.executemany(
                    """INSERT INTO services
                    (organization_id, name, active, created_at)
                    VALUES (?, ?, 1, ?)""",
                    [(org_id, name, stamp) for name in defaults],
                )

        await db.commit()


async def register_user(user_id: int, full_name: str, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users(user_id, full_name, username, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            full_name=excluded.full_name,
            username=excluded.username""",
            (user_id, full_name, username, now_text()),
        )
        await db.commit()


async def get_organizations():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT id, name FROM organizations
            WHERE active=1 ORDER BY name COLLATE NOCASE"""
        )
        return await cur.fetchall()


async def get_all_organizations():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name, active FROM organizations ORDER BY name COLLATE NOCASE"
        )
        return await cur.fetchall()


async def add_organization(name: str):
    name = name.strip()
    if not name:
        return None

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT OR IGNORE INTO organizations
            (name, active, created_at) VALUES (?, 1, ?)""",
            (name, now_text()),
        )

        if cur.rowcount == 0:
            cur = await db.execute(
                "SELECT id FROM organizations WHERE name=?", (name,)
            )
            row = await cur.fetchone()
            await db.commit()
            return row[0] if row else None

        await db.commit()
        return cur.lastrowid


async def rename_organization(org_id: int, new_name: str):
    new_name = new_name.strip()
    if not new_name:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE organizations SET name=? WHERE id=?",
            (new_name, org_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def set_organization_active(org_id: int, active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE organizations SET active=? WHERE id=?",
            (int(active), org_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_organization(org_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM queues WHERE organization_id=?",
            (org_id,),
        )
        if (await cur.fetchone())[0]:
            return False

        await db.execute(
            "DELETE FROM services WHERE organization_id=?",
            (org_id,),
        )
        cur = await db.execute(
            "DELETE FROM organizations WHERE id=?",
            (org_id,),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_services(org_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT id, name FROM services
            WHERE organization_id=? AND active=1
            ORDER BY name COLLATE NOCASE""",
            (org_id,),
        )
        return await cur.fetchall()


async def get_all_services(org_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT id, name, active FROM services
            WHERE organization_id=?
            ORDER BY name COLLATE NOCASE""",
            (org_id,),
        )
        return await cur.fetchall()


async def add_service(org_id: int, name: str):
    name = name.strip()
    if not name:
        return None

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM organizations WHERE id=? AND active=1",
            (org_id,),
        )
        if not await cur.fetchone():
            return None

        cur = await db.execute(
            "SELECT id FROM services WHERE organization_id=? AND name=?",
            (org_id, name),
        )
        existing = await cur.fetchone()
        if existing:
            return existing[0]

        cur = await db.execute(
            """INSERT INTO services
            (organization_id, name, active, created_at)
            VALUES (?, ?, 1, ?)""",
            (org_id, name, now_text()),
        )
        await db.commit()
        return cur.lastrowid


async def rename_service(service_id: int, new_name: str):
    new_name = new_name.strip()
    if not new_name:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE services SET name=? WHERE id=?",
            (new_name, service_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def set_service_active(service_id: int, active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE services SET active=? WHERE id=?",
            (int(active), service_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_service(service_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM queues WHERE service_id=?",
            (service_id,),
        )
        if (await cur.fetchone())[0]:
            return False

        cur = await db.execute(
            "DELETE FROM services WHERE id=?",
            (service_id,),
        )
        await db.commit()
        return cur.rowcount > 0


async def create_queue(user_id: int, org_id: int, service_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        cur = await db.execute(
            """SELECT id FROM queues
            WHERE user_id=? AND status IN ('waiting', 'called')
            LIMIT 1""",
            (user_id,),
        )
        if await cur.fetchone():
            return "ACTIVE_QUEUE"

        cur = await db.execute(
            """SELECT o.name, s.name
            FROM organizations o
            JOIN services s ON s.organization_id=o.id
            WHERE o.id=? AND s.id=?
            AND o.active=1 AND s.active=1""",
            (org_id, service_id),
        )
        pair = await cur.fetchone()
        if not pair:
            return None

        org_name, service_name = pair
        today = datetime.now().strftime("%Y-%m-%d")

        cur = await db.execute(
            """SELECT COUNT(*) FROM queues
            WHERE organization_id=? AND substr(created_at, 1, 10)=?""",
            (org_id, today),
        )
        number = f"{(await cur.fetchone())[0] + 1:03d}"
        stamp = now_text()

        cur = await db.execute(
            """INSERT INTO queues
            (number, user_id, organization_id, service_id,
             status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'waiting', ?, ?)""",
            (number, user_id, org_id, service_id, stamp, stamp),
        )
        queue_id = cur.lastrowid
        await db.commit()
        return queue_id, number, org_name, service_name, stamp


async def get_user_queue(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT q.id, q.number,
            CASE q.status
                WHEN 'waiting' THEN 'Kutilmoqda'
                WHEN 'called' THEN 'Chaqirildi'
                ELSE q.status
            END,
            o.name, s.name, q.created_at
            FROM queues q
            JOIN organizations o ON o.id=q.organization_id
            JOIN services s ON s.id=q.service_id
            WHERE q.user_id=?
            AND q.status IN ('waiting', 'called')
            ORDER BY q.id DESC LIMIT 1""",
            (user_id,),
        )
        return await cur.fetchone()


async def get_queue_position(queue_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT COUNT(*) FROM queues current
            JOIN queues earlier
            ON earlier.organization_id=current.organization_id
            AND earlier.status='waiting'
            AND earlier.id <= current.id
            WHERE current.id=? AND current.status='waiting'""",
            (queue_id,),
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def cancel_queue(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """UPDATE queues SET status='cancelled', updated_at=?
            WHERE user_id=? AND status IN ('waiting', 'called')""",
            (now_text(), user_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_statistics():
    today = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT COUNT(*),
            SUM(CASE WHEN status='waiting' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status='called' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status='done' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END)
            FROM queues WHERE substr(created_at, 1, 10)=?""",
            (today,),
        )
        row = await cur.fetchone()

        return {
            "total": row[0] or 0,
            "waiting": row[1] or 0,
            "called": row[2] or 0,
            "done": row[3] or 0,
            "cancelled": row[4] or 0,
        }


async def get_waiting_and_called_queues():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT q.id, q.number,
            CASE q.status WHEN 'waiting' THEN 'Kutilmoqda'
            ELSE 'Chaqirildi' END,
            q.user_id, u.full_name, o.name, s.name, q.created_at
            FROM queues q
            JOIN users u ON u.user_id=q.user_id
            JOIN organizations o ON o.id=q.organization_id
            JOIN services s ON s.id=q.service_id
            WHERE q.status IN ('waiting', 'called')
            ORDER BY CASE q.status WHEN 'called' THEN 0 ELSE 1 END,
            q.created_at ASC"""
        )
        return await cur.fetchall()


async def call_next_queue():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")

        cur = await db.execute(
            """SELECT q.id, q.user_id, q.number, o.name, s.name
            FROM queues q
            JOIN organizations o ON o.id=q.organization_id
            JOIN services s ON s.id=q.service_id
            WHERE q.status='waiting'
            ORDER BY q.created_at ASC, q.id ASC LIMIT 1"""
        )
        row = await cur.fetchone()

        if not row:
            await db.commit()
            return None

        cur = await db.execute(
            """UPDATE queues SET status='called', updated_at=?
            WHERE id=? AND status='waiting'""",
            (now_text(), row[0]),
        )
        await db.commit()
        return row if cur.rowcount else None


async def skip_queue(queue_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """UPDATE queues SET status='waiting', updated_at=?
            WHERE id=? AND status='called'""",
            (now_text(), queue_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_queue_by_id(queue_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT q.user_id, q.number, o.name, s.name
            FROM queues q
            JOIN organizations o ON o.id=q.organization_id
            JOIN services s ON s.id=q.service_id
            WHERE q.id=? AND q.status IN ('waiting', 'called')""",
            (queue_id,),
        )
        return await cur.fetchone()


async def finish_queue(queue_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """UPDATE queues SET status='done', updated_at=?
            WHERE id=? AND status IN ('waiting', 'called')""",
            (now_text(), queue_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def admin_cancel_queue(queue_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """UPDATE queues SET status='cancelled', updated_at=?
            WHERE id=? AND status IN ('waiting', 'called')""",
            (now_text(), queue_id),
        )
        await db.commit()
        return cur.rowcount > 0