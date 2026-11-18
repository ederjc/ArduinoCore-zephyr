#!/usr/bin/env python3
# Copyright (c) Infineon Technologies AG
#
# SPDX-License-Identifier: Apache-2.0

"""Maintain the versioned documentation site published on GitHub Pages.

Every branch and release tag is published into its own folder, named after
the Read the Docs style slug of the Git ref, so existing URL paths keep their
shape:

    <site>/versions.json        manifest of all published versions
    <site>/index.html           redirect to stable/ (or latest/)
    <site>/404.html             "page not found" with links to valid versions
    <site>/<slug>/              docs built from one branch or tag
    <site>/latest/              copy of the default branch docs
    <site>/stable/              copy of the newest release tag docs

The manifest is the single source of truth; aliases, the root redirect and
the 404 page are regenerated from it on every change.
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import shutil
import sys
from pathlib import Path

MANIFEST = "versions.json"
ALIASES = ("latest", "stable")
RESERVED = frozenset(ALIASES) | {MANIFEST, "index.html", "404.html"}
RELEASE_TAG = re.compile(r"^v?(\d+(?:\.\d+)*)$")
# Sphinx build byproducts that must not be published.
BUILD_BYPRODUCTS = (".buildinfo", ".doctrees")


class SiteError(Exception):
    """Raised when a requested change would corrupt the published site."""


def slugify(ref: str) -> str:
    """Return the URL folder name for a Git ref, as Read the Docs does.

    The name is lowercased, every run of characters outside ``a-z0-9._-``
    becomes a single ``-``, and leading/trailing separators are dropped.
    """
    slug = re.sub(r"[^a-z0-9._-]+", "-", ref.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-._")
    if not slug:
        raise SiteError(f"Ref {ref!r} does not produce a usable URL slug.")
    return slug


def release_key(tag: str) -> tuple[int, ...] | None:
    """Return a sort key for final release tags, ``None`` for anything else.

    ``1.2.0`` and ``v1.2.0`` are releases; ``1.2.0-rc1`` or ``nightly``
    are not, and never become ``stable``.
    """
    match = RELEASE_TAG.match(tag)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def load_manifest(site: Path, default_branch: str) -> dict:
    path = site / MANIFEST
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    manifest.setdefault("versions", [])
    manifest["default_branch"] = default_branch
    return manifest


def _sorted_versions(versions: list[dict], default_branch: str) -> list[dict]:
    tags = sorted(
        (v for v in versions if v["type"] == "tag"),
        key=lambda v: (release_key(v["name"]) or (), v["name"]),
        reverse=True,
    )
    branches = sorted(
        (v for v in versions if v["type"] == "branch"),
        key=lambda v: (v["name"] != default_branch, v["name"].lower()),
    )
    return tags + branches


def _copy_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _redirect_page(target: str, manifest: dict) -> str:
    items = "\n".join(
        f'      <li><a href="{html.escape(v["slug"])}/">{html.escape(v["name"])}</a></li>'
        for v in manifest["versions"]
    )
    refresh = (
        f'  <meta http-equiv="refresh" content="0; url={html.escape(target)}">\n'
        f'  <link rel="canonical" href="{html.escape(target)}">\n'
        if target
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Documentation</title>
{refresh}</head>
<body>
  <p>Available documentation versions:</p>
  <ul>
{items}
  </ul>
</body>
</html>
"""


