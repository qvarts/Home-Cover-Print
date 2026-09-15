#!/usr/bin/env bash
set -euo pipefail

# Produce a patch with the application changes only, so it can be applied
# to an existing local repository without creating any commits.
# The patch is written next to this script as cd-cover-changes.patch.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_NAME="cd-cover-changes.patch"
PATCH_PATH="${PROJECT_ROOT}/${PATCH_NAME}"

# Application files that carry the refactoring. Helper/transfer scripts and
# repository metadata are intentionally left out of the patch.
TARGETS=("main.py" "build_icon.py" "src")

cd "${PROJECT_ROOT}"

# Mark new files as intent-to-add so they show up in the diff. This only
# touches the index, it never creates a commit.
git add -N -- "${TARGETS[@]}"

# Capture the worktree diff, including binary-safe data, into the patch file.
git diff --binary -- "${TARGETS[@]}" > "${PATCH_PATH}"

# Undo the intent-to-add markers to leave the repository the way it was.
git reset -q -- "${TARGETS[@]}"

echo "Patch created:"
echo "  ${PATCH_PATH}"
