# SPDX-FileCopyrightText: 2021 - 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: BSD-2-Clause
"""Common definitions for the OS/distribution variant detection library."""

from __future__ import annotations

import dataclasses
import sys
from typing import TYPE_CHECKING, NamedTuple


if TYPE_CHECKING:
    import pathlib
    from typing import Any, Final, Pattern


class Detect(NamedTuple):
    """Check whether this host is running this particular OS variant."""

    filename: str
    """The name of the file to read."""

    regex: Pattern[str]
    """The regular expression pattern to look for in the file."""

    os_id: str
    """The "ID" field in the /etc/os-release file."""

    os_version_regex: Pattern[str]
    """The regular expression pattern for the "VERSION_ID" os-release field."""


class CommandsPackage(NamedTuple):
    """Variant-specific commands related to OS packages."""

    update_db: list[str]
    """Make the package manager fetch new data from the upstream repositories."""

    install: list[str]
    """Install one or more packages from the upstream repositories."""

    list_all: list[str]
    """List the currently installed packages."""

    purge: list[str]
    """Remove a package and all its files, including configuration ones."""

    remove: list[str]
    """Remove a package and all its files, possibly leaving configuration ones."""

    remove_impl: list[str]
    """Remove a package using the low-level OS package manager."""


class CommandsPkgFile(NamedTuple):
    """Variant-specific commands related to OS package files."""

    dep_query: list[str]
    """List the packages that the one in the specified package file depends on."""

    install: list[str]
    """Install a package from a locally-fetched file."""


class Commands(NamedTuple):
    """Variant-specific commands, mainly related to the packaging system."""

    package: CommandsPackage
    """Commands related to installing packages from upstream repositories."""

    pkgfile: CommandsPkgFile
    """Commands related to installing packages from locally-fetched files."""


class DebRepo(NamedTuple):
    """Debian package repository data."""

    codename: str
    """The distribution codename (e.g. "buster")."""

    vendor: str
    """The distribution vendor ("debian", "ubuntu", etc.)."""

    sources: str
    """The APT sources list file to copy to /etc/apt/sources.list.d/."""

    keyring: str
    """The GnuPG keyring file to copy to /usr/share/keyrings/."""

    req_packages: list[str]
    """OS packages that need to be installed before `apt-get update` is run."""


class YumRepo(NamedTuple):
    """Yum/DNF package repository data."""

    yumdef: str
    """The *.repo file to copy to /etc/yum.repos.d/."""

    keyring: str
    """The keyring file to copy to /etc/pki/rpm-gpg/."""


class Builder(NamedTuple):
    """StorPool builder data."""

    alias: str
    """The builder name."""

    base_image: str
    """The base Docker image that the builder is generated from."""

    branch: str
    """The branch used by the sp-pkg tool to specify the variant."""

    kernel_package: str
    """The base kernel OS package."""

    utf8_locale: str
    """The name of the locale to use for clean UTF-8 output."""


class Supported(NamedTuple):
    """The aspects of the StorPool operation supported for this build variant."""

    repo: bool
    """Is there a StorPool third-party packages repository?"""


class Variant(NamedTuple):
    """The information about a Linux distribution version (build variant)."""

    name: str
    """The name of the variant, e.g. `ALMA9`, `UBUNTU2204`, etc."""

    descr: str
    """The human-readable description of the variant."""

    parent: str
    """The name of the variant that this one is based on."""

    family: str
    """The OS "family" that this distribution belongs to."""

    detect: Detect
    """The ways to check whether we are running this variant."""

    supported: Supported
    """The aspects of StorPool operation supported for this build variant."""

    commands: Commands
    """The OS commands to execute for particular purposes."""

    min_sys_python: str
    """The minimum Python version that we can depend on."""

    repo: DebRepo | YumRepo
    """The StorPool repository files to install."""

    package: dict[str, str]
    """The names of the packages to be used for this variant."""

    systemd_lib: str
    """The name of the directory to install systemd unit files to."""

    file_ext: str
    """The filename extension of the OS packages ("deb", "rpm", etc.)."""

    initramfs_flavor: str
    """The type of initramfs-generating tools."""

    builder: Builder
    """The data specific to the StorPool builder containers."""


