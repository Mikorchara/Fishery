"""SQLite 持久化：传感器历史、事件日志。"""
import sqlite3
import threading
import time
import os

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.db")


class Storage:
    def __init__(self, db_path=_DB_PATH):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    temp REAL, ph REAL, oxygen REAL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)
            self._conn.commit()

    # ---- 传感器 ----

    def add_sensor(self, temp, ph, oxygen):
        try:
            t, p, o = float(temp), float(ph), float(oxygen)
        except (ValueError, TypeError):
            return
        with self._lock:
            self._conn.execute(
                "INSERT INTO sensor_history (ts, temp, ph, oxygen) VALUES (?,?,?,?)",
                (time.time(), t, p, o)
            )
            self._conn.commit()

    def get_sensor_history(self, minutes=120):
        cutoff = time.time() - minutes * 60
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, temp, ph, oxygen FROM sensor_history WHERE ts > ? ORDER BY ts",
                (cutoff,)
            ).fetchall()
        return [{"time": r[0], "temp": r[1], "ph": r[2], "oxygen": r[3]} for r in rows]

    # ---- 事件 ----

    def add_event(self, level, message):
        with self._lock:
            self._conn.execute(
                "INSERT INTO event_log (ts, level, message) VALUES (?,?,?)",
                (time.time(), level, message)
            )
            self._conn.commit()

    def get_events(self, limit=50, minutes=30):
        with self._lock:
            cutoff = time.time() - minutes * 60
            rows = self._conn.execute(
                "SELECT ts, level, message FROM event_log WHERE ts > ? ORDER BY ts DESC LIMIT ?",
                (cutoff, limit)
            ).fetchall()
        return [{"time": _fmt_time(r[0]), "level": r[1], "message": r[2]} for r in rows]

    def close(self):
        self._conn.close()


def _fmt_time(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts))
