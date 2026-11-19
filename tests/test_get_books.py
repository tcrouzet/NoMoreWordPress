from pathlib import Path
import sqlite3
import sys
import unittest

TOOLS_DIR = str(Path(__file__).resolve().parents[1] / "tools")
sys.path.insert(0, TOOLS_DIR)
try:
    from db import Db
finally:
    sys.path.remove(TOOLS_DIR)


class GetBooksTests(unittest.TestCase):
    def setUp(self):
        self.db = Db.__new__(Db)
        self.db.site = "test"
        self.db.conn = sqlite3.connect(":memory:")
        self.db.conn.row_factory = sqlite3.Row
        self.db.conn.execute(
            """
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                site TEXT,
                type INTEGER,
                pub_date INTEGER,
                frontmatter TEXT
            )
            """
        )
        self.db.conn.executemany(
            "INSERT INTO posts VALUES (?, ?, ?, ?, ?)",
            [
                (1, "test", 2, 100, '{"slider": 1}'),
                (2, "test", 2, 200, '{"slider": 1}'),
                (3, "test", 2, 300, '{"slider": 0}'),
                (4, "test", 0, 400, '{"slider": 1}'),
                (5, "other", 2, 500, '{"slider": 1}'),
                (6, "test", 2, 600, '{"slider": "1"}'),
            ],
        )

    def tearDown(self):
        self.db.conn.close()

    def test_filters_books_by_yaml_frontmatter(self):
        books = self.db.get_books("slider=1")

        self.assertEqual([book["id"] for book in books], [6, 2, 1])

    def test_returns_all_site_books_without_a_filter(self):
        books = self.db.get_books()

        self.assertEqual([book["id"] for book in books], [6, 3, 2, 1])

    def test_rejects_malformed_filter(self):
        with self.assertRaises(ValueError):
            self.db.get_books("slider")

    def test_rejects_non_scalar_filter_value(self):
        with self.assertRaises(ValueError):
            self.db.get_books("slider=[]")


if __name__ == "__main__":
    unittest.main()
