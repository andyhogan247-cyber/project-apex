import sqlite3
from pathlib import Path


class ApexDatabase:

    def __init__(self):
        self.base_path = Path(__file__).parent
        self.db_path = self.base_path / "apex.db"
        self.schema_path = self.base_path / "schema.sql"

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def initialise(self):
        """Create database tables from schema.sql"""

        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema = f.read()

        self.connection.executescript(schema)
        self.connection.commit()

        print("✅ Database initialised")

    def execute(self, sql, params=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        self.connection.commit()
        return cursor

    def query(self, sql, params=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    def close(self):
        self.connection.close()


if __name__ == "__main__":
    db = ApexDatabase()
    db.initialise()
    db.close()