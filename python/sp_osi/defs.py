# SPDX-FileCopyrightText: 2022, 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Common definitions for the StorPool OpenStack integration helpers."""

import pathlib
import sys

from typing import Callable, Dict, List, NamedTuple

from sp_variant import variant as spvariant


class ComponentFile(NamedTuple):
    """A single file to be matched in a component definition."""

    sha256: str
    """The SHA256 checksum of the file."""


class ComponentVersion(NamedTuple):
    """A specific version of an OpenStack component."""

    comment: str
    """The human-readable description of this component version entry."""

    files: Dict[pathlib.Path, ComponentFile]
    """The list of files and checkums for this particular version."""

    outdated: bool
    """Indicate whether this component's files be updated or it is up to date."""


class Component(NamedTuple):
    """An OpenStack component with its various recognized versions."""

    detect_files_order: List[pathlib.Path]
    """The files to examine (verify checksums) to determine this component's version."""

    branches: Dict[str, Dict[str, ComponentVersion]]
    """The branches (versions) recognized for this OpenStack component."""


class ComponentsTop(NamedTuple):
    """The top-level structure of the component definitions file."""

    components: Dict[str, Component]
    """The list of OpenStack components and their versions."""


class OSIError(Exception):
    """An error that occurred during the integration setup."""


class OSIEnvError(Exception):
    """An error caused by the OS/platform environment."""


class Config(NamedTuple):
    """Runtime configuration for the sp-openstack tool."""

    all_components: ComponentsTop
    components: List[str]
    no_divert: bool
    noop: bool
    utf8_env: Dict[str, str]
    variant: spvariant.Variant
    verbose: bool

    def diag(self, func: Callable[[], str]) -> None:
        """Output a diagnostic message if requested."""
        if self.verbose:
            print(func(), file=sys.stderr)
