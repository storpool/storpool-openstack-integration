# SPDX-FileCopyrightText: 2022, 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Use dpkg-divert to divert files on Debian systems."""

import pathlib
import subprocess

from . import defs


class OSIDivertError(defs.OSIError):
    """An error that occurred while checking whether we can divert a file."""

    def __init__(self, path: pathlib.Path, err: str) -> None:
        """Store the path."""
        super().__init__(f"Could not divert {path}: {err}")
        self.osi_path = path


def get_diverted_name(path: pathlib.Path) -> pathlib.Path:
    """Get the target name of the divert-and-rename operation."""
    return path.with_name(path.name + ".sp-ospkg")


def has_dpkg_divert(cfg: defs.Config) -> bool:
    """Check whether we can and should use dpkg-divert."""
    if cfg.variant.family != "debian":
        print(f"No dpkg-divert on {cfg.variant.name}")
        return False

    if cfg.no_divert:
        print("The --no-divert option was specified")
        return False

    return True


def ensure_diverted_rename(cfg: defs.Config, path: pathlib.Path) -> pathlib.Path:
    """Simulate diverting a file on systems that do not have dpkg-divert."""
    target = get_diverted_name(path)
    print(f"Renaming {path} to {target}")
    if not cfg.noop:
        try:
            path.rename(target)
        except OSError as err:
            raise OSIDivertError(path, f"Could not rename {path} to {target}: {err}") from err
    else:
        print("- would rename {path} to {target}")

    return target


def ensure_diverted(cfg: defs.Config, path: pathlib.Path) -> pathlib.Path:
    """Divert a file."""
    if not path.is_absolute():
        raise OSIDivertError(path, "Internal error: ensure_diverted() invoked for a relative path")

    if not has_dpkg_divert(cfg):
        return ensure_diverted_rename(cfg, path)

    target = get_diverted_name(path)
    print(f"Checking whether {path} is already diverted to {target}")
    try:
        lines = subprocess.check_output(
            ["dpkg-divert", "--quiet", "--list", "--", path], encoding="UTF-8", env=cfg.utf8_env
        ).splitlines()
    except (OSError, subprocess.CalledProcessError) as err:
        raise OSIDivertError(path, f"`dpkg-divert --list` failed: {err}") from err

    if len(lines) > 1:
        raise OSIDivertError(path, f"`dpkg-divert --list` returned too many lines: {lines!r}")

    if len(lines) == 1:
        if lines[0] != f"local diversion of {path} to {target}":
            raise OSIDivertError(path, f"Unexpected `dpkg-divert --list` output: {lines[0]}")
        print(f"- already diverted to {target}")
        return target

    if not cfg.noop:
        print(f"- diverting it to {target}")
        try:
            subprocess.check_call(
                ["dpkg-divert", "--quiet", "--local", "--rename", "--divert", target, "--", path],
                env=cfg.utf8_env,
            )
        except (OSError, subprocess.CalledProcessError) as err:
            raise OSIDivertError(path, f"dpkg-divert failed: {err}") from err
    else:
        print(f"- would divert it to {target}")

    return target


def ensure_undiverted_rename(cfg: defs.Config, path: pathlib.Path) -> pathlib.Path:
    """Remove a simulated diversion for a file when there is no dpkg-divert."""
    target = get_diverted_name(path)
    print(f"Renaming {target} to {path}")
    if not cfg.noop:
        try:
            target.rename(path)
        except OSError as err:
            raise OSIDivertError(path, f"Could not rename {target} to {path}: {err}") from err
    else:
        print("- would rename {target} to {path}")

    return path


def ensure_undiverted(cfg: defs.Config, path: pathlib.Path) -> pathlib.Path:
    """Remove a diversion for a file."""
    if not path.is_absolute():
        raise OSIDivertError(
            path, "Internal error: ensure_undiverted() invoked for a relative path"
        )

    if not has_dpkg_divert(cfg):
        return ensure_undiverted_rename(cfg, path)

    target = get_diverted_name(path)
    print(f"Checking whether {path} is already diverted to {target}")
    try:
        lines = subprocess.check_output(
            ["dpkg-divert", "--quiet", "--list", "--", path], encoding="UTF-8", env=cfg.utf8_env
        ).splitlines()
    except (OSError, subprocess.CalledProcessError) as err:
        raise OSIDivertError(path, f"`dpkg-divert --list` failed: {err}") from err

    if len(lines) > 1:
        raise OSIDivertError(path, f"`dpkg-divert --list` returned too many lines: {lines!r}")

    if len(lines) == 0:
        print("- not diverted at all")
        return path

    if lines[0] != f"local diversion of {path} to {target}":
        raise OSIDivertError(path, f"Unexpected `dpkg-divert --list` output: {lines[0]}")
    print(f"- currently diverted to {target}")

    if not cfg.noop:
        print(f"- removing the diversion to {target}")
        try:
            subprocess.check_call(
                ["dpkg-divert", "--quiet", "--local", "--rename", "--remove", "--", path],
                env=cfg.utf8_env,
            )
        except (OSError, subprocess.CalledProcessError) as err:
            raise OSIDivertError(path, f"dpkg-divert failed: {err}") from err
    else:
        print(f"- would remove the diversion to {target}")

    return path