NOT_FOUND_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Page not found</title>
  <style>
    body { font-family: "Source Sans 3", Arial, sans-serif; color: #1D1D1D;
           max-width: 40em; margin: 4em auto; padding: 0 1em; }
    h1 { color: #0A8276; font-weight: 600; }
    a { color: #0A8276; }
  </style>
</head>
<body>
  <h1>Page not found</h1>
  <p>The page you requested does not exist in this version of the
     documentation. It may have been moved, or the version may no longer
     be published.</p>
  <ul id="links"></ul>
  <script>
    // GitHub Pages serves this page for any missing path, so locate the site
    // root by probing for the versions manifest along the requested path.
    (function () {
      var parts = window.location.pathname.split("/").filter(Boolean);
      var list = document.getElementById("links");
      function add(href, text) {
        var item = document.createElement("li");
        var link = document.createElement("a");
        link.href = href;
        link.textContent = text;
        item.appendChild(link);
        list.appendChild(item);
      }
      function probe(depth) {
        if (depth > parts.length) {
          add("/", "Go to the home page");
          return;
        }
        var root = "/" + parts.slice(0, depth).join("/") + (depth ? "/" : "");
        fetch(root + "versions.json").then(function (response) {
          if (!response.ok) { throw new Error(); }
          return response.json();
        }).then(function (manifest) {
          var folder = parts[depth];
          var aliases = manifest.aliases || {};
          var slug = aliases[folder] || folder;
          var version = (manifest.versions || []).filter(function (v) {
            return v.slug === slug;
          })[0];
          if (version) {
            add(root + folder + "/", "Go to the start page of version " + version.name);
          }
          add(root, "Go to the documentation home page");
        }).catch(function () { probe(depth + 1); });
      }
      probe(0);
    })();
  </script>
</body>
</html>
"""


def regenerate(site: Path, manifest: dict) -> None:
    """Rebuild aliases, root redirect and 404 page from the manifest."""
    default_branch = manifest["default_branch"]
    versions = _sorted_versions(manifest["versions"], default_branch)
    manifest["versions"] = versions

    aliases: dict[str, str] = {}
    latest = next(
        (v for v in versions if v["type"] == "branch" and v["name"] == default_branch),
        None,
    )
    if latest:
        aliases["latest"] = latest["slug"]
    releases = [v for v in versions if v["type"] == "tag" and release_key(v["name"])]
    if releases:
        aliases["stable"] = max(releases, key=lambda v: release_key(v["name"]))["slug"]
    manifest["aliases"] = aliases

    for alias in ALIASES:
        if alias in aliases:
            _copy_tree(site / aliases[alias], site / alias)
        elif (site / alias).exists():
            shutil.rmtree(site / alias)

    home = next((f"{a}/" for a in ("stable", "latest") if a in aliases), "")
    if not home and versions:
        home = f'{versions[0]["slug"]}/'

    (site / "index.html").write_text(_redirect_page(home, manifest), encoding="utf-8")
    (site / "404.html").write_text(NOT_FOUND_PAGE, encoding="utf-8")
    (site / ".nojekyll").touch()
    (site / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def add_version(
    site: Path,
    html_dir: Path,
    ref: str,
    ref_type: str,
    commit: str,
    default_branch: str,
) -> str:
    """Publish ``html_dir`` as the docs of ``ref`` and return its slug."""
    if not (html_dir / "index.html").is_file():
        raise SiteError(f"{html_dir} does not contain a built HTML site.")

    slug = slugify(ref)
    if slug in RESERVED:
        raise SiteError(
            f"Ref {ref!r} maps to the reserved folder {slug!r}; rename the ref."
        )

    manifest = load_manifest(site, default_branch)
    for version in manifest["versions"]:
        same_ref = version["name"] == ref and version["type"] == ref_type
        if version["slug"] == slug and not same_ref:
            raise SiteError(
                f"{ref_type} {ref!r} and {version['type']} {version['name']!r} "
                f"both map to the folder {slug!r}; rename one of them."
            )
    manifest["versions"] = [v for v in manifest["versions"] if v["slug"] != slug]
    manifest["versions"].append(
        {
            "name": ref,
            "slug": slug,
            "type": ref_type,
            "commit": commit,
            "updated": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
        }
    )

    _copy_tree(html_dir, site / slug)
    for byproduct in BUILD_BYPRODUCTS:
        path = site / slug / byproduct
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    regenerate(site, manifest)
    return slug


def remove_version(site: Path, ref: str, ref_type: str, default_branch: str) -> bool:
    """Unpublish the docs of ``ref``. Returns ``False`` if it was not published."""
    manifest = load_manifest(site, default_branch)
    match = [
        v for v in manifest["versions"] if v["name"] == ref and v["type"] == ref_type
    ]
    if not match:
        return False
    for version in match:
        if (site / version["slug"]).exists():
            shutil.rmtree(site / version["slug"])
    manifest["versions"] = [v for v in manifest["versions"] if v not in match]
    regenerate(site, manifest)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    slug_cmd = commands.add_parser("slug", help="print the URL slug of a ref")
    slug_cmd.add_argument("ref")

    for name, help_text in (
        ("add", "publish a built HTML directory as a version"),
        ("remove", "unpublish a version"),
    ):
        cmd = commands.add_parser(name, help=help_text)
        cmd.add_argument("--site", type=Path, required=True)
        cmd.add_argument("--ref", required=True)
        cmd.add_argument("--ref-type", choices=("branch", "tag"), required=True)
        cmd.add_argument("--default-branch", required=True)
        if name == "add":
            cmd.add_argument("--html", type=Path, required=True)
            cmd.add_argument("--commit", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "slug":
            print(slugify(args.ref))
        elif args.command == "add":
            slug = add_version(
                args.site, args.html, args.ref, args.ref_type, args.commit,
                args.default_branch,
            )
            print(f"Published {args.ref_type} {args.ref!r} to {slug}/")
        else:
            if remove_version(args.site, args.ref, args.ref_type, args.default_branch):
                print(f"Removed {args.ref_type} {args.ref!r}")
            else:
                print(f"{args.ref_type} {args.ref!r} was not published; nothing to do")
    except SiteError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
