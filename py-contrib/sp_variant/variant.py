# SPDX-FileCopyrightText: 2021 - 2024  StorPool <support@storpool.com>
# SPDX-License-Identifier: BSD-2-Clause
"""Build variant definitions and commands."""

from __future__ import annotations

import errno
import pathlib
import shlex
import subprocess
import typing

from . import defs
from . import vbuild
from . import yaiparser
from .defs import (
    VERSION,
    Config,
    Variant,
    VariantError,
)
from .vbuild import update_namedtuple


if typing.TYPE_CHECKING:
    from typing import Final, Iterable


class VariantKeyError(VariantError):
    """A variant with an unknown name was requested."""


class VariantFileError(VariantError):
    """A filesystem-related error occurred."""


class VariantRemoteError(VariantError):
    """An error occurred while communicating with a remote host."""

    hostname: str
    """The name of the remote host that we could not communicate with."""

    msg: str
    """The description of the error that occurred."""

    def __init__(self, hostname: str, msg: str) -> None:
        """Store the hostname and the error message."""
        super().__init__()
        self.hostname = hostname
        self.msg = msg

    def __str__(self) -> str:
        """Return a human-readable representation of the error."""
        return f"{self.hostname}: {self.msg}"


class VariantDetectError(VariantError):
    """An error that occurred during the detection of a variant."""


_DEFAULT_CONFIG = Config()

SAFEENC = "Latin-1"


def _detect_from_os_release(cfg: Config) -> Variant | None:
    """Try to match the contents of /etc/os-release with a known variant."""
    try:
        data: Final = yaiparser.YAIParser("/etc/os-release").parse()
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise
        os_id, os_version = None, None
    else:
        os_id, os_version = data.get("ID"), data.get("VERSION_ID")

    if os_id is not None and os_version is not None:
        cfg.diag(f"Matching os-release id {os_id!r} version {os_version!r}")
        for var in vbuild.DETECT_ORDER:
            cfg.diag(f"- trying {var.name}")
            if var.detect.os_id == os_id and var.detect.os_version_regex.match(os_version):
                cfg.diag("  - found it!")
                return var

    return None


def _detect_from_files(cfg: Config) -> Variant | None:
    """Try to match the contents of some variant-specific files."""
    cfg.diag("Trying non-os-release-based heuristics")
    for var in vbuild.DETECT_ORDER:
        cfg.diag(f"- trying {var.name}")
        try:
            cfg.diag(f"  - {var.detect.filename}")
            for line in pathlib.Path(var.detect.filename).read_text(encoding=SAFEENC).splitlines():
                if var.detect.regex.match(line):
                    cfg.diag(f"  - found it: {line}")
                    return var
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise VariantDetectError(
                    f"Could not read the {var.detect.filename} file: {err}",
                ) from err
            cfg.diag(f"  - no {var.detect.filename}")

    return None


def detect_variant(cfg: Config = _DEFAULT_CONFIG) -> Variant:
    """Detect the build variant for the current host."""
    vbuild.build_variants(cfg)
    cfg.diag("Trying to detect the current hosts's build variant")

    if (var := _detect_from_os_release(cfg)) is not None:
        return var

    if (var := _detect_from_files(cfg)) is not None:
        return var

    raise VariantDetectError("Could not detect the current host's build variant")


def get_all_variants(cfg: Config = _DEFAULT_CONFIG) -> dict[str, Variant]:
    """Return information about all the supported variants."""
    vbuild.build_variants(cfg)
    return dict(vbuild.VARIANTS)


def get_all_variants_in_order(cfg: Config = _DEFAULT_CONFIG) -> list[Variant]:
    """Return information about all supported variants in detect order."""
    vbuild.build_variants(cfg)
    return list(vbuild.DETECT_ORDER)


def get_by_alias(alias: str, cfg: Config = _DEFAULT_CONFIG) -> Variant:
    """Return the variant with the specified name."""
    vbuild.build_variants(cfg)
    for var in vbuild.VARIANTS.values():
        if var.builder.alias == alias:
            return var
    raise VariantKeyError(f"No variant with alias {alias}")


def get_variant(name: str, cfg: Config = _DEFAULT_CONFIG) -> Variant:
    """Return the variant with the specified name."""
    vbuild.build_variants(cfg)
    try:
        return vbuild.VARIANTS[name]
    except KeyError as err:
        raise VariantKeyError(f"No variant named {name}") from err


def list_all_packages(var: Variant, patterns: Iterable[str] | None = None) -> list[defs.OSPackage]:
    """Parse the output of the "list installed packages" command."""
    cmd: Final = list(var.commands.package.list_all)
    if patterns is not None:
        cmd.extend(patterns)

    res: Final = []
    for line in subprocess.check_output(cmd, shell=False).decode("UTF-8").splitlines():
        fields = line.split("\t")
        if len(fields) != 4:
            raise VariantFileError(f"Unexpected line in the '{shlex.join(cmd)}' output: {line!r}")
        # This may need updating at some point, but it'll work for now
        if not fields[3].startswith("ii"):
            continue

        res.append(
            defs.OSPackage(
                name=fields[0],
                version=fields[1],
                arch=fields[2],
                status="installed",
            ),
        )

    return res


__all__ = (
    "VERSION",
    "Config",
    "Variant",
    "VariantError",
    "detect_variant",
    "get_all_variants",
    "get_all_variants_in_order",
    "get_by_alias",
    "get_variant",
    "list_all_packages",
    "update_namedtuple",
)
