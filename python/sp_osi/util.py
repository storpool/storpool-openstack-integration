"""Miscellaneous utilities for the StorPool OpenStack integration tooling."""

import hashlib
import pathlib

from typing import Optional


def file_sha256sum(path: pathlib.Path) -> str:
    """Read a file, calculate its SHA-256 checksum, return the hex digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_driver_path(comp_name: str, branch_name: str, file_name: str) -> Optional[pathlib.Path]:
    """Get the path to a StorPool file to update the installation with."""
    path = pathlib.Path("drivers") / comp_name / "openstack" / branch_name / file_name
    return path if path.is_file() else None
