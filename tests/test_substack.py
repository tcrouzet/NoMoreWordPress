import csv
import datetime
from pathlib import Path
import tempfile
import unittest

from tools.substack import Substack


class SubstackTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.date = datetime.datetime(2026, 11, 20, 12, tzinfo=datetime.timezone.utc)

    def entry(self, title, slug, date="2026-11-20T12:00:00Z", published="true"):
        return {"post_id": f"123.{slug}", "post_date": date, "title": title, "is_published": published}

    def service(self, entries=(), corrections=()):
        export = self.directory / "posts.csv"
        manual = self.directory / "corrections.csv"
        for path, fields, rows in (
            (export, ["post_id", "post_date", "title", "is_published"], entries),
            (manual, ["titre_source", "slug_substack"], corrections),
        ):
            with path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        return Substack({
            "substack_fr": "https://tcrouzet.substack.com/",
            "substack_727": "https://727bikepacking.substack.com/",
            "substack_post_csv": str(export),
            "substack_slug_csv": str(manual),
        })

    def test_manual_correction_has_priority_and_normalizes_typography(self):
        service = self.service(
            [self.entry("Rien ne remplacera le plaisir d’écrire ?", "export-slug")],
            [{"titre_source": "Rien ne remplacera le plaisir d’écrire\u00a0?", "slug_substack": " bon-slug "}],
        )
        self.assertEqual(service.guess({"title": "rien ne remplacera le plaisir d'écrire?"}),
                         "https://tcrouzet.substack.com/p/bon-slug")

    def test_exact_export_title_preserves_the_real_long_slug(self):
        title = "Contre l’industrialisation de la littérature"
        slug = "contre-lindustrialisation-de-la-litterature"
        service = self.service([self.entry(title, slug)])
        self.assertEqual(service.guess({"title": title, "pub_date": self.date.timestamp()}),
                         f"https://tcrouzet.substack.com/p/{slug}")

    def test_unique_exact_title_can_match_a_republication_without_matching_dates(self):
        service = self.service([self.entry("Avril 1999", "avril-1999-journal-decriture")])
        for date in (None, "1999-04-30"):
            with self.subTest(date=date):
                self.assertEqual(service.guess({"title": "Avril 1999", "pub_date_str": date}),
                                 "https://tcrouzet.substack.com/p/avril-1999-journal-decriture")

    def test_fuzzy_lookup_uses_the_actual_post_date_fields(self):
        service = self.service([self.entry("J’IAccuse", "jiacuse")])
        for field, value in (("pub_date", self.date.timestamp()),
                             ("pub_date_str", self.date.isoformat()),
                             ("post_date", self.date.isoformat())):
            with self.subTest(field=field):
                self.assertEqual(service.guess({"title": "J’accuse", field: value}),
                                 "https://tcrouzet.substack.com/p/jiacuse")

    def test_duplicate_titles_are_disambiguated_by_date(self):
        service = self.service([
            self.entry("ConstellationW", "constellationw", "2006-04-10T06:14:00Z"),
            self.entry("ConstellationW", "constellationw-2", "2006-04-13T08:45:00Z"),
        ])
        self.assertEqual(service.guess({"title": "ConstellationW", "pub_date_str": "2006-04-13"}),
                         "https://tcrouzet.substack.com/p/constellationw-2")
        self.assertIsNone(service._lookup_csv_slug("ConstellationW"))

    def test_equally_likely_matches_are_not_chosen_arbitrarily(self):
        service = self.service([
            self.entry("Un récit d’écriture A", "version-a"),
            self.entry("Un récit d’écriture B", "version-b"),
        ])
        self.assertIsNone(service._lookup_csv_slug("Un récit d’écriture", self.date))

    def test_unrelated_titles_and_outdated_fuzzy_candidates_keep_the_fallback(self):
        for title, date in (("Une recette de tarte", "2026-11-20"), ("J’IAccuse", "2020-01-01")):
            with self.subTest(title=title):
                service = self.service([self.entry(title, "mauvais-slug", date)])
                self.assertEqual(service.guess({"title": "J’accuse", "pub_date": self.date.timestamp()}),
                                 "https://tcrouzet.substack.com/p/jaccuse")

    def test_drafts_and_malformed_ids_are_ignored(self):
        service = self.service([
            self.entry("J’accuse", "brouillon", published="false"),
            {**self.entry("J’accuse", "invalide"), "post_id": "sans-separateur"},
        ])
        self.assertEqual(service.guess({"title": "J’accuse", "pub_date": self.date.timestamp()}),
                         "https://tcrouzet.substack.com/p/jaccuse")

    def test_bike_routing_missing_titles_and_non_posts_are_preserved(self):
        service = self.service(corrections=[{"titre_source": "Une sortie", "slug_substack": "sortie"}])
        for tags in (["velo"], '["velo"]', 'velo'):
            with self.subTest(tags=tags):
                self.assertEqual(service.guess({"title": "Une sortie", "tags": tags}),
                                 "https://727bikepacking.substack.com/p/sortie")
        self.assertEqual(service.guess({"title": None}), "")
        self.assertEqual(service.guess({"title": "Un livre", "type": 2}), "")

    def test_legacy_export_without_titles_still_uses_slug_similarity(self):
        service = self.service([self.entry("", "jiaccuse")])
        Path(service.substack_post_csv).write_text("post_id,post_date\n123.jiaccuse,2026-11-20T12:00:00Z\n", encoding="utf-8")
        self.assertEqual(service.guess({"title": "J’IAccuse", "pub_date_str": self.date.isoformat()}),
                         "https://tcrouzet.substack.com/p/jiaccuse")

    def test_csv_paths_expand_home_and_resolve_relative_to_the_project(self):
        service = Substack({"substack_post_csv": "~/export/posts.csv", "substack_slug_csv": "sites/substack.csv"})
        self.assertEqual(Path(service.substack_post_csv), Path.home() / "export/posts.csv")
        self.assertEqual(Path(service.slug_path), Path(__file__).resolve().parents[1] / "sites/substack.csv")

    def test_missing_files_keep_the_heuristic_fallback(self):
        service = Substack({"substack_fr": "https://example.test", "substack_post_csv": str(self.directory / "absent.csv")})
        self.assertEqual(service.guess({"title": "Un billet", "pub_date": self.date.timestamp()}),
                         "https://example.test/p/un-billet")

    def test_date_normalization_supports_timestamps_and_iso_dates(self):
        service = self.service()
        for value in (self.date, self.date.date(), self.date.timestamp(), self.date.isoformat(), "2026-11-20"):
            with self.subTest(value=value):
                self.assertEqual(service._extract_date_key(value), "2026-11-20")
        self.assertIsNone(service._extract_date_key("date invalide"))
        self.assertEqual(service._extract_date_key("2026-11-20T00:30:00+02:00"), "2026-11-19")


if __name__ == "__main__":
    unittest.main()
