"""Versioned profile storage; no fabricated circuits or learned profiles."""
import json
import sqlite3

class Database:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
          id TEXT PRIMARY KEY, circuit TEXT NOT NULL, category TEXT NOT NULL,
          model TEXT NOT NULL, weather TEXT NOT NULL, version INTEGER NOT NULL,
          confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
          data_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY, path TEXT NOT NULL, source TEXT NOT NULL,
          assistance_active INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        PRAGMA user_version=1;
        """)
    def record_session(self, path, source):
        with self.connection:
            self.connection.execute("INSERT OR IGNORE INTO sessions(id,path,source,assistance_active) VALUES (?,?,?,0)", (path.name, str(path), source))
    def sessions(self):
        return self.connection.execute("SELECT created_at,source,path FROM sessions ORDER BY created_at DESC").fetchall()
    def close(self): self.connection.close()
