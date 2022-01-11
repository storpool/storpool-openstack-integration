"""Use dpkg-divert to divert files on Debian systems."""

import pathlib
import subprocess

from . import defs


class OSIDivertError(defs.OSIError):
    """An error that occurred while checking whether we can divert a file."""

    def __init__(self, path: pathlib.Path, err: str) -> None:
        """Store the path."""
        super().__init__("Could not divert {path}: {err}".format(path=path, err=err))
        self.osi_path = path


def get_diverted_name(path: pathlib.Path) -> pathlib.Path:
    """Get the target name of the divert-and-rename operation."""
    return path.with_name(path.name + ".sp-ospkg")


def has_dpkg_divert(cfg: defs.Config) -> bool:
    """Check whether we can and should use dpkg-divert."""
    if cfg.variant.family != "debian":
        print("No dpkg-divert on {vname}".format(vname=cfg.variant.name))
        return False

    if cfg.no_divert:
        print("The --no-divert option was specified")
        return False

    return True


def ensure_diverted_rename(cfg: defs.Config, path: pathlib.Path) -> pathlib.Path:
    """Simulate diverting a file on systems that do not have dpkg-divert."""
    target = get_diverted_name(path)
    print("Renaming {path} to {target}".format(path=path, target=target))
    if not cfg.noop:
        try:
            path.rename(target)
        except OSError as err:
            raise OSIDivertError(
                path,
                "Could not rename {path} to {target}: {err}".format(
                    path=path, target=target, err=err
                ),
            ) from err
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
    print(
        "Checking whether {path} is already diverted to {target}".format(path=path, target=target)
    )
    try:
        lines = subprocess.check_output(
            ["dpkg-divert", "--quiet", "--list", "--", path], encoding="UTF-8", env=cfg.utf8_env
        ).splitlines()
    except (OSError, subprocess.CalledProcessError) as err:
        raise OSIDivertError(path, "`dpkg-divert --list` failed: {err}".format(err=err)) from err

    if len(lines) > 1:
        raise OSIDivertError(
            path, "`dpkg-divert --list` returned too many lines: {lines!r}".format(lines=lines)
        )

    if len(lines) == 1:
        if lines[0] != "local diversion of {path} to {target}".format(path=path, target=target):
            raise OSIDivertError(
                path, "Unexpected `dpkg-divert --list` output: {line}".format(line=lines[0])
            )
        print("- already diverted to {target}".format(target=target))
        return target

    if not cfg.noop:
        print("- diverting it to {target}".format(target=target))
        try:
            subprocess.check_call(
                ["dpkg-divert", "--quiet", "--local", "--rename", "--divert", target, "--", path],
                env=cfg.utf8_env,
            )
        except (OSError, subprocess.CalledProcessError) as err:
            raise OSIDivertError(path, "dpkg-divert failed: {err}".format(err=err)) from err
    else:
        print("- would divert it to {target}".format(target=target))

    return target


def ensure_undiverted_rename(cfg: defs.Config, path: pathlib.Path) -> pathlib.Path:
    """Remove a simulated diversion for a file when there is no dpkg-divert."""
    target = get_diverted_name(path)
    print("Renaming {target} to {path}".format(path=path, target=target))
    if not cfg.noop:
        try:
            target.rename(path)
        except OSError as err:
            raise OSIDivertError(
                path,
                "Could not rename {target} to {path}: {err}".format(
                    path=path, target=target, err=err
                ),
            ) from err
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
    print(
        "Checking whether {path} is already diverted to {target}".format(path=path, target=target)
    )
    try:
        lines = subprocess.check_output(
            ["dpkg-divert", "--quiet", "--list", "--", path], encoding="UTF-8", env=cfg.utf8_env
        ).splitlines()
    except (OSError, subprocess.CalledProcessError) as err:
        raise OSIDivertError(path, "`dpkg-divert --list` failed: {err}".format(err=err)) from err

    if len(lines) > 1:
        raise OSIDivertError(
            path, "`dpkg-divert --list` returned too many lines: {lines!r}".format(lines=lines)
        )

    if len(lines) == 0:
        print("- not diverted at all")
        return path

    if lines[0] != "local diversion of {path} to {target}".format(path=path, target=target):
        raise OSIDivertError(
            path, "Unexpected `dpkg-divert --list` output: {line}".format(line=lines[0])
        )
    print("- currently diverted to {target}".format(target=target))

    if not cfg.noop:
        print("- removing the diversion to {target}".format(target=target))
        try:
            subprocess.check_call(
                ["dpkg-divert", "--quiet", "--local", "--rename", "--remove", "--", path],
                env=cfg.utf8_env,
            )
        except (OSError, subprocess.CalledProcessError) as err:
            raise OSIDivertError(path, "dpkg-divert failed: {err}".format(err=err)) from err
    else:
        print("- would remove the diversion to {target}".format(target=target))

    return path
