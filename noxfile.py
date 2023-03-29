# SPDX-FileCopyrightText: 2022 - 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Nox definitions for the StorPool OpenStack integration helper."""

from __future__ import annotations

import pathlib
import tempfile

import nox


nox.needs_version = ">= 2022.8.7"


class BuildError(Exception):
    """An exception that occurred while trying to build a Python wheel."""


def _read_req(flavor: str) -> list[str]:
    """Read a requirements file."""
    return (
        pathlib.Path(f"python/requirements/{flavor}.txt").read_text(encoding="UTF-8").splitlines()
    )


DISTFILES = ["python/sp_osi"]
TESTFILES = ["noxfile.py", "python/chroot_test.py"]
PYFILES = DISTFILES + TESTFILES


def _build_wheel(session: nox.Session, tempd: pathlib.Path) -> str:
    """Build a wheel using a PEP518 build system."""
    session.install("build")
    session.run("python3", "-m", "build", "-n", "-o", str(tempd), "--wheel")
    found = [
        item
        for item in tempd.iterdir()
        if item.is_file() and item.name.startswith("sp_osi-") and item.name.endswith(".whl")
    ]
    if len(found) != 1:
        raise BuildError(f"Expected a single sp_osi*.whl file in {tempd}, got {found}")
    return str(found[0])


@nox.session(tags=["check"])
def black(session: nox.Session) -> None:
    """Run the black format checker."""
    session.install(*_read_req("black"))
    session.run("black", "--check", *PYFILES)


@nox.session(tags=["check"])
def pep8(session: nox.Session) -> None:
    """Run the flake8 PEP8 compliance checker."""
    session.install(*_read_req("flake8"))
    session.run("flake8", *PYFILES)


@nox.session(tags=["check"])
def mypy(session: nox.Session) -> None:
    """Run the mypy type checker."""
    session.install(*_read_req("mypy"), *_read_req("install"), *_read_req("test"))
    session.run("mypy", *DISTFILES)
    session.run("mypy", "--python-version=3.8", *TESTFILES)


@nox.session(tags=["check"])
def pylint(session: nox.Session) -> None:
    """Run the pylint code checker."""
    session.install(*_read_req("pylint"), *_read_req("install"), *_read_req("test"))
    session.run("pylint", *PYFILES)


@nox.session(tags=["tests"])
def validate(session: nox.Session) -> None:
    """Run the internal validation checks."""
    with tempfile.TemporaryDirectory() as tempd:
        session.install(_build_wheel(session, pathlib.Path(tempd)))

    session.install(*_read_req("install"))
    session.run("sp-openstack", "-v", "validate")
