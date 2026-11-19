from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

from bs4 import BeautifulSoup
from liquid import Liquid

TOOLS_DIR = str(Path(__file__).resolve().parents[1] / "tools")
sys.path.insert(0, TOOLS_DIR)
try:
    from layout import Layout
finally:
    sys.path.remove(TOOLS_DIR)


class HomeGenBooksTests(unittest.TestCase):
    def test_home_template_renders_book_with_small_thumbnail_only(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "tcrouzet"
            / "home.liquid"
        )
        template = Liquid(str(template_path))
        rendered = template.render(
            post={},
            newsletter="",
            lastposts=[],
            books=[
                {
                    "url": "/book/",
                    "title": "Book",
                    "thumb": {"url_small": "/small/book.jpg"},
                }
            ],
        )
        soup = BeautifulSoup(rendered, "html.parser")
        link = soup.find("a", href="/book/")
        self.assertIsNotNone(link)
        self.assertEqual(link.find("img")["src"], "/small/book.jpg")

    def test_books_are_supercharged_without_loading_their_content(self):
        layout = Layout.__new__(Layout)
        layout.config = {
            "description": "Description",
            "home_title": "Home",
            "home_main_post_exclude": [],
        }
        template = {
            "name": "tcrouzet",
            "domain": "https://example.test/",
            "header": None,
            "footer": None,
            "newsletter": None,
            "home": None,
        }
        layout.templates = [template]
        layout.web = Mock()
        layout.web.db.get_last_posts.return_value = []
        layout.web.supercharge_posts.side_effect = (
            lambda _template, posts: [
                {**dict(post), "thumb": {"url_small": "/small/book.jpg"}}
                for post in posts
            ]
        )
        layout.web.supercharge_post.side_effect = (
            lambda _template, post: {
                **dict(post),
                "pub_update_str": "2026-11-19",
                "pub_update": 1,
                "thumb": None,
                "thumb_path": None,
                "thumb_legend": None,
            }
        )
        layout.header_html = Mock(return_value="")
        layout.footer_html = Mock(return_value="")
        layout.get_html = Mock(side_effect=["newsletter", "home"])
        layout.save = Mock()

        book = {
            "id": 1,
            "url": "/book/",
            "title": "Book",
            "content": "Book content",
            "thumb_path": "book.jpg",
        }
        layout.home_gen(
            last_post={"url": "/latest/"},
            books=[book],
        )

        home_context = layout.get_html.call_args_list[1].kwargs
        self.assertEqual(
            home_context["books"][0]["thumb"]["url_small"],
            "/small/book.jpg",
        )
        self.assertNotIn("content", home_context["books"][0])
        self.assertIn("content", book)


if __name__ == "__main__":
    unittest.main()
