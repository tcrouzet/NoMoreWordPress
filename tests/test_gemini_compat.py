import unittest

from tools.gemini_compat import md2gemini


class GeminiConversionTests(unittest.TestCase):
    def test_markdown_features(self):
        cases = [
            ('Texte simple', 'Texte simple'),
            ('[Texte](https://example.org)', '=> https://example.org Texte'),
            ('![Photo](_i/photo.webp)', '=> _i/photo.webp Photo'),
            ('Avant `code` après', 'code'),
            ('Avant **gras** et _italique_', 'italique'),
            ('> Une citation', '> Une citation'),
            ('- Un\n- Deux', '* Deux'),
            ('[Référence][ref]\n\n[ref]: https://example.org', '=> https://example.org Référence'),
            ('[ref]\n\n[ref]: https://example.org', '=> https://example.org ref'),
            ('[référence inconnue]', '[référence inconnue]'),
            ('Voir https://example.org', '=> https://example.org'),
            ('| Nom |\n| --- |\n| Test |', 'Test'),
        ]
        for markdown, expected in cases:
            with self.subTest(markdown=markdown):
                self.assertIn(expected, md2gemini(markdown, links='copy'))


if __name__ == '__main__':
    unittest.main()
