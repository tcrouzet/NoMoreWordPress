from pathlib import Path
import sqlite3
import sys
import unittest

TOOLS_DIR = str(Path(__file__).resolve().parents[1] / 'tools')
sys.path.insert(0, TOOLS_DIR)
try:
    from db import Db
finally:
    sys.path.remove(TOOLS_DIR)


class LastPostsTests(unittest.TestCase):
    def setUp(self):
        self.db = Db.__new__(Db)
        self.db.site = 'test'
        self.db.conn = sqlite3.connect(':memory:')
        self.db.conn.row_factory = sqlite3.Row
        self.db.conn.executescript('''
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                site TEXT,
                type INTEGER,
                pub_date INTEGER,
                title TEXT,
                url TEXT
            );
            CREATE TABLE connectors (
                con_post_id INTEGER,
                con_tag_id INTEGER
            );
            CREATE TABLE tags (
                tag_id INTEGER PRIMARY KEY,
                tag_slug TEXT,
                tag_title TEXT,
                tag_url TEXT
            );
        ''')
        self.db.conn.executemany(
            'INSERT INTO tags VALUES (?, ?, ?, ?)',
            [
                (1, 'private', 'Private', '/private/'),
                (2, 'invisible', 'Invisible', '/invisible/'),
                (3, 'blog', 'Blog', '/blog/'),
                (4, 'velo', 'Vélo', '/borntobike/'),
            ],
        )
        self.db.conn.executemany(
            'INSERT INTO posts VALUES (?, ?, ?, ?, ?, ?)',
            [
                (1, 'test', 0, 100, 'Old', '/old/'),
                (2, 'test', 0, 200, 'Middle', '/middle/'),
                (3, 'test', 0, 300, 'Newest', '/newest/'),
                (4, 'test', 0, 400, 'Private', '/private-post/'),
                (5, 'test', 1, 500, 'Page', '/page/'),
                (6, 'test', 0, 600, 'Invisible', '/invisible-post/'),
            ],
        )
        self.db.conn.executemany(
            'INSERT INTO connectors VALUES (?, ?)',
            [(post_id, tag_id) for post_id, tag_id in (
                (1, 3), (2, 3), (3, 4), (4, 1), (5, 3), (6, 2)
            )],
        )

    def tearDown(self):
        self.db.conn.close()

    def test_returns_limited_newest_public_blog_posts(self):
        posts = self.db.get_last_posts(2)

        self.assertEqual([post['id'] for post in posts], [3, 2])
        self.assertEqual([post['title'] for post in posts], ['Newest', 'Middle'])

    def test_excludes_configured_tags(self):
        posts = self.db.get_last_posts(1, exclude_tags=['velo'])

        self.assertEqual([post['id'] for post in posts], [2])

    def test_rejects_negative_limit(self):
        with self.assertRaises(ValueError):
            self.db.get_last_posts(-1)


if __name__ == '__main__':
    unittest.main()