class VariantUpdate(NamedTuple):
    """The changes to be applied to the parent variant definition."""

    name: str
    """The name of the new variant."""

    descr: str
    """The description of the new variant."""

    parent: str
    """The variant that the new one is based on."""

    detect: Detect
    """The ways to detect the new variant."""

    updates: dict[str, Any]
    """The changes to be applied to the parent variant's structure."""


class OSPackage(NamedTuple):
    """The attributes of a currently-installed or known OS package."""

    name: str
    """The package name."""

    version: str
    """The package version."""

    arch: str
    """The system-dependent package architecture name."""

    status: str
    """The system-dependent status of the package (installed, half-installed, removed, etc)."""


class RepoType(NamedTuple):
    """Attributes common to a StorPool package repository."""

    name: str
    """The name of the StorPool package repository."""

    extension: str
    """The extension to be used in filenames for configurating the package manager."""

    url: str
    """The base URL of the StorPool package repository."""


VERSION: Final = "3.5.2"
FORMAT_VERSION: Final = (1, 4)

REPO_TYPES: Final = [
    RepoType(name="contrib", extension="", url="https://repo.storpool.com/public/"),
    RepoType(
        name="staging",
        extension="-staging",
        url="https://repo.storpool.com/public/",
    ),
    RepoType(
        name="infra",
        extension="-infra",
        url="https://intrepo.storpool.com/repo/",
    ),
]


class VariantError(Exception):
    """Base class for errors that occurred during variant processing."""


class VariantConfigError(VariantError):
    """Invalid parameters passed to the variant routines."""


@dataclasses.dataclass(frozen=True)
class Config:
    """Runtime configuration for the sp-variant library functions."""

    args: list[str] | None = None
    """Additional arguments passed to the command."""

    command: str | None = None
    """The main argument: a command to execute, a variant specification to show, etc."""

    noop: bool = False
    """No-operation mode; display what would have been done."""

    repodir: pathlib.Path | None = None
    """The path to the directory containing the `add-storpool-repo` data files to install."""

    repotype: RepoType = REPO_TYPES[0]
    """Which StorPool repository to configure."""

    verbose: bool = False
    """Verbose operation; display diagnostic output."""

    def diag(self, msg: str) -> None:
        """Output a diagnostic message in verbose mode."""
        if self.verbose:
            print(msg, file=sys.stderr)  # noqa: T201

    @property
    def _diag_to_stderr(self) -> bool:
        """We always send the diagnostic messages to stderr now."""
        return True

    @_diag_to_stderr.setter
    def _diag_to_stderr(self, value: bool) -> None:
        """Simulate setting the property, do nothing instead."""

    # OK, this is a bit ugly. It's going away soon.
    def _do_setattr(self, name: str, value: Any) -> None:  # noqa: ANN401
        """Ignore any attempts to set the `_diag_to_stderr` member."""
        if name == "_diag_to_stderr":
            return

        _config_orig_setattr(self, name, value)


# Let us not do this ever again.
_config_orig_setattr = Config.__setattr__
Config.__setattr__ = Config._do_setattr  # type: ignore[method-assign,assignment]  # noqa: SLF001


def jsonify(obj: Any) -> Any:  # noqa: ANN401  # this needs to operate on, well, anything
    """Return a more readable representation of an object."""
    if type(obj).__name__.endswith("Pattern") and hasattr(obj, "pattern"):
        return jsonify(obj.pattern)

    if hasattr(obj, "_asdict"):
        return {name: jsonify(value) for name, value in obj._asdict().items()}
    if isinstance(obj, dict):
        return {name: jsonify(value) for name, value in obj.items()}

    if isinstance(obj, list):
        return [jsonify(item) for item in obj]

    return obj
