from copy import deepcopy
from pathlib import Path
import sys
import unittest

from bs4 import BeautifulSoup
import tools  # Keep script imports from shadowing the package used by other tests.

TOOLS_DIR = str(Path(__file__).resolve().parents[1] / "tools")
sys.path.insert(0, TOOLS_DIR)
try:
    from layout import Layout, make_liquid_loader, without_image
finally:
    sys.path.remove(TOOLS_DIR)


class BookCoverTemplateTests(unittest.TestCase):
    def render(self, content, post_type=2, thumb=True):
        post = {
            "type": post_type,
            "title": "Un livre",
            "frontmatter": {},
            "content": content,
            "thumb": {
                "url": "/covers/book.webp", "width": 600, "height": 900,
                "legend": "Couverture", "jpeg": "/social/book.jpg",
            } if thumb else None,
        }
        original = deepcopy(post)
        template_dir = Path(__file__).resolve().parents[1] / "templates/tcrouzet"
        template = make_liquid_loader(str(template_dir))("article")
        rendered = Layout.__new__(Layout).get_html(template, post=post, template={"sizes": ""}, share="")
        self.assertEqual(post, original)
        return BeautifulSoup(rendered, "html.parser")

    def test_selected_cover_is_shown_once_and_other_images_are_kept(self):
        content = '<p>Introduction.</p><figure><img src="/inside/book.webp"><figcaption>Autre image</figcaption></figure><a href="/original/"><figure><img src="/covers/book.webp"><figcaption>Légende de la couverture</figcaption></figure></a><p>Conclusion.</p>'
        soup = self.render(content)
        self.assertEqual([image["src"] for image in soup.select("img")], ["/covers/book.webp", "/inside/book.webp"])
        self.assertEqual(len(soup.select("img.book")), 1)
        self.assertNotIn("Légende de la couverture", soup.get_text())
        self.assertIn("Autre image", soup.get_text())
        self.assertIn("Introduction.", soup.get_text())
        self.assertIn("Conclusion.", soup.get_text())
        self.assertFalse(soup.select('a[href="/original/"]'))

    def test_cover_only_content_does_not_reappear_as_a_fallback(self):
        soup = self.render('<p><a href="/original/"><img src="/covers/book.webp"></a></p>')
        self.assertEqual(len(soup.select("img")), 1)
        self.assertFalse(soup.select('a[href="/original/"]'))

    def test_article_or_book_without_generated_cover_keeps_its_image(self):
        content = '<figure><img src="/covers/book.webp"><figcaption>Image du texte</figcaption></figure>'
        for post_type, thumb in ((0, True), (1, True), (2, False)):
            with self.subTest(post_type=post_type, thumb=thumb):
                soup = self.render(content, post_type, thumb)
                self.assertEqual(len(soup.select("img")), 1)
                self.assertIn("Image du texte", soup.get_text())

    def test_filter_preserves_surrounding_text_and_shared_figures(self):
        content = '<p>Avant <a href="/original/"><img src="/covers/book.webp"></a> après <a href="/lire/">lire</a>.</p><figure><img src="/covers/book.webp"><img src="/inside/other.webp"><figcaption>Deux images</figcaption></figure>'
        soup = BeautifulSoup(without_image(content, "/covers/book.webp"), "html.parser")
        self.assertEqual([image["src"] for image in soup.select("img")], ["/inside/other.webp"])
        self.assertIn("Avant", soup.p.get_text())
        self.assertIn("après", soup.p.get_text())
        self.assertIsNotNone(soup.select_one('a[href="/lire/"]'))
        self.assertIsNotNone(soup.select_one("figure figcaption"))
        self.assertFalse(soup.select('a[href="/original/"]'))

    def test_filter_without_matching_url_leaves_content_unchanged(self):
        content = "<p>Texte <img src='/covers/book.webp'></p>"
        for url in (None, "", "/inside/book.webp"):
            with self.subTest(url=url):
                self.assertEqual(without_image(content, url), content)


if __name__ == "__main__":
    unittest.main()
