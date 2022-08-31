"""Common definitions for the StorPool OpenStack integration helpers."""

import pathlib
import sys

from typing import Dict, List, NamedTuple

from sp_variant import variant as spvariant

ComponentFile = NamedTuple("ComponentFile", [("sha256", str)])

ComponentVersion = NamedTuple(
    "ComponentVersion",
    [
        ("comment", str),
        ("files", Dict[pathlib.Path, ComponentFile]),
        ("outdated", bool),
    ],
)

Component = NamedTuple(
    "Component",
    [
        ("detect_files_order", List[pathlib.Path]),
        ("branches", Dict[str, Dict[str, ComponentVersion]]),
    ],
)

ComponentsTop = NamedTuple("ComponentsTop", [("components", Dict[str, Component])])


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

    def diag(self, msg: str) -> None:
        """Output a diagnostic message if requested."""
        if self.verbose:
            print(msg, file=sys.stderr)
