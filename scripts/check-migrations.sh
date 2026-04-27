#!/usr/bin/env bash
#
# Refuse a commit that modifies an Alembic revision which is already part of
# the applied history on main.
#
# Why: revisions are applied to dev, staging and production in order. Editing
# one that has already run leaves environments silently divergent — the
# alembic_version table still says the revision is applied, so the edit never
# executes anywhere it matters. New behaviour goes in a new revision.
#
# Adding a brand-new revision file is always allowed.
set -euo pipefail

status=0

for path in "$@"; do
  case "$path" in
    */versions/*.py) ;;
    *) continue ;;
  esac

  # Unknown to main => new revision => fine.
  if ! git cat-file -e "origin/main:${path}" 2>/dev/null; then
    continue
  fi

  if ! git diff --quiet "origin/main" -- "$path"; then
    echo "error: ${path} is already applied on main and must not be edited." >&2
    echo "       Create a new revision instead: alembic revision -m '...'" >&2
    status=1
  fi
done

exit "$status"
