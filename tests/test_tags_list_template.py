from pathlib import Path
from datetime import datetime, timezone
import unittest

from bs4 import BeautifulSoup
from liquid import Liquid


class TagsListTemplateTests(unittest.TestCase):
    def test_series_lists_only_categories_even_when_the_latest_article_is_shared(self):
        template_path = Path(__file__).resolve().parents[1] / "templates/tcrouzet/tags_list.liquid"
        categories = [("Vélo", "/borntobike/"), ("Carnets", "/carnet-de-route/"), ("Édition", "/tag/edition/")]
        rendered = Liquid(str(template_path)).render(
            post={"tag_slug": "series"},
            tags=[{
                "tag_title": title,
                "tag_url": url,
                "title": "Le même dernier article",
                "url": "/dernier-article/",
                "pub_date_str": "2026-11-19",
                "navigation": {},
            } for title, url in categories],
        )
        soup = BeautifulSoup(rendered, "html.parser")
        links = soup.select("li a")
        self.assertEqual([(link.get_text(strip=True), link["href"]) for link in links], categories)
        self.assertEqual(len(soup.select("li")), len(categories))
        self.assertNotIn("Le même dernier article", soup.get_text())
        self.assertEqual([date.get_text(strip=True) for date in soup.select("time")], ["19.11.2026"] * len(categories))
        self.assertFalse(soup.select("li > span"))
        self.assertIsNotNone(soup.select_one('ol[aria-label="Catégories"]'))

    def test_series_keeps_latest_article_dates_and_category_order(self):
        template_path = Path(__file__).resolve().parents[1] / "templates/tcrouzet/tags_list.liquid"
        categories = [
            {"tag_title": "Vélo", "tag_url": "/borntobike/", "pub_date": int(datetime(2026, 11, 19, 12, tzinfo=timezone.utc).timestamp())},
            {"tag_title": "Carnets", "tag_url": "/carnet-de-route/", "pub_date": int(datetime(2026, 11, 18, 12, tzinfo=timezone.utc).timestamp())},
        ]
        soup = BeautifulSoup(Liquid(str(template_path)).render(post={"tag_slug": "series"}, tags=categories), "html.parser")
        self.assertEqual([link.get_text(strip=True) for link in soup.select("li a")], ["Vélo", "Carnets"])
        self.assertEqual([date["datetime"] for date in soup.select("time")], ["2026-11-19", "2026-11-18"])
        self.assertEqual([date.get_text(strip=True) for date in soup.select("time")], ["19.11.2026", "18.11.2026"])

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
