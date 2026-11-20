from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from tools import tools as tool_helpers

TOOLS_DIR = str(Path(__file__).resolve().parents[1] / "tools")
sys.path.insert(0, TOOLS_DIR)
try:
    from db import Db
    from web import Web
finally:
    sys.path.remove(TOOLS_DIR)


class FrontmatterThumbTests(unittest.TestCase):
    def extract(self, body, metadata="", poster=0):
        source_text = (f"---\n{metadata}\n---\n" if metadata else "") + f"# Le billet\n\n{body}\n\n#blog #2026-11-20-12h00\n"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "billet.md"
            source.write_text(source_text, encoding="utf-8")
            db = Db.__new__(Db)
            db.poster = poster
            db.config = {
                "vault": directory, "vault_comments": "_comments", "pages": [],
                "canonical_domain": "https://example.test/", "tags": {"blog": {}},
            }
            with patch("db.tools", tool_helpers):
                post = db.markdown_extract(str(source), "2026/11/billet.md", 1795172400)
            self.assertEqual(source.read_text(encoding="utf-8"), source_text)
            return post

    def test_yaml_image_works_without_an_image_in_the_body(self):
        post = self.extract("Un billet sans illustration.", "image: _i/social.webp")
        self.assertEqual(post["thumb_path"], "_i/social.webp")
        self.assertEqual(post["thumb_legend"], "Le billet")
        self.assertFalse(BeautifulSoup(post["content"], "html.parser").select("img"))
        self.assertIn("Un billet sans illustration.", post["content"])

    def test_yaml_image_wins_and_keeps_all_body_images(self):
        body = "![Première](_i/first.webp)\n\nTexte.\n\n![Autre thumb](_i/marked.webp)"
        for poster in (0, 1):
            with self.subTest(poster=poster):
                post = self.extract(body, 'image: " _i/social.webp "\nbackground: _i/background.webp', poster)
                self.assertEqual(post["thumb_path"], "_i/social.webp")
                images = BeautifulSoup(post["content"], "html.parser").select("img")
                self.assertEqual([image["src"] for image in images], ["_i/first.webp", "_i/marked.webp"])

    def test_yaml_image_is_sent_to_media_production_without_body_images(self):
        post = self.extract("Un billet sans illustration.", "image: _i/social.webp\ncaption: Une légende choisie")
        web = Web.__new__(Web)
        web.db = Mock()
        web.source_images = Mock(return_value={"cached": True})
        templates = [{"name": "test"}]
        self.assertEqual(web.media_production(templates, post), 1)
        web.source_images.assert_called_once_with(templates, "_i/social.webp", post, legend="Une légende choisie", thumb=True)

    def test_yaml_caption_sets_the_thumb_legend_or_falls_back_to_the_title(self):
        for caption, expected in (("Une légende choisie", "Une légende choisie"), ("", "Le billet"), ('"   "', "Le billet")):
            with self.subTest(caption=caption):
                post = self.extract("Texte.", f"image: _i/social.webp\ncaption: {caption}")
                self.assertEqual(post["thumb_legend"], expected)

    def test_caption_without_yaml_image_keeps_the_image_alt_as_legend(self):
        post = self.extract("![Première](_i/first.webp)", "caption: Une autre légende")
        self.assertEqual(post["thumb_legend"], "Première")

    def test_yaml_caption_requires_text(self):
        with patch("builtins.print") as output, self.assertRaises(SystemExit):
            self.extract("Texte.", "image: _i/social.webp\ncaption: [légende1, légende2]")
        self.assertIn("caption", output.call_args.args[0])

    def test_missing_or_empty_yaml_image_keeps_image_selection(self):
        for metadata in ("", "image:", 'image: "   "'):
            with self.subTest(metadata=metadata):
                post = self.extract("![Première](_i/first.webp)", metadata)
                self.assertEqual(post["thumb_path"], "_i/first.webp")
                self.assertEqual(post["thumb_legend"], "Première")

    def test_without_yaml_image_the_explicit_marker_still_wins(self):
        body = "![Première](_i/first.webp)\n\nTexte.\n\n![Choisie thumb](_i/marked.webp)"
        for poster in (0, 1):
            with self.subTest(poster=poster):
                post = self.extract(body, poster=poster)
                self.assertEqual(post["thumb_path"], "_i/marked.webp")
                self.assertEqual(post["thumb_legend"], "Choisie")
                images = BeautifulSoup(post["content"], "html.parser").select("img")
                self.assertEqual(len(images), 2 if poster == 0 else 1)

    def test_yaml_image_requires_an_image_path(self):
        with patch("builtins.print") as output, self.assertRaises(SystemExit):
            self.extract("Texte.", "image: [image1.webp, image2.webp]")
        self.assertIn("image", output.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
