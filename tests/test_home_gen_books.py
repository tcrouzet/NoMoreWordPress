from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
import csscompressor
from liquid import Liquid
from tools import tools as tool_helpers

TOOLS_DIR = str(Path(__file__).resolve().parents[1] / "tools")
sys.path.insert(0, TOOLS_DIR)
try:
    from layout import Layout
finally:
    sys.path.remove(TOOLS_DIR)


class HomeGenBooksTests(unittest.TestCase):
    def test_template_css_is_minified_and_selected_by_page(self):
        template_dir = Path(__file__).resolve().parents[1] / "templates" / "tcrouzet"
        expected_css = {
            path.stem: csscompressor.compress(path.read_text())
            for path in template_dir.glob("*.css")
        }

        for version in (0, 1):
            for inline in (True, False):
                with self.subTest(version=version, inline=inline):
                    config = {
                        "version": version,
                        "templates": [{
                            "name": "tcrouzet",
                            "domain": "https://example.test/",
                            "export": "/unused",
                            "inline_assets": inline,
                        }],
                    }
                    with patch("layout.tools", tool_helpers), patch.object(
                        Layout, "copy_assets", return_value=[]
                    ), patch.object(Layout, "_load_micro_executor", return_value=None):
                        layout = Layout(config, Mock())
                    template = layout.templates[0]
                    self.assertEqual(template["css"], expected_css)
                    for post, extra_styles in (
                        ({"is_home": True}, ["style_tags", "style_home"]),
                        ({"is_tag": True, "tag_slug": "book"}, ["style_book"]),
                        ({"type": 2}, ["style_book"]),
                        ({"is_tag": True, "tag_slug": "blog"}, ["style_tags"]),
                        ({"is_tag": True, "tag_slug": "series"}, ["style_tags"]),
                        ({"is_tag": True, "tag_slug": "2026"}, ["style_tags"]),
                        ({"type": 0}, []),
                        ({"type": 1}, []),
                        ({"title": "Recherche"}, []),
                        ({"type": 3, "canonical": "https://example.test/search/"}, ["style_search"]),
                        ({"is_tag": True, "tag_slug": "search", "canonical": "https://example.test/tag/search/"}, ["style_tags"]),
                    ):
                        rendered = layout.get_html(
                            template["header"],
                            post={"thumb": {}, "frontmatter": {}, **post},
                            blog=config,
                            template=template,
                        )
                        soup = BeautifulSoup(rendered, "html.parser")
                        styles = "".join(style.get_text() for style in soup.find_all("style"))
                        expected = ""
                        if inline:
                            expected = "".join(expected_css[name] for name in ["style", *extra_styles])
                        self.assertEqual(styles, expected)
                        links = [link["href"] for link in soup.select('link[rel="stylesheet"]')]
                        expected_links = [] if inline else [
                            f'/{name}.css?ver={config["version"]}' for name in ["style", *extra_styles]
                        ]
                        self.assertEqual(links, expected_links)

    def test_search_page_keeps_the_standard_page_wrapper_and_search_form(self):
        config = {
            "version": 1,
            "templates": [{
                "name": "tcrouzet", "domain": "https://example.test/", "export": "/unused",
            }],
        }
        with patch("layout.tools", tool_helpers), patch.object(
            Layout, "copy_assets", return_value=[]
        ), patch.object(Layout, "_load_micro_executor", return_value=None):
            layout = Layout(config, Mock())
        layout.save = Mock()
        layout.search_gen()
        soup = BeautifulSoup(layout.save.call_args.args[1], "html.parser")
        self.assertEqual(len(soup.find_all("main")), 1)
        self.assertEqual([h.get_text(strip=True) for h in soup.find_all("h1")], ["Recherche"])
        self.assertEqual([h.get_text(strip=True) for h in soup.select("#search h2")], ["Thématiques", "Liens"])
        form = soup.select_one('#search form[role="search"]')
        self.assertEqual(form["action"], "https://cse.google.com/cse/publicurl")
        self.assertEqual(form["method"], "get")
        self.assertEqual(form.select_one('input[name="cx"]')["value"], "d5dc254fba5984394")
        query = form.select_one('input[name="q"]')
        self.assertEqual(query["type"], "search")
        self.assertTrue(query.has_attr("required"))
        label = form.find("label", attrs={"for": query["id"]})
        self.assertTrue(query.get("aria-label") or (label and label.get_text(strip=True)))
        self.assertEqual(form.select_one("button")["type"], "submit")
        self.assertIn(layout.templates[0]["css"]["style_search"], soup.style.get_text())

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
