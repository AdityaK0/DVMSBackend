# apps/core/sqlite_cache.py
import sqlite3
import json
import os
import threading
from datetime import datetime, timedelta
from django.conf import settings

_lock = threading.Lock()  # process-level lock for writes

class SqliteCache:
    """
    Lightweight sqlite-based local cache helper.
    - uses raw sqlite3 (no Django ORM)
    - per-model sqlite DB paths configured in settings.SQLITE_CACHE_FILES
    - designed to be updated by event subscribers running in each instance
    """

    PRAGMAS = [
        ("journal_mode", "WAL"),
        ("synchronous", "NORMAL"),
    ]

    @staticmethod
    def ensure_dir():
        d = settings.SQLITE_CACHE_DIR
        os.makedirs(d, exist_ok=True)

    @staticmethod
    def get_db_path(model_name: str) -> str:
        return settings.SQLITE_CACHE_FILES.get(model_name)

    @staticmethod
    def get_conn(model_name: str):
        db_path = SqliteCache.get_db_path(model_name)
        if not db_path:
            raise RuntimeError("No sqlite cache path configured for model: %s" % model_name)

        # connect: each call uses its own connection; set timeout and row factory
        conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # apply pragmas (idempotent)
        for k, v in SqliteCache.PRAGMAS:
            try:
                cur.execute(f"PRAGMA {k}={v}")
            except sqlite3.OperationalError:
                pass
        return conn

    # ---- CRUD helpers ----
    @staticmethod
    def get(model_name: str, key_column: str, key_value, ttl_seconds: int = 0):
        """
        Returns dict (parsed JSON) or None.
        ttl_seconds: if >0, only return if not older than TTL.
        """
        try:
            conn = SqliteCache.get_conn(model_name)
            cur = conn.cursor()
            cur.execute(
                f"SELECT data, updated_at FROM cache_{model_name} WHERE {key_column} = ?",
                (key_value,),
            )
            row = cur.fetchone()
            conn.close()
            if not row:
                return None
            if ttl_seconds and row["updated_at"]:
                updated = datetime.fromisoformat(row["updated_at"])
                if datetime.utcnow() - updated > timedelta(seconds=ttl_seconds):
                    return None
            data = json.loads(row["data"])
            return data
        except Exception:
            return None

    @staticmethod
    def set(model_name: str, key_column: str, key_value, vendor_id, data_obj: dict):
        """
        Upsert JSON data into sqlite cache. data_obj is a Python dict (serializable).
        Uses a process-level lock to avoid contention in the same process.
        """
        SqliteCache.ensure_dir()
        db_path = SqliteCache.get_db_path(model_name)
        if not db_path:
            raise RuntimeError("No sqlite cache path configured for model: %s" % model_name)

        payload = json.dumps(data_obj, ensure_ascii=False)
        # Use upsert (ON CONFLICT) on unique key column (e.g., product_id UNIQUE)
        # Wrap in lock to avoid check-then-insert races within process.
        with _lock:
            conn = SqliteCache.get_conn(model_name)
            cur = conn.cursor()
            # Using column product_id as UNIQUE assumed in schema
            cur.execute(
                f"""
                INSERT INTO cache_{model_name} ({key_column}, vendor_id, data, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT({key_column}) DO UPDATE SET
                    vendor_id=excluded.vendor_id,
                    data=excluded.data,
                    updated_at=datetime('now')
                """,
                (key_value, vendor_id, payload),
            )
            conn.commit()
            conn.close()

    @staticmethod
    def delete(model_name: str, key_column: str, key_value):
        try:
            conn = SqliteCache.get_conn(model_name)
            cur = conn.cursor()
            cur.execute(f"DELETE FROM cache_{model_name} WHERE {key_column} = ?", (key_value,))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def scan_all(model_name: str, limit: int = 100, offset: int = 0):
        conn = SqliteCache.get_conn(model_name)
        cur = conn.cursor()
        cur.execute(
            f"SELECT {model_name}_id, vendor_id, data, updated_at FROM cache_{model_name} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cur.fetchall()
        conn.close()
        return [json.loads(r["data"]) for r in rows]
