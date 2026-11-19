from pathlib import Path
import unittest

from bs4 import BeautifulSoup
from liquid import Liquid


class TagsListTemplateTests(unittest.TestCase):
    def test_blog_category_links_use_each_posts_navigation(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "tcrouzet"
            / "tags_list.liquid"
        )
        template = Liquid(str(template_path))
        rendered = template.render(
            post={"tag_slug": "blog"},
            tags=[
                {
                    "url": "/article/",
                    "title": "Article",
                    "pub_date_str": "20261119",
                    "navigation": {
                        "title": "Vélo",
                        "url": "/borntobike/",
                    },
                }
            ],
        )
        soup = BeautifulSoup(rendered, "html.parser")
        category_link = soup.select_one("li > span > a")

        self.assertIsNotNone(category_link)
        self.assertEqual(category_link["href"], "/borntobike/")
        self.assertEqual(category_link.get_text(strip=True), "Vélo")


if __name__ == "__main__":
    unittest.main()
