# SPDX-FileCopyrightText: 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Examine files and directories within the source tree."""

from __future__ import annotations

import functools
import pathlib
import re
import sys
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Final


CHANGELOG_FILE: Final = pathlib.Path("CHANGES.md")
"""The relative path to the changelog file from the project's top-level directory."""

CHANGELOG_SKIP_HEADINGS: Final = (
    "# Change log for the StorPool OpenStack integration",
    "## [Unreleased]",
)
"""The changelog headings to skip before the last released version entry."""

RE_KCH_ENTRY: Final = re.compile(
    r""" ^
    [#][#] \s+
    \[
        # Start with a digit, then letters, numbers, or dots, end with a non-dot.
        (?P<version>
            [0-9]
            (?:
                [0-9a-zA-Z.]*
                [0-9a-zA-Z]
            )?
        )
    \]
    \s+ - \s+
    \d{4}-\d{2}-\d{2}
    $ """,
    re.X,
)
"""Match a "Keep a Changelog"-style entry heading: version string and date."""

MARKER_FILE = pathlib.Path("defs/components.json")
"""The file to check for when we are looking for the project top-level directory."""

OURSELF: Final = ("python", "kolla_rebuild", "find.py")
"""The last parts of the absolute path to this file within the source directory."""


@functools.lru_cache
def find_topdir() -> pathlib.Path:
    """Find the project's top-level directory based on our own location."""
    try:
        ourself: Final = pathlib.Path(__file__).resolve()
    except OSError as err:
        sys.exit(f"Could not resolve the path to our own source file: {err}")
    if ourself.parts[-len(OURSELF) :] != OURSELF:
        sys.exit(
            f"Unexpected path to our own source file {ourself};"
            f" expected it to end in {OURSELF!r}"
        )

    topdir: Final = ourself.parents[len(OURSELF) - 1]
    if not (topdir / MARKER_FILE).is_file():
        sys.exit(f"No {MARKER_FILE} in the autodetect project top-level directory {topdir}")
    return topdir


def find_changelog_file() -> pathlib.Path:
    """Find the default changelog file for the project."""
    return find_topdir() / CHANGELOG_FILE


def find_sp_osi_version(*, changelog: pathlib.Path | None = None) -> str:
    """Determine the last released version of the storpool-openstack-integration package.

    This function cheats a little bit by reading the changelog file.
    """
    if changelog is None:
        changelog = find_changelog_file()
    if not changelog.is_file():
        sys.exit(f"The changelog file {changelog} does not exist or is not a regular file")

    skip = iter(CHANGELOG_SKIP_HEADINGS)
    for line in changelog.read_text(encoding="UTF-8").splitlines():
        if not line.startswith("#"):
            continue

        expected = next(skip, None)
        if expected is not None:
            if line != expected:
                sys.exit(f"Unexpected changelog heading {line!r}, expected {expected!r}")
            continue

        m_version = RE_KCH_ENTRY.match(line)
        if m_version is None:
            sys.exit(f"Unexpected format for the {line!r} changelog heading")
        return m_version.group("version")

    sys.exit("Could not find the last released version in the changelog file")
