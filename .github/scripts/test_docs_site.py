# Copyright (c) Infineon Technologies AG
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for docs_site.py. Run with: python -m unittest discover .github/scripts"""

import json
import tempfile
import unittest
from pathlib import Path

import docs_site


class SlugTest(unittest.TestCase):
    def test_matches_read_the_docs_slugs(self):
        self.assertEqual(docs_site.slugify("ifx-main"), "ifx-main")
        self.assertEqual(docs_site.slugify("feature/add-psoc-control"), "feature-add-psoc-control")
        self.assertEqual(docs_site.slugify("V1.2.0"), "v1.2.0")
        self.assertEqual(docs_site.slugify("fix//two  seps"), "fix-two-seps")
        self.assertEqual(docs_site.slugify("-/edge/-"), "edge")

    def test_rejects_ref_without_usable_characters(self):
        with self.assertRaises(docs_site.SiteError):
            docs_site.slugify("///")


class SiteTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.site = self.root / "site"
        self.site.mkdir()

    def build(self, marker):
        self.builds = getattr(self, "builds", 0) + 1
        html = self.root / f"html-{self.builds}"
        html.mkdir()
        (html / "index.html").write_text(marker, encoding="utf-8")
        (html / ".buildinfo").write_text("x", encoding="utf-8")
        return html

    def add(self, ref, ref_type, marker=None):
        return docs_site.add_version(
            self.site, self.build(marker or ref), ref, ref_type, "0" * 40, "ifx-main"
        )

    def manifest(self):
        return json.loads((self.site / "versions.json").read_text(encoding="utf-8"))

    def page(self, folder):
        return (self.site / folder / "index.html").read_text(encoding="utf-8")

    def test_latest_follows_default_branch(self):
        self.add("feature/x", "branch")
        self.assertNotIn("latest", self.manifest()["aliases"])
        self.add("ifx-main", "branch", "main v1")
        self.add("ifx-main", "branch", "main v2")
        self.assertEqual(self.manifest()["aliases"]["latest"], "ifx-main")
        self.assertEqual(self.page("latest"), "main v2")
        self.assertIn('url=latest/', (self.site / "index.html").read_text(encoding="utf-8"))

    def test_stable_is_newest_final_release(self):
        self.add("ifx-main", "branch")
        self.add("1.9.0", "tag")
        self.add("v1.10.0", "tag")
        self.add("2.0.0-rc1", "tag")
        manifest = self.manifest()
        self.assertEqual(manifest["aliases"]["stable"], "v1.10.0")
        self.assertEqual(self.page("stable"), "v1.10.0")
        self.assertEqual(
            [v["name"] for v in manifest["versions"]],
            ["v1.10.0", "1.9.0", "2.0.0-rc1", "ifx-main"],
        )
        self.assertIn('url=stable/', (self.site / "index.html").read_text(encoding="utf-8"))

    def test_removing_stable_release_falls_back_to_previous(self):
        self.add("1.0.0", "tag")
        self.add("1.1.0", "tag")
        self.assertTrue(docs_site.remove_version(self.site, "1.1.0", "tag", "ifx-main"))
        self.assertFalse((self.site / "1.1.0").exists())
        self.assertEqual(self.manifest()["aliases"]["stable"], "1.0.0")
        self.assertEqual(self.page("stable"), "1.0.0")
        self.assertTrue(docs_site.remove_version(self.site, "1.0.0", "tag", "ifx-main"))
        self.assertFalse((self.site / "stable").exists())
        self.assertFalse(docs_site.remove_version(self.site, "1.0.0", "tag", "ifx-main"))

    def test_rejects_slug_collisions_and_reserved_names(self):
        self.add("feature/a", "branch")
        with self.assertRaises(docs_site.SiteError):
            self.add("feature-a", "branch")
        with self.assertRaises(docs_site.SiteError):
            self.add("Stable", "branch")
        self.assertEqual(self.page("feature-a"), "feature/a")

    def test_build_byproducts_are_not_published(self):
        self.add("ifx-main", "branch")
        self.assertFalse((self.site / "ifx-main" / ".buildinfo").exists())


if __name__ == "__main__":
    unittest.main()
