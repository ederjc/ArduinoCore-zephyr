#!/usr/bin/env bash
# Copyright (c) Infineon Technologies AG
#
# SPDX-License-Identifier: Apache-2.0
#
# Apply one change to the documentation site stored in the gh-pages branch.
#
# Usage: update_docs_site.sh <add|remove> [docs_site.py options...]
#
# Environment:
#   DOCS_SITE_BRANCH          branch holding the site (default: gh-pages)
#   DOCS_SITE_COMMIT_MESSAGE  message of the published commit
#   DOCS_SITE_PUSH_ATTEMPTS   push attempts before giving up (default: 5)
#
# The current site is exported from gh-pages into a scratch directory,
# docs_site.py applies the change, and the result is pushed back as a single
# orphan commit. The branch therefore holds only the current site, so it
# does not grow with every publish.
#
# Documentation runs for different refs may publish at the same time. The
# push uses --force-with-lease against the exact commit the change was based
# on; if another run won the race, the change is re-applied on top of the new
# site and pushed again.
#
# Must run inside a checkout of the repository with push access to origin.

set -euo pipefail

branch="${DOCS_SITE_BRANCH:-gh-pages}"
attempts="${DOCS_SITE_PUSH_ATTEMPTS:-5}"
message="${DOCS_SITE_COMMIT_MESSAGE:-docs: update documentation site}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
action="$1"
shift

export GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-github-actions[bot]}"
export GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

for attempt in $(seq 1 "$attempts"); do
  site="$work/site"
  rm -rf "$site" "$work/index"
  mkdir -p "$site"

  if git fetch --quiet --no-tags --depth=1 origin \
      "+refs/heads/$branch:refs/remotes/origin/$branch" 2>/dev/null; then
    base="$(git rev-parse "refs/remotes/origin/$branch")"
    git archive "$base" | tar -x -C "$site"
  else
    if [[ "$action" == "remove" ]]; then
      echo "Branch $branch does not exist; nothing to remove."
      exit 0
    fi
    base=""
  fi

  python3 "$script_dir/docs_site.py" "$action" --site "$site" "$@"

  gitdir="$(git rev-parse --absolute-git-dir)"
  tree="$(GIT_INDEX_FILE="$work/index" git --git-dir="$gitdir" -C "$site" \
            --work-tree="$site" add --all . &&
          GIT_INDEX_FILE="$work/index" git write-tree)"
  if [[ -n "$base" && "$tree" == "$(git rev-parse "$base^{tree}")" ]]; then
    echo "Site is already up to date."
    exit 0
  fi

  commit="$(git commit-tree "$tree" -m "$message")"
  if git push --force-with-lease="refs/heads/$branch:$base" origin \
      "$commit:refs/heads/$branch"; then
    echo "Pushed $commit to $branch."
    exit 0
  fi

  echo "Push rejected (attempt $attempt/$attempts); retrying on the updated site." >&2
  sleep $((attempt * 5))
done

echo "error: could not update $branch after $attempts attempts." >&2
exit 1
