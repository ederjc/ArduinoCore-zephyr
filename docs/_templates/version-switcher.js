// Copyright (c) Infineon Technologies AG
//
// SPDX-License-Identifier: Apache-2.0

// Version switcher for the documentation published on GitHub Pages.
//
// Every version is published to its own folder next to a shared
// versions.json manifest:
//
//   <site root>/versions.json
//   <site root>/<version>/_static/version-switcher.js   (this file)
//
// The site and version roots are derived from this script's own URL, so the
// switcher works for project pages, custom domains and the latest/stable
// aliases alike. Local builds have no manifest and keep the plain theme.
(function () {
  "use strict";

  var script = document.currentScript;
  if (!script || !window.fetch) {
    return;
  }

  var versionRoot = new URL("../", script.src);
  var siteRoot = new URL("../", versionRoot);
  var currentFolder = decodeURIComponent(
    versionRoot.pathname.replace(/\/+$/, "").split("/").pop()
  );

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function versionUrl(folder) {
    var page = window.location.pathname.indexOf(versionRoot.pathname) === 0
      ? window.location.pathname.slice(versionRoot.pathname.length)
      : "";
    return new URL(encodeURIComponent(folder) + "/" + page, siteRoot).href;
  }

  function linkList(title, entries) {
    var list = el("dl");
    list.appendChild(el("dt", null, title));
    entries.forEach(function (entry) {
      var item = el("dd");
      var link = el("a", null, entry.label);
      link.href = versionUrl(entry.folder);
      if (entry.folder === currentFolder) {
        item.appendChild(el("strong")).appendChild(link);
      } else {
        item.appendChild(link);
      }
      list.appendChild(item);
    });
    return list;
  }

  function renderSwitcher(manifest, current) {
    var aliases = manifest.aliases || {};
    var versions = manifest.versions || [];

    var flyout = el("div", "rst-versions");
    flyout.setAttribute("role", "note");
    flyout.setAttribute("aria-label", "Versions");

    var toggle = el("span", "rst-current-version");
    toggle.setAttribute("role", "button");
    toggle.setAttribute("tabindex", "0");
    toggle.appendChild(el("span", "fa fa-book", " Version"));
    toggle.appendChild(document.createTextNode(" " + current + " "));
    toggle.appendChild(el("span", "fa fa-caret-down"));

    var menu = el("div", "rst-other-versions");
    var aliasEntries = ["stable", "latest"]
      .filter(function (name) { return aliases[name]; })
      .map(function (name) {
        return { folder: name, label: name + " (" + aliases[name] + ")" };
      });
    var releases = versions
      .filter(function (v) { return v.type === "tag"; })
      .map(function (v) { return { folder: v.slug, label: v.name }; });
    var branches = versions
      .filter(function (v) { return v.type === "branch"; })
      .map(function (v) { return { folder: v.slug, label: v.name }; });

    if (aliasEntries.length) {
      menu.appendChild(linkList("Default", aliasEntries));
    }
    if (releases.length) {
      menu.appendChild(linkList("Releases", releases));
    }
    if (branches.length) {
      menu.appendChild(linkList("Branches", branches));
    }

    function toggleMenu() {
      flyout.classList.toggle("shift-up");
    }
    toggle.addEventListener("click", toggleMenu);
    toggle.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggleMenu();
      }
    });

    flyout.appendChild(toggle);
    flyout.appendChild(menu);
    document.body.appendChild(flyout);
  }

  function renderBanner(manifest, current, isBranch) {
    var stableSlug = (manifest.aliases || {}).stable;
    if (!stableSlug || current.slug === stableSlug ||
        currentFolder === "stable") {
      return;
    }
    var stable = ((manifest.versions || []).filter(function (v) {
      return v.slug === stableSlug;
    })[0] || { name: stableSlug }).name;
    var content = document.querySelector("[itemprop='articleBody']") ||
      document.querySelector("[role='main']");
    if (!content) {
      return;
    }

    var banner = el("div", "admonition warning version-banner");
    banner.appendChild(el("p", "admonition-title", "Note"));
    var text = el("p");
    text.appendChild(document.createTextNode(isBranch
      ? "This is the development documentation for the " + current.name +
        " branch and may describe unreleased features. "
      : "This is the documentation for release " + current.name +
        ", which is not the latest stable release. "));
    var link = el("a", null, "Go to the documentation of the latest release (" +
      stable + ").");
    link.href = versionUrl("stable");
    text.appendChild(link);
    banner.appendChild(text);
    content.insertBefore(banner, content.firstChild);
  }

  function render(manifest) {
    var versions = manifest.versions || [];
    var aliases = manifest.aliases || {};
    var slug = aliases[currentFolder] || currentFolder;
    var entry = versions.filter(function (v) { return v.slug === slug; })[0];
    if (!entry) {
      return;
    }
    renderSwitcher(manifest, entry.name);
    renderBanner(manifest, entry, entry.type === "branch");
  }

  function start() {
    fetch(new URL("versions.json", siteRoot).href, { cache: "no-cache" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("No versions manifest");
        }
        return response.json();
      })
      .then(render)
      .catch(function () {
        // Not served from the versioned site (e.g. a local build).
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
