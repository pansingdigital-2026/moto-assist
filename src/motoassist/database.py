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
    def save_profile(self, profile, replace=False):
        from .learning import validate_profile
        validate_profile(profile)
        sql="INSERT OR REPLACE" if replace else "INSERT"
        with self.connection:
            self.connection.execute(sql+" INTO profiles(id,circuit,category,model,weather,version,confidence,data_json) VALUES (?,?,?,?,?,?,?,?)", (profile["id"],profile["circuit"],profile["category"],profile["model"],profile["weather"],profile["version"],profile["confidence"],json.dumps(profile,allow_nan=False)))
    def profiles(self):
        return self.connection.execute("SELECT id,circuit,category,weather,confidence FROM profiles ORDER BY circuit").fetchall()
    def get_profile(self, identity):
        row=self.connection.execute("SELECT data_json FROM profiles WHERE id=?",(identity,)).fetchone()
        if not row:raise ValueError("Profile no longer exists")
        return json.loads(row[0])
    def delete_profile(self, identity):
        with self.connection:self.connection.execute("DELETE FROM profiles WHERE id=?",(identity,))
    def close(self): self.connection.close()
